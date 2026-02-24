# Authentication

SRF provides a complete authentication system, supporting JWT authentication and social login.

## JWT Authentication

SRF uses the `sanic-jwt` library to implement JWT (JSON Web Token) authentication, providing a stateless authentication mechanism.

### Basic Concepts

JWT is a token-based authentication method:

1. When a user logs in, the server verifies the credentials and generates a JWT Token
2. The client carries the Token in subsequent requests (usually in the Authorization header)
3. The server verifies the Token and identifies the user's identity
4. The Token contains user information and an expiration time

### Configure JWT

#### 1. Set Environment Variables

In the `.env` file:

```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24 hours
```

#### 2. Configuration File

In `config.py`:

```python
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
```

#### 3. Implement Authentication Functions

Create `auth.py`:

```python
from models import Account
from sanic.exceptions import Unauthorized

async def authenticate(request):
    """Verify user credentials

    Args:
        request: Request object containing JSON data (email and password)

    Returns:
        dict: JWT payload containing user information

    Raises:
        Unauthorized: Raised when authentication fails
    """
    email = request.json.get("email")
    password = request.json.get("password")

    if not email or not password:
        raise Unauthorized("Please provide email and password")

    # Find user
    account = await Account.get_or_none(email=email)
    if not account:
        raise Unauthorized("Email or password is incorrect")

    # Verify password
    if not account.verify_password(password):
        raise Unauthorized("Email or password is incorrect")

    # Check account status
    if not account.is_active:
        raise Unauthorized("Account has been disabled")

    # Update last login time
    from datetime import datetime
    account.last_login = datetime.now()
    await account.save()

    # Return JWT payload
    return {
        "user_id": account.id,
        "username": account.name,
        "email": account.email,
        "role": account.role.name if account.role else "user",
    }

async def retrieve_user(request, payload, *args, **kwargs):
    """Retrieve user object from JWT payload

    Args:
        request: Request object
        payload: JWT payload (contains user_id etc.)

    Returns:
        Account: User object
    """
    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    account = await Account.get_or_none(id=user_id).prefetch_related("role")
    return account

async def store_user(request, user_id):
    """Store user in request context

    Args:
        request: Request object
        user_id: User ID
    """
    account = await Account.get_or_none(id=user_id).prefetch_related("role")
    if account:
        request.ctx.user = account
```

#### 4. Initialize JWT

In `app.py`:

```python
from sanic import Sanic
from srf.auth.viewset import setup_auth
from auth import authenticate, retrieve_user, store_user
from config import config

app = Sanic("MyApp")

# Initialize JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)
```

### Login Process

#### 1. User Login

**Request**:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**Response**:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 2. Access Protected Endpoints with Token

**Request**:

```bash
curl http://localhost:8000/api/products \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### User Registration

#### 1. Create Register View

```python
from sanic.response import json
from sanic.exceptions import InvalidUsage
from models import Account, Role
from schemas import AccountSchemaWriter
import aioredis

async def register(request):
    """User registration

    Request body:
        email: Email
        password: Password
        name: Name
        code: Verification code
    """
    try:
        # Validate data
        data = AccountSchemaWriter(**request.json)
    except Exception as e:
        raise InvalidUsage(str(e))

    # Verify email verification code
    code = request.json.get("code")
    if not code:
        raise InvalidUsage("Please provide verification code")

    # Get verification code from Redis
    redis = request.app.ctx.redis
    stored_code = await redis.get(f"email_code:{data.email}")

    if not stored_code or stored_code.decode() != code:
        raise InvalidUsage("Verification code is incorrect or expired")

    # Check if email is already registered
    if await Account.filter(email=data.email).exists():
        raise InvalidUsage("This email is already registered")

    # Create user
    default_role = await Role.get_or_none(name="user")
    account = await Account.create(
        email=data.email,
        name=data.name,
        password=data.password,  # Model will automatically hash the password
        role=default_role,
    )

    # Delete verification code
    await redis.delete(f"email_code:{data.email}")

    return json({
        "message": "Registration successful",
        "user": {
            "id": account.id,
            "email": account.email,
            "name": account.name,
        }
    }, status=201)
```

#### 2. Send Verification Code

```python
from srf.tools.email import send_email
import random
import string

async def send_verification_email(request):
    """Send email verification code"""
    email = request.json.get("email")
    if not email:
        raise InvalidUsage("Please provide an email address")

    # Generate 6-digit verification code
    code = ''.join(random.choices(string.digits, k=6))

    # Store in Redis (expires in 10 minutes)
    redis = request.app.ctx.redis
    await redis.setex(f"email_code:{email}", 600, code)

    # Send email
    await send_email(
        to=email,
        subject="Verification Code",
        content=f"Your verification code is: {code}, valid for 10 minutes."
    )

    return json({"message": "Verification code sent"})
```

#### 3. Register Routes

```python
from srf.auth.route import register_auth_urls

# Register authentication routes (including login, registration, etc.)
register_auth_urls(app, prefix="/api/auth")
```

### Get Current User

Get the currently logged-in user in a ViewSet:

```python
from srf.views import BaseViewSet
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """Create product"""
        # Get current user
        current_user = self.get_current_user(request)

        if not current_user:
            return json({"error": "Not logged in"}, status=401)

        # Use user information
        print(f"User {current_user.name} is creating a product")

        # ... creation logic ...
```

## Authentication Middleware

The authentication middleware automatically handles JWT token validation and adds user information to the request context.

### Configure Middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    """Authentication middleware"""
    await set_user_to_request_ctx(request)
```

### Public Endpoint Configuration

Configure endpoints that do not require authentication:

```python
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # Public product list
        "/health/",
    ]
```

### Middleware Workflow

1. Extract the Bearer Token from the Authorization header
2. Validate the token's validity
3. Extract user_id from the token
4. Load user information from the database
5. Store the user in `request.ctx.user`

## Full Example

### Account Model

```python
from tortoise import fields
from tortoise.models import Model
import bcrypt

class Role(Model):
    """Role model"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField(null=True)

class Account(Model):
    """Account model"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password = fields.CharField(max_length=255)
    role = fields.ForeignKeyField("models.Role", related_name="accounts", null=True)
    is_active = fields.BooleanField(default=True)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode(), self.password.encode())

    async def save(self, *args, **kwargs):
        """Hash password before saving"""
        if self._custom_generated_pk or not self.pk:
            # New account, hash password
            self.password = self.hash_password(self.password)
        await super().save(*args, **kwargs)
```

### Schema Definitions

```python
from pydantic import BaseModel, EmailStr, Field

class AccountSchemaWriter(BaseModel):
    """Account write schema"""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=6, max_length=50, description="Password")
    name: str = Field(..., min_length=1, max_length=100, description="Name")

class AccountSchemaReader(BaseModel):
    """Account read schema"""
    id: int
    email: str
    name: str
    is_active: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True
```

### Application Configuration

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.auth.viewset import setup_auth
from srf.auth.route import register_auth_urls
from srf.middleware.authmiddleware import set_user_to_request_ctx
from auth import authenticate, retrieve_user, store_user
from config import config

app = Sanic("MyApp")
srfconfig.set_app(app)

# Configure JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)

# Register authentication routes
register_auth_urls(app, prefix="/api/auth")

# Authentication middleware
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

## Best Practices

1. **Securely Store Passwords**: Use strong encryption algorithms like bcrypt
2. **Token Expiration Time**: Set a reasonable expiration time (e.g., 24 hours)
3. **Refresh Token**: Implement a token refresh mechanism
4. **HTTPS**: Use HTTPS in production environments
5. **Verify Email**: Send verification emails during registration
6. **Limit Login Attempts**: Prevent brute force attacks
7. **Log Login Activities**: Record login times and IP addresses
8. **Role-Based Permissions**: Use roles to manage user permissions

## Next Steps

- Learn [Permissions](permissions.md) to understand detailed permission control
- Read [Authentication Middleware](../advanced/middleware/auth-middleware.md) to understand middleware principles
- View [Views](viewsets.md) to learn how to use authentication in ViewSets