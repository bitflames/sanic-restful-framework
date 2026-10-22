# 配置

SRF 使用 `srf.config.settings`（`LazySettings`）读取配置。查找顺序为：

1. 最近一次通过 `settings.set_app(app)` 绑定的 `app.config`
2. `srf.config.settings` 模块中的大写默认值

## 初始化

请在 Sanic 配置中设置：

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
settings.set_app(app)
```

`LazySettings` 是进程级单例。多应用共用一个进程时，后一次 `set_app()` 会影响
所有通过 `settings` 读取配置的代码。

## 默认配置

以下配置项定义在 `srf/config/settings.py`，以源码为准。

### 分页 / 过滤 / 权限

ViewSet 未声明对应类属性时使用的默认值。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `PAGINATION_CLASS` | `PageNumberPagination` | 默认分页类 |
| `DEFAULT_FILTERS` | `[SearchFilter, QueryParamFilter, OrderingFactory]` | 默认过滤器链 |
| `DEFAULT_PERMISSION_CLASSES` | `(AllowAny,)` | 默认权限类 |

### 序列化与缓存

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `BASE_DIR` | `os.getcwd()` | 项目根目录（进程工作目录） |
| `CACHE_ROOT` | `BASE_DIR/.diskcache` | 缓存目录 |
| `DATETIME_FORMAT` | `"%Y-%m-%d %H:%M:%S"` | 时间字符串模板 |
| `JSON_ENCODER` | `custom_dumps` | JSON 序列化函数（处理 `datetime` / `Exception`），需应用自行接入 Sanic |

### 健康检查与限流

健康检查路由实际读取 `app.config.HEALTH_CHECK_LIST`：

```python
from srf.health.checks import RedisCheck

app.config.HEALTH_CHECK_LIST = [RedisCheck]
app.ctx.redis = redis_client
```

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `HEALTH_CHECK_LIST` | `[]` | 健康检查类列表 |
| `REQUEST_LIMITERS` | `[]` | 限流器列表，`throttle_rate()` 从 `app.config.REQUEST_LIMITERS` 读取 |
| `THROTTLE_REDIS_PREFIX` | `"throttle"` | 限流 Redis 键前缀（`RedisStorage`） |

### 邮件

`srf.tools.email.send_email()` 直接读取 `srf.config.settings.EmailConfig`，
各属性在模块导入时从环境变量读取，后续修改 `app.config` 不会改变邮件配置。

| 属性 | 环境变量 | 说明 |
| --- | --- | --- |
| `EmailConfig.from_email` | `FROM_EMAIL` | 发件人地址 |
| `EmailConfig.smtp_server` | `SMTP_SERVER` | SMTP 服务器 |
| `EmailConfig.smtp_port` | `SMTP_PORT` | SMTP 端口 |
| `EmailConfig.password` | `PASSWORD` | 邮箱密码 / 授权码 |

### 社交登录

GitHub OAuth 的使用教程见[社交登录](usage/core/social-login.md)。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `SOCIAL_CONFIG` | GitHub OAuth 配置字典 | 各字段从 `GITHUB_CLIENT_ID` 等环境变量读取 |
| `SOCIAL_LOGIN_COOKIE_KEY` | `"oauth_state"` | OAuth state 的 Cookie 名 |
| `SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE` | `600` | state Cookie 有效期（秒） |

### 注册验证码与密码

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `MIN_PASSWORD_LENGTH` | `8` | 密码最小长度 |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL` | `60` | 验证码有效期（秒） |
| `USER_REGISTER_EMAIL_CODE` | `"USER_REGISTER:EMAIL_CODE:{email}"` | 验证码 Redis 键模板 |
| `USER_REGISTER_EMAIL_CODE_TIMES` | `"USER_REGISTER:EMAIL_CODE_TIMES:{email}"` | 失败次数 Redis 键模板 |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10` | 验证码失败次数上限 |

### JWT

`JWT_SECRET`（签名密钥）与 `SECRET_KEY`（刷新令牌摘要密钥）无默认值，必须在
`app.config` 中显式设置。`setup_auth()` 会将 `JWT_ACCESS_TOKEN_EXPIRES` 换算为
秒并传给 `sanic-jwt`。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `JWT_ACCESS_TOKEN_EXPIRES` | `timedelta(hours=24)` | 访问令牌有效期 |
| `JWT_REFRESH_TOKEN_EXPIRES` | `timedelta(days=30)` | 刷新令牌有效期 |

## 最佳实践

1. **分离敏感信息**：使用环境变量存储密钥和密码
2. **多环境配置**：为开发、测试、生产环境创建不同配置
3. **使用 .env 文件**：便于本地开发
4. **不要提交 .env**：将 `.env` 添加到 `.gitignore`
5. **提供默认值**：使用 `os.getenv()` 的第二个参数提供默认值
6. **验证配置**：应用启动时验证必需的配置项（如 `JWT_SECRET`）
7. **文档化配置**：在 README 中说明所有配置项

## 下一步

- 阅读[认证](usage/core/authentication.md)配置 JWT。
- 阅读[项目搭建](usage/project-setup.md)查看完整应用结构。
