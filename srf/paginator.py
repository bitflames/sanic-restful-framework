from functools import lru_cache
from math import ceil
from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter
from sanic.exceptions import BadRequest
from sanic.request import Request
from tortoise.exceptions import ValidationError
from tortoise.queryset import QuerySet

T = TypeVar("T")


@lru_cache
def _list_type_adapter(schema: type[BaseModel]) -> TypeAdapter:
    """Compile list[schema] validation once per schema class (process-local cache)."""
    return TypeAdapter(list[schema])


def serialize_page(schema: type[BaseModel], rows: list[Any]) -> list[dict[str, Any]]:
    """
    Serialize ORM rows through a Reader/Writer schema for list responses.

    Uses a cached TypeAdapter so schema structure is not re-built per row.
    Row data is still validated on every call; only the adapter is reused.
    """
    if not rows:
        return []
    adapter = _list_type_adapter(schema)
    validated = adapter.validate_python(list(rows), from_attributes=True)
    dumped = adapter.dump_python(validated, by_alias=True, mode="json")
    return list(dumped)


class PaginationResult(BaseModel):
    count: int
    next: bool
    previous: bool
    results: list[Any]


class BasePagination:
    """
    Base class for pagination styles (DRF-style).

    Custom pagination must subclass this and implement the methods that raise
    NotImplementedError. Inheritance is the supported extension path.
    """

    @classmethod
    def from_queryset(cls, queryset: QuerySet[T], request: Request) -> "BasePagination":
        raise NotImplementedError("from_queryset() must be implemented.")

    async def paginate(self, sch_model: type[BaseModel] | None = None) -> PaginationResult:
        raise NotImplementedError("paginate() must be implemented.")

    async def to_dict(self, sch_model: type[BaseModel] | None = None) -> dict[str, Any]:
        result = await self.paginate(sch_model=sch_model)
        return result.model_dump(by_alias=True)

    def num_pages(self, total_count: int) -> int:
        raise NotImplementedError("num_pages() must be implemented.")

    def serialize_list(self, sch_model: type[BaseModel], rows: list[Any]) -> list[dict[str, Any]]:
        """Convert ORM rows to JSON-ready dicts; override for custom list serialization."""
        return serialize_page(sch_model, rows)


class PageNumberPagination(BasePagination):
    """
    A simple page number based style that supports page numbers as query parameters. For example:

    /api/users/?page=1
    /api/users/?page=2&page_size=100

    Invalid or missing parameters fall back to ``page=1`` / ``page_size=10``.

    Attributes:
        MAX_PAGE_SIZE: Upper bound accepted for the ``page_size`` query parameter.
        PAGE_QUERY_PARAM: Name of the query parameter carrying the page number.
        PAGE_SIZE_QUERY_PARAM: Name of the query parameter carrying the page size.
        queryset: The Tortoise QuerySet being paginated.
        page: Current page number (1-based).
        page_size: Items per page.
    """

    MAX_PAGE_SIZE: int = 100
    PAGE_QUERY_PARAM: str = 'page'
    PAGE_SIZE_QUERY_PARAM: str = 'page_size'

    def __init__(
        self,
        queryset: QuerySet[T],
        page: int = 1,
        page_size: int = 10,
    ):
        """
        :param queryset: Tortoise ORM queryset
        :param page: 1-based page number; values below 1 are clamped.
        :param page_size: Items per page; clamped to 1..MAX_PAGE_SIZE.
        """
        self.queryset = queryset
        self.page = max(int(page), 1)
        self.page_size = min(max(int(page_size), 1), max(self.MAX_PAGE_SIZE, 1))

    @staticmethod
    def _positive_int(value, default: int) -> int:
        """Parse an int and fall back to ``default`` when missing/invalid."""
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    @classmethod
    def from_queryset(cls, queryset: QuerySet[T], request: Request) -> "PageNumberPagination":
        """Parse page and page_size from request; fall back to defaults when invalid."""
        page = cls._positive_int(request.args.get(cls.PAGE_QUERY_PARAM, 1), 1)
        page_size = min(
            cls._positive_int(request.args.get(cls.PAGE_SIZE_QUERY_PARAM, 10), 10),
            max(cls.MAX_PAGE_SIZE, 1),
        )
        return cls(queryset=queryset, page=page, page_size=page_size)

    async def paginate(self, sch_model: type[BaseModel] | None = None) -> PaginationResult:
        offset = (self.page - 1) * self.page_size
        try:
            total_count = await self.queryset.count()
            items = await self.queryset.offset(offset).limit(self.page_size)
        except (ValidationError, ValueError) as e:
            raise BadRequest(message=str(e))
        if sch_model is not None:
            items = self.serialize_list(sch_model, list(items))
        else:
            raise ValueError("sch_model is required for paginate() to serialize results")
        total_pages = ceil(total_count / self.page_size) if total_count > 0 else 1
        return PaginationResult(
            results=items,
            previous=self.page > 1,
            next=self.page < total_pages,
            count=total_count,
        )

    async def to_dict(self, sch_model: type[BaseModel] | None = None) -> dict[str, Any]:
        result = await self.paginate(sch_model=sch_model)
        return result.model_dump(by_alias=True)

    def num_pages(self, total_count: int) -> int:
        """Return the total number of pages (empty results still have one page)."""

        total_count = total_count or 0
        return max(ceil(total_count / self.page_size), 1)
