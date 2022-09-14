from dataclasses import dataclass

from sanic import Request
from web_foundation.environment.workers.web.ext.request_handler import ProtectIdentity

from asbp_app.enviroment.infrastructure.database.models import SystemUserSession, SystemUser


@dataclass
class UserIdentity(ProtectIdentity):
    user: SystemUser
    session: SystemUserSession


async def user_protector(request: Request, container):
    user, payload, session = await container.auth_service.validate_request(request, SystemUserSession)
    await container.auth_service.check_scopes(request, user)
    return UserIdentity(user=user, session=session)
