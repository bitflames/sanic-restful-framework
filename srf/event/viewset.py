from typing import ClassVar

from pydantic import BaseModel
from sanic.exceptions import Forbidden
from tortoise.queryset import QuerySet

from srf.event import models, schema
from srf.permission.permission import SuperuserOnly
from srf.views.base import CreateAndReadOnlyModelViewSet


class EventViewSet(CreateAndReadOnlyModelViewSet):
    """superuser-only audit event API (create / list / retrieve)."""

    permission_classes = (SuperuserOnly,)
    search_fields: ClassVar[list[str]] = ["id", "action", "obj_name", "req_remote"]
    filter_fields: ClassVar[list[str]] = search_fields + ["obj_id", "user_id"]
    ordering_fields: ClassVar[list[str]] = filter_fields + ["create_time"]

    schema = schema.EventSchema

    @property
    def queryset(self) -> QuerySet:
        if not self.request.ctx.user.is_superuser:
            raise Forbidden(message="Forbidden")
        return models.Event.all()

    async def perform_create(self, sch_model: BaseModel) -> models.Event:
        data = sch_model.model_dump(exclude_unset=True, exclude_none=True)
        request = getattr(self, "request", None)
        user = getattr(getattr(request, "ctx", None), "user", None) if request is not None else None
        if user is not None:
            data["user_id"] = user.id
        return await models.Event.create(**data)
