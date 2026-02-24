"""Unit tests for srf.exceptions."""

import pytest

from srf.exceptions import ImproperlyConfigured, TargetObjectAlreadyExist


class TestTargetObjectAlreadyExist:
    def test_status_code(self):
        assert TargetObjectAlreadyExist.status_code == 409

    def test_quiet(self):
        assert TargetObjectAlreadyExist.quiet is True

    def test_with_message(self):
        exc = TargetObjectAlreadyExist(message="user already exists")
        assert exc.message == "user already exists"


class TestImproperlyConfigured:
    def test_status_code(self):
        assert ImproperlyConfigured.status_code == 500

    def test_raises_with_message(self):
        with pytest.raises(ImproperlyConfigured, match="must be a list or tuple"):
            raise ImproperlyConfigured("SOME_SETTING must be a list or tuple.")
