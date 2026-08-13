from sanic.response import JSONResponse


async def health_check(request):
    checked = []
    health_check_list = request.app.config.HEALTH_CHECK_LIST or []

    # Build check instances; each check reads its client from app.ctx.<name>
    for CheckClass in health_check_list:
        check = CheckClass(request.app)
        checked.append(await check.run())

    status = {name: result for name, result in checked}
    return JSONResponse(status)
