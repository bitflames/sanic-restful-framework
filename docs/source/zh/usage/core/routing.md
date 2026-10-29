# 路由

SRF 的路由系统通过 `SanicRouter` 类自动为 ViewSet 生成 RESTful 路由。

## SanicRouter 基础

`SanicRouter` 是 SRF 的核心路由类，它负责：

- 将 ViewSet 注册为路由
- 自动生成标准的 RESTful 端点
- 发现并注册 `@action` 装饰的自定义操作
- 管理 URL 前缀和命名

### 基本用法

```python
from sanic import Sanic
from srf.route import SanicRouter
from viewsets import ProductViewSet

app = Sanic("ShopApp")
router = SanicRouter(app, prefix="api")

# 注册 ViewSet
router.register("products", ProductViewSet, name="products")
```

## 初始化参数

### `SanicRouter(instance, prefix="")`

```python
router = SanicRouter(app, prefix="api")
```

**参数说明**：

- `instance`: 必填的 Sanic `Sanic` 或 `Blueprint` 实例。传入 Sanic 实例时，路由直接注册到应用；传入 Blueprint 时，路由注册到该 Blueprint。
- `prefix`: URL 前缀，会添加到所有路由前面

## 注册 ViewSet

### register(path, view_cls, name=None)

```python
router.register(
    path="products",           # URL 路径
    view_cls=ProductViewSet,   # ViewSet 类
    name="products"            # 可选：路由名称
)
```

**参数说明**：

- `path`: 资源的 URL 路径（不包含前缀）
- `view_cls`: ViewSet 类
- `name`: 路由名称前缀，用于生成路由名称

## 自动生成的路由

当注册一个 ViewSet 时，`SanicRouter` 会自动生成以下路由：

### 标准 CRUD 路由

假设注册代码为：

```python
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet, name="products")
```

生成的路由：

| HTTP 方法 | URL 路径             | 操作             | ViewSet 方法 | 路由名称          |
| --------- | -------------------- | ---------------- | ------------ | ----------------- |
| GET       | `/api/products`      | 列表             | `list()`     | `products-list`   |
| HEAD      | `/api/products`      | 列表（无响应体） | `list()`     | `products-list`   |
| POST      | `/api/products`      | 创建             | `create()`   | `products-list`   |
| GET       | `/api/products/<pk>` | 详情             | `retrieve()` | `products-detail` |
| HEAD      | `/api/products/<pk>` | 详情（无响应体） | `retrieve()` | `products-detail` |
| PUT       | `/api/products/<pk>` | 完整更新         | `update()`   | `products-detail` |
| PATCH     | `/api/products/<pk>` | 部分更新         | `update()`   | `products-detail` |
| DELETE    | `/api/products/<pk>` | 删除             | `destroy()`  | `products-detail` |

### 自定义操作路由

对于使用 `@action` 装饰的方法：

**集合级操作** (`detail=False`)：

```python
@action(methods=["get"], detail=False, url_path="featured")
async def list_featured(self, request):
    pass
```

生成路由：

- URL: `/api/products/featured`
- 方法: GET
- 路由名称: `products-list_featured`（默认 `url_name` 为方法名）

**详情级操作** (`detail=True`)：

```python
@action(methods=["post"], detail=True, url_path="publish")
async def publish(self, request, pk):
    pass
```

生成路由：

- URL: `/api/products/<pk>/publish`
- 方法: POST
- 路由名称: `products-publish`（默认 `url_name` 为方法名）

## URL 前缀

URL 前缀用于为所有路由添加统一的前缀。

### 单一前缀

```python
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet)
# 生成: /api/products, /api/products/<pk>
```

### 版本化 API

```python
# v1 API
router_v1 = SanicRouter(app, prefix="api/v1")
router_v1.register("products", ProductViewSetV1)
# 生成: /api/v1/products

# v2 API
router_v2 = SanicRouter(app, prefix="api/v2")
router_v2.register("products", ProductViewSetV2)
# 生成: /api/v2/products
```

### 嵌套资源

`SanicRouter.register()` 会在资源名后添加集合和详情路径。嵌套路由可把父资源 ID 放在前缀中，并将子资源名作为 `path` 注册。子资源 ViewSet 需在 `get_queryset()` 中按父资源 ID 限定数据：

```python
review_router = SanicRouter(app, prefix="api/products/<product_id:int>")
review_router.register("reviews", ReviewViewSet)
# 集合: /api/products/<product_id:int>/reviews
# 详情: /api/products/<product_id:int>/reviews/<pk>
```

## 多个 ViewSet 注册

### 在同一个 Router 中注册

```python
router = SanicRouter(app, prefix="api")

# 注册多个 ViewSet
router.register("products", ProductViewSet)
router.register("categories", CategoryViewSet)
router.register("orders", OrderViewSet)
router.register("reviews", ReviewViewSet)

```

### 使用多个 Router

```python
# 公开 API 路由
public_router = SanicRouter(app, prefix="api/public")
public_router.register("products", ProductViewSet)
public_router.register("categories", CategoryViewSet)

# 管理员 API 路由
admin_router = SanicRouter(app, prefix="api/admin")
admin_router.register("users", UserViewSet)
admin_router.register("orders", OrderViewSet)
```

## 自定义 Blueprint

需要按模块组织路由或为路由添加 Blueprint 中间件时，可以传入自己的 Blueprint 对象。
`SanicRouter` 会将路由直接注册到该 Blueprint；注册完成后，再用 `app.blueprint(bp)`
将 Blueprint 挂载到 Sanic 应用。URL 前缀由 `SanicRouter` 的 `prefix` 统一设置：

```python
from sanic import Blueprint
from srf.route import SanicRouter

# 创建自定义 Blueprint
my_blueprint = Blueprint("my_api")

# 使用自定义 Blueprint
router = SanicRouter(my_blueprint, prefix="api")
router.register("products", ProductViewSet)

# Blueprint 完成路由注册后，再挂载到 Sanic 应用
app.blueprint(my_blueprint)
```

## URL 反向解析

使用路由名称生成 URL：

```python
from sanic import Sanic

app = Sanic("MyApp")

# ... 注册路由 ...

# 反向解析 URL
url = app.url_for("products-list")
# 结果: /api/products

url = app.url_for("products-detail", pk=1)
# 结果: /api/products/1

url = app.url_for("products-list_featured")
# 结果: /api/products/featured

url = app.url_for("products-publish", pk=1)
# 结果: /api/products/1/publish
```

在 ViewSet 中使用：

```python
class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # ... 创建产品 ...

        # 生成详情 URL
        detail_url = request.app.url_for("products-detail", pk=product.id)

        return json({"id": product.id, "url": detail_url}, status=201)
```

## 路由中间件

为特定路由添加中间件：

```python
from sanic import Blueprint
from srf.route import SanicRouter

# 创建 Blueprint
bp = Blueprint("api")


# 添加中间件
@bp.middleware("request")
async def add_custom_header(request):
    request.ctx.custom_data = "value"


# 使用 Blueprint
router = SanicRouter(bp, prefix="api")
router.register("products", ProductViewSet)

app.blueprint(bp)
```

## 完整示例

### 示例 1：基本路由设置

```python
# app.py
from sanic import Sanic
from srf.route import SanicRouter
from viewsets import ProductViewSet, CategoryViewSet

app = Sanic("ShopApp")

# 创建路由器
router = SanicRouter(app, prefix="api")

# 注册 ViewSets
router.register("products", ProductViewSet, name="products")
router.register("categories", CategoryViewSet, name="categories")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

生成的路由：

```
GET    /api/products              -> list
POST   /api/products              -> create
GET    /api/products/<pk>         -> retrieve
PUT    /api/products/<pk>         -> update
PATCH  /api/products/<pk>         -> update
DELETE /api/products/<pk>         -> destroy

GET    /api/categories            -> list
POST   /api/categories            -> create
GET    /api/categories/<pk>       -> retrieve
PUT    /api/categories/<pk>       -> update
PATCH  /api/categories/<pk>       -> update
DELETE /api/categories/<pk>       -> destroy
```

### 示例 2：多版本 API

```python
# routes.py
from srf.route import SanicRouter
from viewsets.v1 import ProductViewSetV1
from viewsets.v2 import ProductViewSetV2


def register_routes(app):
    # v1 路由
    router_v1 = SanicRouter(app, prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)

    router_v2 = SanicRouter(app, prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
```

生成的路由：

```
# v1 API
GET    /api/v1/products           -> ProductViewSetV1.list
POST   /api/v1/products           -> ProductViewSetV1.create
GET    /api/v1/products/<pk>      -> ProductViewSetV1.retrieve

# v2 API
GET    /api/v2/products           -> ProductViewSetV2.list
POST   /api/v2/products           -> ProductViewSetV2.create
GET    /api/v2/products/<pk>      -> ProductViewSetV2.retrieve
```

## 路由调试

### 查看所有路由

```python
@app.before_server_start
async def print_routes(app, loop):
    """打印所有注册的路由"""
    for route in app.router.routes:
        print(f"{route.methods} {route.path} -> {route.name}")
```

### 使用 Sanic 的路由列表

```python
from sanic import Sanic

app = Sanic("MyApp")
# ... 注册路由 ...

# 打印路由
for route in app.router.routes:
    methods = ", ".join(route.methods)
    print(f"[{methods}] {route.path}")
```

输出示例：

```
[GET, HEAD, POST] /api/products
[GET, HEAD, PUT, PATCH, DELETE] /api/products/<pk>
[GET] /api/products/featured
[POST] /api/products/<pk>/publish
```

## 最佳实践

1. **使用有意义的路径名称**：路径应该清晰地表示资源类型
2. **保持 URL 结构一致**：使用统一的命名规范
3. **版本化 API**：使用 URL 前缀区分不同版本
4. **模块化组织**：将相关的路由组织在一起
5. **使用路由名称**：利用路由名称进行 URL 反向解析
6. **文档化路由**：为每个 ViewSet 添加文档字符串

## 常见问题

### 如何禁用某些 HTTP 方法？

重写对应的方法并返回 405 错误：

```python
class ProductViewSet(BaseViewSet):
    async def destroy(self, request, pk):
        """禁用删除操作"""
        from sanic.response import json

        return json({"error": "不支持删除操作"}, status=405)
```

### 如何自定义 URL 参数类型？

使用 Sanic 的路径参数语法：

```python
# SanicRouter 生成的 pk 参数不指定类型；调用 get_object(pk) 时 SRF 会规范化主键
# /api/products/<pk>

# 可以在自定义操作中使用其他类型
@action(methods=["get"], detail=True, url_path="by-slug/<slug:str>")
async def get_by_slug(self, request, pk, slug):
    pass
```

### 如何处理嵌套资源？

使用多个 Router 和不同的 URL 前缀：

```python
# 产品路由
router.register("products", ProductViewSet)

# 产品下的评论（需要在 ViewSet 中处理 product_id）
review_router = SanicRouter(app, prefix="api/products/<product_id:int>")
review_router.register("reviews", ReviewViewSet)
```

## 下一步

- 学习 [视图](viewsets.md) 了解如何创建 ViewSet
- 阅读 [认证](authentication.md) 了解如何保护路由
- 查看 [权限](permissions.md) 了解访问控制
