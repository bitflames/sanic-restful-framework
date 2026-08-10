from typing import ClassVar

from srf.auth.models import User
from srf.auth.schema import UserSchemaReader
from srf.permission.permission import IsRoleAdminUser
from srf.views.base import CreateModelMixin, GenericAPIView


class EventViewSet(GenericAPIView, CreateModelMixin):
    model = User
    schema = UserSchemaReader
    permission_classes = (IsRoleAdminUser,)
    search_fields: ClassVar[list[str]] = [
        "name",
        "is_active",
        "id",
    ]  # The is_active field is inconsistent with the database field, resulting in invalidation
    filter_fields = {'id': "id", "name": "name", "is_active": "is_active"}


def temp_event(request: Request):
    data = request.json
    return JSONResponse(data)
