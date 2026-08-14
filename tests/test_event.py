"""Unit tests for srf.event."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sanic.exceptions import Forbidden

from srf.event.models import Event
from srf.event.schema import EventSchemaReader, EventSchemaWriter
from srf.event.viewset import EventViewSet
from srf.permission.permission import IsRoleAdminUser


class TestEventSchemas:
    def test_writer_accepts_audit_payload(self):
        sch = EventSchemaWriter.model_validate(
            {
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_source": "api",
                "req_data": {"username": "alice"},
                "res_data": {"ok": True},
            }
        )
        assert sch.action == "user.update"
        assert sch.obj_id == 7
        assert sch.req_data == {"username": "alice"}

    def test_writer_rejects_oversized_action(self):
        with pytest.raises(ValidationError):
            EventSchemaWriter.model_validate({"action": "x" * 129})

    def test_reader_builds_url(self):
        sch = EventSchemaReader.model_validate(
            {
                "id": 3,
                "user_id": 9,
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_source": "api",
                "create_time": datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc),
            }
        )
        assert sch.url == "/events/3"
        assert sch.user_id == 9


class TestEventViewSet:
    def test_get_schema_safe_vs_write(self):
        vs = EventViewSet()
        request = MagicMock()
        request.method = "GET"
        assert vs.get_schema(request) is EventSchemaReader
        request.method = "POST"
        assert vs.get_schema(request) is EventSchemaWriter
        assert vs.get_schema(request, is_safe=True) is EventSchemaReader

    def test_queryset_uses_event_model(self):
        with patch.object(Event, "all", return_value="qs") as all_mock:
            assert EventViewSet().queryset == "qs"
            all_mock.assert_called_once()

    def test_permission_is_admin(self):
        assert EventViewSet.permission_classes == (IsRoleAdminUser,)

    def test_search_and_filter_fields_match_model(self):
        assert "action" in EventViewSet.search_fields
        assert "obj_name" in EventViewSet.search_fields
        assert EventViewSet.filter_fields["user_id"] == "user_id"
        assert EventViewSet.filter_fields["obj_id"] == "obj_id"

    @pytest.mark.asyncio
    async def test_check_permissions_requires_admin_role(self):
        vs = EventViewSet()
        request = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.role = MagicMock()
        request.ctx.user.role.name = "user"
        with pytest.raises(Forbidden):
            await vs.check_permissions(request)

        request.ctx.user.role.name = "admin"
        await vs.check_permissions(request)

    @pytest.mark.asyncio
    async def test_perform_create_sets_user_id(self):
        vs = EventViewSet()
        vs.request = MagicMock()
        vs.request.ctx.user = MagicMock(id=9)
        sch = EventSchemaWriter.model_validate(
            {
                "action": "user.update",
                "obj_id": 7,
                "obj_name": "User",
                "req_source": "api",
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
