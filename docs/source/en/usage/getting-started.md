# Getting Started

This guide walks you through creating your first Sanic RESTful Framework project from scratch.

## Requirements

Before you begin, make sure your environment meets the following requirements:

- **Python**: 3.11 or later
- **pip**: Python package manager
- **Database**: PostgreSQL, MySQL, SQLite, etc. (this tutorial uses SQLite)

## Installation

### 1. Create the project directory

```bash
mkdir bookstore
cd bookstore
```

### 2. Create a virtual environment

Using conda to create an isolated Python environment is recommended:

```bash
# Create a virtual environment named srf
conda create -n srf python=3.11

# Activate the virtual environment
conda activate srf
```

Or use UV:

```bash
uv init
```

### 3. Install SRF

```bash
pip install sanic-restful-framework
# or
uv add sanic-restful-framework
```

### 4. Check the runtime dependencies

Installing SRF automatically installs the core dependencies, including Sanic `>=25.0.0,<26`,
Tortoise ORM `>=1.1.8,<2`, Pydantic `>=2.6.1,<3`, `sanic-jwt`, `redis`,
and `bcrypt`.

`sanic-cors` and `python-dotenv` are optional dependencies, used for CORS integration and loading
configuration from `.env` files respectively; install them separately only when using the corresponding examples.

## Create your first project

Let's create a simple book management API.

### Step 1: Create the application file

Create an `app.py` file:

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.config import settings

# Create the Sanic application
app = Sanic("BookStore")

# Configure SRF
settings.set_app(app)

# Database configuration
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### Step 2: Define the data model

Create a `models.py` file:

```python
from tortoise import fields
from tortoise.models import Model


class Book(Model):
    """Book model"""

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    author = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)

    class Meta:
        table = "books"
```

### Step 3: Define the schemas

Create a `schemas.py` file:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class BookSchemaWriter(BaseModel):
    """Book write schema (used for create and update)"""

    title: str = Field(..., max_length=200)
    author: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)


class BookSchemaReader(BaseModel):
    """Book read schema (used for serialization)"""

    id: int
    title: str
    author: str
    price: float
    stock: int

    model_config = ConfigDict(from_attributes=True)
```

### Step 4: Create the ViewSet

Create a `viewsets.py` file:

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from sanic.response import json
from models import Book
from schemas import BookSchemaWriter, BookSchemaReader


class BookViewSet(BaseViewSet):
    """Book ViewSet"""

    search_fields = ["title", "author"]
    # Both search_fields and filter_fields support alias mapping; dictionaries map query parameter names to ORM fields
    filter_fields = {"author": "author"}

    @property
    def queryset(self):
        return Book.all()

    def get_schema(self):
        # as_view sets self.action; distinguish read/write schemas by ViewSet action name here.
        if self.action in ("list", "retrieve"):
            return BookSchemaReader
        return BookSchemaWriter

    @action(methods=["get"], detail=False, url_path="search")
    async def search_books(self, request):
        """Search books"""
        keyword = request.args.get("q", "")
        books = await Book.filter(title__icontains=keyword)
        data = [BookSchemaReader.model_validate(b).model_dump() for b in books]
        return json({"results": data})
```

### Step 5: Register the routes

Add the imports at the top of `app.py`, then register the ViewSet after `register_tortoise(...)`:

```python
from srf.route import SanicRouter
from viewsets import BookViewSet

router = SanicRouter(app, prefix="api")
router.register("books", BookViewSet, name="books")
```

`SanicRouter` automatically generates collection routes (`/api/books`) and detail routes
(`/api/books/<pk>`) for the ViewSet, and discovers `@action` methods.

### Step 6: Run the application

```bash
python app.py
```

You should see output similar to the following:

```
[2026-02-07 10:00:00 +0800] [12345] [INFO] Goin' Fast @ http://0.0.0.0:8000
[2026-02-07 10:00:00 +0800] [12345] [INFO] Starting worker [12345]
```

## Test the API

Your API is now running. Let's test it!

### 1. Create a book

```bash
curl -X POST http://localhost:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming",
    "author": "John Doe",
    "price": 89.00,
    "stock": 50
  }'
```

Response:

```json
{
  "id": 1,
  "title": "Python Programming",
  "author": "John Doe",
  "price": 89.00,
  "stock": 50
}
```

### 2. Get the book list

```bash
curl http://localhost:8000/api/books
```

Response:

```json
{
  "count": 1,
  "next": false,
  "previous": false,
  "results": [
    {
      "id": 1,
      "title": "Python Programming",
      "author": "John Doe",
      "price": 89.00,
      "stock": 50
    }
  ]
}
```

### 3. Get a single book

```bash
curl http://localhost:8000/api/books/1
```

The response body is the same book object returned by the create endpoint.

### 4. Update a book

```bash
curl -X PUT http://localhost:8000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming (2nd Edition)",
    "author": "John Doe",
    "price": 99.00,
    "stock": 50
  }'
```

Response:

```json
{
  "id": 1,
  "title": "Python Programming (2nd Edition)",
  "author": "John Doe",
  "price": 99.00,
  "stock": 50
}
```

### 5. Filter by field

Parameters declared in `filter_fields` can be used directly for exact filtering:

```bash
curl "http://localhost:8000/api/books?author=John%20Doe"
```

The response structure is the same as the list endpoint, with only matching records in `results`.

### 6. Pagination

```bash
# Get page 1 with 10 items per page
curl "http://localhost:8000/api/books?page=1&page_size=10"
```

The response format is the same as above: `count` is the total, and `results` contains the current page's data.

### 7. Use a custom action

```bash
# The custom action uses the q parameter to search titles
curl "http://localhost:8000/api/books/search?q=Python"
```

Response:

```json
{
  "results": [
    {
      "id": 1,
      "title": "Python Programming (2nd Edition)",
      "author": "John Doe",
      "price": 99.00,
      "stock": 50
    }
  ]
}
```

### 8. Delete a book

```bash
curl -i -X DELETE http://localhost:8000/api/books/1
```

Response: `204 No Content` (no response body).

## Complete project structure

```
bookstore/
├── app.py                 # Application entry point
├── models.py              # Data models
├── schemas.py             # Pydantic schemas
├── viewsets.py            # ViewSets
└── db.sqlite3             # Database file (generated automatically)
```

## Next steps

Congratulations! You have successfully created your first SRF project. Next you can:

1. **Add authentication**: see [Authentication](core/authentication.md) to add JWT authentication to your API
2. **Add permission control**: read [Permissions](core/permissions.md) to restrict user access
3. **Learn more about ViewSets**: study the advanced usage of [Views](core/viewsets.md)
4. **Configure the project**: see [Project Setup](project-setup.md) for more configuration options

## FAQ

### How do I change the database?

Change `db_url` in `register_tortoise`:

```python
# PostgreSQL
db_url = "postgres://user:password@localhost:5432/dbname"

# MySQL
db_url = "mysql://user:password@localhost:3306/dbname"

# SQLite
db_url = "sqlite://db.sqlite3"
```

### How do I disable automatic schema generation?

Set `generate_schemas=False`:

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=False,  # Disable automatic generation
)
```

### How do I change the port?

Change the arguments to `app.run()`:

```python
app.run(host="0.0.0.0", port=9000, debug=True)
```

### How do I enable CORS?

Install and configure sanic-cors:

```bash
pip install sanic-cors
```

```python
from sanic_cors import CORS

app = Sanic("BookStore")
CORS(app)
```
