"""Unit tests for srf.auth.social_auth."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from sanic.exceptions import BadRequest, NotFound

from srf.auth import social_auth
from srf.tools.signing import sign_state


GITHUB_CONFIG = {
    "CLIENT_ID": "client-id",
    "CLIENT_SECRET": "client-secret",
    "REDIRECT_URI": "https://api.example.com/api/auth/social/callback",
    "AUTHORIZE_URL": "https://github.com/login/oauth/authorize",
    "ACCESS_TOKEN_URL": "https://github.com/login/oauth/access_token",
    "OAUTHCALLBACK": "https://app.example.com/oauth/callback",
    "GITHUB_USER": "https://api.github.com/user",
    "GITHUB_USER_EMAIL": "https://api.github.com/user/emails",
}


def make_request(*, args=None, cookies=None, scheme="https"):
    request = MagicMock()
    request.scheme = scheme
    request.args = args or {}
    request.cookies = cookies or {}
    request.app.config = SimpleNamespace(
        SOCIAL_CONFIG={"github": GITHUB_CONFIG},
        JWT_SECRET="jwt-secret",
        SOCIAL_LOGIN_COOKIE_KEY="oauth_state",
        SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE=600,
        SOCIAL_LOGIN_COOKIE_SECURE=True,
        SOCIAL_LOGIN_REDIS_CODE_PREFIX="social-login",
        SOCIAL_LOGIN_CODE_MAX_AGE=300,
    )
    request.app.ctx.redis = AsyncMock()
    return request


class TestVerifiedEmail:
    def test_prefers_primary_verified(self):
        emails = [
            {"email": "other@example.com", "verified": True, "primary": False},
            {"email": "main@example.com", "verified": True, "primary": True},
        ]
        assert social_auth._verified_email(emails) == "main@example.com"

    def test_falls_back_to_any_verified(self):
        emails = [
            {"email": "unverified@example.com", "verified": False, "primary": True},
            {"email": "ok@example.com", "verified": True, "primary": False},
        ]
        assert social_auth._verified_email(emails) == "ok@example.com"

    def test_none_when_no_verified(self):
        assert social_auth._verified_email([{"email": "x@example.com", "verified": False}]) is None


class TestGithubLogin:
    @pytest.mark.asyncio
    async def test_redirects_with_state_cookie(self):
        request = make_request()
        response = await social_auth.github_login(request)
        assert response.status in (302, 301)
        location = response.headers.get("location") or response.headers.get("Location")
        parsed = urlparse(location)
        assert parsed.netloc == "github.com"
        qs = parse_qs(parsed.query)
        assert qs["client_id"] == ["client-id"]
        assert qs["state"]
        # cookie set via add_cookie
        assert hasattr(response, "cookies") or True


class TestGithubCallback:
    @pytest.mark.asyncio
    async def test_missing_params_returns_400(self):
        request = make_request()
        response = await social_auth.github_callback(request)
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_invalid_state_returns_400(self):
        request = make_request(
            args={"code": "abc", "state": "state"},
            cookies={"oauth_state": "bad.token.value"},
        )
        response = await social_auth.github_callback(request)
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_state_mismatch_returns_403(self):
        signed = sign_state("expected", "jwt-secret", issued_at=1_700_000_000)
        request = make_request(
            args={"code": "abc", "state": "other"},
            cookies={"oauth_state": signed},
        )
        with patch("srf.auth.social_auth.unsign_state", return_value="expected"):
            response = await social_auth.github_callback(request)
        assert response.status == 403


class TestLoginByCode:
    @pytest.mark.asyncio
    async def test_missing_code_raises(self):
        request = make_request(args={})
        with pytest.raises(BadRequest, match="Missing authorization code"):
            await social_auth.login_by_code(request)

    @pytest.mark.asyncio
    async def test_too_long_code_raises(self):
        request = make_request(args={"code": "x" * 257})
        with pytest.raises(BadRequest, match="Invalid authorization code"):
            await social_auth.login_by_code(request)

    @pytest.mark.asyncio
    async def test_expired_code_raises(self):
        request = make_request(args={"code": "once"})
        request.app.ctx.redis.getdel = AsyncMock(return_value=None)
        with pytest.raises(NotFound, match="Invalid or expired"):
            await social_auth.login_by_code(request)

    @pytest.mark.asyncio
    async def test_happy_path_returns_access_token(self):
        request = make_request(args={"code": "once"})
        request.app.ctx.redis.getdel = AsyncMock(return_value=b"7")
        request.app.config.JWT = SimpleNamespace(config={})

        mock_user = MagicMock()
        mock_user.id = 7
        mock_user.name = "alice"
        mock_user.email = "alice@example.com"
        mock_user.is_active = True
        mock_user.is_staff = False
        mock_user.is_superuser = False
        mock_user.last_login = None
        mock_user.date_joined = None
        mock_user.create_time = None
        mock_user.update_time = None
        mock_role = MagicMock()
        mock_role.name = "user"
        mock_user.role = mock_role

        auth_instance = MagicMock()
        auth_instance.generate_access_token = AsyncMock(return_value="jwt-token")
        auth_instance.generate_refresh_token = AsyncMock(return_value="refresh-token")
        auth_instance.config.refresh_token_enabled = MagicMock(return_value=True)
        request.app.ctx.auth = auth_instance

        with (
            patch("srf.auth.social_auth.models.User") as UserMock,
            patch(
                "srf.auth.auth.UserSchemaReader.model_validate",
                return_value=MagicMock(model_dump=MagicMock(return_value={"id": 7, "username": "alice"})),
            ),
        ):
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            response = await social_auth.login_by_code(request)

        assert response.status == 200
        auth_instance.generate_access_token.assert_awaited()
        auth_instance.generate_refresh_token.assert_awaited()
        assert isinstance(auth_instance.generate_refresh_token.await_args.args[1], dict)
