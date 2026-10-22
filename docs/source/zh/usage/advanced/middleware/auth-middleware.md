# 认证中间件

认证中间件从请求中读取 JWT，并把数据库中的用户对象写入
`request.ctx.user`。没有认证信息时，`request.ctx.user` 会设为 `None`，请求仍可继续；
权限类可据此区分匿名用户和已认证用户。

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

1. 从 `request.app.ctx.auth` 提取 JWT payload。
2. 没有 payload 时，将 `request.ctx.user` 设为 `None` 并继续处理请求。
3. 有 payload 时，调用 `retrieve_user(request, payload)` 加载用户，并将 ORM 用户放到
   `request.ctx.user`。

`Authorization` 请求头格式错误、未初始化 JWT 或 Token 对应的用户不存在时返回 401；
Token 缺失，或签名/有效期校验失败时 payload 为 `None`，请求按匿名请求继续执行
（`request.ctx.user` 为 `None`），是否拒绝由权限类决定。

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

await authenticate_request(request)
user = request.ctx.user
```

### set_user_to_request_ctx

该函数调用 `authenticate_request(request)`，可直接用于应用 middleware。没有认证信息时，
`request.ctx.user` 为 `None`；携带有效 Token 时则为对应的 ORM 用户。

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
