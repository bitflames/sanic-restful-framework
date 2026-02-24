# 配置项

SRF 提供了灵活的配置系统，允许您自定义框架的行为。

## 配置系统

SRF 使用 `SrfConfig` 单例类管理配置，配置优先级：

1. **应用配置** (`app.config`): 最高优先级
2. **模块配置** (`srf.config.settings`): 默认配置

### 设置配置

```python
from sanic import Sanic
from srf.config import srfconfig

app = Sanic("MyApp")

# 方法1：直接在 app.config 中设置
app.config.SECRET_KEY = "your-secret-key"
app.config.JWT_SECRET = "your-jwt-secret"

# 方法2：使用配置类
class Config:
    SECRET_KEY = "your-secret-key"
    JWT_SECRET = "your-jwt-secret"

app.config.update_config(Config)

# 无论使用哪种方法对app进行更新，最后都应用配置到 SRF
srfconfig.set_app(app)
```

## 核心配置

### SECRET_KEY

**类型**: `str`  
**必需**: 是  
**说明**: 应用密钥，用于加密和签名

```python
SECRET_KEY = "your-secret-key-keep-it-secret"
```

**推荐做法**：
- 从环境变量读取
- 使用足够长且随机的字符串
- 不要提交到版本控制

```python
import os
SECRET_KEY = os.getenv("SECRET_KEY")
```

## JWT 配置

### JWT_SECRET

**类型**: `str`  
**默认值**: `SECRET_KEY`  
**说明**: JWT Token 签名密钥

```python
JWT_SECRET = "your-jwt-secret"
```

### JWT_ACCESS_TOKEN_EXPIRES

**类型**: `int`  
**默认值**: `86400` (24小时)  
**单位**: 秒  
**说明**: Access Token 过期时间

```python
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1小时
```

## 认证配置

### NON_AUTH_ENDPOINTS

**类型**: `list[str]`  
**默认值**: `[]`  
**说明**: 不需要认证的端点列表

```python
NON_AUTH_ENDPOINTS = [
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/send-verification-email",
    "/api/products",  # 公开的产品列表
    "/health/",
]
```

**匹配规则**：
- 精确匹配：`/api/auth/login`
- 前缀匹配：`/api/public/` 匹配所有以此开头的路径

## 日期时间配置

### DATETIME_FORMAT

**类型**: `str`  
**默认值**: `"%Y-%m-%d %H:%M:%S"`  
**说明**: 日期时间格式化字符串

```python
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
```

**示例**：
- `"%Y-%m-%d"`: `2026-02-07`
- `"%Y-%m-%d %H:%M:%S"`: `2026-02-07 10:30:45`
- `"%Y/%m/%d %H:%M"`: `2026/02/07 10:30`

## 过滤器配置

### DEFAULT_FILTERS

**类型**: `list`  
**默认值**: `[SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory]`  
**说明**: 默认使用的过滤器类列表

```python
from srf.filters.filter import (
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory
)

DEFAULT_FILTERS = [
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory,
]
```

**自定义**：

```python
from filters import CustomFilter

DEFAULT_FILTERS = [
    SearchFilter,
    QueryParamFilter,
    CustomFilter,  # 添加自定义过滤器
]
```

## 社交登录配置

### SOCIAL_CONFIG

**类型**: `dict`  
**说明**: 社交登录配置

```python
SOCIAL_CONFIG = {
    "github": {
        "client_id": "your-github-client-id",
        "client_secret": "your-github-client-secret",
        "redirect_uri": "http://localhost:8000/api/auth/social/callback",
    }
}
```

**从环境变量读取**：

```python
import os

SOCIAL_CONFIG = {
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/social/callback"),
    }
}
```

## 邮件配置

### EmailConfig

**类型**: `class`  
**说明**: 邮件发送配置

```python
class EmailConfig:
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "your-email@gmail.com"
    SMTP_PASSWORD = "your-password"
    SMTP_FROM = "your-email@gmail.com"
    SMTP_USE_TLS = True
```

**从环境变量读取**：

```python
import os

class EmailConfig:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
```

## 缓存配置

### CACHES

**类型**: `dict`  
**说明**: 缓存配置

```python
CACHES = {
    "default": {
        "backend": "redis",
        "location": "redis://localhost:6379/0",
    }
}
```

**Redis 配置**：

```python
CACHES = {
    "default": {
        "backend": "redis",
        "location": "redis://localhost:6379/0",
        "options": {
            "maxsize": 10,
            "minsize": 1,
        }
    }
}
```

## 完整配置示例

### config.py

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置"""
    # 核心配置
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = False
    
    # JWT 配置
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    
    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    
    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 认证配置
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/auth/social/",
        "/api/public/",
        "/health/",
    ]
    
    # 日期时间格式
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 过滤器配置
    from srf.filters.filter import (
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory
    )
    DEFAULT_FILTERS = [
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
    
    # 社交登录配置
    SOCIAL_CONFIG = {
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": os.getenv(
                "GITHUB_REDIRECT_URI",
                "http://localhost:8000/api/auth/social/callback"
            ),
        }
    }
    
    # 邮件配置
    class EmailConfig:
        SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
        SMTP_USE_TLS = True
    
    # 缓存配置
    CACHES = {
        "default": {
            "backend": "redis",
            "location": REDIS_URL,
        }
    }
    
    # 分页配置
    PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS 配置
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # 限流配置
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_PER_MINUTE = 60

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    DATABASE_URL = "sqlite://db_dev.sqlite3"

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL")

class TestConfig(Config):
    """测试环境配置"""
    TESTING = True
    DATABASE_URL = "sqlite://:memory:"

# 根据环境选择配置
env = os.getenv("ENVIRONMENT", "development")
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
}
config = config_map[env]
```

### .env

```bash
# 核心配置
SECRET_KEY=your-secret-key-keep-it-secret
ENVIRONMENT=development

# JWT 配置
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/social/callback

# 邮件
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### app.py

```python
from sanic import Sanic
from srf.config import srfconfig
from config import config

app = Sanic("MyApp")

# 应用配置
app.config.update_config(config)
srfconfig.set_app(app)

# 访问配置
print(f"Environment: {config.__name__}")
print(f"Debug: {app.config.DEBUG}")
print(f"Database: {app.config.DATABASE_URL}")
```

## 访问配置

### 在代码中访问

```python
from srf.config import srfconfig

# 访问配置值
secret_key = srfconfig.SECRET_KEY
jwt_secret = srfconfig.JWT_SECRET
non_auth_endpoints = srfconfig.NON_AUTH_ENDPOINTS
```

### 在 ViewSet 中访问

```python
from srf.views import BaseViewSet
from srf.config import srfconfig

class ProductViewSet(BaseViewSet):
    def __init__(self):
        super().__init__()
        # 访问配置
        self.page_size = getattr(srfconfig, 'PAGE_SIZE', 20)
```

## 环境变量

推荐使用环境变量管理敏感配置：

### 使用 python-dotenv

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 读取环境变量
SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
```

### Docker 环境变量

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
```

## 最佳实践

1. **分离敏感信息**：使用环境变量存储密钥和密码
2. **多环境配置**：为开发、测试、生产环境创建不同配置
3. **使用 .env 文件**：便于本地开发
4. **不要提交 .env**：将 `.env` 添加到 `.gitignore`
5. **提供默认值**：使用 `os.getenv()` 的第二个参数提供默认值
6. **验证配置**：应用启动时验证必需的配置项
7. **文档化配置**：在 README 中说明所有配置项

## 配置验证

```python
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY is required")
        
        if len(cls.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")

# 在应用启动时验证
@app.before_server_start
async def validate_config(app, loop):
    Config.validate()
```

## 下一步

- 查看 [项目设置](usage/project-setup.md) 了解完整的项目配置
- 阅读 [认证](usage/core/authentication.md) 了解认证配置
- 浏览 [API 参考](api-reference.md) 了解配置 API
