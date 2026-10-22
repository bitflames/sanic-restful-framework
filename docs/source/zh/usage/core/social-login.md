# 社交登录

SRF 支持社交登录集成，目前支持 GitHub OAuth。

## 概述

SRF 内置 GitHub OAuth 登录。其他身份提供商需要应用自行实现和注册对应的 OAuth 流程。

### 优势

- **用户体验好**：无需记住额外的密码
- **降低注册门槛**：一键登录，提高转化率
- **安全性高**：利用第三方平台的安全机制
- **自动获取信息**：可获取用户的基本信息

## GitHub OAuth

### 准备工作

#### 1. 创建 GitHub OAuth App

1. 访问 [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. 点击 **"New OAuth App"**
3. 填写应用信息：
   - **Application name**: Your App Name
   - **Homepage URL**: `http://localhost:8000` (开发环境)
   - **Authorization callback URL**: `http://localhost:8000/api/auth/social/callback`
4. 点击 **"Register application"**
5. 记录 **Client ID** 和生成 **Client Secret**

#### 2. 配置环境变量

在 `.env` 文件中添加：

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

这里的密钥示例仅用于说明变量名称，部署时应使用安全的随机值。社交登录回调还需要
可用的 `app.ctx.redis`。

#### 3. 配置应用

社交登录处理器直接读取 `request.app.config.SOCIAL_CONFIG`。应用启动时将以下配置
写入 Sanic 配置，并注册认证路由：

```python
import os
from sanic import Sanic
from redis.asyncio import Redis
from srf.auth.route import register_auth_urls
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
register_auth_urls(app, prefix="/api/auth")


@app.before_server_start
async def setup_redis(app):
    app.ctx.redis = Redis.from_url(os.environ["REDIS_URL"])


@app.before_server_stop
async def close_redis(app):
    await app.ctx.redis.aclose()
```

`SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY` 用于签名 OAuth state Cookie。生产环境应设置
为独立的随机密钥。可选行为配置如下：

| 配置项 | 默认值 | 作用 |
| --- | --- | --- |
| `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY` | 回退到 `JWT_SECRET` | HMAC 签名 OAuth state Cookie |
| `SOCIAL_LOGIN_COOKIE_KEY` | `oauth_state` | OAuth state Cookie 名称 |
| `SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE` | `600` | state Cookie 有效期，秒 |
| `SOCIAL_LOGIN_COOKIE_SECURE` | 根据当前请求是否为 HTTPS | 是否只通过 HTTPS 发送 Cookie |
| `SOCIAL_LOGIN_REDIS_CODE_PREFIX` | `social-login` | Redis 一次性登录码 key 前缀 |
| `SOCIAL_LOGIN_CODE_MAX_AGE` | `300` | 一次性登录码有效期，秒 |

### 登录流程

#### 流程图

```
1. 用户点击"GitHub 登录"
   ↓
2. 前端向 POST /api/auth/social/github/login 发起请求
   ↓
3. 后端生成随机 state，将带时间戳的签名 state 写入 HttpOnly Cookie
   ↓
4. 后端直接重定向到 GitHub 授权页面
   ↓
5. 用户在 GitHub 上授权
   ↓
6. GitHub 重定向到后端 callback URL（带 OAuth code 和 state）
   ↓
7. 后端验证签名 Cookie、state 和有效期，再用 code 交换 access_token
   ↓
8. 后端用 access_token 获取用户信息和已验证邮箱
   ↓
9. 后端创建/获取用户账户
   ↓
10. 后端生成随机一次性 code，以 <前缀>:<code> 写入 Redis
   ↓
11. 后端重定向到 OAUTHCALLBACK?code=<临时 code>
   ↓
12. 前端用 POST /api/auth/social/github/login_by_code with JSON {"code":"..."} 换取 JWT
```

### API 端点

通过 `register_auth_urls(app)` 自动注册以下 GitHub OAuth 端点：

#### 1. 获取授权 URL

**端点**: `POST /api/auth/social/github/login`

**请求**：

```bash
curl -i -X POST http://localhost:8000/api/auth/social/github/login
```

响应是 `302` 重定向，同时写入带签名的 OAuth state Cookie。该 Cookie 使用
`HttpOnly`、`SameSite=Lax`，作用路径来自 `GITHUB_REDIRECT_URI`；`Secure`
由 `SOCIAL_LOGIN_COOKIE_SECURE` 控制，未配置时根据当前请求是否为 HTTPS
决定。

**前端处理**：

```javascript
const form = document.createElement('form');
form.method = 'POST';
form.action = '/api/auth/social/github/login';
document.body.appendChild(form);
form.submit(); // 浏览器跟随后端 302 跳转到 GitHub
```

#### 2. 处理回调

**端点**: `GET /api/auth/social/callback`

这个端点由 GitHub 重定向触发，SRF 会自动：
1. 验证 URL 中的 `state` 与带签名、带有效期的 Cookie
2. 用 OAuth code 交换 access_token
3. 获取 GitHub 用户信息，并选择已验证的主邮箱（没有主邮箱时选择首个已验证邮箱）
4. 使用邮箱创建或获取本地用户账户；若该邮箱对应用户不存在，SRF 会创建本地用户并绑定 OAuth 账号
5. 生成随机一次性 code，写入 `app.ctx.redis`
6. 重定向到 `SOCIAL_CONFIG['github']['OAUTH_SUCCESS_REDIRECT_URI']?code=<一次性 code>`
7. 在正常响应路径中删除 OAuth state Cookie

Redis key 格式默认为 `social-login:<code>`，有效期默认 300 秒。可通过
`SOCIAL_LOGIN_REDIS_CODE_PREFIX` 和 `SOCIAL_LOGIN_CODE_MAX_AGE` 覆盖。

**URL 格式**（GitHub → 后端）：

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. 通过临时 code 登录

**端点**: `POST /api/auth/social/github/login_by_code`

**请求**（JSON body）：

```bash
curl -X POST http://localhost:8000/api/auth/social/github/login_by_code \
  -H 'Content-Type: application/json' \
  -d '{"code":"one-time-code"}'
```

**响应**（扁平结构：用户字段 + `access_token` + `refresh_token`，不是嵌套的 `{"user": {...}}`）：

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

### 前端集成

#### React 示例

```javascript
import React, { useEffect } from 'react';

function GitHubLogin() {
  const handleGitHubLogin = () => {
    // 后端会直接重定向到 GitHub，并设置 OAuth state Cookie。
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/api/auth/social/github/login';
    document.body.appendChild(form);
    form.submit(); // 由浏览器跟随后端 302 跳转到 GitHub
  };

  return (
    <button onClick={handleGitHubLogin}>
      使用 GitHub 登录
    </button>
  );
}

// 回调页面（前端路由，对应 OAUTHCALLBACK）
function GitHubCallback() {
  useEffect(() => {
    const handleCallback = async () => {
      // 从 URL 获取临时 code
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (!code) {
        console.error('未获取到 code');
        return;
      }
      
      try {
        // 3. 将临时 code 放入 JSON 请求体，通过 POST 换取 JWT
        const response = await fetch(
          `/api/auth/social/github/login_by_code`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
          }
        );
        
        const data = await response.json();
        
        // 4. 保存 token（响应为扁平结构）
        localStorage.setItem('access_token', data.access_token);
        
        // 5. 跳转到首页
        window.location.href = '/';
      } catch (error) {
        console.error('获取 token 失败:', error);
      }
    };
    
    handleCallback();
  }, []);

  return <div>正在登录...</div>;
}

export { GitHubLogin, GitHubCallback };
```

#### Vue 示例

```vue
<template>
  <div>
    <button @click="handleGitHubLogin">使用 GitHub 登录</button>
  </div>
</template>

<script>
export default {
  methods: {
    handleGitHubLogin() {
      // 后端会直接重定向到 GitHub，并设置 OAuth state Cookie。
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = '/api/auth/social/github/login';
      document.body.appendChild(form);
      form.submit(); // 由浏览器跟随后端 302 跳转到 GitHub
    }
  }
}
</script>
```

**回调页面**：

```vue
<template>
  <div>正在登录...</div>
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
        `/api/auth/social/github/login_by_code`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code }),
        }
      );
      
      const data = await response.json();
      
      // 保存 token
      localStorage.setItem('access_token', data.access_token);
      
      // 跳转到首页
      this.$router.push('/');
    } catch (error) {
      console.error('获取 token 失败:', error);
      this.$router.push('/login');
    }
  }
}
</script>
```


## 扩展其他登录提供商

SRF 目前只内置 GitHub OAuth。其他提供商需要应用自行实现 OAuth 授权、回调校验、
本地用户关联和登录凭据签发；SRF 不会自动为其创建路由或账号绑定逻辑。

## 安全考虑

1. **验证 state 参数**：防止 CSRF 攻击

框架会为每次登录生成随机 `state`，使用 HMAC-SHA256 将 state 与签发时间一起
签名后写入 HttpOnly Cookie。回调时同时验证签名、有效期以及 URL 中的 state；
验证使用 `hmac.compare_digest()`。Cookie 默认有效期为 600 秒，并在回调正常
返回时删除。签名只能防止篡改，不会加密 state。

生产环境应配置独立的 `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY`，以便单独轮换并隔离用途。

2. **HTTPS only**：生产环境必须使用 HTTPS

3. **限制作用域**：只请求必要的权限

4. **一次性兑换**：临时 code 设置短过期时间，并在成功兑换时立即原子删除

## 最佳实践

1. **提供多种登录方式**：社交登录与传统登录可以并存，由应用选择接入方式
2. **邮箱策略**：当前 GitHub 流程只接受已验证邮箱；应用还应明确处理邮箱冲突
3. **用户协议**：首次登录时显示用户协议和隐私政策
4. **错误处理**：提供友好的错误提示
5. **日志记录**：记录社交登录事件

SRF 当前按 GitHub 用户 ID 查找已绑定的 OAuth 账号；多提供商账号绑定需由应用另行实现。

## 下一步

- 学习 [JWT 认证](authentication.md) 了解基础认证
- 阅读 [接口权限验证](auth-permissions.md) 了解权限控制
