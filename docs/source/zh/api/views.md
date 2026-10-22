# API 参考：Views

视图层是 SRF 的请求处理核心。`GenericAPIView` 负责动作分发、Schema 校验、权限、过滤与分页，几个 CRUD Mixin 组合成可直接使用的 ViewSet。机制说明与完整示例见 [ViewSet](../usage/core/viewsets.md) 与 [动作与装饰器](../usage/core/viewset-actions.md)。

```python
from srf.views import BaseViewSet, GenericAPIView, ReadOnlyModelViewSet, action
```

## 动作分发

`as_view(actions)` 把 HTTP 方法映射到视图方法。通常由 `SanicRouter.register()` 自动构建映射；手动调用 `app.add_route()` 时才需要自己传入：

```python
from sanic import Sanic

from srf.views import BaseViewSet

app = Sanic("demo")


class BookViewSet(BaseViewSet):
    queryset = Book.all()  # Tortoise QuerySet
    schema = BookSchema  # Pydantic 模型


app.add_route(
    BookViewSet.as_view({"get": "list", "post": "create"}),
    "/books",
)
```

`actions` 的键是小写 HTTP 方法，值是要调用的方法名。未在映射中出现的方法不会注册到路由；运行期取不到对应方法时抛出 `405 Method Not Allowed`。

!!! warning "PUT 与 PATCH"
    当前 `put` 和 `patch` 都映射到 `update`，且 `update` 按完整 Schema 校验请求体。两者语义上的区分（完整更新 / 部分更新）尚未实现。

## 视图基类

`GenericAPIView` 是所有视图的公共基类；另外三个组合类只是把 CRUD Mixin 预先拼好。

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

三个组合类的差异：

| 类 | 提供的动作 |
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

## CRUD Mixins

每个 Mixin 只提供一个动作，需要更细粒度的组合时可以直接继承。

::: srf.views.base.CreateModelMixin
    options:
      heading_level: 4
      members:
        - create
        - perform_create
      show_source: false
      inherited_members: false

`create` 的行为：

- 请求体不是 JSON 时返回 `400`。
- 使用 `schema` 以 `strict=True` 校验输入，随后调用 `perform_create()`。
- 输出使用同一个 Schema 序列化，返回 `201`。
- 数据库唯一约束冲突（`IntegrityError`）转换为 `409 TargetObjectAlreadyExist`。

::: srf.views.base.RetrieveModelMixin
    options:
      heading_level: 4
      members:
        - retrieve
      show_source: false
      inherited_members: false

查询对象时先做主键类型归一化，再执行对象级权限检查；对象不存在返回 `404`。

::: srf.views.base.UpdateModelMixin
    options:
      heading_level: 4
      members:
        - update
        - perform_update
      show_source: false
      inherited_members: false

`perform_update()` 只写入请求中显式提供的字段（`exclude_unset=True`），并跳过主键字段。

::: srf.views.base.DestroyModelMixin
    options:
      heading_level: 4
      members:
        - destroy
        - perform_destroy
      show_source: false
      inherited_members: false

删除成功后返回 `204 No Content`。

::: srf.views.base.ListModelMixin
    options:
      heading_level: 4
      members:
        - list
      show_source: false
      inherited_members: false

`list` 的执行顺序是：`get_queryset()` → `filter_queryset()` → `pagination_class.from_queryset()` → `paginate()`。响应结构见 [分页](pagination.md)。

::: srf.views.base.ModelMixin
    options:
      heading_level: 4
      members: false
      show_source: false
      inherited_members: false

## 动作装饰器

`action` 把 ViewSet 中的普通方法声明为一个独立接口，`SanicRouter` 会自动发现并注册。

::: srf.views.decorators.action
    options:
      heading_level: 4
      show_source: false

`validate_request` 用于装饰函数式视图（例如 `srf.auth` 中的 `register`、`verify_email`）。ViewSet 的请求校验由 `as_view()` 统一处理，不需要再叠加这个装饰器。

::: srf.views.decorators.validate_request
    options:
      heading_level: 4
      show_source: false

## 导出清单

`from srf.views import ...` 可用以下名字：

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

`validate_request` 不在导出清单中，需从 `srf.views.decorators` 导入。
