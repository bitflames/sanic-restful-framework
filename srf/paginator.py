from math import ceil
from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel, field_validator
from sanic.request import Request
from tortoise.queryset import QuerySet

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10

    @field_validator("page", "page_size")
    def validate_positive(cls, v):
        if v < 1:
            raise ValueError("page and page_size must be integers greater than 0")
        return v


class PaginationResult(BaseModel):
    count: int
    next: bool
    previous: bool
    results: list[Any]


class PaginationHandler(Generic[T]):
    """
    A simple page number based style that supports page numbers as query parameters. For example:

    /api/users/?page=1
    /api/users/?page=2&page_size=100
    """

    page_size = 10
    max_page_size = 100
    page_query_param = 'page'
    page_size_query_param = 'page_size'

    def __init__(
        self,
        queryset: QuerySet[T],
        page: int = 1,
        page_size: int = page_size,
        max_page_size: int = max_page_size,
    ):
        """
        :param queryset: Tortoise ORM queryset
        :param page:
        :param page_size:
        :param max_page_size:
        """
        self.queryset = queryset
        self.page = page
        self.page_size = page_size
        self.max_page_size = max_page_size

    @classmethod
    def from_queryset(cls, queryset: QuerySet[T], request: Request) -> "PaginationHandler":
        """Parse page and page_size from request; ensure they are positive and within limits."""
        try:
            page = int(request.args.get(cls.page_query_param, 1))
            page_size = int(request.args.get(cls.page_size_query_param, cls.page_size))
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = cls.page_size
            if page_size > cls.max_page_size:
                page_size = cls.max_page_size
        except (TypeError, ValueError):
            page = 1
            page_size = cls.page_size
        return cls(queryset=queryset, page=page, page_size=page_size)

    async def paginate(self, sch_model: BaseModel = None) -> PaginationResult:
        offset = (self.page - 1) * self.page_size
        total_count = await self.queryset.count()
        items = await self.queryset.offset(offset).limit(self.page_size)
        if sch_model is not None:
            items = [sch_model.model_validate(instance).model_dump(by_alias=True) for instance in items]
        else:
            raise ValueError("sch_model is required for paginate() to serialize results")
        total_pages = ceil(total_count / self.page_size) if total_count > 0 else 1
        return PaginationResult(
            results=items,
            previous=self.page > 1,
            next=self.page < total_pages,
            count=total_count,
        )

    async def to_dict(self, sch_model: BaseModel = None) -> Dict[str, Any]:
        result = await self.paginate(sch_model=sch_model)
        return result.model_dump(by_alias=True)

    def num_pages(self, total_count: int = None):
        """Return the total number of pages."""

        total_count = total_count or 0
        if total_count == 0:
            return 0
        return ceil(total_count / self.page_size)
