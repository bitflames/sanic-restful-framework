# API 参考

本文档提供 SRF 核心 API 的详细参考。

## 视图（Views）

### BaseViewSet

所有 ViewSet 的基类。

```python
from srf.views import BaseViewSet
from pydantic import BaseModel

class BaseViewSet(HTTPMethodView, ModelMixin):
    """ViewSet 基类"""
    
    # 配置属性
    schema: BaseModel = None
    permission_classes = ()          # 权限类列表
    search_fields = []               # 搜索字段
    filter_fields = {}               # 过滤字段映射
    ordering_fields = {}             # 排序字段映射
    filter_class = []                # 过滤器类列表
    
    # 核心属性
    @property
    def queryset(self):
        """返回查询集（必须实现）"""
        raise NotImplementedError
    
    # 核心方法
    def get_schema(self, request, is_safe=False):
        """返回 Schema（可选） """
        raise NotImplementedError
    
    async def check_permissions(self, request):
        """检查视图级权限（可选）"""
        pass
    
    async def check_object_permissions(self, request, obj):
        """检查对象级权限（可选）"""
        pass
    
    async def get_object(self, request, id: int):
        """获取对象并检查权限（可选）"""
        pass
```

### Mixins

#### CreateModelMixin

```python
class CreateModelMixin:
    """创建 Mixin"""
    
    async def create(self, request):
        """处理 POST 请求"""
        pass
    
    async def perform_create(self, request, schema):
        """执行创建（可重写）"""
        pass
```

#### RetrieveModelMixin

```python
class RetrieveModelMixin:
    """详情 Mixin"""
    
    async def retrieve(self, request, pk):
        """处理 GET /resource/<pk> 请求"""
        pass
```

#### UpdateModelMixin

```python
class UpdateModelMixin:
    """更新 Mixin"""
    
    async def update(self, request, pk):
        """处理 PUT/PATCH 请求"""
        pass
    
    async def perform_update(self, request, obj, schema):
        """执行更新（可重写）"""
        pass
```

#### DestroyModelMixin

```python
class DestroyModelMixin:
    """删除 Mixin"""
    
    async def destroy(self, request, pk):
        """处理 DELETE 请求"""
        pass
    
    async def perform_destroy(self, request, obj):
        """执行删除（可重写）"""
        pass
```

#### ListModelMixin

```python
class ListModelMixin:
    """列表 Mixin"""
    
    async def list(self, request):
        """处理 GET /resource 请求"""
        pass
```

### 装饰器

#### @action

```python
from srf.views.decorators import action

@action(
    methods: list = ["get"],     # HTTP 方法列表
    detail: bool = False,        # 是否为详情级操作
    url_path: str = None,        # URL 路径
    url_name: str = None         # 路由名称
)
```

**示例**：

```python
@action(methods=["get"], detail=False)
async def featured(self, request):
    """集合级操作"""
    pass

@action(methods=["post"], detail=True)
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
    
    def has_permission(self, request, view) -> bool:
        """视图级权限检查"""
        return True
    
    def has_object_permission(self, request, view, obj) -> bool:
        """对象级权限检查"""
        return True
```

### 内置权限类

```python
from srf.permission.permission import (
    IsAuthenticated,      # 需要登录
    IsRoleAdminUser,      # 需要管理员角色
    IsSafeMethodOnly      # 仅允许安全方法
)
```

## 分页（Pagination）

### PaginationHandler

```python
from srf.paginator import PaginationHandler

class PaginationHandler:
    """分页处理器"""
    
    page_size = 10                      # 默认每页数量
    max_page_size = 100                 # 最大每页数量
    page_query_param = 'page'           # 页码参数名
    page_size_query_param = 'page_size' # 每页数量参数名
    
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
    
    async def filter_queryset(self, request, queryset):
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
async def authenticate(request):
    """验证用户凭证，返回 JWT payload"""
    pass

async def retrieve_user(request, payload, *args, **kwargs):
    """从 JWT payload 获取用户对象"""
    pass

async def store_user(request, user_id):
    """将用户存储到请求上下文"""
    pass
```

### setup_auth

```python
from srf.auth.viewset import setup_auth

setup_auth(
    app,                                # Sanic 应用
    secret: str,                        # JWT 密钥
    expiration_delta: int,              # 过期时间（秒）
    url_prefix: str = "/auth",          # URL 前缀
    authenticate: callable,             # 认证函数
    retrieve_user: callable,            # 获取用户函数
    store_user: callable                # 存储用户函数
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

app.config.RequestLimiter = [
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
from srf.health.base import BaseHealthCheck, HealthCheckRegistry

class BaseHealthCheck:
    """健康检查基类"""
    
    name: str = None
    
    def __init__(self, app):
        self.app = app
    
    async def check(self) -> bool:
        """执行检查"""
        raise NotImplementedError
    
    async def run(self):
        """运行检查并返回结果"""
        pass

# 注册自定义检查
HealthCheckRegistry.register(CustomHealthCheck)
```

### 内置健康检查

```python
from srf.health.checks import (
    RedisCheck,       # Redis 检查
    PostgresCheck,    # PostgreSQL 检查
    MongoCheck,       # MongoDB 检查
    SQLiteCheck       # SQLite 检查
)
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
from srf.views.http_status import HTTPStatus

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

# 辅助函数
HTTPStatus.is_informational(code)  # 1xx
HTTPStatus.is_success(code)        # 2xx
HTTPStatus.is_redirect(code)       # 3xx
HTTPStatus.is_client_error(code)   # 4xx
HTTPStatus.is_server_error(code)   # 5xx
```

## 配置（Configuration）

### SrfConfig

```python
from srf.config import srfconfig

# 设置应用配置
srfconfig.set_app(app)

# 访问应用的任意配置
srfconfig.SECRET_KEY
srfconfig.JWT_SECRET
srfconfig.JWT_ACCESS_TOKEN_EXPIRES
srfconfig.NON_AUTH_ENDPOINTS
srfconfig.DEFAULT_FILTERS
```

## 工具函数（Utils）

### 邮件发送

```python
from srf.tools.email import send_email

await send_email(
    to: str,              # 收件人
    subject: str,         # 主题
    content: str,         # 内容
    is_html: bool = False # 是否为 HTML
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
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    async def list(self, request: Request) -> json:
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
from typing import Optional

from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.views.http_status import HTTPStatus
from srf.route import SanicRouter
from srf.permission.permission import IsAuthenticated
from srf.config import srfconfig

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
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    @action(methods=["get"], detail=False)
    async def featured(self, request):
        products = await Product.filter(stock__gt=0).limit(10)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data}, status=HTTPStatus.HTTP_200_OK)

# 应用
app = Sanic("MyApp")
srfconfig.set_app(app)

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
