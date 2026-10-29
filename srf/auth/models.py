import hashlib

import bcrypt
from tortoise import fields
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.models import Model as TorModel
from tortoise.timezone import now as tortoise_timezone_now
from tortoise.transactions import in_transaction

from srf.exceptions import TargetObjectAlreadyExist


class AnonymousUser:
    """Placeholder user for unauthenticated requests (Django/DRF style).

    Assigned to ``request.ctx.user`` by optional authentication (``authenticate_request(strict=False)``) when no credentials are presented.
    ``is_active=False`` and ``is_superuser=False`` make ``IsAuthenticated`` and ``SuperuserOnly`` reject it out of the box.
    """

    id = None
    username = ""
    email = ""
    is_active = False
    is_superuser = False
    is_anonymous = True
    is_authenticated = False

    def __repr__(self) -> str:
        return "AnonymousUser"

    def __str__(self) -> str:
        return "AnonymousUser"


class Role(TorModel):
    name = fields.CharField(max_length=256, null=False, unique=True)
    description = fields.CharField(max_length=256, null=True)

    class Meta:
        table = "auth_role"


class PasswordMixin(TorModel):
    password = fields.CharField(max_length=128, null=True)

    class Meta:
        abstract = True

    @staticmethod
    def _password_digest(password: str) -> bytes:
        """SHA-256 digest for bcrypt input.

        Only supported scheme: bcrypt(sha256(password)).
        No legacy bcrypt(password) fallback (avoids bcrypt's 72-byte limit).
        """
        return hashlib.sha256(password.encode("utf-8")).digest()

    def verify_password(self, password: str) -> bool:
        if self.password is None:
            return False
        try:
            return bcrypt.checkpw(self._password_digest(password), self.password.encode("utf-8"))
        except ValueError:
            # bcrypt raises ValueError on malformed stored hash — treat as failed verify.
            return False

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Store bcrypt(sha256(password)); never bcrypt(raw password)."""
        return bcrypt.hashpw(cls._password_digest(password), bcrypt.gensalt()).decode("utf-8")

    def set_password(self, raw_password: str) -> None:
        """Django-like password setter."""
        self.password = self.hash_password(raw_password)

    def set_unusable_password(self) -> None:
        """Mark the account as passwordless; social-login-only users can use this."""
        self.password = None

    def check_password(self, raw_password: str) -> bool:
        """Django-like password checker."""
        return self.verify_password(raw_password)

    def has_usable_password(self) -> bool:
        return bool(self.password)


class AbstractUser(TorModel):
    username = fields.CharField(max_length=150, unique=True, null=False)
    email = fields.CharField(max_length=256, null=True, unique=True)
    is_active = fields.BooleanField(default=True, null=False)
    is_superuser = fields.BooleanField(default=False, null=False)
    last_login = fields.DatetimeField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True, read_only=True)
    update_time = fields.DatetimeField(auto_now=True, null=True)

    refresh_tokens: fields.ReverseRelation["RefreshToken"]

    class Meta:
        abstract = True


class User(AbstractUser, PasswordMixin):
    roles: fields.ManyToManyRelation[Role] = fields.ManyToManyField(Role, through="auth_user_roles", related_name="users", backward_key="user_id")
    oauth_accounts: fields.ReverseRelation["OAuthAccount"]

    class Meta:
        table = "auth_user"

    def __repr__(self) -> str:
        # Never print stored credential material (hash or otherwise) during debug.
        return f"<User id={getattr(self, 'id', None)} username={getattr(self, 'username', None)!r} password='**********'>"

    @classmethod
    async def create_user(cls, user_info: dict) -> "User":
        """
        Do not override Tortoise's create method,
        create user with hashed password and role resolution.

        user_info["password"]:
            Expect plaintext str; callers unwrap SecretStr at the API boundary.
        user_info["roles"]:
            Optional list of role names; names that do not exist are ignored.
        """
        user_info = dict(user_info)
        user_info.pop("id", None)
        raw_password = user_info.pop("password", None)
        role_names = user_info.pop("roles", None)
        if not user_info.get("username"):
            raise ValueError("username is required")
        if user_info.get("email") is not None:
            user_info["email"] = str(user_info["email"]).lower()
        if raw_password:
            user_info["password"] = cls.hash_password(raw_password)
        else:
            user_info["password"] = None
        # Privilege flags default to safe values; only superuser-facing callers
        # (UserViewSet admin schema) pass them explicitly. register() never does.
        user_info.setdefault("is_superuser", False)
        user_info.setdefault("is_active", True)

        async with in_transaction() as conn:
            query = Q(username=user_info["username"])
            if user_info.get("email") is not None:
                query |= Q(email=user_info["email"])
            existing = await cls.filter(query).using_db(conn).first()
            if existing:
                if existing.username == user_info["username"]:
                    raise TargetObjectAlreadyExist(message="username or email already exists")
                if user_info.get("email") is not None and existing.email == user_info["email"]:
                    raise TargetObjectAlreadyExist(message="username or email already exists")
            roles = await Role.filter(name__in=role_names).using_db(conn) if role_names else []

            user_orm = cls(**user_info)
            try:
                await user_orm.save(using_db=conn)
            except IntegrityError:
                raise TargetObjectAlreadyExist(message="username or email already exists") from None
            if roles:
                await user_orm.roles.add(*roles, using_db=conn)

            return user_orm

    def check_active(self):
        return getattr(self, "is_active", True)

    async def update_user_last_login(self) -> None:
        """Record successful login time without rewriting unrelated columns."""
        self.last_login = tortoise_timezone_now()
        await self.save(update_fields=["last_login"])


class OAuthAccount(TorModel):
    provider = fields.CharField(max_length=20)  # "github" / "google" / ...
    provider_user_id = fields.CharField(max_length=100)  # user id
    user = fields.ForeignKeyField(User, related_name="oauth_accounts", on_delete=fields.CASCADE)

    class Meta:
        table = "auth_oauth_accounts"
        unique_together = (("provider", "provider_user_id"),)


class RefreshToken(TorModel):
    """Persisted JWT refresh token (one active row per user; login replaces it)."""

    user = fields.ForeignKeyField(User, related_name="refresh_tokens", on_delete=fields.CASCADE, unique=True)
    token = fields.CharField(max_length=512, null=False)
    expires_at = fields.DatetimeField(null=False)
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "auth_refresh_token"
