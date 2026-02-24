# 认证中间件

认证中间件自动处理 JWT Token 验证并将用户信息添加到请求上下文中。

## 概述

认证中间件的主要功能：

- 从请求头提取 JWT Token
- 验证 Token 的有效性
- 从 Token 中提取用户 ID
- 加载用户信息并存储到请求上下文
- 处理公开端点（无需认证）

## 快速开始

### 1. 配置中间件

```python
from sanic import Sanic
from srf.middleware.authmiddleware import set_user_to_request_ctx

app = Sanic("MyApp")

@app.middleware("request")
async def auth_middleware(request):
    """认证中间件"""
    await set_user_to_request_ctx(request)
```

### 2. 配置公开端点

在配置文件中定义不需要认证的端点：

```python
# config.py
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # 公开的产品列表
        "/health/",
    ]
```

### 3. 在 ViewSet 中使用

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """创建产品"""
        # 获取当前用户
        user = self.get_current_user(request)
        
        if user:
            print(f"用户 {user.name} 正在创建产品")
        else:
            print("匿名用户访问")
```

## 工作原理

### 中间件流程

```
1. 检查是否为公开端点
   ├─ 是：跳过认证，继续处理请求
   └─ 否：继续认证流程

2. 提取 Bearer Token
   ├─ Authorization 头存在
   │  └─ 提取 Token
   └─ Authorization 头不存在
      └─ 跳过认证（request.ctx.user = None）

3. 验证 Token
   ├─ Token 有效
   │  ├─ 提取 user_id
   │  ├─ 加载用户信息
   │  └─ 存储到 request.ctx.user
   └─ Token 无效
      └─ request.ctx.user = None

4. 继续处理请求
```

### 核心函数

#### is_public_endpoint(request)

检查请求路径是否为公开端点：

```python
from srf.middleware.authmiddleware import is_public_endpoint

def is_public_endpoint(request):
    """检查是否为公开端点
    
    Args:
        request: 请求对象
    
    Returns:
        bool: True 表示公开端点，False 表示需要认证
    """
    from srf.config import srfconfig
    
    path = request.path
    non_auth_endpoints = srfconfig.NON_AUTH_ENDPOINTS
    
    # 精确匹配或前缀匹配
    for endpoint in non_auth_endpoints:
        if path == endpoint or path.startswith(endpoint):
            return True
    
    return False
```

#### extract_bearer_token(request)

从 Authorization 头提取 Bearer Token：

```python
from srf.middleware.authmiddleware import extract_bearer_token

def extract_bearer_token(request):
    """提取 Bearer Token
    
    Args:
        request: 请求对象
    
    Returns:
        str | None: Token 字符串，如果不存在返回 None
    """
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # 移除 "Bearer " 前缀
    
    return None
```

#### authenticate_request(request)

验证 Token 并返回用户信息：

```python
async def authenticate_request(request):
    """验证请求并返回用户
    
    Args:
        request: 请求对象
    
    Returns:
        User | None: 用户对象，如果验证失败返回 None
    """
    token = extract_bearer_token(request)
    
    if not token:
        return None
    
    try:
        # 验证 JWT Token
        payload = verify_jwt_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            return None
        
        # 加载用户
        from models import Account
        user = await Account.get_or_none(id=user_id).prefetch_related('role')
        
        return user
    except Exception as e:
        # Token 无效或已过期
        return None
```

## 公开端点配置

### 精确匹配

```python
NON_AUTH_ENDPOINTS = [
    "/api/auth/login",        # 精确匹配 /api/auth/login
    "/api/auth/register",     # 精确匹配 /api/auth/register
]
```

### 前缀匹配

```python
NON_AUTH_ENDPOINTS = [
    "/api/public/",           # 匹配所有 /api/public/* 路径
    "/health/",               # 匹配所有 /health/* 路径
]
```

### 混合配置

```python
NON_AUTH_ENDPOINTS = [
    # 认证相关
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/send-verification-email",
    "/api/auth/social/",
    
    # 公开 API
    "/api/public/",
    
    # 健康检查
    "/health/",
    
    # 静态文件
    "/static/",
    "/media/",
]
```

## 获取当前用户

### 在 ViewSet 中

```python
from srf.views import BaseViewSet

class OrderViewSet(BaseViewSet):
    async def list(self, request):
        """获取订单列表"""
        # 方法1：使用 get_current_user
        user = self.get_current_user(request)
        
        # 方法2：直接访问 request.ctx.user
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        
        if not user:
            from sanic.response import json
            return json({"error": "未登录"}, status=401)
        
        # 获取用户的订单
        orders = await Order.filter(user_id=user.id)
        # ...
```

### 在路由处理器中

```python
from sanic.response import json

@app.route('/api/profile')
async def get_profile(request):
    """获取用户资料"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if not user:
        return json({"error": "未登录"}, status=401)
    
    return json({
        "id": user.id,
        "name": user.name,
        "email": user.email,
    })
```

### 在自定义中间件中

```python
@app.middleware("request")
async def log_user(request):
    """记录用户信息"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if user:
        print(f"User {user.id} ({user.name}) is accessing {request.path}")
    else:
        print(f"Anonymous user is accessing {request.path}")
```

## 完整示例

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from sanic.response import json

app = Sanic("MyApp")

# 配置公开端点
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/products",
        "/health/",
    ]

app.config.update_config(Config)
srfconfig.set_app(app)

# 注册认证中间件
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)

# 记录用户访问
@app.middleware("request")
async def log_access(request):
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    user_info = f"User {user.id}" if user else "Anonymous"
    print(f"{user_info} - {request.method} {request.path}")

# ViewSet 示例
class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @property
    def queryset(self):
        # 只返回当前用户的订单
        user = self.get_current_user(request)
        if user:
            return Order.filter(user_id=user.id)
        return Order.none()

# 路由示例
@app.route('/api/me')
async def get_current_user_info(request):
    """获取当前用户信息"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if not user:
        return json({"error": "未登录"}, status=401)
    
    return json({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.name if user.role else None,
    })
```

## Token 刷新

### 实现 Token 刷新机制

```python
from sanic_jwt import refresh_token_required

@app.route('/api/auth/refresh', methods=['POST'])
@refresh_token_required
async def refresh(request):
    """刷新 access token"""
    from sanic_jwt import generate_access_token
    
    user = request.ctx.user
    
    # 生成新的 access token
    access_token = await generate_access_token(
        request.app,
        user,
        refresh_request=True
    )
    
    return json({
        "access_token": access_token
    })
```

### 客户端使用

```javascript
// 保存 tokens
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);

// 请求时使用 access token
fetch('/api/orders', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

// access token 过期时刷新
async function refreshAccessToken() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('refresh_token')}`
    }
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
}
```

## 安全最佳实践

### 1. 使用 HTTPS

生产环境必须使用 HTTPS 传输 Token：

```python
# 配置 SSL
app.run(
    host="0.0.0.0",
    port=443,
    ssl={'cert': 'cert.pem', 'key': 'key.pem'}
)
```

### 2. 设置合理的过期时间

```python
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1小时
JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30天
```

### 3. Token 黑名单

实现 Token 黑名单机制（用于注销）：

```python
import aioredis

async def blacklist_token(token):
    """将 Token 加入黑名单"""
    redis = request.app.ctx.redis
    # 存储到 Redis，过期时间与 Token 一致
    await redis.setex(f"blacklist:{token}", 3600, "1")

async def is_token_blacklisted(token):
    """检查 Token 是否在黑名单中"""
    redis = request.app.ctx.redis
    return await redis.exists(f"blacklist:{token}")

# 在中间件中检查
@app.middleware("request")
async def check_blacklist(request):
    token = extract_bearer_token(request)
    if token and await is_token_blacklisted(token):
        from sanic.response import json
        return json({"error": "Token 已失效"}, status=401)
```

### 4. 限制 Token 使用范围

在 Token payload 中添加额外信息：

```python
async def authenticate(request):
    # ...验证用户...
    
    return {
        "user_id": user.id,
        "username": user.name,
        "role": user.role.name,
        "ip": request.ip,  # 绑定 IP
        "device": request.headers.get('User-Agent'),  # 绑定设备
    }

# 在中间件中验证
async def authenticate_request(request):
    payload = verify_jwt_token(token)
    
    # 验证 IP
    if payload.get('ip') != request.ip:
        return None
    
    # 加载用户
    user = await Account.get_or_none(id=payload['user_id'])
    return user
```

## 故障排查

### 常见问题

#### 1. Token 验证失败

**症状**：请求返回 401，但 Token 看起来是有效的

**检查**：
- Token 格式是否正确（Bearer + 空格 + Token）
- Token 是否过期
- JWT Secret 是否匹配
- Token 是否在黑名单中

**调试**：

```python
import jwt

# 解码 Token（不验证）
try:
    payload = jwt.decode(token, options={"verify_signature": False})
    print(payload)  # 查看 payload 内容
except Exception as e:
    print(f"解码失败: {e}")
```

#### 2. 用户信息未设置

**症状**：`request.ctx.user` 为 None

**检查**：
- 是否注册了认证中间件
- 是否在公开端点列表中
- 数据库中是否存在该用户

**调试**：

```python
@app.middleware("request")
async def debug_auth(request):
    token = extract_bearer_token(request)
    print(f"Path: {request.path}")
    print(f"Token: {token}")
    print(f"Is public: {is_public_endpoint(request)}")
    print(f"User: {request.ctx.user if hasattr(request.ctx, 'user') else None}")
```

#### 3. 性能问题

**症状**：每个请求都很慢

**原因**：每次请求都查询数据库加载用户

**解决**：使用缓存

```python
async def authenticate_request(request):
    token = extract_bearer_token(request)
    if not token:
        return None
    
    payload = verify_jwt_token(token)
    user_id = payload.get('user_id')
    
    # 尝试从缓存获取
    redis = request.app.ctx.redis
    cache_key = f"user:{user_id}"
    cached = await redis.get(cache_key)
    
    if cached:
        import json
        user_data = json.loads(cached)
        # 从缓存数据构造用户对象
        # ...
    else:
        # 从数据库加载
        user = await Account.get_or_none(id=user_id)
        # 存入缓存（5分钟）
        await redis.setex(cache_key, 300, json.dumps(user_data))
    
    return user
```

## 下一步

- 学习 [认证](../../core/authentication.md) 了解 JWT 认证详情
- 阅读 [权限](../../core/permissions.md) 了解权限控制
- 查看 [CSRF 中间件](csrf-middleware.md) 了解 CSRF 保护
