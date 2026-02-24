# Authentication Middleware

The authentication middleware automatically handles JWT Token validation and adds user information to the request context.

## Overview

Main functions of the authentication middleware:

- Extract JWT Token from request headers
- Validate the validity of the Token
- Extract user ID from the Token
- Load user information and store it in the request context
- Handle public endpoints (no authentication required)

## Quick Start

### 1. Configure Middleware

```python
from sanic import Sanic
from srf.middleware.authmiddleware import set_user_to_request_ctx

app = Sanic("MyApp")

@app.middleware("request")
async def auth_middleware(request):
    """Authentication middleware"""
    await set_user_to_request_ctx(request)
```

### 2. Configure Public Endpoints

Define endpoints that do not require authentication in the configuration file:

```python
# config.py
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # Public product list
        "/health/",
    ]
```

### 3. Use in ViewSet

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        """Create product"""
        # Get current user
        user = self.get_current_user(request)
        
        if user:
            print(f"User {user.name} is creating a product")
        else:
            print("Anonymous user access")
```

## Working Principle

### Middleware Flow

```
1. Check if it's a public endpoint
   ├─ Yes: Skip authentication, continue processing the request
   └─ No: Continue the authentication process

2. Extract Bearer Token
   ├─ Authorization header exists
   │  └─ Extract Token
   └─ Authorization header does not exist
      └─ Skip authentication (request.ctx.user = None)

3. Validate Token
   ├─ Token is valid
   │  ├─ Extract user_id
   │  ├─ Load user information
   │  └─ Store in request.ctx.user
   └─ Token is invalid
      └─ request.ctx.user = None

4. Continue processing the request
```

### Core Functions

#### is_public_endpoint(request)

Check if the request path is a public endpoint:

```python
from srf.middleware.authmiddleware import is_public_endpoint

def is_public_endpoint(request):
    """Check if it's a public endpoint
    
    Args:
        request: Request object
    
    Returns:
        bool: True indicates a public endpoint, False indicates it requires authentication
    """
    from srf.config import srfconfig
    
    path = request.path
    non_auth_endpoints = srfconfig.NON_AUTH_ENDPOINTS
    
    # Exact match or prefix match
    for endpoint in non_auth_endpoints:
        if path == endpoint or path.startswith(endpoint):
            return True
    
    return False
```

#### extract_bearer_token(request)

Extract Bearer Token from the Authorization header:

```python
from srf.middleware.authmiddleware import extract_bearer_token

def extract_bearer_token(request):
    """Extract Bearer Token
    
    Args:
        request: Request object
    
    Returns:
        str | None: Token string, returns None if not found
    """
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None
```

#### authenticate_request(request)

Validate the Token and return user information:

```python
async def authenticate_request(request):
    """Validate the request and return the user
    
    Args:
        request: Request object
    
    Returns:
        User | None: User object, returns None if validation fails
    """
    token = extract_bearer_token(request)
    
    if not token:
        return None
    
    try:
        # Validate JWT Token
        payload = verify_jwt_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            return None
        
        # Load user
        from models import Account
        user = await Account.get_or_none(id=user_id).prefetch_related('role')
        
        return user
    except Exception as e:
        # Token is invalid or expired
        return None
```

## Public Endpoint Configuration

### Exact Match

```python
NON_AUTH_ENDPOINTS = [
    "/api/auth/login",        # Exact match /api/auth/login
    "/api/auth/register",     # Exact match /api/auth/register
]
```

### Prefix Match

```python
NON_AUTH_ENDPOINTS = [
    "/api/public/",           # Match all /api/public/* paths
    "/health/",               # Match all /health/* paths
]
```

### Mixed Configuration

```python
NON_AUTH_ENDPOINTS = [
    # Authentication-related
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/send-verification-email",
    "/api/auth/social/",
    
    # Public API
    "/api/public/",
    
    # Health check
    "/health/",
    
    # Static files
    "/static/",
    "/media/",
]
```

## Get Current User

### In ViewSet

```python
from srf.views import BaseViewSet

class OrderViewSet(BaseViewSet):
    async def list(self, request):
        """Get order list"""
        # Method 1: use get_current_user
        user = self.get_current_user(request)
        
        # Method 2: directly access request.ctx.user
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        
        if not user:
            from sanic.response import json
            return json({"error": "Not logged in"}, status=401)
        
        # Get user's orders
        orders = await Order.filter(user_id=user.id)
        # ...
```

### In Route Handler

```python
from sanic.response import json

@app.route('/api/profile')
async def get_profile(request):
    """Get user profile"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if not user:
        return json({"error": "Not logged in"}, status=401)
    
    return json({
        "id": user.id,
        "name": user.name,
        "email": user.email,
    })
```

### In Custom Middleware

```python
@app.middleware("request")
async def log_user(request):
    """Log user information"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if user:
        print(f"User {user.id} ({user.name}) is accessing {request.path}")
    else:
        print(f"Anonymous user is accessing {request.path}")
```

## Full Example

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from sanic.response import json

app = Sanic("MyApp")

# Configure public endpoints
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/products",
        "/health/",
    ]

app.config.update_config(Config)
srfconfig.set_app(app)

# Register authentication middleware
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)

# Log user access
@app.middleware("request")
async def log_access(request):
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    user_info = f"User {user.id}" if user else "Anonymous"
    print(f"{user_info} - {request.method} {request.path}")

# ViewSet example
class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @property
    def queryset(self):
        # Return only the current user's orders
        user = self.get_current_user(request)
        if user:
            return Order.filter(user_id=user.id)
        return Order.none()

# Route example
@app.route('/api/me')
async def get_current_user_info(request):
    """Get current user information"""
    user = request.ctx.user if hasattr(request.ctx, 'user') else None
    
    if not user:
        return json({"error": "Not logged in"}, status=401)
    
    return json({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.name if user.role else None,
    })
```

## Token Refresh

### Implement Token Refresh Mechanism

```python
from sanic_jwt import refresh_token_required

@app.route('/api/auth/refresh', methods=['POST'])
@refresh_token_required
async def refresh(request):
    """Refresh access token"""
    from sanic_jwt import generate_access_token
    
    user = request.ctx.user
    
    # Generate new access token
    access_token = await generate_access_token(
        request.app,
        user,
        refresh_request=True
    )
    
    return json({
        "access_token": access_token
    })
```

### Client Usage

```javascript
// Save tokens
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);

// Use access token when making requests
fetch('/api/orders', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

// Refresh access token when it expires
async function refreshAccessToken() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('refresh_token')}`
    }
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
}
```

## Security Best Practices

### 1. Use HTTPS

HTTPS must be used for token transmission in production environments:

```python
# Configure SSL
app.run(
    host="0.0.0.0",
    port=443,
    ssl={'cert': 'cert.pem', 'key': 'key.pem'}
)
```

### 2. Set Appropriate Expiration Time

```python
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
```

### 3. Token Blacklist

Implement a token blacklist mechanism (for logout):

```python
import aioredis

async def blacklist_token(token):
    """Add Token to blacklist"""
    redis = request.app.ctx.redis
    # Store in Redis, with expiration time matching the Token
    await redis.setex(f"blacklist:{token}", 3600, "1")

async def is_token_blacklisted(token):
    """Check if Token is in the blacklist"""
    redis = request.app.ctx.redis
    return await redis.exists(f"blacklist:{token}")

# Check in middleware
@app.middleware("request")
async def check_blacklist(request):
    token = extract_bearer_token(request)
    if token and await is_token_blacklisted(token):
        from sanic.response import json
        return json({"error": "Token has been invalidated"}, status=401)
```

### 4. Limit Token Usage Scope

Add additional information in the Token payload:

```python
async def authenticate(request):
    # ... validate user ...
    
    return {
        "user_id": user.id,
        "username": user.name,
        "role": user.role.name,
        "ip": request.ip,  # Bind IP
        "device": request.headers.get('User-Agent'),  # Bind device
    }

# Validate in middleware
async def authenticate_request(request):
    payload = verify_jwt_token(token)
    
    # Validate IP
    if payload.get('ip') != request.ip:
        return None
    
    # Load user
    user = await Account.get_or_none(id=payload['user_id'])
    return user
```

## Troubleshooting

### Common Issues

#### 1. Token Validation Failure

**Symptoms**: The request returns 401, but the Token appears to be valid

**Check**:
- Is the Token format correct (Bearer + space + Token)?
- Is the Token expired?
- Does the JWT Secret match?
- Is the Token in the blacklist?

**Debugging**:

```python
import jwt

# Decode Token (without verification)
try:
    payload = jwt.decode(token, options={"verify_signature": False})
    print(payload)  # View payload content
except Exception as e:
    print(f"Decoding failed: {e}")
```

#### 2. User Information Not Set

**Symptoms**: `request.ctx.user` is None

**Check**:
- Has the authentication middleware been registered?
- Is it in the public endpoint list?
- Does the user exist in the database?

**Debugging**:

```python
@app.middleware("request")
async def debug_auth(request):
    token = extract_bearer_token(request)
    print(f"Path: {request.path}")
    print(f"Token: {token}")
    print(f"Is public: {is_public_endpoint(request)}")
    print(f"User: {request.ctx.user if hasattr(request.ctx, 'user') else None}")
```

#### 3. Performance Issues

**Symptoms**: Each request is slow

**Cause**: Querying the database to load the user on every request

**Solution**: Use caching

```python
async def authenticate_request(request):
    token = extract_bearer_token(request)
    if not token:
        return None
    
    payload = verify_jwt_token(token)
    user_id = payload.get('user_id')
    
    # Try to get from cache
    redis = request.app.ctx.redis
    cache_key = f"user:{user_id}"
    cached = await redis.get(cache_key)
    
    if cached:
        import json
        user_data = json.loads(cached)
        # Construct user object from cached data
        # ...
    else:
        # Load from database
        user = await Account.get_or_none(id=user_id)
        # Store in cache (5 minutes)
        await redis.setex(cache_key, 300, json.dumps(user_data))
    
    return user
```

## Next Steps

- Learn [Authentication](../../core/authentication.md) to understand details about JWT authentication
- Read [Permissions](../../core/permissions.md) to understand permission control
- View [CSRF Middleware](csrf-middleware.md) to learn about CSRF protection