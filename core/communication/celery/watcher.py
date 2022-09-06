from celery.exceptions import SoftTimeLimitExceeded, TaskRevokedError
from pyee.asyncio import AsyncIOEventEmitter

from core.communication.celery.tasks import (parking_time_exceeded,
                                             send_email_before_n_minutes,
                                             send_email_celery, send_webpush)
from core.communication.event import (Event, MaxParkingTimeHoursExceededEvent,
                                      NotifyUsersInClaimWayBeforeNminutesEvent,
                                      SendWebPushEvent)
from core.communication.subscriber import Subscriber
from core.utils.loggining import logger


class CeleryEventWatcher(Subscriber):

    def __init__(self, emitter: AsyncIOEventEmitter):
        super().__init__(emitter)
        self.set_listener("visitor_in_black_list", self.send_email_events)
        self.set_listener("users_in_claimway", self.send_email_events)
        self.set_listener("users_in_claimway_before_N_minutes", self.send_email_before_n_minutes_event)
        self.set_listener("max_parking_time_hours_exceeded", self.max_parking_time_hours_event)
        self.set_listener("webpush_event", self.webpush_event)

    @staticmethod
    async def send_email_events(event: Event):
        try:
            send_email_celery.delay(await event.to_celery())
        except send_email_celery.OperationalError as exc:
            logger.exception(f'Sending task raised: {exc}')
        except SoftTimeLimitExceeded as ex:
            logger.exception(ex)

    @staticmethod
    async def send_email_before_n_minutes_event(event: NotifyUsersInClaimWayBeforeNminutesEvent):
        time_to_send, time_to_expire = await event.extract_time()
        try:
            if all((time_to_send, time_to_expire)):
                send_email_before_n_minutes.apply_async((await event.to_celery(),),
                                                        eta=time_to_send,
                                                        # expires=time_to_expire
                                                        )
        except send_email_before_n_minutes.OperationalError as exc:
            logger.exception(f'Sending task raised: {exc}')
        except SoftTimeLimitExceeded as ex:
            logger.exception(ex)
        except TaskRevokedError as e:
            logger.exception(f"Task has reached expiration time:{time_to_expire}.", e)

    @staticmethod
    async def max_parking_time_hours_event(event: MaxParkingTimeHoursExceededEvent):
        time_to_send = await event.extract_time()
        try:
            if time_to_send:
                parking_time_exceeded.apply_async((await event.to_celery(),),
                                                  eta=time_to_send)
        except parking_time_exceeded.OperationalError as exc:
            logger.exception(f'Sending task raised: {exc}')
        except SoftTimeLimitExceeded as ex:
            logger.exception(ex)

    @staticmethod
    async def webpush_event(event: SendWebPushEvent):
        try:
            send_webpush.delay(await event.to_celery())
        except send_webpush.OperationalError as exc:
            logger.exception(f'Sending task raised: {exc}')
        except SoftTimeLimitExceeded as ex:
            logger.exception(ex)
