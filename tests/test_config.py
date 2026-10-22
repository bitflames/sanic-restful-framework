"""Unit tests for srf.config LazySettings."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from srf.config import settings


def _restore_settings_app(previous):
    if previous is None:
        if hasattr(settings, "app"):
            delattr(settings, "app")
    else:
        object.__setattr__(settings, "app", previous)


class TestLazySettings:
    def test_uppercase_settings_loaded(self):
        assert settings.HEALTH_CHECK_LIST == []
        assert settings.REQUEST_LIMITERS == []
        assert settings.USER_REGISTER_EMAIL_CODE == "USER_REGISTER:EMAIL_CODE:{email}"
        assert len(settings.DEFAULT_FILTERS) == 4
        assert settings.DEFAULT_PERMISSION_CLASSES[0].__name__ == "AllowAny"

    def test_missing_attr_raises(self):
        with pytest.raises(AttributeError, match="NotImplemented"):
            _ = settings.THIS_DOES_NOT_EXIST

    def test_set_app_last_app_wins(self):
        previous = getattr(settings, "app", None)
        try:
            app1 = MagicMock()
            app1.config = SimpleNamespace(USER_REGISTER_EMAIL_CODE="FROM_APP1:{email}")
            app2 = MagicMock()
            app2.config = SimpleNamespace(USER_REGISTER_EMAIL_CODE="FROM_APP2:{email}")

            settings.set_app(app1)
            assert settings.USER_REGISTER_EMAIL_CODE == "FROM_APP1:{email}"

            settings.set_app(app2)
            assert settings.USER_REGISTER_EMAIL_CODE == "FROM_APP2:{email}"
            assert settings.MIN_PASSWORD_LENGTH == 8
        finally:
            _restore_settings_app(previous)

    def test_two_apps_each_override_then_fallback(self):
        previous = getattr(settings, "app", None)
        try:
            app1 = MagicMock()
            app1.config = SimpleNamespace(
                USER_REGISTER_EMAIL_CODE="A:{email}",
                MIN_PASSWORD_LENGTH=10,
            )
            app2 = MagicMock()
            app2.config = SimpleNamespace(USER_REGISTER_EMAIL_CODE="B:{email}")

            settings.set_app(app1)
            assert settings.USER_REGISTER_EMAIL_CODE == "A:{email}"
            assert settings.MIN_PASSWORD_LENGTH == 10

            settings.set_app(app2)
            assert settings.USER_REGISTER_EMAIL_CODE == "B:{email}"
            assert settings.MIN_PASSWORD_LENGTH == 8
        finally:
            _restore_settings_app(previous)

    def test_password_min_length_follows_bound_app(self):
        from srf.auth.schema import validate_password_strength

        previous = getattr(settings, "app", None)
        try:
            app = MagicMock()
            app.config = SimpleNamespace(MIN_PASSWORD_LENGTH=12)
            settings.set_app(app)
            with pytest.raises(ValueError, match="at least 12"):
                validate_password_strength("Abcdef1")
            assert validate_password_strength("Abcdefghijk1") == "Abcdefghijk1"
        finally:
            _restore_settings_app(previous)
