from sanic.exceptions import NotFound
from web_foundation.environment.workers.web.ext.request_handler import InputContext

from asbp_app.container import AppContainer
from asbp_app.enviroment.infrastructure.database.access_loaders import *


async def get_visit_info(context: InputContext, container: AppContainer):
    return await container.visitor_service.get_info_about_current_visit(context.r_kwargs.get("visitor_id"))
