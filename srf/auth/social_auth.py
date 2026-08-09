import hmac
import secrets
from functools import wraps
from typing import Any
from urllib.parse import urlencode, urlparse

import aiohttp
from sanic import Request
from sanic.exceptions import BadRequest, NotFound
from sanic.log import error_logger
from sanic.response import JSONResponse
from sanic.response import redirect as RedirectResponse
from sanic_jwt.authentication import Authentication

from srf.config import settings
from srf.tools.signing import sign_state, unsign_state
from srf.views.http_status import HTTPStatus

from . import models
from .schema import UserSchemaReader

DEFAULT_EXCHANGE_CODE_TTL = 300
DEFAULT_EXCHANGE_CODE_PREFIX = "social-login"
GITHUB_REQUEST_TIMEOUT = 10


def _state_secret(request: Request) -> str:
    """Return the dedicated OAuth state secret or the JWT secret as a fallback."""
    secret = getattr(request.app.config, "SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY", None) or getattr(request.app.config, "JWT_SECRET", None)
    if not secret:
        raise RuntimeError("SOCIAL_LOGIN_COOKIE_KEY_SECRET_KEY or JWT_SECRET must be configured")
    return secret


def _cookie_settings(request: Request) -> tuple[str, int, bool]:
    """Return the OAuth cookie name, lifetime, and secure flag."""
    cookie_name = getattr(request.app.config, "SOCIAL_LOGIN_COOKIE_KEY", settings.SOCIAL_LOGIN_COOKIE_KEY)
    max_age = int(getattr(request.app.config, "SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE", settings.SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE))
    secure = bool(getattr(request.app.config, "SOCIAL_LOGIN_COOKIE_SECURE", request.scheme == "https"))
    return cookie_name, max_age, secure


def _callback_cookie_path(github_config: dict) -> str:
    """Scope the state cookie to the configured backend callback path."""
    return urlparse(github_config["REDIRECT_URI"]).path or "/"


def _exchange_code_settings(request: Request) -> tuple[str, int]:
    prefix = getattr(request.app.config, "SOCIAL_LOGIN_REDIS_CODE_PREFIX", DEFAULT_EXCHANGE_CODE_PREFIX)
    ttl = int(getattr(request.app.config, "SOCIAL_LOGIN_CODE_MAX_AGE", DEFAULT_EXCHANGE_CODE_TTL))
    if not prefix or ttl <= 0:
        raise RuntimeError("Invalid social login exchange-code configuration")
    return prefix, ttl


def _exchange_code_key(request: Request, code: str) -> str:
    prefix, _ = _exchange_code_settings(request)
    return f"{prefix}:{code}"


def _delete_state_cookie(response, request: Request, github_config: dict) -> None:
    """Delete the state cookie."""

    cookie_name, _, _ = _cookie_settings(request)
    response.delete_cookie(cookie_name, path=_callback_cookie_path(github_config))


async def _github_request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    **kwargs,
) -> dict[str, Any] | list[Any]:
    """Send a GitHub API request, validate its status, and decode its JSON body."""
    async with session.request(method, url, **kwargs) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)
        if not isinstance(data, (dict, list)):
            raise ValueError("GitHub returned an unexpected JSON response")
        return data


def _verified_email(emails: list[dict]) -> str | None:
    """Prefer GitHub's verified primary email, then any verified email."""
    verified = [email for email in emails if email.get("verified") and email.get("email")]
    primary = next((email for email in verified if email.get("primary")), None)
    selected = primary or (verified[0] if verified else None)
    return selected["email"] if selected else None


async def _store_exchange_code(request: Request, user_id: int) -> str:
    """Create a short-lived code that the frontend can exchange for a JWT.

    The code, rather than the JWT, is placed in the redirect URL. Redis maps
    the code to the authenticated user ID until ``login_by_code`` consumes it.
    """
    _, ttl = _exchange_code_settings(request)

    for _ in range(3):
        code = secrets.token_urlsafe(32)
        created = await request.app.ctx.redis.set(
            _exchange_code_key(request, code),
            user_id,
            ex=ttl,
            nx=True,
        )
        if created:
            return code

    raise RuntimeError("Could not allocate a unique social login exchange code")


async def github_login(request: Request):
    """Redirect the user to the GitHub login page."""

    # get the github configurations from the request
    github_config = request.app.config.SOCIAL_CONFIG["github"]
    # generate a random state
    state = secrets.token_urlsafe(32)
    # get the cookie settings from the request
    cookie_name, max_age, secure = _cookie_settings(request)
    # sign the state
    signed_state = sign_state(state, _state_secret(request))
    # encode the query parameters
    query = urlencode(
        {
            "client_id": github_config["CLIENT_ID"],
            "redirect_uri": github_config["REDIRECT_URI"],
            "scope": "user:email",
            "state": state,
        }
    )
    github_url = f"{github_config['AUTHORIZE_URL']}?{query}"

    response = RedirectResponse(github_url)
    response.add_cookie(
        key=cookie_name,
        value=signed_state,
        httponly=True,
        secure=secure,
        samesite="Lax",
        max_age=max_age,
        path=_callback_cookie_path(github_config),
    )
    return response


def clear_oauth_state_cookie(func):
    @wraps(func)
    async def wrapper(request: Request):
        resp = await func(request)
        _delete_state_cookie(resp, request, request.app.config.SOCIAL_CONFIG["github"])
        return resp

    return wrapper


@clear_oauth_state_cookie
async def github_callback(request: Request):
    """Handle the GitHub callback and exchange the code for a JWT."""
    # get the github configurations from the request
    github_config = request.app.config.SOCIAL_CONFIG["github"]
    # get the cookie settings from the request
    cookie_name, max_age, _ = _cookie_settings(request)
    # get the code from the request
    code = request.args.get("code")
    # get the received state from the request
    received_state = request.args.get("state")
    # get the signed state from the cookies
    signed_state = request.cookies.get(cookie_name)

    if not code or not received_state or not signed_state:
        return JSONResponse({"error": "Missing OAuth callback parameters"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

    try:
        expected_state = unsign_state(signed_state, _state_secret(request), max_age=max_age)
    except ValueError:
        return JSONResponse({"error": "Invalid or expired OAuth state"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

    if not hmac.compare_digest(expected_state, received_state):
        return JSONResponse({"error": "OAuth state mismatch"}, status=HTTPStatus.HTTP_403_FORBIDDEN)

    timeout = aiohttp.ClientTimeout(total=GITHUB_REQUEST_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            token_data = await _github_request_json(
                session,
                "POST",
                github_config["ACCESS_TOKEN_URL"],
                headers={"Accept": "application/json"},
                data={
                    "client_id": github_config["CLIENT_ID"],
                    "client_secret": github_config["CLIENT_SECRET"],
                    "code": code,
                    "redirect_uri": github_config["REDIRECT_URI"],
                },
            )
            access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
            if not access_token:
                return JSONResponse({"error": "GitHub rejected the authorization code"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

            github_headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            }
            user = await _github_request_json(
                session,
                "GET",
                github_config["GITHUB_USER"],
                headers=github_headers,
            )
            emails = await _github_request_json(
                session,
                "GET",
                github_config["GITHUB_USER_EMAIL"],
                headers=github_headers,
            )
    except (aiohttp.ClientError, TimeoutError, ValueError):
        error_logger.exception("GitHub OAuth request failed")
        return JSONResponse({"error": "GitHub is temporarily unavailable"}, status=HTTPStatus.HTTP_502_BAD_GATEWAY)

    primary_email = _verified_email(emails) if isinstance(emails, list) else None
    if not primary_email:
        return JSONResponse({"error": "GitHub did not provide a verified email address"}, status=HTTPStatus.HTTP_400_BAD_REQUEST)

    fallback_username = primary_email.split("@", 1)[0]
    if isinstance(user, dict):
        username = user.get("name") or user.get("login") or fallback_username
    else:
        username = fallback_username
    try:
        role = await models.Role.filter(name="user").first()
        if role is None:
            raise RuntimeError("The default user role is not configured")
        user_db, _ = await models.User.get_or_create(
            email=primary_email,
            defaults={
                "name": username,
                "role": role,
            },
        )
        # Redirect with a temporary code so the JWT is never exposed in a URL.
        one_time_code = await _store_exchange_code(request, user_db.id)
    except Exception:
        error_logger.exception("Could not complete GitHub user login")
        return JSONResponse({"error": "Could not complete social login"}, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)

    separator = "&" if "?" in github_config["OAUTHCALLBACK"] else "?"
    return RedirectResponse(f"{github_config['OAUTHCALLBACK']}{separator}{urlencode({'code': one_time_code})}")


async def login_by_code(request: Request):
    """Consume a one-time social login code and return the application's JWT."""
    code = request.args.get("code")
    if not code:
        raise BadRequest("Missing authorization code")
    if len(code) > 256:
        raise BadRequest("Invalid authorization code")

    user_id = await request.app.ctx.redis.getdel(_exchange_code_key(request, code))
    if user_id is None:
        raise NotFound("Invalid or expired authorization code")

    try:
        user_id = int(user_id.decode("ascii") if isinstance(user_id, bytes) else user_id)
    except (TypeError, ValueError, UnicodeDecodeError):
        error_logger.error("Social login code contained an invalid user ID")
        raise NotFound("Invalid authorization code") from None

    user_db = await models.User.filter(pk=user_id).select_related("role").first()
    if user_db is None:
        raise NotFound("User not found")

    authentication = Authentication(request.app, request.app.ctx.jwt.config)
    user_data = UserSchemaReader.model_validate(user_db).model_dump(
        by_alias=True,
        mode="json",
    )
    role_name = user_db.role.name if user_db.role else None
    access_token = await authentication.generate_access_token(
        user={
            "user_id": user_db.id,
            "username": user_db.name,
            "role": role_name,
        }
    )
    user_data["access_token"] = access_token
    return JSONResponse(user_data)
