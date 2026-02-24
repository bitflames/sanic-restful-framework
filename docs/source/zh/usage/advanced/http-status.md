# HTTP 状态码

SRF 提供了完整的 HTTP 状态码枚举，方便在代码中使用语义化的常量。

## 概述

使用状态码常量的好处：

- **可读性**：`HTTP_200_OK` 比 `200` 更清晰
- **类型安全**：避免输入错误的状态码
- **IDE 支持**：提供自动补全和文档提示
- **统一标准**：团队使用一致的状态码

## 导入

```python
from srf.views.http_status import HTTPStatus
```

## 状态码分类

### 1xx - 信息响应

| 状态码 | 常量 | 说明 |
|--------|------|------|
| 100 | `HTTP_100_CONTINUE` | 继续 |
| 101 | `HTTP_101_SWITCHING_PROTOCOLS` | 切换协议 |

```python
from srf.views.http_status import HTTPStatus

# 检查是否为信息响应
if HTTPStatus.is_informational(status_code):
    print("信息响应")
```

### 2xx - 成功响应

| 状态码 | 常量 | 说明 | 使用场景 |
|--------|------|------|----------|
| 200 | `HTTP_200_OK` | 成功 | GET, PUT, PATCH 成功 |
| 201 | `HTTP_201_CREATED` | 已创建 | POST 创建资源成功 |
| 202 | `HTTP_202_ACCEPTED` | 已接受 | 异步处理请求 |
| 204 | `HTTP_204_NO_CONTENT` | 无内容 | DELETE 成功 |

```python
from sanic.response import json

# GET 请求成功
return json(data, status=HTTPStatus.HTTP_200_OK)

# POST 创建成功
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# DELETE 成功
return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### 3xx - 重定向

| 状态码 | 常量 | 说明 |
|--------|------|------|
| 301 | `HTTP_301_MOVED_PERMANENTLY` | 永久重定向 |
| 302 | `HTTP_302_FOUND` | 临时重定向 |
| 304 | `HTTP_304_NOT_MODIFIED` | 未修改 |

```python
from sanic.response import redirect

# 永久重定向
return redirect('/new-url', status=HTTPStatus.HTTP_301_MOVED_PERMANENTLY)

# 临时重定向
return redirect('/temp-url', status=HTTPStatus.HTTP_302_FOUND)
```

### 4xx - 客户端错误

| 状态码 | 常量 | 说明 | 使用场景 |
|--------|------|------|----------|
| 400 | `HTTP_400_BAD_REQUEST` | 错误请求 | 参数错误、格式错误 |
| 401 | `HTTP_401_UNAUTHORIZED` | 未授权 | 未登录、Token 无效 |
| 403 | `HTTP_403_FORBIDDEN` | 禁止访问 | 权限不足 |
| 404 | `HTTP_404_NOT_FOUND` | 未找到 | 资源不存在 |
| 405 | `HTTP_405_METHOD_NOT_ALLOWED` | 方法不允许 | HTTP 方法不支持 |
| 409 | `HTTP_409_CONFLICT` | 冲突 | 资源冲突（如重复创建） |
| 422 | `HTTP_422_UNPROCESSABLE_ENTITY` | 无法处理 | 数据验证失败 |
| 429 | `HTTP_429_TOO_MANY_REQUESTS` | 请求过多 | 超过限流限制 |

```python
from sanic.response import json

# 参数错误
if not data:
    return json({"error": "缺少参数"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

# 未登录
if not user:
    return json({"error": "未登录"}, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

# 权限不足
if not user.is_admin:
    return json({"error": "权限不足"}, status=HTTPStatus.HTTP_403_FORBIDDEN)

# 资源不存在
if not product:
    return json({"error": "产品不存在"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

# 资源冲突
if exists:
    return json({"error": "已存在"}, status=HTTPStatus.HTTP_409_CONFLICT)

# 数据验证失败
return json({"errors": errors}, status=HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY)

# 限流
return json({"error": "请求过多"}, status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)
```

### 5xx - 服务器错误

| 状态码 | 常量 | 说明 | 使用场景 |
|--------|------|------|----------|
| 500 | `HTTP_500_INTERNAL_SERVER_ERROR` | 服务器错误 | 未捕获的异常 |
| 501 | `HTTP_501_NOT_IMPLEMENTED` | 未实现 | 功能未实现 |
| 502 | `HTTP_502_BAD_GATEWAY` | 网关错误 | 上游服务错误 |
| 503 | `HTTP_503_SERVICE_UNAVAILABLE` | 服务不可用 | 服务维护、过载 |

```python
# 服务器错误
try:
    result = await process_data()
except Exception as e:
    logger.error(f"Error: {e}")
    return json(
        {"error": "服务器错误"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )

# 服务不可用
if not healthy:
    return json(
        {"error": "服务维护中"},
        status=HTTPStatus.HTTP_503_SERVICE_UNAVAILABLE
    )
```

## 辅助函数

### 检查状态码类型

```python
from srf.views.http_status import HTTPStatus

# 是否为信息响应 (1xx)
HTTPStatus.is_informational(100)  # True

# 是否为成功响应 (2xx)
HTTPStatus.is_success(200)  # True
HTTPStatus.is_success(201)  # True

# 是否为重定向 (3xx)
HTTPStatus.is_redirect(301)  # True

# 是否为客户端错误 (4xx)
HTTPStatus.is_client_error(400)  # True
HTTPStatus.is_client_error(404)  # True

# 是否为服务器错误 (5xx)
HTTPStatus.is_server_error(500)  # True
HTTPStatus.is_server_error(503)  # True
```

## 在 ViewSet 中使用

### 基本用法

```python
from srf.views import BaseViewSet
from srf.views.http_status import HTTPStatus
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """创建产品"""
        # 验证数据
        schema_class = self.get_schema(request, is_safe=False)
        try:
            schema = schema_class(**request.json)
        except Exception as e:
            return json(
                {"error": str(e)},
                status=HTTPStatus.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已存在
        if await Product.filter(sku=schema.sku).exists():
            return json(
                {"error": "SKU 已存在"},
                status=HTTPStatus.HTTP_409_CONFLICT
            )
        
        # 创建
        obj = await Product.create(**schema.dict())
        
        # 序列化
        reader_schema = self.get_schema(request, is_safe=True)
        data = reader_schema.model_validate(obj).model_dump()
        
        # 返回 201 Created
        return json(data, status=HTTPStatus.HTTP_201_CREATED)
    
    async def destroy(self, request, pk):
        """删除产品"""
        # 获取对象
        try:
            obj = await self.get_object(request, pk)
        except:
            return json(
                {"error": "产品不存在"},
                status=HTTPStatus.HTTP_404_NOT_FOUND
            )
        
        # 删除
        await obj.delete()
        
        # 返回 204 No Content
        return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### 自定义操作

```python
from srf.views.decorators import action

class ProductViewSet(BaseViewSet):
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """发布产品"""
        # 获取产品
        try:
            product = await self.get_object(request, pk)
        except:
            return json(
                {"error": "产品不存在"},
                status=HTTPStatus.HTTP_404_NOT_FOUND
            )
        
        # 检查状态
        if product.is_published:
            return json(
                {"error": "产品已发布"},
                status=HTTPStatus.HTTP_409_CONFLICT
            )
        
        # 发布
        product.is_published = True
        await product.save()
        
        return json(
            {"message": "发布成功"},
            status=HTTPStatus.HTTP_200_OK
        )
```

## 常见场景

### RESTful API 标准响应

| 操作 | 方法 | 成功状态码 | 失败状态码 |
|------|------|-----------|-----------|
| 列表 | GET | 200 OK | 404 Not Found |
| 详情 | GET | 200 OK | 404 Not Found |
| 创建 | POST | 201 Created | 400 Bad Request, 409 Conflict, 422 Unprocessable Entity |
| 更新 | PUT/PATCH | 200 OK | 400 Bad Request, 404 Not Found, 422 Unprocessable Entity |
| 删除 | DELETE | 204 No Content | 404 Not Found |

### 异步任务

```python
@action(methods=["post"], detail=False, url_path="import")
async def import_products(self, request):
    """批量导入产品（异步任务）"""
    file = request.files.get('file')
    
    if not file:
        return json(
            {"error": "缺少文件"},
            status=HTTPStatus.HTTP_400_BAD_REQUEST
        )
    
    # 创建异步任务
    task_id = await create_import_task(file)
    
    # 返回 202 Accepted
    return json({
        "message": "任务已创建",
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}"
    }, status=HTTPStatus.HTTP_202_ACCEPTED)
```

### 条件请求

```python
async def retrieve(self, request, pk):
    """获取产品（支持条件请求）"""
    product = await self.get_object(request, pk)
    
    # 检查 If-None-Match
    etag = f'"{product.id}-{product.updated_at.timestamp()}"'
    if_none_match = request.headers.get('If-None-Match')
    
    if if_none_match == etag:
        # 未修改
        return json({}, status=HTTPStatus.HTTP_304_NOT_MODIFIED)
    
    # 返回数据
    schema = self.get_schema(request, is_safe=True)
    data = schema.model_validate(product).model_dump()
    
    response = json(data, status=HTTPStatus.HTTP_200_OK)
    response.headers['ETag'] = etag
    return response
```

## 完整状态码列表

```python
from srf.views.http_status import HTTPStatus

# 1xx 信息响应
HTTPStatus.HTTP_100_CONTINUE
HTTPStatus.HTTP_101_SWITCHING_PROTOCOLS

# 2xx 成功
HTTPStatus.HTTP_200_OK
HTTPStatus.HTTP_201_CREATED
HTTPStatus.HTTP_202_ACCEPTED
HTTPStatus.HTTP_203_NON_AUTHORITATIVE_INFORMATION
HTTPStatus.HTTP_204_NO_CONTENT
HTTPStatus.HTTP_205_RESET_CONTENT
HTTPStatus.HTTP_206_PARTIAL_CONTENT

# 3xx 重定向
HTTPStatus.HTTP_300_MULTIPLE_CHOICES
HTTPStatus.HTTP_301_MOVED_PERMANENTLY
HTTPStatus.HTTP_302_FOUND
HTTPStatus.HTTP_303_SEE_OTHER
HTTPStatus.HTTP_304_NOT_MODIFIED
HTTPStatus.HTTP_305_USE_PROXY
HTTPStatus.HTTP_307_TEMPORARY_REDIRECT
HTTPStatus.HTTP_308_PERMANENT_REDIRECT

# 4xx 客户端错误
HTTPStatus.HTTP_400_BAD_REQUEST
HTTPStatus.HTTP_401_UNAUTHORIZED
HTTPStatus.HTTP_402_PAYMENT_REQUIRED
HTTPStatus.HTTP_403_FORBIDDEN
HTTPStatus.HTTP_404_NOT_FOUND
HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED
HTTPStatus.HTTP_406_NOT_ACCEPTABLE
HTTPStatus.HTTP_407_PROXY_AUTHENTICATION_REQUIRED
HTTPStatus.HTTP_408_REQUEST_TIMEOUT
HTTPStatus.HTTP_409_CONFLICT
HTTPStatus.HTTP_410_GONE
HTTPStatus.HTTP_411_LENGTH_REQUIRED
HTTPStatus.HTTP_412_PRECONDITION_FAILED
HTTPStatus.HTTP_413_REQUEST_ENTITY_TOO_LARGE
HTTPStatus.HTTP_414_REQUEST_URI_TOO_LONG
HTTPStatus.HTTP_415_UNSUPPORTED_MEDIA_TYPE
HTTPStatus.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
HTTPStatus.HTTP_417_EXPECTATION_FAILED
HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY
HTTPStatus.HTTP_423_LOCKED
HTTPStatus.HTTP_424_FAILED_DEPENDENCY
HTTPStatus.HTTP_426_UPGRADE_REQUIRED
HTTPStatus.HTTP_428_PRECONDITION_REQUIRED
HTTPStatus.HTTP_429_TOO_MANY_REQUESTS
HTTPStatus.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE

# 5xx 服务器错误
HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
HTTPStatus.HTTP_501_NOT_IMPLEMENTED
HTTPStatus.HTTP_502_BAD_GATEWAY
HTTPStatus.HTTP_503_SERVICE_UNAVAILABLE
HTTPStatus.HTTP_504_GATEWAY_TIMEOUT
HTTPStatus.HTTP_505_HTTP_VERSION_NOT_SUPPORTED
HTTPStatus.HTTP_507_INSUFFICIENT_STORAGE
HTTPStatus.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
```

## 最佳实践

1. **使用语义化常量**：用 `HTTP_200_OK` 代替 `200`
2. **正确选择状态码**：为不同情况使用适当的状态码
3. **一致性**：团队统一使用状态码标准
4. **文档化**：在 API 文档中说明各端点的状态码
5. **客户端友好**：提供清晰的错误消息和状态码
6. **遵循 RESTful 规范**：遵循标准的 REST API 状态码约定

## 常见错误

### ❌ 错误做法

```python
# 所有错误都返回 200
return json({"error": "not found"}, status=200)

# 使用魔法数字
return json(data, status=201)

# 错误的状态码
# 删除成功返回 200 而不是 204
return json({"message": "deleted"}, status=200)
```

### ✅ 正确做法

```python
# 使用语义化常量
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# 使用适当的状态码
if not found:
    return json({"error": "not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

# 删除成功返回 204
return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

## 下一步

- 学习 [异常处理](exceptions.md) 了解异常和状态码的关系
- 阅读 [视图](../core/viewsets.md) 了解在 ViewSet 中使用状态码
- 查看 [API 参考](../../api-reference.md) 了解完整的 API 文档
