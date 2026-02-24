# Exception Handling

SRF provides a unified exception handling mechanism that automatically converts exceptions into standard HTTP responses.

## Overview

Good exception handling can:

- Provide friendly error messages
- Hide internal implementation details
- Unify the error response format
- Simplify error handling logic

## Built-in Exception Classes

### TargetObjectAlreadyExist

Object already exists exception, returns HTTP 409 Conflict.

```python
from srf.exceptions import TargetObjectAlreadyExist

async def create_product(self, request, schema):
    # Check if SKU already exists
    if await Product.filter(sku=schema.sku).exists():
        raise TargetObjectAlreadyExist(f"SKU {schema.sku} already exists")
    
    product = await Product.create(**schema.dict())
    return product
```

**Response**:

```json
{
  "error": "SKU PRD-001 already exists"
}
```

HTTP Status Code: 409

### ImproperlyConfigured

Configuration error exception, returns HTTP 500 Internal Server Error.

```python
from srf.exceptions import ImproperlyConfigured

class ProductViewSet(BaseViewSet):
    def get_schema(self, request, is_safe=False):
        schema = getattr(self, 'schema_class', None)
        if not schema:
            raise ImproperlyConfigured("schema_class not configured")
        return schema
```

**Response**:

```json
{
  "error": "schema_class not configured"
}
```

HTTP Status Code: 500

## Sanic Built-in Exceptions

SRF automatically handles Sanic's built-in exceptions:

### NotFound (404)

Resource not found.

```python
from sanic.exceptions import NotFound

async def get_product(product_id):
    product = await Product.get_or_none(id=product_id)
    if not product:
        raise NotFound(f"Product {product_id} does not exist")
    return product
```

### Forbidden (403)

Insufficient permissions.

```python
from sanic.exceptions import Forbidden

async def delete_product(request, product_id):
    user = request.ctx.user
    if not user.is_admin:
        raise Forbidden("Requires administrator privileges")
    
    await Product.filter(id=product_id).delete()
```

### Unauthorized (401)

Not authorized, login required.

```python
from sanic.exceptions import Unauthorized

async def get_profile(request):
    user = request.ctx.user
    if not user:
        raise Unauthorized("Please log in first")
    
    return user
```

### InvalidUsage (400)

Invalid request.

```python
from sanic.exceptions import InvalidUsage

async def create_order(request):
    product_id = request.json.get('product_id')
    if not product_id:
        raise InvalidUsage("Missing product_id parameter")
    
    # ...
```

## Data Validation Exceptions

Pydantic validation failures automatically return HTTP 422.

```python
from pydantic import ValidationError

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        try:
            schema_class = self.get_schema(request, is_safe=False)
            schema = schema_class(**request.json)
        except ValidationError as e:
            # SRF will automatically catch and return 422
            pass
```

**Response**:

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

HTTP Status Code: 422

## Tortoise ORM Exceptions

### DoesNotExist

Object does not exist.

```python
from tortoise.exceptions import DoesNotExist

try:
    product = await Product.get(id=product_id)
except DoesNotExist:
    raise NotFound(f"Product {product_id} does not exist")
```

### IntegrityError

Database integrity error (e.g., unique constraint violation).

```python
from tortoise.exceptions import IntegrityError
from srf.exceptions import TargetObjectAlreadyExist

try:
    product = await Product.create(sku=sku, name=name)
except IntegrityError:
    raise TargetObjectAlreadyExist(f"SKU {sku} already exists")
```

## Custom Exceptions

### Creating Custom Exception Classes

```python
from sanic.exceptions import SanicException

class ProductOutOfStock(SanicException):
    """Product out of stock exception"""
    status_code = 400
    message = "Product stock is insufficient"

class PaymentFailed(SanicException):
    """Payment failed exception"""
    status_code = 402
    message = "Payment failed"

class ResourceLocked(SanicException):
    """Resource locked exception"""
    status_code = 423
    message = "Resource is locked"
```

### Using Custom Exceptions

```python
from exceptions import ProductOutOfStock

async def create_order(request):
    product_id = request.json['product_id']
    quantity = request.json['quantity']
    
    product = await Product.get(id=product_id)
    
    # Check stock
    if product.stock < quantity:
        raise ProductOutOfStock(
            f"Product {product.name} stock is insufficient, "
            f"needs {quantity}, current stock {product.stock}"
        )
    
    # Create order
    # ...
```

## Unified Exception Handling

### Global Exception Handler

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
    """Handle 404 errors"""
    return json({
        "error": "Resource not found",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_404_NOT_FOUND)

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    """Handle 403 errors"""
    return json({
        "error": "Insufficient permissions",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_403_FORBIDDEN)

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    """Handle 401 errors"""
    return json({
        "error": "Unauthorized",
        "message": "Please log in first"
    }, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    """Handle 400 errors"""
    return json({
        "error": "Invalid request",
        "message": str(exception)
    }, status=HTTPStatus.HTTP_400_BAD_REQUEST)

@app.exception(Exception)
async def handle_exception(request, exception):
    """Handle uncaught exceptions"""
    # Log detailed error
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra={
            'path': request.path,
            'method': request.method,
            'ip': request.ip,
        }
    )
    
    # Return generic error (do not expose internal information)
    return json({
        "error": "Server internal error",
        "message": "Please try again later"
    }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
```

### Unified Error Response Format

```python
from sanic.response import json as json_response
from srf.views.http_status import HTTPStatus

class ErrorResponse:
    """Unified error response"""
    
    @staticmethod
    def not_found(message="Resource not found", details=None):
        return json_response({
            "error": "NOT_FOUND",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def forbidden(message="Insufficient permissions", details=None):
        return json_response({
            "error": "FORBIDDEN",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def unauthorized(message="Unauthorized", details=None):
        return json_response({
            "error": "UNAUTHORIZED",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def bad_request(message="Invalid request", details=None):
        return json_response({
            "error": "BAD_REQUEST",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def conflict(message="Resource conflict", details=None):
        return json_response({
            "error": "CONFLICT",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_409_CONFLICT)
    
    @staticmethod
    def server_error(message="Server internal error", details=None):
        return json_response({
            "error": "INTERNAL_ERROR",
            "message": message,
            "details": details
        }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)

# Usage
async def get_product(request, product_id):
    product = await Product.get_or_none(id=product_id)
    if not product:
        return ErrorResponse.not_found(f"Product {product_id} does not exist")
    
    # ...
```

## Error Logging

### Configure Logging

```python
import logging
from logging.handlers import RotatingFileHandler

# Create logger
logger = logging.getLogger('app')
logger.setLevel(logging.INFO)

# Console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File output (auto-rotating)
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

### Record Exceptions

```python
@app.exception(Exception)
async def handle_exception(request, exception):
    """Handle uncaught exceptions"""
    # Build error context
    context = {
        'path': request.path,
        'method': request.method,
        'ip': request.ip,
        'user_agent': request.headers.get('User-Agent'),
        'user_id': getattr(request.ctx, 'user', {}).get('id'),
    }
    
    # Log error
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra=context
    )
    
    # Send alert (optional)
    # await send_alert(exception, context)
    
    return json({
        "error": "Server internal error"
    }, status=500)
```

## Development vs Production Environment

### Development Environment

Display detailed error messages for debugging:

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

### Production Environment

Hide internal details and return a generic error:

```python
if not app.config.DEBUG:
    @app.exception(Exception)
    async def handle_exception_prod(request, exception):
        # Log detailed error
        logger.error(f"Error: {exception}", exc_info=True)
        
        # Return generic error
        return json({
            "error": "Server internal error",
            "message": "Please try again later"
        }, status=500)
```

## Complete Example

```python
from sanic import Sanic
from sanic.response import json
from sanic.exceptions import NotFound, Forbidden, Unauthorized, InvalidUsage, SanicException
from srf.views.http_status import HTTPStatus
from pydantic import ValidationError
import logging

app = Sanic("MyApp")
logger = logging.getLogger(__name__)

# Custom exceptions
class BusinessException(SanicException):
    """Business exception base class"""
    status_code = 400

class ProductOutOfStock(BusinessException):
    """Out of stock"""
    message = "Product stock is insufficient"

class InsufficientBalance(BusinessException):
    """Insufficient balance"""
    message = "Account balance is insufficient"

# Unified error response
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
        "message": "Please log in first"
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
    # Log error
    logger.error(
        f"Unhandled exception: {exception}",
        exc_info=True,
        extra={
            'path': request.path,
            'method': request.method,
            'ip': request.ip,
        }
    )
    
    # Return different information based on environment
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
            "message": "Server internal error, please try again later"
        }, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
```

## Best Practices

1. **Classify exceptions**: Use different exception classes for different types of errors
2. **Friendly error messages**: Provide clear and helpful error messages
3. **Unify response format**: Use a consistent error response structure
4. **Log detailed logs**: Log context information for errors
5. **Hide internal details**: Do not expose internal errors in production
6. **Use appropriate status codes**: Use correct HTTP status codes for different errors
7. **Internationalization**: Support multilingual error messages

## Error Code Design

Define error codes for different business errors:

```python
class ErrorCode:
    """Error codes"""
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    
    # Authentication errors (2000-2999)
    UNAUTHORIZED = 2000
    INVALID_TOKEN = 2001
    TOKEN_EXPIRED = 2002
    
    # Permission errors (3000-3999)
    FORBIDDEN = 3000
    INSUFFICIENT_PERMISSIONS = 3001
    
    # Resource errors (4000-4999)
    NOT_FOUND = 4000
    ALREADY_EXISTS = 4001
    
    # Business errors (5000-5999)
    OUT_OF_STOCK = 5000
    INSUFFICIENT_BALANCE = 5001

# Usage
return json({
    "error": {
        "code": ErrorCode.OUT_OF_STOCK,
        "message": "Product stock is insufficient",
        "details": {"product_id": product_id, "available": 0}
    }
}, status=400)
```

## Next Steps

- Learn [HTTP Status Codes](http-status.md) to understand their usage
- Read [Authentication](../core/authentication.md) to understand authentication exceptions
- View [Views](../core/viewsets.md) to understand exception handling in ViewSet