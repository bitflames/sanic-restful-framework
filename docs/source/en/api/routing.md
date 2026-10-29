# API Reference: Routing

The routing layer exposes a single public class, `SanicRouter`: it splits a ViewSet into collection routes, detail routes, and `@action` routes, then registers them on a `Sanic` application or `Blueprint`. See [Routing](../usage/core/routing.md) for usage.

```python
from srf.route import SanicRouter

router = SanicRouter(app, prefix="/api/v1")
router.register("books", BookViewSet)
```

::: srf.route.SanicRouter
options:
heading_level: 3
members: - **init** - register
show_source: false
inherited_members: false

## Registration result

`register(path, view_cls, name=None)` only registers routes for view methods that **actually exist** on the class:

| URL                               | HTTP             | View method                    | Route name          |
| --------------------------------- | ---------------- | ------------------------------ | ------------------- |
| `{prefix}/{path}`                 | `GET`            | `list`                         | `{name}-list`       |
| `{prefix}/{path}`                 | `HEAD`           | `list`                         | `{name}-list`       |
| `{prefix}/{path}`                 | `POST`           | `create`                       | `{name}-list`       |
| `{prefix}/{path}/<pk>`            | `GET`            | `retrieve`                     | `{name}-detail`     |
| `{prefix}/{path}/<pk>`            | `HEAD`           | `retrieve`                     | `{name}-detail`     |
| `{prefix}/{path}/<pk>`            | `PUT`            | `update`                       | `{name}-detail`     |
| `{prefix}/{path}/<pk>`            | `PATCH`          | `update`                       | `{name}-detail`     |
| `{prefix}/{path}/<pk>`            | `DELETE`         | `destroy`                      | `{name}-detail`     |
| `{prefix}/{path}/{url_path}`      | `action.methods` | Method decorated with `action` | `{name}-{url_name}` |
| `{prefix}/{path}/<pk>/{url_path}` | `action.methods` | Action with `detail=True`      | `{name}-{url_name}` |

- `name` defaults to `path`.
- If a ViewSet does not define `list`, no collection route is created; the same applies to detail routes.
- `GET` routes also support `HEAD`, reusing the same `list` / `retrieve` method.
- A read-only ViewSet generates only the routes for `list` / `retrieve` (including `HEAD`).

## Discovery rules for `@action`

`register()` uses `inspect.getmembers()` to scan the view class (including inherited methods); any method with an `extra_info` attribute is registered as a separate route. `extra_info` is written by [`action`](views.md#srf.views.decorators.action):

| Parameter  | Default              | Purpose                                          |
| ---------- | -------------------- | ------------------------------------------------ |
| `detail`   | `False`              | When `True`, the URL includes `<pk>`             |
| `methods`  | `("GET",)`           | HTTP methods accepted by the action              |
| `url_path` | `"/{function name}"` | Appended after the collection/detail path        |
| `url_name` | Function name        | Used to build the route name `{name}-{url_name}` |

!!! tip "Prefix normalization"
`prefix="api/v1/"` is normalized to `/api/v1`, and leading/trailing `/` in `path` are removed. Therefore `SanicRouter(app, prefix="api/v1").register("/books/", BookViewSet)` produces the collection URL `/api/v1/books`.

!!! warning "Duplicate route names"
`SanicRouter` does not check for route name conflicts. If two ViewSets use the same `name`, or two actions use the same `url_name`, you must ensure uniqueness yourself; otherwise Sanic reports a duplicate route name.
