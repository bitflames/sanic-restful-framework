# Social Login

SRF supports social login integration and currently supports GitHub OAuth.

## Overview

SRF includes GitHub OAuth login. Other identity providers require the application to implement and register the corresponding OAuth flow itself.

### Advantages

- **Good user experience**: no extra password to remember
- **Lower registration barrier**: one-click login improves conversion
- **High security**: leverages the security mechanisms of third-party platforms
- **Automatic data retrieval**: basic user information can be obtained

## GitHub OAuth

### Preparation

#### 1. Create a GitHub OAuth App

1. Go to [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill in the application information:
   - **Application name**: Your App Name
   - **Homepage URL**: `http://localhost:8000` (development environment)
   - **Authorization callback URL**: `http://localhost:8000/api/auth/social/callback`
4. Click **"Register application"**
5. Note the **Client ID** and the generated **Client Secret**

#### 2. Configure environment variables

Add the following to the `.env` file:

```bash
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/social/callback
OAUTH_SUCCESS_REDIRECT_URI=http://localhost:3000/auth/callback
JWT_SECRET=replace-with-a-long-random-secret
SECRET_KEY=replace-with-another-long-random-secret
SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY=replace-with-another-long-random-secret
REDIS_URL=redis://localhost:6379/0
```

The secret examples here only illustrate the variable names; deployments should use secure random values. The social login callback also requires
a usable `app.ctx.redis`.

#### 3. Configure the application

The social login handlers read `request.app.config.SOCIAL_CONFIG` directly. At application startup, write the following configuration
into the Sanic configuration and register the authentication routes:

```python
import os
from sanic import Sanic
from redis.asyncio import Redis
from srf.auth.route import register_all_auth_urls
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = os.environ["JWT_SECRET"]
app.config.SECRET_KEY = os.environ["SECRET_KEY"]
app.config.SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY = os.environ["SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY"]
app.config.SOCIAL_CONFIG = {
    "github": {
        "CLIENT_ID": os.environ["GITHUB_CLIENT_ID"],
        "CLIENT_SECRET": os.environ["GITHUB_CLIENT_SECRET"],
        "AUTHORIZE_URL": "https://github.com/login/oauth/authorize",
        "REDIRECT_URI": os.environ["GITHUB_REDIRECT_URI"],
        "ACCESS_TOKEN_URL": "https://github.com/login/oauth/access_token",
        "OAUTH_SUCCESS_REDIRECT_URI": os.environ["OAUTH_SUCCESS_REDIRECT_URI"],
        "GITHUB_USER": "https://api.github.com/user",
        "GITHUB_USER_EMAIL": "https://api.github.com/user/emails",
    }
}

settings.set_app(app)
register_all_auth_urls(app, prefix="/api/auth")


@app.before_server_start
async def setup_redis(app):
    app.ctx.redis = Redis.from_url(os.environ["REDIS_URL"])


@app.before_server_stop
async def close_redis(app):
    await app.ctx.redis.aclose()
```

`SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY` is used to sign the OAuth state cookie. Production environments should set
it to an independent random secret. Optional behavior settings are as follows:

| Option                               | Default                                       | Purpose                                    |
| ------------------------------------ | --------------------------------------------- | ------------------------------------------ |
| `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY` | Falls back to `JWT_SECRET`                    | HMAC-signs the OAuth state cookie          |
| `SOCIAL_LOGIN_COOKIE_KEY`            | `oauth_state`                                 | OAuth state cookie name                    |
| `SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE`    | `600`                                         | State cookie lifetime in seconds           |
| `SOCIAL_LOGIN_COOKIE_SECURE`         | Based on whether the current request is HTTPS | Whether to send the cookie only over HTTPS |
| `SOCIAL_LOGIN_REDIS_CODE_PREFIX`     | `social-login`                                | Redis key prefix for one-time login codes  |
| `SOCIAL_LOGIN_CODE_MAX_AGE`          | `300`                                         | One-time login code lifetime in seconds    |

### Login flow

#### Flow diagram

```
1. The user clicks "Sign in with GitHub"
   ↓
2. The frontend sends a request to POST /api/auth/social/github/login
   ↓
3. The backend generates a random state, writes the timestamped signed state into an HttpOnly cookie
   ↓
4. The backend redirects directly to the GitHub authorization page
   ↓
5. The user authorizes on GitHub
   ↓
6. GitHub redirects to the backend callback URL (with the OAuth code and state)
   ↓
7. The backend verifies the signed cookie, state, and validity period, then exchanges the code for an access_token
   ↓
8. The backend uses the access_token to fetch user information and a verified email
   ↓
9. The backend creates or retrieves the user account
   ↓
10. The backend generates a random one-time code and writes it to Redis as <prefix>:<code>
   ↓
11. The backend redirects to OAUTHCALLBACK?code=<temporary code>
   ↓
12. The frontend calls POST /api/auth/social/github/login_by_code with JSON {"code":"..."} to exchange for a JWT
```

### API endpoints

The following GitHub OAuth endpoints are registered automatically by `register_all_auth_urls(app)` (or `register_social_auth_urls(app)` alone):

#### 1. Get the authorization URL

**Endpoint**: `POST /api/auth/social/github/login`

**Request**:

```bash
curl -i -X POST http://localhost:8000/api/auth/social/github/login
```

The response is a `302` redirect, and a signed OAuth state cookie is written at the same time. The cookie uses
`HttpOnly`, `SameSite=Lax`, and its path comes from `GITHUB_REDIRECT_URI`; `Secure`
is controlled by `SOCIAL_LOGIN_COOKIE_SECURE` and, when not configured, is decided by whether the current request is HTTPS.

**Frontend handling**:

```javascript
const form = document.createElement("form");
form.method = "POST";
form.action = "/api/auth/social/github/login";
document.body.appendChild(form);
form.submit(); // The browser follows the backend 302 redirect to GitHub
```

#### 2. Handle the callback

**Endpoint**: `GET /api/auth/social/callback`

This endpoint is triggered by the GitHub redirect. SRF automatically:

1. Validates the `state` in the URL against the signed, time-limited cookie
2. Exchanges the OAuth code for an access_token
3. Fetches GitHub user information and selects a verified primary email (or the first verified email if there is no primary email)
4. Creates or retrieves the local user account using the email; if no user exists for that email, SRF creates a local user and binds the OAuth account
5. Generates a random one-time code and writes it to `app.ctx.redis`
6. Redirects to `SOCIAL_CONFIG['github']['OAUTH_SUCCESS_REDIRECT_URI']?code=<one-time code>`
7. Deletes the OAuth state cookie on the normal response path

The Redis key format defaults to `social-login:<code>`, with a default lifetime of 300 seconds. It can be overridden
via `SOCIAL_LOGIN_REDIS_CODE_PREFIX` and `SOCIAL_LOGIN_CODE_MAX_AGE`.

**URL format** (GitHub → backend):

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. Log in with the temporary code

**Endpoint**: `POST /api/auth/social/github/login_by_code`

**Request** (JSON body):

```bash
curl -X POST http://localhost:8000/api/auth/social/github/login_by_code \
  -H 'Content-Type: application/json' \
  -d '{"code":"one-time-code"}'
```

**Response** (flat structure: user fields + `access_token`, not a nested `{"user": {...}}`):

```json
{
  "id": 1,
  "username": "github-user",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "last_login": null,
  "roles": null,
  "create_time": "2026-01-01 00:00:00",
  "update_time": "2026-01-01 00:00:00",
  "access_token": "...",
  "refresh_token": "..."
}
```

### Frontend integration

#### React example

```javascript
import React, { useEffect } from "react";

function GitHubLogin() {
  const handleGitHubLogin = () => {
    // The backend redirects directly to GitHub and sets the OAuth state cookie.
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "/api/auth/social/github/login";
    document.body.appendChild(form);
    form.submit(); // The browser follows the backend 302 redirect to GitHub
  };

  return <button onClick={handleGitHubLogin}>Sign in with GitHub</button>;
}

// Callback page (frontend route, corresponding to OAUTHCALLBACK)
function GitHubCallback() {
  useEffect(() => {
    const handleCallback = async () => {
      // Get the temporary code from the URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");

      if (!code) {
        console.error("No code received");
        return;
      }

      try {
        // 3. Put the temporary code in the JSON request body and exchange it for a JWT via POST
        const response = await fetch(`/api/auth/social/github/login_by_code`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });

        const data = await response.json();

        // 4. Save the token (the response has a flat structure)
        localStorage.setItem("access_token", data.access_token);

        // 5. Redirect to the home page
        window.location.href = "/";
      } catch (error) {
        console.error("Failed to get token:", error);
      }
    };

    handleCallback();
  }, []);

  return <div>Signing in...</div>;
}

export { GitHubLogin, GitHubCallback };
```

#### Vue example

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
      // The backend redirects directly to GitHub and sets the OAuth state cookie.
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/api/auth/social/github/login";
      document.body.appendChild(form);
      form.submit(); // The browser follows the backend 302 redirect to GitHub
    },
  },
};
</script>
```

**Callback page**:

```vue
<template>
  <div>Signing in...</div>
</template>

<script>
export default {
  async mounted() {
    const code = this.$route.query.code;

    if (!code) {
      this.$router.push("/login");
      return;
    }

    try {
      const response = await fetch(`/api/auth/social/github/login_by_code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });

      const data = await response.json();

      // Save the token
      localStorage.setItem("access_token", data.access_token);

      // Redirect to the home page
      this.$router.push("/");
    } catch (error) {
      console.error("Failed to get token:", error);
      this.$router.push("/login");
    }
  },
};
</script>
```

## Extending to other login providers

SRF currently only includes GitHub OAuth. Other providers require the application to implement OAuth authorization, callback validation,
local user association, and login credential issuance itself; SRF does not automatically create routes or account binding logic for them.

## Security considerations

1. **Validate the state parameter**: prevent CSRF attacks

The framework generates a random `state` for each login, signs the state together with the issuance time using HMAC-SHA256,
and writes it into an HttpOnly cookie. On callback it validates the signature, the lifetime, and the state in the URL at the same time,
using `hmac.compare_digest()`. The cookie defaults to a 600-second lifetime and is deleted on a normal callback
response. The signature only prevents tampering; it does not encrypt the state.

Production environments should configure an independent `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY` so it can be rotated separately and its purpose isolated.

2. **HTTPS only**: production environments must use HTTPS

3. **Limit scopes**: request only the necessary permissions

4. **One-time exchange**: the temporary code has a short expiry and is deleted atomically as soon as it is successfully exchanged

## Best practices

1. **Offer multiple login methods**: social login and traditional login can coexist; the application chooses how to integrate them
2. **Email policy**: the current GitHub flow only accepts verified emails; the application should also handle email conflicts explicitly
3. **User agreement**: show the user agreement and privacy policy on first login
4. **Error handling**: provide friendly error messages
5. **Logging**: log social login events

SRF currently looks up bound OAuth accounts by GitHub user ID; multi-provider account binding must be implemented separately by the application.

## Next steps

- Study [JWT Authentication](authentication.md) to learn about basic authentication
- Read [API Permissions](auth-permissions.md) to learn about permission control
