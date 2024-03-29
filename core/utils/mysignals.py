from typing import Optional, Type

import aioredis
from sanic import Sanic
from tortoise import BaseDBAsyncClient
from tortoise.signals import post_save

import settings
from application.service.asbp_archive import ArchiveController
from application.service.web_push import WebPushController
from core.server.controllers import BaseAccessController
from core.server.routes import BaseServiceController
from core.server.sse_monitoring import (StrangerThingsController,
                                        StrangerThingsEventsController)
from core.utils.orjson_default import odumps
from infrastructure.database.models import StrangerThings


class MySignalHandler:

    def __init__(self, app: Sanic):
        app.add_signal(handler=self.enabled_scopes_signal_handler, event="controller.enabled_scopes.changed")

    @staticmethod
    async def enabled_scopes_signal_handler(**context) -> None:
        """
        After changing scopes in ScopeConstructorAccess.update(),
        changing enabled_scopes in appropriate Controller.
        """
        for controller in BaseAccessController.__subclasses__():
            if controller.entity_name == context["enable_scope_name"]:
                setattr(controller, "enabled_scopes", context["scopes"])
                return

        for controller in BaseServiceController.__subclasses__():
            if controller.target_route == context["enable_scope_name"]:
                setattr(controller, "enabled_scopes", context["scopes"])
                return

        controllers = (
            StrangerThingsEventsController,
            StrangerThingsController,
            ArchiveController,
            WebPushController.Subscription,
            WebPushController.NotifyAll,
        )

        for controller in controllers:
            setattr(controller, "enabled_scopes", context["scopes"])
            return

    @staticmethod
    @post_save(StrangerThings)
    async def signal_post_save(
            sender: "Type[StrangerThings]",
            instance: StrangerThings,
            created: bool,
            using_db: "Optional[BaseDBAsyncClient]",
            update_fields: list[str],
    ) -> None:
        data = odumps(await instance.values_dict())
        red = await aioredis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        await red.publish(settings.STRANGER_THINGS_EVENTS_KEY, data)
        await red.close()



