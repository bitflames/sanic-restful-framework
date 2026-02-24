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
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": os.getenv(
                "GITHUB_REDIRECT_URI",
                "http://localhost:8000/api/auth/social/callback"
            ),
        }
    }
```

### 登录流程

#### 流程图

```
1. 用户点击"GitHub 登录"
   ↓
2. 前端请求 GET /api/auth/social/github/login
   ↓
3. 后端返回 GitHub 授权 URL
   ↓
4. 前端重定向到 GitHub 授权页面
   ↓
5. 用户在 GitHub 上授权
   ↓
6. GitHub 重定向到 callback URL (带 code)
   ↓
7. 后端用 code 交换 access_token
   ↓
8. 后端用 access_token 获取用户信息
   ↓
9. 后端创建/获取用户账户
   ↓
10. 后端生成临时 code 存储到 Redis
   ↓
11. 前端用临时 code 换取 JWT token
```

### API 端点

SRF 自动注册以下 GitHub OAuth 端点：

#### 1. 获取授权 URL

**端点**: `GET /api/auth/social/github/login`

**请求**：

```bash
curl http://localhost:8000/api/auth/social/github/login
```

**响应**：

```json
{
  "url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&scope=user:email"
}
```

**前端处理**：

```javascript
// 获取授权 URL
const response = await fetch('/api/auth/social/github/login');
const data = await response.json();

// 重定向到 GitHub
window.location.href = data.url;
```

#### 2. 处理回调

**端点**: `GET /api/auth/social/callback`

这个端点由 GitHub 重定向触发，SRF 会自动：
1. 用 code 交换 access_token
2. 获取 GitHub 用户信息
3. 创建或获取本地用户账户
4. 生成临时 code
5. 返回前端页面（带临时 code）

**URL 格式**：

```
http://localhost:8000/api/auth/social/callback?code=xxx&state=xxx
```

#### 3. 通过临时 code 登录

**端点**: `POST /api/auth/social/github/login_by_code`

**请求**：

```bash
curl -X POST http://localhost:8000/api/auth/social/github/login_by_code \
  -H "Content-Type: application/json" \
  -d '{"code": "temporary-code-from-redis"}'
```

**响应**：

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

### 前端集成

#### React 示例

```javascript
import React, { useEffect } from 'react';

function GitHubLogin() {
  const handleGitHubLogin = async () => {
    try {
      // 1. 获取授权 URL
      const response = await fetch('/api/auth/social/github/login');
      const data = await response.json();
      
      // 2. 重定向到 GitHub
      window.location.href = data.url;
    } catch (error) {
      console.error('GitHub 登录失败:', error);
    }
  };

  return (
    <button onClick={handleGitHubLogin}>
      使用 GitHub 登录
    </button>
  );
}

// 回调页面
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
        // 3. 用临时 code 换取 JWT token
        const response = await fetch('/api/auth/social/github/login_by_code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code }),
        });
        
        const data = await response.json();
        
        // 4. 保存 token
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
    async handleGitHubLogin() {
      try {
        // 获取授权 URL
        const response = await fetch('/api/auth/social/github/login');
        const data = await response.json();
        
        // 重定向到 GitHub
        window.location.href = data.url;
      } catch (error) {
        console.error('GitHub 登录失败:', error);
      }
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
      const response = await fetch('/api/auth/social/github/login_by_code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      });
      
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

### 自定义用户创建逻辑

如果需要自定义用户创建逻辑，可以修改 `srf/auth/social_auth.py` 中的相关函数。

```python
from srf.auth.social_auth import github_callback
from models import Account, Role

async def custom_github_callback(request):
    """自定义 GitHub 回调处理"""
    # 获取 GitHub 用户信息
    github_user = await get_github_user_info(request)
    
    # 检查用户是否存在
    account = await Account.get_or_none(email=github_user['email'])
    
    if not account:
        # 创建新用户，添加自定义逻辑
        default_role = await Role.get_or_none(name='user')
        
        account = await Account.create(
            name=github_user['name'] or github_user['login'],
            email=github_user['email'],
            password=Account.hash_password(secrets.token_urlsafe(32)),
            role=default_role,
            # 自定义字段
            github_id=github_user['id'],
            github_username=github_user['login'],
            avatar_url=github_user['avatar_url'],
        )
    
    # 生成临时 code
    code = secrets.token_urlsafe(32)
    await request.app.ctx.redis.setex(
        f"social_login_code:{code}",
        300,  # 5分钟过期
        str(account.id)
    )
    
    # 返回前端页面
    return redirect(f"/auth/callback?code={code}")
```

## 添加其他社交登录

### Google OAuth 示例

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
    """Google 登录"""
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
    """Google 回调"""
    code = request.args.get("code")
    
    if not code:
        return json({"error": "Missing code"}, status=400)
    
    from srf.config import srfconfig
    config = srfconfig.SOCIAL_CONFIG['google']
    
    # 交换 access_token
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
    
    # 获取用户信息
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ) as resp:
            user_info = await resp.json()
    
    # 创建或获取用户
    # ... 类似 GitHub 的逻辑
    
    return redirect(f"/auth/callback?code={temp_code}")
```

## 安全考虑

1. **验证 state 参数**：防止 CSRF 攻击

```python
import secrets

@bp.route("/github/login", methods=["GET"])
async def github_login(request):
    # 生成 state
    state = secrets.token_urlsafe(32)
    
    # 存储 state 到 Redis
    await request.app.ctx.redis.setex(f"oauth_state:{state}", 300, "1")
    
    auth_url = f"{base_url}&state={state}"
    return json({"url": auth_url})

@bp.route("/callback", methods=["GET"])
async def callback(request):
    state = request.args.get("state")
    
    # 验证 state
    if not await request.app.ctx.redis.exists(f"oauth_state:{state}"):
        return json({"error": "Invalid state"}, status=400)
    
    # 删除 state
    await request.app.ctx.redis.delete(f"oauth_state:{state}")
    
    # 继续处理...
```

2. **HTTPS only**：生产环境必须使用 HTTPS

3. **限制作用域**：只请求必要的权限

4. **Token 过期**：临时 code 设置短的过期时间（5分钟）

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
