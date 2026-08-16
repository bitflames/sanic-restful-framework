"""Tortoise models used only by tests/app_server.py integration harness."""

from tortoise import fields
from tortoise.models import Model


class SecretNote(Model):
    """Per-user note with a globally unique title (for 409 / IDOR scenarios)."""

    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField(
        "models.User",
        related_name="secret_notes",
        on_delete=fields.CASCADE,
    )
    title = fields.CharField(max_length=128, unique=True)
    body = fields.TextField(null=True)

    class Meta:
        table = "app_server_secret_note"
