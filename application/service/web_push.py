from pywebpush import webpush, WebPushException
from sanic.views import HTTPMethodView
from sanic import Sanic, Request, HTTPResponse, json
from tortoise.transactions import atomic
from tortoise import connections

import settings
from application.exceptions import InconsistencyError
from infrastructure.database.models import PushSubscription, SystemUser
from core.server.auth import protect
from core.utils.loggining import logger
from core.utils.orjson_default import odumps
from core.dto.access import EntityId
from core.dto.validator import validate
from core.dto.service import WebPush


class WebPushController:
    class Subscription(HTTPMethodView):
        enabled_scopes = ["Сотрудник службы безопасности"]
        post_dto = WebPush.SubscriptionDto

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            dto = validate(self.post_dto, request)
            """
            {
                "endpoint": "http://localhost",
                "keys": {
                    "p256dh": "BDu6tBfNIhThUj5epb8P9nvQsuMQuF_7C8PeKPtW_GPM6nzHTyHLuuRm0_cMdLYZDhWXIsECK-9CXZB6i_s6BOA",
                    "auth": "OX_52Uf3XDjjuHbJHIP7wXKXu_u56Y_K5ZoffhiZR3c"
                }
            }
            """
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

        @staticmethod
        @atomic(settings.CONNECTION_NAME)
        async def delete_subscription(sub_id: EntityId) -> None:
            subscription = await PushSubscription.get_or_none(id=sub_id)
            if subscription is None:
                raise InconsistencyError(message=f"There is no subscription with id={sub_id}.")
            await subscription.delete()
            logger.info(f"Subscription id={sub_id} has been deleted from DB.")

    # class NotifySingle(HTTPMethodView):
    #     """Send notification for current user."""
    #     enabled_scopes = ["Сотрудник службы безопасности"]
    #
    #     @protect()
    #     async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
    #         # json_data = request.json['subscription_info']
    #         json_data = request.json
    #         # subscription = {'subscription_info': json_data['subscription_info']}
    #         # subscription = {'subscription_info': json_data}
    #         # subscription = default_json.loads({'subscription_info': json_data})
    #         subscription = request.json
    #         print("notify_signle: {}".format(subscription))
    #         title = "Yay!"
    #         body = "Mary had a little lamb, with a nice mint jelly"
    #         results = await WebPushController.trigger_push_notification(
    #             subscription,
    #             title,
    #             body,
    #             system_user
    #         )
    #         return json({
    #             "status": "success",
    #             "result": results
    #         })

    class NotifyAll(HTTPMethodView):
        enabled_scopes = ["Сотрудник службы безопасности"]
        post_dto = WebPush.NotifyAllDto

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
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
    async def trigger_push_notification(sub: PushSubscription, title: str, body: str) -> bool:
        """Send Push notification using pywebpush."""
        try:
            response = webpush(
                subscription_info=sub.subscription_info,
                data=odumps({"title": title, "body": body}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=settings.VAPID_CLAIMS
            )
            return response.ok
        except WebPushException as ex:
            await WebPushController.check_for_exceptions(ex, sub.id)
            return False

    @staticmethod
    async def trigger_push_notifications_for_subscriptions(subscriptions: list[PushSubscription], title: str,
                                                           body: str) -> list[bool]:
        """
        Loop through all subscriptions and send all the clients a push notification.
        """
        return [await WebPushController.trigger_push_notification(subscription, title, body)
                for subscription in subscriptions]


def init_web_push(app: Sanic) -> None:
    app.add_route(WebPushController.Subscription.as_view(), "/wp/subscription", methods=["POST"])
    app.add_route(WebPushController.NotifyAll.as_view(), "/wp/notify-all", methods=["POST"])
    # app.add_route(WebPushController.NotifySingle.as_view(), "/wp/notify-single", methods=["POST"])
