from datetime import timedelta

from pydantic import ValidationError
from sanic.exceptions import BadRequest, ServerError, Unauthorized
from sanic.request import Request
from sanic_jwt.authentication import Authentication
from tortoise.expressions import Q

from srf.config import settings

from .models import RefreshToken, User
from .schema import UserLoginSchema, UserSchemaReader, utc_now

LOGIN_FAILED_MESSAGE = "Unable to log in with provided credentials."


def build_user_payload(user: User) -> dict:
    """JWT payload dict for sanic-jwt (login / refresh / me / token issue)."""
    return {
        "user_id": user.id,
        "username": user.name,
        "role": user.role.name if user.role else None,
    }


async def update_user_last_login(user: User) -> None:
    """Record successful login time without rewriting unrelated columns."""
    user.last_login = utc_now()
    await user.save(update_fields=["last_login"])


async def authenticate(request: Request, *args, **kwargs) -> dict:
    """Validate credentials and return JWT payload (user_id, username, role). Used by sanic_jwt."""
    if request.json is None:
        raise BadRequest("Request body is required")
    try:
        sch_user = UserLoginSchema.model_validate(request.json, by_alias=True)  # TODO, form login
    except (ValidationError, TypeError, ValueError):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    if sch_user.email:
        query = Q(email=sch_user.email)
        if sch_user.username:
            query |= Q(name=sch_user.username)
    else:
        query = Q(name=sch_user.username)
    user = await User.filter(query).select_related("role").first()
    if user is None or not check_active(user):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    if not user.verify_password(sch_user.password.get_secret_value()):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    await update_user_last_login(user)
    return build_user_payload(user)


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
    if ctx_user is not None and getattr(ctx_user, "id", None) == user_id and check_active(ctx_user):
        return build_user_payload(ctx_user)

    user = await User.filter(id=user_id).select_related("role").first()
    if user is None or not check_active(user):
        return None
    if ctx is not None:
        ctx.user = user
    return build_user_payload(user)


def check_active(user: User):
    return getattr(user, "is_active", True)


async def gen_user_access_token(request: Request, user_db: User) -> dict:
    """Serialize user and attach a JWT access_token from app.ctx.auth."""
    auth: Authentication | None = getattr(request.app.ctx, "auth", None)
    if auth is None:
        raise ServerError("JWT is not configured; call register_auth_urls() first")

    user_payload = build_user_payload(user_db)
    access_token = await auth.generate_access_token(user=user_payload)
    data = UserSchemaReader.model_validate(user_db, from_attributes=True).model_dump(
        by_alias=True,
        mode="json",
    )
    data["access_token"] = access_token
    if auth.config.refresh_token_enabled():
        data["refresh_token"] = await auth.generate_refresh_token(request, user_payload)
    return data


def _refresh_ttl() -> timedelta:
    ttl = getattr(settings, "JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
    if isinstance(ttl, timedelta):
        return ttl if ttl.total_seconds() > 0 else timedelta(seconds=1)
    return timedelta(seconds=max(int(ttl), 1))


async def store_refresh_token(user_id, refresh_token, request):
    """Persist refresh token in DB; upsert the single row for this user."""
    expires_at = utc_now() + _refresh_ttl()
    await RefreshToken.update_or_create(
        user_id=user_id,
        defaults={"token": refresh_token, "expires_at": expires_at},
    )


async def retrieve_refresh_token(request, user_id):
    """Return the active (non-expired) refresh token for user, or None."""
    row = await RefreshToken.filter(user_id=user_id, expires_at__gt=utc_now()).first()
    return row.token if row else None


async def revoke_refresh_token(request, user_id) -> None:
    """Delete all refresh tokens for the user (logout)."""
    await RefreshToken.filter(user_id=user_id).delete()
