# CSRF 中间件

SRF 的 CSRF 防护由应用接入 Sanic 中间件或其他适用组件实现。浏览器使用会自动附带的 Cookie 认证写请求时，应设置合适的 `SameSite`、`Secure`、`HttpOnly` 属性。使用 `Authorization: Bearer ...` 显式发送 Token 时，传统 CSRF 风险较低，但仍需正确配置 CORS、XSS 防护和 Token 存储。
