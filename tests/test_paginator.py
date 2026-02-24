"""Unit tests for srf.paginator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from srf.paginator import PaginationHandler, PaginationParams, PaginationResult


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


class TestPaginationHandler:
    def test_from_queryset_defaults(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: d
        qs = MagicMock()
        handler = PaginationHandler.from_queryset(qs, request)
        assert handler.page == 1
        assert handler.page_size == 10

    def test_from_queryset_parses_page_and_size(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page": 2, "page_size": 20}.get(k, d)
        qs = MagicMock()
        handler = PaginationHandler.from_queryset(qs, request)
        assert handler.page == 2
        assert handler.page_size == 20

    def test_from_queryset_clamps_page_size_to_max(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: {"page_size": 1000}.get(k, 1)
        qs = MagicMock()
        handler = PaginationHandler.from_queryset(qs, request)
        assert handler.page_size == 100  # max_page_size

    def test_from_queryset_invalid_falls_back_to_defaults(self):
        request = MagicMock()
        request.args.get.side_effect = lambda k, d=None: "not_a_number"
        qs = MagicMock()
        handler = PaginationHandler.from_queryset(qs, request)
        assert handler.page == 1
        assert handler.page_size == 10

    @pytest.mark.asyncio
    async def test_paginate_requires_sch_model(self):
        handler = PaginationHandler(queryset=MagicMock(), page=1, page_size=10)
        handler.queryset.count = AsyncMock(return_value=0)
        handler.queryset.offset.return_value.limit = AsyncMock(return_value=[])
        with pytest.raises(ValueError, match="sch_model is required"):
            await handler.paginate(sch_model=None)

    @pytest.mark.asyncio
    async def test_paginate_returns_result(self):
        handler = PaginationHandler(queryset=MagicMock(), page=1, page_size=10)
        handler.queryset.count = AsyncMock(return_value=5)
        handler.queryset.offset.return_value.limit = AsyncMock(return_value=[MagicMock(id=1), MagicMock(id=2)])
        schema = MagicMock()
        schema.model_validate.side_effect = lambda obj: MagicMock(model_dump=MagicMock(return_value={"id": getattr(obj, "id", None)}))
        result = await handler.paginate(sch_model=schema)
        assert result.count == 5
        assert result.next is False
        assert result.previous is False
        assert len(result.results) == 2

    def test_num_pages_zero_count(self):
        handler = PaginationHandler(queryset=MagicMock(), page=1, page_size=10)
        assert handler.num_pages(total_count=0) == 0

    def test_num_pages_positive(self):
        handler = PaginationHandler(queryset=MagicMock(), page=1, page_size=10)
        assert handler.num_pages(total_count=25) == 3
