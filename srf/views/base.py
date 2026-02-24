import asyncio
from typing import Dict, Iterable, Type, cast

from pydantic import BaseModel, Field, ValidationError
from sanic import Request
from sanic.exceptions import Forbidden, HTTPException, NotFound
from sanic.log import error_logger
from sanic.response import HTTPResponse, JSONResponse
from sanic.views import HTTPMethodView
from tortoise import exceptions
from tortoise.models import Model as TorModel
from tortoise.queryset import QuerySet as QuerySetType

from srf.config import srfconfig
from srf.filters.filter import BaseFilter
from srf.paginator import PaginationHandler
from srf.permission.permission import BasePermission
from srf.views.http_status import HTTPStatus


class CreateModelMixin:
    async def create(self, request: Request, *args, **kwargs) -> HTTPResponse:
        """Create an orm model instance."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)
        # validate input schema
        sch_model_in: BaseModel = self._get_schema(request).model_validate(request.json)
        # create orm model instance
        orm_model: TorModel = await self.perform_create(sch_model_in, request)
        # validate output schema
        sch_model_out: BaseModel = self._get_schema(request, is_safe=True).model_validate(orm_model, from_attributes=True)
        # return response
        return JSONResponse(
            sch_model_out.model_dump(by_alias=True),
            status=HTTPStatus.HTTP_201_CREATED,
        )

    async def perform_create(self, sch_model: BaseModel, *args, **kwargs) -> TorModel:
        """
        sch_model: instance of BaseModel
        """
        try:
            return await self.queryset.model.create(**sch_model.model_dump(exclude_unset=True))
        except exceptions.IntegrityError:
            raise HTTPException(status_code=HTTPStatus.HTTP_409_CONFLICT, detail="data conflict")


class RetrieveModelMixin:
    async def retrieve(self, request: Request, pk) -> JSONResponse:
        """Get an orm model instance."""
        orm_model: TorModel = await self.get_object(request, pk)
        schema_out: BaseModel = self._get_schema(request).model_validate(orm_model)
        return JSONResponse(schema_out.model_dump(by_alias=True))


class UpdateModelMixin:
    async def update(self, request: Request, pk: int) -> JSONResponse:
        """Update an orm model instance."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)

        data: Dict = request.json
        sch_model_in: BaseModel = self._get_schema(request).model_validate(data, strict=True, by_alias=True)
        orm_model: TorModel = await self.get_object(request, pk)
        for key, val in sch_model_in.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"]).items():
            # The detailed parameters of model_dump here need to be customized in pydantic model: sch_model_in
            if hasattr(orm_model, key):
                setattr(orm_model, key, val)
        await orm_model.save()
        sch_model_out: BaseModel = self._get_schema(request, is_safe=True).model_validate(orm_model, from_attributes=True)
        return JSONResponse(sch_model_out.model_dump(by_alias=True))


class DestroyModelMixin:
    async def destroy(self, request: Request, pk: int) -> HTTPResponse:
        """Delete an orm model instance."""
        orm_model = await self.get_object(request, pk)
        await orm_model.delete()
        return HTTPResponse(status=HTTPStatus.HTTP_204_NO_CONTENT)


class ListModelMixin:
    async def list(self, request: Request, *args, **kwargs) -> JSONResponse:
        """Get a list orm model instance."""
        sch_model: Type[BaseModel] = self._get_schema(request)
        queryset: QuerySetType = self.queryset
        if hasattr(self, "filter_class"):
            for filter_class in self.filter_class:
                filter_class = cast(BaseFilter, filter_class)
                queryset = filter_class(self).filter_queryset(request, queryset)
        paginator = PaginationHandler.from_queryset(queryset, request)
        result = await paginator.paginate(sch_model=sch_model)
        return JSONResponse(result.model_dump(by_alias=True))


class ModelMixin(
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
):
    pass


class BaseViewSet(HTTPMethodView, ModelMixin):
    permission_classes: Iterable[Type[BasePermission]]
    search_fields: list = Field(default_factory=list)

    def __init__(self, *args, **kwargs):
        self.filter_class = srfconfig.DEFAULT_FILTERS
        super().__init__(*args, **kwargs)

    def get_schema(self, request: Request, *args, is_safe=False, **kwargs):
        """
        Default implementation that returns the schema attribute
        """
        return getattr(self, "schema", None)

    def _get_schema(self, request: Request, *args, is_safe=False, **kwargs):
        """
        get pydantic model,
        params:
            is_safe, default to be False
        """
        return self.get_schema(request, *args, is_safe=is_safe, **kwargs)

    def get_current_user(self, request: Request):
        """Retrieve the currently logged-in user"""
        if hasattr(request.ctx, "user"):
            return request.ctx.user

        # If ctx.user does not exist, attempt to retrieve user information from the JWT payload
        if hasattr(request, "auth"):
            return request.auth

        return None

    def check_object_permissions(self, request: Request, obj):
        """
        Check object-level permissions
        Subclasses should override this method to implement specific permission checking logic
        """
        pass

    async def check_permissions(self, request: Request):
        """
        Check common-level permissions
        Subclasses should override this method to implement specific permission checking logic.
        Supports both sync and async has_permission().
        """
        for permission_class in getattr(self, "permission_classes", []):
            perm = permission_class()
            result = perm.has_permission(request)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")

    async def get_object(self, request: Request, id: int):
        """Get an orm model instance."""
        self.request = request
        instance: TorModel = await self.queryset.get_or_none(id=id)
        if instance is None:
            raise NotFound(message=f"Object with id={id} not found")

        result = self.check_object_permissions(request, instance)
        if asyncio.iscoroutine(result):
            await result
        return instance

    @property
    def queryset(self) -> QuerySetType:
        raise NotImplementedError

    @classmethod
    def as_view(cls, actions=None):
        """
        Construct a view function for registering with Sanic routers.
        custom actions: {'get': 'list', 'post': 'create', ...}
        """
        default_actions = {
            "get": "list",
            "post": "create",
            "put": "update",
            "patch": "update",
            "delete": "destroy",
        }

        actions = actions or {}
        action_map = {**default_actions, **actions}

        async def view(request, *args, **kwargs):
            self = cls()
            self.request = request
            method = request.method.lower()
            handler_name = action_map.get(method)
            if handler_name is None:
                return JSONResponse(
                    {"error": f"Method {request.method} not allowed"},
                    status=HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED,
                )
            handler = getattr(self, handler_name, None)

            if not handler:
                return JSONResponse(
                    {"error": f"Method {request.method} not allowed"},
                    status=HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED,
                )

            await self.check_permissions(request)

            try:
                return await handler(request, *args, **kwargs)
            except exceptions.DoesNotExist:
                error_logger.exception("DoesNotExist")
                return HTTPResponse(
                    "Please ensure that the resource you are accessing exists and that you have permission to access it",
                    status=HTTPStatus.HTTP_404_NOT_FOUND,
                )
            except ValidationError as e:
                error_logger.exception("ValidationError")
                return JSONResponse(
                    {"detail": str(e)},
                    status=HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            except HTTPException as e:
                error_logger.exception("HTTPException")
                return JSONResponse(
                    {"detail": getattr(e, "detail", "Error")},
                    status=e.status_code,
                )

        return view
