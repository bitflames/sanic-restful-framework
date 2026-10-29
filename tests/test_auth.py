"""Unit tests for srf.auth (authenticate, retrieve_user, refresh tokens, verify_password)."""

import hashlib
import hmac
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from pydantic import ValidationError
from sanic import Sanic
from sanic.exceptions import BadRequest, Forbidden, SanicException, ServerError, Unauthorized

from srf.auth.auth import (
    authenticate,
    coerce_timedelta,
    gen_user_access_token,
    retrieve_refresh_token,
    retrieve_user,
    revoke_refresh_token,
    store_refresh_token,
)
from srf.auth.models import RefreshToken, Role, User
from srf.auth.route import register_jwt_urls
from srf.auth.schema import (
    AdminPasswordResetSchema,
    ChangePasswordSchema,
    UserLoginSchema,
    UserSchemaAdminCreate,
    UserSchemaAdminUpdate,
    UserSchemaReader,
    UserSchemaUpdate,
    UserSchemaWriter,
)
from srf.auth.viewset import UserViewSet, logout, register
from srf.config import settings
from srf.exceptions import PydanticValidationException


class TestUserLoginSchema:
    def test_email_only(self):
        sch = UserLoginSchema(account="u@example.com", password="secret")
        assert sch.account == "u@example.com"
        assert sch.is_email is True
        assert sch.password.get_secret_value() == "secret"
        assert "secret" not in repr(sch)

    def test_username_only(self):
        sch = UserLoginSchema(account="alice", password="secret")
        assert sch.account == "alice"
        assert sch.is_email is False

    def test_requires_identifier(self):
        with pytest.raises(ValidationError, match="account"):
            UserLoginSchema(password="secret")


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_requires_body(self):
        request = MagicMock()
        request.json = None

        with pytest.raises(BadRequest, match="Request body is required"):
            await authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_missing_identifier_raises(self):
        request = MagicMock()
        request.json = {"password": "secret"}
        with pytest.raises(Unauthorized, match="Unable to log in"):
            await authenticate(request)


class TestRegisterJwtUrls:
    def test_requires_sanic_app_instance(self):
        from sanic import Blueprint

        with pytest.raises(ServerError, match="requires a Sanic app instance"):
            register_jwt_urls(Blueprint("auth"))

    def test_jwt_secret_required_in_app_config(self):
        app = MagicMock(spec=Sanic)
        app.config = {}
        with pytest.raises(ServerError, match="app.config.JWT_SECRET"):
            register_jwt_urls(app)

    def test_refresh_secret_required_in_app_config(self):
        app = MagicMock(spec=Sanic)
        app.config = {"JWT_SECRET": "configured-jwt-secret"}
        with pytest.raises(ServerError, match="app.config.SECRET_KEY"):
            register_jwt_urls(app)

    def test_passes_full_jwt_config_to_initialize(self):
        app = MagicMock(spec=Sanic)
        app.config = {"JWT_SECRET": "configured-jwt-secret", "SECRET_KEY": "configured-refresh-secret"}
        with patch("srf.auth.route.Initialize") as Init:
            register_jwt_urls(app, prefix="/api/auth")
            args, kwargs = Init.call_args
            assert args[0] is app
            assert kwargs["url_prefix"] == "/api/auth"
            assert kwargs["path_to_authenticate"] == "/login"
            assert kwargs["path_to_retrieve_user"] == "/me"
            assert kwargs["path_to_verify"] == "/verify"
            assert kwargs["path_to_refresh"] == "/refresh"
            assert kwargs["algorithm"] == "HS256"
            assert kwargs["secret"] == "configured-jwt-secret"
            assert kwargs["authenticate"] is authenticate
            assert kwargs["retrieve_user"] is retrieve_user
            assert kwargs["store_refresh_token"] is store_refresh_token
            assert kwargs["retrieve_refresh_token"] is retrieve_refresh_token
            assert kwargs["refresh_token_enabled"] is True
            assert kwargs["verify_exp"] is True
            assert kwargs["expiration_delta"] == int(settings.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())


class TestJwtExpiryConfig:
    def test_coerce_timedelta_accepts_timedelta(self):
        assert coerce_timedelta(timedelta(minutes=5), "JWT_ACCESS_TOKEN_EXPIRES") == timedelta(minutes=5)

    def test_coerce_timedelta_accepts_numeric_seconds(self):
        assert coerce_timedelta(3600, "JWT_ACCESS_TOKEN_EXPIRES") == timedelta(hours=1)
        assert coerce_timedelta("90", "JWT_ACCESS_TOKEN_EXPIRES") == timedelta(seconds=90)

    @pytest.mark.parametrize("value", [0, -1, "not-a-number", None, True])
    def test_coerce_timedelta_rejects_invalid_values(self, value):
        with pytest.raises(ServerError):
            coerce_timedelta(value, "JWT_ACCESS_TOKEN_EXPIRES")

    def test_register_jwt_urls_accepts_numeric_expiry_from_app_config(self):
        from srf.config import settings

        previous = getattr(settings, "app", None)
        app = Sanic("test-jwt-expiry-app")
        app.config.JWT_SECRET = "configured-jwt-secret"
        app.config.SECRET_KEY = "configured-refresh-secret"
        app.config.JWT_ACCESS_TOKEN_EXPIRES = 3600
        try:
            settings.set_app(app)
            with patch("srf.auth.route.Initialize") as Init:
                register_jwt_urls(app, prefix="/api/auth")
                assert Init.call_args.kwargs["expiration_delta"] == 3600
        finally:
            if previous is None:
                if hasattr(settings, "app"):
                    delattr(settings, "app")
            else:
                object.__setattr__(settings, "app", previous)


class TestRetrieveUser:
    @pytest.mark.asyncio
    async def test_retrieve_user_none_payload(self):
        assert await retrieve_user(None, None) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_no_user_id(self):
        assert await retrieve_user(None, {}) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_reuses_ctx_user(self):
        """ctx-cached user short-circuits the DB query entirely."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "alice"
        mock_user.is_active = True
        mock_user.roles = []
        request = MagicMock()
        request.ctx.user = mock_user
        with patch("srf.auth.auth.User.filter") as filt:
            data = await retrieve_user(request, {"user_id": 1})
            assert data == {"user_id": 1, "username": "alice", "roles": []}
            filt.assert_not_called()


class TestRefreshTokenHandlers:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_refresh_token(self):
        request = MagicMock()
        request.app.config.SECRET_KEY = "test-refresh-hmac-key"
        request.app.ctx.auth.retrieve_refresh_token_from_request = AsyncMock(return_value="rtok")
        key = hmac.new(
            b"test-refresh-hmac-key",
            b"srf:refresh-token-storage:v1",
            hashlib.sha256,
        ).digest()
        expected_digest = hmac.new(key, b"rtok", hashlib.sha256).hexdigest()
        mock_qs = MagicMock()
        mock_qs.first = AsyncMock(return_value=MagicMock(token=expected_digest))

        with patch("srf.auth.auth.RefreshToken") as RT:
            RT.filter.return_value = mock_qs
            RT.update_or_create = AsyncMock(return_value=(MagicMock(), True))

            await store_refresh_token(user_id=3, refresh_token="rtok", request=request)
            RT.update_or_create.assert_awaited_once()
            call_kwargs = RT.update_or_create.await_args.kwargs
            assert call_kwargs["user_id"] == 3
            assert call_kwargs["defaults"]["token"] == expected_digest
            assert call_kwargs["defaults"]["token"] != "rtok"
            assert call_kwargs["defaults"]["expires_at"] is not None

            assert await retrieve_refresh_token(request, 3) == "rtok"
            retrieve_kwargs = RT.filter.call_args.kwargs
            assert retrieve_kwargs["user_id"] == 3
            assert "expires_at__gt" in retrieve_kwargs

    @pytest.mark.asyncio
    async def test_retrieve_validates_client_token_before_database_lookup(self):
        request = MagicMock()
        request.app.ctx.auth.retrieve_refresh_token_from_request = AsyncMock(return_value=None)

        with patch("srf.auth.auth.RefreshToken") as RT:
            assert await retrieve_refresh_token(request, 3) is None
            RT.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_rejects_malformed_request_without_json_body(self):
        request = MagicMock()
        request.app.ctx.auth.retrieve_refresh_token_from_request = AsyncMock(side_effect=AttributeError)

        with patch("srf.auth.auth.RefreshToken") as RT:
            assert await retrieve_refresh_token(request, 3) is None
            RT.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_rejects_token_when_digest_does_not_match(self):
        request = MagicMock()
        request.app.config.SECRET_KEY = "test-refresh-hmac-key"
        request.app.ctx.auth.retrieve_refresh_token_from_request = AsyncMock(return_value="wrong-token")
        mock_qs = MagicMock()
        mock_qs.first = AsyncMock(return_value=MagicMock(token="stored-digest"))

        with patch("srf.auth.auth.RefreshToken") as RT:
            RT.filter.return_value = mock_qs
            assert await retrieve_refresh_token(request, 3) is None

    @pytest.mark.asyncio
    async def test_store_requires_secret_key(self):
        request = MagicMock()
        request.app.config.SECRET_KEY = None

        with pytest.raises(ServerError, match="SECRET_KEY must be a non-empty string or bytes"):
            await store_refresh_token(user_id=3, refresh_token="rtok", request=request)

    @pytest.mark.asyncio
    async def test_store_rejects_unsupported_secret_key_type(self):
        request = MagicMock()
        request.app.config.SECRET_KEY = 123

        with pytest.raises(ServerError, match="SECRET_KEY must be a non-empty string or bytes"):
            await store_refresh_token(user_id=3, refresh_token="rtok", request=request)

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        request = MagicMock()
        mock_qs = MagicMock()
        mock_qs.delete = AsyncMock()
        with patch("srf.auth.auth.RefreshToken") as RT:
            RT.filter.return_value = mock_qs
            await revoke_refresh_token(request, 9)
            RT.filter.assert_called_with(user_id=9)
            mock_qs.delete.assert_awaited()

    @pytest.mark.asyncio
    async def test_gen_user_access_token_includes_refresh_when_enabled(self):
        auth = MagicMock()
        auth.generate_access_token = AsyncMock(return_value="access")
        auth.generate_refresh_token = AsyncMock(return_value="refresh")
        auth.config.refresh_token_enabled = MagicMock(return_value=True)

        request = MagicMock()
        request.app.ctx.auth = auth
        user = MagicMock()
        user.id = 1
        user.name = "alice"
        user.role = MagicMock()
        user.role.name = "user"
        user.email = "a@b.com"
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.last_login = None
        user.create_time = MagicMock()
        user.update_time = MagicMock()
        user.fetch_related = AsyncMock()

        with patch(
            "srf.auth.auth.UserSchemaReader.model_validate",
            return_value=MagicMock(model_dump=MagicMock(return_value={"id": 1, "username": "alice"})),
        ):
            data = await gen_user_access_token(request, user)

        assert data["access_token"] == "access"
        assert data["refresh_token"] == "refresh"
        # Register path regression: roles must be fetched before serialization.
        user.fetch_related.assert_awaited_once_with("roles")
        user_arg = auth.generate_refresh_token.await_args.args[1]
        assert isinstance(user_arg, dict)
        assert user_arg["user_id"] == 1


class _LogoutConfig:
    def __contains__(self, item: str) -> bool:
        return False


def _logout_auth(token: str, secret: str = "secret"):
    auth = MagicMock()
    auth.config = _LogoutConfig()
    auth._get_token = MagicMock(return_value=token)
    auth._get_secret = AsyncMock(return_value=secret)
    auth._get_algorithm = MagicMock(return_value="HS256")
    return auth


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token_when_access_token_expired(self):
        token = jwt.encode({"user_id": 5, "exp": 1}, "secret", algorithm="HS256")
        request = MagicMock()
        request.app.ctx.auth = _logout_auth(token)

        with patch("srf.auth.viewset.revoke_refresh_token", new_callable=AsyncMock) as rev:
            response = await logout(request)
            assert response.status == 200
            rev.assert_awaited_once_with(request, 5)

    @pytest.mark.asyncio
    async def test_logout_invalid_signature_does_not_revoke(self):
        token = jwt.encode({"user_id": 5, "exp": 1}, "other-secret", algorithm="HS256")
        request = MagicMock()
        request.app.ctx.auth = _logout_auth(token)

        with patch("srf.auth.viewset.revoke_refresh_token", new_callable=AsyncMock) as rev:
            response = await logout(request)
            assert response.status == 200
            rev.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_logout_without_token_still_ok(self):
        from sanic_jwt.exceptions import MissingAuthorizationHeader

        auth = _logout_auth("unused")
        auth._get_token = MagicMock(side_effect=MissingAuthorizationHeader())
        request = MagicMock()
        request.app.ctx.auth = auth

        with patch("srf.auth.viewset.revoke_refresh_token", new_callable=AsyncMock) as rev:
            response = await logout(request)
            assert response.status == 200
            rev.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_logout_malformed_authorization_header_is_ok(self):
        from sanic_jwt.exceptions import InvalidAuthorizationHeader

        auth = _logout_auth("unused")
        auth._get_token = MagicMock(side_effect=InvalidAuthorizationHeader())
        request = MagicMock()
        request.app.ctx.auth = auth

        with patch("srf.auth.viewset.revoke_refresh_token", new_callable=AsyncMock) as rev:
            response = await logout(request)
            assert response.status == 200
            rev.assert_not_awaited()


class TestUserVerifyPassword:
    def test_verify_password_none_password_returns_false(self):
        user = object.__new__(User)
        user.password = None
        assert user.verify_password("anything") is False

    def test_verify_password_uses_sha256_bcrypt(self):
        import hashlib

        import bcrypt

        hashed = User.hash_password("secret")
        assert hashed.startswith("$2")
        digest = hashlib.sha256(b"secret").digest()
        assert bcrypt.checkpw(digest, hashed.encode("utf-8")) is True
        # Must not be raw bcrypt(password)
        assert bcrypt.checkpw(b"secret", hashed.encode("utf-8")) is False

        user = object.__new__(User)
        user.password = hashed
        object.__setattr__(user, "id", 1)
        object.__setattr__(user, "name", "alice")
        assert user.verify_password("secret") is True
        assert user.verify_password("wrong") is False
        assert "secret" not in repr(user)
        assert "**********" in repr(user)

    def test_legacy_bcrypt_password_hash_is_rejected(self):
        """No fallback: stored bcrypt(password) must not verify."""
        import bcrypt

        legacy = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
        user = object.__new__(User)
        user.password = legacy
        assert user.verify_password("password123") is False


class TestPasswordSchemas:
    def test_username_matches_django_max_length(self):
        username = "u" * 150
        user_data = {
            "username": username,
            "email": "a@example.com",
            "password1": "Secret123",
            "password2": "Secret123",
        }
        assert UserSchemaWriter.model_validate(user_data, by_alias=True).username == username
        assert UserSchemaUpdate.model_validate({"username": username}).username == username

    @pytest.mark.parametrize(
        "schema_cls,payload",
        [
            (
                UserSchemaWriter,
                {
                    "username": "u" * 151,
                    "email": "a@example.com",
                    "password1": "Secret123",
                    "password2": "Secret123",
                },
            ),
            (UserSchemaUpdate, {"username": "u" * 151}),
        ],
    )
    def test_username_rejects_values_longer_than_django_max_length(self, schema_cls, payload):
        with pytest.raises(ValidationError):
            schema_cls.model_validate(payload, by_alias=True)

    def test_writer_accepts_matching_strong_password(self):
        sch = UserSchemaWriter.model_validate(
            {"username": "alice", "email": "a@example.com", "password1": "Secret123", "password2": "Secret123"},
            by_alias=True,
        )
        assert sch.password.get_secret_value() == "Secret123"

    def test_writer_rejects_mismatch(self):
        with pytest.raises(ValidationError, match="do not match"):
            UserSchemaWriter.model_validate(
                {"username": "alice", "email": "a@example.com", "password1": "Secret123", "password2": "Secret124"},
                by_alias=True,
            )

    def test_writer_rejects_short_password(self):
        with pytest.raises(ValidationError, match="at least 8"):
            UserSchemaWriter.model_validate(
                {"username": "alice", "email": "a@example.com", "password1": "Ab1", "password2": "Ab1"},
                by_alias=True,
            )

    def test_writer_strength_failure_is_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            UserSchemaWriter.model_validate(
                {"username": "alice", "email": "a@example.com", "password1": "nodigit!", "password2": "nodigit!"},
                by_alias=True,
            )
        assert "digit" in str(exc_info.value)

    def test_writer_rejects_password_without_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            UserSchemaWriter.model_validate(
                {"username": "alice", "email": "a@example.com", "password1": "SecretOnly", "password2": "SecretOnly"},
                by_alias=True,
            )

    def test_writer_requires_password(self):
        with pytest.raises(ValidationError):
            UserSchemaWriter.model_validate({"username": "alice", "email": "a@example.com"}, by_alias=True)

    def test_writer_allows_missing_email(self):
        sch = UserSchemaWriter.model_validate(
            {"username": "alice", "password1": "Secret123", "password2": "Secret123"},
            by_alias=True,
        )
        assert sch.email is None

    def test_update_schema_has_no_email_or_password_fields(self):
        sch = UserSchemaUpdate.model_validate({"username": "alice"}, by_alias=True)
        assert sch.username == "alice"
        assert not hasattr(sch, "email")
        assert not hasattr(sch, "password")

    def test_change_password_schema_requires_old(self):
        sch = ChangePasswordSchema.model_validate(
            {"old_password": "password123", "password1": "Secret123", "password2": "Secret123"},
            by_alias=True,
        )
        assert sch.old_password.get_secret_value() == "password123"

    def test_password_schemas_accept_alias_and_field_names(self):
        """Change/reset password schemas expose the same field names."""
        cases = [
            (ChangePasswordSchema, {"old_password": "password123", "password1": "Secret123", "password2": "Secret123"}),
            (ChangePasswordSchema, {"old_password": "password123", "password": "Secret123", "password_confirm": "Secret123"}),
            (AdminPasswordResetSchema, {"password1": "Secret123", "password2": "Secret123"}),
            (AdminPasswordResetSchema, {"password": "Secret123", "password_confirm": "Secret123"}),
        ]
        for schema_cls, payload in cases:
            sch = schema_cls.model_validate(payload, by_alias=True)
            assert sch.password.get_secret_value() == "Secret123"


class TestUserPerformUpdateAndChangePassword:
    @pytest.mark.asyncio
    async def test_perform_update_does_not_touch_password(self, db):
        """User update ignores password (schema has no password fields) and persists other fields."""
        user = await User.create_user({"username": "alice", "email": "alice@example.com", "password": "password123"})
        old_hash = user.password

        sch = UserSchemaUpdate.model_validate({"username": "alice2"}, by_alias=True)
        vs = UserViewSet()
        updated = await vs.perform_update(sch, user)

        assert updated.username == "alice2"
        assert updated.password == old_hash
        refreshed = await User.get(pk=user.id)
        assert refreshed.password == old_hash

    def test_update_schema_rejects_explicit_null_for_non_nullable_fields(self):
        """Explicit null for a NOT NULL field is a 422, not a DB error."""
        with pytest.raises(ValidationError, match="username may not be null"):
            UserSchemaUpdate.model_validate({"username": None}, by_alias=True)

    def test_admin_update_schema_rejects_explicit_null_for_flags(self):
        with pytest.raises(ValidationError, match="is_active may not be null"):
            UserSchemaAdminUpdate.model_validate({"is_active": None}, by_alias=True)

    @pytest.mark.asyncio
    async def test_change_password_action(self, db):
        """Real-DB run: change_password persists the new hash and clears refresh tokens."""
        user = await User.create_user({"username": "alice", "email": "alice@example.com", "password": "password123"})

        request = MagicMock()
        request.json = {
            "old_password": "password123",
            "password1": "Secret123",
            "password2": "Secret123",
        }
        request.ctx.user = user

        vs = UserViewSet()
        response = await vs.change_password(request)
        assert response.status == 200

        refreshed = await User.get(pk=user.id)
        assert refreshed.verify_password("Secret123") is True
        assert refreshed.verify_password("password123") is False
        assert await RefreshToken.filter(user=user).count() == 0

    @pytest.mark.asyncio
    async def test_change_password_rejects_wrong_old(self):
        user = MagicMock(spec=User)
        user.verify_password = MagicMock(return_value=False)
        request = MagicMock()
        request.json = {
            "old_password": "wrong",
            "password1": "Secret123",
            "password2": "Secret123",
        }
        request.ctx.user = user
        vs = UserViewSet()
        with pytest.raises(BadRequest, match="The old password is incorrect."):
            await vs.change_password(request)


class TestUserViewSetSchema:
    def test_get_schema_follows_action(self):
        vs = UserViewSet()
        vs.request = MagicMock()

        cases = [
            (False, UserSchemaWriter, UserSchemaUpdate),
            (True, UserSchemaAdminCreate, UserSchemaAdminUpdate),
        ]
        for is_superuser, create_schema, update_schema in cases:
            vs.request.ctx.user.is_superuser = is_superuser
            for action, expected in [
                ("list", UserSchemaReader),
                ("retrieve", UserSchemaReader),
                ("get_self", UserSchemaReader),
                ("create", create_schema),
                ("update", update_schema),
            ]:
                vs.action = action
                assert vs.get_schema() is expected


class TestRegisterEndpoint:
    @staticmethod
    def _body(**overrides):
        body = {
            "username": "alice",
            "email": "user@example.com",
            "confirmations": "123456",
            "password1": "Secret123",
            "password2": "Secret123",
        }
        body.update(overrides)
        return body

    @staticmethod
    def _request(body, eval_result=1):
        request = MagicMock()
        request.json = body
        request.app.ctx.redis.eval = AsyncMock(return_value=eval_result)
        request.app.ctx.auth = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_register_returns_201_on_success(self):
        request = self._request(self._body())
        with (
            patch("srf.auth.viewset.in_transaction", return_value=AsyncMock()),
            patch("srf.auth.viewset.models.User.create_user", new_callable=AsyncMock) as create_user,
            patch("srf.auth.viewset.gen_user_access_token", new_callable=AsyncMock) as issue_token,
        ):
            create_user.return_value = MagicMock()
            issue_token.return_value = {"id": 1, "access_token": "token"}
            response = await register(request)

        assert response.status == 201
        create_user.assert_awaited_once()
        user_data = create_user.await_args.args[0]
        assert user_data["email"] == "user@example.com"
        assert user_data["password"] == "Secret123"

    @pytest.mark.asyncio
    async def test_register_returns_422_for_invalid_payload(self):
        request = self._request(self._body(password1="short", password2="short"))
        with pytest.raises(PydanticValidationException) as exc_info:
            await register(request)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_register_returns_400_for_non_object_json(self):
        request = self._request(["not", "an", "object"])
        with pytest.raises(BadRequest, match="JSON request body is required"):
            await register(request)

    @pytest.mark.asyncio
    async def test_register_returns_429_when_attempt_limit_exceeded(self):
        request = self._request(self._body(), eval_result=3)
        with pytest.raises(SanicException) as exc_info:
            await register(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_register_requires_configured_jwt_before_creating_user(self, db):
        request = self._request(self._body())
        request.app.ctx.auth = None

        with pytest.raises(ServerError, match="JWT is not configured"):
            await register(request)
        request.app.ctx.redis.eval.assert_not_awaited()
        assert await User.filter(username="alice").count() == 0

    @pytest.mark.asyncio
    async def test_register_rolls_back_user_when_token_issuance_fails(self, db):
        request = self._request(self._body())
        with (
            patch("srf.auth.viewset.gen_user_access_token", new_callable=AsyncMock, side_effect=ServerError("boom")),
            pytest.raises(ServerError, match="boom"),
        ):
            await register(request)
        assert await User.filter(username="alice").count() == 0


class TestUserSchemaReaderRoles:
    def test_roles_serialized_from_prefetched_list(self):
        from types import SimpleNamespace

        role = SimpleNamespace(id=2, name="admin", description="admin role")
        user = SimpleNamespace(
            id=1,
            username="alice",
            email="a@example.com",
            is_active=True,
            is_superuser=False,
            last_login=None,
            roles=[role],
        )
        sch = UserSchemaReader.model_validate(user)
        assert sch.roles is not None
        assert [r.name for r in sch.roles] == ["admin"]
        assert sch.roles[0].description == "admin role"

    def test_roles_none_when_relation_not_fetched(self):
        from types import SimpleNamespace

        user = SimpleNamespace(
            id=1,
            username="alice",
            email="a@example.com",
            is_active=True,
            is_superuser=False,
            last_login=None,
            roles=object(),  # non-iterable lazy-relation stand-in
        )
        sch = UserSchemaReader.model_validate(user)
        assert sch.roles is None

    def test_roles_default_none_when_attribute_missing(self):
        from types import SimpleNamespace

        user = SimpleNamespace(id=1, username="alice", email="a@example.com")
        sch = UserSchemaReader.model_validate(user)
        assert sch.roles is None


class TestUserViewSetRolesPrefetch:
    """Regression: framework serialization paths always carry roles (never null)."""

    @pytest.mark.asyncio
    async def test_queryset_prefetches_roles_for_superuser(self, db):
        vs = UserViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(is_superuser=True)
        assert "roles" in vs.queryset._prefetch_map

    @pytest.mark.asyncio
    async def test_queryset_prefetches_roles_for_plain_user(self, db):
        vs = UserViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(id=7, is_superuser=False)
        qs = vs.queryset
        assert "roles" in qs._prefetch_map

    @pytest.mark.asyncio
    async def test_gen_user_access_token_roles_empty_list_for_new_user(self, db):
        """Register path: a freshly created user serializes roles as [], not null."""
        auth = MagicMock()
        auth.generate_access_token = AsyncMock(return_value="access")
        auth.config.refresh_token_enabled = MagicMock(return_value=False)
        request = MagicMock()
        request.app.ctx.auth = auth

        user = await User.create_user({"username": "fresh", "password": "password123"})
        data = await gen_user_access_token(request, user)
        assert data["roles"] == []


class TestAdminUserManagement:
    """Superuser-only privilege fields: is_superuser / is_active / roles."""

    @pytest.mark.asyncio
    async def test_admin_create_with_privileges_and_roles(self, db):
        await Role.create(name="ops", description="ops")
        vs = UserViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(is_superuser=True)

        sch = UserSchemaAdminCreate.model_validate(
            {
                "username": "bob",
                "email": "bob@example.com",
                "password1": "Secret123",
                "password2": "Secret123",
                "is_superuser": True,
                "is_active": False,
                "roles": ["ops", "ghost-role"],
            }
        )
        user = await vs.perform_create(sch)
        assert user.is_superuser is True
        assert user.is_active is False
        await user.fetch_related("roles")
        assert [r.name for r in user.roles] == ["ops"]  # unknown role ignored

    @pytest.mark.asyncio
    async def test_perform_create_rejects_non_superuser(self, db):
        vs = UserViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(is_superuser=False)
        sch = UserSchemaAdminCreate.model_validate({"username": "x", "password1": "Secret123", "password2": "Secret123"})
        with pytest.raises(Forbidden):
            await vs.perform_create(sch)

    @pytest.mark.asyncio
    async def test_admin_update_replaces_roles_and_flags(self, db):
        admin_role = await Role.create(name="admin", description="admin")
        await Role.create(name="ops", description="ops")
        user = await User.create_user({"username": "carol", "password": "password123", "roles": ["admin"]})

        sch = UserSchemaAdminUpdate.model_validate({"roles": ["ops"], "is_active": False})
        vs = UserViewSet()
        updated = await vs.perform_update(sch, user)

        assert updated.is_active is False
        assert [r.name for r in updated.roles] == ["ops"]
        assert await admin_role.users.all().count() == 0

    @pytest.mark.asyncio
    async def test_admin_update_omitted_roles_keeps_existing(self, db):
        await Role.create(name="ops", description="ops")
        user = await User.create_user({"username": "dave", "password": "password123", "roles": ["ops"]})

        sch = UserSchemaAdminUpdate.model_validate({"username": "dave2"})
        vs = UserViewSet()
        updated = await vs.perform_update(sch, user)

        assert updated.username == "dave2"
        assert [r.name for r in updated.roles] == ["ops"]

    @pytest.mark.asyncio
    async def test_admin_update_empty_roles_clears_all(self, db):
        await Role.create(name="ops", description="ops")
        user = await User.create_user({"username": "erin", "password": "password123", "roles": ["ops"]})

        sch = UserSchemaAdminUpdate.model_validate({"roles": []})
        vs = UserViewSet()
        updated = await vs.perform_update(sch, user)
        assert list(updated.roles) == []

    @pytest.mark.asyncio
    async def test_plain_update_schema_cannot_set_privileges(self, db):
        """Non-superuser path: privilege fields are silently dropped by the schema."""
        user = await User.create_user({"username": "frank", "password": "password123"})
        sch = UserSchemaUpdate.model_validate({"username": "frank2", "is_superuser": True, "roles": ["ops"]})
        assert "is_superuser" not in sch.model_dump(exclude_unset=True)
        assert "roles" not in sch.model_dump(exclude_unset=True)

        vs = UserViewSet()
        updated = await vs.perform_update(sch, user)
        assert updated.username == "frank2"
        assert updated.is_superuser is False

    @pytest.mark.asyncio
    async def test_create_user_defaults_privileges_when_not_passed(self, db):
        """register() path never passes privilege flags; defaults must hold."""
        user = await User.create_user({"username": "grace", "password": "password123"})
        assert user.is_superuser is False
        assert user.is_active is True

    def test_admin_create_schema_requires_username(self):
        """username is required at the schema layer (the User column is NOT NULL)."""
        with pytest.raises(ValidationError, match="username"):
            UserSchemaAdminCreate.model_validate({"password1": "Secret123", "password2": "Secret123"})

    def test_admin_create_schema_requires_password(self):
        with pytest.raises(ValidationError, match="password1"):
            UserSchemaAdminCreate.model_validate({"username": "nopass"})

    @pytest.mark.asyncio
    async def test_perform_create_defaults_is_active_true(self, db):
        """Omitted is_active on create falls back to True via create_user."""
        vs = UserViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(is_superuser=True)
        sch = UserSchemaAdminCreate.model_validate({"username": "heidi", "password1": "Secret123", "password2": "Secret123"})
        user = await vs.perform_create(sch)
        assert user.is_active is True
        assert user.is_superuser is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("is_superuser", [False, True])
    async def test_update_rejects_email(self, db, is_superuser):
        user = await User.create_user({"username": "ivan", "password": "password123"})
        request = MagicMock()
        request.json = {"email": "new@example.com"}
        request.ctx.user = MagicMock(is_superuser=is_superuser)
        vs = UserViewSet()
        vs.request = request

        with pytest.raises(BadRequest, match="Email and change-password is not supported"):
            await vs.update(request, pk=user.id)

        refreshed = await User.get(pk=user.id)
        assert refreshed.email is None

    @pytest.mark.asyncio
    async def test_admin_update_rejects_password(self, db):
        """Password keys in an update payload are rejected at the view layer; use the dedicated endpoints."""
        user = await User.create_user({"username": "ivan", "password": "password123"})
        request = MagicMock()
        request.json = {"password1": "NewPass123", "password2": "NewPass123"}
        request.ctx.user = MagicMock(is_superuser=True)
        vs = UserViewSet()
        vs.request = request
        with pytest.raises(BadRequest, match="Email and change-password is not supported"):
            await vs.update(request, pk=user.id)
        refreshed = await User.get(pk=user.id)
        assert refreshed.verify_password("password123") is True

    @pytest.mark.asyncio
    async def test_create_user_role_link_error_not_misreported(self, db):
        """IntegrityError from roles.add must not surface as 'username or email already exists'."""
        from tortoise.exceptions import IntegrityError

        with patch("srf.auth.models.Role.filter", side_effect=IntegrityError("fk boom")), pytest.raises(IntegrityError, match="fk boom"):
            await User.create_user({"username": "judy", "password": "password123", "roles": ["ops"]})


class TestAdminResetPassword:
    """Superuser reset-password action, split from perform_update."""

    @pytest.mark.asyncio
    async def test_reset_password_action_revokes_refresh_tokens(self, db):
        from tortoise.timezone import now as tortoise_timezone_now

        user = await User.create_user({"username": "kate", "password": "password123"})
        await RefreshToken.create(user=user, token="digest", expires_at=tortoise_timezone_now() + timedelta(days=7))

        request = MagicMock()
        request.json = {"password1": "NewPass123", "password2": "NewPass123"}
        request.ctx.user = MagicMock(is_superuser=True)

        vs = UserViewSet()
        vs.request = request
        response = await vs.reset_password(request, pk=user.id)
        assert response.status == 200

        refreshed = await User.get(pk=user.id)
        assert refreshed.verify_password("NewPass123") is True
        assert refreshed.verify_password("password123") is False
        assert await RefreshToken.filter(user=user).count() == 0

    @pytest.mark.asyncio
    async def test_reset_password_rejects_non_superuser(self, db):
        user = await User.create_user({"username": "leo", "password": "password123"})
        request = MagicMock()
        request.json = {"password1": "NewPass123", "password2": "NewPass123"}
        request.ctx.user = MagicMock(is_superuser=False)

        vs = UserViewSet()
        vs.request = request
        with pytest.raises(Forbidden):
            await vs.reset_password(request, pk=user.id)

    @pytest.mark.asyncio
    async def test_reset_password_requires_body(self, db):
        request = MagicMock()
        request.json = None
        request.ctx.user = MagicMock(is_superuser=True)

        vs = UserViewSet()
        vs.request = request
        with pytest.raises(BadRequest, match="JSON request body is required"):
            await vs.reset_password(request, pk=1)

    def test_admin_reset_schema_requires_matching_passwords(self):
        with pytest.raises(ValidationError, match="do not match"):
            AdminPasswordResetSchema.model_validate({"password1": "Secret123", "password2": "Secret456"})
