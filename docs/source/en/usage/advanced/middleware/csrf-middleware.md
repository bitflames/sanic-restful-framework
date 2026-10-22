# CSRF Middleware

SRF's CSRF protection is implemented by the application integrating Sanic middleware or another suitable component. When browsers make write requests using automatically attached cookie authentication, appropriate `SameSite`, `Secure`, and `HttpOnly` attributes should be set. When tokens are sent explicitly with `Authorization: Bearer ...`, traditional CSRF risk is lower, but CORS, XSS protection, and token storage still need to be configured correctly.
