import asyncio
from typing import Dict

from redis.asyncio import Redis
from sanic import Request, Sanic
from sanic.constants import SAFE_HTTP_METHODS
from sanic.exceptions import BadRequest
from sanic.response import HTTPResponse, JSONResponse
from sanic_jwt import Initialize
from sanic_jwt.authentication import Authentication
from tortoise.queryset import QuerySet

from srf.auth import models, schema
from srf.config import srfconfig
from srf.permission.permission import IsAuthenticated
from srf.tools.email import EmailValidator, VerifyEmailRequest, send_verify_code
from srf.tools.utils import generate_code
from srf.views import BaseViewSet, action
from srf.views.http_status import HTTPStatus

from .auth import authenticate, retrieve_user
from .schema import UserSchemaReader, UserSchemaWriter


def setup_auth(app: Sanic, *args, **kwargs) -> Initialize:
    url_prefix = kwargs.pop("url_prefix", "/api/auth")
    secret = kwargs.pop("secret", srfconfig.JWT_SECRET)
    path_to_authenticate = kwargs.pop(
        "login_path", getattr(srfconfig, "LOGIN_PATH", "login")
    )  # TODO: sanic_jwt does not read app.config from Configuration; next SRF version may replace sanic_jwt
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
    req_data = request.json
    if req_data is None:
        return HTTPResponse(
            "Request body is required",
            status=HTTPStatus.HTTP_400_BAD_REQUEST,
        )
    cf_info = VerifyEmailRequest.model_validate(req_data, extra="ignore")

    # Fetch and validate verification code from Redis
    email_code_register = f"{request.app.config.FORMATTER.EMAIL_CODE_REDIS}_{req_data.get('email')}"
    redis: Redis = request.app.ctx.redis
    stored_code = await redis.get(email_code_register)
    if stored_code is None:
        return HTTPResponse(
            "The verification code is incorrect or expired, please retry!",
            status=HTTPStatus.HTTP_400_BAD_REQUEST,
        )
    stored_code = int(stored_code.decode() if isinstance(stored_code, bytes) else stored_code)
    if stored_code != cf_info.confirmations:
        return HTTPResponse(
            "The verification code is incorrect or timeout, please retry!",
            status=HTTPStatus.HTTP_400_BAD_REQUEST,
        )
    await redis.delete(email_code_register)

    # Validate schema and create user (User.create hashes password and resolves role)
    sch = UserSchemaWriter.model_validate(req_data, by_alias=True, extra="ignore")
    user_db = await models.User.create(sch.model_dump(exclude_unset=True, exclude_none=True))
    user_db_data = UserSchemaReader.model_validate(user_db).model_dump(by_alias=True)

    # Generate JWT payload with serializable role (name string, not FK object)
    role_name = user_db.role.name if user_db.role else None
    aut = Authentication(request.app, srfconfig.JWT.config or request.app.ctx.JWT.config)
    access_token = await aut.generate_access_token(
        user={
            "user_id": user_db.id,
            "username": user_db.name,
            "role": role_name,
        }
    )
    user_db_data["access_token"] = access_token

    return JSONResponse(user_db_data, status=HTTPStatus.HTTP_200_OK)


async def verify_email(request: Request):
    """Send verification code email and store it in cache. TODO: verify mailbox validity."""
    if await send_email_with_redis_code(request):
        return HTTPResponse("Email has been sent, please check")
    return HTTPResponse("Email send failed", status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)


async def send_email_with_redis_code(request: Request, data: Dict = None):
    """Send verification code to email and store in cache. TODO: validate with Schema."""
    req_data: Dict = request.json if not data else data
    if req_data is None:
        raise BadRequest("Request body is required")
    EmailValidator.model_validate({"email": req_data.get("email")})
    code = generate_code(5)
    asyncio.create_task(send_verify_code(req_data.get("email"), code))

    email_code_register = f"{request.app.config.FORMATTER.EMAIL_CODE_REDIS}_{req_data.get('email')}"
    redis: Redis = request.app.ctx.redis
    await redis.set(email_code_register, code, ex=600)
    return True


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

    async def perform_create(self, sch_model, *args, **kwargs):
        """Create ORM user from Pydantic schema. TODO: verify email availability."""
        data = sch_model.model_dump(exclude_unset=True, exclude_none=True)
        return await models.User.create(data)
