"""
Pytest configuration and shared fixtures.
Set SECRET_KEY before any srf config is loaded.
"""

import os

import pytest

# Must set before importing srf.config.settings (which is loaded by srf modules)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")


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
