# 认证

SRF 提供了完整的认证系统，支持 JWT 认证和社交登录。

## JWT 认证

SRF 使用 `sanic-jwt` 库实现 JWT（JSON Web Token）认证，提供无状态的身份验证机制。

### 基本概念

JWT 是一种基于 Token 的认证方式：

1. 用户登录时，服务器验证凭证并生成 JWT Token
2. 客户端在后续请求中携带 Token（通常在 Authorization 头中）
3. 服务器验证 Token 并识别用户身份
4. Token 包含用户信息和过期时间

### 配置 JWT

#### 1. 设置环境变量

在 `.env` 文件中配置：

```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24小时
```

#### 2. 配置文件

在 `config.py` 中：

```python
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
```

#### 3. 实现认证函数

创建 `auth.py`：

```python
from models import Account
from sanic.exceptions import Unauthorized

async def authenticate(request):
    """验证用户凭证

    Args:
        request: 请求对象，包含 json 数据（email 和 password）

    Returns:
        dict: JWT payload，包含用户信息

    Raises:
        Unauthorized: 认证失败时抛出
    """
    email = request.json.get("email")
    password = request.json.get("password")

    if not email or not password:
        raise Unauthorized("请提供邮箱和密码")

    # 查找用户
    account = await Account.get_or_none(email=email)
    if not account:
        raise Unauthorized("邮箱或密码错误")

    # 验证密码
    if not account.verify_password(password):
        raise Unauthorized("邮箱或密码错误")

    # 检查账户状态
    if not account.is_active:
        raise Unauthorized("账户已被禁用")

    # 更新最后登录时间
    from datetime import datetime
    account.last_login = datetime.now()
    await account.save()

    # 返回 JWT payload
    return {
        "user_id": account.id,
        "username": account.name,
        "email": account.email,
        "role": account.role.name if account.role else "user",
    }

async def retrieve_user(request, payload, *args, **kwargs):
    """从 JWT payload 中获取用户对象

    Args:
        request: 请求对象
        payload: JWT payload（包含 user_id 等信息）

    Returns:
        Account: 用户对象
    """
    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    account = await Account.get_or_none(id=user_id).prefetch_related("role")
    return account

async def store_user(request, user_id):
    """将用户存储到请求上下文

    Args:
        request: 请求对象
        user_id: 用户 ID
    """
    account = await Account.get_or_none(id=user_id).prefetch_related("role")
    if account:
        request.ctx.user = account
```

#### 4. 初始化 JWT

在 `app.py` 中：

```python
from sanic import Sanic
from srf.auth.viewset import setup_auth
from auth import authenticate, retrieve_user, store_user
from config import config

app = Sanic("MyApp")

# 初始化 JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)
```

### 登录流程

#### 1. 用户登录

**请求**：

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**响应**：

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 2. 使用 Token 访问受保护的端点

**请求**：

```bash
curl http://localhost:8000/api/products \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 用户注册

#### 1. 创建注册视图

```python
from sanic.response import json
from sanic.exceptions import InvalidUsage
from models import Account, Role
from schemas import AccountSchemaWriter
import aioredis

async def register(request):
    """用户注册

    请求体：
        email: 邮箱
        password: 密码
        name: 姓名
        code: 验证码
    """
    try:
        # 验证数据
        data = AccountSchemaWriter(**request.json)
    except Exception as e:
        raise InvalidUsage(str(e))

    # 验证邮箱验证码
    code = request.json.get("code")
    if not code:
        raise InvalidUsage("请提供验证码")

    # 从 Redis 获取验证码
    redis = request.app.ctx.redis
    stored_code = await redis.get(f"email_code:{data.email}")

    if not stored_code or stored_code.decode() != code:
        raise InvalidUsage("验证码错误或已过期")

    # 检查邮箱是否已注册
    if await Account.filter(email=data.email).exists():
        raise InvalidUsage("该邮箱已被注册")

    # 创建用户
    default_role = await Role.get_or_none(name="user")
    account = await Account.create(
        email=data.email,
        name=data.name,
        password=data.password,  # 模型会自动哈希密码
        role=default_role,
    )

    # 删除验证码
    await redis.delete(f"email_code:{data.email}")

    return json({
        "message": "注册成功",
        "user": {
            "id": account.id,
            "email": account.email,
            "name": account.name,
        }
    }, status=201)
```

#### 2. 发送验证码

```python
from srf.tools.email import send_email
import random
import string

async def send_verification_email(request):
    """发送邮箱验证码"""
    email = request.json.get("email")
    if not email:
        raise InvalidUsage("请提供邮箱地址")

    # 生成6位验证码
    code = ''.join(random.choices(string.digits, k=6))

    # 存储到 Redis（10分钟过期）
    redis = request.app.ctx.redis
    await redis.setex(f"email_code:{email}", 600, code)

    # 发送邮件
    await send_email(
        to=email,
        subject="验证码",
        content=f"您的验证码是：{code}，10分钟内有效。"
    )

    return json({"message": "验证码已发送"})
```

#### 3. 注册路由

```python
from srf.auth.route import register_auth_urls

# 注册认证路由（包括登录、注册等）
register_auth_urls(app, prefix="/api/auth")
```

### 获取当前用户

在 ViewSet 中获取当前登录用户：

```python
from srf.views import BaseViewSet
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """创建产品"""
        # 获取当前用户
        current_user = self.get_current_user(request)

        if not current_user:
            return json({"error": "未登录"}, status=401)

        # 使用用户信息
        print(f"用户 {current_user.name} 正在创建产品")

        # ... 创建逻辑 ...
```

## 认证中间件

认证中间件自动处理 JWT Token 验证并将用户信息添加到请求上下文。

### 配置中间件

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    """认证中间件"""
    await set_user_to_request_ctx(request)
```

### 公开端点配置

配置不需要认证的端点：

```python
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # 公开的产品列表
        "/health/",
    ]
```

### 中间件工作流程

1. 提取 Authorization 头中的 Bearer Token
2. 验证 Token 的有效性
3. 从 Token 中提取 user_id
4. 从数据库加载用户信息
5. 将用户存储到 `request.ctx.user`

## 完整示例

### 账户模型

```python
from tortoise import fields
from tortoise.models import Model
import bcrypt

class Role(Model):
    """角色模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField(null=True)

class Account(Model):
    """账户模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password = fields.CharField(max_length=255)
    role = fields.ForeignKeyField("models.Role", related_name="accounts", null=True)
    is_active = fields.BooleanField(default=True)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode(), self.password.encode())

    async def save(self, *args, **kwargs):
        """保存前哈希密码"""
        if self._custom_generated_pk or not self.pk:
            # 新创建的账户，哈希密码
            self.password = self.hash_password(self.password)
        await super().save(*args, **kwargs)
```

### Schema 定义

```python
from pydantic import BaseModel, EmailStr, Field

class AccountSchemaWriter(BaseModel):
    """账户写入 Schema"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")

class AccountSchemaReader(BaseModel):
    """账户读取 Schema"""
    id: int
    email: str
    name: str
    is_active: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True
```

### 应用配置

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.auth.viewset import setup_auth
from srf.auth.route import register_auth_urls
from srf.middleware.authmiddleware import set_user_to_request_ctx
from auth import authenticate, retrieve_user, store_user
from config import config

app = Sanic("MyApp")
srfconfig.set_app(app)

# 配置 JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)

# 注册认证路由
register_auth_urls(app, prefix="/api/auth")

# 认证中间件
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

## 最佳实践

1. **安全存储密码**：使用 bcrypt 等强加密算法
2. **Token 过期时间**：设置合理的过期时间（如24小时）
3. **刷新 Token**：实现 Token 刷新机制
4. **HTTPS**：生产环境必须使用 HTTPS
5. **验证邮箱**：注册时发送验证邮件
6. **限制登录尝试**：防止暴力破解
7. **记录登录日志**：记录登录时间和IP
8. **角色权限**：使用角色管理用户权限

## 下一步

- 学习 [权限](permissions.md) 了解详细的权限控制
- 阅读 [认证中间件](../advanced/middleware/auth-middleware.md) 了解中间件原理
- 查看 [视图](viewsets.md) 了解如何在 ViewSet 中使用认证
