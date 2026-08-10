# API 参考

本文档提供 SRF 核心 API 的详细参考。

## 视图（Views）

### BaseViewSet

所有 ViewSet 的基类。

```python
from srf.views import BaseViewSet
from pydantic import BaseModel

class GenericAPIView(BaseViewSet):
    """ViewSet 基类"""

    # 子类常用配置
    schema: BaseModel = None         # pydantic 模型
    permission_classes = ()          # 未声明时 check_permissions 按空列表处理
    search_fields = []               # 搜索字段，由 SearchFilter 读取
    filter_fields = {}               # 过滤字段映射，由 FilterClass 读取
    ordering_fields = {}             # 排序字段映射，由 OrderingFactory 读取
    queryset = None                  # 设置 QuerySet / property，或重写 get_queryset()

    def get_schema(self, request, *args, is_safe=False, **kwargs):
        """默认返回 self.schema；可以根据请求方法自定义返回"""
        return getattr(self, "schema", None)

    def get_queryset(self):
        """从 self.queryset 返回本次请求的 QuerySet（必要时用 .all() 克隆）"""
        ...

    def filter_queryset(self, queryset):
        """对 queryset 应用 filter_class（list() 使用）"""
        ...

    async def check_permissions(self, request):
        """在 permission_classes 上调用 has_permission；拒绝时 raise Forbidden"""
        ...

    async def check_object_permissions(self, request, obj):
        """在各类上调用 has_object_permission；拒绝时 raise Forbidden"""
        ...

    async def get_object(self, request, id: int):
        """通过 get_queryset() 查找对象，再调用 check_object_permissions()"""
        ...
```

### Mixins

#### CreateModelMixin

```python
class CreateModelMixin:
    """创建 Mixin"""

    async def create(self, request, *args, **kwargs):
        """处理 POST 请求；调用 perform_create(sch_model)"""
        ...

    async def perform_create(self, sch_model):
        """执行创建（可重写）"""
        ...
```

#### RetrieveModelMixin

```python
class RetrieveModelMixin:
    """详情 Mixin"""

    async def retrieve(self, request, pk, *args, **kwargs):
        """处理 GET /resource/<pk> 请求"""
        ...
```

#### UpdateModelMixin

```python
class UpdateModelMixin:
    """更新 Mixin"""

    async def update(self, request, pk, *args, **kwargs):
        """处理 PUT/PATCH 请求"""
        ...

    async def perform_update(self, sch_model, orm_model):
        """执行更新（可重写）"""
        ...
```

#### DestroyModelMixin

```python
class DestroyModelMixin:
    """删除 Mixin"""

    async def destroy(self, request, pk, *args, **kwargs):
        """处理 DELETE 请求；调用 perform_destroy(orm_model)"""
        ...

    async def perform_destroy(self, orm_model):
        """执行删除（可重写）"""
        ...
```

#### ListModelMixin

```python
class ListModelMixin:
    """列表 Mixin"""

    async def list(self, request, *args, **kwargs):
        """处理 GET /resource 请求"""
        ...
```

### 装饰器

#### @action

```python
from srf.views.decorators import action

@action(
    *,
    detail: bool = False,                 # 详情级操作（需要 pk）
    methods: Sequence[str] = ("GET",),    # HTTP 方法
    url_path: str | None = None,          # 默认："/<方法名>"
    url_name: str | None = None,          # 路由名称（默认：方法名）
)
```

**示例**：

```python
@action(methods=["get"], detail=False, url_path="featured")
async def featured(self, request):
    """集合级操作"""
    pass

@action(methods=["post"], detail=True, url_path="publish")
async def publish(self, request, pk):
    """详情级操作"""
    pass
```

## 路由（Routing）

### SanicRouter

```python
from srf.route import SanicRouter

class SanicRouter:
    """路由管理器"""
    
    def __init__(self, bp: Blueprint = None, prefix: str = ""):
        """初始化路由器
        
        Args:
            bp: Sanic Blueprint 实例
            prefix: URL 前缀
        """
        pass
    
    def register(self, path: str, view_cls, name: str = None):
        """注册 ViewSet
        
        Args:
            path: URL 路径
            view_cls: ViewSet 类
            name: 路由名称前缀
        """
        pass
    
    def get_blueprint(self) -> Blueprint:
        """获取 Blueprint"""
        pass
```

**示例**：

```python
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet, name="products")
app.blueprint(router.get_blueprint())
```

## 权限（Permissions）

### BasePermission

```python
from srf.permission.permission import BasePermission

class BasePermission:
    """权限基类"""

    @staticmethod
    def has_permission(request, view=None) -> bool:
        """视图级权限检查"""
        return True

    @staticmethod
    def has_object_permission(request, view=None, obj=None) -> bool:
        """对象级权限检查"""
        return True
```

### 内置权限类

```python
from srf.permission.permission import (
    AllowAny,             # 始终允许（DEFAULT_PERMISSION_CLASSES 默认值）
    IsAuthenticated,      # 需要登录
    IsRoleAdminUser,      # 需要管理员角色
    IsSafeMethodOnly      # 仅允许安全方法
)
```

## 分页（Pagination）

### BasePagination

```python
from srf.paginator import BasePagination

class BasePagination:
    """DRF 风格基类。自定义分页须继承并实现会 raise NotImplementedError 的方法。"""

    @classmethod
    def from_queryset(cls, queryset, request):
        raise NotImplementedError

    async def paginate(self, sch_model=None):
        raise NotImplementedError

    async def to_dict(self, sch_model=None):
        """默认：await paginate() 后 model_dump"""
        ...

    def num_pages(self, total_count=None):
        raise NotImplementedError
```

### PageNumberPagination

```python
from srf.paginator import PageNumberPagination

class PageNumberPagination(BasePagination):
    """分页处理器。"""

    MAX_PAGE_SIZE: int = 100
    PAGE_QUERY_PARAM: str = 'page'
    PAGE_SIZE_QUERY_PARAM: str = 'page_size'
    # 缺少/非法 page_size 时默认 10（from_queryset 回退）

    @classmethod
    def from_queryset(cls, queryset, request):
        """从查询集创建分页器"""
        pass

    async def paginate(self, sch_model):
        """执行分页"""
        pass

    async def to_dict(self, sch_model):
        """返回字典格式"""
        pass
```

## 过滤（Filtering）

### BaseFilter

```python
from srf.filters.filter import BaseFilter

class BaseFilter:
    """过滤器基类"""

    def __init__(self, view_class):
        self.view_class = view_class

    def filter_queryset(self, request, queryset):
        """过滤查询集"""
        raise NotImplementedError
```

### 内置过滤器

```python
from srf.filters.filter import (
    SearchFilter,        # 搜索过滤器
    JsonLogicFilter,     # JSON Logic 过滤器
    QueryParamFilter,    # 查询参数过滤器
    OrderingFactory      # 排序过滤器
)
```

## 认证（Authentication）

### JWT 函数

```python
from srf.auth.auth import authenticate, retrieve_user, store_user

async def authenticate(request, *args, **kwargs):
    """验证用户凭证，返回 JWT payload"""
    pass

async def retrieve_user(payload, *args, **kwargs):
    """从 JWT payload 获取用户对象"""
    pass

async def store_user(request, user_id, *args, **kwargs):
    """将用户存储到请求上下文"""
    pass
```

### setup_auth

```python
from srf.auth.viewset import setup_auth

setup_auth(
    app,
    secret=app.config.JWT_SECRET,  # 必填；缺失会抛 ServerError
    url_prefix="/api/auth",        # 默认 /api/auth
    login_path="login",            # 传给 sanic-jwt 的 path_to_authenticate
    # 其它 sanic-jwt Initialize 关键字参数...
)
```


## 中间件（Middleware）

### 认证中间件

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

### 限流中间件

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    PathRateLimit,
    HeaderRateLimit,
    throttle_rate
)

storage = MemoryStorage()

app.config.REQUEST_LIMITERS = [
    IPRateLimit(100, 60, storage),
    UserRateLimit(1000, 60, storage),
]


@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        return json({"error": "Too many requests"}, status=429)
```

## 健康检查（Health Checks）

### BaseHealthCheck

```python
from srf.health.base import BaseHealthCheck

class BaseHealthCheck:
    """健康检查基类"""

    name: str = "base"
    timeout: int = 5  # 秒；内置检查用 asyncio.timeout(self.timeout)

    def __init__(self, app):
        self.app = app
        client = getattr(app.ctx, self.name, None)
        if client is None:
            raise ValueError(f"{self.name} not found in app.ctx")
        setattr(self, self.name, client)

    async def check(self):
        """执行检查；失败时抛异常"""
        raise NotImplementedError

    async def run(self):
        """运行检查并返回 (name, status)"""
        ...
```


### 内置健康检查

```python
from srf.health.checks import (
    RedisCheck,       # Redis 检查（需 app.ctx.redis）
    SQLiteCheck,      # SQLite 检查（需 app.ctx.sqlite）
)

# 路由读取 app.config.HEALTH_CHECK_LIST
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
```

## 异常（Exceptions）

### 自定义异常

```python
from srf.exceptions import (
    TargetObjectAlreadyExist,  # 对象已存在（409）
    ImproperlyConfigured       # 配置错误（500）
)
```

## HTTP 状态码（HTTP Status）

### HTTPStatus

```python
from srf.views.http_status import (
    HTTPStatus,
    is_informational,
    is_success,
    is_redirect,
    is_client_error,
    is_server_error,
)

# 状态码常量
HTTPStatus.HTTP_200_OK
HTTPStatus.HTTP_201_CREATED
HTTPStatus.HTTP_204_NO_CONTENT
HTTPStatus.HTTP_400_BAD_REQUEST
HTTPStatus.HTTP_401_UNAUTHORIZED
HTTPStatus.HTTP_403_FORBIDDEN
HTTPStatus.HTTP_404_NOT_FOUND
HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY
HTTPStatus.HTTP_429_TOO_MANY_REQUESTS
HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR

# 辅助函数（模块级函数，不是 HTTPStatus 的方法）
is_informational(code)  # 1xx
is_success(code)        # 2xx
is_redirect(code)       # 3xx
is_client_error(code)   # 4xx
is_server_error(code)   # 5xx
```

## 配置（Configuration）

### LazySettings（`settings`）

```python
from srf.config import settings

# 绑定 Sanic app.config（可选；请求路径优先用 request.app.config）
settings.set_app(app)

# 常用配置（大写项来自 srf.config.settings，可被 app.config 覆盖）
settings.JWT_ACCESS_TOKEN_EXPIRES
settings.NON_AUTH_ENDPOINTS
settings.DEFAULT_FILTERS
settings.DEFAULT_PERMISSION_CLASSES
settings.EMAIL_CODE_REDIS      # 默认 "EMAIL_CODE"
settings.REQUEST_LIMITERS      # 默认 []
settings.HEALTH_CHECK_LIST     # 默认 []
settings.SOCIAL_CONFIG

# JWT_SECRET 需由应用设置到 app.config，无模块级默认值
app.config.JWT_SECRET = "..."

# srfconfig 为废弃别名（首次使用会发出 DeprecationWarning）
# from srf.config import srfconfig
```

## 工具函数（Utils）

### 邮件发送

```python
from srf.tools.email import send_email

await send_email(
    to_email: str,        # 收件人
    subject: str = "",    # 主题
    content: str = "",    # 内容
)
```

## 类型提示

```python
from sanic import Request
from tortoise.queryset import QuerySet
from pydantic import BaseModel
from typing import Type, List, Dict, Optional

class MyViewSet(BaseViewSet):
    @property
    def queryset(self) -> QuerySet:
        return Product.all()
    
    def get_schema(self, request: Request, is_safe: bool = False) -> Type[BaseModel]:
        is_read = request.method.upper() in ("GET", "HEAD", "OPTIONS")
        return ProductSchemaReader if is_read or is_safe else ProductSchemaWriter
    
    async def list(self, request: Request) -> JSONResponse:
        pass
```

## 完整示例

```python
from sanic import Sanic
from sanic.response import json
from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.sanic import register_tortoise
from pydantic import BaseModel, Field
from sanic.constants import SAFE_HTTP_METHODS
from typing import Optional

from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.views.http_status import HTTPStatus
from srf.route import SanicRouter
from srf.permission.permission import IsAuthenticated
from srf.config import settings

# 模型
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)

# Schema
class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=200)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class ProductSchemaReader(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    
    class Config:
        from_attributes = True

# ViewSet
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ["name"]
    filter_fields = {"min_price": "price__gte"}
    ordering_fields = {"price": "price"}
    
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        if request.method.upper() in SAFE_HTTP_METHODS or is_safe:
            return ProductSchemaReader
        return ProductSchemaWriter
    
    @action(detail=False, methods=["get"], url_path="featured")
    async def featured(self, request):
        products = await Product.filter(stock__gt=0).limit(10)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data}, status=HTTPStatus.HTTP_200_OK)

# 应用
app = Sanic("MyApp")
app.config.JWT_SECRET = "change-me"
settings.set_app(app)

# 数据库
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["__main__"]},
    generate_schemas=True,
)

# 路由
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet)
app.blueprint(router.get_blueprint())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## 下一步

- 查看 [快速开始](usage/getting-started.md) 创建第一个项目
- 阅读 [核心概念](usage/core/viewsets.md) 深入了解功能
- 浏览 [配置项](config.md) 了解配置选项
