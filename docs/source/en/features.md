# Features

Sanic RESTful Framework (SRF) provides a complete set of tools and features to help you quickly build high-quality RESTful APIs.

## Core features

### 🎯 Class-based view sets (ViewSet)

ViewSet is the core concept of SRF. It provides an elegant way to organize and manage API endpoints.

**Features:**

- Automatically generates standard RESTful routes
- Built-in basic CRUD view functions (Create, Read, Update, Delete, List)
- Supports the Mixin pattern for flexible composition of functionality
- Easily add custom route view functions with the `@action` decorator
- Fast development with an experience close to Django REST Framework

**Advantages:**

- Reduces duplicated code and improves development efficiency
- Consistent code style and structure
- Easy to test and maintain

### 🎨 Automatic route generation

SanicRouter automatically generates routes for ViewSets:

**Standard routes:**

- `GET /api/resource` → list
- `POST /api/resource` → create
- `GET /api/resource/<pk>` → retrieve
- `PUT/PATCH /api/resource/<pk>` → update
- `DELETE /api/resource/<pk>` → destroy

**Custom routes:**

- Defined with the `@action` decorator
- Automatically discovered and registered
- Supports both collection-level and detail-level actions

### 🔐 Authentication components

SRF provides multiple authentication methods to meet the needs of different scenarios.

**Supported authentication methods:**

- **JWT authentication**: Stateless authentication based on JSON Web Tokens
- **Social login**: Supports GitHub OAuth (other platforms can be extended)
- **Email verification**: Built-in email verification code functionality

**Authentication features:**

- Provides token validation middleware (wired in by the application)
- Permission control through built-in and custom permission classes
- Password storage with encryption (bcrypt)
- The JWT secret must be configured explicitly by the application; authentication middleware is wired in by the application

### 🛡️ Flexible permission system

A class-based permission system that supports view-level and object-level permission control.

**Built-in permission classes:**

- `AllowAny`: Always allow (the default when `permission_classes` is not declared)
- `IsAuthenticated`: The user must be logged in
- `SuperuserOnly`: The user must be a superuser
- `SafeMethodOnly`: Only safe HTTP methods are allowed (GET, HEAD, OPTIONS)
- Implement custom permission control based on `BasePermission`

### 📊 Powerful data processing

#### Data validation and serialization

- Data validation based on **Pydantic**
- Automatic data serialization and deserialization
- Supports separating read and write schemas
- Type-safe and IDE-friendly

#### Filtering system

SRF provides multiple filters that can be combined:

1. **SearchFilter**: Keyword containment matching on fields configured in `search_fields`
2. **QueryParamFilter**: Exact filtering based on query parameters
3. **OrderingFactory**: Sorting functionality
4. And more...

#### Pagination

- Page-number-based pagination
- The page size can be set via a query parameter (maximum 100)
- Returns a unified paginated response format

### 🚦 Rate limiting middleware

Protect your API from abuse with multiple rate limiting strategies:

- **IPRateLimit**: Rate limiting based on IP address
- **UserRateLimit**: Rate limiting based on user ID
- **PathRateLimit**: Rate limiting based on request path plus user/IP
- **HeaderRateLimit**: Rate limiting based on request headers

**Storage backends:**

- In-memory storage (MemoryStorage)
- Redis storage (RedisStorage)

### 🏥 Health checks

Built-in health check functionality to monitor the status of the application and its dependencies. Register the check classes to run via the `HEALTH_CHECK_LIST` configuration.

**Built-in service checks:**

- `RedisCheck` (Redis)
- `SQLiteCheck` (SQLite)

**Features:**

- Runs the configured checks and returns a status mapping
- The response remains HTTP 200 even when a check fails
- Easy to integrate into monitoring systems

### 📝 Audit events

SRF provides an `Event` model, `EventSchema`, and a superuser-only `EventViewSet` for creating, listing, and reading events. Events must be written by the application itself; the framework does not automatically record every request.

### 🔧 Utilities

#### HTTP status codes

- Enums for common HTTP status codes
- Semantic constant names (such as `HTTP_200_OK`, `HTTP_404_NOT_FOUND`)

#### Exception handling

- Converts some exceptions within ViewSets
- Custom exception classes
- Global unified responses require the application to register Sanic exception handlers

#### Email sending

- Synchronous SMTP based on the standard library `smtplib` (`srf/tools/email.py`)
- `send_email(to_email, subject, content)` sends HTML content emails (synchronous)
- `send_template_email(...)` provides asynchronous template email sending, executing SMTP in a thread internally
- Registration verification codes default to six digits and support Redis TTL and failure-count limits

## Design philosophy

### Convention over configuration

SRF follows the principle of "convention over configuration", providing sensible defaults so you can start developing quickly. At the same time it remains highly configurable, letting you customize any behavior when needed.

### Modular and extensible

SRF is modular by design: every feature is an independent module that you can use as needed. It also provides clear extension points for adding custom functionality.

### Type safety

Through Pydantic and type annotations, SRF provides good type safety, reducing runtime errors and improving code quality.

### Async first

SRF fully leverages Python's asyncio features and Sanic's asynchronous architecture to deliver high-performance API services.

## Performance advantages

- **Asynchronous I/O**: Built on Sanic with native async/await support
- **Efficient routing**: Routes are generated and registered automatically, reducing runtime overhead
- **Modular**: Components are wired in as needed; data caching is left to the application
- **Lightweight**: A lean core with modules loaded on demand

## Developer experience

### A mature ecosystem

- Built on Sanic as the foundation, it integrates seamlessly with frameworks across the ecosystem

### IDE-friendly

- Complete type annotations
- Clear code structure
- Good code hints and autocompletion

### Easy to test

- Class-based design facilitates unit testing
- Clear interfaces and separation of responsibilities
- Supports mocking and dependency injection

### Well documented

- Detailed documentation in multiple languages
- Rich code examples
- API reference documentation

## Use cases

SRF is suitable for the following scenarios:

- ✅ Building RESTful API services
- ✅ Applications that require high concurrency
- ✅ Microservice architectures
- ✅ Projects with separated frontend and backend
- ✅ Mobile application backends
- ✅ IoT platforms
- ✅ Data API services

## Comparison with other frameworks

| Feature           | Sanic RESTful Framework                     | FastAPI           | Django REST framework |
| ----------------- | ------------------------------------------- | ----------------- | --------------------- |
| Async support     | ✅ Complete                                 | ✅ Complete       | ⚠️ Partial            |
| Performance       | 🚀 Very high                                | 🚀 High           | ⚡ Medium             |
| Development speed | Very fast                                   | Fast              | Very fast             |
| Learning curve    | 📈 Gentle                                   | 📈 Gentle         | 📈 Steep              |
| ViewSet           | ✅ Supported                                | ❌ Not supported  | ✅ Supported          |
| Data validation   | Pydantic                                    | Pydantic          | Serializer            |
| ORM               | Tortoise (other ORM extensions in progress) | SQLAlchemy/others | Django ORM            |
| Community         | 🌱 Growing                                  | 🌳 Active         | 🌲 Mature             |

## Next steps

Now that you understand the main features of SRF, you can:

- See [Getting Started](usage/getting-started.md) to create your first project
- Read [Core Concepts](usage/core/viewsets.md) to dive into using ViewSets
- Browse the [API Reference](api/views.md) for detailed API documentation
