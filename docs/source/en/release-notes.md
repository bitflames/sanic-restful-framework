# Release Notes

The version release history and changelog of the Sanic RESTful Framework.

Current package version: `srf.__version__ == "0.1.0"`.

## Version Naming Convention

SRF follows the [Semantic Versioning](https://semver.org/lang/zh-CN/) specification:

- **Major Version**: Incompatible API changes
- **Minor Version**: Backward-compatible feature additions
- **Patch Version**: Backward-compatible bug fixes

Format: `Major.Version.Patch`

## Version History

### v0.0.2 (2026-02-07)

**First official release** 🎉

#### Core Features

- ✅ **ViewSet System**
  - Implementation of BaseViewSet
  - CRUD Mixins (Create, Retrieve, Update, Destroy, List)
  - @action decorator for custom operations
  - Automatic route generation

- ✅ **Routing System**
  - SanicRouter router manager
  - Automatic discovery of methods decorated with @action
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
  - Separation of read and write Schemas
  - Automatic serialization and deserialization

- ✅ **Filtering and Search**
  - SearchFilter - Full-text search
  - JsonLogicFilter - Complex queries
  - QueryParamFilter - Precise filtering
  - OrderingFactory - Sorting

- ✅ **Pagination**
  - Pagination based on page number
  - Configurable number per page
  - Unified pagination response format

- ✅ **Middleware**
  - Authentication middleware
  - Rate limiting middleware (IP, user, path, request header)
  - CSRF middleware (planned)

- ✅ **Health Check**
  - Expandable health check system (registered via `HEALTH_CHECK_LIST`)
  - Built-in `RedisCheck`, `SQLiteCheck`

- ✅ **Exception Handling**
  - Unified exception handling mechanism
  - Custom exception classes
  - Standardized error responses

- ✅ **Utility Classes**
  - HTTP status code enumeration
  - Email sending functionality
  - Configuration management system

#### ORM Support

- Integration with Tortoise ORM
- Native asynchronous database operations

#### Documentation

- Support for complete English and Chinese documentation
- Code examples and tutorials
- API reference documentation

---

### v0.1.0 (2026-08-06)

**Security Enhancements, Configuration Cleanup, and Alignment of Documentation/Test**

#### ⚠️ Breaking Changes

- Authentication key is now explicitly passed, no longer silently uses default values
- Configuration entry unified to `settings` (`srfconfig` is deprecated)
- Some configuration items have been renamed and aligned with Sanic's uppercase convention
- ViewSet is split out from `GenericAPIView`; creation hook signature is tightened

#### ✅ New / Improved Features

- Improved social login process, reducing CSRF risk
- Login supports email or username
- Health checks are driven by `HEALTH_CHECK_LIST` and support timeouts
- Rate limiting, verification code, and other configurations are more robust, with clearer default behavior
- Completed dependencies and unit tests
- Updated Chinese documentation according to current API; recorded a list of technical debts

---

## Roadmap

### v0.2.0 (Planned)

**Target Release Date**: Not yet determined

#### Planned Improvements

- [ ] Unify login error responses to avoid account enumeration
- [ ] Strict whitelist for filter fields
- [ ] Support PATCH for real partial updates
- [x] Email sending no longer blocks the event loop (`send_verify_code` + `asyncio.to_thread`)

---

## Supported Python Versions

| SRF Version | Python Version |
|-------------|----------------|
| 0.0.x / 0.1.x | >= 3.11 |

---

## Get Updates

- **GitHub**: https://github.com/bitflames/sanic-restful-framework/
- **PyPI**: https://pypi.org/project/sanic-restful-framework/
- **Documentation**: https://sanic-restful-framework.bitflames.com/


## Feedback and Suggestions

We welcome any feedback and suggestions:

- **Bug Reports**: Submit an Issue on GitHub
- **Feature Requests**: Submit a Feature Request on GitHub
- **Questions**: Post on GitHub Discussions
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

*Last updated: 2026-08-06*