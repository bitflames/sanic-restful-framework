from sanic import Sanic

from .social_auth import github_callback, github_login, login_by_code
from .viewset import logout, register, setup_auth, verify_email


def register_auth_urls(app: Sanic, prefix='/api/auth'):
    setup_auth(app, url_prefix=prefix, secret=app.config.JWT_SECRET)  # JWT_SECRET must be set in your Sanic config, no default value

    app.add_route(logout, uri=f'{prefix}/logout', methods=['POST'])
    app.add_route(register, uri=f'{prefix}/register', methods=['POST'])
    app.add_route(verify_email, uri=f'{prefix}/send-verification-email', methods=['POST'])

    # social login
    app.add_route(github_login, uri=f'{prefix}/social/github/login', methods=['GET'])
    app.add_route(github_callback, uri=f"{prefix}/social/callback", methods=['GET'])
    app.add_route(
        login_by_code,
        uri=f"{prefix}/social/github/login_by_code",
        methods=['GET'],
    )
