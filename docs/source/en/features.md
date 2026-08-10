# Features

Sanic RESTful Framework (SRF) provides a complete set of tools and features to help you quickly build high-quality RESTful APIs.

## Core Features

### 🎯 Class-based ViewSets

ViewSet is the core concept of SRF, offering an elegant way to organize and manage API endpoints.

**Features:**

- Automatically generates standard RESTful routes
- Built-in CRUD basic view functions (Create, Read, Update, Delete, List)
- Supports Mixin pattern for flexible function combinations
- Easily add custom route view functions using `@action` decorator
- Rapid development, close to Django REST Framework development experience

**Advantages:**

- Reduce duplicate code, improve development efficiency
- Unified code style and structure
- Easy to test and maintain

### 🎨 Automatic Route Generation

SanicRouter automatically generates routes for ViewSets:

**Standard Routes:**

- `GET /api/resource` → list
- `POST /api/resource` → create
- `GET /api/resource/<pk>` → retrieve
- `PUT/PATCH /api/resource/<pk>` → update
- `DELETE /api/resource/<pk>` → destroy

**Custom Routes:**

- Defined via `@action` decorator
- Automatically discovered and registered
- Supports collection-level and detail-level operations

### 🔐 Authentication Components

SRF provides various authentication methods to meet different scenario needs.

**Supported Authentication Methods:**

- **JWT Authentication**: Stateless authentication based on JSON Web Token
- **Social Login**: Supports GitHub OAuth (extensible to other platforms)
- **Email Verification**: Built-in email verification code function

**Authentication Features:**

- Automatic token validation
- User role and permission management
- Password encryption storage (bcrypt)
- Public endpoint configuration

### 🛡️ Flexible Permission System

Based on class-based permission system, supports view-level and object-level permission control.

**Built-in Permission Classes:**

- `AllowAny`: Always allow (default when `permission_classes` is undeclared)
- `IsAuthenticated`: User must be authenticated
- `IsRoleAdminUser`: User must be an admin role
- `IsSafeMethodOnly`: Only allow safe HTTP methods (GET, HEAD, OPTIONS)
- Custom permission control based on `BasePermission`

### 📊 Powerful Data Processing

#### Data Validation and Serialization

- Data validation based on **Pydantic**
- Automatic data serialization and deserialization
- Supports read/write Schema separation
- Type-safe, IDE-friendly

#### Filtering System

SRF provides multiple filters that can be used in combination:

1. **SearchFilter**: Full-text search filter
2. **JsonLogicFilter**: Supports complex JSON Logic expressions
3. **QueryParamFilter**: Precise filtering based on query parameters
4. **OrderingFactory**: Sorting functionality

#### Pagination

- Page number-based pagination
- Configurable number per page
- Returns a unified pagination response format

### 🚦 Rate Limiting Middleware

Protect your API from abuse, supports various rate limiting strategies:

- **IPRateLimit**: Rate limit based on IP address
- **UserRateLimit**: Rate limit based on user ID
- **PathRateLimit**: Rate limit based on request path
- **HeaderRateLimit**: Rate limit based on request header

**Storage Options:**

- In-memory storage (MemoryStorage)
- Support for external storage like Redis

### 🏥 Health Check

Built-in health check functionality to monitor application and dependent service status. Register the check classes to be run by configuring `HEALTH_CHECK_LIST`.

**Built-in Service Checks:**

- `RedisCheck` (Redis)
- `SQLiteCheck` (SQLite)

**Features:**

- Automatically detect service availability
- Return standardized health status response
- Easy to integrate into monitoring systems

### 🔧 Useful Tools

#### HTTP Status Codes

- Complete HTTP status code enumeration
- Semantic constant naming (e.g., `HTTP_200_OK`, `HTTP_404_NOT_FOUND`)
- Status code type checking functions

#### Exception Handling

- Some exceptions are converted within ViewSet
- Custom exception classes
- Global uniform response requires application to register Sanic exception handler

#### Email Sending

- Synchronous SMTP via standard-library `smtplib` (`srf/tools/email.py`)
- `send_email(to_email, subject, content)` sends plain-text emails (sync)
- `send_verify_code(to_email, code)` is an async wrapper using `asyncio.to_thread` so the event loop is not blocked
- Registration codes support Redis TTL, resend cooldown, and cleanup on send failure

## Design Philosophy

### Convention Over Configuration

SRF follows the "Convention Over Configuration" principle, providing reasonable default configurations to let you start development quickly. At the same time, it maintains a high degree of configurability, allowing you to customize any behavior when needed.

### Modular and Extensible

SRF uses a modular design, with each feature being an independent module that can be selected as needed. It also provides clear extension points, making it easy for you to add custom features.

### Type Safety

Through Pydantic and type annotations, SRF provides good type safety, reducing runtime errors and improving code quality.

### Asynchronous First

Fully utilizes Python's asyncio features and Sanic's asynchronous architecture, providing high-performance API services.

## Performance Advantages

- **Asynchronous I/O**: Based on Sanic, native support for async/await
- **Efficient Routing**: Automatically generates and registers routes, reducing runtime overhead
- **Flexible Caching**: Supports configured caching strategies to improve response speed
- **Lightweight**: Core features are concise, modules are loaded on demand

## Development Experience

### Comprehensive Ecosystem
- Based on Sanic framework, can perfectly integrate with various frameworks in the ecosystem

### IDE-Friendly

- Complete type annotations
- Clear code structure
- Good code suggestions and auto-completion

### Easy to Test

- Class-based design facilitates unit testing
- Clear interfaces and separation of responsibilities
- Supports Mock and dependency injection

### Comprehensive Documentation

- Detailed multilingual documentation
- Rich code examples
- API reference documentation

## Applicable Scenarios

SRF is suitable for the following scenarios:

- ✅ Building RESTful API services
- ✅ Applications requiring high concurrency handling
- ✅ Microservices architecture
- ✅ Front-end and back-end separated projects
- ✅ Mobile application backend
- ✅ Internet of Things (IoT) platform
- ✅ Data API services

## Comparison with Other Frameworks

| Feature | SRF | FastAPI | Django REST |
|--------|-----|---------|-------------|
| Asynchronous Support | ✅ Complete | ✅ Complete | ⚠️ Partial |
| Performance | 🚀 High | 🚀 Moderate | ⚡ Medium |
| Development Speed | Very Fast | Fast | Very Fast |
| Learning Curve | 📈 Gentle | 📈 Gentle | 📈 Steep |
| ViewSet | ✅ Supported | ❌ Not Supported | ✅ Supported |
| Data Validation | Pydantic | Pydantic | Serializer |
| ORM | Tortoise (other ORMs available) | SQLAlchemy/Other | Django ORM |
| Community | 🌱 Growing | 🌳 Active | 🌲 Mature |

## Next Steps

Now that you've learned about the main features of SRF, you can:

- View [Getting Started](usage/getting-started.md) to create your first project
- Read [Core Concepts](usage/core/viewsets.md) to understand the usage of ViewSet
- Browse [API Reference](api-reference.md) to see detailed API documentation