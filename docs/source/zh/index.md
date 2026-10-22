# Sanic RESTful framework

欢迎使用 Sanic RESTful framework (SRF) —— 一个基于 [Sanic](https://sanic.dev/) 的强大而灵活的 RESTful API 开发框架。

## 什么是 SRF？

Sanic RESTful framework（后文称为 SRF） 是一个基于 [Sanic](https://sanic.dev/) 应用设计的现代化 RESTful API 开发框架，它提供了一套完整的工具和最佳实践，帮助您快速构建高性能的 Web API。

SRF 受到 Django REST framework（后文称为 DRF）的启发，将其优秀的设计理念移植到了异步的 Sanic 生态系统中，如果您熟悉 DRF 框架，那您很快就能上手使用 SRF，即使您不熟悉 DRF 也没关系，SRF 的便捷性一定能帮您快速构建您的应用！

## 为什么选择 SRF？

- **🚀 高性能**：以 [Sanic](https://sanic.dev/) 为基础架构，具有卓越的性能
- **📦 常用组件**：提供认证、权限、分页、过滤、限流等基础组件
- **🎯 简单易用**：使用体验最接近 Django REST Framework，学习曲线平缓
- **🔧 灵活可扩展**：模块化设计，可以轻松定制和扩展
- **🔒 安全扩展点**：提供 JWT、权限和限流组件；生产安全仍需应用配置和审计
- **📊 开箱即用**：提供健康检查、异常处理、HTTP 状态码等实用工具

## 主要特性

### ViewSet 和路由

- 基于类的视图集（ViewSet），自动生成 RESTful 路由
- 支持标准的 CRUD 操作（Create, Read, Update, Delete, List 等）
- 通过 `@action` 装饰器轻松添加自定义操作
- 自动路由发现和注册

### 认证与授权

- JWT（JSON Web Token）认证支持
- 社交登录集成（GitHub OAuth等）
- 灵活的权限系统（IsAuthenticated、SafeMethodOnly、SuperuserOnly 等）
- 提供认证中间件工具，需由应用按路由策略接入

### 数据处理

- 基于 Pydantic 的数据验证和序列化
- 页码分页、排序功能

### 安全特性

- 限流中间件（基于 IP、用户、路径等）
- CSRF 防护由应用根据认证方式自行接入
- 密码加密（bcrypt）
- 认证密钥由应用显式配置

## 快速预览

下面是一个简单的示例，展示如何使用 SRF 创建一个 RESTful API：

```python
from sanic import Sanic
from srf.views import BaseViewSet
from srf.route import SanicRouter

from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.sanic import register_tortoise
from pydantic import BaseModel, ConfigDict


# 定义 ORM 模型
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    description = fields.TextField()


# 定义 Schema 模型
class ProductSchema(BaseModel):
    id: int | None = None
    name: str
    price: float
    description: str
    model_config = ConfigDict(from_attributes=True)


# 定义 ViewSet
class ProductViewSet(BaseViewSet):
    schema = ProductSchema

    @property
    def queryset(self):
        return Product.all()


# 创建应用和路由
app = Sanic("MyApp")
register_tortoise(app, db_url=*, modules=*})
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

注册路由后即可使用这些 ViewSet 端点；

- `GET /api/products` - 获取产品列表
- `POST /api/products` - 创建新产品
- `GET /api/products/<pk>` - 获取单个产品
- `PUT/PATCH /api/products/<pk>` - 更新产品
- `DELETE /api/products/<pk>` - 删除产品

## 下一步

- 查看 [特点](features.md) 了解 SRF 的所有功能
- 阅读 [快速开始](usage/getting-started.md) 开始您的第一个项目
- 浏览 [API 参考](api/views.md) 查看详细的 API 文档

## 社区与支持

- **GitHub**: [sanic-restful-framework](https://github.com/bitflames/sanic-restful-framework)
- **问题反馈**: 如果您发现 bug 或有功能建议，请在 GitHub 上提交 issue
- **贡献代码**: 欢迎提交 Pull Request 来帮助改进 SRF

## 许可证

Sanic RESTful framework 采用 MIT 许可证发布。
