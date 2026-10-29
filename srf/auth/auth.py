import hashlib
import hmac
from datetime import timedelta

from pydantic import ValidationError
from sanic.exceptions import BadRequest, ServerError, Unauthorized
from sanic.request import Request
from sanic_jwt.authentication import Authentication
from tortoise.exceptions import NoValuesFetched
from tortoise.expressions import Q
from tortoise.timezone import now as tortoise_timezone_now

from srf.config import settings

from .models import RefreshToken, User
from .schema import UserLoginSchema, UserSchemaReader

LOGIN_FAILED_MESSAGE = "Unable to log in with provided credentials."

__all__ = [
    "authenticate",
    "gen_user_access_token",
    "retrieve_refresh_token",
    "retrieve_user",
    "revoke_refresh_token",
    "store_refresh_token",
]


def coerce_timedelta(value, name: str) -> timedelta:
    """Normalize a JWT lifetime setting to a positive ``timedelta``.

    ``srf.config.settings`` defaults use ``timedelta``, but Sanic config
    values often come from environment variables as numbers or numeric
    strings. Accept all three forms so both spellings work.
    """
    if isinstance(value, timedelta):
        result = value
    elif isinstance(value, bool):
        raise ServerError(f"{name} must be a positive timedelta or number of seconds")
    elif isinstance(value, (int, float)):
        result = timedelta(seconds=value)
    elif isinstance(value, str):
        try:
            result = timedelta(seconds=float(value))
        except ValueError:
            raise ServerError(f"{name} must be a positive timedelta or number of seconds") from None
    else:
        raise ServerError(f"{name} must be a positive timedelta or number of seconds")

    if result <= timedelta(0):
        raise ServerError(f"{name} must be a positive timedelta or number of seconds")
    return result


async def _build_user_payload(user: User) -> dict:
    """JWT payload dict for sanic-jwt (login / refresh / me / token issue).

    Roles come from the prefetch cache when already fetched (zero queries);
    otherwise fall back to one lazy query.
    """
    try:
        roles = [role.name for role in user.roles]
    except NoValuesFetched:
        roles = [role.name for role in await user.roles.all()]
    return {
        "user_id": user.id,
        "username": user.username,
        "roles": roles,
    }


def _refresh_ttl() -> timedelta:
    ttl = getattr(settings, "JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
    normalized = coerce_timedelta(ttl, "JWT_REFRESH_TOKEN_EXPIRES")
    return timedelta(seconds=max(int(normalized.total_seconds()), 1))


def _refresh_token_digest(request: Request, refresh_token: str) -> str:
    """Create a keyed, purpose-separated digest for refresh-token storage."""
    secret = getattr(request.app.config, "SECRET_KEY", None)
    if secret is None or secret == "" or secret == b"":
        raise ServerError("SECRET_KEY must be a non-empty string or bytes")

    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    elif not isinstance(secret, bytes):
        raise ServerError("SECRET_KEY must be a non-empty string or bytes")

    key = hmac.new(secret, b"srf:refresh-token-storage:v1", hashlib.sha256).digest()
    return hmac.new(key, refresh_token.encode("utf-8"), hashlib.sha256).hexdigest()


async def authenticate(request: Request, *args, **kwargs) -> dict:
    """Validate credentials and return JWT payload (user_id, username, roles). Used by sanic_jwt."""
    if request.json is None:
        raise BadRequest("Request body is required")
    try:
        sch_user = UserLoginSchema.model_validate(request.json)
    except (ValidationError, TypeError, ValueError):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    if sch_user.is_email:
        query = Q(email=sch_user.account.lower())
    else:
        query = Q(username=sch_user.account)
    user = await User.filter(query).prefetch_related("roles").first()
    if user is None or not user.check_active():
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    if not user.verify_password(sch_user.password.get_secret_value()):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    await user.update_user_last_login()
    return await _build_user_payload(user)


async def retrieve_user(request, payload, *args, **kwargs) -> dict | None:
    """
    Single place to resolve an active User from JWT payload.

    - Loads ORM User once per request and stores it on ``request.ctx.user``
    - Returns a dict for sanic-jwt (refresh / me); ViewSets use ``request.ctx.user``
    """

    if not payload or (user_id := payload.get("user_id")) is None:
        return None

    # Reuse ORM user already attached earlier in this request
    ctx = getattr(request, "ctx", None) if request is not None else None
    ctx_user = getattr(ctx, "user", None) if ctx is not None else None
    if ctx_user is not None and getattr(ctx_user, "id", None) == user_id and ctx_user.check_active():
        return await _build_user_payload(ctx_user)

    user = await User.filter(id=user_id, is_active=True).prefetch_related("roles").first()
    if user is None:
        return None
    if ctx is not None:
        ctx.user = user
    return await _build_user_payload(user)


async def gen_user_access_token(request: Request, user_db: User) -> dict:
    """
    Serialize user and attach a JWT access_token from app.ctx.auth.

    Args:
        request: The Sanic request object.
        user_db: The ORM User instance to serialize.

    Raises:
        ServerError: If JWT is not configured on the application.
    """

    auth: Authentication | None = getattr(request.app.ctx, "auth", None)
    if auth is None:
        raise ServerError("JWT is not configured; call register_jwt_urls() first")

    user_payload = await _build_user_payload(user_db)
    access_token = await auth.generate_access_token(user=user_payload)
    # roles serialize as [] rather than None.
    await user_db.fetch_related("roles")
    data = UserSchemaReader.model_validate(user_db, from_attributes=True).model_dump(mode="json")
    data["access_token"] = access_token
    if auth.config.refresh_token_enabled():
        data["refresh_token"] = await auth.generate_refresh_token(request, user_payload)
    return data


async def store_refresh_token(user_id, refresh_token, request):
    """Persist a keyed digest of the refresh token; upsert the user's single row."""
    if not isinstance(refresh_token, str) or not refresh_token:
        raise ServerError("sanic-jwt generated an invalid refresh token")

    expires_at = tortoise_timezone_now() + _refresh_ttl()
    await RefreshToken.update_or_create(
        user_id=user_id,
        defaults={"token": _refresh_token_digest(request, refresh_token), "expires_at": expires_at},
    )


async def retrieve_refresh_token(request, user_id):
    """Verify the presented refresh token and return it for sanic-jwt, or None."""

    auth: Authentication | None = getattr(request.app.ctx, "auth", None)
    if auth is None:
        raise ServerError("JWT is not configured; call register_jwt_urls() first")

    try:
        presented_token = await auth.retrieve_refresh_token_from_request(request)
    except AttributeError:
        # sanic-jwt 1.8.0 dereferences request.json when a refresh request has a
        # header but no JSON body; treat that malformed request as unauthenticated.
        return None
    if not presented_token or not isinstance(presented_token, str):
        return None

    presented_digest = _refresh_token_digest(request, presented_token)
    row = await RefreshToken.filter(user_id=user_id, expires_at__gt=tortoise_timezone_now()).first()
    if row is None or not hmac.compare_digest(presented_digest, row.token):
        return None

    return presented_token


async def revoke_refresh_token(request, user_id) -> None:
    """Delete all refresh tokens for the user (logout)."""
    await RefreshToken.filter(user_id=user_id).delete()
