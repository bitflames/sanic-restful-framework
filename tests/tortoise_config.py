"""Tortoise config for the local test harness only — not part of the framework."""

TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "models": {
            "models": ["srf.auth.models", "srf.event.models", "tests.app_models"],
            "default_connection": "default",
        },
    },
    "use_tz": True,
    "timezone": "UTC",
}
