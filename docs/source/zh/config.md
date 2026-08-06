# 配置

SRF 使用 `srf.config.settings`（`LazySettings`）读取配置。查找顺序为：

1. 最近一次通过 `settings.set_app(app)` 绑定的 `app.config`
2. `srf.config.settings` 模块中的大写默认值


## 初始化

`SECRET_KEY` / `JWT_SECRET` **不再**在导入 SRF 时强制读取。启用 JWT 认证时，
请在 Sanic 配置中自行设置，并传给 `setup_auth(..., secret=...)`：

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = "请从安全的环境变量读取"
app.config.NON_AUTH_ENDPOINTS = ("login", "health")
settings.set_app(app)
```

`LazySettings` 是进程级单例。多应用共用一个进程时，后一次 `set_app()` 会影响
所有通过 `settings` 读取配置的代码。

## 默认配置

### 核心与 JWT

| 名称 | 默认值 | 当前用途 |
|---|---|---|
| `JWT_SECRET` | 无（需应用设置） | JWT 签名、认证中间件、OAuth state 回退密钥 |
| `JWT_ACCESS_TOKEN_EXPIRES` | `timedelta(hours=24)` | 仅定义；`setup_auth()` 当前未自动读取 |

如需控制 `sanic-jwt` 的过期设置，请把该库支持的参数直接传给
`setup_auth()`，不要假设 `JWT_ACCESS_TOKEN_EXPIRES` 会自动生效。

### 认证豁免

`NON_AUTH_ENDPOINTS` 是 URL **最后一段**的集合：

```python
NON_AUTH_ENDPOINTS = (
    "register",
    "login",
    "send-verification-email",
    "health",
    ...
)
```

它不支持完整路径或前缀规则。例如 `"products"` 会同时匹配
`/api/products` 和 `/admin/products`。

### 过滤器

```python
from srf.filters.filter import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)

DEFAULT_FILTERS = [
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory,
]
```

每个 `GenericAPIView` / `BaseViewSet` 实例初始化时，若类上未声明
`filter_class`，则使用 `settings.DEFAULT_FILTERS`。

### 分页

`PAGINATION_CLASS = PageNumberPagination` 虽已定义，但内置 `list()` 当前没有
读取它，而是直接使用 `PageNumberPagination`。当前也没有全局 `PAGE_SIZE`、
`MAX_PAGE_SIZE` 配置；默认值在分页类中。

### 限流

```python
REQUEST_LIMITERS = []  # 默认不限流；由应用设置为限流器实例列表
```

`throttle_rate()` 读取 `app.config.REQUEST_LIMITERS`（缺失时视为 `[]`）。

### 健康检查

`HEALTH_CHECK_LIST` 默认为空列表。健康检查路由实际读取
`app.config.HEALTH_CHECK_LIST`：

```python
from srf.health.checks import RedisCheck

app.config.HEALTH_CHECK_LIST = [RedisCheck]
app.ctx.redis = redis_client
```

### JSON 编码

`DATETIME_FORMAT` 默认为 `"%Y-%m-%d %H:%M:%S"`。
`JSON_ENCODER` 指向 `custom_dumps()`，可序列化 `datetime` 和异常对象。
是否使用该编码器取决于应用如何接入 Sanic 配置；SRF 不会自动安装它。

### 邮件

`srf.tools.email.send_email()` 直接读取 `srf.config.settings.EmailConfig`：

| 属性 | 环境变量 |
|---|---|
| `from_email` | `FROM_EMAIL` |
| `smtp_server` | `SMTP_SERVER` |
| `smtp_port` | `SMTP_PORT` |
| `password` | `PASSWORD` |

这些值在模块导入时读取，后续修改 `app.config` 不会改变邮件配置。
端口判断使用 `int(smtp_port) == 465` 选择 SSL。

### GitHub OAuth

```python
SOCIAL_CONFIG = {
    "github": {
        "CLIENT_ID": ...,
        "CLIENT_SECRET": ...,
        "REDIRECT_URI": ...,
        ...
    }
}

```

默认值来自对应的大写环境变量。可以在绑定应用前通过
`app.config.SOCIAL_CONFIG` 整体覆盖。

## 完整示例

```python
import os

from sanic import Sanic
from srf.config import srfconfig

app = Sanic("MyApp")
app.config.update(
    {
        "JWT_SECRET": os.environ["SECRET_KEY"],
        "NON_AUTH_ENDPOINTS": ("login", "register", "health"),
        "HEALTH_CHECK_LIST": [],
    }
)
settings.set_app(app)
```

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
