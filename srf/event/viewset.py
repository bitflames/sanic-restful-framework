from sanic import Request
from sanic.response import JSONResponse

from srf.auth.models import User
from srf.auth.schema import UserSchemaReader
from srf.permission.permission import IsRoleAdminUser
from srf.views.base import BaseViewSet, CreateModelMixin


class EventViewSet(BaseViewSet, CreateModelMixin):
    model = User
    schema = UserSchemaReader
    permission_classes = (IsRoleAdminUser,)
    search_fields = [
        "name",
        "is_active",
        "id",
    ]  # The is_active field is inconsistent with the database field, resulting in invalidation
    filter_fields = {'id': "id", "name": "name", "is_active": "is_active"}


def temp_event(request: Request):
    data = request.json
    return JSONResponse(data)
