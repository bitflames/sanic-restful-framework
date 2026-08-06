# Sanic RESTful Framework

Welcome to Sanic RESTful Framework (SRF) — a powerful and flexible RESTful API development framework based on [Sanic](https://sanic.dev/).

## What is SRF?

Sanic RESTful Framework is a modern RESTful API development framework built on top of the [Sanic](https://sanic.dev/) application, providing a complete set of tools and best practices to help you quickly build high-performance web APIs.

SRF is inspired by Django REST Framework, porting its excellent design concepts into the asynchronous Sanic ecosystem. If you are familiar with DRF (Django REST framework), you will quickly get up to speed with SRF (Sanic RESTful Framework). Even if you are not familiar with DRF, SRF's convenience will help you quickly build your application!

## Why choose SRF?

- **🚀 High performance**: Built on [Sanic](https://sanic.dev/), offering exceptional performance
- **📦 Common components**: Provides authentication, permissions, pagination, filtering, rate limiting, and other basic components
- **🎯 Easy to use**: Offers an experience closest to Django REST Framework, with a gentle learning curve
- **🔧 Flexible and scalable**: Modular design, allowing easy customization and extension
- **🔒 Secure extension points**: Provides JWT, permission, and rate limiting components; production security still requires application configuration and audit
- **📊 Ready to use out of the box**: Provides health checks, exception handling, HTTP status codes, and other useful tools

## Main Features

### ViewSet and Routing

- Class-based view sets (ViewSet) that automatically generate RESTful routes
- Supports standard CRUD operations (Create, Read, Update, Delete, List)
- Easily add custom operations using the `@action` decorator
- Automatic route discovery and registration

### Authentication and Authorization

- JWT (JSON Web Token) authentication support
- Social login integration (GitHub OAuth, etc.)
- Flexible permission system (IsAuthenticated, IsRoleAdminUser, etc.)
- Authentication middleware automatically handles user authentication, ensuring request legitimacy

### Data Processing

- Data validation and serialization based on Pydantic
- Out-of-the-box filtering system (search, JSON Logic, query parameters)
- Pagination and sorting features

### Security Features

- Rate limiting middleware (based on IP, user, path, etc.)
- CSRF protection
- Password encryption (bcrypt)
- Public endpoint configuration

## Quick Preview

Here is a simple example showing how to use SRF to create a RESTful API:

```python
import os
from sanic import Sanic

os.environ.setdefault("SECRET_KEY", "development-only-change-me")

from srf.views import BaseViewSet
from srf.route import SanicRouter
from tortoise import fields
from tortoise.models import Model
from pydantic import BaseModel, ConfigDict

# Define ORM model
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    description = fields.TextField()

# Define Schema model
class ProductSchema(BaseModel):
    id: int | None = None
    name: str
    price: float
    description: str
    model_config = ConfigDict(from_attributes=True)

# Define ViewSet
class ProductViewSet(BaseViewSet):
    schema = ProductSchema

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

- View [Features](features.md) to learn all the capabilities of SRF
- Read [Getting Started](usage/getting-started.md) to start your first project
- Browse [API Reference](api-reference.md) for detailed API documentation

## Community and Support

- **GitHub**: [sanic-restful-framework](https://github.com/bitflames/sanic-restful-framework)
- **Issue Feedback**: If you find a bug or have a feature suggestion, please submit an issue on GitHub
- **Contribute Code**: Welcome to submit Pull Requests to help improve SRF

## License

Sanic RESTful Framework is released under the MIT License.