"""Unit tests for srf.paginator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel, ConfigDict, Field

from srf.paginator import (
    BasePagination,
    PageNumberPagination,
    PaginationParams,
    PaginationResult,
    _list_type_adapter,
    serialize_page,
)


class _Row:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class _Reader(BaseModel):
    id: int
    name: str = Field(alias="username")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TestSerializePage:
    def test_empty_rows(self):
        assert serialize_page(_Reader, []) == []

    def test_serializes_orm_like_rows_with_aliases(self):
        rows = [_Row(1, "alice"), _Row(2, "bob")]
        out = serialize_page(_Reader, rows)
        assert out == [{"id": 1, "username": "alice"}, {"id": 2, "username": "bob"}]

    def test_type_adapter_cached_per_schema_class(self):
        _list_type_adapter.cache_clear()
        a1 = _list_type_adapter(_Reader)
        a2 = _list_type_adapter(_Reader)
        assert a1 is a2


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 10

    def test_validate_positive_rejects_zero_page(self):
        with pytest.raises(ValueError):
            PaginationParams(page=0)

    def test_validate_positive_rejects_negative_page_size(self):
        with pytest.raises(ValueError):
            PaginationParams(page_size=-1)


class TestPaginationResult:
    def test_model_dump(self):
        r = PaginationResult(count=100, next=True, previous=False, results=[{"id": 1}])
        d = r.model_dump(by_alias=True)
        assert d["count"] == 100
        assert d["next"] is True
        assert d["previous"] is False
        assert len(d["results"]) == 1


class TestPageNumberPagination:
    def test_from_queryset_defaults(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: d
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page == 1
        assert paginator.page_size == 10

    def test_from_queryset_parses_page_and_size(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page": 2, "page_size": 20}.get(k, d)
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page == 2
        assert paginator.page_size == 20

    def test_from_queryset_clamps_page_size_to_max(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page_size": 1000}.get(k, 1)
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page_size == 100  # MAX_PAGE_SIZE

    def test_from_queryset_invalid_falls_back_to_defaults(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: "not_a_number"
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page == 1
        assert paginator.page_size == 10

    def test_from_queryset_invalid_page_keeps_valid_page_size(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page": "bad", "page_size": 25}.get(k, d)
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page == 1
        assert paginator.page_size == 25

    def test_from_queryset_missing_page_size_defaults_to_ten(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page": 3}.get(k, d)
        qs = MagicMock()
        paginator = PageNumberPagination.from_queryset(qs, request)
        assert paginator.page == 3
        assert paginator.page_size == 10

    @pytest.mark.asyncio
    async def test_paginate_requires_sch_model(self):
        paginator = PageNumberPagination(queryset=MagicMock(), page=1, page_size=10)
        paginator.queryset.count = AsyncMock(return_value=0)
        paginator.queryset.offset.return_value.limit = AsyncMock(return_value=[])
        with pytest.raises(ValueError, match="sch_model is required"):
            await paginator.paginate(sch_model=None)

    @pytest.mark.asyncio
    async def test_paginate_returns_result(self):
        paginator = PageNumberPagination(queryset=MagicMock(), page=1, page_size=10)
        paginator.queryset.count = AsyncMock(return_value=5)
        paginator.queryset.offset.return_value.limit = AsyncMock(
            return_value=[_Row(1, "alice"), _Row(2, "bob")]
        )
        result = await paginator.paginate(sch_model=_Reader)
        assert result.count == 5
        assert result.next is False
        assert result.previous is False
        assert len(result.results) == 2
        assert result.results[0]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_to_dict_returns_dict(self):
        paginator = PageNumberPagination(queryset=MagicMock(), page=2, page_size=2)
        paginator.queryset.count = AsyncMock(return_value=5)
        paginator.queryset.offset.return_value.limit = AsyncMock(return_value=[_Row(3, "carol")])
        result = await paginator.to_dict(sch_model=_Reader)
        assert result["count"] == 5
        assert result["previous"] is True
        assert result["next"] is True
        assert result["results"][0]["username"] == "carol"

    def test_num_pages_zero_count(self):
        paginator = PageNumberPagination(queryset=MagicMock(), page=1, page_size=10)
        assert paginator.num_pages(total_count=0) == 0

    def test_num_pages_positive(self):
        paginator = PageNumberPagination(queryset=MagicMock(), page=1, page_size=10)
        assert paginator.num_pages(total_count=25) == 3


class TestBasePagination:
    def test_from_queryset_not_implemented(self):
        with pytest.raises(NotImplementedError):
            BasePagination.from_queryset(MagicMock(), MagicMock())

    @pytest.mark.asyncio
    async def test_paginate_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await BasePagination().paginate()

    def test_num_pages_not_implemented(self):
        with pytest.raises(NotImplementedError):
            BasePagination().num_pages(10)

    def test_page_number_is_subclass(self):
        assert issubclass(PageNumberPagination, BasePagination)
