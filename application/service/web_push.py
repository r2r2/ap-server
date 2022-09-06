from pywebpush import WebPushException, webpush
from sanic import HTTPResponse, Request, Sanic, json
from sanic.exceptions import NotFound
from sanic.views import HTTPMethodView
from tortoise import connections
from tortoise.transactions import atomic

import settings
from application.exceptions import InconsistencyError
from core.dto.access import EntityId
from core.dto.service import WebPush
from core.dto.validator import validate
from core.server.auth import protect
from core.utils.limit_offset import get_limit_offset
from core.utils.loggining import logger
from core.utils.orjson_default import odumps
from infrastructure.database.models import PushSubscription, SystemUser


class WebPushController:
    class Subscription(HTTPMethodView):
        enabled_scopes = ["Сотрудник службы безопасности"]
        post_dto = WebPush.SubscriptionDto

        @protect(retrive_user=False)
        async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
            if entity is None:
                limit, offset = await get_limit_offset(request)
                models = PushSubscription.all().limit(limit).offset(offset)
                return json([await model.values_dict() for model in await models])

            if model := await PushSubscription.get_or_none(id=entity):
                return json(await model.values_dict(fk_fields=True))
            else:
                raise NotFound()

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            dto = validate(self.post_dto, request)
            db = connections.get(settings.CONNECTION_NAME)
            subscription, _ = await PushSubscription.get_or_create(system_user=system_user,
                                                                   subscription_info=dto.dict(),
                                                                   using_db=db)
            return json({
                "status": "success",
                "result": {
                    "id": subscription.id,
                    "subscription_info": subscription.subscription_info
                }
            })

        @protect()
        async def delete(self, _: Request, __: EntityId, entity: EntityId = None) -> HTTPResponse:
            await WebPushController.Subscription.delete_subscription(entity)
            return json({"message": f"Subscription id={entity} has been deleted from DB."})

        @staticmethod
        @atomic(settings.CONNECTION_NAME)
        async def delete_subscription(sub_id: EntityId) -> None:
            subscription = await PushSubscription.get_or_none(id=sub_id)
            if subscription is None:
                raise InconsistencyError(message=f"There is no subscription with id={sub_id}.")
            await subscription.delete()
            logger.info(f"Subscription id={sub_id} has been deleted from DB.")

    class NotifyAll(HTTPMethodView):
        enabled_scopes = ["Сотрудник службы безопасности"]
        post_dto = WebPush.NotifyAllDto

        @protect()
        async def post(self, request: Request, _: SystemUser) -> HTTPResponse:
            dto = validate(self.post_dto, request)
            if subscriptions := await PushSubscription.all():
                results = await WebPushController.trigger_push_notifications_for_subscriptions(
                    subscriptions,
                    dto.title,
                    dto.body
                )
                return json({"status": "success", "result": results})
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
                await WebPushController.Subscription.delete_subscription(sub_id)
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
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"{settings.VAPID_CLAIM_EMAIL}"
                }
            )
            return response.ok
        except WebPushException as ex:
            await WebPushController.check_for_exceptions(ex, sub.id)
            return False

    @staticmethod
    async def trigger_push_notifications_for_subscriptions(subscriptions: list[PushSubscription], title: str,
                                                           body: str, url: str = None) -> list[bool]:
        """
        Loop through all subscriptions and send all the clients a push notification.
        """
        return [await WebPushController.trigger_push_notification(subscription, title, body, url)
                for subscription in subscriptions]


def init_web_push(app: Sanic) -> None:
    app.add_route(WebPushController.Subscription.as_view(), "/wp/subscription", methods=["POST", "GET"])
    app.add_route(WebPushController.Subscription.as_view(), "/wp/subscription/<entity:int>", methods=["GET"])
    app.add_route(WebPushController.NotifyAll.as_view(), "/wp/notify-all", methods=["POST"])
