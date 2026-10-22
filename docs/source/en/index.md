# Sanic RESTful Framework

Welcome to Sanic RESTful Framework (SRF) — a powerful and flexible RESTful API development framework built on [Sanic](https://sanic.dev/).

## What is SRF?

Sanic RESTful Framework (hereafter referred to as SRF) is a modern RESTful API development framework designed for [Sanic](https://sanic.dev/) applications. It provides a complete set of tools and best practices to help you quickly build high-performance web APIs.

SRF is inspired by Django REST framework (hereafter referred to as DRF), bringing its excellent design concepts to the asynchronous Sanic ecosystem. If you are familiar with DRF, you will be able to get started with SRF quickly. Even if you are not familiar with DRF, that is fine — SRF's convenience will certainly help you build your application quickly!

## Why choose SRF?

- **🚀 High performance**: Built on [Sanic](https://sanic.dev/), with outstanding performance
- **📦 Common components**: Provides authentication, permissions, pagination, filtering, rate limiting, and other foundational components
- **🎯 Simple and easy to use**: Offers an experience closest to Django REST Framework, with a gentle learning curve
- **🔧 Flexible and extensible**: Modular design makes customization and extension easy
- **🔒 Security extension points**: Provides JWT, permission, and rate limiting components; production security still requires application configuration and auditing
- **📊 Ready out of the box**: Provides health checks, exception handling, HTTP status codes, and other practical utilities

## Main features

### ViewSet and routing

- Class-based view sets (ViewSet) that automatically generate RESTful routes
- Supports standard CRUD operations (Create, Read, Update, Delete, List, etc.)
- Easily add custom actions with the `@action` decorator
- Automatic route discovery and registration

### Authentication and authorization

- JWT (JSON Web Token) authentication support
- Social login integration (GitHub OAuth, etc.)
- Flexible permission system (IsAuthenticated, SafeMethodOnly, SuperuserOnly, etc.)
- Provides authentication middleware utilities that the application must wire in according to its routing strategy

### Data processing

- Data validation and serialization based on Pydantic
- Page-number pagination and sorting

### Security features

- Rate limiting middleware (based on IP, user, path, etc.)
- CSRF protection is implemented by the application according to its authentication approach
- Password encryption (bcrypt)
- Authentication keys must be configured explicitly by the application

## Quick preview

Here is a simple example showing how to create a RESTful API with SRF:

```python
from sanic import Sanic
from srf.views import BaseViewSet
from srf.route import SanicRouter

from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.sanic import register_tortoise
from pydantic import BaseModel, ConfigDict


# Define the ORM model
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    description = fields.TextField()


# Define the Schema model
class ProductSchema(BaseModel):
    id: int | None = None
    name: str
    price: float
    description: str
    model_config = ConfigDict(from_attributes=True)


# Define the ViewSet
class ProductViewSet(BaseViewSet):
    schema = ProductSchema

    @property
    def queryset(self):
        return Product.all()


# Create the application and routes
app = Sanic("MyApp")
register_tortoise(app, db_url=*, modules=*})
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Once the routes are registered, these ViewSet endpoints are available:

- `GET /api/products` - Get the product list
- `POST /api/products` - Create a new product
- `GET /api/products/<pk>` - Get a single product
- `PUT/PATCH /api/products/<pk>` - Update a product
- `DELETE /api/products/<pk>` - Delete a product

## Next steps

- See [Features](features.md) to learn about everything SRF can do
- Read [Getting Started](usage/getting-started.md) to start your first project
- Browse the [API Reference](api/views.md) for detailed API documentation

## Community and support

- **GitHub**: [sanic-restful-framework](https://github.com/bitflames/sanic-restful-framework)
- **Issue feedback**: If you find a bug or have a feature suggestion, please submit an issue on GitHub
- **Contribute code**: Pull Requests to help improve SRF are welcome

## License

Sanic RESTful Framework is released under the MIT License.
