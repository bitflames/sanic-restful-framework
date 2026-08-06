# 社交登录

SRF 支持社交登录集成，目前支持 GitHub OAuth。

## 概述

社交登录允许用户使用第三方账号（如 GitHub、Google 等）登录您的应用，无需单独注册账号。

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
```

#### 3. 配置应用

在 `config.py` 中：

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

### 登录流程

#### 流程图

```
1. 用户点击"GitHub 登录"
   ↓
2. 浏览器访问 GET /api/auth/social/github/login
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
12. 前端用 GET /api/auth/social/github/login_by_code?code=... 换取 JWT
```

### API 端点

通过 `register_auth_urls(app)` 自动注册以下 GitHub OAuth 端点：

#### 1. 获取授权 URL

**端点**: `GET /api/auth/social/github/login`

**请求**：

```bash
curl -i http://localhost:8000/api/auth/social/github/login
```

响应是 `302` 重定向，同时写入带签名的 OAuth state Cookie。该 Cookie 使用
`HttpOnly`、`SameSite=Lax`，作用路径来自 `GITHUB_REDIRECT_URI`；`Secure`
由 `SOCIAL_LOGIN_COOKIE_SECURE` 控制，未配置时根据当前请求是否为 HTTPS
决定。

**前端处理**：

```javascript
window.location.assign('/api/auth/social/github/login');
```

#### 2. 处理回调

**端点**: `GET /api/auth/social/callback`

这个端点由 GitHub 重定向触发，SRF 会自动：
1. 验证 URL 中的 `state` 与带签名、带有效期的 Cookie
2. 用 OAuth code 交换 access_token
3. 获取 GitHub 用户信息，并选择已验证的主邮箱（没有主邮箱时选择首个已验证邮箱）
4. 使用邮箱创建或获取本地用户账户；数据库中必须已有名为 `user` 的角色
5. 生成随机一次性 code，写入 `app.ctx.redis`
6. 重定向到 `SOCIAL_CONFIG['github']['OAUTHCALLBACK']?code=<一次性 code>`
7. 在正常响应路径中删除 OAuth state Cookie

Redis key 格式默认为 `social-login:<code>`，有效期默认 300 秒。可通过
`SOCIAL_LOGIN_REDIS_CODE_PREFIX` 和 `SOCIAL_LOGIN_CODE_MAX_AGE` 覆盖。

**URL 格式**（GitHub → 后端）：

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. 通过临时 code 登录

**端点**: `GET /api/auth/social/github/login_by_code`

**请求**（query 参数 `code`，不是 JSON body）：

```bash
curl "http://localhost:8000/api/auth/social/github/login_by_code?code=one-time-code"
```

**响应**（扁平结构：用户字段 + `access_token`，不是嵌套的 `{"user": {...}}`）：

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

### 前端集成

#### React 示例

```javascript
import React, { useEffect } from 'react';

function GitHubLogin() {
  const handleGitHubLogin = () => {
    // 后端会直接重定向到 GitHub，并设置 OAuth state Cookie。
    window.location.assign('/api/auth/social/github/login');
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
        // 3. 用临时 code 换取 JWT（GET + query）
        const response = await fetch(
          `/api/auth/social/github/login_by_code?code=${encodeURIComponent(code)}`
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
      window.location.assign('/api/auth/social/github/login');
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
        `/api/auth/social/github/login_by_code?code=${encodeURIComponent(code)}`
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


## 添加其他社交登录

以下 Google 示例为**自定义扩展代码**（框架目前只内置 GitHub）。配置键建议与框架 `SOCIAL_CONFIG` 风格一致，使用大写 `CLIENT_ID` 等。

### Google OAuth 示例

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
# social_auth.py（自定义扩展，非框架内置）
from sanic import Blueprint
from sanic.response import json, redirect
import aiohttp

bp = Blueprint("social_auth", url_prefix="/api/auth/social")

@bp.route("/google/login", methods=["POST"])
async def google_login(request):
    """Google 登录（自定义）"""
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
    """Google 回调（自定义）"""
    code = request.args.get("code")
    
    if not code:
        return json({"error": "Missing code"}, status=400)
    
    from srf.config import settings
    config = settings.SOCIAL_CONFIG['google']
    
    # 交换 access_token
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
    
    # 获取用户信息
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ) as resp:
            user_info = await resp.json()
    
    # 创建或获取用户，写入 Redis 一次性 code
    # ... 类似 GitHub 的逻辑（需使用 app.ctx.redis）
    
    return redirect(f"/auth/callback?code={temp_code}")
```

## 安全考虑

1. **验证 state 参数**：防止 CSRF 攻击

框架会为每次登录生成随机 `state`，使用 HMAC-SHA256 将 state 与签发时间一起
签名后写入 HttpOnly Cookie。回调时同时验证签名、有效期以及 URL 中的 state；
验证使用 `hmac.compare_digest()`。Cookie 默认有效期为 600 秒，并在回调正常
返回时删除。签名只能防止篡改，不会加密 state。

建议配置独立的 `SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY`。未配置时框架会回退到
`JWT_SECRET`，但独立密钥便于轮换和隔离用途。

2. **HTTPS only**：生产环境必须使用 HTTPS

3. **限制作用域**：只请求必要的权限

4. **一次性兑换**：临时 code 设置短过期时间，并在成功兑换时立即原子删除

## 最佳实践

1. **提供多种登录方式**：社交登录 + 传统邮箱登录
2. **账号绑定**：允许用户绑定多个社交账号
3. **邮箱验证**：获取到邮箱后验证其有效性
4. **用户协议**：首次登录显示用户协议和隐私政策
5. **错误处理**：提供友好的错误提示
6. **日志记录**：记录社交登录事件

## 常见问题

### 如何处理邮箱冲突？

如果 GitHub 账号的邮箱已被其他用户使用：

```python
account = await Account.get_or_none(email=github_user['email'])

if account:
    if account.github_id != github_user['id']:
        # 邮箱已被其他账号使用
        return json({"error": "该邮箱已被其他账号使用"}, status=400)
```

### 如何绑定多个社交账号？

创建社交账号关联表：

```python
class SocialAccount(Model):
    user = fields.ForeignKeyField("models.Account")
    provider = fields.CharField(max_length=50)  # github, google, etc.
    provider_user_id = fields.CharField(max_length=255)
    access_token = fields.TextField(null=True)
    
    class Meta:
        unique_together = (("provider", "provider_user_id"),)
```

## 下一步

- 学习 [JWT 认证](authentication.md) 了解基础认证
- 阅读 [接口权限验证](auth-permissions.md) 了解权限控制
- 查看 [配置项](../../config.md) 了解社交登录配置
