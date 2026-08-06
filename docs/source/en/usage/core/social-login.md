# Social Login

SRF supports social login integration, currently supporting GitHub OAuth.

## Overview

Social login allows users to log in to your application using third-party accounts (such as GitHub, Google, etc.), without the need to register a separate account.

### Benefits

- **Improved User Experience**: No need to remember additional passwords
- **Lower Registration Barriers**: One-click login, improving conversion rates
- **High Security**: Utilizing the security mechanisms of third-party platforms
- **Automatic Information Retrieval**: Can retrieve user basic information

## GitHub OAuth

### Preparation

#### 1. Create GitHub OAuth App

1. Visit [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill in the application information:
   - **Application name**: Your App Name
   - **Homepage URL**: `http://localhost:8000` (development environment)
   - **Authorization callback URL**: `http://localhost:8000/api/auth/social/callback`
4. Click **"Register application"**
5. Record the **Client ID** and generate the **Client Secret**

#### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/social/callback
```

#### 3. Configure the Application

In `config.py`:

```python
import os

class Config:
    SOCIAL_CONFIG = {
        "github": {
            "CLIENT_ID": os.getenv("GITHUB_CLIENT_ID"),
            "CLIENT_SECRET": os.getenv("GITHUB_CLIENT_SECRET"),
            "REDIRECT_URI": os.getenv(
                "GITHUB_REDIRECT_URI",
                "http://localhost:8000/api/auth/social/callback"
            ),
            ...
        }
    }
```

### Login Process

#### Flowchart

```
1. User clicks "GitHub Login"
   ↓
2. Browser accesses GET /api/auth/social/github/login
   ↓
3. Backend generates a random state, writes a signed state with timestamp into an HttpOnly Cookie
   ↓
4. Backend directly redirects to GitHub authorization page
   ↓
5. User authorizes on GitHub
   ↓
6. GitHub redirects to backend callback URL (with OAuth code and state)
   ↓
7. Backend verifies the signed Cookie, state, and expiration, then exchanges code for access_token
   ↓
8. Backend retrieves user information and verified email using access_token
   ↓
9. Backend creates or retrieves user account
   ↓
10. Backend generates a random one-time code, writes it into Redis with <prefix>:<code>
   ↓
11. Backend redirects to OAUTHCALLBACK?code=<temporary code>
   ↓
12. Frontend exchanges the temporary code for JWT via GET /api/auth/social/github/login_by_code?code=...
```

### API Endpoints

The `register_auth_urls(app)` automatically registers the following GitHub OAuth endpoints:

#### 1. Get Authorization URL

**Endpoint**: `GET /api/auth/social/github/login`

**Request**:

```bash
curl -i http://localhost:8000/api/auth/social/github/login
```

The response is a `302` redirect, while also writing a signed OAuth state cookie. This cookie uses `HttpOnly`, `SameSite=Lax`, and the path comes from `GITHUB_REDIRECT_URI`; `Secure` is controlled by `SOCIAL_LOGIN_COOKIE_SECURE`. If not configured, it depends on whether the current request is HTTPS.

**Frontend Handling**:

```javascript
window.location.assign('/api/auth/social/github/login');
```

#### 2. Handle Callback

**Endpoint**: `GET /api/auth/social/callback`

This endpoint is triggered by GitHub redirection. SRF will automatically:
1. Verify the `state` in the URL against the signed, time-stamped cookie
2. Exchange OAuth code for access_token
3. Retrieve GitHub user information and select the primary verified email (or the first verified email if no primary email exists)
4. Create or retrieve a local user account using the email; the database must already have a role named `user`
5. Generate a random one-time code and write it into `app.ctx.redis`
6. Redirect to `SOCIAL_CONFIG['github']['OAUTHCALLBACK']?code=<one-time code>`
7. Delete the OAuth state cookie in the normal response path

The default Redis key format is `social-login:<code>`, with a default expiration of 300 seconds. This can be overridden via `SOCIAL_LOGIN_REDIS_CODE_PREFIX` and `SOCIAL_LOGIN_CODE_MAX_AGE`.

**URL Format** (GitHub → Backend):

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. Log in Using Temporary Code

**Endpoint**: `GET /api/auth/social/github/login_by_code`

**Request** (query parameter `code`, not JSON body):

```bash
curl "http://localhost:8000/api/auth/social/github/login_by_code?code=one-time-code"
```

**Response** (flat structure: user fields + `access_token`, not nested `{"user": {...}}`):

```json
{
  "id": 1,
  "username": "github-user",
  "email": "user@example.com",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "created_date": "2026-01-01 00:00:00",
  "updated_date": "2026-01-01 00:00:00",
  "url": "/users/1",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Frontend Integration

#### React Example

```javascript
import React, { useEffect } from 'react';

function GitHubLogin() {
  const handleGitHubLogin = () => {
    // The backend will directly redirect to GitHub and set the OAuth state Cookie.
    window.location.assign('/api/auth/social/github/login');
  };

  return (
    <button onClick={handleGitHubLogin}>
      Sign in with GitHub
    </button>
  );
}

// Callback page (frontend route, corresponding to OAUTHCALLBACK)
function GitHubCallback() {
  useEffect(() => {
    const handleCallback = async () => {
      // Get temporary code from URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (!code) {
        console.error('No code received');
        return;
      }
      
      try {
        // 3. Exchange temporary code for JWT (GET + query)
        const response = await fetch(
          `/api/auth/social/github/login_by_code?code=${encodeURIComponent(code)}`
        );
        
        const data = await response.json();
        
        // 4. Save token (response is flat structure)
        localStorage.setItem('access_token', data.access_token);
        
        // 5. Redirect to homepage
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
    <button @click="handleGitHubLogin">Sign in with GitHub</button>
  </div>
</template>

<script>
export default {
  methods: {
    handleGitHubLogin() {
      // The backend will directly redirect to GitHub and set the OAuth state Cookie.
      window.location.assign('/api/auth/social/github/login');
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
      const response = await fetch(
        `/api/auth/social/github/login_by_code?code=${encodeURIComponent(code)}`
      );
      
      const data = await response.json();
      
      // Save token
      localStorage.setItem('access_token', data.access_token);
      
      // Redirect to homepage
      this.$router.push('/');
    } catch (error) {
      console.error('Failed to get token:', error);
      this.$router.push('/login');
    }
  }
}
</script>
```


## Adding Other Social Logins

The following Google example is **custom extended code** (the framework currently only includes GitHub natively). Configuration keys are recommended to follow the framework's `SOCIAL_CONFIG` style, using uppercase `CLIENT_ID`, etc.

### Google OAuth Example

```python
# config.py
SOCIAL_CONFIG = {
    "github": {
        "CLIENT_ID": os.getenv("GITHUB_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("GITHUB_CLIENT_SECRET"),
        "REDIRECT_URI": "http://localhost:8000/api/auth/social/callback",
    },
    "google": {
        "CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "REDIRECT_URI": "http://localhost:8000/api/auth/social/google/callback",
    }
}
```

```python
# social_auth.py (custom extension, not built-in to framework)
from sanic import Blueprint
from sanic.response import json, redirect
import aiohttp

bp = Blueprint("social_auth", url_prefix="/api/auth/social")

@bp.route("/google/login", methods=["POST"])
async def google_login(request):
    """Google Login (custom)"""
    from srf.config import settings
    
    config = settings.SOCIAL_CONFIG['google']
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={config['CLIENT_ID']}"
        f"&redirect_uri={config['REDIRECT_URI']}"
        "&response_type=code"
        "&scope=email profile"
    )
    
    return json({"auth_url": auth_url})

@bp.route("/google/callback", methods=["GET"])
async def google_callback(request):
    """Google Callback (custom)"""
    code = request.args.get("code")
    
    if not code:
        return json({"error": "Missing code"}, status=400)
    
    from srf.config import settings
    config = settings.SOCIAL_CONFIG['google']
    
    # Exchange access_token
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": config['CLIENT_ID'],
                "client_secret": config['CLIENT_SECRET'],
                "code": code,
                "redirect_uri": config['REDIRECT_URI'],
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
    
    # Create or get user, write one-time code to Redis
    # ... similar logic to GitHub (use app.ctx.redis)
    
    return redirect(f"/auth/callback?code={temp_code}")
```

## Security Considerations

1. **Validate the state parameter**: Prevent CSRF attacks

The framework generates a random `state` for each login, signs it with HMAC-SHA256 along with the issuance time, and writes it into an HttpOnly Cookie. During the callback, it simultaneously validates the signature, validity, and state in the URL; validation uses `hmac.compare_digest()`. The default cookie validity is 600 seconds and is deleted upon normal return. The signature prevents tampering but does not encrypt the state.

It is recommended to configure a separate `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY`. If not configured, the framework will fall back to `JWT_SECRET`, but a separate key facilitates rotation and isolation of purposes.

2. **HTTPS Only**: Must use HTTPS in production environments

3. **Limit Scope**: Request only necessary permissions

4. **One-Time Redemption**: Set a short expiration time for temporary codes and immediately atomically delete them upon successful redemption

## Best Practices

1. **Provide multiple login methods**: Social login + traditional email login
2. **Account Binding**: Allow users to bind multiple social accounts
3. **Email Verification**: Verify the validity of the email after obtaining it
4. **User Agreement**: Display the user agreement and privacy policy on first login
5. **Error Handling**: Provide friendly error messages
6. **Log Recording**: Record social login events

## Frequently Asked Questions

### How to Handle Email Conflicts?

If the email of the GitHub account has already been used by another user:

```python
account = await Account.get_or_none(email=github_user['email'])

if account:
    if account.github_id != github_user['id']:
        # The email is already used by another account
        return json({"error": "This email is already used by another account"}, status=400)
```

### How to Bind Multiple Social Accounts?

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

- Learn [JWT Authentication](authentication.md) to understand the basics of authentication
- Read [Interface Permission Verification](auth-permissions.md) to understand permission control
- View [Configuration Items](../../config.md) to understand social login configuration