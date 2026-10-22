import asyncio
from collections.abc import Iterable
from typing import ClassVar

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sanic import Request
from sanic.exceptions import Forbidden, MethodNotAllowed, NotFound
from sanic.response import HTTPResponse, JSONResponse
from sanic.views import HTTPMethodView
from tortoise.exceptions import IntegrityError, ValidationError as TortoiseValidationError
from tortoise.models import Model as TorModel
from tortoise.queryset import QuerySet as QuerySetType

from srf.config import settings
from srf.exceptions import PydanticValidationException, TargetObjectAlreadyExist
from srf.filters import BaseFilter
from srf.paginator import BasePagination
from srf.permission.permission import BasePermission
from srf.views.http_status import HTTPStatus


class CreateModelMixin:
    async def create(self, request: Request, *args, **kwargs) -> HTTPResponse:
        """Create an orm model instance."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)
        # validate input schema
        sch_model_cls: type[BaseModel] = self.get_schema()
        sch_model_in: BaseModel = sch_model_cls.model_validate(request.json, strict=True)
        # create orm model instance
        orm_model: TorModel = await self.perform_create(sch_model_in)
        # validate output schema
        sch_model_out: BaseModel = sch_model_cls.model_validate(orm_model, from_attributes=True)
        # return response
        return JSONResponse(sch_model_out.model_dump(mode="json"), status=HTTPStatus.HTTP_201_CREATED)

    async def perform_create(self, sch_model: BaseModel) -> TorModel:
        """
        sch_model: instance of BaseModel
        """
        try:
            return await self.get_queryset().model.create(**sch_model.model_dump(exclude_unset=True, exclude_none=True))
        except IntegrityError:
            raise TargetObjectAlreadyExist(message="data conflict")


class RetrieveModelMixin:
    async def retrieve(self, request: Request, pk, *args, **kwargs) -> JSONResponse:
        """Get an orm model instance."""
        orm_model: TorModel = await self.get_object(pk)
        schema_out: BaseModel = self.get_schema().model_validate(orm_model, from_attributes=True)
        return JSONResponse(schema_out.model_dump(mode="json"))


class UpdateModelMixin:
    async def update(self, request: Request, pk, *args, **kwargs) -> JSONResponse:
        """Update an orm model instance."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)

        sch_model_cls: type[BaseModel] = self.get_schema()  # not distinguishing between full or partial updates
        sch_model_in: BaseModel = sch_model_cls.model_validate(request.json, strict=True)

        orm_model: TorModel = await self.get_object(pk)

        orm_model = await self.perform_update(sch_model_in, orm_model)
        sch_model_out: BaseModel = sch_model_cls.model_validate(orm_model, from_attributes=True)
        return JSONResponse(sch_model_out.model_dump(mode="json"))

    async def perform_update(self, sch_model: BaseModel, orm_model: TorModel) -> TorModel:
        """
        sch_model: instance of BaseModel
        orm_model: instance of TorModel
        """
        data = sch_model.model_dump(exclude_unset=True)
        data.pop(orm_model._meta.pk_attr, None)
        orm_model.update_from_dict(data)
        await orm_model.save()
        return orm_model


class DestroyModelMixin:
    async def destroy(self, request: Request, pk, *args, **kwargs) -> HTTPResponse:
        """Delete an orm model instance."""
        orm_model: TorModel = await self.get_object(pk)
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
        sch_model: type[BaseModel] = self.get_schema()
        queryset: QuerySetType = self.filter_queryset(self.get_queryset())
        paginator: BasePagination = self.pagination_class.from_queryset(queryset, request)
        result = await paginator.paginate(sch_model=sch_model)
        return JSONResponse(result.model_dump(mode="json"))


class GenericAPIView(HTTPMethodView):
    """
    Base class for all SRF views: schema validation, permissions, filtering and pagination.

    Attributes:
        schema: Pydantic model class used to validate request data and serialize responses.
            Set it on the subclass or override ``get_schema()``.
        queryset: Tortoise QuerySet the view operates on. Set it on the subclass or
            override ``get_queryset()``.
        filter_class: Filter classes applied in ``list()``. Defaults to
            ``settings.DEFAULT_FILTERS`` when not declared on the class.
        permission_classes: Permission classes checked before the handler runs. Defaults
            to ``settings.DEFAULT_PERMISSION_CLASSES``.
        pagination_class: Pagination class used by ``list()``. Defaults to
            ``settings.PAGINATION_CLASS``.
        search_fields: Fields matched by ``SearchFilter`` via ``?search=`` (icontains).
            Accepts a list of ORM field names or a dict of ``{alias: orm_field}``.
        filter_fields: Fields allowed for exact filtering by ``QueryParamFilter`` /
            ``JsonLogicFilter``. Accepts a list or a dict of ``{param: orm_field}``.
        ordering_fields: Fields allowed for ordering via ``?ordering=``. Use ``-name``
            for descending order.
    """

    permission_classes: Iterable[type[BasePermission]]
    search_fields: ClassVar[list[str] | dict[str, str]] = []
    filter_fields: ClassVar[list[str] | dict[str, str]] = []
    ordering_fields: ClassVar[list[str] | dict[str, str]] = []
    pagination_class: type[BasePagination]
    queryset: QuerySetType | None = None
    filter_class: ClassVar[list[type[BaseFilter]]]
    schema: ClassVar[type[BaseModel] | None] = None

    def __init__(self, *args, **kwargs):
        cls = type(self)
        self.filter_class = getattr(cls, "filter_class", settings.DEFAULT_FILTERS)
        self.permission_classes = getattr(cls, "permission_classes", settings.DEFAULT_PERMISSION_CLASSES)
        self.pagination_class = getattr(cls, "pagination_class", settings.PAGINATION_CLASS)
        super().__init__(*args, **kwargs)

    def get_schema(self) -> type[BaseModel]:
        """
        Return the Pydantic model class for this view action.

        Override this method (or set class attribute ``schema``) like DRF's ``get_serializer_class`` /
        ``serializer_class``. Uses ``self.action`` and ``self.request`` set by ``as_view`` — do not pass
        ``request`` as a parameter.
        """
        schema_cls: BaseModel = getattr(type(self), "schema", None)
        assert schema_cls is not None, (
            f"'{self.__class__.__name__}' should either include a `schema` attribute, " "or override the `get_schema` method."
        )
        return schema_cls

    def get_current_user(self, request: Request):
        """Retrieve the currently logged-in user"""
        if hasattr(request.ctx, "user"):
            return request.ctx.user

        # If ctx.user does not exist, attempt to retrieve user information from the JWT payload
        if hasattr(request, "auth"):
            return request.auth

        return None

    async def check_object_permissions(self, obj: TorModel):
        """
        Check object-level permissions.
        Permission classes are used as callables on the class (no instantiation).
        Supports both sync and async has_object_permission().
        """
        for permission_class in self.permission_classes:
            result = permission_class.has_object_permission(self.request, self, obj)
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

    def normalize_pk(self, pk, model: type[TorModel] | None = None):
        """
        Coerce the route parameter pk to the model's pk type before it reaches a query.

        Sanic always hands ``<pk>`` over as str. Querying with the raw str only  works by implicit conversion,
        and a non-integer pk against an int field raises ValueError deep inside Tortoise (a 500).
        Convert up front: a pk that cannot be parsed can never match a row, so respond 404.
        """
        if model is None:
            model = self.get_queryset().model
        try:
            return model._meta.pk.to_db_value(pk, None)
        except (ValueError, TypeError, TortoiseValidationError) as e:
            raise NotFound(message=f"Object with pk={pk} not found") from e

    async def get_object(self, pk):
        """Get an orm model instance."""
        queryset = self.get_queryset()
        pk = self.normalize_pk(pk, queryset.model)
        instance: TorModel | None = await queryset.get_or_none(pk=pk)
        if instance is None:
            raise NotFound(message=f"Object with pk={pk} not found")

        await self.check_object_permissions(instance)

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
            for filter_cls in self.filter_class:
                queryset = filter_cls(self).filter_queryset(self.request, queryset)
        return queryset

    @classmethod
    def as_view(cls, actions: dict[str, str] | None = None):
        """
        Construct a view function for registering with Sanic.

        ``actions`` maps an HTTP method to a view method, for example `{"get": "list"}`` or ``{"get": "retrieve"}``.
        Callers pass this map explicitly: ``SanicRouter.register`` builds it,
        and ``add_route`` callers pass it themselves. Sanic's default route method is GET; that does not choose ``list`` versus ``retrieve``.
        """
        if not actions:
            raise TypeError("The actions argument must be provided when calling as_view() on a ViewSet. " "For example as_view({'get': 'list'}).")

        async def view(request, *args, **kwargs):
            self = cls()  # a new instance for each request
            self.request = request
            method = request.method.lower()

            if (handler_name := actions.get(method)) is None or (handler := getattr(self, handler_name, None)) is None:
                raise MethodNotAllowed(message=f"Method {request.method} not allowed", method=request.method)

            self.action = handler_name
            await self.check_permissions(request)

            try:
                return await handler(request, *args, **kwargs)
            except (PydanticValidationError, TortoiseValidationError) as e:
                raise PydanticValidationException(message=str(e))

        return view


class ModelMixin(
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
):
    """Convenience bundle of all five CRUD mixins (create, retrieve, update, destroy, list)."""


class BaseViewSet(GenericAPIView, ModelMixin):
    """
    Full-featured ViewSet: all five CRUD actions plus schema validation,
    permissions, filtering and pagination from ``GenericAPIView``.
    """


class ReadOnlyModelViewSet(GenericAPIView, ListModelMixin, RetrieveModelMixin):
    """Read-only ViewSet exposing only ``list`` and ``retrieve``."""


class CreateAndReadOnlyModelViewSet(GenericAPIView, CreateModelMixin, ListModelMixin, RetrieveModelMixin):
    """ViewSet exposing ``create``, ``list`` and ``retrieve`` — no update or delete."""
