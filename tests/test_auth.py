"""Unit tests for srf.auth (authenticate, retrieve_user, verify_password)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from srf.auth.auth import authenticate, retrieve_user
from srf.auth.models import User


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_requires_body(self):
        request = MagicMock()
        request.json = None
        from sanic.exceptions import BadRequest

        with pytest.raises(BadRequest, match="Request body is required"):
            await authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        request = MagicMock()
        request.json = {"email": "nobody@example.com", "password": "secret"}
        with patch("srf.auth.auth.User") as UserMock:
            UserMock.filter.return_value.select_related.return_value.first = AsyncMock(return_value=None)
            from sanic.exceptions import NotFound

            with pytest.raises(NotFound):
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
