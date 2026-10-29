# 健康检查

SRF 提供了内置的健康检查功能，用于监控应用和依赖服务的状态。

## 概述

健康检查是监控系统的重要组成部分，它可以：

- 检测应用是否正常运行
- 监控依赖服务（数据库、缓存等）的可用性
- 集成到负载均衡器和容器编排系统
- 提供早期预警，及时发现问题

## 快速开始

Redis 已包含在 SRF 依赖中；SQLite 检查使用的 `aiosqlite` 是可选依赖，需
`pip install aiosqlite`。

### 1. 注册健康检查路由并配置检查列表

路由会读取 `app.config.HEALTH_CHECK_LIST`（默认为空列表），并对其中每个检查类执行一次。

```python
from sanic import Sanic
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.route import health_check

app = Sanic("MyApp")
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
app.add_route(health_check, "/health", methods=["GET"])
```

### 2. 配置依赖服务

检查类按 `name` 从 `app.ctx` 读取客户端。Redis 检查使用 `app.ctx.redis`；SQLite 检查要求 `app.ctx.sqlite` 是 `aiosqlite.Connection`。

```python
from aiosqlite import connect
from redis.asyncio import Redis


@app.before_server_start
async def setup_services(app):
    app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
    app.ctx.sqlite = await connect("db.sqlite3")
```

### 3. 访问健康检查端点

```bash
curl http://localhost:8000/health
```

响应是检查名称到状态的 JSON 映射，例如：

```json
{ "redis": "up", "sqlite": "down" }
```

即使检查返回 `"down"`，当前 handler 仍返回 HTTP 200。若客户端未预先挂载到 `app.ctx`，构造检查实例会抛出异常并由 Sanic 处理。

## 内置健康检查

SRF 提供以下检查类。

### RedisCheck

```python
from srf.health.checks import RedisCheck
from redis.asyncio import Redis

app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
```

检查逻辑是调用 `ping()`，默认超时 5 秒。

### SQLiteCheck

```python
from srf.health.checks import SQLiteCheck
from aiosqlite import connect

app.ctx.sqlite = await connect("db.sqlite3")
```

检查逻辑是执行 `SELECT 1`。该检查需要 `aiosqlite`，不能使用标准库同步 `sqlite3.Connection`。

## 自定义健康检查

继承 `BaseHealthCheck`，设置 `name`，实现 `check()`，并把检查类加入 `HEALTH_CHECK_LIST`。构造时框架会读取 `app.ctx.<name>` 并设置为同名实例属性。`run()` 在检查成功时返回 `(name, "up")`，失败时记录日志并返回 `(name, "down")`。

```python
from srf.health.checks import BaseHealthCheck


class APIServiceCheck(BaseHealthCheck):
    name = "api_service"
    timeout = 5

    async def check(self):
        await self.api_service.ping()


# 由应用初始化并创建 API 客户端
app.ctx.api_service = api_client
app.config.HEALTH_CHECK_LIST = [APIServiceCheck]
```

## 完整示例

```python
from sanic import Sanic
from redis.asyncio import Redis
from aiosqlite import connect
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.route import health_check

app = Sanic("MyApp")
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
app.add_route(health_check, "/health", methods=["GET"])


@app.before_server_start
async def setup_services(app):
    app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
    app.ctx.sqlite = await connect("db.sqlite3")


@app.after_server_stop
async def cleanup_services(app):
    await app.ctx.redis.aclose()
    await app.ctx.sqlite.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

## 最佳实践

1. 检查应快速完成并设置合理超时。
2. 检查应避免副作用。
3. 只将需要监控的依赖加入 `HEALTH_CHECK_LIST`。
4. 应用启动时先初始化检查依赖的客户端，并在停止时关闭。
5. 若负载均衡器需要非 200 失败状态，应在应用层包装 `health_check` 并实现相应状态码。

## 下一步

- 了解 [异常处理](exceptions.md) 处理健康检查异常
- 学习 [限流](middleware/rate-limiting.md) 保护健康检查端点
- 查看 [HTTP 状态码](http-status.md) 了解状态码使用
