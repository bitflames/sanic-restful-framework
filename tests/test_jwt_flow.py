"""End-to-end JWT flow tests: login, /me, /verify, /refresh, logout, and the auth middleware.

Uses Sanic's built-in test client (in-process). tests/app_server.py stays the only
ReusableClient module and keeps running last (see conftest.py).
"""

import asyncio
import tempfile
import time
from pathlib import Path

import jwt
import pytest
from sanic import Sanic, json
from tortoise.contrib.sanic import register_tortoise

from srf.auth.models import Role, User
from srf.auth.route import register_auth_urls, register_jwt_urls
from srf.config import settings
from srf.middleware.authmiddleware import set_user_to_request_ctx
from tests.tortoise_config import TORTOISE_ORM

# SanicTestClient restarts the server per request, which would reset an
# in-memory SQLite database (and lose stored refresh tokens) between requests.
_DB_PATH = Path(tempfile.mkdtemp(prefix="srf-jwt-flow-")) / "db.sqlite3"
_TORTOISE_CONFIG = {**TORTOISE_ORM, "connections": {"default": f"sqlite://{_DB_PATH}"}}

JWT_SECRET = "jwt-flow-test-jwt-secret-32bytes!!!"
SECRET_KEY = "jwt-flow-test-refresh-secret-32byte!!"

EMAIL = "bob@example.com"
USERNAME = "bob"
PASSWORD = "password123"
INACTIVE_EMAIL = "inactive@example.com"
INACTIVE_USERNAME = "inactive-bob"


def create_app() -> Sanic:
    app = Sanic("srf-jwt-flow-test")
    app.config.JWT_SECRET = JWT_SECRET
    app.config.SECRET_KEY = SECRET_KEY

    register_tortoise(app, config=_TORTOISE_CONFIG, generate_schemas=True)
    register_jwt_urls(app, prefix="/api/auth")
    register_auth_urls(app, prefix="/api/auth")

    @app.get("/whoami")
    async def whoami(request):
        user = getattr(request.ctx, "user", None)
        return json({"user": user.username if user else None})

    @app.get("/protected")
    async def protected(request):
        user = getattr(request.ctx, "user", None)
        if user is None:
            return json({"detail": "anonymous"}, status=401)
        return json({"user": user.username})

    @app.get("/optional")
    async def optional(request):
        user = getattr(request.ctx, "user", None)
        return json({"user": user.username if user else None, "is_anonymous": getattr(user, "is_anonymous", False)})

    @app.middleware("request")
    async def auth_middleware(request):
        # Whitelist BEFORE authentication: the sanic-jwt endpoints and logout
        # self-handle tokens; /whoami exercises anonymous pass-through.
        if request.path.startswith("/api/auth/") or request.path == "/whoami":
            request.ctx.user = None
            return
        if request.path == "/optional":
            await set_user_to_request_ctx(request)  # optional mode (default)
            return
        await set_user_to_request_ctx(request, strict=True)

    @app.after_server_start
    async def seed(_app):
        from tortoise import Tortoise

        await Tortoise.generate_schemas()
        role, _ = await Role.get_or_create(name="user", defaults={"description": "default user role"})
        for username, email, is_active in (
            (USERNAME, EMAIL, True),
            (INACTIVE_USERNAME, INACTIVE_EMAIL, False),
        ):
            user = await User.filter(email=email).first()
            if user is None:
                user = await User.create_user({"username": username, "email": email, "password": PASSWORD, "roles": [role.name]})
            if user.is_active != is_active:
                user.is_active = is_active
                await user.save(update_fields=["is_active"])

    return app


@pytest.fixture(scope="module")
def app():
    # Earlier pytest-asyncio tests may close the main thread's default loop,
    # which sanic-jwt's Initialize still expects to find.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    return create_app()


def _login(client, account=EMAIL, password=PASSWORD):
    _, response = client.post("/api/auth/login", json={"account": account, "password": password})
    return response


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _decode(access_token: str) -> dict:
    return jwt.decode(access_token, JWT_SECRET, algorithms=["HS256"])


class TestLogin:
    def test_login_by_email(self, app):
        response = _login(app.test_client)
        assert response.status == 200
        assert response.json["access_token"]
        assert response.json["refresh_token"]

    def test_login_by_username(self, app):
        assert _login(app.test_client, account=USERNAME).status == 200

    def test_login_wrong_password(self, app):
        assert _login(app.test_client, password="wrong-password").status == 401

    def test_login_unknown_account(self, app):
        assert _login(app.test_client, account="ghost@example.com").status == 401

    def test_login_inactive_user_rejected(self, app):
        assert _login(app.test_client, account=INACTIVE_EMAIL).status == 401

    def test_login_missing_body(self, app):
        _, response = app.test_client.post("/api/auth/login")
        assert response.status == 400

    def test_login_missing_account_field(self, app):
        _, response = app.test_client.post("/api/auth/login", json={"password": PASSWORD})
        assert response.status == 401

    def test_access_token_payload_claims(self, app):
        response = _login(app.test_client)
        payload = _decode(response.json["access_token"])
        # sanic-jwt's build_payload embeds only the user id; username/roles are
        # returned by /me and refresh, not embedded in the signed token.
        assert payload["user_id"]
        assert "exp" in payload
        assert "username" not in payload
        # sanic-jwt's claim_iat defaults to False and SRF does not enable it
        assert "iat" not in payload
        assert "password" not in payload

    def test_access_token_lifetime_matches_settings(self, app):
        response = _login(app.test_client)
        payload = _decode(response.json["access_token"])
        expected = int(settings.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
        assert abs(payload["exp"] - int(time.time()) - expected) < 120


class TestMeEndpoint:
    def test_me_with_valid_token(self, app):
        response = _login(app.test_client)
        _, me = app.test_client.get("/api/auth/me", headers=_bearer(response.json["access_token"]))
        assert me.status == 200
        assert me.json["me"]["user_id"]
        assert me.json["me"]["username"] == USERNAME
        assert me.json["me"]["roles"] == ["user"]

    def test_me_without_token_is_401(self, app):
        """sanic-jwt's /me endpoint is @protected: no token means 401, not me=null."""
        _, me = app.test_client.get("/api/auth/me")
        assert me.status == 401

    def test_me_with_expired_token_is_401(self, app):
        expired = jwt.encode({"user_id": 1, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, me = app.test_client.get("/api/auth/me", headers=_bearer(expired))
        assert me.status == 401


class TestVerifyEndpoint:
    def test_verify_valid_token(self, app):
        response = _login(app.test_client)
        _, verify = app.test_client.get("/api/auth/verify", headers=_bearer(response.json["access_token"]))
        assert verify.status == 200
        assert verify.json["valid"] is True

    def test_verify_expired_token(self, app):
        expired = jwt.encode({"user_id": 1, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, verify = app.test_client.get("/api/auth/verify", headers=_bearer(expired))
        assert verify.status == 401
        assert verify.json["valid"] is False

    def test_verify_missing_header(self, app):
        _, verify = app.test_client.get("/api/auth/verify")
        assert verify.status == 401


class TestRefresh:
    def test_refresh_with_valid_access_token(self, app):
        response = _login(app.test_client)
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": response.json["refresh_token"]},
            headers=_bearer(response.json["access_token"]),
        )
        assert refreshed.status == 200
        assert refreshed.json["access_token"]
        # sanic-jwt does not rotate refresh tokens: only a new access token is returned
        assert "refresh_token" not in refreshed.json

    def test_refresh_with_expired_access_token(self, app):
        """The point of refresh: an expired access token must still unlock a new one."""
        response = _login(app.test_client)
        user_id = _decode(response.json["access_token"])["user_id"]
        expired = jwt.encode({"user_id": user_id, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": response.json["refresh_token"]},
            headers=_bearer(expired),
        )
        assert refreshed.status == 200
        assert refreshed.json["access_token"]

    def test_refresh_missing_authorization_header(self, app):
        response = _login(app.test_client)
        _, refreshed = app.test_client.post("/api/auth/refresh", json={"refresh_token": response.json["refresh_token"]})
        assert refreshed.status == 401

    def test_refresh_rejects_forged_refresh_token(self, app):
        response = _login(app.test_client)
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "forged-refresh-token"},
            headers=_bearer(response.json["access_token"]),
        )
        assert refreshed.status == 401

    def test_new_access_token_authenticates_after_refresh(self, app):
        response = _login(app.test_client)
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": response.json["refresh_token"]},
            headers=_bearer(response.json["access_token"]),
        )
        _, whoami = app.test_client.get("/protected", headers=_bearer(refreshed.json["access_token"]))
        assert whoami.status == 200
        assert whoami.json["user"] == USERNAME

    def test_refresh_after_logout_is_rejected(self, app):
        response = _login(app.test_client)
        _, logged_out = app.test_client.post("/api/auth/logout", headers=_bearer(response.json["access_token"]))
        assert logged_out.status == 200
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": response.json["refresh_token"]},
            headers=_bearer(response.json["access_token"]),
        )
        assert refreshed.status == 401


class TestLogout:
    def test_logout_without_token_is_ok(self, app):
        _, response = app.test_client.post("/api/auth/logout")
        assert response.status == 200

    def test_logout_with_expired_access_token_still_revokes_refresh(self, app):
        response = _login(app.test_client)
        user_id = _decode(response.json["access_token"])["user_id"]
        expired = jwt.encode({"user_id": user_id, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, logged_out = app.test_client.post("/api/auth/logout", headers=_bearer(expired))
        assert logged_out.status == 200
        _, refreshed = app.test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": response.json["refresh_token"]},
            headers=_bearer(expired),
        )
        assert refreshed.status == 401


class TestAuthMiddleware:
    """Non-whitelisted routes require a valid, non-expired access token."""

    def test_whitelisted_route_without_token_is_anonymous(self, app):
        _, response = app.test_client.get("/whoami")
        assert response.status == 200
        assert response.json["user"] is None

    def test_whitelisted_route_skips_authentication_entirely(self, app):
        """Whitelisting happens before authenticate_request: even a valid token
        is not parsed on a whitelisted path."""
        response = _login(app.test_client)
        _, whoami = app.test_client.get("/whoami", headers=_bearer(response.json["access_token"]))
        assert whoami.status == 200
        assert whoami.json["user"] is None

    def test_no_token_is_401(self, app):
        _, response = app.test_client.get("/protected")
        assert response.status == 401

    def test_expired_token_is_401(self, app):
        expired = jwt.encode({"user_id": 1, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, response = app.test_client.get("/protected", headers=_bearer(expired))
        assert response.status == 401

    def test_wrong_signature_is_401(self, app):
        forged = jwt.encode({"user_id": 1}, "forged-secret-key-32-bytes-xxxxxx", algorithm="HS256")
        _, response = app.test_client.get("/protected", headers=_bearer(forged))
        assert response.status == 401

    def test_malformed_authorization_header_is_401(self, app):
        _, response = app.test_client.get("/protected", headers={"Authorization": "Token abc"})
        assert response.status == 401

    def test_valid_token_loads_user(self, app):
        response = _login(app.test_client)
        _, whoami = app.test_client.get("/protected", headers=_bearer(response.json["access_token"]))
        assert whoami.status == 200
        assert whoami.json["user"] == USERNAME

    def test_token_for_unknown_user_is_401(self, app):
        ghost = jwt.encode({"user_id": 99999, "exp": int(time.time()) + 3600}, JWT_SECRET, algorithm="HS256")
        _, response = app.test_client.get("/protected", headers=_bearer(ghost))
        assert response.status == 401


class TestOptionalAuthMiddleware:
    """strict=False (default): no credentials -> AnonymousUser; invalid credentials -> 401."""

    def test_no_token_resolves_to_anonymous_user(self, app):
        _, response = app.test_client.get("/optional")
        assert response.status == 200
        assert response.json["is_anonymous"] is True

    def test_valid_token_loads_user(self, app):
        response = _login(app.test_client)
        _, opt = app.test_client.get("/optional", headers=_bearer(response.json["access_token"]))
        assert opt.status == 200
        assert opt.json["user"] == USERNAME
        assert opt.json["is_anonymous"] is False

    def test_expired_token_is_401(self, app):
        """A presented-but-expired token must fail even in optional mode."""
        expired = jwt.encode({"user_id": 1, "exp": 1}, JWT_SECRET, algorithm="HS256")
        _, response = app.test_client.get("/optional", headers=_bearer(expired))
        assert response.status == 401

    def test_forged_token_is_401(self, app):
        forged = jwt.encode({"user_id": 1}, "forged-secret-key-32-bytes-xxxxxx", algorithm="HS256")
        _, response = app.test_client.get("/optional", headers=_bearer(forged))
        assert response.status == 401

    def test_malformed_authorization_header_is_401(self, app):
        _, response = app.test_client.get("/optional", headers={"Authorization": "Token abc"})
        assert response.status == 401
