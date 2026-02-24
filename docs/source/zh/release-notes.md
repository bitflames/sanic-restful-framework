# 发布说明

Sanic RESTful Framework 的版本发布历史和更新日志。

## 版本命名规则

SRF 遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

- **主版本号**：不兼容的 API 变更
- **次版本号**：向后兼容的功能性新增
- **修订号**：向后兼容的问题修正

格式：`主版本号.次版本号.修订号`

## 版本历史

### v0.0.1 (2026-02-07)

**首个正式版本发布** 🎉

#### 核心功能

- ✅ **ViewSet 系统**
  - BaseViewSet 实现
  - CRUD Mixins (Create, Retrieve, Update, Destroy, List)
  - @action 装饰器支持自定义操作
  - 自动路由生成

- ✅ **路由系统**
  - SanicRouter 路由管理器
  - 自动发现 @action 装饰的方法
  - 支持集合级和详情级操作
  - URL 前缀和命名支持

- ✅ **认证与授权**
  - JWT (JSON Web Token) 认证
  - 社交登录（GitHub OAuth）
  - 邮箱验证码
  - 权限类系统（IsAuthenticated, IsRoleAdminUser, IsSafeMethodOnly）
  - 认证中间件

- ✅ **数据处理**
  - 基于 Pydantic 的数据验证
  - 读写 Schema 分离
  - 自动序列化和反序列化

- ✅ **过滤与搜索**
  - SearchFilter - 全文搜索
  - JsonLogicFilter - 复杂查询
  - QueryParamFilter - 精确过滤
  - OrderingFactory - 排序

- ✅ **分页**
  - 基于页码的分页
  - 可配置每页数量
  - 统一的分页响应格式

- ✅ **中间件**
  - 认证中间件
  - 限流中间件（IP、用户、路径、请求头）
  - CSRF 中间件（规划中）

- ✅ **健康检查**
  - 可扩展的健康检查系统
  - 内置 Redis、PostgreSQL、MongoDB、SQLite 检查

- ✅ **异常处理**
  - 统一的异常处理机制
  - 自定义异常类
  - 标准化的错误响应

- ✅ **工具类**
  - HTTP 状态码枚举
  - 邮件发送功能
  - 配置管理系统

#### ORM 支持

- Tortoise ORM 集成
- 原生异步数据库操作

#### 文档

- 支持完整的English、中文文档
- 代码示例和教程
- API 参考文档

---

## 路线图

### v0.1.0 (计划中)

**目标发布日期**: 暂无

#### 计划功能

- [ ] 解除对第三方应用的依赖

#### 改进

- [ ] 性能优化
- [ ] 更多的运行日志
- [ ] 更多国际化文档支持

---

## 已知问题

### v0.0.1

| 问题 | 严重性 | 状态 | 预计修复版本 |
|------|--------|------|-------------|
| 注册时验证邮箱的有效性 | 低 | 规划中 |  |

---

## 贡献者

感谢以下贡献者对 SRF 的贡献：

- **Chacer** - 项目创建者和主要维护者

---

## 支持的 Python 版本

| SRF 版本 | Python 版本 |
|----------|-------------|
| 1.0.x | 3.8, 3.9, 3.10, 3.11, 3.12 |
| 0.9.x | 3.8, 3.9, 3.10, 3.11 |

---

## 支持的依赖版本

### v1.0.0

| 依赖 | 版本要求 |
|------|---------|
| Sanic | >= 21.0.0 |
| Tortoise ORM | >= 0.19.0 |
| Pydantic | >= 2.0.0 |
| sanic-jwt | >= 1.8.0 |
| aioredis | >= 2.0.0 |
| bcrypt | >= 4.0.0 |

---

## 获取更新

- **GitHub**: https://github.com/bitblames/sanic-restful-framework/sanic-restful-framework
- **PyPI**: https://pypi.org/project/sanic-restful-framework/
- **文档**: https://sanic-restful-framework.readthedocs.io/


## 反馈和建议

我们欢迎任何反馈和建议：

- **Bug 报告**: 在 GitHub 提交 Issue
- **功能请求**: 在 GitHub 提交 Feature Request
- **问题咨询**: 在 GitHub Discussions 发帖
- **安全问题**: 发送邮件到 security@example.com

---

## 许可证

Sanic RESTful Framework 采用 MIT 许可证。

---

## 更新日志格式说明

### 图例

- ✅ 新增功能
- 🔧 改进
- 🐛 Bug 修复
- ⚠️ 破坏性变更
- 📝 文档更新
- 🎨 代码风格改进
- ⚡ 性能优化
- 🔒 安全修复

### 贡献

欢迎提交 Pull Request 来改进 SRF！

---

*最后更新: 2026-02-24*
