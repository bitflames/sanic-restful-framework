# CSRF Middleware

The CSRF (Cross-Site Request Forgery, Cross-Site Request Forgery) middleware is used to protect the application from CSRF attacks.

## Overview

A CSRF attack is a type of attack that exploits a user's authenticated session to perform unauthorized actions.

### Example of a CSRF Attack

1. The user logs in to the bank website `bank.com` and receives an authentication cookie.
2. The user visits a malicious website `evil.com`.
3. `evil.com` contains a hidden form that automatically submits a transfer request to `bank.com`.
4. Since the browser automatically carries the cookie, the request appears to be initiated by the user.
5. The bank performs the transfer operation.

## Current Status

!!! note "In Development"
    The CSRF middleware is currently under development, and the file `srf/middleware/csrfmiddleware.py` has not been implemented yet.

## Protection Principles

CSRF protection typically uses the following methods:

### 1. CSRF Token

- The server generates a random token.
- The token is stored on the server side (Session) or sent to the client after encryption.
- The client includes the token with each request.
- The server verifies the token's validity.

### 2. SameSite Cookie

Set the `SameSite` attribute of the cookie:

```python
# Strict mode: completely block cross-site requests
Set-Cookie: sessionid=xxx; SameSite=Strict

# Lax mode: allow safe cross-site requests (GET)
Set-Cookie: sessionid=xxx; SameSite=Lax
```

### 3. Referer Check

Verify that the `Referer` header of the request comes from the same origin.

### 4. Custom Request Header

Require the client to add a custom request header (e.g., `X-Requested-With`), as cross-site requests cannot set custom headers.

## Temporary Solutions

Before the CSRF middleware is implemented, the following methods can be used:

### Method 1: Use SameSite Cookie

```python
from sanic import Sanic
from sanic.response import json

app = Sanic("MyApp")

@app.route('/api/auth/login', methods=['POST'])
async def login(request):
    # Validate user...
    
    response = json({"message": "Login successful"})
    
    # Set Cookie with SameSite
    response.cookies['session'] = session_token
    response.cookies['session']['httponly'] = True
    response.cookies['session']['secure'] = True  # HTTPS only
    response.cookies['session']['samesite'] = 'Strict'  # or 'Lax'
    
    return response
```

### Method 2: Validate Custom Request Header

```python
@app.middleware("request")
async def check_custom_header(request):
    """Check custom request header"""
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        # Check for custom header
        if not request.headers.get('X-Requested-With'):
            from sanic.response import json
            return json({"error": "Missing required header"}, status=403)
```

The client needs to add the header:

```javascript
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  },
  body: JSON.stringify(data)
});
```

### Method 3: Use JWT Token (Recommended)

JWT tokens are usually stored in localStorage and are not automatically sent, thus naturally protecting against CSRF:

```javascript
// Store Token
localStorage.setItem('access_token', token);

// Add manually when sending requests
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

## Expected CSRF Middleware Implementation

Here is a reference for the expected CSRF middleware implementation:

### Generate CSRF Token

```python
import secrets
from sanic import Sanic
from sanic.response import json

app = Sanic("MyApp")

@app.route('/api/csrf-token', methods=['GET'])
async def get_csrf_token(request):
    """Get CSRF Token"""
    # Generate random token
    csrf_token = secrets.token_hex(32)
    
    # Store in Session or Redis
    session_id = request.cookies.get('session_id')
    if session_id:
        redis = request.app.ctx.redis
        await redis.setex(f"csrf:{session_id}", 3600, csrf_token)
    
    return json({"csrf_token": csrf_token})
```

### Validate CSRF Token

```python
@app.middleware("request")
async def csrf_middleware(request):
    """CSRF Middleware"""
    # Safe methods don't need CSRF protection
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return
    
    # Public endpoints skip
    if is_public_endpoint(request):
        return
    
    # Extract CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    
    if not csrf_token:
        from sanic.response import json
        return json({"error": "CSRF token missing"}, status=403)
    
    # Validate Token
    session_id = request.cookies.get('session_id')
    if not session_id:
        from sanic.response import json
        return json({"error": "Session missing"}, status=403)
    
    redis = request.app.ctx.redis
    stored_token = await redis.get(f"csrf:{session_id}")
    
    if not stored_token or stored_token.decode() != csrf_token:
        from sanic.response import json
        return json({"error": "CSRF token invalid"}, status=403)
```

### Client Usage

```javascript
// 1. Get CSRF Token
const tokenResponse = await fetch('/api/csrf-token');
const { csrf_token } = await tokenResponse.json();

// 2. Send request with Token
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrf_token
  },
  credentials: 'include',  // Include Cookie
  body: JSON.stringify(data)
});
```

## Using sanic-csrf

Before the official middleware is implemented, you can use the third-party library `sanic-csrf`:

### Installation

```bash
pip install sanic-csrf
```

### Configuration

```python
from sanic import Sanic
from sanic_csrf import SanicCSRF

app = Sanic("MyApp")

# Initialize CSRF protection
csrf = SanicCSRF(app, secret='your-secret-key')
```

### Usage

```python
from sanic.response import html

@app.route('/form')
async def show_form(request):
    """Display form"""
    csrf_token = csrf.generate_token(request)
    
    return html(f'''
        <form method="POST" action="/submit">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <input type="text" name="data">
            <button type="submit">Submit</button>
        </form>
    ''')

@app.route('/submit', methods=['POST'])
async def submit_form(request):
    """Process form submission"""
    # CSRF validation is automatic
    data = request.form.get('data')
    return json({"message": "Success"})
```

## Best Practices

1. **Use HTTPS**: CSRF Tokens must be transmitted over HTTPS
2. **Token Uniqueness**: Use unique tokens per session
3. **Token Expiry**: Set a reasonable expiration time
4. **No Protection Needed for Safe Methods**: GET, HEAD, OPTIONS do not require CSRF protection
5. **Use SameSite Cookies**: Combine with SameSite cookies
6. **Dual Verification**: Use both CSRF tokens and Referer checks

## Specificity of API Scenarios

For pure API applications (not using Session Cookies):

### Use JWT Token

JWT Token is stored in localStorage and is not automatically sent, so no CSRF protection is needed:

```javascript
// Token is not in Cookie, CSRF attack is invalid
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

### Use Custom Header

Require all write operations to carry a custom header:

```python
@app.middleware("request")
async def require_custom_header(request):
    """Require custom header"""
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        if not request.headers.get('X-API-Key'):
            from sanic.response import json
            return json({"error": "Missing API Key"}, status=403)
```

## Frequently Asked Questions

### 1. What is the difference between CSRF and CORS?

- **CSRF**: Prevents cross-site request forgery, exploiting an authenticated session
- **CORS**: Controls cross-origin resource sharing, a browser security policy

They solve different problems and are usually configured together.

### 2. Do I still need CSRF protection if using JWT?

If the JWT token is stored in localStorage (not in a cookie), no CSRF protection is needed.

If the token is stored in a cookie, CSRF protection is needed.

### 3. What is the difference between SameSite=Strict and Lax?

- **Strict**: Completely blocks cross-site requests, most secure but may affect user experience
- **Lax**: Allows safe cross-site navigation (e.g., link clicks), balances security and user experience

### 4. Do Single Page Applications (SPAs) need CSRF protection?

If using JWT tokens stored in localStorage, no.

If using Session Cookies, yes.

## Next Steps

- Learn about [Authentication Middleware](auth-middleware.md) to understand authentication
- Read about [Rate Limiting Middleware](rate-limiting.md) to understand request limits
- View [Authentication](../../core/authentication.md) to learn about JWT usage