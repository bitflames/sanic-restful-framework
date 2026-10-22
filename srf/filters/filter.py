import functools
import json
import operator
from abc import ABC
from collections.abc import Callable
from typing import Any, ClassVar

from sanic import Request
from sanic.exceptions import BadRequest
from sanic.log import logger
from tortoise.expressions import Q
from tortoise.queryset import QuerySet


def visualize_q(q: Q, indent=0):
    prefix = " " * indent
    if isinstance(q.children, list):
        for child in q.children:
            if isinstance(child, Q):
                visualize_q(child, indent + 4)
            else:
                k, v = child
                logger.info(f"{' ' * (indent + 4)}{k} = {v}")
    else:
        logger.info(f"{prefix}{q}")


class BaseFilter(ABC):
    """
    Base class for all filters.

    Subclasses must set ``cls_fields`` to the name of the view attribute holding the
    field configuration (e.g. ``"search_fields"``); missing it raises ``TypeError``
    at class-definition time.

    Attributes:
        cls_fields: Name of the view attribute that lists the allowed fields.
        view_class: The view instance this filter is bound to.
        filter_fields: Resolved field mapping. A list config becomes ``{field: field}``,
            a dict config is used as-is, anything else becomes ``{}``.
    """

    # Name of the attribute on the view that lists allowed fields.
    # Default None so a subclass missing it fails fast (TypeError) at class-definition time.
    cls_fields: str | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.cls_fields is None:
            raise TypeError(f"cls_fields must be set in {cls.__name__}.")

    def __init__(self, view_class):
        self.view_class = view_class
        raw = getattr(view_class, self.cls_fields, None)
        if isinstance(raw, list):
            self.filter_fields = {field: field for field in raw}
        elif isinstance(raw, dict):
            self.filter_fields = raw
        else:
            self.filter_fields = {}

    def filter_queryset(self, request: Request, queryset: QuerySet) -> QuerySet:
        """Actual filtering logic (to be implemented according to ORM)"""
        raise NotImplementedError("The filter_queryset method must be implemented")


class SearchFilter(BaseFilter):
    """
    Keyword filter applicable to common ORM (example uses TortoiseORM syntax).

    Reads the ``search`` query parameter, splits it on whitespace, and matches each
    term against every configured field with ``__icontains``: terms are AND-ed,
    fields are OR-ed.
    """

    cls_fields = "search_fields"

    def get_search_terms(self, request: Request):
        search_param = request.args.get("search", None)
        if search_param:
            return search_param.split()
        return []

    def filter_queryset(self, request: Request, queryset: QuerySet) -> QuerySet:
        search_terms = self.get_search_terms(request)
        if not search_terms or not self.filter_fields:
            return queryset

        query = None  # Tortoise: empty Q() | Q(...) yields empty; build term_query first then combine
        for term in search_terms:
            term_query = None
            for value in self.filter_fields.values():
                condition = Q(**{f"{value}__icontains": term})
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
    """
    Filter driven by a JSON expression in the ``filter`` query parameter.

    Supports operators ``==``, ``!=``, ``>``, ``>=``, ``<``, ``<=``, ``in``, ``not in``,
    ``like`` (icontains) and nested ``and`` / ``or`` / ``not``. Only fields listed in
    the view's ``filter_fields`` are usable; anything else is ignored.

    Attributes:
        OPERATOR_MAP: Mapping of JSON-logic operators to ``Q`` expression builders.
    """

    cls_fields = "filter_fields"
    OPERATOR_MAP: ClassVar[dict[str, Callable]] = {
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

    def filter_queryset(self, request, queryset: QuerySet):
        raw_logic = request.args.get("filter")
        if not raw_logic or not self.filter_fields:
            return queryset

        if isinstance(raw_logic, str):
            try:
                raw_logic = json.loads(raw_logic)
            except (json.JSONDecodeError, TypeError) as exc:
                raise BadRequest("Invalid filter JSON") from exc

        q_expr = self._parse_logic_recursively(raw_logic)
        if q_expr:
            return queryset.filter(q_expr)
        return queryset

    def _parse_logic_recursively(self, logic: dict[str, Any]) -> Q | None:
        """Recursively parse JSON Logic into a Tortoise ORM Q expression."""
        if not isinstance(logic, dict):
            return None

        for op, args in logic.items():
            if op in ("and", "or"):
                sub_qs = [self._parse_logic_recursively(sub) for sub in args]
                sub_qs = [q for q in sub_qs if q is not None]
                if not sub_qs:
                    return None
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
                    if key and self.filter_fields.get(key):
                        return self.OPERATOR_MAP[op](self.filter_fields[key], value)
                    return None
        return None


class QueryParamFilter(BaseFilter):
    """
    Exact-match filter based on query parameters.

    A query parameter is applied only when its name exactly matches a key of the view's
    ``filter_fields``. A repeated parameter (``?a=1&a=2``) becomes an ``__in`` lookup,
    a single value becomes an exact match.
    """

    cls_fields = "filter_fields"

    def filter_queryset(self, request, queryset: QuerySet):
        filters = {}
        _filter_keys = self.filter_fields.keys()
        if self.filter_fields:
            for key in request.args:
                if key not in self.filter_fields:
                    continue
                values = request.args.getlist(key)
                mapped = self.filter_fields[key]
                if values and len(values) > 1:
                    filters[f"{mapped}__in"] = values
                elif values:
                    filters[mapped] = values[0]
            return queryset.filter(**filters)
        return queryset


class OrderingFactory(BaseFilter):
    """
    Ordering filter driven by the ``ordering`` query parameter.

    Accepts a comma-separated list such as ``?ordering=name,-create_time``; fields not
    listed in the view's ``ordering_fields`` are silently ignored.
    """

    cls_fields = "ordering_fields"

    def filter_queryset(self, request, queryset: QuerySet):
        order_by_fields = []
        for raw in request.args.get("ordering", "").strip().split(","):
            if not raw:
                continue
            desc = raw.startswith("-")
            mapped = self.filter_fields.get(raw[1:] if desc else raw)
            if mapped:
                order_by_fields.append(f"-{mapped}" if desc else mapped)

        return queryset.order_by(*order_by_fields) if order_by_fields else queryset
