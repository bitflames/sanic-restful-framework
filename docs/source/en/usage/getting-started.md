# Quick Start

This guide will take you from zero to your first project based on the Sanic RESTful Framework.

## Environment Requirements

Before starting, ensure your environment meets the following requirements:

- **Python**: 3.9 or higher
- **pip**: Python package management tool
- **Database**: PostgreSQL, MySQL, SQLite, etc. (This tutorial uses SQLite)

## Installation

### 1. Create Project Directory

```bash
mkdir bookstore
cd bookstore
```

### 2. Create a Virtual Environment

It is recommended to use conda to create an independent Python environment:

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

### 4. Install Dependencies

SRF requires the following dependencies (usually installed automatically):

```bash
sanic
tortoise-orm
pydantic
sanic-jwt
aioredis
bcrypt
```

## Create Your First Project

Let's create a simple book management API.

### Step 1: Create the Application File

Create `app.py` file:

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.route import SanicRouter
from srf.config import srfconfig

# Create Sanic application
app = Sanic("BookStore")

# Configure SRF
srfconfig.set_app(app)

# Database configuration
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

# Create route
router = SanicRouter(prefix="api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### Step 2: Define Data Models

Create `models.py` file:

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

### Step 3: Define Schema

Create `schemas.py` file:

```python
from pydantic import BaseModel, Field
from typing import Optional

class BookSchemaWriter(BaseModel):
    """Book write schema (for creating and updating)"""
    title: str = Field(..., max_length=200)
    author: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class BookSchemaReader(BaseModel):
    """Book read schema (for serialization)"""
    id: int
    title: str
    author: str
    price: float
    stock: int
    
    class Config:
        from_attributes = True
```

### Step 4: Create ViewSet

Create `viewsets.py` file:

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from sanic.constants import SAFE_HTTP_METHODS
from sanic.response import json
from models import Book
from schemas import BookSchemaWriter, BookSchemaReader

class BookViewSet(BaseViewSet):
    """Book ViewSet"""
    
    search_fields = ["title", "author"]
    
    @property
    def queryset(self):
        return Book.all()
    
    def get_schema(self, request, *args, **kwargs):
        return BookSchemaReader if request.method.lower() in SAFE_HTTP_METHODS else BookSchemaWriter
    
    @action(methods=["get"], detail=False, url_path="search")
    async def search_books(self, request):
        """Search books"""
        keyword = request.args.get('q', '')
        books = await Book.filter(title__icontains=keyword)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(b).model_dump() for b in books]
        return json({"results": data})
```

### Step 5: Register Routes

Update `app.py`, register the ViewSet:

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.route import SanicRouter
from srf.config import srfconfig
from viewsets import BookViewSet

app = Sanic("BookStore")

# Apply our SRF framework
srfconfig.set_app(app)

# Register database
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

# Create routes and register ViewSet
router = SanicRouter(prefix="api")
router.register("books", BookViewSet, name="books")

# Add routes to the application
app.blueprint(router.get_blueprint())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### Step 6: Run the Application

```bash
python app.py
```

You should see output similar to the following:

```
[2026-02-07 10:00:00 +0800] [12345] [INFO] Goin' Fast @ http://0.0.0.0:8000
[2026-02-07 10:00:00 +0800] [12345] [INFO] Starting worker [12345]
```

## Test the API

Now that your API is running, let's test it!

### 1. Create a Book

```bash
curl -X POST http://localhost:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming",
    "author": "Zhang San",
    "price": 89.00,
    "stock": 50
  }'
```

Response:

```json
{
  "id": 1,
  "title": "Python Programming",
  "author": "Zhang San",
  "price": 89.00,
  "stock": 50
}
```

### 2. Get Book List

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
      "author": "Zhang San",
      "price": 89.00,
      "stock": 50
    }
  ]
}
```

### 3. Get a Single Book

```bash
curl http://localhost:8000/api/books/1
```

### 4. Update a Book

```bash
curl -X PUT http://localhost:8000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming (Second Edition)",
    "author": "Zhang San",
    "price": 99.00,
    "stock": 50
  }'
```

### 5. Search for Books

```bash
# Search for books with "Python" in the title
curl "http://localhost:8000/api/books?search=Python"

# Filter by author
curl "http://localhost:8000/api/books?author=Zhang San"
```

### 6. Pagination

```bash
# Get page 1 with 10 items per page
curl "http://localhost:8000/api/books?page=1&page_size=10"
```

### 7. Use Custom Actions

```bash
# Search for books
curl "http://localhost:8000/api/books/search?q=Python"
```

### 8. Delete a Book

```bash
curl -X DELETE http://localhost:8000/api/books/1
```

## Complete Project Structure

```
bookstore/
├── app.py                 # Application entry point
├── models.py              # Data models
├── schemas.py             # Pydantic Schemas
├── viewsets.py            # ViewSets
├── db.sqlite3             # Database file (auto-generated)
└── requirements.txt       # Dependency list
```

## Next Steps

Congratulations! You have successfully created your first SRF project. Next, you can:

1. **Add Authentication**: See the [Authentication](core/authentication.md) section to add JWT authentication to your API
2. **Add Permission Control**: Read the [Permissions](core/permissions.md) section to restrict user access
3. **Understand ViewSet in Depth**: Learn advanced usage of [Views](core/viewsets.md)
4. **Configure the Project**: See [Project Setup](project-setup.md) for more configuration options

## Frequently Asked Questions

### How to Modify the Database?

Modify the `db_url` in `register_tortoise`:

```python
# PostgreSQL
db_url="postgres://user:password@localhost:5432/dbname"

# MySQL
db_url="mysql://user:password@localhost:3306/dbname"

# SQLite
db_url="sqlite://db.sqlite3"
```

### How to Disable Auto-Generating Table Structures?

Set `generate_schemas=False`:

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=False,  # Disable auto-generation
)
```

### How to Change the Port?

Modify the parameters in `app.run()`:

```python
app.run(host="0.0.0.0", port=9000, debug=True)
```

### How to Enable CORS?

Install and configure sanic-cors:

```bash
pip install sanic-cors
```

```python
from sanic_cors import CORS

app = Sanic("BookStore")
CORS(app)
```