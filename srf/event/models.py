from tortoise import fields
from tortoise.models import Model as TorModel


class Event(TorModel):
    """Audit / activity event log."""

    id = fields.BigIntField(pk=True, generated=True)
    user = fields.ForeignKeyField("models.User", related_name="events", null=True, on_delete=fields.SET_NULL)

    action = fields.CharField(max_length=128, null=True, description="action of the event")
    obj_id = fields.BigIntField(null=True, description="id of the object")
    obj_name = fields.CharField(max_length=128, null=True, description="name of the object")

    req_data = fields.JSONField(null=True, description="request data of the event")
    req_remote = fields.CharField(max_length=128, null=True, description="request source of the event")
    res_data = fields.JSONField(null=True, description="response data of the event")

    create_time = fields.DatetimeField(auto_now_add=True, description="create time of the event")

    class Meta:
        table = "event_event"

    def __repr__(self) -> str:
        return f"<Event id={getattr(self, 'id', None)} " f"action={getattr(self, 'action', None)!r} obj_name={getattr(self, 'obj_name', None)!r}>"
