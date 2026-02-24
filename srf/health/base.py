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

    # def __init_subclass__(cls, **kwargs):
    #     registry.register(cls)

    async def check(self):
        raise NotImplementedError("Must implement check()")

    async def run(self):
        try:
            await self.check()
            return (self.name, "up")
        except Exception as e:
            return (self.name, f"down ({str(e)})")
