from sanic import Sanic

from .social_auth import github_callback, github_login, login_by_code
from .viewset import logout, register, setup_auth, verify_email


def register_auth_urls(app: Sanic, prefix='/api/auth'):
    jwt = setup_auth(app, url_prefix=prefix)
    app.config.update({"JWT": jwt})
    app.add_route(logout, uri=f'{prefix}/logout', methods=['POST'])
    app.add_route(register, uri=f'{prefix}/register', methods=['POST'])
    app.add_route(verify_email, uri=f'{prefix}/send-verification-email', methods=['POST'])

    # social login
    app.add_route(github_login, uri=f'{prefix}/social/github/login', methods=['POST'])
    app.add_route(github_callback, uri=f"{prefix}/social/callback", methods=['GET'])
    app.add_route(
        login_by_code,
        uri=f"{prefix}/social/github/login_by_code",
        methods=['GET'],
    )
