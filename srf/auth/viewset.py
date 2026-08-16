from typing import ClassVar

from redis.asyncio import Redis
from sanic import Request, Sanic
from sanic.constants import SAFE_HTTP_METHODS
from sanic.exceptions import BadRequest, ServerError
from sanic.response import HTTPResponse, JSONResponse
from sanic_jwt import Initialize
from sanic_jwt.authentication import Authentication
from tortoise.queryset import QuerySet

from srf.auth import models, schema
from srf.config import settings
from srf.permission.permission import IsAuthenticated
from srf.tools.email import EmailCodeVerifySchema, EmailValidator, send_verify_code
from srf.tools.utils import generate_code
from srf.views import BaseViewSet, action
from srf.views.http_status import HTTPStatus

from .auth import (
    authenticate,
    gen_user_access_token,
    retrieve_refresh_token,
    retrieve_user,
    revoke_refresh_token,
    store_refresh_token,
    update_user_last_login,
)
from .schema import ChangePasswordSchema, UserSchemaWriter, unwrap_secret


def setup_auth(app: Sanic, *args, **kwargs) -> Initialize:
    """
    Setup authentication for the application.

    Args:
        app: The Sanic application instance.
        url_prefix: The URL prefix for the authentication endpoints.
        secret: The secret key for the authentication.
        login_path: The path to the login endpoint.
    """

    secret = kwargs.pop("secret", None)
    if secret is None:
        raise ServerError("secret is required")
    url_prefix = kwargs.pop("url_prefix", "/api/auth")

    path_to_authenticate = kwargs.pop("login_path", getattr(settings, "LOGIN_PATH", "login"))
    # TODO: sanic_jwt does not read app.config from Configuration; SRF will replace sanic_jwt in the future

    return Initialize(
        app,
        authenticate=authenticate,
        path_to_authenticate=path_to_authenticate,
        retrieve_user=retrieve_user,
        secret=secret,
        url_prefix=url_prefix,
        refresh_token_enabled=True,
        store_refresh_token=store_refresh_token,
        retrieve_refresh_token=retrieve_refresh_token,
        expiration_delta=int(settings.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        **kwargs,
    )


async def logout(request: Request):
    auth: Authentication | None = getattr(request.app.ctx, "auth", None)
    if auth is None:
        raise ServerError("JWT is not configured; call register_auth_urls() first")
    try:
        payload = await auth.extract_payload(request, verify=False)
    except Exception:  # noqa: BLE001
        return HTTPResponse(status=HTTPStatus.HTTP_200_OK)
    if isinstance(payload, dict):
        user_id = payload.get("user_id")
        if user_id is not None:
            await revoke_refresh_token(request, user_id)
    return HTTPResponse(status=HTTPStatus.HTTP_200_OK)


async def register(request: Request):
    """Register a new user after verifying email code; return user data and access token."""
    if not request.json:
        raise BadRequest("Request body is required")
    sch_email_verification = EmailCodeVerifySchema.model_validate(request.json, extra="ignore")

    # Fetch and validate verification code from Redis
    redis: Redis = request.app.ctx.redis
    email_cache_key = f"{settings.EMAIL_CODE_REDIS}_{sch_email_verification.email}"
    stored_code = await redis.get(email_cache_key)

    # Verify code and delete it， whther code is None or incorrect
    if stored_code is None or (stored_code.decode() if isinstance(stored_code, bytes) else str(stored_code)) != sch_email_verification.confirmations:
        await redis.delete(email_cache_key)
        return HTTPResponse("The verification code is incorrect or timeout, please retry!", status=HTTPStatus.HTTP_400_BAD_REQUEST)
    await redis.delete(email_cache_key)

    # Validate schema; unwrap SecretStr here, create_user only accepts plaintext str.
    sch_user_in = UserSchemaWriter.model_validate(request.json, by_alias=True, extra="ignore")
    user_data = sch_user_in.model_dump(
        exclude_unset=True,
        exclude_none=True,
        exclude={"password", "password_confirm"},
    )
    user_data["password"] = unwrap_secret(sch_user_in.password)
    user_db = await models.User.create_user(user_data)
    await update_user_last_login(user_db)
    user_return_data = await gen_user_access_token(request, user_db)
    return JSONResponse(user_return_data, status=HTTPStatus.HTTP_200_OK)


async def verify_email(request: Request):
    """Send verification code email and store it in cache. TODO: verify mailbox validity."""
    return await send_email_with_redis_code(request)


async def send_email_with_redis_code(request: Request):
    """Send verification code to email and store in cache. TODO: validate with Schema."""
    if not request.json:
        raise BadRequest("Request body is required")
    email = EmailValidator.model_validate(request.json, extra="ignore").email
    code = generate_code(5)
    email_cache_key = f"{settings.EMAIL_CODE_REDIS}_{email}"

    # Check cache
    redis: Redis = request.app.ctx.redis
    if await redis.get(email_cache_key) is not None:
        return HTTPResponse("Email has been sent, please check your email", status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)
    await redis.set(email_cache_key, code, ex=settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL, nx=True)

    # Send verification code to email in background
    async def _send_and_cleanup(email, code):
        ok = await send_verify_code(email, code)
        if not ok:
            await redis.delete(email_cache_key)
        return ok

    # asyncio.create_task(_send_and_cleanup(email, code))  # no need to use asyncio, await is enough

    if await _send_and_cleanup(email, code):
        return HTTPResponse("Email has been sent, please check your email")
    return HTTPResponse("Email send failed, please try again", status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields: ClassVar[list[str]] = [
        "name",
        "is_active",
        "id",
    ]
    filter_fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "name": "name",
        "is_active": "is_active",
    }

    @property
    def queryset(self) -> QuerySet:
        return models.User.all()

    def get_schema(self, request: Request, *args, is_safe=False, **kwargs):
        if request.method.lower() in SAFE_HTTP_METHODS or is_safe is True:
            return schema.UserSchemaReader
        if request.method.upper() in ("PUT", "PATCH"):
            return schema.UserSchemaUpdate
        return schema.UserSchemaWriter

    @action(detail=False, url_name="self", url_path="self")
    async def get_self(self, request: Request):
        user_json = self.get_schema(request).model_validate(request.ctx.user).model_dump(mode="json", by_alias=True)
        return JSONResponse(user_json)

    @action(detail=False, methods=["post"], url_name="change-password", url_path="change-password")
    async def change_password(self, request: Request):
        """Change password for the authenticated user (SHA-256 + bcrypt)."""
        if not request.json:
            raise BadRequest("Request body is required")
        sch = ChangePasswordSchema.model_validate(request.json, by_alias=True)
        user: models.User = request.ctx.user
        old_password = unwrap_secret(sch.old_password)
        if not old_password or not user.verify_password(old_password):
            raise BadRequest("Old password is incorrect")
        new_password = unwrap_secret(sch.password)
        assert new_password is not None  # validated by ChangePasswordSchema
        user.password = models.User.hash_password(new_password)
        await user.save()
        return HTTPResponse(status=HTTPStatus.HTTP_200_OK)

    async def perform_create(self, sch_model: UserSchemaWriter):
        """Create ORM user from Pydantic schema. TODO: verify email availability."""
        data = sch_model.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude={"password", "password_confirm"},
        )
        data["password"] = unwrap_secret(sch_model.password)
        return await models.User.create_user(data)
