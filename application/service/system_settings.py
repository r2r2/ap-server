from tortoise.transactions import atomic

import settings
from application.exceptions import InconsistencyError
from application.service.base_service import BaseService
from core.dto.service import SystemSettingsDto
from infrastructure.database.models import SystemSettings, SystemUser


class SystemSettingsService(BaseService):
    target_model = SystemSettings

    @atomic(settings.CONNECTION_NAME)
    async def update(self, alter_user: SystemUser, dto: SystemSettingsDto) -> SystemSettings:
        sys_settings = await SystemSettings.get_or_none(id=1)
        if sys_settings is None:
            raise InconsistencyError(message=f"SystemSettings can't be None.")
        for field, value in dto.dict().items():
            if value:
                setattr(sys_settings, field, value)

        await sys_settings.save()
        return sys_settings
