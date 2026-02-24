from typing import Dict

import bcrypt
from tortoise import exceptions, fields
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
    async def create(cls, user_info: Dict) -> "User":
        """
        Override Tortoise's create: create user with hashed password and role resolution.
        """
        user_info = dict(user_info)
        user_info.pop("id", None)
        user_info["password"] = cls.hash_password(user_info["password"])
        async with in_transaction() as conn:
            role = await Role.filter(name=user_info.pop("role_name", "user")).using_db(conn).first()
            if not role:
                raise ValueError("Role 'user' not found. Please ensure the role exists in the database.")
            user_db = cls(**user_info, role=role)
            try:
                user_db = await user_db.save(using_db=conn)
            except exceptions.IntegrityError:
                raise TargetObjectAlreadyExist(message="user already exists")
            return user_db


class UserRoles(TorModel):
    id = fields.BigIntField(pk=True, generated=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE)
    role = fields.ForeignKeyField("models.Role", on_delete=fields.SET_DEFAULT)

    class Meta:
        table = "auth_user_role"
