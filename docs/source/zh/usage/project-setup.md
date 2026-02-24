# 项目设置

本章介绍如何正确设置和配置一个 SRF 项目，包括项目结构、配置管理、数据库设置等。

## 推荐的项目结构

假定一个 SRF 项目结构如下：

```
myproject/
├── app.py                      # 应用入口
├── config.py                   # 配置文件
├── requirements.txt            # 依赖列表
├── .env                        # 环境变量
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── schemas/                    # Pydantic Schemas
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── viewsets/                   # ViewSets
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── routes.py                   # 路由配置
├── permissions.py              # 自定义权限类
├── filters.py                  # 自定义过滤器
├── middlewares.py              # 自定义中间件
├── utils/                      # 工具函数
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
└── tests/                      # 测试
    ├── __init__.py
    ├── test_products.py
    └── test_orders.py
```

## 配置管理

### 环境变量

创建 `.env` 文件来存储敏感信息：

```bash
# .env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite://db.sqlite3
REDIS_URL=redis://localhost:6379/0

# JWT 配置
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400

# 邮件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### 配置文件

创建 `config.py` 来管理配置：

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置"""
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT 配置
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    
    # 邮件配置
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    # 分页配置
    PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS 配置
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
    
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

# 根据环境变量选择配置
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
}

env = os.getenv("ENVIRONMENT", "development")
config = config_map[env]
```

### 应用配置

在 `app.py` 中应用配置：

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.config import srfconfig
from config import config

app = Sanic("MyApp")

# 应用配置到 Sanic
app.config.update_config(config)

# 配置 SRF
srfconfig.set_app(app)

# 配置数据库
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

## 数据库设置

### Tortoise ORM 配置

SRF 使用 Tortoise ORM 作为默认的 ORM 框架。

#### 基本配置

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### PostgreSQL 配置

```python
register_tortoise(
    app,
    db_url="postgres://user:password@localhost:5432/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### MySQL 配置

```python
register_tortoise(
    app,
    db_url="mysql://user:password@localhost:3306/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### 高级配置

```python
from tortoise.contrib.sanic import register_tortoise

register_tortoise(
    app,
    config={
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "postgres",
                    "password": "password",
                    "database": "mydb",
                    "minsize": 1,
                    "maxsize": 5,
                }
            }
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai"
    },
    generate_schemas=True,
)
```

### 数据库迁移

使用 Aerich 进行数据库迁移：

#### 安装 Aerich

```bash
pip install aerich
```

#### 初始化 Aerich

```bash
aerich init -t config.TORTOISE_ORM
```

#### 初始化数据库

```bash
aerich init-db
```

#### 创建迁移

```bash
aerich migrate --name "add_user_model"
```

#### 应用迁移

```bash
aerich upgrade
```

#### 回滚迁移

```bash
aerich downgrade
```

### 配置文件示例

创建 `config.py` 用于 Aerich：

```python
TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://db.sqlite3"
    },
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
```

## 认证设置

### JWT 配置

```python
from srf.auth.viewset import setup_auth

# 配置 JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    class_views=[
        ("/register", register),
        ("/send-verification-email", verify_email),
    ],
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)
```

### 社交登录配置

在配置文件中设置社交登录：

```python
class Config:
    SOCIAL_CONFIG = {
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": "http://localhost:8000/api/auth/social/callback",
        }
    }
```

### 公开端点配置

配置不需要认证的端点：

```python
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # 公开的产品列表
        "/health/",       # 健康检查
    ]
```

## 中间件设置

### 认证中间件

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    """认证中间件"""
    await set_user_to_request_ctx(request)
```

### 限流中间件

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    throttle_rate
)

# 创建存储
storage = MemoryStorage()

# 配置限流规则
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100次/分钟
    UserRateLimit(1000, 60, storage),   # 用户: 1000次/分钟
]

@app.middleware("request")
async def throttle_middleware(request):
    """限流中间件"""
    if not await throttle_rate(request):
        from sanic.response import json
        return json({"error": "请求过于频繁，请稍后再试"}, status=429)
```

### CORS 中间件

```python
from sanic_cors import CORS

# 配置 CORS
CORS(
    app,
    origins=config.CORS_ORIGINS,
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Range", "X-Content-Range"],
    supports_credentials=True,
)
```

## 路由设置

### 基本路由注册

创建 `routes.py`：

```python
from srf.route import SanicRouter
from viewsets.product import ProductViewSet
from viewsets.order import OrderViewSet
from viewsets.category import CategoryViewSet

def register_routes(app):
    """注册所有路由"""
    router = SanicRouter(prefix="api")
    
    # 注册 ViewSets
    router.register("products", ProductViewSet, name="products")
    router.register("orders", OrderViewSet, name="orders")
    router.register("categories", CategoryViewSet, name="categories")
    
    # 将路由添加到应用
    app.blueprint(router.get_blueprint())
```

在 `app.py` 中调用：

```python
from routes import register_routes

app = Sanic("MyApp")
# ... 其他配置 ...

# 注册路由
register_routes(app)
```

### 多版本 API

```python
from srf.route import SanicRouter

def register_routes(app):
    # v1 API
    router_v1 = SanicRouter(prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)
    app.blueprint(router_v1.get_blueprint())
    
    # v2 API
    router_v2 = SanicRouter(prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
    app.blueprint(router_v2.get_blueprint())
```

## 健康检查设置

```python
from srf.health.route import bp as health_bp

# 注册健康检查路由
app.blueprint(health_bp)

# 配置健康检查服务
@app.before_server_start
async def setup_health_checks(app, loop):
    """设置健康检查依赖的服务"""
    import aioredis
    
    # Redis 客户端
    app.ctx.redis = await aioredis.create_redis_pool(config.REDIS_URL)
    
    # PostgreSQL 连接池
    # app.ctx.pg = await asyncpg.create_pool(config.DATABASE_URL)
```

## 日志设置

```python
import logging
from sanic.log import logger

# 配置日志
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# 在代码中使用
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

## 异常处理

```python
from sanic.exceptions import NotFound, InvalidUsage
from srf.views.http_status import HTTPStatus
from sanic.response import json

@app.exception(NotFound)
async def handle_not_found(request, exception):
    """处理 404 错误"""
    return json(
        {"error": "资源未找到", "message": str(exception)},
        status=HTTPStatus.HTTP_404_NOT_FOUND
    )

@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    """处理 400 错误"""
    return json(
        {"error": "无效请求", "message": str(exception)},
        status=HTTPStatus.HTTP_400_BAD_REQUEST
    )

@app.exception(Exception)
async def handle_exception(request, exception):
    """处理未捕获的异常"""
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    return json(
        {"error": "服务器内部错误"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

## 完整的应用示例

`app.py`：

```python
from sanic import Sanic
from sanic_cors import CORS
from tortoise.contrib.sanic import register_tortoise
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.health.route import bp as health_bp
from config import config
from routes import register_routes
import logging

# 创建应用
app = Sanic("MyApp")

# 应用配置
app.config.update_config(config)
srfconfig.set_app(app)

# 配置 CORS
CORS(app, origins=config.CORS_ORIGINS)

# 配置日志
logging.basicConfig(level=logging.INFO)

# 注册数据库
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)

# 注册中间件
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)

# 注册路由
register_routes(app)
app.blueprint(health_bp)

# 异常处理
@app.exception(Exception)
async def handle_exception(request, exception):
    from sanic.response import json
    logging.error(f"Error: {exception}", exc_info=True)
    return json({"error": str(exception)}, status=500)

if __name__ == "__main__":
    app.run(
        host=config.get("HOST", "0.0.0.0"),
        port=config.get("PORT", 8000),
        debug=config.DEBUG,
        auto_reload=config.DEBUG,
    )
```

## 生产环境部署

### 使用 Gunicorn

```bash
pip install gunicorn
```

```bash
gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sanic.worker.GunicornWorker
```

### 使用 Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
```

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

运行：

```bash
docker-compose up -d
```

## 最佳实践

1. **使用环境变量**：不要在代码中硬编码敏感信息
2. **分离配置**：为不同环境创建不同的配置
3. **使用迁移**：通过迁移管理数据库变更
4. **日志记录**：记录重要操作和错误
5. **异常处理**：全局处理异常，返回友好的错误信息
6. **健康检查**：提供健康检查端点供监控系统使用
7. **限流保护**：防止 API 被滥用
8. **CORS 配置**：正确配置跨域访问

## 下一步

- 学习 [核心概念](core/viewsets.md) 深入了解 SRF 的功能
- 查看 [配置项](../config.md) 了解所有配置选项
- 阅读 [API 参考](../api-reference.md) 查看详细的 API 文档
