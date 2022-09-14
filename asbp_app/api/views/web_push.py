import os

from sanic.exceptions import NotFound
from web_foundation.environment.workers.web.ext.request_handler import InputContext
from web_foundation.environment.workers.web.utils.access import exec_access

from asbp_app.container import AppContainer
from asbp_app.enviroment.event.event import NotifyVisitorInBlackListEvent
from asbp_app.enviroment.infrastructure.database.access_loaders import *


async def notify_all_handler(context: InputContext[service_dto.ClaimDto.ApproveDto, UserIdentity],
                                container: AppContainer):
    return await container.web_push_service.notify_all(context.dto)
