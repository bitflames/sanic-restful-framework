# Srf default configuration
# Sanic requires the configuration name to be in uppercase

import json
import os
from datetime import datetime, timedelta

from srf.filters.filter import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)

SECRET_KEY = os.getenv("SECRET_KEY", None)
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")

# BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = os.getcwd()
# Cache root directory
CACHE_ROOT = os.path.join(BASE_DIR, ".diskcache")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # Time string template


# JWT config
JWT_SECRET = SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

# SRF authentication-free URL suffixes
NON_AUTH_ENDPOINTS = (
    "register",
    "login",
    "send-verification-email",
    "health",
    "about",
    "social_login",
    "callback",
    "login_by_code",
    "rules",
)


def custom_dumps(obj):
    def default(obj):
        if isinstance(obj, datetime):
            return obj.strftime(DATETIME_FORMAT)
        if isinstance(obj, Exception):
            return str(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    return json.dumps(obj, default=default)


JSON_ENCODER = custom_dumps


# cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "media": {
        "BACKEND": "diskcache.DjangoCache",
        "LOCATION": CACHE_ROOT,
        "TIMEOUT": None,
        "SHARDS": 32,
        "OPTIONS": {
            "size_limit": 2**40,  # 1 Tb
        },
    },
}


DEFAULT_FILTERS = [
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory,
]


class EmailConfig:
    from_email = os.getenv("FROM_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    password = os.getenv("PASSWORD")


SOCIAL_CONFIG = {
    "github": {
        "CLIENT_ID": os.getenv("GITHUB_CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("GITHUB_CLIENT_SECRET"),
        "REDIRECT_URI": os.getenv("GITHUB_REDIRECT_URI"),
        "AUTHORIZE": os.getenv("AUTHORIZE", "https://github.com/login/oauth/authorize"),
        "ACCESS_TOKEN": os.getenv("ACCESS_TOKEN", "https://github.com/login/oauth/access_token"),
        "OAUTHCALLBACK": os.getenv("OAUTHCALLBACK"),
        "GITHUB_USER": "https://api.github.com/user",
        "GITHUB_USER_EMAIL": "https://api.github.com/user/emails",
    }
}
