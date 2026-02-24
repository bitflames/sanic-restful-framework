from sanic.exceptions import BadRequest, NotFound
from sanic.request import Request

from .models import User
from .schema import UserLoginSchema


async def authenticate(request: Request, *args, **kwargs):
    """Validate credentials and return JWT payload (user_id, username, role). Used by sanic_jwt."""
    if request.json is None:
        raise BadRequest("Request body is required")
    sch_user = UserLoginSchema.model_validate(request.json, by_alias=True)  # TODO, form login

    user = await User.filter(email=sch_user.email).select_related("role").first()
    if user is None or not await check_active(user):
        raise NotFound("User not found.")

    if not user.verify_password(sch_user.password):
        raise BadRequest("Login information is incorrect. Login failed")

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
