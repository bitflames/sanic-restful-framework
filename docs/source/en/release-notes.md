# Release Notes

The version release history and changelog of the Sanic RESTful Framework.

## Version Naming Convention

SRF follows the [Semantic Versioning](https://semver.org/lang/zh-CN/) specification:

- **Major Version**: Incompatible API changes
- **Minor Version**: Backward-compatible feature additions
- **Patch Version**: Backward-compatible bug fixes

Format: `Major Version.Minor Version.Patch Version`

## Version History

### v0.0.2 (2026-02-07)

**First official release** 🎉

#### Core Features

- ✅ **ViewSet System**
  - BaseViewSet implementation
  - CRUD Mixins (Create, Retrieve, Update, Destroy, List)
  - @action decorator for custom operations
  - Automatic route generation

- ✅ **Routing System**
  - SanicRouter router manager
  - Automatic discovery of methods with @action decorator
  - Support for collection-level and detail-level operations
  - URL prefix and naming support

- ✅ **Authentication and Authorization**
  - JWT (JSON Web Token) authentication
  - Social login (GitHub OAuth)
  - Email verification code
  - Permission class system (IsAuthenticated, IsRoleAdminUser, IsSafeMethodOnly)
  - Authentication middleware

- ✅ **Data Processing**
  - Data validation based on Pydantic
  - Separation of read and write schemas
  - Automatic serialization and deserialization

- ✅ **Filtering and Search**
  - SearchFilter - Full-text search
  - JsonLogicFilter - Complex queries
  - QueryParamFilter - Exact filtering
  - OrderingFactory - Sorting

- ✅ **Pagination**
  - Page number-based pagination
  - Configurable number of items per page
  - Unified pagination response format

- ✅ **Middleware**
  - Authentication middleware
  - Rate limiting middleware (IP, user, path, request header)
  - CSRF middleware (planned)

- ✅ **Health Check**
  - Extensible health check system
  - Built-in checks for Redis, PostgreSQL, MongoDB, SQLite

- ✅ **Exception Handling**
  - Unified exception handling mechanism
  - Custom exception classes
  - Standardized error responses

- ✅ **Utility Classes**
  - HTTP status code enumeration
  - Email sending functionality
  - Configuration management system

#### ORM Support

- Tortoise ORM integration
- Native asynchronous database operations

#### Documentation

- Support for complete English and Chinese documentation
- Code examples and tutorials
- API reference documentation

---

## Roadmap

### v0.1.0 (planned)

**Target Release Date**: TBA

#### Planned Features

- [ ] Remove dependencies on third-party applications

#### Improvements

- [ ] Performance optimization
- [ ] More detailed runtime logs
- [ ] More internationalization documentation support

---

## Known Issues

### v0.0.2

| Issue | Severity | Status | Estimated Fix Version |
|------|--------|------|-------------|
| Validate email validity during registration | Low | Planned |  |

---

## Contributors

Thank you to the following contributors for their contributions to SRF:

- **Chacer** - Project creator and main maintainer

---

## Supported Python Versions

| SRF Version | Python Version |
|----------|-------------|
| 1.0.x | 3.8, 3.9, 3.10, 3.11, 3.12 |
| 0.9.x | 3.8, 3.9, 3.10, 3.11 |

---

## Supported Dependency Versions

### v0.0.2

| Dependency | Version Requirements |
|------|---------|
| Sanic | >= 21.0.0 |
| Tortoise ORM | >= 0.19.0 |
| Pydantic | >= 2.0.0 |
| sanic-jwt | >= 1.8.0 |
| aioredis | >= 2.0.0 |
| bcrypt | >= 4.0.0 |

---

## Get Updates

- **GitHub**: https://github.com/bitflames/sanic-restful-framework/
- **PyPI**: https://pypi.org/project/sanic-restful-framework/
- **Documentation**: https://sanic-restful-framework.bitflames.com/


## Feedback and Suggestions

We welcome any feedback and suggestions:

- **Bug Report**: Submit an Issue on GitHub
- **Feature Request**: Submit a Feature Request on GitHub
- **Questions**: Post in GitHub Discussions
- **Security Issues**: Send an email to security@example.com

---

## License

Sanic RESTful Framework is released under the MIT License.

---

## Changelog Format Explanation

### Legend

- ✅ New Feature
- 🔧 Improvement
- 🐛 Bug Fix
- ⚠️ Breaking Change
- 📝 Documentation Update
- 🎨 Code Style Improvement
- ⚡ Performance Optimization
- 🔒 Security Fix

### Contribution

Welcome to submit Pull Requests to improve SRF!

---

*Last Updated: 2026-02-24*