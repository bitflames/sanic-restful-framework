import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class EventSchema(BaseModel):
    """Read payload for audit events."""

    id: int | None = Field(None, frozen=True)
    user_id: int | None = None
    action: str | None = Field(None, max_length=128)
    obj_id: int | None = None
    obj_name: str | None = Field(None, max_length=128)
    req_data: dict[str, Any] | list[Any] | None = None
    req_remote: str | None = Field(None, max_length=128)
    res_data: dict[str, Any] | list[Any] | None = None
    create_time: datetime.datetime | None = Field(None, frozen=True)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, ser_json_alias=True)

    @computed_field()
    def url(self) -> str:
        return f"/events/{self.id}"
