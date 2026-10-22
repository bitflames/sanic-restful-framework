from typing import ClassVar

import jwt
from jwt.exceptions import InvalidTokenError
from redis.asyncio import Redis
from sanic import Request, Sanic
from sanic.exceptions import BadRequest, Forbidden, HTTPException, InternalServerError, ServerError
from sanic.response import HTTPResponse, JSONResponse
from sanic_jwt import Initialize
from sanic_jwt.authentication import Authentication
from sanic_jwt.exceptions import MissingAuthorizationCookie, MissingAuthorizationHeader, MissingAuthorizationQueryArg
from tortoise.exceptions import IntegrityError
from tortoise.queryset import QuerySet
from tortoise.transactions import in_transaction

from srf.auth import models, schema
from srf.config import settings
from srf.exceptions import TargetObjectAlreadyExist
from srf.permission.permission import IsAuthenticated
from srf.tools.email import EmailCodeVerifySchema, EmailValidator, send_template_email
from srf.tools.utils import generate_code
from srf.views import BaseViewSet, action
from srf.views.decorators import validate_request
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
from .models import RefreshToken

__all__ = [
    "UserViewSet",
    "logout",
    "register",
    "setup_auth",
    "verify_email",
]


def setup_auth(app: Sanic, *args, **kwargs) -> Initialize:
    """
    Setup authentication for the application.

    Args:
        app: The Sanic application instance.
        url_prefix: The URL prefix for the authentication endpoints.
        login_path: The path to the login endpoint.
    """

    jwt_secret = app.config.get("JWT_SECRET")
    if not isinstance(jwt_secret, (str, bytes)) or not jwt_secret:
        raise ServerError("app.config.JWT_SECRET must be a non-empty string or bytes")
    refresh_token_secret = app.config.get("SECRET_KEY")
    if not isinstance(refresh_token_secret, (str, bytes)) or not refresh_token_secret:
        raise ServerError("app.config.SECRET_KEY must be a non-empty string or bytes")

    url_prefix = kwargs.pop("url_prefix", "/api/auth")

    # TODO: sanic_jwt does not read app.config from Configuration; SRF will replace sanic_jwt in the future

    return Initialize(
        app,
        authenticate=authenticate,
        retrieve_user=retrieve_user,
        secret=jwt_secret,
        url_prefix=url_prefix,
        refresh_token_enabled=True,
        store_refresh_token=store_refresh_token,
        retrieve_refresh_token=retrieve_refresh_token,
        expiration_delta=int(settings.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        **kwargs,
    )


def _decode_access_token(auth: Authentication, token: str, secret) -> dict:
    """Verify the access-token signature and ignore expiry so logout can still revoke refresh."""
    kwargs = {}
    if "claim_aud" in auth.config:
        kwargs["audience"] = auth.config.claim_aud()
    if "claim_iss" in auth.config:
        kwargs["issuer"] = auth.config.claim_iss()
    return jwt.decode(
        token,
        secret,
        algorithms=[auth._get_algorithm()],
        options={"verify_signature": True, "verify_exp": False},
        **kwargs,
    )


async def logout(request: Request):
    auth: Authentication | None = getattr(request.app.ctx, "auth", None)
    if auth is None:
        raise ServerError("JWT is not configured; call register_auth_urls() first")
    try:
        token = auth._get_token(request)
        secret = await auth._get_secret(token)
        payload = _decode_access_token(auth, token, secret)
    except (InvalidTokenError, MissingAuthorizationHeader, MissingAuthorizationCookie, MissingAuthorizationQueryArg):
        return HTTPResponse(status=HTTPStatus.HTTP_200_OK)
    user_id = payload.get("user_id")
    if user_id is not None:
        await revoke_refresh_token(request, user_id)
    return HTTPResponse(status=HTTPStatus.HTTP_200_OK)


VERIFY_EMAIL_CODE_LUA = """
local stored_code = redis.call('GET', KEYS[1])

-- Verification code is missing or expired
if not stored_code then
    return 0
end

-- Verification succeeded; consume the code
if stored_code == ARGV[1] then
    redis.call('DEL', KEYS[1], KEYS[2])
    return 1
end

-- Increment failed verification attempts
local tried_times = redis.call('INCR', KEYS[2])

-- Set expiration on the first attempt
if tried_times == 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[3])
end

-- Invalidate the verification code after too many failed attempts
if tried_times >= tonumber(ARGV[2]) then
    redis.call('DEL', KEYS[1], KEYS[2])
    return 3
end

return 2
"""


@validate_request(show_errors=True)
async def register(request: Request):
    """Register a new user after verifying email code."""
    if not request.json:
        raise BadRequest("JSON request body is required.")

    sch_email_verification = EmailCodeVerifySchema.model_validate(request.json, extra="ignore")
    sch_user_in = schema.UserSchemaWriter.model_validate(request.json, extra="ignore")

    redis: Redis = request.app.ctx.redis
    email = sch_email_verification.email.lower()

    email_cache_key = settings.USER_REGISTER_EMAIL_CODE.format(email=email)
    times_key = settings.USER_REGISTER_EMAIL_CODE_TIMES.format(email=email)

    user_data = sch_user_in.model_dump(exclude_unset=True, exclude_none=True, exclude={"password", "password_confirm"})
    user_data["password"] = schema.unwrap_secret(sch_user_in.password)

    result = await redis.eval(
        VERIFY_EMAIL_CODE_LUA,
        2,
        email_cache_key,
        times_key,
        sch_email_verification.confirmations,
        settings.USER_REGISTER_EMAIL_CODE_TIMES_LIMIT,
        settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL,
    )

    if result == 0:
        raise BadRequest("The verification code is invalid or has expired.")
    if result == 2:
        raise BadRequest("The verification code is invalid.")
    if result == 3:
        raise HTTPException("Too many incorrect attempts. Please request a new verification code.", status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)
    if result != 1:
        raise InternalServerError("Unexpected email verification result.")

    user_db = await models.User.create_user(user_data)
    await update_user_last_login(user_db)

    user_return_data = await gen_user_access_token(request, user_db)
    return JSONResponse(user_return_data, status=HTTPStatus.HTTP_200_OK)


CREATE_EMAIL_CODE_LUA = """
local created = redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2], 'NX')

if not created then
    return 0
end

redis.call('DEL', KEYS[2])
return 1
"""


DELETE_EMAIL_CODE_IF_MATCH_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end

return 0
"""


async def _send_email_with_redis_code(request: Request):
    """Send a verification code email and store the code in Redis."""
    if not request.json:
        raise BadRequest("JSON request body is required.")

    email = EmailValidator.model_validate(request.json, extra="ignore").email.lower()

    redis: Redis = request.app.ctx.redis
    email_cache_key = settings.USER_REGISTER_EMAIL_CODE.format(email=email)
    times_key = settings.USER_REGISTER_EMAIL_CODE_TIMES.format(email=email)

    code = generate_code(6)

    # Atomically create the verification code and reset the failed attempt counter.
    created = await redis.eval(
        CREATE_EMAIL_CODE_LUA,
        2,
        email_cache_key,
        times_key,
        code,
        settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL,
    )

    if not created:
        return HTTPResponse("Verification email already sent. Please check your email.", status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)

    try:
        ok = await send_template_email(
            to_email=email,
            subject="Registration Verification Code",
            template_name="email_code.html",
            context={"code": code, "duration": f"{settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL}s"},
        )
    except Exception as exc:
        # Delete the verification code only if it still matches the code generated by this request.
        await redis.eval(DELETE_EMAIL_CODE_IF_MATCH_LUA, 1, email_cache_key, code)
        raise ServerError("Failed to send verification email. Please try again later.") from exc

    if not ok:
        # Delete the verification code only if it still matches the code generated by this request.
        await redis.eval(DELETE_EMAIL_CODE_IF_MATCH_LUA, 1, email_cache_key, code)
        raise ServerError("Failed to send verification email. Please try again later.")

    return HTTPResponse("Verification email sent. Please check your email.")


@validate_request(show_errors=True)
async def verify_email(request: Request):
    """Send verification code email and store it in cache. TODO: verify mailbox validity."""
    return await _send_email_with_redis_code(request)


class UserViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields: ClassVar[list[str]] = ["username", "email"]
    filter_fields: ClassVar[list[str]] = search_fields
    ordering_fields: ClassVar[list[str]] = ["id", "username", "is_active", "create_time", "update_time"]

    async def get_object(self, pk):
        """Get user object by ID. Only superuser can get other user's information."""
        pk = self.normalize_pk(pk)
        if self.request.ctx.user.is_superuser:
            return await super().get_object(pk)
        if pk != self.request.ctx.user.id:
            raise Forbidden(message="Forbidden")
        return self.request.ctx.user

    @property
    def queryset(self) -> QuerySet:
        return models.User.filter(id=self.request.ctx.user.id) if not self.request.ctx.user.is_superuser else models.User.all()

    def get_schema(self):
        action = getattr(self, "action", None)
        if action in ("list", "retrieve", "get_self"):
            return schema.UserSchemaReader
        if action == "create":
            return schema.UserSchemaWriter
        if action == "update":
            return schema.UserSchemaUpdate
        return schema.UserSchemaReader

    @action(detail=False, url_name="self", url_path="self")
    async def get_self(self, request: Request):
        user_json = self.get_schema().model_validate(request.ctx.user).model_dump(mode="json")
        return JSONResponse(user_json)

    @action(detail=False, methods=["post"], url_name="change-password", url_path="change-password")
    async def change_password(self, request: Request):
        """Change password for the authenticated user (SHA-256 + bcrypt)."""
        if not request.json:
            raise BadRequest("JSON request body is required.")
        sch = schema.ChangePasswordSchema.model_validate(request.json)
        user: models.User = request.ctx.user
        old_password = schema.unwrap_secret(sch.old_password)
        if not old_password or not user.verify_password(old_password):
            raise BadRequest("The old password is incorrect.")
        new_password = schema.unwrap_secret(sch.password)
        assert new_password is not None  # validated by ChangePasswordSchema
        user.password = models.User.hash_password(new_password)

        # update and delete refresh token in a transaction
        async with in_transaction() as conn:
            await user.save(using_db=conn)
            await RefreshToken.filter(user=user).using_db(conn).delete()
        return HTTPResponse(status=HTTPStatus.HTTP_200_OK)

    async def create(self, request: Request, *args, **kwargs) -> HTTPResponse:
        """Create a user by superuser. The write schema validates input; the read schema serializes the new row."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)
        if not self.request.ctx.user.is_superuser:
            raise Forbidden(message="Forbidden")
        sch_model_in = schema.UserSchemaWriter.model_validate(request.json, strict=True)
        orm_model = await self.perform_create(sch_model_in)
        sch_model_out = schema.UserSchemaReader.model_validate(orm_model, from_attributes=True)
        return JSONResponse(sch_model_out.model_dump(mode="json"), status=HTTPStatus.HTTP_201_CREATED)

    async def perform_create(self, sch_model: schema.UserSchemaWriter):
        """Create ORM user from Pydantic schema. TODO: verify email availability.
        Only superuser can create user.  # TODO , is_superuser, is_active, roles
        """
        if not self.request.ctx.user.is_superuser:
            raise Forbidden(message="Forbidden")
        user_data = sch_model.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude={"password", "password_confirm", "is_superuser", "is_active"},
        )
        user_data["password"] = schema.unwrap_secret(sch_model.password)
        return await models.User.create_user(user_data)

    async def update(self, request: Request, pk, *args, **kwargs) -> JSONResponse:
        """Update a user. The update schema validates input; the read schema serializes the row."""
        if request.json is None:
            return HTTPResponse(status=HTTPStatus.HTTP_400_BAD_REQUEST)
        sch_model_in = schema.UserSchemaUpdate.model_validate(request.json, strict=True)
        orm_model = await self.get_object(pk)
        orm_model = await self.perform_update(sch_model_in, orm_model)
        sch_model_out = schema.UserSchemaReader.model_validate(orm_model, from_attributes=True)
        return JSONResponse(sch_model_out.model_dump(mode="json"))

    async def perform_update(self, sch_model: schema.UserSchemaUpdate, orm_model: models.User) -> models.User:
        """
        sch_model: instance of BaseModel
        orm_model: instance of TorModel
        """
        try:
            return await super().perform_update(sch_model, orm_model)
        except IntegrityError:
            raise TargetObjectAlreadyExist(message="data conflict")
