import asyncio
import io
import itertools
from aioredis.client import PubSub
from aioredis import Redis
from sanic.views import HTTPMethodView
from sanic import Sanic, Request, HTTPResponse, json
from typing import Optional, Union, List
from sanic.response import ResponseStream
from sanic.exceptions import NotFound
from pydantic import BaseModel

import settings
from application.exceptions import InconsistencyError
from infrastructure.database.models import StrangerThings, SystemUser
from infrastructure.database.layer import DbLayer
from core.server.auth import protect
from core.utils.loggining import logger
from core.dto.access import EntityId


class BaseField(str):
    name: str

    def __str__(self) -> str:
        return f"{self.name}: {super().__str__()}\r\n"


class Event(BaseField):
    name = "event"


class Data(BaseField):
    name = "data"


class ID(BaseField):
    name = "id"


class Retry(BaseField):
    name = "retry"


class Message(list):
    cnt = itertools.count(1)

    def __init__(self, *fields: BaseField) -> None:
        fields += (ID(Message.cnt.__next__()),)
        self.extend(fields)

    def __str__(self) -> str:
        return "".join(map(str, self)) + "\r\n\r\n"


class SseEventProtocol(BaseModel):
    data: str

    def _prepare(self):
        buffer = io.StringIO()
        buffer.write(self.data)
        return buffer.getvalue()

    @property
    def to_send(self):
        return self._prepare()

    @staticmethod
    async def ping_event():
        data = "id: 0\r\nevent: :ping\r\n\r\n"
        return SseEventProtocol(data=data).to_send


class StrangerThingsEventsController(HTTPMethodView):
    enabled_scopes = ["Сотрудник службы безопасности"]

    @protect()
    async def get(self, request: Request, system_user: SystemUser):
        conf = request.app.ctx.config.streaming
        watcher: Redis = request.app.ctx.redis
        my_key = settings.STRANGER_THINGS_EVENTS_KEY
        pubsub: PubSub = watcher.pubsub()

        async def sent_ping(response: ResponseStream):

            sent = await SseEventProtocol.ping_event()
            while True:
                logger.debug(f"SSE Ping to {request.ip}")
                await asyncio.sleep(conf.ping_timeout)
                try:
                    await response.write(sent)
                    await response.eof()
                except:
                    return

        async def streaming_fn(response: ResponseStream):
            ping_task = request.app.loop.create_task(sent_ping(response))
            await pubsub.subscribe(my_key)

            try:
                while True:
                    data = await pubsub.get_message(ignore_subscribe_messages=True, timeout=conf.listen_timeout)
                    if data:
                        msg = Message(Event("message"), Data(data["data"])).__str__()
                        sending_data = SseEventProtocol(data=msg).to_send
                        await response.write(sending_data)
                        await response.eof()
                    await asyncio.sleep(conf.listen_timeout)
            except Exception as e:
                logger.warning(f"Sse disconnect with crash {e}")
            finally:
                ping_task.cancel()
                await pubsub.close()
                logger.debug(f"Sse on {request.ip} disconnected, task canceled")

        headers = {"Cache-Control": "no-cache", "keep-alive": "timeout=500, max=100000"}
        return ResponseStream(streaming_fn, headers=headers, content_type="text/event-stream; charset=utf-8")


class StrangerThingsController(HTTPMethodView):
    target_model = StrangerThings
    enabled_scopes = ["Сотрудник службы безопасности"]

    @protect()
    async def get(self, request: Request, system_user: SystemUser, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None
            models = await self.read_all(limit, offset)
            return json([await model.values_dict(m2m_fields=True) for model in models])

        model = await self.read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True))
        else:
            raise NotFound()

    async def read_all(self,
                       limit: int = None,
                       offset: int = None) -> Union[List[StrangerThings], StrangerThings]:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)  # type: ignore
        query = self.target_model.all().prefetch_related(*related_fields)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return await query

    async def read(self, _id: EntityId) -> StrangerThings:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)  # type: ignore
        return await self.target_model.get_or_none(id=_id).prefetch_related(*related_fields)

    @protect()
    async def post(self, request: Request, system_user: SystemUser):
        raise InconsistencyError(message="POST method is not allowed.")


def init_sse_monitoring(app: Sanic):
    app.add_route(StrangerThingsEventsController.as_view(), "/stranger-things-sse")
    app.add_route(StrangerThingsController.as_view(), "/stranger-things")
    app.add_route(StrangerThingsController.as_view(), "/stranger-things/<entity:int>")
