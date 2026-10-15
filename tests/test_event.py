"""Unit tests for srf.event."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sanic.exceptions import Forbidden

from srf.event.models import Event
from srf.event.schema import EventSchema
from srf.event.viewset import EventViewSet
from srf.permission.permission import SuperuserOnly


class TestEventSchemas:
    def test_schema_accepts_audit_payload(self):
        sch = EventSchema.model_validate(
            {
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_remote": "api",
                "req_data": {"username": "alice"},
                "res_data": {"ok": True},
            }
        )
        assert sch.action == "user.update"
        assert sch.obj_id == 7
        assert sch.req_remote == "api"
        assert sch.req_data == {"username": "alice"}

    def test_schema_rejects_oversized_action(self):
        with pytest.raises(ValidationError):
            EventSchema.model_validate({"action": "x" * 129})

    def test_schema_accepts_full_payload(self):
        sch = EventSchema.model_validate(
            {
                "id": 3,
                "user_id": 9,
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_remote": "api",
                "create_time": datetime(2026, 8, 14, 4, 0, tzinfo=UTC),
            }
        )
        assert sch.id == 3
        assert sch.user_id == 9
        assert sch.create_time == datetime(2026, 8, 14, 4, 0, tzinfo=UTC)


class TestEventViewSet:
    def test_get_schema_is_event_schema(self):
        vs = EventViewSet()
        vs.request = MagicMock()
        vs.action = "retrieve"
        assert vs.get_schema() is EventSchema
        vs.action = "create"
        assert vs.get_schema() is EventSchema

    def _superuser_view(self):
        vs = EventViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = SimpleNamespace(is_superuser=True)
        return vs

    def test_queryset_uses_event_model(self):
        with patch.object(Event, "all", return_value="qs") as all_mock:
            assert self._superuser_view().queryset == "qs"
            all_mock.assert_called_once()

    def test_permission_is_superuser_only(self):
        assert EventViewSet.permission_classes == (SuperuserOnly,)

    def test_search_and_filter_fields_match_model(self):
        assert "action" in EventViewSet.search_fields
        assert "obj_name" in EventViewSet.search_fields
        assert "user_id" in EventViewSet.filter_fields
        assert "obj_id" in EventViewSet.filter_fields

    @pytest.mark.asyncio
    async def test_check_permissions_requires_superuser(self):
        vs = EventViewSet()
        request = MagicMock()
        request.ctx.user = SimpleNamespace(is_superuser=False)
        with pytest.raises(Forbidden):
            await vs.check_permissions(request)

        request.ctx.user = SimpleNamespace(is_superuser=True)
        await vs.check_permissions(request)

    @pytest.mark.asyncio
    async def test_perform_create_sets_user_id(self):
        vs = EventViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(id=9)
        sch = EventSchema.model_validate(
            {
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_remote": "api",
            }
        )
        with patch.object(Event, "create", new_callable=AsyncMock) as create_mock:
            create_mock.return_value = MagicMock()
            await vs.perform_create(sch)
        kwargs = create_mock.await_args.kwargs
        assert kwargs["action"] == "user.update"
        assert kwargs["obj_id"] == 7
        assert kwargs["user_id"] == 9
        assert "organizer_id" not in kwargs
