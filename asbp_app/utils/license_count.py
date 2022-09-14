from typing import Type

from asbp_app.enviroment.infrastructure.database.models import AbstractDbModel, SystemUser, SystemSettingsTypes
from asbp_app.utils.system import get_system_settings


class LicenseCounter:
    """Счетчик кол-ва активных лицензий"""
    target_model: Type[AbstractDbModel]
    role_count: int

    @classmethod
    async def activate(cls):
        await SysUserLicenses.get_count()

    @classmethod
    async def get_count(cls) -> int:
        cls.role_count = await cls.target_model.filter(deleted=False).count()
        return cls.role_count

    @classmethod
    async def increment_count(cls) -> None:
        cls.role_count += 1

    @classmethod
    async def decrement_count(cls) -> None:
        cls.role_count -= 1

    @classmethod
    async def available_license(cls):
        return NotImplementedError()


class SysUserLicenses(LicenseCounter):
    target_model = SystemUser
    role_count: int

    @classmethod
    async def available_license(cls) -> int:
        licenses: int = await get_system_settings(SystemSettingsTypes.MAX_USER_LICENSE)
        return licenses - cls.role_count
