from sanic import Blueprint, Sanic
from sanic.exceptions import ServerError
from sanic_jwt import Initialize

from srf.config import settings

from .auth import authenticate, coerce_timedelta, retrieve_refresh_token, retrieve_user, store_refresh_token
from .social_auth import github_login_access, github_login_by_code, github_login_callback
from .viewset import logout, register, verify_email


def register_jwt_urls(instance: Sanic, prefix=''):
    """
    Setup JWT authentication (sanic-jwt) on the application.

    Registers the login / me / verify / refresh endpoints and stores the
    sanic-jwt Authentication object on ``app.ctx.auth``, which the SRF auth
    middleware reads. A Sanic app instance is required: initializing sanic-jwt
    on a Blueprint would attach ``ctx.auth`` to the blueprint, where the
    middleware cannot find it.

    Args:
        instance: The Sanic application instance.
        prefix: The URL prefix for the JWT endpoints.

    Raises:
        ServerError: If a Blueprint is passed, or the JWT secrets are missing.
    """
    if not isinstance(instance, Sanic):
        raise ServerError("register_jwt_urls() requires a Sanic app instance")

    jwt_secret = instance.config.get("JWT_SECRET")
    if not isinstance(jwt_secret, (str, bytes)) or not jwt_secret:
        raise ServerError("app.config.JWT_SECRET must be a non-empty string or bytes")
    refresh_token_secret = instance.config.get("SECRET_KEY")
    if not isinstance(refresh_token_secret, (str, bytes)) or not refresh_token_secret:
        raise ServerError("app.config.SECRET_KEY must be a non-empty string or bytes")

    # init sanic_jwt
    Initialize(
        instance,
        url_prefix=prefix,
        path_to_authenticate="/login",
        path_to_retrieve_user='/me',
        path_to_verify='/verify',
        path_to_refresh='/refresh',
        algorithm="HS256",
        authenticate=authenticate,
        retrieve_user=retrieve_user,
        store_refresh_token=store_refresh_token,
        retrieve_refresh_token=retrieve_refresh_token,
        secret=jwt_secret,
        refresh_token_enabled=True,
        verify_exp=True,
        expiration_delta=int(coerce_timedelta(settings.JWT_ACCESS_TOKEN_EXPIRES, "JWT_ACCESS_TOKEN_EXPIRES").total_seconds()),
    )


def register_auth_urls(instance: Sanic | Blueprint, prefix=''):
    instance.add_route(register, uri=f'{prefix}/register', methods=['POST'])
    instance.add_route(verify_email, uri=f"{prefix}/verify_email", methods=["POST"])
    instance.add_route(logout, uri=f'{prefix}/logout', methods=['POST'])


def register_social_auth_urls(instance: Sanic | Blueprint, prefix=''):
    instance.add_route(github_login_access, uri=f'{prefix}/social/github/login', methods=['POST'])
    instance.add_route(github_login_callback, uri=f"{prefix}/social/callback", methods=['GET'])
    instance.add_route(github_login_by_code, uri=f"{prefix}/social/github/login_by_code", methods=['POST'])


def register_all_auth_urls(instance: Sanic, prefix='/api/auth'):
    """Register JWT, local-auth and social-auth routes on the Sanic app."""
    register_jwt_urls(instance, prefix=prefix)
    register_auth_urls(instance, prefix=prefix)
    register_social_auth_urls(instance, prefix=prefix)
