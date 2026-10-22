# 数据校验

SRF 使用 [Pydantic](https://docs.pydantic.dev/latest/) 进行数据验证和序列化，提供强大的类型安全和数据验证能力。关于[Pydantic](https://docs.pydantic.dev/latest/)的详细使用，请参考官方文档!

## 基本用法

### 定义 Schema

```python
from pydantic import BaseModel, Field
from typing import Optional


class ProductSchema(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    description: Optional[str] = None
```

### 在 ViewSet 中使用

```python
from srf.views import BaseViewSet
from models import Product
from schemas import ProductSchema


class ProductViewSet(BaseViewSet):
    schema = ProductSchema

    @property
    def queryset(self):
        return Product.all()
```

## Field 字段验证

### 数值验证

```python
from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    price: float = Field(..., gt=0)           # 大于0
    stock: int = Field(..., ge=0)             # 大于等于0
    discount: float = Field(..., lt=100)      # 小于100
    rating: int = Field(..., le=5)            # 小于等于5
    quantity: int = Field(..., ge=1, le=1000) # 范围：1-1000
```

### 字符串验证

```python
from pydantic import BaseModel, Field, EmailStr


class ProductSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sku: str = Field(..., pattern=r"^[A-Z]{3}-\d{6}$")
    email: EmailStr  # 邮箱验证
```

### 列表和集合

```python
from typing import List, Set
from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    tags: List[str] = Field(default_factory=list)
    images: List[str] = Field(..., min_length=1, max_length=10)
    categories: Set[int] = Field(default_factory=set)
```

## 自定义验证器

```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProductSchema(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("产品名称不能为空")
        return value.strip()

    @field_validator("discount_price")
    @classmethod
    def validate_discount(cls, value, info):
        if value is not None and "price" in info.data:
            if value >= info.data["price"]:
                raise ValueError("折扣价必须小于原价")
        return value
```

## 读写 Schema 分离

### Writer Schema（写入）

用于创建和更新操作：

```python
from pydantic import BaseModel, Field


class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
```

### Reader Schema（读取）

用于序列化返回数据：

```python
from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime


class ProductSchemaReader(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category_id: int
    created_at: datetime

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    @computed_field
    @property
    def url(self) -> str:
        return f"/api/products/{self.id}"

    model_config = ConfigDict(from_attributes=True)
```

### 在 ViewSet 中使用

`BaseViewSet.as_view()` 会在调用操作方法前设置 `self.request` 和 `self.action`，
因此 `get_schema()` 不需要接收 `request` 参数。Sanic 的 `request.is_safe` 是属性，
表示当前 HTTP 方法是否为安全方法；适合按读写请求选择 Schema：

```python
from srf.views import BaseViewSet
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    def get_schema(self):
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

如果要按 ViewSet 操作名选择，例如某个自定义操作需要单独的 Schema，则判断
`self.action`：

```python
from srf.views import BaseViewSet
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    def get_schema(self):
        if self.action in ("list", "retrieve"):
            return ProductSchemaReader
        return ProductSchemaWriter
```

也可以根据需求直接固定 schema 类属性

```python
from srf.views import BaseViewSet
from srf.permission import SafeMethodOnly
from schemas import ProductSchemaReader


class ProductViewSet(BaseViewSet):
    permission_classes = [
        SafeMethodOnly,
    ]
    schema = ProductSchemaReader
```

`is_safe` 根据 HTTP 方法分类；`self.action` 根据路由绑定的 ViewSet 方法分类。选择
哪一种取决于接口设计。内置 `create` / `update` 会用 `get_schema()` 返回的同一个
Schema 校验输入并序列化响应。

!!! warning "strict=True 与部分更新"
    内置 `create` / `update` 使用 `schema.model_validate(request.json, strict=True)`：

    - 请求体中的字符串不会被自动转换成 `datetime` / `date` / `Decimal` 等类型；
      写入 Schema 中若包含这些字段，客户端需要发送可被严格校验的类型（通常应改用
      `str` 或 `float` 字段，或重写 `create` / `update`）。
    - `update` 按完整 Schema 校验请求体，且 `PUT` 与 `PATCH` 行为相同；当前没有
      真正的部分更新。请求体需要满足 Schema 的必填字段。

## 数据类型

### 基本类型

```python
from pydantic import BaseModel
from typing import Optional


class ExampleSchema(BaseModel):
    name: str           # 字符串
    age: int            # 整数
    price: float        # 浮点数
    is_active: bool     # 布尔值
    description: Optional[str] = None  # 可选
```

### 日期和时间

```python
from datetime import date, datetime, time


class EventSchema(BaseModel):
    event_date: date         # 日期
    created_at: datetime     # 日期时间
    start_time: time         # 时间
```

### 高级类型

```python
from pydantic import EmailStr, HttpUrl
from decimal import Decimal


class AdvancedSchema(BaseModel):
    email: EmailStr       # 邮箱
    website: HttpUrl      # URL
    price: Decimal        # 精确十进制数
```

### 枚举类型

```python
from enum import Enum
from pydantic import BaseModel
from srf.views import BaseViewSet
from models import Product


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ProductSchema(BaseModel):
    name: str
    status: ProductStatus = ProductStatus.DRAFT
```

## 验证错误响应

当 `create` / `update` 中的 Pydantic 校验失败时，`as_view()` 会把它转换成
`PydanticValidationException`（422）。Sanic 返回的响应体形如：

```json
{
  "description": "Unprocessable Entity",
  "status": 422,
  "message": "1 validation error for ProductSchemaWriter\nprice\n  Input should be greater than 0 ..."
}
```

`message` 是 `str(ValidationError)`，不是结构化字段列表。需要逐字段错误时，
应注册全局异常处理器或重写 `create` / `update`，自行调用 `error.errors()`。

## 完整示例

```python
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum
from srf.views import BaseViewSet
from models import Product


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ProductSchemaWriter(BaseModel):
    """写入 Schema"""

    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., pattern=r"^[A-Z]{3}-\d{6}$")
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
    tags: List[str] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.DRAFT

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("产品名称不能为空")
        return value.strip()


class ProductSchemaReader(BaseModel):
    """读取 Schema"""

    id: int
    name: str
    sku: str
    price: float
    stock: int
    category_id: int
    tags: List[str]
    status: ProductStatus
    created_at: datetime

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    model_config = ConfigDict(from_attributes=True)


# 在 ViewSet 中使用
class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()

    def get_schema(self):
        # 这里按 HTTP 方法选择读写 Schema；完整选择方式见上文。
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

## 最佳实践

1. **使用类型注解**：提供完整的类型信息
2. **分离读写 Schema**：为不同操作定义不同的 Schema
3. **添加验证规则**：使用 Field 和 validator 确保数据有效性
4. **使用枚举**：为固定选项使用枚举类型
5. **计算字段**：使用 `@computed_field` 添加派生字段
6. **友好错误**：在验证器中返回清晰的错误消息

## 下一步

- 学习 [视图](viewsets.md) 了解如何在 ViewSet 中使用 Schema
- 阅读 [认证](authentication.md) 了解用户数据验证
- 查看 [过滤](filtering.md) 了解查询参数验证
