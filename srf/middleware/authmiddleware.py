import jwt
from sanic import Request
from sanic.exceptions import Unauthorized

from srf.auth.auth import retrieve_user


def is_public_endpoint(request: Request) -> bool:
    tail = request.path.rstrip("/").rpartition("/")[2]
    return tail in getattr(request.app.config, "NON_AUTH_ENDPOINTS", [])


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
    token = extract_bearer_token(request)

    try:
        payload = jwt.decode(token, request.app.config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token has expired, please login again")
    except jwt.InvalidTokenError:
        raise Unauthorized("Invalid token")

    user = await retrieve_user(payload)
    if not user:
        raise Unauthorized("User not found")

    request.ctx.user = user


async def set_user_to_request_ctx(request: Request):
    if is_public_endpoint(request):
        return

    await authenticate_request(request)
