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

from .auth import authenticate, retrieve_user
from .schema import UserSchemaReader, UserSchemaWriter


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
        retrieve_user=retrieve_user,
        path_to_authenticate=path_to_authenticate,
        secret=secret,
        url_prefix=url_prefix,
        **kwargs,
    )


async def logout(request: Request):
    # TODO token handle
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

    # Validate schema and create user (User.create hashes password and resolves role)
    sch_user_in = UserSchemaWriter.model_validate(request.json, by_alias=True, extra="ignore")
    user_db = await models.User.create(sch_user_in.model_dump(exclude_unset=True, exclude_none=True))
    user_db_data = UserSchemaReader.model_validate(user_db, from_attributes=True).model_dump(by_alias=True)

    # Generate JWT payload with serializable role (name string, not FK object)

    jwt = request.app.ctx.jwt
    if jwt is None:
        raise ServerError("JWT is not configured; call register_auth_urls() first")
    aut = Authentication(request.app, jwt.config)

    # Generate access token
    access_token = await aut.generate_access_token(
        user={
            "user_id": user_db.id,
            "username": user_db.name,
            "role": user_db.role.name if user_db.role else None,
        }
    )
    user_db_data["access_token"] = access_token
    return JSONResponse(user_db_data, status=HTTPStatus.HTTP_200_OK)


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
            return False
        return True

    # asyncio.create_task(_send_and_cleanup(email, code))  # no need to use asyncio, await is enough

    if await _send_and_cleanup(email, code):
        return HTTPResponse("Email has been sent, please check your email")
    return HTTPResponse("Email send failed, please try again", status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = [
        "name",
        "is_active",
        "id",
    ]
    filter_fields = {"id": "id", "name": "name", "is_active": "is_active"}

    @property
    def queryset(self, *args, **kwargs) -> QuerySet:
        return models.User.all()

    def get_schema(self, request: Request, *args, is_safe=False, **kwargs):
        if request.method.lower() in SAFE_HTTP_METHODS or is_safe is True:
            return schema.UserSchemaReader
        else:
            return schema.UserSchemaWriter

    @action(detail=False, url_name="self", url_path="self")
    async def get_self(self, request: Request):
        user_json = self.get_schema(request).model_validate(request.ctx.user).model_dump(mode="json", by_alias=True)
        return JSONResponse(user_json)

    async def perform_create(self, sch_model):
        """Create ORM user from Pydantic schema. TODO: verify email availability."""
        data = sch_model.model_dump(exclude_unset=True, exclude_none=True)
        return await models.User.create(data)
