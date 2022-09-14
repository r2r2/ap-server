import asyncio
import sys
from enum import Enum
from pathlib import Path

import loguru
# from loguru import logger
from sanic_ext.extensions.openapi.constants import SecuritySchemeType, SecuritySchemeLocation
from web_foundation.environment.resources.file_repo.system_repo import SystemFileRepository
from web_foundation.environment.workers.web.ext.addons_loader import AddonsLoader, ApiAddon
from web_foundation.environment.workers.web.ext.request_handler import ChainRequestHandler
from web_foundation.environment.workers.web.ext.router import DictRouter
from web_foundation.environment.workers.web.worker import create_io_workers, HttpServer, create_rt_subscribes
from web_foundation.utils.helpers import load_config
from web_foundation.utils.logger import setup_loggers
from web_foundation import settings
from web_foundation.environment.app import App

from asbp_app.config import Config
from asbp_app.container import AppContainer
from asbp_app.routes_dict import routes_dict


# from pqueue_app.utils.sdk.sdk_gen import SDKGenerator
# from source.core.server.server import Server
# from source.config.config import get_config
# from source.core.utils.loggining import logger
# import argparse

class FileSections(Enum):
    REPORTS = "reports"
    CONFIG = "config"
    LOGS = "logs"
    PLUGINS = "plugins"


class AddonsExt(AddonsLoader):  # TODO check company on exec plugin
    pass
    # async def configure_middleware(self, plugin: ApiAddon, *args, **kwargs) -> ApiAddon:
    #     db_plugin = await DBPlugin.get_or_none(filename=plugin.filename)
    #     if not db_plugin:
    #         loguru.logger.warning(f"Plugin {plugin.filename} not found in database")
    #         plugin.enabled = False
    #         plugin.name = "undefined"
    #         return plugin
    #     plugin.name = f"{db_plugin.name}{db_plugin.company_id}"
    #     plugin.target = db_plugin.entrypoint
    #     plugin.enabled = db_plugin.enabled
    #     loguru.logger.warning(f"plugin {plugin.name} target={plugin.target} enabled={plugin.enabled}")
    #     return plugin


async def main():
    settings.DEBUG = True
    settings.METRICS_ENABLE = True
    settings.EVENTS_METRIC_ENABLE = True

    repo = SystemFileRepository(Path("applied_files"), FileSections)
    conf = load_config(Path("./applied_files/config/config.json"), Config)
    setup_loggers(conf.logger)

    container = AppContainer(app_config=conf, router=routes_dict, file_repository=repo)
    await container.init_resources()
    # await plugin_manager.discover_middleware()
    # api_addons_loader = EQPluginExt(sections=EQFileSections)
    await container.shutdown_resources()
    router = DictRouter[ChainRequestHandler](routes_dict, ChainRequestHandler)
    asbp_app = App(container)
    workers = create_io_workers(HttpServer, config=container.app_config().server, router=router,
                                api_addons_loader=AddonsExt())
    for worker in workers:
        worker.sanic_app.ext.openapi.add_security_scheme("cookieAuth",
                                                         type=SecuritySchemeType.API_KEY,
                                                         location=SecuritySchemeLocation.COOKIE,
                                                         name="token")
    # create_rt_subscribes(*workers, event_type=[OperatorEvent, OfficeToolEvent],
    #                      resolve_callback=resolve_send_operator_event,
    #                      use_nested_classes=True)
    asbp_app.add_worker(workers)
    asbp_app.add_service(container.auth_service)
    asbp_app.add_service(container.claim_service)
    asbp_app.add_service(container.web_push_service)
    # asbp_app.add_service(container.metrics_service)
    setup_loggers(conf.logger)
    await asbp_app.run()


if __name__ == '__main__':
    """
    pre requirements: 
    Redis: 
        - install
        - redis-cli : CONFIG SET notify-keyspace-events KEA
    """

    # parser = argparse.ArgumentParser(description='PYTHON CORE SERVER')
    # parser.add_argument('--generate',
    #                     type=str,
    #                     help='Language to generate lib')
    # parser.add_argument('--output',
    #                     type=str,
    #                     default="./sdk",
    #                     help='Path to generate lib, default is ./ci/sdk')
    # args = parser.parse_args()
    if len(sys.argv) == 1:
        asyncio.run(main())
        exit(0)
    # if not os.path.isdir(args.output):
    #     logger.warning("Please pass path like folder [--output <folder> default ./sdk]")
    #     exit(-1)
    # if args.generate not in ["js", "dart"]:
    #     logger.warning("Please pass language to generate from [js,dart]")
    #     exit(-1)
    # generator = SDKGenerator(args.generate, args.output)
    # generator.create_sdk()
