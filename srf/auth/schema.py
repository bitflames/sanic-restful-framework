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
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)
from tortoise.timezone import now as tortoise_timezone_now

from srf.config import settings


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


def require_matching_passwords(password: SecretStr, password_confirm: SecretStr) -> None:
    plain = password.get_secret_value()
    confirm = password_confirm.get_secret_value()
    if plain != confirm:
        raise ValueError("password1 and password2 do not match")


class RoleSchemaReader(BaseModel):
    id: int = Field(..., frozen=True)
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None)

    model_config = ConfigDict(from_attributes=True)


class SchemaBaseUser(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    email: EmailStr | None = Field(None)

    model_config = ConfigDict(from_attributes=True)


class UserSchemaUpdate(BaseModel):
    """Profile update payload — email and password are immutable here."""

    username: str | None = Field(None, min_length=1, max_length=150)

    @model_validator(mode="after")
    def reject_null_username(self) -> "UserSchemaUpdate":
        if "username" in self.model_fields_set and self.username is None:
            raise ValueError("username may not be null")
        return self


# Reusable type: SecretStr masks repr/logs; AfterValidator enforces strength → ValidationError
StrongPassword = Annotated[SecretStr, AfterValidator(validate_secret)]


class UserSchemaWriter(SchemaBaseUser):
    password: StrongPassword = Field(..., alias="password1", exclude=True)
    password_confirm: StrongPassword = Field(..., alias="password2", exclude=True)

    @model_validator(mode="after")
    def check_passwords(self) -> "UserSchemaWriter":
        if self.password is None or self.password_confirm is None:
            raise ValueError("password1 and password2 are required")
        require_matching_passwords(self.password, self.password_confirm)
        return self


class UserSchemaAdminBase(BaseModel):
    is_superuser: bool | None = None
    is_active: bool | None = None
    roles: list[str] | None = None

    @model_validator(mode="after")
    def reject_null_flags(self) -> "UserSchemaAdminBase":
        for field in ("is_superuser", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} may not be null")
        return self


class UserSchemaAdminCreate(UserSchemaWriter, UserSchemaAdminBase):
    """Superuser-only create payload: required username/password plus privilege fields.

    ``is_superuser`` / ``is_active``: omitted falls back to the safe defaults in
    ``User.create_user`` (``False`` / ``True``).

    ``roles`` takes role names; unknown names are ignored.
    """


class UserSchemaAdminUpdate(UserSchemaUpdate, UserSchemaAdminBase):
    """Superuser-only update payload: optional privilege fields, no password/email.

    Omitted fields stay untouched. ``roles`` replaces the whole role set
    (``[]`` clears all); omitted leaves it untouched.
    Password changes go through the change-password / reset-password actions.
    """


class AdminPasswordResetSchema(BaseModel):
    """Superuser password reset payload (no old-password verification)."""

    password: StrongPassword = Field(..., alias="password1")
    password_confirm: StrongPassword = Field(..., alias="password2")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="after")
    def check_passwords(self) -> "ChangePasswordSchema":
        require_matching_passwords(self.password, self.password_confirm)
        return self


class ChangePasswordSchema(AdminPasswordResetSchema):
    old_password: SecretStr


class UserSchemaReader(SchemaBaseUser):
    id: int = Field(..., frozen=True)
    is_active: bool = True
    is_superuser: bool = False
    last_login: datetime.datetime | None = None
    roles: list[RoleSchemaReader] | None = None
    create_time: datetime.datetime = Field(default_factory=tortoise_timezone_now)
    update_time: datetime.datetime | None = Field(default_factory=tortoise_timezone_now)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("create_time", "update_time", when_used="json")
    def _format_datetime(self, v: datetime.datetime | None) -> str | None:
        return v.strftime(settings.DATETIME_FORMAT) if v else None

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


class UserLoginSchema(BaseModel):
    account: str
    password: SecretStr

    @property
    def is_email(self) -> bool:
        try:
            TypeAdapter(EmailStr).validate_python(self.account)
            return True
        except ValidationError:
            return False
