# API Reference: Views

The view layer is the core of request handling in SRF. `GenericAPIView` handles action dispatch, schema validation, permissions, filtering, and pagination, while several CRUD mixins combine into ready-to-use ViewSets. For mechanism details and complete examples, see [ViewSet](../usage/core/viewsets.md) and [Actions and Decorators](../usage/core/viewset-actions.md).

```python
from srf.views import BaseViewSet, GenericAPIView, ReadOnlyModelViewSet, action
```

## Action dispatch

`as_view(actions)` maps HTTP methods to view methods. Usually `SanicRouter.register()` builds the mapping automatically; you only need to pass it yourself when calling `app.add_route()` manually:

```python
from sanic import Sanic

from srf.views import BaseViewSet

app = Sanic("demo")


class BookViewSet(BaseViewSet):
    queryset = Book.all()  # Tortoise QuerySet
    schema = BookSchema  # Pydantic model


app.add_route(
    BookViewSet.as_view({"get": "list", "post": "create"}),
    "/books",
)
```

The keys of `actions` are lowercase HTTP methods and the values are the method names to call. Methods not present in the mapping are not registered as routes; if the corresponding method cannot be resolved at runtime, `405 Method Not Allowed` is raised.

!!! warning "PUT and PATCH"
    Currently both `put` and `patch` map to `update`, and `update` validates the request body against the full schema. The semantic distinction between the two (full update / partial update) has not been implemented yet.

## View base classes

`GenericAPIView` is the common base class for all views; the other three composite classes simply pre-assemble the CRUD mixins.

::: srf.views.base.GenericAPIView
    options:
      heading_level: 4
      members:
        - __init__
        - get_schema
        - get_queryset
        - filter_queryset
        - get_object
        - normalize_pk
        - check_permissions
        - check_object_permissions
        - get_current_user
        - as_view
      show_source: false
      inherited_members: false

Differences between the three composite classes:

| Class | Provided actions |
| --- | --- |
| `BaseViewSet` | `create` / `list` / `retrieve` / `update` / `destroy` |
| `ReadOnlyModelViewSet` | `list` / `retrieve` |
| `CreateAndReadOnlyModelViewSet` | `create` / `list` / `retrieve` |

::: srf.views.base.BaseViewSet
    options:
      heading_level: 4
      members: false
      show_source: false
      inherited_members: false

::: srf.views.base.ReadOnlyModelViewSet
    options:
      heading_level: 4
      members: false
      show_source: false
      inherited_members: false

::: srf.views.base.CreateAndReadOnlyModelViewSet
    options:
      heading_level: 4
      members: false
      show_source: false
      inherited_members: false

## CRUD mixins

Each mixin provides a single action; inherit from them directly when you need finer-grained composition.

::: srf.views.base.CreateModelMixin
    options:
      heading_level: 4
      members:
        - create
        - perform_create
      show_source: false
      inherited_members: false

Behavior of `create`:

- Returns `400` when the request body is not JSON.
- Validates input with `schema` using `strict=True`, then calls `perform_create()`.
- Serializes output with the same schema and returns `201`.
- Database unique constraint violations (`IntegrityError`) are converted to `409 TargetObjectAlreadyExist`.

::: srf.views.base.RetrieveModelMixin
    options:
      heading_level: 4
      members:
        - retrieve
      show_source: false
      inherited_members: false

When looking up an object, the primary key type is normalized first, then object-level permission checks run; if the object does not exist, `404` is returned.

::: srf.views.base.UpdateModelMixin
    options:
      heading_level: 4
      members:
        - update
        - perform_update
      show_source: false
      inherited_members: false

`perform_update()` only writes fields explicitly provided in the request (`exclude_unset=True`) and skips primary key fields.

::: srf.views.base.DestroyModelMixin
    options:
      heading_level: 4
      members:
        - destroy
        - perform_destroy
      show_source: false
      inherited_members: false

Returns `204 No Content` after a successful delete.

::: srf.views.base.ListModelMixin
    options:
      heading_level: 4
      members:
        - list
      show_source: false
      inherited_members: false

The execution order of `list` is: `get_queryset()` → `filter_queryset()` → `pagination_class.from_queryset()` → `paginate()`. See [Pagination](pagination.md) for the response structure.

::: srf.views.base.ModelMixin
    options:
      heading_level: 4
      members: false
      show_source: false
      inherited_members: false

## Action decorator

`action` declares a regular method in a ViewSet as a standalone endpoint; `SanicRouter` discovers and registers it automatically.

::: srf.views.decorators.action
    options:
      heading_level: 4
      show_source: false

`validate_request` is used to decorate functional views (for example, `register` and `verify_email` in `srf.auth`). Request validation for ViewSets is handled uniformly by `as_view()`, so there is no need to stack this decorator on top.

::: srf.views.decorators.validate_request
    options:
      heading_level: 4
      show_source: false

## Export list

The following names are available from `from srf.views import ...`:

```python
from srf.views import (
    BaseViewSet,
    CreateAndReadOnlyModelViewSet,
    CreateModelMixin,
    DestroyModelMixin,
    GenericAPIView,
    ListModelMixin,
    ModelMixin,
    ReadOnlyModelViewSet,
    RetrieveModelMixin,
    UpdateModelMixin,
    action,
)
```

`validate_request` is not in the export list and must be imported from `srf.views.decorators`.
