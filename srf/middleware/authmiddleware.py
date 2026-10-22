from sanic import Request
from sanic.exceptions import Unauthorized
from sanic_jwt.authentication import Authentication
from sanic_jwt.exceptions import InvalidAuthorizationHeader, SanicJWTException


def extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth:
        raise Unauthorized("Authentication required")

    try:
        schema, token = auth.split(None, 1)
    except ValueError:
        raise Unauthorized("Invalid authorization header format")

    if schema.lower() != "bearer" or not token:
        raise Unauthorized("Invalid authorization header format")

    return token


async def authenticate_request(request: Request):
    if not hasattr(request.app.ctx, "auth"):
        raise Unauthorized("Authentication is not configured")
    auth: Authentication = request.app.ctx.auth
    try:
        payload = await auth.extract_payload(request)
    except (InvalidAuthorizationHeader, SanicJWTException) as exc:
        raise Unauthorized(str(exc) or "Invalid authorization header format") from exc

    if not payload:
        request.ctx.user = None
        return

    # Sole User lookup: retrieve_user loads ORM onto request.ctx.user
    user_data = await auth.retrieve_user(request, payload)
    if not user_data or getattr(request.ctx, "user", None) is None:
        raise Unauthorized("User not found")


async def set_user_to_request_ctx(request: Request):
    await authenticate_request(request)
