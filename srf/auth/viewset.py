from typing import ClassVar

import jwt
from jwt.exceptions import InvalidTokenError
from redis.asyncio import Redis
from sanic import Request, Sanic
from sanic.exceptions import BadRequest, Forbidden, ServerError
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
from .models import RefreshToken


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


async def register(request: Request):
    """Register a new user after verifying email code; return user data and access token."""
    if not request.json:
        raise BadRequest("JSON request body is required.")
    sch_email_verification = EmailCodeVerifySchema.model_validate(request.json, extra="ignore")

    # Fetch and validate verification code from Redis
    redis: Redis = request.app.ctx.redis
    email_cache_key = f"{settings.EMAIL_CODE_REDIS}_{sch_email_verification.email.lower()}"
    stored_code = await redis.get(email_cache_key)

    # Verify the code, then delete it whether it was missing or incorrect.
    if stored_code is None or (stored_code.decode() if isinstance(stored_code, bytes) else str(stored_code)) != sch_email_verification.confirmations:
        await redis.delete(email_cache_key)
        return HTTPResponse("The verification code is invalid or has expired.", status=HTTPStatus.HTTP_400_BAD_REQUEST)
    await redis.delete(email_cache_key)

    # Validate schema; unwrap SecretStr here, create_user only accepts plaintext str.
    sch_user_in = schema.UserSchemaWriter.model_validate(request.json, extra="ignore")
    user_data = sch_user_in.model_dump(
        exclude_unset=True,
        exclude_none=True,
        exclude={"password", "password_confirm"},
    )
    user_data["password"] = schema.unwrap_secret(sch_user_in.password)
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
        raise BadRequest("JSON request body is required.")
    email = EmailValidator.model_validate(request.json, extra="ignore").email
    email_cache_key = f"{settings.EMAIL_CODE_REDIS}_{email.lower()}"

    # Check cache
    redis: Redis = request.app.ctx.redis
    if await redis.get(email_cache_key) is not None:
        return HTTPResponse("Verification email already sent. Please check your email.", status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)
    code = generate_code(5)
    created = await redis.set(email_cache_key, code, ex=settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL, nx=True)
    if not created:
        return HTTPResponse("Verification email already sent. Please check your email.", status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)

    # Send verification code to email in background
    async def _send_and_cleanup(email, code):
        ok = await send_verify_code(email, code)
        if not ok:
            await redis.delete(email_cache_key)
        return ok

    # asyncio.create_task(_send_and_cleanup(email, code))  # no need to use asyncio, await is enough

    if await _send_and_cleanup(email, code):
        return HTTPResponse("Verification email sent. Please check your email.")
    return HTTPResponse("Failed to send verification email. Please try again later.", status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)


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
