# API 参考：Routing

路由层只有一个公开类 `SanicRouter`：把 ViewSet 拆成集合路由、详情路由和 `@action` 路由，再注册到 `Sanic` 应用或 `Blueprint`。使用说明见 [路由](../usage/core/routing.md)。

```python
from srf.route import SanicRouter

router = SanicRouter(app, prefix="/api/v1")
router.register("books", BookViewSet)
```

::: srf.route.SanicRouter
    options:
      heading_level: 3
      members:
        - __init__
        - register
      show_source: false
      inherited_members: false

## 注册结果

`register(path, view_cls, name=None)` 只会为类中__实际存在__的视图方法注册路由：

| URL | HTTP | 视图方法 | 路由名 |
| --- | --- | --- | --- |
| `{prefix}/{path}` | `GET` | `list` | `{name}-list` |
| `{prefix}/{path}` | `POST` | `create` | `{name}-list` |
| `{prefix}/{path}/<pk>` | `GET` | `retrieve` | `{name}-detail` |
| `{prefix}/{path}/<pk>` | `PUT` | `update` | `{name}-detail` |
| `{prefix}/{path}/<pk>` | `PATCH` | `update` | `{name}-detail` |
| `{prefix}/{path}/<pk>` | `DELETE` | `destroy` | `{name}-detail` |
| `{prefix}/{path}/{url_path}` | `action.methods` | `action` 装饰的方法 | `{name}-{url_name}` |
| `{prefix}/{path}/<pk>/{url_path}` | `action.methods` | `detail=True` 的 action | `{name}-{url_name}` |

- `name` 默认等于 `path`。
- 若 ViewSet 没有定义 `list`，就不会创建集合路由；详情路由同理。
- 只读 ViewSet 只会生成 `list` / `retrieve` 对应的路由。

## `@action` 的发现规则

`register()` 用 `inspect.getmembers()` 扫描视图类（包括继承来的方法），凡是带有 `extra_info` 属性的方法都会注册为独立路由。`extra_info` 由 [`action`](views.md#srf.views.decorators.action) 写入：

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `detail` | `False` | 为 `True` 时 URL 中带 `<pk>` |
| `methods` | `("GET",)` | 该 action 接受的 HTTP 方法 |
| `url_path` | `"/{函数名}"` | 追加在集合/详情路径之后 |
| `url_name` | 函数名 | 用于生成路由名 `{name}-{url_name}` |

!!! tip "前缀规范化"
    `prefix="api/v1/"` 会被规范化为 `/api/v1`，`path` 两端的 `/` 会被去掉。因此 `SanicRouter(app, prefix="api/v1").register("/books/", BookViewSet)` 得到的集合地址是 `/api/v1/books`。

!!! warning "重名路由"
    `SanicRouter` 不检查路由名冲突。两个 ViewSet 使用同一个 `name`，或两个 action 使用同一个 `url_name` 时，需要自行保证唯一，否则 Sanic 会报重复路由名。
