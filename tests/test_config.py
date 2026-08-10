"""Unit tests for srf.config LazySettings."""

import warnings

import pytest

from srf.config import settings


class TestLazySettings:
    def test_uppercase_settings_loaded(self):
        assert settings.HEALTH_CHECK_LIST == []
        assert settings.REQUEST_LIMITERS == []
        assert settings.EMAIL_CODE_REDIS == "EMAIL_CODE"
        assert len(settings.DEFAULT_FILTERS) == 4
        assert settings.DEFAULT_PERMISSION_CLASSES[0].__name__ == "AllowAny"

    def test_missing_attr_raises(self):
        with pytest.raises(AttributeError, match="NotImplemented"):
            _ = settings.THIS_DOES_NOT_EXIST

    def test_srfconfig_deprecated_alias(self):
        from srf.config import srfconfig

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # reset one-time flag for a deterministic assertion
            type(srfconfig)._warned = False
            assert srfconfig.SOCIAL_LOGIN_COOKIE_KEY == settings.SOCIAL_LOGIN_COOKIE_KEY
            assert any(issubclass(w.category, DeprecationWarning) for w in caught)
