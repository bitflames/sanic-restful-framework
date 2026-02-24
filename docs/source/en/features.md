# Features

Sanic RESTful Framework (SRF) provides a complete set of tools and features to help you quickly build high-quality RESTful APIs.

## Core Features

### 🎯 Class-based ViewSets

ViewSet is the core concept of SRF, providing an elegant way to organize and manage API endpoints.

**Features:**

- Automatically generates standard RESTful routes
- Built-in CRUD basic view functions (Create, Read, Update, Delete, List)
- Supports Mixin pattern for flexible function combination
- Easily add custom route view functions using `@action` decorator
- Fast development with an experience close to Django REST Framework

**Advantages:**

- Reduce repetitive code and improve development efficiency
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

- Defined using `@action` decorator
- Automatically discovered and registered
- Supports collection-level and detail-level operations

### 🔐 Comprehensive Authentication System

SRF provides multiple authentication methods to meet different scenario requirements.

**Supported Authentication Methods:**

- **JWT Authentication**: Stateless authentication based on JSON Web Token
- **Social Login**: Supports GitHub OAuth (can be extended to other platforms)
- **Email Verification**: Built-in email verification code functionality

**Authentication Features:**

- **Automatic token verification**: Authentication middleware automatically validates JWT tokens
- User role and permission management
- Password encryption storage (bcrypt)
- Public endpoint configuration

### 🛡️ Flexible Permission System

A class-based permission system that supports view-level and object-level permission control.

**Built-in Permission Classes:**

- `IsAuthenticated`: The user must be authenticated
- `IsRoleAdminUser`: The user must be an admin role
- `IsSafeMethodOnly`: Only allows safe HTTP methods (GET, HEAD, OPTIONS)
- Custom permission control based on `BasePermission`

### 📊 Powerful Data Processing

#### Data Validation and Serialization

- Data validation based on **Pydantic**
- Automatic data serialization and deserialization
- Supports separation of read and write schemas
- Type-safe and IDE-friendly

#### Filter System

SRF provides various filters that can be used in combination:

1. **SearchFilter**: Full-text search filter
2. **JsonLogicFilter**: Supports complex JSON Logic expressions
3. **QueryParamFilter**: Precise filtering based on query parameters
4. **OrderingFactory**: Sorting functionality

#### Pagination

- Page number-based pagination
- Configurable number of items per page
- Returns a unified pagination response format

### 🚦 Rate Limiting Middleware

Protect your API from abuse, supporting multiple rate-limiting strategies:

- **IPRateLimit**: Rate limiting based on IP address
- **UserRateLimit**: Rate limiting based on user ID
- **PathRateLimit**: Rate limiting based on request path
- **HeaderRateLimit**: Rate limiting based on request headers

**Storage Methods:**

- In-memory storage (MemoryStorage)
- Support for external storage such as Redis, which is extensible

### 🏥 Health Check

Built-in health check feature to monitor the status of the application and dependent services.

**Supported Service Checks:**

- Redis
- PostgreSQL
- MongoDB
- SQLite

**Features:**

- Automatically detects service availability
- Returns standardized health status responses
- Easy to integrate into monitoring systems

### 🔧 Useful Tools

#### HTTP Status Codes

- Complete HTTP status code enumeration
- Semantic constant naming (e.g., `HTTP_200_OK`, `HTTP_404_NOT_FOUND`)
- Status code type checking functions

#### Exception Handling

- Unified exception handling mechanism
- Custom exception classes
- Automatically converts to standard HTTP responses

#### Email Sending

- Asynchronous email sending based on aiosmtplib
- Supports HTML and plain text emails
- Flexible configuration, easy to use

## Design Philosophy

### Convention Over Configuration

SRF follows the principle of "convention over configuration," providing reasonable default configurations so you can start developing quickly. It also maintains high configurability, allowing you to customize any behavior when needed.

### Modular and Expandable

SRF uses a modular design, where each feature is an independent module that can be selected as needed. It also provides clear extension points, making it easy for you to add custom features.

### Type Safety

Through Pydantic and type annotations, SRF provides good type safety, reducing runtime errors and improving code quality.

### Asynchronous First

Leveraging Python's asyncio features and Sanic's asynchronous architecture, SRF provides high-performance API services.

## Performance Advantages

- **Asynchronous I/O**: Native support for async/await, fast event loop based on uvloop, performance far exceeds synchronous frameworks
- **Efficient Routing**: Automatically generates and registers routes, reducing runtime overhead
- **Flexible Caching**: Supports configuring caching strategies to improve response speed
- **Lightweight**: Core features are streamlined, modules are loaded on demand

## Development Experience

### Comprehensive Ecosystem

- Based on Sanic as the base framework, it can perfectly integrate with various frameworks in the ecosystem

### IDE Friendly

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
- ✅ Applications requiring high concurrency processing
- ✅ Microservices architecture
- ✅ Frontend-backend separated projects
- ✅ Mobile application backend
- ✅ Internet of Things (IoT) platform
- ✅ Data API services

## Comparison with Other Frameworks

| Feature              | SRF                                   | FastAPI          | Django REST  |
| -------------------- | ------------------------------------- | ---------------- | ------------ |
| Asynchronous Support | ✅ Full                               | ✅ Full          | ⚠️ Partial   |
| Performance          | 🚀 Very High                          | 🚀 High          | ⚡ Medium    |
| Development Speed    | Very Fast                             | Fast             | Very Fast    |
| Learning Curve       | 📈 Gentle                             | 📈 Gentle        | 📈 Steep     |
| ViewSet              | ✅ Supported                          | ❌ Not Supported | ✅ Supported |
| Data Validation      | Pydantic                              | Pydantic         | Serializer   |
| ORM                  | Tortoise (other ORMs can be extended) | SQLAlchemy/Other | Django ORM   |
| Community            | 🌱 Growing                            | 🌳 Active        | 🌲 Mature    |

## Next Steps

Now that you have understood the main features of SRF, you can:

- View [Getting Started](usage/getting-started.md) to create your first project
- Read [Core Concepts](usage/core/viewsets.md) to learn more about the usage of ViewSet
- Browse [API Reference](api-reference.md) to see detailed API documentation
