import asyncio
import os
from functools import wraps
import importlib.util
from loguru import logger
from typing import List
from types import ModuleType

from infrastructure.database.models import Plugin

#TODO move to config
PLUGINS_DIRNAME = "plugins"


class AddPlugins:

    def __init__(self, *args, **kwargs):
        pass

    async def get_plugins_from_db(self, func_name) -> List[Plugin]:
        return await Plugin.filter(entrypoint=func_name)

    def get_plugin_filepath(self, plugin: Plugin) -> str:
        return os.path.join(os.getcwd(), PLUGINS_DIRNAME, plugin.filename)

    def plugin_exist(self, plugin: Plugin) -> bool:
        if os.path.exists(self.get_plugin_filepath(plugin)):
            return True
        return False

    def import_plugin(self, plugin: Plugin):
        try:
            spec = importlib.util.spec_from_file_location(plugin.name,
                                                          self.get_plugin_filepath(plugin))
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)
            return imported
        except Exception as e:
            logger.error(f"Can't import plugin \"{plugin.name}\". Exception: {e}")

    async def run_plugin(self, imported_plugin: ModuleType, *func_args, result=None,
                         after=False, **func_kwargs):
        try:
            if after and hasattr(imported_plugin, "after"):
                if asyncio.iscoroutine(imported_plugin.after):
                    await imported_plugin.after(*func_args, result=result, **func_kwargs)
                else:
                    imported_plugin.after(*func_args, result=result, **func_kwargs)
            elif hasattr(imported_plugin, "before"):
                if asyncio.iscoroutine(imported_plugin.before):
                    await imported_plugin.before(*func_args, **func_kwargs)
                else:
                    imported_plugin.before(*func_args, **func_kwargs)
        except Exception as e:
            logger.error(f"Can't run plugin \"{imported_plugin.__name__}\". Exception: {e}")

    def __call__(self, func):
        @wraps(func)
        async def func_with_plugins(*args, **kwargs):

            plugins_for_func = await self.get_plugins_from_db(func.__name__)
            after_plugins = []
            for plugin in plugins_for_func:
                if not plugin.enabled:
                    continue
                if not self.plugin_exist(plugin):
                    logger.error(f"For plugin \"{plugin.name}\" file \"{plugin.filename}\" not found")
                    continue

                imported_plugin = self.import_plugin(plugin)
                if imported_plugin and hasattr(imported_plugin, "after"):
                    after_plugins.append(imported_plugin)
                elif imported_plugin and hasattr(imported_plugin, "before"):
                    await self.run_plugin(imported_plugin, *args, **kwargs)

            result = await func(*args, **kwargs)

            for imported_plugin in after_plugins:
                await self.run_plugin(imported_plugin, *args, result=result, after=True, **kwargs)

            return result
        return func_with_plugins
