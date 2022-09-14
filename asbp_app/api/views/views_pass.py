from web_foundation.environment.workers.web.ext.request_handler import InputContext

from asbp_app.container import AppContainer
from asbp_app.enviroment.service.pass_service import PassService


async def create_qr_code(context: InputContext, container: AppContainer):
    return await container.pass_service.create_qr_code(entity=context.r_kwargs.get('pass_id'))


async def create_barcode(context: InputContext, container: AppContainer):
    return await container.pass_service.create_barcode(entity=context.r_kwargs.get('pass_id'))
