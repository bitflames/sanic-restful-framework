"""Unit tests for srf.filters.filter."""

import json
import pytest
from unittest.mock import MagicMock

from srf.filters.filter import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)


class ViewWithSearchFields:
    search_fields = ["name", "email"]


class ViewWithFilterFields:
    filter_fields = {"id": "id", "name": "name", "is_active": "is_active"}


class ViewWithOrderingFields:
    ordering_fields = ["name", "created_date"]


class ViewWithOrderingDict:
    ordering_fields = {"name": "name", "created_date": "created_date"}


class TestSearchFilter:
    def test__filter_params(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        assert f._filter_params == "search"

    def test_get_search_terms_empty(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        request = MagicMock()
        request.args.get.return_value = None
        assert f.get_search_terms(request) == []

    def test_get_search_terms_single(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        request = MagicMock()
        request.args.get.return_value = "foo"
        terms = f.get_search_terms(request)
        assert terms == ["foo"]

    def test_filter_queryset_no_terms_returns_unchanged(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        request = MagicMock()
        request.args.get.return_value = None
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs

    def test_filter_queryset_applies_filter(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        request = MagicMock()
        request.args.get.return_value = "test"
        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs
        result = f.filter_queryset(request, qs)
        assert result is filtered_qs
        qs.filter.assert_called_once()


class TestJsonLogicFilter:
    def test__filter_params_returns_filter(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        assert f._filter_params == "filter"

    def test_filter_fields_set_in_init(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        assert f.filter_fields == view.filter_fields

    def test_filter_queryset_no_param_returns_unchanged(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = None
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs

    def test_filter_queryset_invalid_json_returns_unchanged(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = "not-valid-json{{{"
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs

    def test_filter_queryset_valid_logic(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = json.dumps({"==": [{"var": "name"}, "alice"]})
        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs
        result = f.filter_queryset(request, qs)
        assert result is filtered_qs
        qs.filter.assert_called_once()


class TestQueryParamFilter:
    def test_filter_queryset_empty_args_returns_filtered_with_empty_kwargs(self):
        view = ViewWithFilterFields()
        f = QueryParamFilter(view)
        request = MagicMock()
        request.args.keys.return_value = []
        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs
        result = f.filter_queryset(request, qs)
        assert result is filtered_qs
        qs.filter.assert_called_once_with()

    def test_filter_queryset_applies_mapped_filter(self):
        view = ViewWithFilterFields()
        f = QueryParamFilter(view)
        request = MagicMock()
        request.args.keys.return_value = ["name"]
        request.args.getlist.return_value = ["alice"]
        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs
        result = f.filter_queryset(request, qs)
        assert result is filtered_qs
        qs.filter.assert_called_once_with(name="alice")


class TestOrderingFactory:
    def test_filter_queryset_no_sort_returns_unchanged(self):
        view = ViewWithOrderingFields()
        f = OrderingFactory(view)
        request = MagicMock()
        request.args.get.return_value = None
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs

    def test_filter_queryset_sort_single_field(self):
        view = ViewWithOrderingFields()
        f = OrderingFactory(view)
        request = MagicMock()
        request.args.get.return_value = "name"
        qs = MagicMock()
        ordered_qs = MagicMock()
        qs.order_by.return_value = ordered_qs
        result = f.filter_queryset(request, qs)
        assert result is ordered_qs
        qs.order_by.assert_called_once_with("name")

    def test_filter_queryset_sort_descending(self):
        view = ViewWithOrderingFields()
        f = OrderingFactory(view)
        request = MagicMock()
        request.args.get.return_value = "-name"
        qs = MagicMock()
        ordered_qs = MagicMock()
        qs.order_by.return_value = ordered_qs
        result = f.filter_queryset(request, qs)
        qs.order_by.assert_called_once_with("-name")
