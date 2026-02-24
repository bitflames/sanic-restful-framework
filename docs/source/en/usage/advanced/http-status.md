# HTTP Status Codes

SRF provides a complete HTTP status code enumeration, making it convenient to use semantic constants in code.

## Overview

Benefits of using status code constants:

- **Readability**: `HTTP_200_OK` is clearer than `200`
- **Type Safety**: Avoid input errors in status codes
- **IDE Support**: Provide auto-completion and documentation hints
- **Unified Standards**: Use consistent status codes across the team

## Import

```python
from srf.views.http_status import HTTPStatus
```

## Status Code Classification

### 1xx - Informational Responses

| Status Code | Constant | Description |
|-------------|----------|-------------|
| 100 | `HTTP_100_CONTINUE` | Continue |
| 101 | `HTTP_101_SWITCHING_PROTOCOLS` | Switching Protocols |

```python
from srf.views.http_status import HTTPStatus

# Check if it's an informational response
if HTTPStatus.is_informational(status_code):
    print("Informational response")
```

### 2xx - Successful Responses

| Status Code | Constant | Description | Use Case |
|-------------|----------|-------------|----------|
| 200 | `HTTP_200_OK` | OK | GET, PUT, PATCH successful |
| 201 | `HTTP_201_CREATED` | Created | POST successfully created a resource |
| 202 | `HTTP_202_ACCEPTED` | Accepted | Asynchronous request processing |
| 204 | `HTTP_204_NO_CONTENT` | No Content | DELETE successful |

```python
from sanic.response import json

# GET request successful
return json(data, status=HTTPStatus.HTTP_200_OK)

# POST creation successful
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# DELETE successful
return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### 3xx - Redirection

| Status Code | Constant | Description |
|-------------|----------|-------------|
| 301 | `HTTP_301_MOVED_PERMANENTLY` | Moved Permanently |
| 302 | `HTTP_302_FOUND` | Found |
| 304 | `HTTP_304_NOT_MODIFIED` | Not Modified |

```python
from sanic.response import redirect

# Permanent redirection
return redirect('/new-url', status=HTTPStatus.HTTP_301_MOVED_PERMANENTLY)

# Temporary redirection
return redirect('/temp-url', status=HTTPStatus.HTTP_302_FOUND)
```

### 4xx - Client Errors

| Status Code | Constant | Description | Use Case |
|-------------|----------|-------------|----------|
| 400 | `HTTP_400_BAD_REQUEST` | Bad Request | Parameter error, format error |
| 401 | `HTTP_401_UNAUTHORIZED` | Unauthorized | Not logged in, invalid Token |
| 403 | `HTTP_403_FORBIDDEN` | Forbidden | Insufficient permissions |
| 404 | `HTTP_404_NOT_FOUND` | Not Found | Resource not found |
| 405 | `HTTP_405_METHOD_NOT_ALLOWED` | Method Not Allowed | HTTP method not supported |
| 409 | `HTTP_409_CONFLICT` | Conflict | Resource conflict (e.g., duplicate creation) |
| 422 | `HTTP_422_UNPROCESSABLE_ENTITY` | Unprocessable Entity | Data validation failed |
| 429 | `HTTP_429_TOO_MANY_REQUESTS` | Too Many Requests | Exceeded rate limit |

```python
from sanic.response import json

# Parameter error
if not data:
    return json({"error": "Missing parameter"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

# Not logged in
if not user:
    return json({"error": "Not logged in"}, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

# Insufficient permissions
if not user.is_admin:
    return json({"error": "Insufficient permissions"}, status=HTTPStatus.HTTP_403_FORBIDDEN)

# Resource not found
if not product:
    return json({"error": "Product not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

# Resource conflict
if exists:
    return json({"error": "Already exists"}, status=HTTPStatus.HTTP_409_CONFLICT)

# Data validation failed
return json({"errors": errors}, status=HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY)

# Rate limiting
return json({"error": "Too many requests"}, status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)
```

### 5xx - Server Errors

| Status Code | Constant | Description | Use Case |
|-------------|----------|-------------|----------|
| 500 | `HTTP_500_INTERNAL_SERVER_ERROR` | Internal Server Error | Uncaught exception |
| 501 | `HTTP_501_NOT_IMPLEMENTED` | Not Implemented | Function not implemented |
| 502 | `HTTP_502_BAD_GATEWAY` | Bad Gateway | Upstream service error |
| 503 | `HTTP_503_SERVICE_UNAVAILABLE` | Service Unavailable | Service maintenance, overload |

```python
# Server error
try:
    result = await process_data()
except Exception as e:
    logger.error(f"Error: {e}")
    return json(
        {"error": "Server error"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )

# Service unavailable
if not healthy:
    return json(
        {"error": "Service under maintenance"},
        status=HTTPStatus.HTTP_503_SERVICE_UNAVAILABLE
    )
```

## Helper Functions

### Checking Status Code Types

```python
from srf.views.http_status import HTTPStatus

# Is it an informational response (1xx)
HTTPStatus.is_informational(100)  # True

# Is it a successful response (2xx)
HTTPStatus.is_success(200)  # True
HTTPStatus.is_success(201)  # True

# Is it a redirection (3xx)
HTTPStatus.is_redirect(301)  # True

# Is it a client error (4xx)
HTTPStatus.is_client_error(400)  # True
HTTPStatus.is_client_error(404)  # True

# Is it a server error (5xx)
HTTPStatus.is_server_error(500)  # True
HTTPStatus.is_server_error(503)  # True
```

## Using in ViewSet

### Basic Usage

```python
from srf.views import BaseViewSet
from srf.views.http_status import HTTPStatus
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """Create product"""
        # Validate data
        schema_class = self.get_schema(request, is_safe=False)
        try:
            schema = schema_class(**request.json)
        except Exception as e:
            return json(
                {"error": str(e)},
                status=HTTPStatus.HTTP_400_BAD_REQUEST
            )
        
        # Check if already exists
        if await Product.filter(sku=schema.sku).exists():
            return json(
                {"error": "SKU already exists"},
                status=HTTPStatus.HTTP_409_CONFLICT
            )
        
        # Create
        obj = await Product.create(**schema.dict())
        
        # Serialize
        reader_schema = self.get_schema(request, is_safe=True)
        data = reader_schema.model_validate(obj).model_dump()
        
        # Return 201 Created
        return json(data, status=HTTPStatus.HTTP_201_CREATED)
    
    async def destroy(self, request, pk):
        """Delete product"""
        # Get object
        try:
            obj = await self.get_object(request, pk)
        except:
            return json(
                {"error": "Product does not exist"},
                status=HTTPStatus.HTTP_404_NOT_FOUND
            )
        
        # Delete
        await obj.delete()
        
        # Return 204 No Content
        return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### Custom Actions

```python
from srf.views.decorators import action

class ProductViewSet(BaseViewSet):
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish product"""
        # Get product
        try:
            product = await self.get_object(request, pk)
        except:
            return json(
                {"error": "Product does not exist"},
                status=HTTPStatus.HTTP_404_NOT_FOUND
            )
        
        # Check status
        if product.is_published:
            return json(
                {"error": "Product already published"},
                status=HTTPStatus.HTTP_409_CONFLICT
            )
        
        # Publish
        product.is_published = True
        await product.save()
        
        return json(
            {"message": "Published successfully"},
            status=HTTPStatus.HTTP_200_OK
        )
```

## Common Scenarios

### RESTful API Standard Response

| Operation | Method | Success Status Code | Failure Status Code |
|---------|--------|--------------------|--------------------|
| List | GET | 200 OK | 404 Not Found |
| Detail | GET | 200 OK | 404 Not Found |
| Create | POST | 201 Created | 400 Bad Request, 409 Conflict, 422 Unprocessable Entity |
| Update | PUT/PATCH | 200 OK | 400 Bad Request, 404 Not Found, 422 Unprocessable Entity |
| Delete | DELETE | 204 No Content | 404 Not Found |

### Asynchronous Tasks

```python
@action(methods=["post"], detail=False, url_path="import")
async def import_products(self, request):
    """Batch import products (asynchronous task)"""
    file = request.files.get('file')
    
    if not file:
        return json(
            {"error": "Missing file"},
            status=HTTPStatus.HTTP_400_BAD_REQUEST
        )
    
    # Create asynchronous task
    task_id = await create_import_task(file)
    
    # Return 202 Accepted
    return json({
        "message": "Task created",
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}"
    }, status=HTTPStatus.HTTP_202_ACCEPTED)
```

### Conditional Requests

```python
async def retrieve(self, request, pk):
    """Get product (supports conditional requests)"""
    product = await self.get_object(request, pk)
    
    # Check If-None-Match
    etag = f'"{product.id}-{product.updated_at.timestamp()}"'
    if_none_match = request.headers.get('If-None-Match')
    
    if if_none_match == etag:
        # Not modified
        return json({}, status=HTTPStatus.HTTP_304_NOT_MODIFIED)
    
    # Return data
    schema = self.get_schema(request, is_safe=True)
    data = schema.model_validate(product).model_dump()
    
    response = json(data, status=HTTPStatus.HTTP_200_OK)
    response.headers['ETag'] = etag
    return response
```

## Complete Status Code List

```python
from srf.views.http_status import HTTPStatus

# 1xx Informational responses
HTTPStatus.HTTP_100_CONTINUE
HTTPStatus.HTTP_101_SWITCHING_PROTOCOLS

# 2xx Success
HTTPStatus.HTTP_200_OK
HTTPStatus.HTTP_201_CREATED
HTTPStatus.HTTP_202_ACCEPTED
HTTPStatus.HTTP_203_NON_AUTHORITATIVE_INFORMATION
HTTPStatus.HTTP_204_NO_CONTENT
HTTPStatus.HTTP_205_RESET_CONTENT
HTTPStatus.HTTP_206_PARTIAL_CONTENT

# 3xx Redirection
HTTPStatus.HTTP_300_MULTIPLE_CHOICES
HTTPStatus.HTTP_301_MOVED_PERMANENTLY
HTTPStatus.HTTP_302_FOUND
HTTPStatus.HTTP_303_SEE_OTHER
HTTPStatus.HTTP_304_NOT_MODIFIED
HTTPStatus.HTTP_305_USE_PROXY
HTTPStatus.HTTP_307_TEMPORARY_REDIRECT
HTTPStatus.HTTP_308_PERMANENT_REDIRECT

# 4xx Client errors
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

# 5xx Server errors
HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
HTTPStatus.HTTP_501_NOT_IMPLEMENTED
HTTPStatus.HTTP_502_BAD_GATEWAY
HTTPStatus.HTTP_503_SERVICE_UNAVAILABLE
HTTPStatus.HTTP_504_GATEWAY_TIMEOUT
HTTPStatus.HTTP_505_HTTP_VERSION_NOT_SUPPORTED
HTTPStatus.HTTP_507_INSUFFICIENT_STORAGE
HTTPStatus.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
```

## Best Practices

1. **Use Semantic Constants**: Use `HTTP_200_OK` instead of `200`
2. **Correctly Choose Status Codes**: Use appropriate status codes for different situations
3. **Consistency**: The team uses a unified standard for status codes
4. **Documentation**: Document the status codes in the API documentation
5. **Client-Friendly**: Provide clear error messages and status codes
6. **Follow RESTful Conventions**: Follow standard REST API status code conventions

## Common Mistakes

### ❌ Incorrect Practice

```python
# Return 200 for all errors
return json({"error": "not found"}, status=200)

# Use magic numbers
return json(data, status=201)

# Incorrect status code
# Return 200 instead of 204 for successful deletion
return json({"message": "deleted"}, status=200)
```

### ✅ Correct Practice

```python
# Use semantic constants
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# Use appropriate status codes
if not found:
    return json({"error": "not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

# Return 204 for successful deletion
return json({}, status=HTTPStatus.HTTP_204_NO_CONTENT)
```

## Next Steps

- Learn about [Exception Handling](exceptions.md) to understand the relationship between exceptions and status codes
- Read [Views](../core/viewsets.md) to learn how to use status codes in ViewSet
- View [API Reference](../../api-reference.md) to see the complete API documentation