# 快速开始

本指南将带您从零开始创建第一个基于 Sanic RESTful framework 的项目。

## 环境要求

在开始之前，请确保您的环境满足以下要求：

- **Python**: 3.11 或更高版本
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

### 4. 核对运行依赖

安装 SRF 时会自动安装核心依赖，包括 Sanic `>=25.0.0,<26`、
Tortoise ORM `>=1.1.8,<2`、Pydantic `>=2.6.1,<3`、`sanic-jwt`、`redis`
和 `bcrypt`。

`sanic-cors` 和 `python-dotenv` 是可选依赖，分别用于 CORS 集成和从 `.env`
文件加载配置；只有使用相应示例时才需要单独安装。

## 创建第一个项目

让我们创建一个简单的图书管理 API。

### 步骤 1：创建应用文件

创建 `app.py` 文件：

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.config import settings

# 创建 Sanic 应用
app = Sanic("BookStore")

# 配置 SRF
settings.set_app(app)

# 数据库配置
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)

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
from pydantic import BaseModel, Field, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)
```

### 步骤 4：创建 ViewSet

创建 `viewsets.py` 文件：

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from sanic.response import json
from models import Book
from schemas import BookSchemaWriter, BookSchemaReader


class BookViewSet(BaseViewSet):
    """图书 ViewSet"""

    search_fields = ["title", "author"]
    # search_fields、filter_fields 都可以用别名映射；字典可将查询参数名映射到 ORM 字段
    filter_fields = {"author": "author"}

    @property
    def queryset(self):
        return Book.all()

    def get_schema(self):
        # as_view 会设置 self.action；此处按 ViewSet 操作名区分读写 Schema。
        if self.action in ("list", "retrieve"):
            return BookSchemaReader
        return BookSchemaWriter

    @action(methods=["get"], detail=False, url_path="search")
    async def search_books(self, request):
        """搜索图书"""
        keyword = request.args.get("q", "")
        books = await Book.filter(title__icontains=keyword)
        data = [BookSchemaReader.model_validate(b).model_dump() for b in books]
        return json({"results": data})
```

### 步骤 5：注册路由

在 `app.py` 顶部补充导入，然后在 `register_tortoise(...)` 之后注册 ViewSet：

```python
from srf.route import SanicRouter
from viewsets import BookViewSet

router = SanicRouter(app, prefix="api")
router.register("books", BookViewSet, name="books")
```

`SanicRouter` 会为 ViewSet 自动生成集合路由（`/api/books`）和详情路由
（`/api/books/<pk>`），并发现 `@action` 方法。

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

响应体是创建接口返回的同一个图书对象。

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

响应：

```json
{
  "id": 1,
  "title": "Python 编程（第2版）",
  "author": "张三",
  "price": 99.00,
  "stock": 50
}
```

### 5. 按字段过滤

`filter_fields` 中声明的参数可以直接用于精确过滤：

```bash
curl "http://localhost:8000/api/books?author=张三"
```

响应结构与列表接口相同，`results` 中只包含匹配的记录。

### 6. 分页

```bash
# 获取第1页，每页10条
curl "http://localhost:8000/api/books?page=1&page_size=10"
```

响应格式同上：`count` 为总数，`results` 为当前页数据。

### 7. 使用自定义操作

```bash
# 自定义 action 使用 q 参数搜索标题
curl "http://localhost:8000/api/books/search?q=Python"
```

响应：

```json
{
  "results": [
    {
      "id": 1,
      "title": "Python 编程（第2版）",
      "author": "张三",
      "price": 99.00,
      "stock": 50
    }
  ]
}
```

### 8. 删除图书

```bash
curl -i -X DELETE http://localhost:8000/api/books/1
```

响应：`204 No Content`（无响应体）。

## 完整的项目结构

```
bookstore/
├── app.py                 # 应用入口
├── models.py              # 数据模型
├── schemas.py             # Pydantic Schemas
├── viewsets.py            # ViewSets
└── db.sqlite3             # 数据库文件（自动生成）
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
db_url = "postgres://user:password@localhost:5432/dbname"

# MySQL
db_url = "mysql://user:password@localhost:3306/dbname"

# SQLite
db_url = "sqlite://db.sqlite3"
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
