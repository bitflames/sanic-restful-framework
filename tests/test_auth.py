"""Unit tests for srf.auth (authenticate, retrieve_user, refresh tokens, verify_password)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sanic.exceptions import BadRequest, ServerError, Unauthorized

from srf.auth.auth import (
    authenticate,
    build_user_payload,
    gen_user_access_token,
    retrieve_refresh_token,
    retrieve_user,
    revoke_refresh_token,
    store_refresh_token,
)
from srf.auth.models import User
from srf.auth.schema import UserLoginSchema
from srf.auth.viewset import logout, setup_auth
from srf.config import settings


class TestUserLoginSchema:
    def test_email_only(self):
        sch = UserLoginSchema(email="u@example.com", password="secret")
        assert sch.email == "u@example.com"
        assert sch.username is None

    def test_username_only(self):
        sch = UserLoginSchema(username="alice", password="secret")
        assert sch.username == "alice"
        assert sch.email is None

    def test_requires_identifier(self):
        with pytest.raises(ValidationError, match="email or username is required"):
            UserLoginSchema(password="secret")


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_requires_body(self):
        request = MagicMock()
        request.json = None

        with pytest.raises(BadRequest, match="Request body is required"):
            await authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        request = MagicMock()
        request.json = {"email": "nobody@example.com", "password": "secret"}
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=None)

            with pytest.raises(Unauthorized, match="Unable to log in"):
                await authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_by_username(self):
        request = MagicMock()
        request.json = {"username": "alice", "password": "right"}
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.name = "alice"
        mock_user.verify_password = MagicMock(return_value=True)
        mock_user.role = MagicMock(name="user")
        mock_user.role.name = "user"
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            payload = await authenticate(request)
            assert payload["user_id"] == 2
            assert payload["username"] == "alice"
            filter_arg = UserMock.filter.call_args[0][0]
            assert "email" not in str(filter_arg).lower() or "None" not in str(filter_arg)

    @pytest.mark.asyncio
    async def test_authenticate_missing_identifier_raises(self):
        request = MagicMock()
        request.json = {"password": "secret"}
        with pytest.raises(Unauthorized, match="Unable to log in"):
            await authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_returns_serializable_role(self):
        request = MagicMock()
        request.json = {"email": "u@example.com", "password": "right"}
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "alice"
        mock_user.verify_password = MagicMock(return_value=True)
        mock_role = MagicMock()
        mock_role.name = "user"
        mock_user.role = mock_role
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            payload = await authenticate(request)
            assert payload["user_id"] == 1
            assert payload["username"] == "alice"
            assert payload["role"] == "user"


class TestSetupAuth:
    def test_secret_required(self):
        app = MagicMock()
        with pytest.raises(ServerError, match="secret is required"):
            setup_auth(app)

    def test_passes_refresh_and_expiration(self):
        app = MagicMock()
        with patch("srf.auth.viewset.Initialize") as Init:
            setup_auth(app, secret="s3cret", url_prefix="/api/auth")
            kwargs = Init.call_args.kwargs
            assert kwargs["refresh_token_enabled"] is True
            assert kwargs["store_refresh_token"] is store_refresh_token
            assert kwargs["retrieve_refresh_token"] is retrieve_refresh_token
            assert kwargs["expiration_delta"] == int(settings.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())


class TestRetrieveUser:
    @pytest.mark.asyncio
    async def test_retrieve_user_none_payload(self):
        assert await retrieve_user(None, None) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_no_user_id(self):
        assert await retrieve_user(None, {}) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_not_found(self):
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=None)
            assert await retrieve_user(None, {"user_id": 999}) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_found_sets_ctx_and_returns_dict(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "alice"
        mock_user.is_active = True
        mock_user.role = MagicMock()
        mock_user.role.name = "user"
        request = MagicMock()
        request.ctx.user = None
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            data = await retrieve_user(request, {"user_id": 1})
            assert data == {"user_id": 1, "username": "alice", "role": "user"}
            assert request.ctx.user is mock_user

    @pytest.mark.asyncio
    async def test_retrieve_user_reuses_ctx_user(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "alice"
        mock_user.is_active = True
        mock_user.role = MagicMock()
        mock_user.role.name = "user"
        request = MagicMock()
        request.ctx.user = mock_user
        with patch("srf.auth.auth.User.filter") as filt:
            data = await retrieve_user(request, {"user_id": 1})
            assert data == {"user_id": 1, "username": "alice", "role": "user"}
            filt.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_user_inactive_returns_none(self):
        mock_user = MagicMock()
        mock_user.is_active = False
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            assert await retrieve_user(None, {"user_id": 1}) is None


class TestRefreshTokenHandlers:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_refresh_token(self):
        request = MagicMock()
        mock_qs = MagicMock()
        mock_qs.delete = AsyncMock()
        mock_qs.first = AsyncMock(return_value=MagicMock(token="rtok"))

        with patch("srf.auth.auth.RefreshToken") as RT:
            RT.filter.return_value = mock_qs
            RT.create = AsyncMock()

            await store_refresh_token(user_id=3, refresh_token="rtok", request=request)
            mock_qs.delete.assert_awaited()
            RT.create.assert_awaited()
            create_kw = RT.create.await_args.kwargs
            assert create_kw["user_id"] == 3
            assert create_kw["token"] == "rtok"
            assert create_kw["expires_at"] is not None

            assert await retrieve_refresh_token(request, 3) == "rtok"
            retrieve_kwargs = RT.filter.call_args.kwargs
            assert retrieve_kwargs["user_id"] == 3
            assert "expires_at__gt" in retrieve_kwargs

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
        user.date_joined = None
        user.create_time = MagicMock()
        user.update_time = MagicMock()

        with patch(
            "srf.auth.auth.UserSchemaReader.model_validate",
            return_value=MagicMock(model_dump=MagicMock(return_value={"id": 1, "username": "alice"})),
        ):
            data = await gen_user_access_token(request, user)

        assert data["access_token"] == "access"
        assert data["refresh_token"] == "refresh"
        user_arg = auth.generate_refresh_token.await_args.args[1]
        assert isinstance(user_arg, dict)
        assert user_arg["user_id"] == 1


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self):
        auth = MagicMock()
        auth.extract_payload = AsyncMock(return_value={"user_id": 5})
        request = MagicMock()
        request.app.ctx.auth = auth

        with patch("srf.auth.viewset.revoke_refresh_token", new_callable=AsyncMock) as rev:
            response = await logout(request)
            assert response.status == 200
            rev.assert_awaited_once_with(request, 5)

    @pytest.mark.asyncio
    async def test_logout_without_token_still_ok(self):
        auth = MagicMock()
        auth.extract_payload = AsyncMock(side_effect=Exception("no token"))
        request = MagicMock()
        request.app.ctx.auth = auth

        response = await logout(request)
        assert response.status == 200


class TestNonAuthEndpoints:
    def test_public_endpoints_use_full_paths(self):
        assert "/api/auth/refresh" in settings.NON_AUTH_ENDPOINTS
        assert "/api/auth/send-verification-email" in settings.NON_AUTH_ENDPOINTS
        assert "refresh" not in settings.NON_AUTH_ENDPOINTS


class TestUserVerifyPassword:
    def test_verify_password_none_password_returns_false(self):
        user = object.__new__(User)
        user.password = None
        assert user.verify_password("anything") is False

    def test_verify_password_uses_bcrypt(self):
        import bcrypt

        pwd = b"secret"
        hashed = bcrypt.hashpw(pwd, bcrypt.gensalt())
        user = object.__new__(User)
        user.password = hashed.decode("utf-8")
        assert user.verify_password("secret") is True
        assert user.verify_password("wrong") is False


class TestBuildUserPayload:
    def test_build_user_payload(self):
        user = object.__new__(User)
        object.__setattr__(user, "id", 7)
        object.__setattr__(user, "name", "alice")
        role = MagicMock()
        role.name = "admin"
        object.__setattr__(user, "role", role)
        assert build_user_payload(user) == {"user_id": 7, "username": "alice", "role": "admin"}

    def test_build_user_payload_no_role(self):
        user = object.__new__(User)
        object.__setattr__(user, "id", 1)
        object.__setattr__(user, "name", "bob")
        object.__setattr__(user, "role", None)
        assert build_user_payload(user) == {"user_id": 1, "username": "bob", "role": None}

