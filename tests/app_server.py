"""
Local SRF server for manual API testing (sqlite + fakeredis).

  python tests/app_server.py
  python tests/api_call_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python tests/app_server.py` without `pip install -e .`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import fakeredis.aioredis as fakeredis_aio
from sanic import Blueprint, Sanic, json
from tortoise.contrib.sanic import register_tortoise

from srf.auth.models import Role, User
from srf.auth.route import register_auth_urls
from srf.auth.viewset import UserViewSet
from srf.config import settings
from srf.event.viewset import EventViewSet
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.permission.permission import IsAuthenticated
from srf.route import SanicRouter
from srf.views import BaseViewSet, action

HOST = "127.0.0.1"
PORT = 8800
JWT_SECRET = "local-srf-jwt-secret-key-32bytes!!"
SECRET_KEY = "local-srf-secret-key-32-bytes!!!!"
DB_URL = f"sqlite://{_ROOT / 'tests' / 'app_server.sqlite3'}"

SEED_EMAIL = "alice@example.com"
SEED_USERNAME = "alice"
SEED_PASSWORD = "password123"
SEED_ROLE = "user"

ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin12345"
ADMIN_ROLE = "admin"

# Shared across Sanic reloads so refresh tokens survive worker restarts in debug mode
_REDIS = fakeredis_aio.FakeRedis(decode_responses=False)


class ProfileViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)

    @property
    def queryset(self):
        return User.all()

    def get_schema(self, request, *args, is_safe=False, **kwargs):
        from srf.auth.schema import UserSchemaReader

        return UserSchemaReader

    @action(methods=["get"], detail=False, url_path="ping", url_name="profile-ping")
    async def ping(self, request):
        user = request.ctx.user
        return json(
            {
                "ok": True,
                "user_id": user.id,
                "username": user.name,
                "email": user.email,
            }
        )


async def ensure_seed_data() -> User:
    role, _ = await Role.get_or_create(
        name=SEED_ROLE,
        defaults={"description": "default user role"},
    )
    admin_role, _ = await Role.get_or_create(name=ADMIN_ROLE, defaults={"description": "admin role"})

    user = await User.filter(email=SEED_EMAIL).first()
    if user is None:
        user = await User.create_user(
            {
                "name": SEED_USERNAME,
                "email": SEED_EMAIL,
                "password": SEED_PASSWORD,
                "role_name": SEED_ROLE,
                "is_active": True,
            }
        )
    else:
        user.password = User.hash_password(SEED_PASSWORD)
        user.is_active = True
        user.role = role
        await user.save()

    admin = await User.filter(email=ADMIN_EMAIL).first()
    if admin is None:
        await User.create_user(
            {
                "name": ADMIN_USERNAME,
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "role_name": ADMIN_ROLE,
                "is_active": True,
            }
        )
    else:
        admin.password = User.hash_password(ADMIN_PASSWORD)
        admin.is_active = True
        admin.role = admin_role
        await admin.save()

    return user


def create_app() -> Sanic:
    app = Sanic("srf-local-server")
    app.config.JWT_SECRET = JWT_SECRET
    app.config.SECRET_KEY = SECRET_KEY
    app.config.NON_AUTH_ENDPOINTS = tuple(settings.NON_AUTH_ENDPOINTS) + (
        "/api/public/hello",
        "/health",
    )
    settings.set_app(app)

    register_tortoise(
        app,
        db_url=DB_URL,
        modules={"models": ["srf.auth.models", "srf.event.models"]},
        generate_schemas=True,
    )
    register_auth_urls(app, prefix="/api/auth")

    router = SanicRouter(Blueprint("api"), prefix="api")
    router.register("users", UserViewSet, name="users")
    router.register("profile", ProfileViewSet, name="profile")
    router.register("events", EventViewSet, name="events")
    app.blueprint(router.get_blueprint())

    @app.get("/health")
    async def health(_request):
        return json({"status": "ok"})

    @app.get("/api/public/hello")
    async def public_hello(_request):
        return json({"message": "hello"})

    @app.middleware("request")
    async def auth_middleware(request):
        await set_user_to_request_ctx(request)

    @app.before_server_start
    async def setup(app_: Sanic):
        from tortoise import Tortoise

        await Tortoise.generate_schemas()
        app_.ctx.redis = _REDIS
        await ensure_seed_data()

    return app


def main():
    app = create_app()
    print(f"SRF → http://{HOST}:{PORT}")
    print(f"DB   {DB_URL}  (sqlite)")
    print("Redis fakeredis (in-memory)")
    print(f"Login POST /api/auth/login  {SEED_EMAIL} / {SEED_PASSWORD}")
    print(f"Admin  POST /api/auth/login  {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("API calls: python tests/api_call_tests.py")
    app.run(host=HOST, port=PORT, debug=True, access_log=True, single_process=True)


if __name__ == "__main__":
    main()
