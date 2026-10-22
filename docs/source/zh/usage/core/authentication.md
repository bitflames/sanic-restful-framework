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
app.config.SECRET_KEY = "请从另一个安全的环境变量读取"
settings.set_app(app)
```

`JWT_SECRET` 用于 JWT 签名；`SECRET_KEY` 用于计算刷新令牌的 HMAC 摘要，数据库只保存摘要而不保存令牌原文。
请将二者设为不同的强随机密钥。升级前数据库中的明文刷新令牌以及更换 `SECRET_KEY` 后的旧令牌均无法通过校验，用户需要重新登录。

## 注册认证路由

推荐使用 `register_auth_urls()`。它会调用 `setup_auth()`，并注册认证、注册、
注销和验证邮件路由：

```python
from srf.auth.route import register_auth_urls

register_auth_urls(app, prefix="/api/auth")
```

`register_auth_urls()` 会从 `app.config` 读取并校验 `JWT_SECRET` 与 `SECRET_KEY`。

不要先调用 `setup_auth()` 再调用 `register_auth_urls()`，否则会重复初始化
`sanic-jwt`。

如需向 `setup_auth()` 传入 `sanic-jwt` 的其他初始化参数，可直接初始化：

```python
from srf.auth.viewset import setup_auth

jwt = setup_auth(
    app,
    url_prefix="/api/auth",
    # 其余关键字参数传给 sanic_jwt.Initialize
)
```

`setup_auth()` 已固定使用 SRF 自带的 `authenticate` 和 `retrieve_user`，不要再通过关键字传入这两个名称，否则会发生重复参数错误。
`setup_auth()` 不从关键字参数读取 JWT 密钥；缺少有效的 `app.config.JWT_SECRET` 或 `app.config.SECRET_KEY` 时会在初始化阶段抛出 `ServerError`。

## 登录

默认登录地址是 `POST /api/auth`。请求字段为 `account` 和 `password`，`account` 可以是邮箱或用户名：

```bash
# 邮箱登录
curl -X POST http://localhost:8000/api/auth \
  -H "Content-Type: application/json" \
  -d '{"account":"user@example.com","password":"password123"}'
```

响应（由 `sanic-jwt` 返回）：

```json
{
  "access_token": "******",
  "refresh_token": "******"
}
```

`authenticate()` 使用 `UserLoginSchema`（`account`、`password`），
查询 `srf.auth.models.User`、检查用户是否启用并验证密码，然后把 `user_id`、
`username` 和角色名称放入 JWT payload。

## 密码与 Token 的算法

SRF 的密码存储方式是 **bcrypt(SHA-256(密码))**：密码先按 UTF-8 编码并
计算 SHA-256 摘要，再由 bcrypt 使用随机 salt 生成密码哈希。登录时执行相同的
预处理，再用 `bcrypt.checkpw()` 校验。

## 认证中间件

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

携带 Token 时，请求头格式为：

```http
Authorization: Bearer <token>
```

中间件使用 HS256 和 `app.config.JWT_SECRET` 解码 Token，通过
`retrieve_user()` 查询用户，并设置 `request.ctx.user`。具体行为：

- 没有认证信息，或 Token 的签名/有效期校验失败时，`extract_payload()` 返回
  `None`，`request.ctx.user` 被设为 `None`，请求按匿名请求继续执行。此时是否
  拒绝由权限类决定（例如 `IsAuthenticated` 会返回 403）。
- `Authorization` 请求头格式错误（例如缺少 `Bearer` 前缀）、JWT 未初始化，
  或 Token 对应的用户不存在时，中间件抛出 `Unauthorized`（401）。

因此，需要 401 与 403 语义区分时，不要只依赖认证中间件；可在权限类或全局异常
处理器中统一处理。

## 获取当前用户

```python
from sanic.response import json
from srf.views import BaseViewSet


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

`register_auth_urls()` 注册以下常用 SRF 路由：

- `POST /api/auth/register`
- `POST /api/auth/verify_email`
- `POST /api/auth/logout`

邮箱验证码相关配置定义在 `srf.config.settings`：

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL` | `60` | 验证码有效期，单位为秒 |
| `USER_REGISTER_EMAIL_CODE` | `USER_REGISTER:EMAIL_CODE:{email}` | Redis 中验证码的 key 格式，`{email}` 会替换为邮箱地址 |
| `USER_REGISTER_EMAIL_CODE_TIMES` | `USER_REGISTER:EMAIL_CODE_TIMES:{email}` | Redis 中错误尝试次数的 key 格式 |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10` | 验证码允许的错误尝试次数上限 |

### 注册调用流程

```bash
# 1. 发送邮箱验证码（有效期内重复请求返回 429）
curl -X POST http://localhost:8000/api/auth/verify_email \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'

# 2. 查看邮件中的 6 位数字验证码，提交注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"zhangsan","password1":"Passw0rd123","password2":"Passw0rd123","confirmations":"123456"}'

# 3. 注册成功即返回 access_token / refresh_token，之后携带 Token 访问
curl http://localhost:8000/api/users/self \
  -H "Authorization: Bearer <access-token>"

# 4. 登出（撤销当前用户的 refresh token）
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <access-token>"
```

## 注册用户资源 API

`register_auth_urls()` 只注册认证流程路由，不会自动注册用户管理资源。需要用户资料及密码修改 API 时，可显式导入 `UserViewSet` 并通过 `SanicRouter` 注册：

```python
from srf.auth.viewset import UserViewSet
from srf.route import SanicRouter

user_router = SanicRouter(app, prefix="api")
user_router.register("users", UserViewSet, name="users")
```

该资源提供 `GET /api/users/self`、`POST /api/users/change-password`，以及 `/api/users` 的 CRUD 路由。普通用户只能访问自己的用户记录；超级用户可管理其他用户。修改密码请求体为：

```json
{"old_password": "old-password", "password1": "new-password", "password2": "new-password"}
```

修改成功后会撤销该用户已保存的 refresh token；已签发的 access token 在过期前仍可使用。

### 用户资源调用流程

```bash
# 1. 登录获取 Token（account 支持用户名或邮箱）
curl -X POST http://localhost:8000/api/auth \
  -H "Content-Type: application/json" \
  -d '{"account":"user@example.com","password":"Passw0rd123"}'

# 2. 查询自己的资料
curl http://localhost:8000/api/users/self \
  -H "Authorization: Bearer <access-token>"

# 3. 修改自己的资料
curl -X PATCH http://localhost:8000/api/users/<user-id> \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"username":"new-name"}'

# 4. 修改密码（成功后需重新登录）
curl -X POST http://localhost:8000/api/users/change-password \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"Passw0rd123","password1":"NewPassw0rd456","password2":"NewPassw0rd456"}'
```

## 安全注意事项

- 生产环境必须使用 HTTPS，并从密钥管理系统读取 `JWT_SECRET`。
- SRF 启用了 refresh token 持久化；登出会撤销当前用户的 refresh token，但已签发的 access token 在过期前仍有效。
- GitHub OAuth 是可选认证功能，配置和接入见[社交登录教程](social-login.md)。
