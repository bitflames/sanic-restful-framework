import functools
import json
import operator
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union, cast
from urllib.parse import unquote

from sanic import Request
from sanic.log import logger
from sanic.views import HTTPMethodView
from tortoise.expressions import Q
from tortoise.queryset import QuerySet


def visualize_q(q: Q, indent=0):
    prefix = " " * indent
    if isinstance(q.children, list):
        op = q.connector  # AND / OR
        for child in q.children:
            if isinstance(child, Q):
                visualize_q(child, indent + 4)
            else:
                k, v = child
                logger.info(f"{' ' * (indent + 4)}{k} = {v}")
    else:
        logger.info(f"{prefix}{q}")


class BaseFilter(ABC):
    def __init__(self, view_class: HTTPMethodView):
        self.view_class = view_class

    @property
    @abstractmethod
    def _filter_params(self) -> Any:
        """Subclasses must implement;
        return type is filter-specific. For internal use only."""
        pass

    def get_search_terms(self, request: Request):
        """Extract search keywords from requests"""
        return request.args.getlist(self._filter_params, [])

    def filter_queryset(self, request: Request, queryset: QuerySet) -> QuerySet:
        """Actual filtering logic (to be implemented according to ORM)"""
        raise NotImplementedError("The filter_queryset method must be implemented")


class SearchFilter(BaseFilter):
    """Search filter applicable to common ORM (example uses TortoiseORM syntax)"""

    def __init__(self, view_class):
        super().__init__(view_class)

    @property
    def _filter_params(self) -> str:
        return "search"

    def get_search_terms(self, request: Request):
        search_param = request.args.get(self._filter_params, None)
        if search_param:
            return search_param.split()
        return []

    def filter_queryset(self, request: Request, queryset: QuerySet) -> QuerySet:
        search_terms = self.get_search_terms(request)
        if not search_terms or not self.view_class.search_fields:
            return queryset

        query = None  # Tortoise: empty Q() | Q(...) yields empty; build term_query first then combine
        for term in search_terms:
            term_query = None
            for field in self.view_class.search_fields:
                condition = Q(**{f"{field}__icontains": term})
                if term_query is None:
                    term_query = condition
                else:
                    term_query |= condition
            if term_query is not None:
                if query is None:
                    query = term_query
                else:
                    query &= term_query
        if query is None:
            return queryset
        return queryset.filter(query)


class JsonLogicFilter(BaseFilter):
    OPERATOR_MAP = {
        "==": lambda k, v: Q(**{k: v}),
        "!=": lambda k, v: ~Q(**{k: v}),
        "!": lambda k, v: ~Q(**{k: v}),
        ">": lambda k, v: Q(**{f"{k}__gt": v}),
        ">=": lambda k, v: Q(**{f"{k}__gte": v}),
        "<": lambda k, v: Q(**{f"{k}__lt": v}),
        "<=": lambda k, v: Q(**{f"{k}__lte": v}),
        "in": lambda k, v: Q(**{f"{k}__in": v}),
        "not in": lambda k, v: ~Q(**{f"{k}__in": v}),
        "like": lambda k, v: Q(**{f"{k}__icontains": v}),
    }

    def __init__(self, view_class):
        super().__init__(view_class)
        self.filter_fields = cast(
            Dict,
            getattr(view_class, "filter_fields", {}),
        )

    @property
    def _filter_params(self) -> str:
        return "filter"

    def filter_queryset(self, request, queryset: QuerySet):
        raw_logic = request.args.get(self._filter_params)
        if not raw_logic:
            return queryset

        if isinstance(raw_logic, str):
            try:
                raw_logic = json.loads(raw_logic)
            except Exception:
                return queryset

        q_expr = self._parse_logic_recursively(raw_logic)
        if q_expr:
            return queryset.filter(q_expr)
        return queryset

    def _parse_logic_recursively(self, logic: Dict[str, Any]) -> Union[Q, None]:
        """Recursively parse JSON Logic into a Tortoise ORM Q expression."""
        if not isinstance(logic, dict):
            return None

        for op, args in logic.items():
            if op in ("and", "or"):
                sub_qs = [self._parse_logic_recursively(sub) for sub in args]
                sub_qs = [q for q in sub_qs if q is not None]
                if not sub_qs:
                    return None
                # return (sub_qs[0] if op == "and" else sub_qs[0]).__class__.reduce(op.upper(), sub_qs)
                if op == "and":
                    return functools.reduce(operator.and_, sub_qs)
                elif op == "or":
                    return functools.reduce(operator.or_, sub_qs)

            elif op == "not":
                inner_q = self._parse_logic_recursively(args)
                return ~inner_q if inner_q else None

            elif op in self.OPERATOR_MAP:
                if isinstance(args, list) and len(args) == 2:
                    left, right = args
                    key = left.get("var") if isinstance(left, dict) and "var" in left else None
                    value = right
                    if key:
                        if self.filter_fields and self.filter_fields.get(key):
                            return self.OPERATOR_MAP[op](self.filter_fields.get(key), value)
                        return self.OPERATOR_MAP[op](key, value)
        return None


class QueryParamFilter(BaseFilter):
    def __init__(self, view_class=None):
        super().__init__(view_class)

    @property
    def _filter_params(self) -> Dict:
        if hasattr(self.view_class, "filter_fields"):
            return cast(Dict, self.view_class.filter_fields)
        return {}

    def filter_queryset(self, request, queryset: QuerySet):
        filters = {}
        _filter_keys = self._filter_params.keys()
        if self._filter_params:
            for key in request.args.keys():
                if key in ("ordering",):
                    continue
                if self._filter_params and not any(key.startswith(field) for field in _filter_keys):
                    continue
                if key not in self._filter_params:
                    continue
                values = request.args.getlist(key)
                mapped = self._filter_params[key]
                if values and len(values) > 1:
                    filters[f"{mapped}__in"] = values
                elif values:
                    filters[mapped] = values[0]
            return queryset.filter(**filters)
        return queryset


class OrderingFactory(BaseFilter):
    def __init__(self, view_class=None):
        super().__init__(view_class)

    @property
    def _filter_params(self) -> Dict:
        if hasattr(self.view_class, "ordering_fields"):
            ordering_fields = cast(List | Dict, self.view_class.ordering_fields)
            # If it's a list, convert to dict for easier lookup
            if isinstance(ordering_fields, list):
                return {field: field for field in ordering_fields}
            return ordering_fields
        return {}

    def filter_queryset(self, request, queryset: QuerySet):
        sort_value = request.args.get("sort")
        if not sort_value:
            return queryset

        allowed_fields = self._filter_params
        order_by_fields = []

        # Parse multiple sorting fields, and support '-' to indicate reverse order
        for raw_field in unquote(sort_value).split(","):
            raw_field = raw_field.strip()
            if not raw_field:
                continue

            desc = raw_field.startswith("-")
            field_name = raw_field[1:] if desc else raw_field

            # Verify that it is in the allowed field
            if field_name in allowed_fields:
                mapped_field = allowed_fields[field_name]
                if desc:
                    order_by_fields.append(f"-{mapped_field}")
                else:
                    order_by_fields.append(mapped_field)

        if order_by_fields:
            return queryset.order_by(*order_by_fields)
        return queryset
