# 其他功能

SRF 提供了许多实用的高级功能，帮助您构建更健壮和功能完善的 API 服务。

## 功能概览

本章节涵盖以下高级功能：

### 运维相关

- **[健康检查](health-check.md)**: 监控应用和依赖服务的健康状态
- **[异常处理](exceptions.md)**: 统一的异常处理机制
- **[HTTP 状态码](http-status.md)**: 标准化的状态码管理

### 中间件

- **[认证中间件](middleware/auth-middleware.md)**: 自动处理用户身份验证
- **[CSRF 中间件](middleware/csrf-middleware.md)**: 防止跨站请求伪造攻击
- **[限流中间件](middleware/rate-limiting.md)**: 防止 API 滥用，控制请求频率

## 快速导航

### 健康检查

监控应用和依赖服务（Redis、PostgreSQL、MongoDB 等）的健康状态：

```python
from srf.health.route import bp as health_bp

app.blueprint(health_bp)

# 访问 /health/ 查看健康状态
```

### 异常处理

SRF 提供了统一的异常处理机制，自动将异常转换为标准的 HTTP 响应：

```python
from srf.exceptions import TargetObjectAlreadyExist

# 抛出自定义异常
if await Product.filter(sku=sku).exists():
    raise TargetObjectAlreadyExist("该 SKU 已存在")
```

### HTTP 状态码

使用语义化的状态码常量：

```python
from srf.views.http_status import HTTPStatus
from sanic.response import json

return json(data, status=HTTPStatus.HTTP_201_CREATED)
```

### 认证中间件

自动验证 JWT Token 并设置用户上下文：

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

### 限流中间件

控制 API 请求频率，防止滥用：

```python
from srf.middleware.throttlemiddleware import IPRateLimit, MemoryStorage

storage = MemoryStorage()
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),  # 100 requests per 60 seconds
]
```

### CSRF 保护

防止跨站请求伪造攻击（开发中）。

## 使用建议

### 生产环境必备

以下功能在生产环境中强烈推荐使用：

1. **健康检查**: 集成到监控系统，实时了解服务状态
2. **限流中间件**: 防止恶意请求和 DDoS 攻击
3. **异常处理**: 提供友好的错误信息，不暴露内部细节
4. **认证中间件**: 自动处理用户身份验证

### 开发环境辅助

以下功能在开发环境中有助于调试：

1. **HTTP 状态码**: 使用语义化常量，代码更易读
2. **异常处理**: 快速定位问题，提供详细错误信息

## 功能组合示例

### 完整的生产环境配置

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.middleware.throttlemiddleware import IPRateLimit, UserRateLimit, MemoryStorage, throttle_rate
from srf.health.route import bp as health_bp
from srf.views.http_status import HTTPStatus
from sanic.response import json
from sanic.exceptions import NotFound, Forbidden, Unauthorized

app = Sanic("ProductionApp")
srfconfig.set_app(app)

# 1. 配置限流
storage = MemoryStorage()
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100次/分钟
    UserRateLimit(1000, 60, storage),   # 用户: 1000次/分钟
]

# 2. 注册中间件
@app.middleware("request")
async def auth_middleware(request):
    """认证中间件"""
    await set_user_to_request_ctx(request)

@app.middleware("request")
async def throttle_middleware(request):
    """限流中间件"""
    if not await throttle_rate(request):
        return json({"error": "请求过于频繁"}, status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)

# 3. 注册健康检查
app.blueprint(health_bp)

# 4. 统一异常处理
@app.exception(NotFound)
async def handle_not_found(request, exception):
    return json(
        {"error": "资源未找到", "message": str(exception)},
        status=HTTPStatus.HTTP_404_NOT_FOUND
    )

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    return json(
        {"error": "权限不足", "message": str(exception)},
        status=HTTPStatus.HTTP_403_FORBIDDEN
    )

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    return json(
        {"error": "未授权", "message": "请先登录"},
        status=HTTPStatus.HTTP_401_UNAUTHORIZED
    )

@app.exception(Exception)
async def handle_exception(request, exception):
    import logging
    logging.error(f"Unhandled exception: {exception}", exc_info=True)
    return json(
        {"error": "服务器内部错误"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

## 监控和日志

### 日志配置

```python
import logging
from sanic.log import logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# 在代码中使用
logger.info("Application started")
logger.error("Error occurred", exc_info=True)
```

### 请求日志中间件

```python
@app.middleware("request")
async def log_request(request):
    """记录请求信息"""
    logger.info(f"{request.method} {request.path} from {request.ip}")

@app.middleware("response")
async def log_response(request, response):
    """记录响应信息"""
    logger.info(f"{request.method} {request.path} -> {response.status}")
```

### 性能监控

```python
import time

@app.middleware("request")
async def add_start_time(request):
    """添加请求开始时间"""
    request.ctx.start_time = time.time()

@app.middleware("response")
async def add_process_time(request, response):
    """计算处理时间"""
    if hasattr(request.ctx, 'start_time'):
        process_time = time.time() - request.ctx.start_time
        response.headers['X-Process-Time'] = str(process_time)
```

## 安全最佳实践

### 1. 使用 HTTPS

生产环境必须使用 HTTPS：

```python
# 配置 SSL
app.run(
    host="0.0.0.0",
    port=443,
    ssl={
        'cert': '/path/to/cert.pem',
        'key': '/path/to/key.pem'
    }
)
```

### 2. 限制请求大小

```python
app.config.REQUEST_MAX_SIZE = 10 * 1024 * 1024  # 10MB
```

### 3. 设置超时

```python
app.config.REQUEST_TIMEOUT = 60  # 60秒
app.config.RESPONSE_TIMEOUT = 60
```

### 4. 隐藏敏感信息

```python
# 不要在生产环境开启 debug
app.run(host="0.0.0.0", port=8000, debug=False)

# 不要在错误响应中暴露详细的堆栈信息
@app.exception(Exception)
async def handle_exception(request, exception):
    # 记录详细错误到日志
    logger.error(f"Error: {exception}", exc_info=True)

    # 只返回通用错误给客户端
    return json({"error": "服务器内部错误"}, status=500)
```

### 5. 验证输入

```python
from pydantic import BaseModel, validator

class ProductSchema(BaseModel):
    name: str
    price: float

    @validator('price')
    def validate_price(cls, value):
        if value <= 0:
            raise ValueError('价格必须大于0')
        if value > 1000000:
            raise ValueError('价格不能超过100万')
        return value
```

## 性能优化

### 1. 使用连接池

```python
# PostgreSQL 连接池
register_tortoise(
    app,
    config={
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "user",
                    "password": "pass",
                    "database": "db",
                    "minsize": 1,
                    "maxsize": 10,  # 连接池大小
                }
            }
        },
        "apps": {
            "models": {
                "models": ["models"],
                "default_connection": "default",
            }
        }
    }
)
```

### 2. 使用缓存

```python
import aioredis

@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis_pool(
        'redis://localhost:6379',
        minsize=5,
        maxsize=10
    )

# 在 ViewSet 中使用缓存
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        # 尝试从缓存获取
        redis = request.app.ctx.redis
        cache_key = f"product:{pk}"
        cached = await redis.get(cache_key)

        if cached:
            from sanic.response import json
            import json as json_lib
            return json(json_lib.loads(cached))

        # 从数据库获取
        obj = await self.get_object(request, pk)
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(obj).model_dump()

        # 存入缓存（10分钟过期）
        await redis.setex(cache_key, 600, json_lib.dumps(data))

        from sanic.response import json
        return json(data)
```

### 3. 使用异步操作

```python
import asyncio

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # 并行执行多个异步操作
        results = await asyncio.gather(
            Product.all().count(),
            Category.all(),
            Brand.all()
        )

        product_count, categories, brands = results
```

## 部署建议

### 使用 Gunicorn

```bash
gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sanic.worker.GunicornWorker \
  --access-logfile /var/log/access.log \
  --error-logfile /var/log/error.log
```

### 使用 Supervisor

```ini
[program:myapp]
command=/path/to/venv/bin/gunicorn app:app --bind 0.0.0.0:8000 --workers 4 --worker-class sanic.worker.GunicornWorker
directory=/path/to/app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/myapp.log
```

### 使用 Nginx 反向代理

```nginx
upstream myapp {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://myapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/static/;
    }
}
```

## 下一步

- 详细了解 [健康检查](health-check.md)
- 学习 [限流中间件](middleware/rate-limiting.md) 的使用
- 查看 [异常处理](exceptions.md) 的最佳实践
- 阅读 [HTTP 状态码](http-status.md) 参考
