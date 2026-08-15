import asyncio
from collections.abc import Iterable
from typing import ClassVar, cast

from pydantic import BaseModel, ValidationError
from sanic import Request
from sanic.exceptions import Forbidden, HTTPException, NotFound
from sanic.response import HTTPResponse, JSONResponse
from sanic.views import HTTPMethodView
from tortoise import exceptions
from tortoise.models import Model as TorModel
from tortoise.queryset import QuerySet as QuerySetType

from srf.config import settings
from srf.exceptions import TargetObjectAlreadyExist
from srf.filters.filter import BaseFilter
from srf.paginator import PageNumberPagination
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
        orm_model: TorModel = await self.perform_create(sch_model_in)
        # validate output schema
        sch_model_out: BaseModel = self._get_schema(request, is_safe=True).model_validate(orm_model, from_attributes=True)
        # return response
        return JSONResponse(
            sch_model_out.model_dump(mode="json", by_alias=True),
            status=HTTPStatus.HTTP_201_CREATED,
        )

    async def perform_create(self, sch_model: BaseModel) -> TorModel:
        """
        sch_model: instance of BaseModel
        """
        try:
            return await self.get_queryset().model.create(**sch_model.model_dump(exclude_unset=True))
        except exceptions.IntegrityError:
            raise TargetObjectAlreadyExist(message="data conflict")


class RetrieveModelMixin:
    async def retrieve(self, request: Request, pk, *args, **kwargs) -> JSONResponse:
        """Get an orm model instance."""
        orm_model: TorModel = await self.get_object(request, pk)
        schema_out: BaseModel = self._get_schema(request).model_validate(orm_model)
        return JSONResponse(schema_out.model_dump(mode="json", by_alias=True))


class UpdateModelMixin:
    async def update(self, request: Request, pk: int, *args, **kwargs) -> JSONResponse:
        """Update an orm model instance."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)

        partial: bool = kwargs.get("partial", False)
        sch_model_in: BaseModel = self._get_schema(request, partial=partial).model_validate(request.json, strict=True, by_alias=True)
        orm_model: TorModel = await self.get_object(request, pk)
        orm_model = await self.perform_update(sch_model_in, orm_model)
        sch_model_out: BaseModel = self._get_schema(request, is_safe=True).model_validate(orm_model, from_attributes=True)
        return JSONResponse(sch_model_out.model_dump(mode="json", by_alias=True))

    async def perform_update(self, sch_model: BaseModel, orm_model: TorModel) -> TorModel:
        """
        sch_model: instance of BaseModel
        orm_model: instance of TorModel
        """
        data = sch_model.model_dump(exclude_unset=True, exclude_none=True)
        data.pop(orm_model._meta.pk_attr, None)
        orm_model.update_from_dict(data)
        await orm_model.save()
        return orm_model

    async def partial_update(self, request: Request, pk: int, *args, **kwargs):
        """
        Partial update an orm model instance.
        """
        kwargs["partial"] = True
        return await self.update(request, pk, *args, **kwargs)


class DestroyModelMixin:
    async def destroy(self, request: Request, pk: int, *args, **kwargs) -> HTTPResponse:
        """Delete an orm model instance."""
        orm_model: TorModel = await self.get_object(request, pk)
        await self.perform_destroy(orm_model)
        return HTTPResponse(status=HTTPStatus.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, orm_model: TorModel) -> None:
        """
        orm_model: instance of TorModel
        """
        await orm_model.delete()


class ListModelMixin:
    async def list(self, request: Request, *args, **kwargs) -> JSONResponse:
        """Get a list orm model instance."""
        sch_model: type[BaseModel] = self._get_schema(request)
        queryset: QuerySetType = self.filter_queryset(self.get_queryset())
        paginator = PageNumberPagination.from_queryset(queryset, request)  # TODO，config
        result = await paginator.paginate(sch_model=sch_model)
        return JSONResponse(result.model_dump(mode="json", by_alias=True))


class GenericAPIView(HTTPMethodView):
    permission_classes: Iterable[type[BasePermission]]
    search_fields: ClassVar[list[str]] = []
    queryset = None

    def __init__(self, *args, **kwargs):
        cls = type(self)
        self.filter_class = getattr(cls, "filter_class", settings.DEFAULT_FILTERS)
        self.permission_classes = getattr(cls, "permission_classes", settings.DEFAULT_PERMISSION_CLASSES)
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

    async def check_object_permissions(self, request: Request, obj: TorModel):
        """
        Check object-level permissions.
        Permission classes are used as callables on the class (no instantiation).
        Supports both sync and async has_object_permission().
        """
        for permission_class in self.permission_classes:
            result = permission_class.has_object_permission(request, self, obj)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")

    async def check_permissions(self, request: Request):
        """
        Check view-level permissions.
        Permission classes are used as callables on the class (no instantiation).
        Supports both sync and async has_permission().
        """
        for permission_class in self.permission_classes:
            result = permission_class.has_permission(request, self)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")

    async def get_object(self, request: Request, id: int):
        """Get an orm model instance."""
        instance: TorModel = await self.get_queryset().get_or_none(id=id)
        if instance is None:
            raise NotFound(message=f"Object with id={id} not found")

        await self.check_object_permissions(request, instance)

        return instance

    def get_queryset(self) -> QuerySetType:
        """
        Prioritize using get_queryset, followed by queryset
        """
        assert self.queryset is not None, (
            f"'{self.__class__.__name__}' should either include a `queryset` attribute, " "or override the `get_queryset()` method."
        )
        queryset = self.queryset
        if isinstance(queryset, QuerySetType):
            # Ensure queryset is re-evaluated on each request, tortoise
            queryset = queryset.all()
        return queryset

    def filter_queryset(self, queryset):
        """
        The filter class should be obtained first from view class or, if not, from settings
        """
        if hasattr(self, "filter_class"):
            for filter_class in self.filter_class:
                filter_class = cast(BaseFilter, filter_class)
                queryset = filter_class(self).filter_queryset(self.request, queryset)
        return queryset

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
            "patch": "partial_update",
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
                return HTTPResponse(
                    "Please ensure that the resource you are accessing exists and that you have permission to access it",
                    status=HTTPStatus.HTTP_404_NOT_FOUND,
                )
            except ValidationError as e:
                return JSONResponse(
                    {"detail": str(e)},
                    status=HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            except HTTPException as e:
                return JSONResponse(
                    {"detail": getattr(e, "message", "Error")},
                    status=e.status_code,
                )

        return view


class ModelMixin(
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
): ...


class BaseViewSet(GenericAPIView, ModelMixin): ...


class ReadOnlyModelViewSet(GenericAPIView, ListModelMixin, RetrieveModelMixin): ...


class CreateAndReadOnlyModelViewSet(GenericAPIView, CreateModelMixin, ListModelMixin, RetrieveModelMixin): ...
