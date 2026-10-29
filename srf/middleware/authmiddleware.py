from sanic import Request
from sanic.exceptions import Unauthorized
from sanic_jwt.authentication import Authentication
from sanic_jwt.exceptions import (
    MissingAuthorizationCookie,
    MissingAuthorizationHeader,
    MissingAuthorizationQueryArg,
    SanicJWTException,
)

from srf.auth.models import AnonymousUser


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


async def authenticate_request(request: Request, strict: bool = False):
    """Authenticate the request and load the ORM user onto ``request.ctx.user``.

    Two modes:

    * ``strict=False`` (default, optional authentication): a request with no
      credentials at all (no ``Authorization`` header, cookie, or query token)
      resolves to ``request.ctx.user = AnonymousUser()``. A *presented* token that
      is malformed, invalid, expired, forged, or whose user no longer exists
      still raises ``Unauthorized`` (401) — once the client attempts
      authentication, the attempt must succeed.
    * ``strict=True`` (mandatory authentication): every request must carry a
      valid, non-expired access token; anything else (including requests with
      no credentials at all) raises ``Unauthorized`` (401).

    Public endpoints (login, register, refresh, health checks, ...) can
    alternatively be whitelisted by the caller BEFORE this function runs,
    e.g.::

        @app.middleware("request")
        async def auth_middleware(request):
            if request.path.startswith(("/api/auth/", "/health")):
                return  # whitelist: skip authentication entirely
            await set_user_to_request_ctx(request, strict=True)
    """
    if not hasattr(request.app.ctx, "auth"):
        raise Unauthorized("Authentication is not configured")
    auth: Authentication = request.app.ctx.auth

    try:
        auth._get_token(request)
    except (MissingAuthorizationHeader, MissingAuthorizationCookie, MissingAuthorizationQueryArg) as exc:
        # No credentials at all (header / cookie / query token depending on config).
        if strict:
            raise Unauthorized("Authentication required") from exc
        request.ctx.user = AnonymousUser()
        return
    except SanicJWTException as exc:
        # Malformed header (InvalidAuthorizationHeader): the client attempted
        # authentication, so the attempt must succeed — always 401.
        raise Unauthorized(str(exc) or "Authentication required") from exc

    payload = await auth.extract_payload(request)
    if not payload:
        # A token was presented but failed verification (expired, forged, or
        # undecodable); sanic-jwt swallows the specific reason internally.
        raise Unauthorized("Invalid or expired token")

    # Sole User lookup: retrieve_user loads ORM onto request.ctx.user
    user_data = await auth.retrieve_user(request, payload)
    if not user_data or getattr(request.ctx, "user", None) is None:
        raise Unauthorized("User not found")


async def set_user_to_request_ctx(request: Request, strict: bool = False):
    """Middleware entry point; see :func:`authenticate_request` for modes."""
    await authenticate_request(request, strict=strict)
