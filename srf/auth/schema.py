import datetime
import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    computed_field,
    model_validator,
)

from srf.config import settings


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def unwrap_secret(value: SecretStr | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def validate_password_strength(password: str) -> str:
    """Common password rules: length, letter and digit.

    Raising ValueError here is the Pydantic V2 convention: field/model validators
    convert it into a ValidationError (there is no separate password API in Pydantic).
    """
    min_length = settings.MIN_PASSWORD_LENGTH
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


def validate_secret(v: SecretStr) -> SecretStr:
    validate_password_strength(v.get_secret_value())
    return v


def _require_matching_passwords(password: SecretStr, password_confirm: SecretStr) -> None:
    plain = password.get_secret_value()
    confirm = password_confirm.get_secret_value()
    if plain != confirm:
        raise ValueError("password1 and password2 do not match")


class SchemaBaseTime(BaseModel):
    create_time: datetime.datetime = Field(default_factory=utc_now, alias="created_date")
    update_time: datetime.datetime = Field(default_factory=utc_now, alias="updated_date")

    model_config = ConfigDict(json_encoders={datetime.datetime: lambda v: (v.strftime(settings.DATETIME_FORMAT) if v else None)})


# Reusable type: SecretStr masks repr/logs; AfterValidator enforces strength → ValidationError
StrongPassword = Annotated[SecretStr, AfterValidator(validate_secret)]


class UserSchemaWriter(SchemaBaseTime):
    id: int | None = None
    name: str = Field(..., alias="username")
    email: EmailStr | None = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    password: StrongPassword = Field(..., alias="password1")
    password_confirm: StrongPassword = Field(..., alias="password2")
    role_name: str = Field(default="user")

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, ser_json_alias=True
    )  # Both name and alias are allowed to be assigned. The output of ser_json_alias must use alias

    @model_validator(mode="after")
    def check_passwords(self) -> "UserSchemaWriter":
        _require_matching_passwords(self.password, self.password_confirm)
        return self


class UserSchemaUpdate(SchemaBaseTime):
    """Profile update payload — no password fields (use change-password action)."""

    id: int | None = Field(None, frozen=True)
    name: str | None = Field(None, alias="username")
    email: EmailStr | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    is_superuser: bool | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, ser_json_alias=True)


class ChangePasswordSchema(BaseModel):
    old_password: SecretStr
    password: StrongPassword = Field(..., alias="password1")
    password_confirm: StrongPassword = Field(..., alias="password2")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_passwords(self) -> "ChangePasswordSchema":
        _require_matching_passwords(self.password, self.password_confirm)
        return self


class UserSchemaReader(SchemaBaseTime):
    id: int
    name: str = Field(..., alias="username")
    email: EmailStr | None = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    last_login: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, ser_json_alias=True)
    # Both name and alias are allowed to be assigned. The output of ser_json_alias must use alias

    @computed_field()
    def url(self) -> str:
        return f"/users/{self.id}"


class UserLoginSchema(BaseModel):
    email: EmailStr | None = Field(None)
    username: str | None = Field(None)
    password: SecretStr

    @model_validator(mode="after")
    def check_identifier(self) -> "UserLoginSchema":
        if not self.email and not self.username:
            raise ValueError("email or username is required")
        return self
