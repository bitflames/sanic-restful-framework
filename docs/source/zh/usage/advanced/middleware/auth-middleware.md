# 认证中间件

认证中间件从请求中读取 JWT，并把数据库中的用户对象写入
`request.ctx.user`。`authenticate_request()` 支持两种模式：

- **`strict=False`（默认，可选认证）**：完全未携带凭证（没有 `Authorization` 头）的请求回退为
  `request.ctx.user = AnonymousUser()`（见 `srf.auth.models.AnonymousUser`）。**出示了**
  但无效、过期、伪造或其用户已不存在的 token 仍然抛出 401——一旦客户端尝试认证，该次尝试必须成功。
- **`strict=True`（强制认证）**：每个请求都必须携带有效且未过期的 access token；
  否则（包括完全未携带凭证的请求）抛出 401。

公开端点（登录、注册、刷新令牌、健康检查等）也可以由调用方在调用该函数**之前**过滤（白名单），
使其完全跳过认证。

## 配置

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    # 白名单先行过滤：公开端点完全跳过认证
    if request.path == "/health" or request.path.startswith("/api/auth/"):
        request.ctx.user = None
        return
    await set_user_to_request_ctx(request, strict=True)  # 强制认证
```

应用必须提供与签发 Token 相同的密钥：

```python
app.config.JWT_SECRET = "从安全的环境变量读取"
```

## 请求流程

1. 从 `Authorization: Bearer <token>` 提取 token。头缺失时：`strict=True` 抛出 401，
   否则回退为 `request.ctx.user = AnonymousUser()`；格式错误时一律抛出 401。
2. 通过 `request.app.ctx.auth` 验签并校验有效期；过期、伪造或无法解码时抛出 401
   （两种模式一致）。
3. 调用 `retrieve_user(request, payload)` 加载用户，并将 ORM 用户放到
   `request.ctx.user`；用户不存在或被禁用时抛出 401。

注意：白名单路径完全跳过认证——即使携带有效 token，`request.ctx.user` 也是 `None`。

## 核心函数

### extract_bearer_token

```python
from srf.middleware.authmiddleware import extract_bearer_token

token = extract_bearer_token(request)
```

该函数要求认证方案为 Bearer（大小写不敏感），并在请求头缺失或格式错误时抛出 401。

### authenticate_request

```python
from srf.middleware.authmiddleware import authenticate_request

await authenticate_request(request)               # 可选认证（默认）：无 token -> AnonymousUser
await authenticate_request(request, strict=True)  # 强制认证：无 token -> 401
user = request.ctx.user
```

### set_user_to_request_ctx

该函数透传参数给 `authenticate_request` 并作为应用 middleware 使用。`strict=False`（默认）为可选认证：
无凭证回退 `AnonymousUser`；`strict=True` 为强制认证。出示了但无效的 token 在两种模式下都抛出 401
（见 [authenticate_request](#authenticate_request)）。

## 中间件顺序

用户限流、访问日志等逻辑如需读取 `request.ctx.user`，应确保认证中间件先
执行。认证上下文可能尚未设置，读取时使用：

```python
user = getattr(request.ctx, "user", None)
```

## 安全限制

- 每个携带有效 Token 的请求都会查询数据库。
- 认证中间件自身不实现 Token 黑名单；刷新令牌由认证路由管理。

生产应用可根据需要配置 Token 吊销和适当的用户缓存。

## 下一步

- 阅读[认证](../../core/authentication.md)配置 Token 签发。
- 阅读[权限](../../core/permissions.md)控制用户访问范围。
- 阅读[限流](rate-limiting.md)保护认证接口。
