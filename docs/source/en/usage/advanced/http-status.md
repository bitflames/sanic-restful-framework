# HTTP Status

SRF provides enums for common HTTP status codes, making it convenient to use semantic constants in code.

## Overview

Benefits of using status code constants:

- **Readability**: `HTTP_200_OK` is clearer than `200`
- **Type safety**: avoid mistyping status codes
- **IDE support**: provides autocompletion and documentation hints
- **Consistency**: teams use consistent status codes

## Import

```python
from srf.views.http_status import HTTPStatus
```

## Status code categories

### 1xx - Informational responses

| Status code | Constant                       | Description         |
| ----------- | ------------------------------ | ------------------- |
| 100         | `HTTP_100_CONTINUE`            | Continue            |
| 101         | `HTTP_101_SWITCHING_PROTOCOLS` | Switching protocols |

```python
from srf.views.http_status import is_informational

# Check whether it is an informational response
if is_informational(status_code):
    print("Informational response")
```

### 2xx - Successful responses

| Status code | Constant              | Description | Use case                                     |
| ----------- | --------------------- | ----------- | -------------------------------------------- |
| 200         | `HTTP_200_OK`         | OK          | GET, PUT, PATCH succeeded                    |
| 201         | `HTTP_201_CREATED`    | Created     | POST created a resource successfully         |
| 202         | `HTTP_202_ACCEPTED`   | Accepted    | Request accepted for asynchronous processing |
| 204         | `HTTP_204_NO_CONTENT` | No content  | DELETE succeeded                             |

```python
from sanic.response import HTTPResponse, json

# GET request succeeded
return json(data, status=HTTPStatus.HTTP_200_OK)

# POST created successfully
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# DELETE succeeded (204 should not carry a JSON body)
return HTTPResponse(status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### 3xx - Redirects

| Status code | Constant                     | Description        |
| ----------- | ---------------------------- | ------------------ |
| 301         | `HTTP_301_MOVED_PERMANENTLY` | Permanent redirect |
| 302         | `HTTP_302_FOUND`             | Temporary redirect |
| 304         | `HTTP_304_NOT_MODIFIED`      | Not modified       |

```python
from sanic.response import redirect

# Permanent redirect
return redirect("/new-url", status=HTTPStatus.HTTP_301_MOVED_PERMANENTLY)

# Temporary redirect
return redirect("/temp-url", status=HTTPStatus.HTTP_302_FOUND)
```

### 4xx - Client errors

| Status code | Constant                        | Description          | Use case                                       |
| ----------- | ------------------------------- | -------------------- | ---------------------------------------------- |
| 400         | `HTTP_400_BAD_REQUEST`          | Bad request          | Invalid parameters or format                   |
| 401         | `HTTP_401_UNAUTHORIZED`         | Unauthorized         | Not logged in, invalid token                   |
| 403         | `HTTP_403_FORBIDDEN`            | Forbidden            | Insufficient permissions                       |
| 404         | `HTTP_404_NOT_FOUND`            | Not found            | Resource does not exist                        |
| 405         | `HTTP_405_METHOD_NOT_ALLOWED`   | Method not allowed   | HTTP method is not supported                   |
| 409         | `HTTP_409_CONFLICT`             | Conflict             | Resource conflict (such as duplicate creation) |
| 422         | `HTTP_422_UNPROCESSABLE_ENTITY` | Unprocessable entity | Data validation failed                         |
| 429         | `HTTP_429_TOO_MANY_REQUESTS`    | Too many requests    | Rate limit exceeded                            |

```python
from sanic.response import HTTPResponse, json

# Invalid parameters
if not data:
    return json({"error": "Missing parameters"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

# Not logged in
if not user:
    return json({"error": "Not logged in"}, status=HTTPStatus.HTTP_401_UNAUTHORIZED)

# Insufficient permissions
if not user.is_admin:
    return json({"error": "Insufficient permissions"}, status=HTTPStatus.HTTP_403_FORBIDDEN)

# Resource does not exist
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

### 5xx - Server errors

| Status code | Constant                         | Description           | Use case                |
| ----------- | -------------------------------- | --------------------- | ----------------------- |
| 500         | `HTTP_500_INTERNAL_SERVER_ERROR` | Internal server error | Uncaught exception      |
| 501         | `HTTP_501_NOT_IMPLEMENTED`       | Not implemented       | Feature not implemented |
| 502         | `HTTP_502_BAD_GATEWAY`           | Bad gateway           | Upstream service error  |
| 503         | `HTTP_503_SERVICE_UNAVAILABLE`   | Service unavailable   | Maintenance or overload |

```python
# Server error
try:
    result = await process_data()
except Exception as e:
    logger.error(f"Error: {e}")
    return json({"error": "Server error"}, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)

# Service unavailable
if not healthy:
    return json({"error": "Service under maintenance"}, status=HTTPStatus.HTTP_503_SERVICE_UNAVAILABLE)
```

## Helper functions

### Checking status code categories

```python
from srf.views.http_status import (
    is_informational,
    is_success,
    is_redirect,
    is_client_error,
    is_server_error,
)

# Whether it is an informational response (1xx)
is_informational(100)  # True

# Whether it is a successful response (2xx)
is_success(200)  # True
is_success(201)  # True

# Whether it is a redirect (3xx)
is_redirect(301)  # True

# Whether it is a client error (4xx)
is_client_error(400)  # True
is_client_error(404)  # True

# Whether it is a server error (5xx)
is_server_error(500)  # True
is_server_error(503)  # True
```

## Using them in ViewSets

### Basic usage

```python
from sanic.exceptions import NotFound
from sanic.response import HTTPResponse, json
from srf.views import BaseViewSet
from srf.views.http_status import HTTPStatus


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """Create a product"""
        # Validate the data
        schema_class = self.get_schema()
        try:
            schema = schema_class.model_validate(request.json, strict=True)
        except Exception as e:
            return json({"error": str(e)}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

        # Check whether it already exists
        if await Product.filter(sku=schema.sku).exists():
            return json({"error": "SKU already exists"}, status=HTTPStatus.HTTP_409_CONFLICT)

        # Create
        obj = await Product.create(**schema.model_dump(by_alias=False))

        # Serialize
        data = schema_class.model_validate(obj, from_attributes=True).model_dump(mode="json")

        # Return 201 Created
        return json(data, status=HTTPStatus.HTTP_201_CREATED)

    async def destroy(self, request, pk):
        """Delete a product"""
        # Get the object
        try:
            obj = await self.get_object(pk)
        except NotFound:
            return json({"error": "Product not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

        # Delete
        await obj.delete()

        # Return 204 No Content
        return HTTPResponse(status=HTTPStatus.HTTP_204_NO_CONTENT)
```

### Custom actions

```python
from srf.views.decorators import action


class ProductViewSet(BaseViewSet):
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish a product"""
        # Get the product
        try:
            product = await self.get_object(pk)
        except NotFound:
            return json({"error": "Product not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

        # Check the status
        if product.is_published:
            return json({"error": "Product already published"}, status=HTTPStatus.HTTP_409_CONFLICT)

        # Publish
        product.is_published = True
        await product.save()

        return json({"message": "Published successfully"}, status=HTTPStatus.HTTP_200_OK)
```

## Common scenarios

### Standard RESTful API responses

| Operation | Method    | Success status code | Failure status codes                                     |
| --------- | --------- | ------------------- | -------------------------------------------------------- |
| List      | GET       | 200 OK              | 400 Bad Request                                          |
| Detail    | GET       | 200 OK              | 404 Not Found                                            |
| Create    | POST      | 201 Created         | 400 Bad Request, 409 Conflict, 422 Unprocessable Entity  |
| Update    | PUT/PATCH | 200 OK              | 400 Bad Request, 404 Not Found, 422 Unprocessable Entity |
| Delete    | DELETE    | 204 No Content      | 404 Not Found                                            |

### Asynchronous tasks

```python
@action(methods=["post"], detail=False, url_path="import")
async def import_products(self, request):
    """Bulk import products (asynchronous task)"""
    file = request.files.get("file")

    if not file:
        return json({"error": "Missing file"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

    # Create an asynchronous task
    task_id = await create_import_task(file)

    # Return 202 Accepted
    return json({
        "message": "Task created",
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}"
    }, status=HTTPStatus.HTTP_202_ACCEPTED)
```

### Conditional requests

```python
async def retrieve(self, request, pk):
    """Get a product (with conditional request support)"""
    product = await self.get_object(pk)

    # Check If-None-Match
    etag = f'"{product.id}-{product.updated_at.timestamp()}"'
    if_none_match = request.headers.get("If-None-Match")

    if if_none_match == etag:
        # Not modified
        return json({}, status=HTTPStatus.HTTP_304_NOT_MODIFIED)

    # Return the data
    schema = self.get_schema()
    data = schema.model_validate(product).model_dump()

    response = json(data, status=HTTPStatus.HTTP_200_OK)
    response.headers["ETag"] = etag
    return response
```

## Complete constant list

See [HTTP Status API](../../api/http-status.md) for the complete list of `HTTPStatus` enum members.

## Best practices

1. **Use semantic constants**: use `HTTP_200_OK` instead of `200`
2. **Choose status codes correctly**: use the appropriate status code for each situation
3. **Consistency**: teams should use a consistent status code standard
4. **Documentation**: describe the status codes of each endpoint in the API documentation
5. **Client-friendly**: provide clear error messages and status codes
6. **Follow RESTful conventions**: follow standard REST API status code conventions

## Common mistakes

### ❌ Incorrect

```python
# Return 200 for all errors
return json({"error": "not found"}, status=200)

# Use magic numbers
return json(data, status=201)

# Wrong status code
# Return 200 instead of 204 on successful delete
return json({"message": "deleted"}, status=200)
```

### ✅ Correct

```python
from sanic.response import HTTPResponse

# Use semantic constants
return json(data, status=HTTPStatus.HTTP_201_CREATED)

# Use the appropriate status code
if not found:
    return json({"error": "not found"}, status=HTTPStatus.HTTP_404_NOT_FOUND)

# Return 204 on successful delete
return HTTPResponse(status=HTTPStatus.HTTP_204_NO_CONTENT)
```

## Next steps

- Study [Exception Handling](exceptions.md) to learn about the relationship between exceptions and status codes
- Read [Views](../core/viewsets.md) to learn about using status codes in ViewSets
- See the [HTTP Status API](../../api/http-status.md) for the complete constant list
