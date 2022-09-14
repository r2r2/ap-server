import os

from sanic.exceptions import NotFound
from web_foundation.environment.workers.web.ext.request_handler import InputContext
from web_foundation.environment.workers.web.utils.access import exec_access

from asbp_app.api.dto.service import ClaimDto
from asbp_app.container import AppContainer
from asbp_app.enviroment.infrastructure.database.access_loaders import *



async def claim_approve_handler(context: InputContext[ClaimDto.ApproveDto, UserIdentity],
                                container: AppContainer):
    model = await container.claim_service.system_user_approve_claim(context.identity.user,
                                                                    context.r_kwargs.get("claim_id"),
                                                                    context.dto)  # type: ignore
    return await model.values_dict()


async def claim_excel_handler(context: InputContext, container: AppContainer):
    match context.request.method:
        case "GET":
            with open(f"{os.getcwd()}/static/sample_excel.txt", "rb") as f:  # TODO rewrite with repo
                data = f.read().decode(encoding="utf-8")
                return data
        case "POST":
            return await container.claim_service.upload_excel(context.dto)
