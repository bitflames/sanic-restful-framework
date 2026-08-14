from typing import ClassVar

from pydantic import BaseModel
from sanic import Request
from sanic.constants import SAFE_HTTP_METHODS
from tortoise.queryset import QuerySet

from srf.event import models, schema
from srf.permission.permission import IsRoleAdminUser
from srf.views.base import CreateAndReadOnlyModelViewSet


class EventViewSet(CreateAndReadOnlyModelViewSet):
    """Admin-only audit event API (create / list / retrieve)."""

    permission_classes = (IsRoleAdminUser,)
    search_fields: ClassVar[list[str]] = [
        "action",
        "obj_name",
        "req_remote",
        "id",
    ]
    filter_fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "action": "action",
        "obj_id": "obj_id",
        "obj_name": "obj_name",
        "req_remote": "req_remote",
        "user_id": "user_id",
    }

    @property
    def queryset(self) -> QuerySet:
        return models.Event.all()

    def get_schema(self, request: Request, *args, is_safe=False, **kwargs):
        if request.method.lower() in SAFE_HTTP_METHODS or is_safe is True:
            return schema.EventSchemaReader
        return schema.EventSchemaWriter

    async def perform_create(self, sch_model: BaseModel) -> models.Event:
        data = sch_model.model_dump(exclude_unset=True, exclude_none=True)
        request = getattr(self, "request", None)
        user = getattr(getattr(request, "ctx", None), "user", None) if request is not None else None
        if user is not None:
            data["user_id"] = user.id
        return await models.Event.create(**data)
