import asyncio
import io
import json
import itertools
from orjson import loads
from pywebpush import webpush, WebPushException
from sanic.views import HTTPMethodView
from sanic import Sanic, Request, HTTPResponse, json
from sanic.exceptions import NotFound
from tortoise.transactions import atomic
from pydantic import BaseModel

import settings
from application.exceptions import InconsistencyError
from infrastructure.database.models import PushSubscription, SystemUser
from infrastructure.database.layer import DbLayer
from core.server.auth import protect
from core.utils.loggining import logger
from core.utils.orjson_default import odumps
from core.dto.access import EntityId


class WebPushController:

    class Subscription(HTTPMethodView):
        enabled_scopes = ["Сотрудник службы безопасности"]

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            # json_data = request.json.get('subscription_info')
            json_data = request.json
            subscription = await PushSubscription.get_or_none(subscription_info=json_data)
            if subscription is None:
                subscription = await self.create_subscription(system_user, json_data)

            print(subscription.subscription_info)
            return json({
                "status": "success",
                "result": {
                    "id": subscription.id,
                    "subscription_info": subscription.subscription_info
                }
            })

        @atomic(settings.CONNECTION_NAME)
        async def create_subscription(self, system_user: SystemUser, json_data: dict) -> PushSubscription:
            return await PushSubscription.create(system_user=system_user, subscription_info=json_data)

        @atomic(settings.CONNECTION_NAME)
        async def delete_subscription(self, system_user: SystemUser, subscription) -> None:
            sub = await PushSubscription.get_or_none(id=subscription.id)
            if sub is None:
                raise InconsistencyError
            return

    class NotifySingle(HTTPMethodView):

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            # json_data = request.json['subscription_info']
            json_data = request.json
            # subscription = {'subscription_info': json_data['subscription_info']}
            subscription = {'subscription_info': json_data}
            print("notify_signle: {}".format(subscription))

            results = await WebPushController.trigger_push_notification(
                subscription,
                "Yay!",
                "Mary had a little lamb, with a nice mint jelly"
            )
            return json({
                "status": "success",
                "result": results
            })

    class NotifyAll(HTTPMethodView):

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            # get all the subscription from the database
            subscriptions = await PushSubscription.all()
            results = await WebPushController.trigger_push_notifications_for_subscriptions(
                subscriptions,
                "Yay!",
                "Mary had a little lamb, with a nice mint jelly"
            )
            return json({
                "status": "success",
                "result": results
            })

    @staticmethod
    async def trigger_push_notification(sub: dict[str, dict], title: str, body: str) -> bool:
        try:
            # print(json.loads(push_subscription.subscription_json))
            response = webpush(
                subscription_info=json.loads(sub),
                data=odumps({"title": title, "body": body}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=settings.VAPID_CLAIMS
            )
            return response.ok
        except WebPushException as ex:
            logger.warning(ex)
            if ex.response and ex.response.json():
                extra = ex.response.json()
                print("Remote service replied with a {}:{}, {}",
                    extra.code,
                    extra.errno,
                    extra.message
                )
            print(ex)
            return False

    @staticmethod
    async def trigger_push_notifications_for_subscriptions(subscriptions: list[PushSubscription], title: str, body: str):
        """
        loop through all subscirptions and send all the clients a push notification
        """
        print(subscriptions)
        return [await WebPushController.trigger_push_notification(await subscription.subscription_info, title, body)
                for subscription in subscriptions]


def init_web_push(app: Sanic) -> None:
    app.add_route(WebPushController.Subscription.as_view(), "/wp/subscription", methods=["POST"])
    app.add_route(WebPushController.NotifySingle.as_view(), "/wp/notify-single", methods=["POST"])
    app.add_route(WebPushController.NotifyAll.as_view(), "/wp/notify-all", methods=["POST"])


    # async def check_for_exceptions(self):
    #     const triggerPushMsg = function(subscription, dataToSend)
    #     {
    #     return webpush.sendNotification(subscription, dataToSend).catch((err) = > {
    #     if (err.statusCode === 404 | | err.statusCode == = 410)
    #     {
    #         console.log('Subscription has expired or is no longer valid: ', err);
    #     return deleteSubscriptionFromDatabase(subscription._id);
    #     } else {throw err;}});};