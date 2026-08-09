# 认证

SRF 通过 `sanic-jwt` 提供登录和 Token 生成，并提供一个独立的请求中间件来
校验 Bearer Token、加载用户并写入 `request.ctx.user`。

## 前置条件

启用 JWT 前，在 Sanic 配置中设置 `JWT_SECRET`（不再要求导入前设置
`SECRET_KEY` 环境变量）：

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = "请从安全的环境变量读取"
settings.set_app(app)
```

## 注册认证路由

推荐使用 `register_auth_urls()`。它会调用 `setup_auth()`，并注册注册、注销、
验证邮件和 GitHub 登录相关路由：

```python
from srf.auth.route import register_auth_urls

register_auth_urls(app, prefix="/api/auth")
```

`register_auth_urls()` 内部使用 `secret=app.config.JWT_SECRET`，请确保已设置。

不要先调用 `setup_auth()` 再调用 `register_auth_urls()`，否则会重复初始化
`sanic-jwt`。

如果只需要 `sanic-jwt` 登录端点，可直接初始化：

```python
from srf.auth.viewset import setup_auth

jwt = setup_auth(
    app,
    secret=app.config.JWT_SECRET,
    url_prefix="/api/auth",
    login_path="login",
    # 其余关键字参数传给 sanic_jwt.Initialize
)
app.ctx.jwt = jwt  # register_auth_urls() 也会这样挂载
```

`setup_auth()` 已固定使用 SRF 自带的 `authenticate` 和 `retrieve_user`，不要再
通过关键字传入这两个名称，否则会发生重复参数错误。`secret` 缺失时抛出
`ServerError("secret is required")`。

## 登录

默认登录地址是 `POST /api/auth/login`。支持邮箱或用户名：

```bash
# 邮箱登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

`authenticate()` 使用 `UserLoginSchema`（`email` / `username` 至少一个），
查询 `srf.auth.models.User`、检查用户是否启用并验证密码，然后把 `user_id`、
`username` 和角色名称放入 JWT payload。

## 认证中间件

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

受保护请求必须携带：

```http
Authorization: Bearer <token>
```

中间件使用 HS256 和 `app.config.JWT_SECRET` 解码 Token，通过
`retrieve_user()` 查询用户，并设置 `request.ctx.user`。Token 缺失、格式错误、
过期、无效或用户不存在时返回 401。

## 公开端点

`NON_AUTH_ENDPOINTS` 存放的是路径最后一段，不是完整 URL：

```python
app.config.NON_AUTH_ENDPOINTS = (
    "login",
    "register",
    "send-verification-email",
    "health",
    ...
)
```

例如 `"products"` 会同时豁免 `/api/products` 和
`/admin/products`。它不支持前缀匹配，也不能区分 HTTP 方法。对安全要求较高
的应用，建议修改中间件，使用明确的 `(method, path)` 规则。

## 获取当前用户

```python
class ProductViewSet(BaseViewSet):
    async def create(self, request):
        user = self.get_current_user(request)
        if user is None:
            return json({"error": "未登录"}, status=401)
        # ...
```

`get_current_user()` 优先返回 `request.ctx.user`，不存在时尝试
`request.auth`。

## 注册和邮箱验证码

`register_auth_urls()` 注册以下端点：

- `POST /api/auth/register`
- `POST /api/auth/send-verification-email`
- `POST /api/auth/logout`
- `GET /api/auth/social/github/login`
- `GET /api/auth/social/callback`
- `GET /api/auth/social/github/login_by_code`

注册与验证邮件依赖：

- `request.app.ctx.redis`
- `settings.EMAIL_CODE_REDIS`（或 `app.config.EMAIL_CODE_REDIS`），默认 `"EMAIL_CODE"`；
  Redis key 形如 `EMAIL_CODE_{email}`
- `FROM_EMAIL`、`SMTP_SERVER`、`SMTP_PORT`、`PASSWORD` 环境变量

发送邮件相关 API：

```python
from srf.tools.email import send_email, send_verify_code

# 发送邮件：同步 SMTP（不要在事件循环里长时间直接调用）
ok = send_email(
    to_email="user@example.com",
    subject="验证码",
    content="您的验证码是：12345",
)

# 注册验证码专用：固定主题/正文，内部 asyncio.to_thread 调用 send_email
ok = await send_verify_code("user@example.com", "12345")
```

## 安全注意事项

- 生产环境必须使用 HTTPS，并从密钥管理系统读取 `JWT_SECRET`。
- 默认代码没有刷新 Token 和真正的注销/吊销机制。
- GitHub OAuth 使用随机 `state` 和带时间戳的 HMAC 签名 Cookie 防止篡改，
  回调时还会进行常量时间比较。
