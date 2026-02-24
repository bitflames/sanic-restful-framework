import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from srf.config.settings import DATETIME_FORMAT


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class SchemaBaseTime(BaseModel):
    create_time: datetime.datetime = Field(default_factory=utc_now, alias="created_date")
    update_time: datetime.datetime = Field(default_factory=utc_now, alias="updated_date")

    model_config = ConfigDict(json_encoders={datetime.datetime: lambda v: (v.strftime(DATETIME_FORMAT) if v else None)})  # for model_dump_json


class CreateUserEmail(BaseModel):
    name: str
    email: EmailStr
    create_time: datetime.datetime = Field(default_factory=utc_now, alias="created_date")
    confirm_time: datetime.datetime = Field(default_factory=utc_now, alias="confirm_date")

    # model_config = ConfigDict(json_encoders={datetime.datetime: lambda v: (v.strftime(DATETIME_FORMAT) if v else None)})


class UserSchemaWriter(SchemaBaseTime):
    id: Optional[int] = None
    name: str = Field(..., alias="username")
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    password: Optional[str]
    role_name: str = Field(default="user")

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, ser_json_alias=True
    )  # Both name and alias are allowed to be assigned. The output of ser_json_alias must use alias


class UserSchemaReader(SchemaBaseTime):
    id: int
    name: str = Field(..., alias="username")
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    last_login: Optional[datetime.datetime] = None
    date_joined: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, ser_json_alias=True)
    # Both name and alias are allowed to be assigned. The output of ser_json_alias must use alias

    @computed_field()
    def url(self) -> str:
        return f"/users/{self.id}"


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str
