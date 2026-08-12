import bcrypt
from tortoise import fields
from tortoise.models import Model as TorModel
from tortoise.transactions import in_transaction

from srf.exceptions import TargetObjectAlreadyExist


class Role(TorModel):
    id = fields.BigIntField(pk=True, generated=True)
    name = fields.CharField(max_length=256, null=False)
    description = fields.CharField(max_length=256, null=False)

    class Meta:
        table = "auth_role"


class User(TorModel):
    id = fields.BigIntField(primary_key=True, generated=True)
    name = fields.CharField(max_length=64, null=False)
    password = fields.CharField(max_length=128, null=True)
    role = fields.ForeignKeyField("models.Role", on_delete=fields.SET_DEFAULT)
    is_active = fields.BooleanField(default=True, null=False)
    email = fields.CharField(max_length=256, null=False, unique=True)
    last_login = fields.DatetimeField(auto_now_add=True, null=False)
    date_joined = fields.DatetimeField(auto_now_add=True, null=False)
    create_time = fields.DatetimeField(auto_now_add=True, read_only=True)
    update_time = fields.DatetimeField(auto_now=True, null=True)

    refresh_tokens: fields.ReverseRelation["RefreshToken"]

    class Meta:
        table = "auth_user"

    def verify_password(self, password: str) -> bool:
        if self.password is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    async def create_user(cls, user_info: dict) -> "User":
        """
        Do not override Tortoise's create method,
        create user with hashed password and role resolution.
        """
        user_info = dict(user_info)
        user_info.pop("id", None)
        user_info["password"] = cls.hash_password(user_info["password"])

        async with in_transaction() as conn:
            if await cls.filter(email=user_info["email"]).using_db(conn).exists():
                raise TargetObjectAlreadyExist(message="user already exists")

            role = await Role.filter(name=user_info.pop("role_name", "user")).using_db(conn).first()
            if not role:
                raise ValueError("Role not found. Please ensure the role you chooseexists in the database.")

            user_orm = cls(**user_info, role=role)
            await user_orm.save(using_db=conn)
            return user_orm


class UserRoles(TorModel):
    id = fields.BigIntField(pk=True, generated=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    role = fields.ForeignKeyField("models.Role", on_delete=fields.SET_DEFAULT)

    class Meta:
        table = "auth_user_role"


class RefreshToken(TorModel):
    """Persisted JWT refresh token (one active row per user; login replaces it)."""

    id = fields.BigIntField(pk=True, generated=True)
    user = fields.ForeignKeyField("models.User", related_name="refresh_tokens", on_delete=fields.CASCADE)
    token = fields.CharField(max_length=512, null=False)
    expires_at = fields.DatetimeField(null=False)
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "auth_refresh_token"
