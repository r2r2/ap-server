import asyncio
import aioredis
from multiprocessing import Process
from orjson import loads
from pyee.asyncio import AsyncIOEventEmitter
from sanic import Sanic
from sanic_openapi import openapi3_blueprint
from tortoise.contrib.sanic import register_tortoise

import settings
from application.service.service_registry import ServiceRegistry
from application.access.access_registry import AccessRegistry
from application.service.scope_constructor import EnabledScopeSetter
from application.service.asbp_archive import init_archive_routes
from application.service.web_push import init_web_push
from config.config import Config
from core.server.routes import BaseServiceController
from core.utils.loggining import LogsHandler, logger
from core.server.sse_monitoring import init_sse_monitoring
from core.utils.license_count import LicenseCounter
from core.utils.mysignals import MySignalHandler
from core.utils.orjson_default import odumps
from core.errors.error_handler import ExtendedErrorHandler
from core.server.auth import init_auth
from core.server.controllers import BaseAccessController
from core.communication.celery.celery_ import celery
from core.communication.celery.watcher import CeleryEventWatcher
from infrastructure.database.connection import sample_conf, init_database_conn
from infrastructure.database.init_db import setup_db
from ci.openapi.openapi import SanicRoutesFormatter, overwrite_swagger_route


class Server:

    def __init__(self, app_config: Config):
        self.celery = celery
        self.emitter = AsyncIOEventEmitter()
        self._app_config = app_config
        self.sanic_app = Sanic('app', dumps=odumps, loads=loads)
        self._set_error_handler()
        self._configure_app()
        LogsHandler.setup_loggers()
        self._init_extentions()
        self._register_api()
        self._setup()
        self._set_listeners()
        self._configure_openapi()
        MySignalHandler(self.sanic_app)
        # self._init_celery()

    def _setup(self):
        async def _set_db():

            conn, conn_archive = await init_database_conn()
            await setup_db(conn, self.sanic_app, conn_archive)

            await conn.close()
            await conn_archive.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_set_db())

    def _configure_app(self):
        self.sanic_app.update_config(settings.SanicConfig)

    def _set_error_handler(self):
        self.sanic_app.error_handler = ExtendedErrorHandler()

    async def setup_worker_context(self, app: Sanic, loop: asyncio.AbstractEventLoop):
        await EnabledScopeSetter().set_en_sc()
        await LicenseCounter.activate()
        CeleryEventWatcher(self.emitter)
        app.ctx.config = self._app_config
        app.ctx.service_registry = ServiceRegistry(self.emitter)
        app.ctx.access_registry = AccessRegistry()

    def _configure_openapi(self):
        op3 = openapi3_blueprint
        op3.name = "swagger"
        overwrite_swagger_route(op3)
        self.sanic_app.blueprint(op3)

        SanicRoutesFormatter(self.sanic_app).create_sanic_js()

    def _set_listeners(self):
        self.sanic_app.register_listener(self.setup_worker_context, "before_server_start")
        self.sanic_app.register_listener(self.setup_redis, "before_server_start")
        register_tortoise(self.sanic_app, sample_conf)

    async def setup_redis(self, app, _):
        app.ctx.redis = aioredis.Redis.from_url(self._app_config.redis.url, decode_responses=True)

    def _init_celery(self):
        def _start_celery():
            self.celery.start(settings.CELERY_STARTUP_PARAMS)

        def _start_celery_beat():
            self.celery.start(settings.CELERY_BEAT_STARTUP_PARAMS)

        def _start_flower():
            self.celery.start(settings.FLOWER_STARTUP_PARAMS)

        Process(target=_start_celery, name='celery').start()
        Process(target=_start_celery_beat, name='celery_beat').start()
        Process(target=_start_flower, name='flower').start()

    def _init_extentions(self):
        init_auth(self.sanic_app)
        init_sse_monitoring(self.sanic_app)
        init_archive_routes(self.sanic_app)
        init_web_push(self.sanic_app)

    def _register_api(self):

        for controller in BaseServiceController.__subclasses__():
            self.sanic_app.add_route(controller.as_view(), controller.target_route)

        for controller in BaseAccessController.__subclasses__():
            self.sanic_app.add_route(controller.as_view(),
                                     f'/{controller.entity_name}')
            self.sanic_app.add_route(controller.as_view(),
                                     f"/{controller.entity_name}/<entity:{controller.identity_type.__name__}>")

        logger.info("Registered routes:")
        for route in self.sanic_app.router.routes:
            logger.info(f"> /{route.path}")

    def run(self):
        self.sanic_app.go_fast(host=settings.SANIC_HOST,
                               port=settings.SANIC_PORT,
                               debug=settings.SANIC_DEBUG,
                               fast=settings.SANIC_FAST,
                               workers=settings.SANIC_WORKERS,
                               )

