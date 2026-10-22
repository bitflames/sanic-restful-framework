# Release Notes

Release history and changelog for Sanic RESTful Framework.

Current package version: `srf.__version__ == "0.1.1"`.

## Versioning scheme

SRF follows [Semantic Versioning](https://semver.org/):

- **Major version**: Incompatible API changes
- **Minor version**: Backward-compatible feature additions
- **Patch version**: Backward-compatible bug fixes

Format: `major.minor.patch`

## Version history

### v0.1.1

- Login requests use the `account` field, which accepts a username or an email address.
- Email verification codes are six-digit numbers, handled atomically together with failure counts via a Redis Lua script.
- Added the asynchronous template email interface `send_template_email()`.
- GitHub OAuth login now uses a one-time login code flow.

### v0.0.2 (2026-02-07)

**First official release** 🎉

#### Core features

- ✅ **ViewSet system**
  - BaseViewSet implementation
  - CRUD mixins (Create, Retrieve, Update, Destroy, List)
  - The @action decorator for custom actions
  - Automatic route generation

- ✅ **Routing system**
  - SanicRouter route manager
  - Automatic discovery of methods decorated with @action
  - Supports both collection-level and detail-level actions
  - URL prefix and naming support

- ✅ **Authentication and authorization**
  - JWT (JSON Web Token) authentication
  - Social login (GitHub OAuth)
  - Email verification codes
  - Permission class system (AllowAny, IsAuthenticated, SafeMethodOnly, SuperuserOnly)
  - Authentication middleware

- ✅ **Data processing**
  - Data validation based on Pydantic
  - Separate read/write schemas
  - Automatic serialization and deserialization

- ✅ **Filtering and search**
  - SearchFilter - searches the fields configured in `search_fields`
  - QueryParamFilter - exact filtering
  - OrderingFactory - sorting

- ✅ **Pagination**
  - Page-number-based pagination
  - Configurable page size
  - Unified paginated response format

- ✅ **Middleware**
  - Authentication middleware
  - Rate limiting middleware (IP, user, path, headers)
  - Authentication and rate limiting middleware (no CSRF middleware)

- ✅ **Health checks**
  - Extensible health check system (registered via `HEALTH_CHECK_LIST`)
  - Built-in `RedisCheck` and `SQLiteCheck`

- ✅ **Exception handling**
  - Unified exception handling mechanism
  - Custom exception classes
  - Standardized error responses

- ✅ **Utilities**
  - HTTP status code enums
  - Email sending
  - Configuration management system

#### ORM support

- Tortoise ORM integration
- Native asynchronous database operations

#### Documentation

- Complete English and Chinese documentation
- Code examples and tutorials
- API reference documentation

---

### v0.1.0 (2026-08-06)

**Security hardening, configuration cleanup, and documentation/test alignment**

#### ⚠️ Breaking changes

- Authentication keys are now passed explicitly instead of silently using defaults
- The configuration entry point is unified as `srf.config.settings`
- Several configuration options were renamed and aligned with Sanic's uppercase convention
- `GenericAPIView` was split out of ViewSet; create hook signatures were tightened

#### ✅ Added / Improved

- Refined the social login flow to reduce CSRF risk
- Login supports either email or username
- Health checks are driven by `HEALTH_CHECK_LIST` and support timeouts
- Configuration for rate limiting, verification codes, and more is more robust, with clearer default behavior
- Completed dependencies and unit tests
- Updated the Chinese documentation to the current API; recorded the technical debt list

---

## Roadmap

### v0.2.0 (planned)

**Target release date**: TBD

#### Planned improvements

- [ ] Unify login error responses to prevent account enumeration
- [ ] Strict allowlists for filter fields
- [ ] True partial updates for PATCH
- [ ] Add a configurable password strength validator that lets projects compose length, character-type, and other password rules as needed, and use it consistently for registration and password changes

---

## Supported Python versions

| SRF version | Python version |
|----------|-------------|
| 0.0.x / 0.1.x | >= 3.11 |

---

## Getting updates

- **GitHub**: <https://github.com/bitflames/sanic-restful-framework/>
- **PyPI**: <https://pypi.org/project/sanic-restful-framework/>
- **Documentation**: <https://sanic-restful-framework.bitflames.com/>

## Feedback and suggestions

We welcome any feedback and suggestions:

- **Bug reports**: submit an Issue on GitHub
- **Feature requests**: submit a Feature Request on GitHub
- **Questions**: post in GitHub Discussions
- **Security issues**: email <1364707405c@gmail.com>

---

## License

Sanic RESTful Framework is released under the MIT License.

---

## Changelog format

### Legend

- ✅ New feature
- 🔧 Improvement
- 🐛 Bug fix
- ⚠️ Breaking change
- 📝 Documentation update
- 🎨 Code style improvement
- ⚡ Performance optimization
- 🔒 Security fix

### Contributing

Pull Requests to help improve SRF are welcome!

---

*Last updated: 2026-08-06*
