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
