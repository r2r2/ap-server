from web_foundation.environment.container import AppDependencyContainer
from web_foundation.kernel.abstract.dependency import Dependency

from asbp_app.enviroment.resources.database import AsbpDatabaseResource
from asbp_app.enviroment.service.auth import AuthService
from asbp_app.enviroment.service.claim import ClaimService
from asbp_app.enviroment.service.visitor import VisitorService
from asbp_app.enviroment.service.web_push import WebPushService
from asbp_app.enviroment.service.pass_service import PassService


class EnvConf:
    SECRET = "SECRET"
    USE_UVLOOP = True
    TOKEN_LIVE_TIME = 999999999


class AppContainer(AppDependencyContainer):
    router = Dependency(instance_of=dict)
    database = AsbpDatabaseResource(modules=["asbp_app.enviroment.infrastructure.database.models"], router=router)
    auth_service = AuthService(EnvConf.SECRET, EnvConf.TOKEN_LIVE_TIME)
    claim_service = ClaimService()
    web_push_service = WebPushService()
    pass_service = PassService()
    visitor_service = VisitorService()

