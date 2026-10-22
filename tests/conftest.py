"""
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Optional for tests that still read env-based email/social settings
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-32bytes!!")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-pytest-32bytes!!")


@pytest.fixture
async def db():
    """Fresh in-memory Tortoise DB per test, schema generated from TORTOISE_ORM."""
    from tortoise import Tortoise

    from tests.tortoise_config import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
def mock_request():
    """Minimal Sanic request-like object for unit tests."""
    from unittest.mock import MagicMock

    req = MagicMock()
    req.method = "GET"
    req.args = {}
    req.json = None
    req.headers = {}
    req.path = "/api/items/"
    return req


def pytest_collection_modifyitems(items):
    """Run the real-server tests (tests/test_app_server.py) last.

    sanic_testing's ReusableClient leaves the process in a state that makes a
    later SanicTestClient server startup hang, so every other test module must
    complete first.
    """
    server_items = [item for item in items if item.path.name == "test_app_server.py"]
    if server_items:
        items[:] = [item for item in items if item not in server_items] + server_items
