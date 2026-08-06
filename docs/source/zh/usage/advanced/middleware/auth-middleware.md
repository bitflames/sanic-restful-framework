# 认证中间件

认证中间件校验 JWT，并把数据库中的用户对象写入
`request.ctx.user`。

## 配置

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

应用必须提供与签发 Token 相同的密钥：

```python
app.config.JWT_SECRET = "从安全的环境变量读取"
```

## 请求流程

1. 取 URL 最后一段，检查它是否在 `app.config.NON_AUTH_ENDPOINTS` 中。
2. 公开端点直接放行，不设置 `request.ctx.user`。
3. 非公开端点要求 `Authorization: Bearer <token>`。
4. 使用 HS256 和 `app.config.JWT_SECRET` 解码 Token。
5. 调用 `srf.auth.auth.retrieve_user(payload)` 查询用户。
6. 设置 `request.ctx.user`。

Token 缺失、格式错误、过期、无效或用户不存在都会抛出
`Unauthorized`（HTTP 401），不会匿名放行。

## 核心函数

### is_public_endpoint

```python
def is_public_endpoint(request):
    tail = request.path.rstrip("/").rpartition("/")[2]
    return tail in getattr(request.app.config, "NON_AUTH_ENDPOINTS", [])
```

配置值是路径最后一段：

```python
app.config.NON_AUTH_ENDPOINTS = (
    "login",
    "register",
    "send-verification-email",
    "health",
)
```

不要写 `"/api/auth/login"` 或 `"/api/public/"`；当前实现既不做完整路径匹配，
也不做前缀匹配。相同尾段会同时被豁免，例如 `"products"` 会匹配多个不同
前缀下的 `/products`。

### extract_bearer_token

```python
from srf.middleware.authmiddleware import extract_bearer_token

token = extract_bearer_token(request)
```

该函数要求认证方案为 Bearer（大小写不敏感），并在头缺失或格式错误时抛出
401，而不是返回 `None`。

### authenticate_request

```python
from srf.middleware.authmiddleware import authenticate_request

await authenticate_request(request)
user = request.ctx.user
```

该函数不检查公开端点；通常应通过 `set_user_to_request_ctx()` 调用。

## 中间件顺序

用户限流、访问日志等逻辑如需读取 `request.ctx.user`，应确保认证中间件先
执行。公开端点不会创建 `ctx.user`，读取时使用：

```python
user = getattr(request.ctx, "user", None)
```

## 安全限制

- 只允许 HS256，不能通过配置切换算法。
- 每个受保护请求都会查询数据库。
- 没有 Token 黑名单、注销吊销或刷新机制。
- 公开规则只看路径尾段，粒度较粗。

生产应用可重写中间件，使用明确的 `(HTTP 方法, 完整路径)` 白名单、可配置
算法、Token 吊销和适当的用户缓存。

## 下一步

- 阅读[认证](../../core/authentication.md)配置 Token 签发。
- 阅读[权限](../../core/permissions.md)控制用户访问范围。
- 阅读[限流](rate-limiting.md)保护认证接口。
