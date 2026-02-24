# 特点

Sanic RESTful Framework(SRF) 提供了一套完整的工具和功能，帮助您快速构建高质量的 RESTful API。

## 核心特性

### 🎯 基于类的视图集（ViewSet）

ViewSet 是 SRF 的核心概念，它提供了一种优雅的方式来组织和管理 API 端点。

**特点：**

- 自动生成标准的 RESTful 路由
- 内置 CRUD 基本视图函数（Create, Read, Update, Delete, List）
- 支持 Mixin 模式，灵活组合功能
- 通过 `@action` 装饰器轻松添加自定义路由视图函数
- 快速开发，接近 Django REST Framework的开发体验

**优势：**

- 减少重复代码，提高开发效率
- 统一的代码风格和结构
- 易于测试和维护

### 🎨 自动路由生成

SanicRouter 自动为 ViewSet 生成路由：

**标准路由：**

- `GET /api/resource` → list
- `POST /api/resource` → create
- `GET /api/resource/<pk>` → retrieve
- `PUT/PATCH /api/resource/<pk>` → update
- `DELETE /api/resource/<pk>` → destroy

**自定义路由：**

- 通过 `@action` 装饰器定义
- 自动发现并注册
- 支持集合级和详情级操作

### 🔐 完整的认证系统

SRF 提供了多种认证方式，满足不同场景的需求。

**支持的认证方式：**

- **JWT 认证**：基于 JSON Web Token 的无状态认证
- **社交登录**：支持 GitHub OAuth（可扩展其他平台）
- **邮箱验证**：内置邮箱验证码功能

**认证特性：**

- 自动处理 token 验证
- 用户角色和权限管理
- 密码加密存储（bcrypt）
- 公开端点配置

### 🛡️ 灵活的权限系统

基于类的权限系统，支持视图级和对象级权限控制。

**内置权限类：**

- `IsAuthenticated`：用户必须已登录
- `IsRoleAdminUser`：用户必须是管理员角色
- `IsSafeMethodOnly`：仅允许安全的 HTTP 方法（GET, HEAD, OPTIONS）
- 基于`BasePermission`实现自定义的权限管控


### 📊 强大的数据处理

#### 数据验证与序列化

- 基于 **Pydantic** 的数据验证
- 自动数据序列化和反序列化
- 支持读写 Schema 分离
- 类型安全，IDE 友好

#### 过滤系统

SRF 提供了多种过滤器，可以组合使用：

1. **SearchFilter**：全文搜索过滤
2. **JsonLogicFilter**：支持复杂的 JSON Logic 表达式
3. **QueryParamFilter**：基于查询参数的精确过滤
4. **OrderingFactory**：排序功能

#### 分页

- 基于页码的分页
- 可配置每页数量
- 返回统一的分页响应格式

### 🚦 限流中间件

保护您的 API 免受滥用，支持多种限流策略：

- **IPRateLimit**：基于 IP 地址限流
- **UserRateLimit**：基于用户 ID 限流
- **PathRateLimit**：基于请求路径限流
- **HeaderRateLimit**：基于请求头限流

**存储方式：**

- 内存存储（MemoryStorage）
- 可扩展支持 Redis 等外部存储

### 🏥 健康检查

内置健康检查功能，监控应用和依赖服务的状态。

**支持的服务检查：**

- Redis
- PostgreSQL
- MongoDB
- SQLite

**特点：**

- 自动检测服务可用性
- 返回标准化的健康状态响应
- 易于集成到监控系统

### 🔧 实用工具

#### HTTP 状态码

- 完整的 HTTP 状态码枚举
- 语义化的常量命名（如 `HTTP_200_OK`, `HTTP_404_NOT_FOUND`）
- 状态码类型检查函数

#### 异常处理

- 统一的异常处理机制
- 自定义异常类
- 自动转换为标准的 HTTP 响应

#### 邮件发送

- 基于 aiosmtplib 的异步邮件发送
- 支持 HTML 和纯文本邮件
- 配置灵活，易于使用



## 设计理念

### 约定优于配置

SRF 遵循"约定优于配置"的原则，提供合理的默认配置，让您可以快速开始开发。同时保持高度的可配置性，在需要时可以自定义任何行为。

### 模块化与可扩展

SRF 采用模块化设计，每个功能都是独立的模块，可以根据需要选择使用。同时提供了清晰的扩展点，方便您添加自定义功能。

### 类型安全

通过 Pydantic 和类型注解，SRF 提供了良好的类型安全性，减少运行时错误，提高代码质量。

### 异步优先

充分利用 Python 的 asyncio 特性和 Sanic 的异步架构，提供高性能的 API 服务。

## 性能优势

- **异步 I/O**：原生支持 async/await，基于 uvloop 实现快速事件循环，性能远超同步框架
- **高效路由**：自动生成和注册路由，减少运行时开销
- **灵活缓存**：支持配置缓存策略，提升响应速度
- **轻量级**：核心功能精简，按需加载模块

## 开发体验

### 生态完善
- 基于Sanic为基础框架，可以和生态中各种框架完美融合

### IDE 友好

- 完整的类型注解
- 清晰的代码结构
- 良好的代码提示和自动补全

### 易于测试

- 基于类的设计便于单元测试
- 清晰的接口和职责分离
- 支持 Mock 和依赖注入

### 文档完善

- 详细的多语言文档
- 丰富的代码示例
- API 参考文档

## 适用场景

SRF 适合以下场景：

- ✅ 构建 RESTful API 服务
- ✅ 需要高并发处理的应用
- ✅ 微服务架构
- ✅ 前后端分离项目
- ✅ 移动应用后端
- ✅ 物联网平台
- ✅ 数据 API 服务

## 对比其他框架

| 特性 | SRF | FastAPI | Django REST |
|------|-----|---------|-------------|
| 异步支持 | ✅ 完整 | ✅ 完整 | ⚠️ 部分 |
| 性能 | 🚀很高  | 🚀 较高 | ⚡ 中等 |
| 开发速度 | 很快 | 快 | 很快 |
| 学习曲线 | 📈 平缓 | 📈 平缓 | 📈 陡峭 |
| ViewSet | ✅ 支持 | ❌ 不支持 | ✅ 支持 |
| 数据验证 | Pydantic | Pydantic | Serializer |
| ORM | Tortoise(其他ORM扩展中) | SQLAlchemy/其他 | Django ORM |
| 社区 | 🌱 成长中 | 🌳 活跃 | 🌲 成熟 |

## 下一步

现在您已经了解了 SRF 的主要特性，可以：

- 查看 [快速开始](usage/getting-started.md) 创建您的第一个项目
- 阅读 [核心概念](usage/core/viewsets.md) 深入了解 ViewSet 的使用
- 浏览 [API 参考](api-reference.md) 查看详细的 API 文档
