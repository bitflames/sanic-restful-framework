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
from srf.paginator import PageNumberPagination

PAGINATION_CLASS = PageNumberPagination

# SECRET_KEY and JWT_SECRET must be set in your Sanic config
# SECRET_KEY
# JWT_SECRET
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

# BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = os.getcwd()
# Cache root directory
CACHE_ROOT = os.path.join(BASE_DIR, ".diskcache")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # Time string template

# health check list
HEALTH_CHECK_LIST = []

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


# TODO add caches


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
        "AUTHORIZE_URL": os.getenv("AUTHORIZE_URL", "https://github.com/login/oauth/authorize"),
        "ACCESS_TOKEN_URL": os.getenv("ACCESS_TOKEN_URL", "https://github.com/login/oauth/access_token"),
        "OAUTHCALLBACK": os.getenv("OAUTHCALLBACK"),
        "GITHUB_USER": "https://api.github.com/user",
        "GITHUB_USER_EMAIL": "https://api.github.com/user/emails",
    }
}

SOCIAL_LOGIN_COOKIE_KEY = "oauth_state"
SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE = 600  # seconds
USER_REGISTER_EMAIL_VERIFY_CODE_TTL = 60  # seconds

# Redis key prefix for email verification codes
EMAIL_CODE_REDIS = "EMAIL_CODE"

# Default empty; apps can set REQUEST_LIMITERS on Sanic config
REQUEST_LIMITERS = []
