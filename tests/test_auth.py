"""Unit tests for srf.auth (authenticate, retrieve_user, verify_password)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError
from sanic.exceptions import BadRequest, NotFound, ServerError

from srf.auth.auth import authenticate, retrieve_user
from srf.auth.models import User
from srf.auth.schema import UserLoginSchema
from srf.auth.viewset import setup_auth


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

            with pytest.raises(NotFound):
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
            # username-only must not query email=None
            filter_arg = UserMock.filter.call_args[0][0]
            assert "email" not in str(filter_arg).lower() or "None" not in str(filter_arg)

    @pytest.mark.asyncio
    async def test_authenticate_missing_identifier_raises(self):
        request = MagicMock()
        request.json = {"password": "secret"}
        with pytest.raises(NotFound, match="Unable to log in"):
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


class TestRetrieveUser:
    @pytest.mark.asyncio
    async def test_retrieve_user_none_payload(self):
        assert await retrieve_user(None) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_no_user_id(self):
        assert await retrieve_user({}) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_not_found(self):
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=None)
            assert await retrieve_user({"user_id": 999}) is None

    @pytest.mark.asyncio
    async def test_retrieve_user_found(self):
        mock_user = MagicMock()
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=mock_user)
            user = await retrieve_user({"user_id": 1})
            assert user is mock_user


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
