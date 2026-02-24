# 快速开始

本指南将带您从零开始创建第一个基于 Sanic RESTful Framework 的项目。

## 环境要求

在开始之前，请确保您的环境满足以下要求：

- **Python**: 3.9 或更高版本
- **pip**: Python 包管理工具
- **数据库**: PostgreSQL、MySQL、SQLite 等（本教程使用 SQLite）

## 安装

### 1. 创建项目目录

```bash
mkdir bookstore
cd bookstore
```

### 2. 创建虚拟环境

推荐使用 conda 创建独立的 Python 环境：

```bash
# 创建名为 srf 的虚拟环境
conda create -n srf python=3.11

# 激活虚拟环境
conda activate srf
```

或使用 UV：

```bash
uv init
```

### 3. 安装 SRF

```bash
pip install sanic-restful-framework
# 或者
uv add sanic-restful-framework
```

### 4. 安装依赖

SRF 需要以下依赖（通常会自动安装）：

```bash
sanic
tortoise-orm
pydantic
sanic-jwt
aioredis
bcrypt
```

## 创建第一个项目

让我们创建一个简单的图书管理 API。

### 步骤 1：创建应用文件

创建 `app.py` 文件：

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.route import SanicRouter
from srf.config import srfconfig

# 创建 Sanic 应用
app = Sanic("BookStore")

# 配置 SRF
srfconfig.set_app(app)

# 数据库配置
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

# 创建路由
router = SanicRouter(prefix="api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### 步骤 2：定义数据模型

创建 `models.py` 文件：

```python
from tortoise import fields
from tortoise.models import Model

class Book(Model):
    """图书模型"""
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    author = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)
    
    class Meta:
        table = "books"
```

### 步骤 3：定义 Schema

创建 `schemas.py` 文件：

```python
from pydantic import BaseModel, Field
from typing import Optional

class BookSchemaWriter(BaseModel):
    """图书写入 Schema（用于创建和更新）"""
    title: str = Field(..., max_length=200)
    author: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class BookSchemaReader(BaseModel):
    """图书读取 Schema（用于序列化）"""
    id: int
    title: str
    author: str
    price: float
    stock: int
    
    class Config:
        from_attributes = True
```

### 步骤 4：创建 ViewSet

创建 `viewsets.py` 文件：

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from sanic.constants import SAFE_HTTP_METHODS
from sanic.response import json
from models import Book
from schemas import BookSchemaWriter, BookSchemaReader

class BookViewSet(BaseViewSet):
    """图书 ViewSet"""
    
    search_fields = ["title", "author"]
    
    @property
    def queryset(self):
        return Book.all()
    
    def get_schema(self, request, *args, **kwargs):
        return BookSchemaReader if request.method.lower() in SAFE_HTTP_METHODS else BookSchemaWriter
    
    @action(methods=["get"], detail=False, url_path="search")
    async def search_books(self, request):
        """搜索图书"""
        keyword = request.args.get('q', '')
        books = await Book.filter(title__icontains=keyword)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(b).model_dump() for b in books]
        return json({"results": data})
```

### 步骤 5：注册路由

更新 `app.py`，注册 ViewSet：

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.route import SanicRouter
from srf.config import srfconfig
from viewsets import BookViewSet

app = Sanic("BookStore")

 # 应用我们的SRF框架
srfconfig.set_app(app)

# 注册数据库
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

# 创建路由并注册 ViewSet
router = SanicRouter(prefix="api")
router.register("books", BookViewSet, name="books")

# 将路由添加到应用
app.blueprint(router.get_blueprint())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

### 步骤 6：运行应用

```bash
python app.py
```

您应该看到类似以下的输出：

```
[2026-02-07 10:00:00 +0800] [12345] [INFO] Goin' Fast @ http://0.0.0.0:8000
[2026-02-07 10:00:00 +0800] [12345] [INFO] Starting worker [12345]
```

## 测试 API

现在您的 API 已经运行，让我们测试一下！

### 1. 创建图书

```bash
curl -X POST http://localhost:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python 编程",
    "author": "张三",
    "price": 89.00,
    "stock": 50
  }'
```

响应：

```json
{
  "id": 1,
  "title": "Python 编程",
  "author": "张三",
  "price": 89.00,
  "stock": 50
}
```

### 2. 获取图书列表

```bash
curl http://localhost:8000/api/books
```

响应：

```json
{
  "count": 1,
  "next": false,
  "previous": false,
  "results": [
    {
      "id": 1,
      "title": "Python 编程",
      "author": "张三",
      "price": 89.00,
      "stock": 50
    }
  ]
}
```

### 3. 获取单本图书

```bash
curl http://localhost:8000/api/books/1
```

### 4. 更新图书

```bash
curl -X PUT http://localhost:8000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python 编程（第2版）",
    "author": "张三",
    "price": 99.00,
    "stock": 50
  }'
```

### 5. 搜索图书

```bash
# 搜索标题包含 "Python" 的图书
curl "http://localhost:8000/api/books?search=Python"

# 按作者过滤
curl "http://localhost:8000/api/books?author=张三"
```

### 6. 分页

```bash
# 获取第1页，每页10条
curl "http://localhost:8000/api/books?page=1&page_size=10"
```

### 7. 使用自定义操作

```bash
# 搜索图书
curl "http://localhost:8000/api/books/search?q=Python"
```

### 8. 删除图书

```bash
curl -X DELETE http://localhost:8000/api/books/1
```

## 完整的项目结构

```
bookstore/
├── app.py                 # 应用入口
├── models.py              # 数据模型
├── schemas.py             # Pydantic Schemas
├── viewsets.py            # ViewSets
├── db.sqlite3             # 数据库文件（自动生成）
└── requirements.txt       # 依赖列表
```

## 下一步

恭喜！您已经成功创建了第一个 SRF 项目。接下来可以：

1. **添加认证**：查看 [认证](core/authentication.md) 章节，为您的 API 添加 JWT 认证
2. **添加权限控制**：阅读 [权限](core/permissions.md) 章节，限制用户访问
3. **深入了解 ViewSet**：学习 [视图](core/viewsets.md) 的高级用法
4. **配置项目**：查看 [项目设置](project-setup.md) 了解更多配置选项

## 常见问题

### 如何修改数据库？

修改 `register_tortoise` 中的 `db_url`：

```python
# PostgreSQL
db_url="postgres://user:password@localhost:5432/dbname"

# MySQL
db_url="mysql://user:password@localhost:3306/dbname"

# SQLite
db_url="sqlite://db.sqlite3"
```

### 如何禁用自动生成表结构？

设置 `generate_schemas=False`：

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=False,  # 禁用自动生成
)
```

### 如何修改端口？

修改 `app.run()` 的参数：

```python
app.run(host="0.0.0.0", port=9000, debug=True)
```

### 如何启用 CORS？

安装并配置 sanic-cors：

```bash
pip install sanic-cors
```

```python
from sanic_cors import CORS

app = Sanic("BookStore")
CORS(app)
```
