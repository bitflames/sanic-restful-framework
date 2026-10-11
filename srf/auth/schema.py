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
    field_serializer,
    field_validator,
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

    # populate_by_name lets aliased fields validate from their field names too —
    # ORM objects only expose create_time/update_time, not the aliases.
    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("create_time", "update_time", when_used="json")
    def _format_datetime(self, v: datetime.datetime | None) -> str | None:
        return v.strftime(settings.DATETIME_FORMAT) if v else None


# Reusable type: SecretStr masks repr/logs; AfterValidator enforces strength → ValidationError
StrongPassword = Annotated[SecretStr, AfterValidator(validate_secret)]


class UserSchemaWriter(SchemaBaseTime):
    id: int | None = Field(None, frozen=True)
    username: str
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    password: StrongPassword = Field(..., alias="password1", exclude=True)
    password_confirm: StrongPassword = Field(..., alias="password2", exclude=True)
    roles: list[str] | None = Field(None)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def check_passwords(self) -> "UserSchemaWriter":
        if self.id is not None:
            return self  # if orm instance, skip password check
        if self.password is None or self.password_confirm is None:
            raise ValueError("password1 and password2 are required")
        _require_matching_passwords(self.password, self.password_confirm)
        return self


class UserSchemaUpdate(SchemaBaseTime):
    """Profile update payload — no password fields (use change-password action)."""

    id: int | None = Field(None, frozen=True)
    username: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordSchema(BaseModel):
    old_password: SecretStr
    password: StrongPassword = Field(..., alias="password1")
    password_confirm: StrongPassword = Field(..., alias="password2")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_passwords(self) -> "ChangePasswordSchema":
        _require_matching_passwords(self.password, self.password_confirm)
        return self


class RoleSchemaReader(BaseModel):
    id: int = Field(..., frozen=True)
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class UserSchemaReader(SchemaBaseTime):
    id: int = Field(..., frozen=True)
    username: str = Field(...)
    email: EmailStr | None = None
    is_active: bool = True
    is_superuser: bool = False
    last_login: datetime.datetime | None = None
    roles: list[RoleSchemaReader] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("roles", mode="before")
    @classmethod
    def ignore_unfetched_roles(cls, v: object) -> object:
        """Serialize roles only when already fetched.

        Lists pass through. Tortoise 1.x M2M relations are lazy relation objects:
        iterating one before fetch_related/prefetch_related raises NoValuesFetched,
        so an unfetched relation becomes None instead of failing validation.
        """
        if v is None or isinstance(v, (list, tuple)):
            return v
        try:
            return list(v)
        except Exception:  # noqa: BLE001
            return None

    @computed_field()
    def url(self) -> str:
        return f"/user/{self.id}"


class UserLoginSchema(BaseModel):
    email: EmailStr | None = Field(None)
    username: str | None = Field(None)
    password: SecretStr

    @model_validator(mode="after")
    def check_identifier(self) -> "UserLoginSchema":
        if not self.email and not self.username:
            raise ValueError("email or username is required")
        return self
