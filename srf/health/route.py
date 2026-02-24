from sanic import Blueprint
from sanic.response import JSONResponse

from srf.views.http_status import HTTPStatus

from .checks import RedisCheck, SQLiteCheck

bp = Blueprint("health", url_prefix="/health")


@bp.get("/")
async def health_check(request):
    checked = list()
    need_check = list([RedisCheck, SQLiteCheck])

    # Build check instances from app.ctx (redis, pg, sqlite, etc.)
    for CheckClass in need_check:
        if CheckClass.name == "redis":
            check = CheckClass(request.app.ctx.redis)
        elif CheckClass.name == "postgres":
            check = CheckClass(request.app.ctx.pg)
        elif CheckClass.name == "mongodb":
            check = CheckClass(request.app.ctx.mongo)
        elif CheckClass.name == "sqlite":
            check = CheckClass(request.app.ctx.sqlite)
        else:
            check = CheckClass()

        checked.append(await check.run())

    status = {name: status for name, status in checked}
    ok = all(v.startswith("up") for v in status.values())

    return JSONResponse(
        {"status": "ok" if ok else "fail", "services": status},
        status=(HTTPStatus.HTTP_200_OK if ok else HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR),
    )
