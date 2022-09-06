import asyncio
from typing import Union

from celery import Task
from celery.worker.request import Request
from tortoise.queryset import Q

from application.service.asbp_archive import ArchiveController
from application.service.parking import ParkingTimeslotService
from application.service.web_push import WebPushController
from core.communication.celery.celery_ import celery
from core.communication.celery.sending_emails import _send_email
from core.dto.service import EmailStruct, WebPush
from core.utils.loggining import logger
from infrastructure.database.models import (Claim, ClaimWay, ParkingTimeslot,
                                            SystemUser)


class MyRequest(Request):
    """A minimal custom request to log failures and hard time limits."""

    def on_timeout(self, soft, timeout):
        super().on_timeout(soft, timeout)
        if not soft:
            logger.warning(
                f'A hard timeout was enforced for task {self.task.name}'
            )

    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
        super().on_failure(
            exc_info,
            send_failed_event=send_failed_event,
            return_ok=return_ok
        )
        logger.warning(
            f'Failure detected for task {self.task.name}'
        )


class MyTask(Task):
    Request = MyRequest
    max_retries = 5
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_jitter = True


@celery.task(base=MyTask, name="~Send Email~")
def send_email_celery(data: EmailStruct) -> None:
    """Calling an async func for sending mails"""
    asyncio.get_event_loop().run_until_complete(_send_email(data))


@celery.task(base=MyTask, name="~Before N minutes~")
def send_email_before_n_minutes(data: EmailStruct) -> None:
    """
    autoretry fails when expires is set:
    raised TypeError: '<' not supported between instances of 'str' and 'int'

    Possible to fix it in source code of Celery:
    https://github.com/celery/celery/issues/7091
    https://github.com/celery/celery/pull/7109/files
    """
    """
    Collecting users, who didn't approve Claim.
    """

    async def collect_users_who_not_approved() -> None:
        """
        Change EmailStruct.email depends on users who not approved yet.
        If everyone reacts (approved==True or approved==False) than no need to send notifications.
        """
        data.email.clear()
        sys_users = await SystemUser.filter(
            Q(claim_way_approval__approved=None) & Q(claim_way_approval__claim=data.claim)
        )
        if data.claim_way_2:
            claim: Claim = await Claim.get_or_none(id=data.claim).prefetch_related("claim_way_2")
            if claim.claim_way_approved:
                claim_way = await ClaimWay.get_or_none(id=claim.claim_way_2.id)
                sys_users = await claim_way.system_users.all().filter(
                    Q(claim_way_approval__approved=None) & Q(claim_way_approval__claim=data.claim)
                )
        [data.email.append(user.email) for user in sys_users]
        if data.email:
            await _send_email(data)

    asyncio.get_event_loop().run_until_complete(collect_users_who_not_approved())


@celery.task(base=MyTask)
def archive_data() -> None:
    """Calling ArchiveController.do_archive() for archiving old data from main DB"""
    asyncio.get_event_loop().run_until_complete(ArchiveController.do_archive())


@celery.task(base=MyTask, name="~Max Parking Time Hours~")
def parking_time_exceeded(data: dict[str, Union[str, int]]) -> None:
    """
    ParkingTimeslot should be deleted after transport left parking.
    If it wasn't, creating StrangerThings SSE event and save it to DB.
    """

    async def check_if_transport_leave():
        if await ParkingTimeslot.exists(id=data.get("parking_timeslot")):
            await ParkingTimeslotService.create_strangerthings_sse_event(data)

    asyncio.get_event_loop().run_until_complete(check_if_transport_leave())


@celery.task(base=MyTask, name="~Web Push~")
def send_webpush(data: WebPush.ToCelery) -> None:
    """Sending web push notifications."""
    asyncio.get_event_loop().run_until_complete(
        WebPushController.trigger_push_notifications_for_subscriptions(
            data.subscriptions, data.title, data.body, data.url
        )
    )
