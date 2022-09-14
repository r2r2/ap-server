from datetime import datetime
from typing import Union

from web_foundation.kernel import IMessage

from asbp_app.api.dto.service import EmailStruct, WebPush, ClaimStatus


class Event(IMessage):
    name: str
    _description: str

    def __init__(self):
        super().__init__()
        if not self._description:
            self._description = ""

    async def to_dict(self) -> dict:
        raise NotImplementedError()

    async def to_redis(self) -> dict:
        pd = await self.to_dict()
        pd.update({"description": self._description})
        return pd

    async def to_celery(self) -> dict:
        raise NotImplementedError()

    @staticmethod
    def all_types():
        return [cls.name for cls in Event.__subclasses__()]


class NotifyVisitorInBlackListEvent(Event):
    name = "visitor_in_black_list"
    _security_users: EmailStruct

    def __init__(self, email_struct: EmailStruct):
        self._security_users = email_struct
        self._description = "Notifying security officers about visitor in black list."
        super().__init__()

    async def to_dict(self) -> dict:
        return self._security_users.dict()

    async def to_celery(self) -> EmailStruct:
        return self._security_users


class NotifyUsersInClaimWayEvent(Event):
    name = "users_in_claimway"
    _system_users: EmailStruct

    def __init__(self, email_struct: EmailStruct):
        self._system_users = email_struct
        self._description = "Notifying system users marked in claim way."
        super().__init__()

    async def to_celery(self) -> EmailStruct:
        return self._system_users

    async def to_dict(self) -> dict:
        return self._system_users.dict()


class NotifyUsersInClaimWayBeforeNminutesEvent(Event):
    name = "users_in_claimway_before_N_minutes"
    _system_users: EmailStruct

    def __init__(self, email_struct: EmailStruct):
        self._system_users = email_struct
        self._description = "Notifying system users marked in claim way, who didn't approve claim, before N minutes."
        super().__init__()

    async def to_celery(self) -> EmailStruct:
        return self._system_users

    async def to_dict(self) -> dict:
        return self._system_users.dict()

    async def extract_time(self):
        return self._system_users.time_to_send, self._system_users.time_to_expire


class MaxParkingTimeHoursExceededEvent(Event):
    name = "max_parking_time_hours_exceeded"
    _data: dict[str, Union[str, int, datetime]]

    def __init__(self, data: dict[str, Union[str, int, datetime]]):
        self._data = data
        self._description = "Notifying security about transport, exceeded max time hours on a parking."
        super().__init__()

    async def to_celery(self) -> dict[str, Union[str, int]]:
        return self._data

    async def to_dict(self) -> dict:
        return self._data

    async def extract_time(self):
        return self._data.pop("time_to_send")


class SendWebPushEvent(Event):
    name = "webpush_event"
    _data: WebPush.ToCelery

    def __init__(self, data: WebPush.ToCelery):
        self._data = data
        self._description = "Sending Web Push notifications."
        super().__init__()

    async def to_celery(self) -> WebPush.ToCelery:
        return self._data

    async def to_dict(self) -> dict:
        return self._data.dict()


class ClaimStatusEvent(Event):
    name = "claim_status"
    _data: ClaimStatus | None

    def __init__(self, data: ClaimStatus | None = None):
        self._data = data
        self._description = "Check Claim status."
        super().__init__()

    async def to_celery(self) -> ClaimStatus:
        return self._data

    async def to_dict(self) -> dict:
        return self._data.dict()
