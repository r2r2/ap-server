from typing import Callable

from loguru import logger
from pywebpush import WebPushException, webpush
from web_foundation.environment.resources.database.model_loader import EntityId
from web_foundation.environment.services.service import Service

from application.exceptions import InconsistencyError
from asbp_app.api.dto.service import WebPush
from asbp_app.enviroment.event.event import SendWebPushEvent
from asbp_app.enviroment.infrastructure.database.models import PushSubscription, SystemSettingsTypes
from asbp_app.utils.orjson_default import odumps
from asbp_app.utils.system import get_system_settings


class WebPushService(Service):

    @staticmethod
    async def create_web_push(user_id: list[int], title: str, body: str, url: str, emmit_func: Callable):
        subscriptions = await PushSubscription.filter(system_user__id__in=user_id)
        data = WebPush.ToCelery(subscriptions=subscriptions,
                                title=title,
                                body=body,
                                url=url)
        await emmit_func(SendWebPushEvent(data=data))

    async def emmit_web_push(self, user_id: list[int], title: str, body: str, url: str):
        # Send web push notifications
        await self.create_web_push(user_id=user_id, title=title, body=body, url=url, emmit_func=self.emmit_event)

    async def notify_all(self, dto: WebPush.NotifyAllDto) -> dict:
        if subscriptions := await PushSubscription.all():
            results = await self.trigger_push_notifications_for_subscriptions(
                subscriptions,
                dto.title,
                dto.body
            )
            return {"status": "success", "result": results}
        raise InconsistencyError(message="There are no active subscriptions.")

    @staticmethod
    async def check_for_exceptions(ex: WebPushException, sub_id: EntityId) -> None:
        """
        Check exception status code.
        If status code 404 or 410 then delete this subscription from DB.
        """
        match ex.response.status_code:
            case 404 | 410:
                logger.warning(f'Subscription id={sub_id} has expired or is no longer valid: {ex}')
                await PushSubscription.filter(id=sub_id).delete()
            case _:
                logger.warning(ex)
        # Mozilla returns additional information in the body of the response.
        if ex.response and ex.response.json():
            extra = ex.response.json()
            logger.warning(f"Remote service replied with a {extra.code}:{extra.errno}, {extra.message}")

    @staticmethod
    async def trigger_push_notification(sub: PushSubscription, title: str, body: str, url: str = "None") -> bool:
        """Send Push notification using pywebpush."""
        try:
            response = webpush(
                subscription_info=sub.subscription_info,
                data=odumps({"title": title, "body": body, "url": url}),
                vapid_private_key=await get_system_settings(SystemSettingsTypes.VAPID_PRIVATE_KEY),
                vapid_claims={
                    "sub": f"{await get_system_settings(SystemSettingsTypes.VAPID_CLAIM_EMAIL)}"
                }
            )
            return response.ok
        except WebPushException as ex:
            await WebPushService.check_for_exceptions(ex, sub.id)
            return False

    @staticmethod
    async def trigger_push_notifications_for_subscriptions(subscriptions: list[PushSubscription], title: str,
                                                           body: str, url: str = None) -> list[bool]:
        """
        Loop through all subscriptions and send all the clients a push notification.
        """
        return [await WebPushService.trigger_push_notification(subscription, title, body, url)
                for subscription in subscriptions]
