# Sanic RESTful Framework

欢迎使用 Sanic RESTful Framework (SRF) —— 一个基于 [Sanic](https://sanic.dev/) 的强大而灵活的 RESTful API 开发框架。

## 什么是 SRF？

Sanic RESTful Framework 是一个基于 [Sanic](https://sanic.dev/) 应用设计的现代化 RESTful API 开发框架，它提供了一套完整的工具和最佳实践，帮助您快速构建高性能的 Web API。

SRF 受到 Django REST Framework 的启发，将其优秀的设计理念移植到了异步的 Sanic 生态系统中，如果您熟悉DRF框架，那您很快就能上手使用SRF，即使您不熟悉Django REST Framework,也没关系，SRF的便捷性一定能帮您快速构建您的应用！

## 为什么选择 SRF？

- **🚀 高性能**：以 [Sanic](https://sanic.dev/) 为基础架构，具有卓越的性能
- **📦 功能完整**：内置认证、权限、分页、过滤、限流等常用功能
- **🎯 简单易用**：使用体验最接近 Django REST Framework，学习曲线平缓
- **🔧 灵活可扩展**：模块化设计，可以轻松定制和扩展
- **🔒 安全可靠**：内置 JWT 认证、CSRF 保护、权限控制等安全特性
- **📊 开箱即用**：提供健康检查、异常处理、HTTP 状态码等实用工具

## 主要特性

### ViewSet 和路由

- 基于类的视图集（ViewSet），自动生成 RESTful 路由
- 支持标准的 CRUD 操作（Create, Read, Update, Delete, List）
- 通过 `@action` 装饰器轻松添加自定义操作
- 自动路由发现和注册

### 认证与授权

- JWT（JSON Web Token）认证支持
- 社交登录集成（GitHub OAuth等）
- 灵活的权限系统（IsAuthenticated, IsRoleAdminUser 等）
- 认证中间件自动处理用户身份验证，保证请求合法

### 数据处理

- 基于 Pydantic 的数据验证和序列化
- 开箱即用的过滤系统（搜索、JSON Logic、查询参数）
- 页码分页、排序功能

### 安全特性

- 限流中间件（基于 IP、用户、路径等）
- CSRF 保护
- 密码加密（bcrypt）
- 公开端点配置


## 快速预览

下面是一个简单的示例，展示如何使用 SRF 创建一个 RESTful API：

```python
from sanic import Sanic
from srf.views import BaseViewSet
from srf.route import SanicRouter
from tortoise import fields
from tortoise.models import Model
from pydantic import BaseModel

# 定义 ORM 模型
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    description = fields.TextField()

# 定义 Schema 模型
class ProductSchema(BaseModel):
    id: int = None
    name: str
    price: float
    description: str

# 定义 ViewSet
class ProductViewSet(BaseViewSet):
    schema: BaseModel = ProductSchema  # 这里也可以定义get_schema函数代替

    @property
    def queryset(self):
        return Product.all()


# 创建应用和路由
app = Sanic("MyApp")
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet)
app.blueprint(router.get_blueprint())
```

这样就创建了一个完整的 RESTful API：

- `GET /api/products` - 获取产品列表
- `POST /api/products` - 创建新产品
- `GET /api/products/<id>` - 获取单个产品
- `PUT /api/products/<id>` - 更新产品
- `DELETE /api/products/<id>` - 删除产品

## 下一步

- 查看 [特点](features.md) 了解 SRF 的所有功能
- 阅读 [快速开始](usage/getting-started.md) 开始您的第一个项目
- 浏览 [API 参考](api-reference.md) 查看详细的 API 文档

## 社区与支持

- **GitHub**: [github.com/*](https://github.com/bitblames/sanic-restful-framework)
- **问题反馈**: 如果您发现 bug 或有功能建议，请在 GitHub 上提交 issue
- **贡献代码**: 欢迎提交 Pull Request 来帮助改进 SRF

## 许可证

Sanic RESTful Framework 采用开源许可证发布。
