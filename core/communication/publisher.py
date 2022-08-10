from pyee.asyncio import AsyncIOEventEmitter

from core.communication.event import Event
from core.communication.subscriber import Subscriber


class Publisher:
    subscribers: set[Subscriber]
    _emitter: AsyncIOEventEmitter

    def __init__(self, emitter: AsyncIOEventEmitter):
        self._emitter = emitter

    def notify(self, event: Event):
        self._emitter.emit(event.name, event)
