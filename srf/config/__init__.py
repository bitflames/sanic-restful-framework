"""Configuration package: SrfConfig singleton merges app.config with module settings."""

import importlib

from sanic import Sanic

from srf.exceptions import ImproperlyConfigured

SETTINGS_PATH = "srf.config.settings"


class SrfConfig:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, app: Sanic = None):
        if getattr(self, '_inited', False):
            return
        self._inited = True
        self.__set()
        if app:
            self.set_app(app)

    def __set(self):
        mod = importlib.import_module(SETTINGS_PATH)
        MUST_BE_SEQ = (  # TODO update it
            "ALLOWED_HOSTS",
            "INSTALLED_APPS",
            "TEMPLATE_DIRS",
            "LOCALE_PATHS",
            "SECRET_KEY_FALLBACKS",
        )
        for name in dir(mod):
            if name.isupper():
                value = getattr(mod, name)
                if name in MUST_BE_SEQ and not isinstance(value, (list, tuple)):
                    raise ImproperlyConfigured(f"{name} must be a list or tuple.")
                setattr(self, name, value)

    def set_app(self, app: Sanic):
        setattr(self, "app", app.config)

    def __getattribute__(self, name):
        """Prefer Sanic app.config, then fall back to SRF module settings."""

        try:
            app = object.__getattribute__(self, "app")
        except AttributeError:
            app = None

        if app is not None:
            try:
                return getattr(app, name)
            except AttributeError:
                pass

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            raise AttributeError(f"{name} NotImplemented!")


srfconfig = SrfConfig()
