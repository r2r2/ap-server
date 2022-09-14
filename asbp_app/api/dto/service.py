from datetime import datetime
from typing import Literal, Optional

from pydantic import (AnyUrl, BaseModel, EmailStr, Json, NonNegativeInt,
                      PositiveInt, conint, conlist, constr, validator)

from web_foundation.environment.resources.database.model_loader import EntityId

from asbp_app.enviroment.infrastructure.database.models import WatermarkPosition


PHONE_NUMBER = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'


class EmailStruct(BaseModel):
    """Schema for sending emails through Celery"""
    email: conlist(item_type=str, min_items=1)
    text: constr(min_length=1)
    subject: str
    time_to_send: Optional[datetime]
    time_to_expire: Optional[datetime]
    claim: Optional[EntityId]
    claim_way_2: Optional[bool]

    def __str__(self):
        return self.__class__.__name__


class ClaimStatus(BaseModel):
    """Schema for checking claim status."""
    claim: EntityId
    time_to_expire: datetime


class Auth:
    """Authentication"""

    class LoginDto(BaseModel):
        username: constr(min_length=1)
        password: str


class WebPush:
    """Web Push schema"""

    class SubscriptionDto(BaseModel):
        endpoint: AnyUrl
        keys: dict[Literal["p256dh", "auth"], str]
        expiration_time: str | None

    class NotifyAllDto(BaseModel):
        title: str
        body: str
        url: str | None

    class ToCelery(BaseModel):
        subscriptions: list
        title: str
        body: str
        url: str | None


class ClaimDto:
    """Claim schema"""

    class ApproveDto(BaseModel):
        approved: bool
        comment: Optional[str]

    class GroupVisitDto(BaseModel):
        excel_file: bytes
