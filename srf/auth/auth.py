from pydantic import ValidationError
from sanic.exceptions import BadRequest, Unauthorized
from sanic.request import Request
from tortoise.expressions import Q

from .models import User
from .schema import UserLoginSchema

LOGIN_FAILED_MESSAGE = "Unable to log in with provided credentials."


async def authenticate(request: Request, *args, **kwargs):
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
    if user is None or not await check_active(user):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    if not user.verify_password(sch_user.password):
        raise Unauthorized(LOGIN_FAILED_MESSAGE)

    role_name = user.role.name if user.role else None
    return {"user_id": user.id, "username": user.name, "role": role_name}


async def retrieve_user(payload, *args, **kwargs):
    if payload:
        user_id = payload.get("user_id", None)
        if user_id is not None:
            user = await User.filter(id=user_id).select_related("role").first()
            return user
    return None


async def check_active(user: User):
    return getattr(user, "is_active", True)


async def store_user(request, user_id, *args, **kwargs):
    user = await retrieve_user({"user_id": user_id})
    request.ctx.user = user
