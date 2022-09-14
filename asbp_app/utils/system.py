from asbp_app.enviroment.infrastructure.database.models import SystemSettingsTypes, SystemSettings, \
    system_settings_type_typing
from datetime import time as d_time


async def get_system_settings(setting_name: SystemSettingsTypes):
    setting = await SystemSettings.get(name=setting_name)
    value_type = system_settings_type_typing.get(setting_name)
    if value_type == d_time:
        v = d_time.fromisoformat(setting.value)
    else:
        v = value_type(setting.value)
    return v
