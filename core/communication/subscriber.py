from pyee.asyncio import AsyncIOEventEmitter
from typing import Union, Callable, Coroutine, TypeVar, List

Handler = TypeVar(name="Handler", bound=Union[Callable, Coroutine])


class Subscriber:
    _emitter: AsyncIOEventEmitter

    def __init__(self, emitter: AsyncIOEventEmitter):
        self._emitter = emitter

    def set_listener(self, name: str, handler: Handler):
        self._emitter.on(name, handler)

    def set_all_listener(self, names: List[str], handler: Handler):
        for name in names:
            self._emitter.on(name, handler)
