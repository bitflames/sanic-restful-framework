"""Unit tests for srf.filters.filter."""

import json
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from sanic.exceptions import BadRequest

from srf.filters.filter import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)


class ViewWithSearchFields:
    search_fields: ClassVar[list[str] | dict[str, str]] = ["name", "email"]


class ViewWithSearchDict:
    search_fields: ClassVar[list[str] | dict[str, str]] = {"display_name": "name"}


class ViewWithFilterFields:
    filter_fields: ClassVar[list[str] | dict[str, str]] = {"id": "id", "name": "name", "is_active": "is_active"}


class ViewWithFilterList:
    filter_fields: ClassVar[list[str] | dict[str, str]] = ["id", "name", "is_active"]


class ViewWithFilterAlias:
    filter_fields: ClassVar[list[str] | dict[str, str]] = {"display_name": "name"}


class ViewWithoutFilterFields:
    pass


class ViewWithOrderingFields:
    ordering_fields: ClassVar[list[str] | dict[str, str]] = ["name", "created_date"]


class ViewWithOrderingDict:
    ordering_fields: ClassVar[list[str] | dict[str, str]] = {"created": "created_date", "name": "name"}


class TestSearchFilter:
    def test_reads_search_query_param(self):
        view = ViewWithSearchFields()
        f = SearchFilter(view)
        request = MagicMock()
        request.args.get.side_effect = lambda key, default=None: "foo" if key == "search" else default
        assert f.get_search_terms(request) == ["foo"]

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

    def test_filter_queryset_accepts_dict_mapping(self):
        f = SearchFilter(ViewWithSearchDict())
        request = MagicMock()
        request.args.get.return_value = "alice"
        qs = MagicMock()
        with patch("srf.filters.filter.Q", return_value=object()) as q_mock:
            f.filter_queryset(request, qs)
        q_mock.assert_called_once_with(name__icontains="alice")
        qs.filter.assert_called_once()


class TestJsonLogicFilter:
    def test_reads_filter_query_param(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.side_effect = lambda key, default=None: "{}" if key == "filter" else default
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs
        qs.filter.assert_not_called()

    def test_filter_fields_set_in_init(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        assert f.filter_fields == view.filter_fields

    def test_filter_fields_list_maps_names_to_themselves(self):
        f = JsonLogicFilter(ViewWithFilterList())
        request = MagicMock()
        request.args.get.return_value = json.dumps({"==": [{"var": "name"}, "alice"]})
        qs = MagicMock()

        f.filter_queryset(request, qs)

        qs.filter.assert_called_once()

    def test_filter_queryset_no_param_returns_unchanged(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = None
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs

    def test_filter_queryset_invalid_json_raises_bad_request(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = "not-valid-json{{{"
        qs = MagicMock()
        with pytest.raises(BadRequest, match="Invalid filter JSON"):
            f.filter_queryset(request, qs)

    def test_filter_queryset_without_filter_fields_skips_filtering(self):
        view = ViewWithoutFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = json.dumps({"==": [{"var": "name"}, "alice"]})
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs
        qs.filter.assert_not_called()

    def test_filter_queryset_unknown_field_skips_filtering(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = json.dumps({"==": [{"var": "password_hash"}, "xxx"]})
        qs = MagicMock()
        result = f.filter_queryset(request, qs)
        assert result is qs
        qs.filter.assert_not_called()

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

    @pytest.mark.parametrize(
        "payload",
        [
            {"and": 1},
            {"and": []},
            {"or": "not-a-list"},
            {"not": 1},
            {"==": [{"var": "name"}]},
            {"==": "not-a-list"},
            {"==": [{"var": 1}, "alice"]},
            {"unknown": []},
            {"and": [{"==": [{"var": "name"}, "a"]}], "or": []},
            [],
            "not-an-object",
        ],
    )
    def test_invalid_structure_raises_bad_request(self, payload):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = json.dumps(payload)

        with pytest.raises(BadRequest):
            f.filter_queryset(request, MagicMock())

    def test_error_messages_point_to_docs(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        request = MagicMock()
        request.args.get.return_value = json.dumps({"and": 1})

        with pytest.raises(BadRequest) as exc_info:
            f.filter_queryset(request, MagicMock())
        assert JsonLogicFilter.DOCS_URL in str(exc_info.value)

    def test_nesting_depth_is_limited_to_three_levels(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        qs = MagicMock()

        expr = {"==": [{"var": "name"}, "alice"]}
        for _ in range(2):
            expr = {"and": [expr]}
        request = MagicMock()
        request.args.get.return_value = json.dumps(expr)
        f.filter_queryset(request, qs)
        qs.filter.assert_called_once()

        too_deep = {"and": [expr]}
        request.args.get.return_value = json.dumps(too_deep)
        with pytest.raises(BadRequest, match="too complex"):
            f.filter_queryset(request, MagicMock())

    def test_node_count_is_limited(self):
        view = ViewWithFilterFields()
        f = JsonLogicFilter(view)
        expr = {"and": [{"==": [{"var": "name"}, f"v{i}"]} for i in range(JsonLogicFilter.MAX_NODES)]}
        request = MagicMock()
        request.args.get.return_value = json.dumps(expr)

        with pytest.raises(BadRequest, match="too complex"):
            f.filter_queryset(request, MagicMock())


class TestQueryParamFilter:
    def test_filter_fields_list_maps_names_to_themselves(self):
        f = QueryParamFilter(ViewWithFilterList())
        request = MagicMock()
        request.args = MagicMock()
        request.args.__iter__ = MagicMock(return_value=iter(["name"]))
        request.args.getlist.return_value = ["alice"]
        qs = MagicMock()

        f.filter_queryset(request, qs)

        qs.filter.assert_called_once_with(name="alice")

    def test_filter_fields_dict_maps_query_alias(self):
        f = QueryParamFilter(ViewWithFilterAlias())
        request = MagicMock()
        request.args = MagicMock()
        request.args.__iter__ = MagicMock(return_value=iter(["display_name"]))
        request.args.getlist.return_value = ["alice"]
        qs = MagicMock()

        f.filter_queryset(request, qs)

        qs.filter.assert_called_once_with(name="alice")

    def test_filter_queryset_empty_args_returns_filtered_with_empty_kwargs(self):
        view = ViewWithFilterFields()
        f = QueryParamFilter(view)
        request = MagicMock()
        request.args = MagicMock()
        request.args.__iter__ = MagicMock(return_value=iter([]))
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
        request.args = MagicMock()
        request.args.__iter__ = MagicMock(return_value=iter(["name"]))
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
        # Real Sanic returns "" here (missing param, bare `?ordering`, and `?ordering=` all yield ""),
        # so the mock must mirror that instead of returning None.
        request.args.get.return_value = ""
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
        assert result is ordered_qs
        qs.order_by.assert_called_once_with("-name")

    def test_filter_queryset_maps_dict_alias(self):
        f = OrderingFactory(ViewWithOrderingDict())
        request = MagicMock()
        request.args.get.return_value = "-created"
        qs = MagicMock()

        f.filter_queryset(request, qs)

        qs.order_by.assert_called_once_with("-created_date")
