import asyncio

from sanic.response import JSONResponse


async def health_check(request):
    health_check_list = request.app.config.HEALTH_CHECK_LIST or []
    checks = [CheckClass(request.app) for CheckClass in health_check_list]
    checked = await asyncio.gather(*(check.run() for check in checks))
    return JSONResponse({name: result for name, result in checked})
