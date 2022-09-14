import asyncio
import io
import itertools

from aioredis import Redis
from aioredis.client import PubSub
from loguru import logger
from pydantic import BaseModel

from sanic import Request, Sanic
from sanic.response import ResponseStream
from sanic.views import HTTPMethodView

from asbp_app import settings
from asbp_app.enviroment.infrastructure.database.models import SystemUser


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
        super().__init__()
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


    async def get(self, request: Request, system_user: SystemUser) -> ResponseStream:
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


def init_sse_monitoring(app: Sanic):
    app.add_route(StrangerThingsEventsController.as_view(), "/stranger-things-sse", methods=["GET"])
