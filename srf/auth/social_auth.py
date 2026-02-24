import aiohttp
from sanic import Request
from sanic.exceptions import BadRequest, NotFound
from sanic.response import JSONResponse
from sanic.response import redirect as RedirectResponse
from sanic.response import text as TextResponse
from sanic_jwt.authentication import Authentication

from srf.views.http_status import HTTPStatus

from . import models
from .schema import UserSchemaReader


async def github_login(request: Request):
    github_config = request.app.config.SOCIAL_CONFIG['github']
    url = (
        f"{github_config['AUTHORIZE']}"
        f"?client_id={github_config['CLIENT_ID']}"
        f"&redirect_uri={github_config['REDIRECT_URI']}"
        "&scope=user:email"
        "&state=random_state_string"
    )
    return JSONResponse({"auth_url": url}, status=HTTPStatus.HTTP_200_OK)


async def github_callback(request: Request):
    github_config = request.app.config.SOCIAL_CONFIG['github']
    code = request.args.get("code")
    if code is None:
        raise BadRequest("Missing authorization code")

    # 1. exchange access_token by oauth
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": github_config['CLIENT_ID'],
            "client_secret": github_config['CLIENT_SECRET'],
            "code": code,
            "redirect_uri": github_config['REDIRECT_URI'],
        }
        token_resp = await session.post(
            github_config['ACCESS_TOKEN'],
            headers={"Accept": "application/json"},
            data=data,
        )
        token_resp.raise_for_status()
        token_data = await token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            return TextResponse("GitHub login failed! ", status=HTTPStatus.HTTP_400_BAD_REQUEST)

        # 2. get user info by access_token
        user_resp = await session.get(
            github_config['GITHUB_USER'],
            headers={"Authorization": f"token {access_token}"},
        )
        user = await user_resp.json()

        email_resp = await session.get(
            github_config['GITHUB_USER_EMAIL'],
            headers={"Authorization": f"token {access_token}"},
        )
        emails = await email_resp.json()
        primary_email = next(e["email"] for e in emails if e["primary"])

        # user_db, created = await models.User.get_or_create(email=primary_email, name=user['name'], role=await models.Role.filter(name='user').first())
        try:
            user_db, created = await models.User.get_or_create(
                email=primary_email,
                name=user['name'],
                role=await models.Role.filter(name='user').first(),
            )
        except Exception as e:
            return TextResponse(
                f"Error creating user: {str(e)}",
                status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        access_code = f"{request.app.config.FORMATTER.SOCIAL_LOGIN_REDIS_EX_CODE}_{user_db.id}"
        resp = await request.app.ctx.redis.set(access_code, user_db.id, ex=300)

        return RedirectResponse(f'{github_config["OAUTHCALLBACK"]}?code={access_code}')


async def login_by_code(request: Request):
    code = request.args.get("code")
    if code is None:
        raise BadRequest("Missing authorization code")

    user_id = await request.app.ctx.redis.get(code)
    if user_id is None:
        raise NotFound("Invalid or expired authorization code")
    if isinstance(user_id, bytes):
        user_id = int(user_id.decode())
    else:
        user_id = int(user_id)

    user_db = await models.User.filter(pk=user_id).select_related("role").first()
    if user_db is None:
        raise NotFound("User not found")

    aut = Authentication(request.app, request.app.config.JWT.config)
    user_db_data = UserSchemaReader.model_validate(user_db).model_dump(by_alias=True, mode='json')
    role_name = user_db.role.name if user_db.role else None
    access_token = await aut.generate_access_token(
        user={
            "user_id": user_db.id,
            "username": user_db.name,
            "role": role_name,
        }
    )
    user_db_data['access_token'] = access_token

    return JSONResponse(user_db_data)
