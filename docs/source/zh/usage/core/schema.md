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
from pydantic import BaseModel

class ProductViewSet(BaseViewSet):
    schema: BaseModel = ProductSchema

    @property
    def queryset(self):
        return Product.all()
```

## Field 字段验证

### 数值验证

```python
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
    sku: str = Field(..., pattern=r'^[A-Z]{3}-\d{6}$')
    email: EmailStr  # 邮箱验证
```

### 列表和集合

```python
from typing import List, Set

class ProductSchema(BaseModel):
    tags: List[str] = Field(default=[])
    images: List[str] = Field(..., min_length=1, max_length=10)
    categories: Set[int] = Field(default=set())
```

## 自定义验证器

```python
from pydantic import BaseModel, field_validator

class ProductSchema(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError('产品名称不能为空')
        return value.strip()
    
    @field_validator('discount_price')
    @classmethod
    def validate_discount(cls, value, info):
        if value is not None and 'price' in info.data:
            if value >= info.data['price']:
                raise ValueError('折扣价必须小于原价')
        return value
```

## 读写 Schema 分离

### Writer Schema（写入）

用于创建和更新操作：

```python
class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
```

### Reader Schema（读取）

用于序列化返回数据：

```python
from pydantic import computed_field
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
    
    class Config:
        from_attributes = True
```

### 在 ViewSet 中使用

```python
class ProductViewSet(BaseViewSet):
    def get_schema(self, request, is_safe=False):
        """
        is_safe=True: 读取操作（GET）
        is_safe=False: 写入操作（POST/PUT/PATCH）
        """
        return ProductSchemaReader if is_safe else ProductSchemaWriter
```

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

class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ProductSchema(BaseModel):
    name: str
    status: ProductStatus = ProductStatus.DRAFT
```

## 验证错误响应

当数据验证失败时，返回 422 错误：

```json
{
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["name"],
      "msg": "String should have at least 1 character"
    },
    {
      "type": "greater_than",
      "loc": ["price"],
      "msg": "Input should be greater than 0"
    }
  ]
}
```

## 完整示例

```python
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class ProductSchemaWriter(BaseModel):
    """写入 Schema"""
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., pattern=r'^[A-Z]{3}-\d{6}$')
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
    tags: List[str] = Field(default=[])
    status: ProductStatus = ProductStatus.DRAFT
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError('产品名称不能为空')
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
    
    class Config:
        from_attributes = True

# 在 ViewSet 中使用
class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
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
