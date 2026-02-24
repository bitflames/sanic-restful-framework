# CSRF 中间件

CSRF（Cross-Site Request Forgery，跨站请求伪造）中间件用于保护应用免受 CSRF 攻击。

## 概述

CSRF 攻击是一种利用用户已认证会话执行未授权操作的攻击方式。

### CSRF 攻击示例

1. 用户登录银行网站 `bank.com`，获得认证 Cookie
2. 用户访问恶意网站 `evil.com`
3. `evil.com` 包含一个隐藏的表单，自动提交转账请求到 `bank.com`
4. 由于浏览器自动携带 Cookie，请求看起来像是用户发起的
5. 银行执行转账操作

## 当前状态

!!! note "开发中"
    CSRF 中间件目前正在开发中，文件 `srf/middleware/csrfmiddleware.py` 尚未实现。

## 防护原理

CSRF 防护通常使用以下方法：

### 1. CSRF Token

- 服务器生成一个随机 Token
- Token 存储在服务器端（Session）或加密后发送给客户端
- 客户端在每次请求时携带 Token
- 服务器验证 Token 的有效性

### 2. SameSite Cookie

设置 Cookie 的 `SameSite` 属性：

```python
# 严格模式：完全阻止跨站请求
Set-Cookie: sessionid=xxx; SameSite=Strict

# 宽松模式：允许安全的跨站请求（GET）
Set-Cookie: sessionid=xxx; SameSite=Lax
```

### 3. Referer 检查

验证请求的 `Referer` 头是否来自同源。

### 4. 自定义请求头

要求客户端添加自定义请求头（如 `X-Requested-With`），因为跨站请求无法设置自定义头。

## 临时解决方案

在 CSRF 中间件实现之前，可以使用以下方法：

### 方法 1：使用 SameSite Cookie

```python
from sanic import Sanic
from sanic.response import json

app = Sanic("MyApp")

@app.route('/api/auth/login', methods=['POST'])
async def login(request):
    # 验证用户...
    
    response = json({"message": "登录成功"})
    
    # 设置 Cookie with SameSite
    response.cookies['session'] = session_token
    response.cookies['session']['httponly'] = True
    response.cookies['session']['secure'] = True  # HTTPS only
    response.cookies['session']['samesite'] = 'Strict'  # or 'Lax'
    
    return response
```

### 方法 2：验证自定义请求头

```python
@app.middleware("request")
async def check_custom_header(request):
    """检查自定义请求头"""
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        # 检查是否有自定义头
        if not request.headers.get('X-Requested-With'):
            from sanic.response import json
            return json({"error": "Missing required header"}, status=403)
```

客户端需要添加头：

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

### 方法 3：使用 JWT Token（推荐）

JWT Token 通常存储在 localStorage 中，不会自动发送，因此天然防护 CSRF：

```javascript
// 存储 Token
localStorage.setItem('access_token', token);

// 发送请求时手动添加
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

## 预期的 CSRF 中间件实现

以下是预期的 CSRF 中间件实现方案（供参考）：

### 生成 CSRF Token

```python
import secrets
from sanic import Sanic
from sanic.response import json

app = Sanic("MyApp")

@app.route('/api/csrf-token', methods=['GET'])
async def get_csrf_token(request):
    """获取 CSRF Token"""
    # 生成随机 Token
    csrf_token = secrets.token_hex(32)
    
    # 存储到 Session 或 Redis
    session_id = request.cookies.get('session_id')
    if session_id:
        redis = request.app.ctx.redis
        await redis.setex(f"csrf:{session_id}", 3600, csrf_token)
    
    return json({"csrf_token": csrf_token})
```

### 验证 CSRF Token

```python
@app.middleware("request")
async def csrf_middleware(request):
    """CSRF 中间件"""
    # 安全方法不需要 CSRF 保护
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return
    
    # 公开端点跳过
    if is_public_endpoint(request):
        return
    
    # 提取 CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    
    if not csrf_token:
        from sanic.response import json
        return json({"error": "CSRF token missing"}, status=403)
    
    # 验证 Token
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

### 客户端使用

```javascript
// 1. 获取 CSRF Token
const tokenResponse = await fetch('/api/csrf-token');
const { csrf_token } = await tokenResponse.json();

// 2. 发送请求时携带 Token
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrf_token
  },
  credentials: 'include',  // 携带 Cookie
  body: JSON.stringify(data)
});
```

## 使用 sanic-csrf

在官方中间件实现之前，可以使用第三方库 `sanic-csrf`：

### 安装

```bash
pip install sanic-csrf
```

### 配置

```python
from sanic import Sanic
from sanic_csrf import SanicCSRF

app = Sanic("MyApp")

# 初始化 CSRF 保护
csrf = SanicCSRF(app, secret='your-secret-key')
```

### 使用

```python
from sanic.response import html

@app.route('/form')
async def show_form(request):
    """显示表单"""
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
    """处理表单提交"""
    # CSRF 验证会自动进行
    data = request.form.get('data')
    return json({"message": "Success"})
```

## 最佳实践

1. **使用 HTTPS**：CSRF Token 必须通过 HTTPS 传输
2. **Token 唯一性**：每个 Session 使用唯一的 Token
3. **Token 过期**：设置合理的过期时间
4. **安全方法不需要保护**：GET、HEAD、OPTIONS 不需要 CSRF 保护
5. **SameSite Cookie**：结合使用 SameSite Cookie
6. **双重验证**：同时使用 CSRF Token 和 Referer 检查

## API 场景的特殊性

对于纯 API 应用（不使用 Session Cookie）：

### 使用 JWT Token

JWT Token 存储在 localStorage，不会自动发送，无需 CSRF 保护：

```javascript
// Token 不在 Cookie 中，CSRF 攻击无效
fetch('/api/products', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

### 使用自定义头

要求所有写操作携带自定义头：

```python
@app.middleware("request")
async def require_custom_header(request):
    """要求自定义头"""
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        if not request.headers.get('X-API-Key'):
            from sanic.response import json
            return json({"error": "Missing API Key"}, status=403)
```

## 常见问题

### 1. CSRF 和 CORS 的区别？

- **CSRF**: 防止跨站请求伪造，利用已认证 Session
- **CORS**: 控制跨域资源共享，浏览器安全策略

两者解决不同的问题，通常需要同时配置。

### 2. 使用 JWT 还需要 CSRF 保护吗？

如果 JWT Token 存储在 localStorage（不是 Cookie），则不需要 CSRF 保护。

如果 Token 存储在 Cookie 中，则需要 CSRF 保护。

### 3. SameSite=Strict 和 Lax 的区别？

- **Strict**: 完全阻止跨站请求，最安全但可能影响用户体验
- **Lax**: 允许安全的跨站导航（如链接点击），平衡安全和用户体验

### 4. 单页应用（SPA）需要 CSRF 保护吗？

如果使用 JWT Token 且存储在 localStorage，不需要。

如果使用 Session Cookie，需要。

## 下一步

- 学习 [认证中间件](auth-middleware.md) 了解身份验证
- 阅读 [限流中间件](rate-limiting.md) 了解请求限制
- 查看 [认证](../../core/authentication.md) 了解 JWT 使用
