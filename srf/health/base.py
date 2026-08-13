from sanic.log import error_logger


class HealthCheckRegistry:
    def __init__(self):
        self.checks = []

    def register(self, check_class):
        self.checks.append(check_class)

    def get_checks(self):
        return self.checks


registry = HealthCheckRegistry()


class BaseHealthCheck:
    name = "base"
    timeout = 5  # seconds

    def __init__(self, app):
        """
        app: Sanic application instance
        """

        self.app = app
        client = getattr(app.ctx, self.name, None)
        if client is None:
            raise ValueError(f"{self.name} not found in app.ctx")
        setattr(self, self.name, client)

    # def __init_subclass__(cls, **kwargs):
    #     registry.register(cls)

    async def check(self):
        raise NotImplementedError("Must implement check()")

    async def run(self):
        try:
            await self.check()
            return (self.name, "up")
        except Exception as e:  # noqa: BLE001
            error_logger.exception("Health check %s failed: %s", self.name, e)
            return (self.name, "down")
