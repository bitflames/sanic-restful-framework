"""Tortoise ORM 1.x model definitions (default PK, no framework-level DB config)."""

import warnings

import pytest
from tortoise import fields

from srf.auth.models import RefreshToken, Role, User, UserRoles
from srf.event.models import Event
from tests.app_models import SecretNote
from tests.tortoise_config import TORTOISE_ORM


@pytest.mark.parametrize(
    "model",
    [Role, User, UserRoles, RefreshToken, Event, SecretNote],
)
def test_default_integer_primary_key(model):
    assert model._meta.pk_attr == "id"
    pk = model._meta.fields_map["id"]
    assert pk.pk is True
    assert isinstance(pk, fields.IntField)
    assert pk.generated is True


def test_models_import_without_pk_deprecation():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        from srf.auth import models as auth_models  # noqa: F401
        from srf.event import models as event_models  # noqa: F401
        from tests import app_models  # noqa: F401

        assert auth_models.User is User
        assert event_models.Event is Event
        assert app_models.SecretNote is SecretNote


def test_harness_config_uses_sqlite():
    url = TORTOISE_ORM["connections"]["default"]
    assert url.startswith("sqlite")
    models = TORTOISE_ORM["apps"]["models"]["models"]
    assert "srf.auth.models" in models
    assert "tests.app_models" in models
