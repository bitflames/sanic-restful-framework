# Sanic RESTful Framework

Welcome to Sanic RESTful Framework (SRF) — a powerful and flexible RESTful API development framework based on [Sanic](https://sanic.dev/).

## What is SRF?

Sanic RESTful Framework is a modern RESTful API development framework built on top of Sanic[Sanic](https://sanic.dev/) application, providing a complete set of tools and best practices to help you quickly build high-performance Web APIs.

Inspired by Django REST Framework, SRF transplants its excellent design concepts into the asynchronous Sanic ecosystem. If you are familiar with the DRF framework, you will be able to get started with SRF quickly. Even if you are not familiar with Django REST Framework, the convenience of SRF will help you build your application quickly!

## Why choose SRF?

- **🚀 High Performance**: Built on [Sanic](https://sanic.dev/), offering exceptional performance
- **📦 Full Functionality**: Includes common features like authentication, permissions, pagination, filtering, and rate limiting
- **🎯 Easy to Use**: Provides an experience closest to Django REST Framework, with a gentle learning curve
- **🔧 Flexible and Extensible**: Modular design allows for easy customization and expansion
- **🔒 Secure and Reliable**: Includes security features such as JWT authentication, CSRF protection, and permission control
- **📊 Ready to Use**: Provides practical tools such as health checks, exception handling, and HTTP status codes

## Key Features

### ViewSet and Routing

- Class-based ViewSets that automatically generate RESTful routes
- Supports standard CRUD operations (Create, Read, Update, Delete, List)
- Easily add custom operations using the `@action` decorator
- Automatic route discovery and registration

### Authentication and Authorization

- JWT (JSON Web Token) authentication support
- Social login integration (GitHub OAuth, etc.)
- Flexible permission system (IsAuthenticated, IsRoleAdminUser, etc.)
- Authentication middleware automatically handles user authentication, ensuring request validity

### Data Processing

- Data validation and serialization based on Pydantic
- Built-in filtering system (search, JSON Logic, query parameters)
- Pagination and sorting functions

### Security Features

- Rate-limiting middleware (based on IP, user, path, etc.)
- CSRF protection
- Password encryption (bcrypt)
- Public endpoint configuration

## Quick Preview

Below is a simple example showing how to use SRF to create a RESTful API:

```python
from sanic import Sanic
from srf.views import BaseViewSet
from srf.route import SanicRouter
from tortoise import fields
from tortoise.models import Model
from pydantic import BaseModel

# Define ORM model
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    description = fields.TextField()

# Define Schema model
class ProductSchema(BaseModel):
    id: int = None
    name: str
    price: float
    description: str

# Define ViewSet
class ProductViewSet(BaseViewSet):
    schema: BaseModel = ProductSchema  # This can also be defined using a get_schema function

    @property
    def queryset(self):
        return Product.all()


# Create application and routes
app = Sanic("MyApp")
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet)
app.blueprint(router.get_blueprint())
```

This creates a complete RESTful API:

- `GET /api/products` - Get product list
- `POST /api/products` - Create a new product
- `GET /api/products/<id>` - Get a single product
- `PUT /api/products/<id>` - Update a product
- `DELETE /api/products/<id>` - Delete a product

## Next Steps

- View [Features](features.md) to learn about all the features of SRF
- Read [Getting Started](usage/getting-started.md) to start your first project
- Browse [API Reference](api-reference.md) to see detailed API documentation

## Community and Support

- **GitHub**: [github.com/\*](https://github.com/bitblames/sanic-restful-framework)
- **Issue Feedback**: If you find a bug or have a feature suggestion, please submit an issue on GitHub
- **Contribute Code**: Welcome to submit Pull Requests to help improve SRF

## License

Sanic RESTful Framework is released under an open source license.
