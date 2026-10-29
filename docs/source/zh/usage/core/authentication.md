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

推荐使用 `register_all_auth_urls()`：一次性完成 JWT 初始化并注册登录、注册、
注销、邮件验证和 GitHub 社交登录路由：

```python
from srf.auth.route import register_all_auth_urls

register_all_auth_urls(app, prefix="/api/auth")
```

JWT 初始化会从 `app.config` 读取并校验 `JWT_SECRET` 与 `SECRET_KEY`，缺失时抛出
`ServerError`。

只需其中一部分时，可以按需组合三个细粒度函数：

| 函数                                          | 注册的端点                                                                                            |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `register_jwt_urls(app, prefix)`              | `POST {prefix}/login`、`GET {prefix}/me`、`GET {prefix}/verify`、`POST {prefix}/refresh`（sanic-jwt） |
| `register_auth_urls(instance, prefix)`        | `POST {prefix}/register`、`POST {prefix}/verify_email`、`POST {prefix}/logout`                        |
| `register_social_auth_urls(instance, prefix)` | GitHub OAuth 三个端点                                                                                 |

注意：

- `register_jwt_urls()` 只接受 Sanic 应用实例。在 Blueprint 上初始化 sanic-jwt 会把
  `ctx.auth` 挂到 Blueprint 上，认证中间件读取的是 `request.app.ctx.auth`，会找不到。
- 这三个函数都不转发 `sanic_jwt.Initialize` 的关键字参数。如需自定义 sanic-jwt 行为
  （例如 `leeway`、`claim_iss`），请直接调用 `sanic_jwt.Initialize`。

## 登录

默认登录地址是 `POST /api/auth/login`。请求字段为 `account` 和 `password`，`account` 可以是邮箱或用户名：

```bash
# 邮箱登录
curl -X POST http://localhost:8000/api/auth/login \
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
查询 `srf.auth.models.User`、检查用户是否启用并验证密码。sanic-jwt 的 `build_payload()` 只会把 `user_id` 写入 access token（另加 `exp`）；
`username` 和角色名称由 `retrieve_user()` 在 `/me` 或 refresh 时返回，不会写进 token。

## 刷新令牌

access token 过期后，携带 access token（过期也可以）和 refresh token 换取新的
access token：

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

响应只包含新的 `access_token`；sanic-jwt 不会轮换 refresh token。refresh token 以
HMAC 摘要形式持久化，绝对有效期为 `JWT_REFRESH_TOKEN_EXPIRES`（默认 30 天），过期或
登出后必须重新登录。

另外两个 sanic-jwt 端点：`GET /api/auth/me` 返回当前用户信息（`{"me": {...}}`），
`GET /api/auth/verify` 校验令牌有效性。两者都受保护：缺失或失效的
`Authorization: Bearer` 头会返回 401。

## 密码与 Token 的算法

SRF 的密码存储方式是 **bcrypt(SHA-256(密码))**：密码先按 UTF-8 编码并
计算 SHA-256 摘要，再由 bcrypt 使用随机 salt 生成密码哈希。登录时执行相同的
预处理，再用 `bcrypt.checkpw()` 校验。

## 认证中间件

SRF 提供独立的请求中间件 `set_user_to_request_ctx`：校验 `Authorization: Bearer`
Token 并把用户写入 `request.ctx.user`。默认（`strict=False`）为可选认证——未携带
Token 的请求回退为 `AnonymousUser`，出示了无效 Token 则返回 401；`strict=True`
为强制认证。配置示例、白名单过滤与请求流程见
[认证中间件](../advanced/middleware/auth-middleware.md)。

由此 401（认证失败，来自中间件）与 403（授权失败，来自 `IsAuthenticated` 等权限类）的语义清晰分离。

## 获取当前用户

```python
from sanic.response import json
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        user = self.get_current_user(request)
        if user is None or getattr(user, "is_anonymous", False):
            return json({"error": "未登录"}, status=401)
        # ...
```

`get_current_user()` 优先返回 `request.ctx.user`，不存在时尝试
`request.auth`。

## 注册和邮箱验证码

`register_all_auth_urls()` 注册以下认证路由（除 sanic-jwt 的四个 JWT 端点外）：

- `POST /api/auth/register`
- `POST /api/auth/verify_email`
- `POST /api/auth/logout`

`register` 成功后会直接签发 token，因此应用必须已经调用 `register_jwt_urls()`（或 `register_all_auth_urls()`）。未配置 JWT 时接口返回 500，且不会消费验证码。

验证码错误次数达到 `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` 后，验证码会被删除，接口返回 429（`TooManyRequest`），需要重新获取验证码。

邮箱验证码相关配置定义在 `srf.config.settings`：

| 配置项                                 | 默认值                                   | 用途                                                  |
| -------------------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL`  | `60`                                     | 验证码有效期，单位为秒                                |
| `USER_REGISTER_EMAIL_CODE`             | `USER_REGISTER:EMAIL_CODE:{email}`       | Redis 中验证码的 key 格式，`{email}` 会替换为邮箱地址 |
| `USER_REGISTER_EMAIL_CODE_TIMES`       | `USER_REGISTER:EMAIL_CODE_TIMES:{email}` | Redis 中错误尝试次数的 key 格式                       |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10`                                     | 验证码允许的错误尝试次数上限                          |

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

`register_all_auth_urls()` 只注册认证流程路由，不会自动注册用户管理资源。需要用户资料及密码修改 API 时，可显式导入 `UserViewSet` 并通过 `SanicRouter` 注册：

```python
from srf.auth.viewset import UserViewSet
from srf.route import SanicRouter

user_router = SanicRouter(app, prefix="api")
user_router.register("users", UserViewSet, name="users")
```

该资源提供 `GET /api/users/self`、`POST /api/users/change-password`、`POST /api/users/<user-id>/reset-password`（仅超级用户），以及 `/api/users` 等等 CRUD 路由。普通用户只能访问自己的用户记录；超级用户可管理其他用户。修改密码请求体为：

```json
{
  "old_password": "old-password",
  "password1": "new-password",
  "password2": "new-password"
}
```

修改成功后会撤销该用户已保存的 refresh token；已签发的 access token 在过期前仍可使用。

更新接口（PUT/PATCH `/api/users/<user-id>`）；提交 `email`、`password`、`password1` 或 `password2` 都会返回 400。修改邮箱暂不通过该接口提供；密码修改只走两个专用接口：`change-password` 自助改密（校验旧密码）；`reset-password` 超管重置

### 用户资源调用流程

```bash
# 1. 登录获取 Token（account 支持用户名或邮箱）
curl -X POST http://localhost:8000/api/auth/login \
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
