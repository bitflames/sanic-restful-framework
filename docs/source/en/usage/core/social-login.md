# Social Login

SRF supports social login integration, currently supporting GitHub OAuth.

## Overview

Social login allows users to log in to your application using third-party accounts (such as GitHub, Google, etc.), without the need for separate account registration.

### Advantages

- **Good User Experience**: No need to remember additional passwords
- **Lower Registration Barriers**: One-click login, improving conversion rates
- **High Security**: Utilizing the security mechanisms of third-party platforms
- **Automatic Information Retrieval**: Can retrieve user basic information

## GitHub OAuth

### Preparation

#### 1. Create a GitHub OAuth App

1. Visit [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill in the application information:
   - **Application name**: Your App Name
   - **Homepage URL**: `http://localhost:8000` (development environment)
   - **Authorization callback URL**: `http://localhost:8000/api/auth/social/callback`
4. Click **"Register application"**
5. Record **Client ID** and generate **Client Secret**

#### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/social/callback
```

#### 3. Configure Application

In `config.py`:

```python
import os

class Config:
    SOCIAL_CONFIG = {
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": os.getenv(
                "GITHUB_REDIRECT_URI",
                "http://localhost:8000/api/auth/social/callback"
            ),
        }
    }
```

### Login Process

#### Flowchart

```
1. User clicks "GitHub Login"
   ↓
2. Frontend requests GET /api/auth/social/github/login
   ↓
3. Backend returns GitHub authorization URL
   ↓
4. Frontend redirects to GitHub authorization page
   ↓
5. User authorizes on GitHub
   ↓
6. GitHub redirects to callback URL (with code)
   ↓
7. Backend exchanges code for access_token
   ↓
8. Backend retrieves user information with access_token
   ↓
9. Backend creates or retrieves user account
   ↓
10. Backend generates a temporary code stored in Redis
   ↓
11. Frontend exchanges temporary code for JWT token
```

### API Endpoints

SRF automatically registers the following GitHub OAuth endpoints:

#### 1. Get Authorization URL

**Endpoint**: `GET /api/auth/social/github/login`

**Request**:

```bash
curl http://localhost:8000/api/auth/social/github/login
```

**Response**:

```json
{
  "url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&scope=user:email"
}
```

**Frontend Handling**:

```javascript
// Get authorization URL
const response = await fetch('/api/auth/social/github/login');
const data = await response.json();

// Redirect to GitHub
window.location.href = data.url;
```

#### 2. Handle Callback

**Endpoint**: `GET /api/auth/social/callback`

This endpoint is triggered by GitHub redirect. SRF will automatically:
1. Exchange code for access_token
2. Retrieve GitHub user information
3. Create or retrieve local user account
4. Generate temporary code
5. Return frontend page (with temporary code)

**URL Format**:

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. Login with Temporary Code

**Endpoint**: `POST /api/auth/social/github/login_by_code`

**Request**:

```bash
curl -X POST http://localhost:8000/api/auth/social/github/login_by_code \
  -H "Content-Type: application/json" \
  -d '{"code": "temporary-code-from-redis"}'
```

**Response**:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "user_id": 1,
    "username": "github-user",
    "email": "user@example.com",
    "role": "user"
  }
}
```

### Frontend Integration

#### React Example

```javascript
import React, { useEffect } from 'react';

function GitHubLogin() {
  const handleGitHubLogin = async () => {
    try {
      // 1. Get authorization URL
      const response = await fetch('/api/auth/social/github/login');
      const data = await response.json();
      
      // 2. Redirect to GitHub
      window.location.href = data.url;
    } catch (error) {
      console.error('GitHub login failed:', error);
    }
  };

  return (
    <button onClick={handleGitHubLogin}>
      Login with GitHub
    </button>
  );
}

// Callback page
function GitHubCallback() {
  useEffect(() => {
    const handleCallback = async () => {
      // Get temporary code from URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (!code) {
        console.error('Code not found');
        return;
      }
      
      try {
        // 3. Exchange temporary code for JWT token
        const response = await fetch('/api/auth/social/github/login_by_code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code }),
        });
        
        const data = await response.json();
        
        // 4. Save token
        localStorage.setItem('access_token', data.access_token);
        
        // 5. Redirect to home
        window.location.href = '/';
      } catch (error) {
        console.error('Failed to get token:', error);
      }
    };
    
    handleCallback();
  }, []);

  return <div>Logging in...</div>;
}

export { GitHubLogin, GitHubCallback };
```

#### Vue Example

```vue
<template>
  <div>
    <button @click="handleGitHubLogin">Login with GitHub</button>
  </div>
</template>

<script>
export default {
  methods: {
    async handleGitHubLogin() {
      try {
        // Get authorization URL
        const response = await fetch('/api/auth/social/github/login');
        const data = await response.json();
        
        // Redirect to GitHub
        window.location.href = data.url;
      } catch (error) {
        console.error('GitHub login failed:', error);
      }
    }
  }
}
</script>
```

**Callback Page**:

```vue
<template>
  <div>Logging in...</div>
</template>

<script>
export default {
  async mounted() {
    const code = this.$route.query.code;
    
    if (!code) {
      this.$router.push('/login');
      return;
    }
    
    try {
      const response = await fetch('/api/auth/social/github/login_by_code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      });
      
      const data = await response.json();
      
      // Save token
      localStorage.setItem('access_token', data.access_token);
      
      // Redirect to home
      this.$router.push('/');
    } catch (error) {
      console.error('Failed to get token:', error);
      this.$router.push('/login');
    }
  }
}
</script>
```

### Custom User Creation Logic

If you need to customize the user creation logic, modify the relevant functions in `srf/auth/social_auth.py`.

```python
from srf.auth.social_auth import github_callback
from models import Account, Role

async def custom_github_callback(request):
    """Custom GitHub callback handling"""
    # Get GitHub user info
    github_user = await get_github_user_info(request)
    
    # Check if user exists
    account = await Account.get_or_none(email=github_user['email'])
    
    if not account:
        # Create new user, add custom logic
        default_role = await Role.get_or_none(name='user')
        
        account = await Account.create(
            name=github_user['name'] or github_user['login'],
            email=github_user['email'],
            password=Account.hash_password(secrets.token_urlsafe(32)),
            role=default_role,
            # Custom fields
            github_id=github_user['id'],
            github_username=github_user['login'],
            avatar_url=github_user['avatar_url'],
        )
    
    # Generate temporary code
    code = secrets.token_urlsafe(32)
    await request.app.ctx.redis.setex(
        f"social_login_code:{code}",
        300,  # 5 minutes expiration
        str(account.id)
    )
    
    # Redirect to frontend page
    return redirect(f"/auth/callback?code={code}")
```

## Adding Other Social Logins

### Google OAuth Example

```python
# config.py
SOCIAL_CONFIG = {
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "redirect_uri": "http://localhost:8000/api/auth/social/callback",
    },
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": "http://localhost:8000/api/auth/social/google/callback",
    }
}
```

```python
# social_auth.py
from sanic import Blueprint
from sanic.response import json, redirect
import aiohttp

bp = Blueprint("social_auth", url_prefix="/api/auth/social")

@bp.route("/google/login", methods=["GET"])
async def google_login(request):
    """Google Login"""
    from srf.config import srfconfig
    
    config = srfconfig.SOCIAL_CONFIG['google']
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={config['client_id']}"
        f"&redirect_uri={config['redirect_uri']}"
        "&response_type=code"
        "&scope=email profile"
    )
    
    return json({"url": auth_url})

@bp.route("/google/callback", methods=["GET"])
async def google_callback(request):
    """Google Callback"""
    code = request.args.get("code")
    
    if not code:
        return json({"error": "Missing code"}, status=400)
    
    from srf.config import srfconfig
    config = srfconfig.SOCIAL_CONFIG['google']
    
    # Exchange access_token
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": config['client_id'],
                "client_secret": config['client_secret'],
                "code": code,
                "redirect_uri": config['redirect_uri'],
                "grant_type": "authorization_code",
            }
        ) as resp:
            token_data = await resp.json()
    
    access_token = token_data.get("access_token")
    
    # Get user info
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ) as resp:
            user_info = await resp.json()
    
    # Create or get user
    # ... similar to GitHub logic
    
    return redirect(f"/auth/callback?code={temp_code}")
```

## Security Considerations

1. **Validate state parameter** to prevent CSRF attacks

```python
import secrets

@bp.route("/github/login", methods=["GET"])
async def github_login(request):
    # Generate state
    state = secrets.token_urlsafe(32)
    
    # Store state in Redis
    await request.app.ctx.redis.setex(f"oauth_state:{state}", 300, "1")
    
    auth_url = f"{base_url}&state={state}"
    return json({"url": auth_url})

@bp.route("/callback", methods=["GET"])
async def callback(request):
    state = request.args.get("state")
    
    # Validate state
    if not await request.app.ctx.redis.exists(f"oauth_state:{state}"):
        return json({"error": "Invalid state"}, status=400)
    
    # Delete state
    await request.app.ctx.redis.delete(f"oauth_state:{state}")
    
    # Continue processing...
```

2. **HTTPS only**: Must use HTTPS in production environments

3. **Limit scope**: Request only necessary permissions

4. **Token expiration**: Set short expiration time for temporary codes (5 minutes)

## Best Practices

1. **Provide multiple login options**: Social login + traditional email login
2. **Account binding**: Allow users to bind multiple social accounts
3. **Email verification**: Verify the validity of the email after obtaining it
4. **User agreement**: Display user agreement and privacy policy on first login
5. **Error handling**: Provide friendly error messages
6. **Log recording**: Record social login events

## Common Issues

### How to handle email conflicts?

If the email of the GitHub account is already used by another user:

```python
account = await Account.get_or_none(email=github_user['email'])

if account:
    if account.github_id != github_user['id']:
        # Email is already used by another account
        return json({"error": "This email is already used by another account"}, status=400)
```

### How to bind multiple social accounts?

Create a social account association table:

```python
class SocialAccount(Model):
    user = fields.ForeignKeyField("models.Account")
    provider = fields.CharField(max_length=50)  # github, google, etc.
    provider_user_id = fields.CharField(max_length=255)
    access_token = fields.TextField(null=True)
    
    class Meta:
        unique_together = (("provider", "provider_user_id"),)
```

## Next Steps

- Learn [JWT Authentication](authentication.md) to understand basic authentication
- Read [Interface Permission Verification](auth-permissions.md) to understand permission control
- View [Configuration Items](../../config.md) to understand social login configuration