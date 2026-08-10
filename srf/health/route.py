from sanic import Blueprint
from sanic.response import JSONResponse

from srf.views.http_status import HTTPStatus

bp = Blueprint("health", url_prefix="/health")


@bp.get("/")
async def health_check(request):
    checked = []
    HEALTH_CHECK_LIST = request.app.config.HEALTH_CHECK_LIST or []

    # Build check instances; each check reads its client from app.ctx.<name>
    for CheckClass in HEALTH_CHECK_LIST:
        check = CheckClass(request.app)
        checked.append(await check.run())

    status = {name: status for name, status in checked}
    ok = all(v.startswith("up") for v in status.values())

    return JSONResponse(
        {"status": "ok" if ok else "fail", "services": status},
        status=(HTTPStatus.HTTP_200_OK if ok else HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR),
    )
