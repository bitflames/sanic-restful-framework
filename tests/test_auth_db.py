"""Real-DB tests for srf.auth against Tortoise ORM (in-memory sqlite via the `db` fixture).

These complement the MagicMock-based unit tests in test_auth.py: every test here
executes real ORM queries, so stale field references and relation misuse surface
immediately instead of being absorbed by mocks.
"""

from unittest.mock import MagicMock

import pytest
from sanic.exceptions import Unauthorized

from srf.auth.auth import authenticate, build_user_payload, retrieve_user
from srf.auth.models import Role, User
from srf.exceptions import TargetObjectAlreadyExist

PASSWORD = "Secret123"


async def _create_user(**overrides) -> User:
    info = {"username": "alice", "email": "alice@example.com", "password": PASSWORD}
    info.update(overrides)
    return await User.create_user(info)


class TestCreateUserDB:
    @pytest.mark.asyncio
    async def test_email_is_stored_lowercase(self, db):
        user = await _create_user(email="Alice@Example.COM")
        assert user.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_duplicate_username_raises(self, db):
        await _create_user()
        with pytest.raises(TargetObjectAlreadyExist, match="username already exists"):
            await _create_user(email="other@example.com")

    @pytest.mark.asyncio
    async def test_duplicate_email_is_case_insensitive(self, db):
        await _create_user()
        with pytest.raises(TargetObjectAlreadyExist, match="email already exists"):
            await _create_user(username="bob", email="ALICE@example.com")

    @pytest.mark.asyncio
    async def test_roles_attach_existing_roles(self, db):
        await Role.create(name="admin", description="admin role")
        await Role.create(name="editor", description="editor role")
        user = await _create_user(roles=["admin", "editor"])
        await user.fetch_related("roles")
        assert sorted(r.name for r in user.roles) == ["admin", "editor"]

    @pytest.mark.asyncio
    async def test_unknown_role_names_are_silently_ignored(self, db):
        await Role.create(name="admin", description="admin role")
        user = await _create_user(roles=["admin", "ghost"])
        await user.fetch_related("roles")
        assert [r.name for r in user.roles] == ["admin"]

    @pytest.mark.asyncio
    async def test_user_without_password_is_unusable(self, db):
        user = await _create_user(password=None)
        assert user.password is None
        assert user.has_usable_password() is False
        assert user.check_password("anything") is False

    @pytest.mark.asyncio
    async def test_password_is_hashed_and_verifiable(self, db):
        user = await _create_user()
        assert user.password != PASSWORD
        assert user.check_password(PASSWORD) is True
        assert user.check_password("wrong") is False


class TestAuthenticateDB:
    @staticmethod
    def _request(json_body: dict) -> MagicMock:
        request = MagicMock()
        request.json = json_body
        return request

    @pytest.mark.asyncio
    async def test_login_by_email_is_case_insensitive(self, db):
        await _create_user()
        payload = await authenticate(self._request({"email": "Alice@Example.com", "password": PASSWORD}))
        assert payload["username"] == "alice"
        assert payload["roles"] == []

    @pytest.mark.asyncio
    async def test_login_by_username(self, db):
        await _create_user()
        payload = await authenticate(self._request({"username": "alice", "password": PASSWORD}))
        assert payload["user_id"] is not None

    @pytest.mark.asyncio
    async def test_wrong_password_rejected(self, db):
        await _create_user()
        with pytest.raises(Unauthorized):
            await authenticate(self._request({"email": "alice@example.com", "password": "WrongPass1"}))

    @pytest.mark.asyncio
    async def test_unknown_user_rejected(self, db):
        with pytest.raises(Unauthorized):
            await authenticate(self._request({"email": "ghost@example.com", "password": PASSWORD}))

    @pytest.mark.asyncio
    async def test_inactive_user_rejected(self, db):
        user = await _create_user()
        user.is_active = False
        await user.save()
        with pytest.raises(Unauthorized):
            await authenticate(self._request({"email": "alice@example.com", "password": PASSWORD}))

    @pytest.mark.asyncio
    async def test_payload_includes_roles(self, db):
        await Role.create(name="admin", description="admin role")
        await _create_user(roles=["admin"])
        payload = await authenticate(self._request({"email": "alice@example.com", "password": PASSWORD}))
        assert payload["roles"] == ["admin"]

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self, db):
        user = await _create_user()
        assert user.last_login is None
        await authenticate(self._request({"email": "alice@example.com", "password": PASSWORD}))
        await user.refresh_from_db()
        assert user.last_login is not None


class TestRetrieveUserDB:
    @staticmethod
    def _request() -> MagicMock:
        request = MagicMock()
        request.ctx.user = None
        return request

    @pytest.mark.asyncio
    async def test_returns_payload_and_caches_user_on_ctx(self, db):
        user = await _create_user()
        request = self._request()
        payload = await retrieve_user(request, {"user_id": user.id})
        assert payload["username"] == "alice"
        assert request.ctx.user.id == user.id

    @pytest.mark.asyncio
    async def test_unknown_user_returns_none(self, db):
        assert await retrieve_user(self._request(), {"user_id": 999}) is None

    @pytest.mark.asyncio
    async def test_inactive_user_returns_none(self, db):
        user = await _create_user()
        user.is_active = False
        await user.save()
        assert await retrieve_user(self._request(), {"user_id": user.id}) is None

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_none(self, db):
        assert await retrieve_user(self._request(), {}) is None


class TestBuildUserPayloadDB:
    @pytest.mark.asyncio
    async def test_prefetched_roles_come_from_cache(self, db):
        await Role.create(name="admin", description="admin role")
        user = await _create_user(roles=["admin"])
        fetched = await User.get(id=user.id).prefetch_related("roles")
        payload = await build_user_payload(fetched)
        assert payload == {"user_id": user.id, "username": "alice", "roles": ["admin"]}

    @pytest.mark.asyncio
    async def test_unfetched_roles_fall_back_to_lazy_query(self, db):
        await Role.create(name="admin", description="admin role")
        user = await _create_user(roles=["admin"])
        fresh = await User.get(id=user.id)  # roles relation not fetched
        payload = await build_user_payload(fresh)
        assert payload["roles"] == ["admin"]

    @pytest.mark.asyncio
    async def test_user_without_roles(self, db):
        user = await _create_user()
        payload = await build_user_payload(user)
        assert payload["roles"] == []
