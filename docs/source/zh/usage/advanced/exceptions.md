# 异常处理

SRF 提供了统一的异常处理机制，将异常自动转换为标准的 HTTP 响应。

## 概述

良好的异常处理可以：

- 提供友好的错误信息
- 隐藏内部实现细节
- 统一错误响应格式
- 简化错误处理逻辑

## 内置异常类

### TargetObjectAlreadyExist

对象已存在异常，返回 HTTP 409 Conflict。

```python
from srf.exceptions import TargetObjectAlreadyExist

async def create_product(self, request, schema):
    # 检查 SKU 是否已存在
    if await Product.filter(sku=schema.sku).exists():
        raise TargetObjectAlreadyExist(f"SKU {schema.sku} 已存在")
    
    product = await Product.create(**schema.dict())
    return product
```

**响应**：

```json
{
  "error": "SKU PRD-001 已存在"
}
```

HTTP 状态码：409

### ImproperlyConfigured

配置错误异常，返回 HTTP 500 Internal Server Error。

```python
from srf.exceptions import ImproperlyConfigured

class ProductViewSet(BaseViewSet):
    def get_schema(self, request, is_safe=False):
        schema = getattr(self, 'schema_class', None)
        if not schema:
            raise ImproperlyConfigured("schema_class 未配置")
        return schema
```

**响应**：

```json
{
  "error": "schema_class 未配置"
}
```

HTTP 状态码：500

## Sanic 内置异常

SRF 会自动处理 Sanic 的内置异常：

### NotFound (404)

资源未找到。

```python
from sanic.exceptions import NotFound

async def get_product(product_id):
    product = await Product.get_or_none(id=product_id)
    if not product:
        raise NotFound(f"产品 {product_id} 不存在")
    return product
```

### Forbidden (403)

权限不足。

```python
from sanic.exceptions import Forbidden

async def delete_product(request, product_id):
    user = request.ctx.user
    if not user.is_admin:
        raise Forbidden("需要管理员权限")
    
    await Product.filter(id=product_id).delete()
```

### Unauthorized (401)

未授权，需要登录。

```python
from sanic.exceptions import Unauthorized

async def get_profile(request):
    user = request.ctx.user
    if not user:
        raise Unauthorized("请先登录")
    
    return user
```

### InvalidUsage (400)

无效请求。

```python
from sanic.exceptions import InvalidUsage

async def create_order(request):
    product_id = request.json.get('product_id')
    if not product_id:
        raise InvalidUsage("缺少 product_id 参数")
    
    # ...
```

## 数据验证异常

Pydantic 验证失败会自动返回 HTTP 422。

```python
from pydantic import ValidationError

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        try:
            schema_class = self.get_schema(request, is_safe=False)
            schema = schema_class(**request.json)
        except ValidationError as e:
            # SRF 会自动捕获并返回 422
            pass
```

**响应**：

```json
{
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["name"],
      "msg": "String should have at least 1 character",
      "input": ""
    },
    {
      "type": "greater_than",
      "loc": ["price"],
      "msg": "Input should be greater than 0",
      "input": -10
    }
  ]
}
```

HTTP 状态码：422

## Tortoise ORM 异常

### DoesNotExist

对象不存在。

```python
from tortoise.exceptions import DoesNotExist

try:
    product = await Product.get(id=product_id)
except DoesNotExist:
    raise NotFound(f"产品 {product_id} 不存在")
```

### IntegrityError

数据库完整性错误（如唯一约束冲突）。

```python
from tortoise.exceptions import IntegrityError
from srf.exceptions import TargetObjectAlreadyExist

try:
    product = await Product.create(sku=sku, name=name)
except IntegrityError:
    raise TargetObjectAlreadyExist(f"SKU {sku} 已存在")
```

## 自定义异常

### 创建自定义异常类

```python
from sanic.exceptions import SanicException

class ProductOutOfStock(SanicException):
    """产品缺货异常"""
    status_code = 400
    message = "产品库存不足"

class PaymentFailed(SanicException):
    """支付失败异常"""
    status_code = 402
    message = "支付失败"

class ResourceLocked(SanicException):
    """资源被锁定异常"""
    status_code = 423
    message = "资源已被锁定"
```

### 使用自定义异常

```python
from exceptions import ProductOutOfStock

async def create_order(request):
    product_id = request.json['product_id']
    quantity = request.json['quantity']
    
    product = await Product.get(id=product_id)
    
    # 检查库存
    if product.stock < quantity:
        raise ProductOutOfStock(
            f"产品 {product.name} 库存不足，"
            f"需要 {quantity}，当前库存 {product.stock}"
        )
    
    # 创建订单
    # ...
```

## 统一异常处理

### 全局异常处理器

```python
from sanic import Sanic
from sanic.response import json
from sanic.exceptions import NotFound, Forbidden, Unauthorized, InvalidUsage
from srf.views.http_status import HTTPStatus
import logging

app = Sanic("MyApp")
logger = logging.getLogger(__name__)

@app.exception(NotFound)
async def handle_not_found(request, exception):
    """处理 404 错误"""
    return json({
        "error": "资源未找到",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_404_NOT_FOUND)

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    """处理 403 错误"""
    return json({
        "error": "权限不足",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_403_FORBIDDEN)

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    """处理 401 错误"""
    return json({
        "error": "未授权",
        "message": "请先登录"
    }, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    """处理 400 错误"""
    return json({
        "error": "无效请求",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_400_BAD_REQUEST)

@app.exception(Exception)
async def handle_exception(request, exception):
    """处理未捕获的异常"""
    # 记录详细错误
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra={
            'path': request.path,
            'method': request.method,
            'ip': request.ip,
        }
    )
    
    # 返回通用错误（不暴露内部信息）
    return json({
        "error": "服务器内部错误",
        "message": "请稍后再试"
    }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
```

### 统一错误响应格式

```python
from sanic.response import json as json_response
from srf.views.http_status import HTTPStatus

class ErrorResponse:
    """统一错误响应"""
    
    @staticmethod
    def not_found(message="资源未找到", details=None):
        return json_response({
            "error": "NOT_FOUND",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def forbidden(message="权限不足", details=None):
        return json_response({
            "error": "FORBIDDEN",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def unauthorized(message="未授权", details=None):
        return json_response({
            "error": "UNAUTHORIZED",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def bad_request(message="无效请求", details=None):
        return json_response({
            "error": "BAD_REQUEST",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def conflict(message="资源冲突", details=None):
        return json_response({
            "error": "CONFLICT",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_409_CONFLICT)
    
    @staticmethod
    def server_error(message="服务器内部错误", details=None):
        return json_response({
            "error": "INTERNAL_ERROR",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)

# 使用
async def get_product(request, product_id):
    product = await Product.get_or_none(id=product_id)
    if not product:
        return ErrorResponse.not_found(f"产品 {product_id} 不存在")
    
    # ...
```

## 错误日志

### 配置日志

```python
import logging
from logging.handlers import RotatingFileHandler

# 创建 logger
logger = logging.getLogger('app')
logger.setLevel(logging.INFO)

# 控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 文件输出（自动轮转）
file_handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
```

### 记录异常

```python
@app.exception(Exception)
async def handle_exception(request, exception):
    """处理未捕获的异常"""
    # 构建错误上下文
    context = {
        'path': request.path,
        'method': request.method,
        'ip': request.ip,
        'user_agent': request.headers.get('User-Agent'),
        'user_id': getattr(request.ctx, 'user', {}).get('id'),
    }
    
    # 记录错误
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra=context
    )
    
    # 发送告警（可选）
    # await send_alert(exception, context)
    
    return json({
        "error": "服务器内部错误"
    }, status=500)
```

## 开发环境 vs 生产环境

### 开发环境

显示详细的错误信息，方便调试：

```python
if app.config.DEBUG:
    @app.exception(Exception)
    async def handle_exception_dev(request, exception):
        import traceback
        
        return json({
            "error": str(exception),
            "type": type(exception).__name__,
            "traceback": traceback.format_exc()
        }, status=500)
```

### 生产环境

隐藏内部细节，只返回通用错误：

```python
if not app.config.DEBUG:
    @app.exception(Exception)
    async def handle_exception_prod(request, exception):
        # 记录详细错误
        logger.error(f"Error: {exception}", exc_info=True)
        
        # 返回通用错误
        return json({
            "error": "服务器内部错误",
            "message": "请稍后再试"
        }, status=500)
```

## 完整示例

```python
from sanic import Sanic
from sanic.response import json
from sanic.exceptions import NotFound, Forbidden, Unauthorized, InvalidUsage, SanicException
from srf.views.http_status import HTTPStatus
from pydantic import ValidationError
import logging

app = Sanic("MyApp")
logger = logging.getLogger(__name__)

# 自定义异常
class BusinessException(SanicException):
    """业务异常基类"""
    status_code = 400

class ProductOutOfStock(BusinessException):
    """产品缺货"""
    message = "产品库存不足"

class InsufficientBalance(BusinessException):
    """余额不足"""
    message = "账户余额不足"

# 统一错误响应
@app.exception(NotFound)
async def handle_not_found(request, exception):
    return json({
        "error": "NOT_FOUND",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_404_NOT_FOUND)

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    return json({
        "error": "FORBIDDEN",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_403_FORBIDDEN)

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    return json({
        "error": "UNAUTHORIZED",
        "message": "请先登录"
    }, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    return json({
        "error": "INVALID_REQUEST",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_400_BAD_REQUEST)

@app.exception(ValidationError)
async def handle_validation_error(request, exception):
    return json({
        "error": "VALIDATION_ERROR",
        "errors": exception.errors()
    }, status=HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY)

@app.exception(BusinessException)
async def handle_business_exception(request, exception):
    return json({
        "error": type(exception).__name__,
        "message": str(exception)
    }, status=exception.status_code)

@app.exception(Exception)
async def handle_exception(request, exception):
    # 记录错误
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra={
            'path': request.path,
            'method': request.method,
            'ip': request.ip,
        }
    )
    
    # 根据环境返回不同信息
    if app.config.DEBUG:
        import traceback
        return json({
            "error": "INTERNAL_ERROR",
            "message": str(exception),
            "traceback": traceback.format_exc()
        }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return json({
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后再试"
        }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
```

## 最佳实践

1. **分类异常**：为不同类型的错误使用不同的异常类
2. **友好的错误信息**：提供清晰、有帮助的错误消息
3. **统一响应格式**：使用一致的错误响应结构
4. **记录详细日志**：记录错误的上下文信息
5. **隐藏内部细节**：生产环境不暴露内部错误
6. **使用适当的状态码**：为不同错误使用正确的 HTTP 状态码
7. **国际化**：支持多语言错误消息

## 错误码设计

为不同的业务错误定义错误码：

```python
class ErrorCode:
    """错误码"""
    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    
    # 认证错误 (2000-2999)
    UNAUTHORIZED = 2000
    INVALID_TOKEN = 2001
    TOKEN_EXPIRED = 2002
    
    # 权限错误 (3000-3999)
    FORBIDDEN = 3000
    INSUFFICIENT_PERMISSIONS = 3001
    
    # 资源错误 (4000-4999)
    NOT_FOUND = 4000
    ALREADY_EXISTS = 4001
    
    # 业务错误 (5000-5999)
    OUT_OF_STOCK = 5000
    INSUFFICIENT_BALANCE = 5001

# 使用
return json({
    "error": {
        "code": ErrorCode.OUT_OF_STOCK,
        "message": "产品库存不足",
        "details": {"product_id": product_id, "available": 0}
    }
}, status=400)
```

## 下一步

- 学习 [HTTP 状态码](http-status.md) 了解状态码使用
- 阅读 [认证](../core/authentication.md) 了解认证异常
- 查看 [视图](../core/viewsets.md) 了解 ViewSet 中的异常处理
