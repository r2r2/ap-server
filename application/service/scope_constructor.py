from typing import Type, TypeVar
from tortoise.queryset import Q
from sanic import Sanic

from infrastructure.database.models import EnableScope, Role
from core.server.controllers import BaseAccessController
from core.server.routes import BaseServiceController
from core.server.sse_monitoring import StrangerThingsEventsController, StrangerThingsController
from application.service.asbp_archive import ArchiveController
from application.service.web_push import WebPushController
from application.exceptions import InconsistencyError


C = TypeVar("C",
            Type[BaseAccessController],
            Type[BaseServiceController],
            Type[StrangerThingsEventsController],
            Type[StrangerThingsController],
            Type[ArchiveController],
            Type[WebPushController],
            )


async def init_scopes(app: Sanic) -> None:
    """
    Creates initial scopes in setup_db() for every registered route.
    Executes only once while first DB initialization.
    """
    app_routes = app.router.routes
    roles = await Role.filter(Q(name="root") | Q(name="Администратор"))
    for route in app_routes:
        if route.path not in ("set-scopes", "set-scopes/<entity:int>", "auth", "system-settings"):
            en_sc = await EnableScope.create(name=route.path)
            await en_sc.scopes.add(*roles)


class EnabledScopeSetter:
    """
    After reloading Server
    sets cls.enabled_scopes in Controllers
    to appropriate scope from EnableScope.
    "root" & "Администратор" will be set for all controllers.
    """

    async def set_en_sc(self):
        for controller in BaseAccessController.__subclasses__():
            if controller.entity_name not in ("set-scopes", "set-scopes/<entity:int>"):
                await self.set_scopes(controller.entity_name, controller)

        for controller in BaseServiceController.__subclasses__():
            if controller.target_route not in ("/auth", "/system-settings"):
                await self.set_scopes(controller.target_route[1:], controller)

        controllers = {
            StrangerThingsEventsController: ("stranger-things-sse",),
            StrangerThingsController: ("stranger-things", "stranger-things/<entity:int>"),
            ArchiveController: ("archive", "archive/<entity:int>"),
            WebPushController.Subscription: ("wp/subscription", "wp/subscription/<entity:int>"),
            WebPushController.NotifyAll: ("wp/notify-all",),
        }
        for controller, routes in controllers.items():
            for route in routes:
                await self.set_scopes(route, controller)

    @staticmethod
    async def set_scopes(name: str, controller: C) -> None:
        en_sc = await EnableScope.get_or_none(name=name).prefetch_related("scopes")
        if en_sc is None:
            raise InconsistencyError(message=f"There is no scope with name: {name}")
            # TODO remove creation in prod
            # en_sc = await EnableScope.create(name=name)
        enable_scopes = await en_sc.scopes.all()
        setattr(
            controller,
            "enabled_scopes",
            list(set([scope.name for scope in enable_scopes] + ["root", "Администратор"]))
        )
