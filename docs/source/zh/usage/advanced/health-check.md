# 健康检查

SRF 提供了内置的健康检查功能，用于监控应用和依赖服务的状态。

## 概述

健康检查是监控系统的重要组成部分，它可以：

- 检测应用是否正常运行
- 监控依赖服务（数据库、缓存等）的可用性
- 集成到负载均衡器和容器编排系统
- 提供早期预警，及时发现问题

## 快速开始

### 1. 注册健康检查路由并配置检查列表

路由会读取 `app.config.HEALTH_CHECK_LIST`（默认为空列表），并对其中每个检查类执行一次。

```python
from sanic import Sanic
from srf.health.route import bp as health_bp
from srf.health.checks import RedisCheck, SQLiteCheck

app = Sanic("MyApp")

# 配置要执行的检查（顺序即响应中 services 的内容）
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]

# 注册健康检查蓝图
app.blueprint(health_bp)
```

### 2. 配置依赖服务

每个检查类通过 `name` 从 `app.ctx.<name>` 取客户端。内置检查对应：

- `RedisCheck.name == "redis"` → `app.ctx.redis`
- `SQLiteCheck.name == "sqlite"` → `app.ctx.sqlite`

```python
from redis.asyncio import Redis
import sqlite3

@app.before_server_start
async def setup_services(app, loop):
    """初始化依赖服务"""
    app.ctx.redis = Redis.from_url("redis://localhost:6379")
    # SQLiteCheck 会在线程中使用该连接，因此需允许跨线程访问。
    app.ctx.sqlite = sqlite3.connect(
        "db.sqlite3", check_same_thread=False
    )
```

### 3. 访问健康检查端点

```bash
curl http://localhost:8000/health/
```

全部正常时的响应（HTTP 200）：

```json
{
  "status": "ok",
  "services": {
    "redis": "up",
    "sqlite": "up"
  }
}
```

有服务异常时的响应（HTTP 500）：

```json
{
  "status": "fail",
  "services": {
    "redis": "up",
    "sqlite": "down (unable to open database file)"
  }
}
```

## 内置健康检查

SRF 提供了多个内置的健康检查类。

### RedisCheck

```python
from srf.health.checks import RedisCheck
from redis.asyncio import Redis

app.ctx.redis = Redis.from_url("redis://localhost:6379")

```

**检查逻辑**：执行 `PING` 命令。

### SQLiteCheck

```python
from srf.health.checks import SQLiteCheck
import sqlite3

app.ctx.sqlite = sqlite3.connect("db.sqlite3", check_same_thread=False)
```

**检查逻辑**：执行 `SELECT 1` 查询

## 自定义健康检查

继承 `BaseHealthCheck`，设置 `name`，实现 `check()`，并把类加入 `HEALTH_CHECK_LIST`。  
构造时会从 `app.ctx.<name>` 读取客户端并挂到 `self.<name>`。  
基类默认 `timeout = 5`（秒）；内置 Redis/SQLite 检查使用 `asyncio.timeout(self.timeout)`。

```python
from srf.health.base import BaseHealthCheck

class APIServiceCheck(BaseHealthCheck):
    """外部 API 服务检查"""

    name = "api_service"
    timeout = 5  # 可覆盖 BaseHealthCheck.timeout

    async def check(self):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.example.com/health", timeout=self.timeout
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"unexpected status {resp.status}")


# 使用前先挂载客户端
# app.ctx.api_service = ...

app.config.HEALTH_CHECK_LIST = [
    RedisCheck,
    SQLiteCheck,
    APIServiceCheck,
]
```

检查失败时在 `check()` 中抛出异常即可；`run()` 会将其格式化为 `"down (<错误信息>)"`。

## 完整示例

```python
from sanic import Sanic
from redis.asyncio import Redis, ConnectionPool
import sqlite3

from srf.health.route import bp as health_bp
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.base import BaseHealthCheck

app = Sanic("MyApp")


class APIServiceCheck(BaseHealthCheck):
    name = "api_service"

    async def check(self):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.example.com/health", timeout=5
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"API unreachable: {resp.status}")


app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck, APIServiceCheck]


@app.before_server_start
async def setup_services(app, loop):
    pool = ConnectionPool.from_url("redis://localhost:6379", max_connections=10)
    app.ctx.redis = Redis(connection_pool=pool)
    app.ctx.sqlite = sqlite3.connect(
        "db.sqlite3", check_same_thread=False
    )
    # 自定义检查所需的客户端（示例用占位对象；真实场景换成你的 SDK）
    app.ctx.api_service = object()


@app.after_server_stop
async def cleanup_services(app, loop):
    await app.ctx.redis.aclose()
    app.ctx.sqlite.close()


app.blueprint(health_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```



## 最佳实践

1. **快速响应**：健康检查应该快速返回（< 5秒）
2. **幂等性**：检查不应该有副作用
3. **依赖检查**：检查关键依赖服务的可用性
4. **合理的超时**：设置适当的超时时间
5. **日志记录**：记录健康检查失败的详细信息
6. **区分严重性**：区分关键服务和非关键服务
7. **按需配置**：只把真正需要探测的检查放进 `HEALTH_CHECK_LIST`

## 下一步

- 了解 [异常处理](exceptions.md) 处理健康检查异常
- 学习 [限流](middleware/rate-limiting.md) 保护健康检查端点
- 查看 [HTTP 状态码](http-status.md) 了解状态码使用
