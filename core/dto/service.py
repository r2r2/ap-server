from datetime import datetime
from typing import Literal, Optional

from pydantic import (AnyUrl, BaseModel, EmailStr, Json, NonNegativeInt,
                      PositiveInt, conint, conlist, constr, validator)

import settings
from core.dto.access import EntityId
from infrastructure.database.models import WatermarkPosition


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


class Auth:
    """Authentication"""
    class LoginDto(BaseModel):
        username: constr(min_length=1)
        password: str


class ScopeConstructor:
    """Updating roles for users"""
    class UpdateDto(BaseModel):
        scopes: conlist(item_type=EntityId, min_items=1)


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
    class CreationDto(BaseModel):
        pass_type: constr(min_length=1)
        claim_way: Optional[EntityId]
        claim_way_2: Optional[EntityId]
        pass_id: Optional[EntityId]
        is_in_blacklist: Optional[bool] = False
        pnd_agreement: Optional[bool] = False
        information: Optional[str]
        status: constr(min_length=1)
        approved: Optional[bool]

    class UpdateDto(BaseModel):
        pass_type: Optional[constr(min_length=1)]
        claim_way: Optional[EntityId]
        claim_way_2: Optional[EntityId]
        pass_id: Optional[EntityId]
        is_in_blacklist: Optional[bool]
        pnd_agreement: Optional[bool]
        information: Optional[str]
        status: Optional[constr(min_length=1)]
        approved: Optional[bool]

    class ApproveDto(BaseModel):
        approved: bool
        comment: Optional[str]

    class GroupVisitDto(BaseModel):
        excel_file: bytes


class VisitorDto:
    """Visitor schema"""
    class CreationDto(BaseModel):
        first_name: constr(min_length=1)
        last_name: constr(min_length=1)
        middle_name: Optional[constr(min_length=1)]
        who_invited: Optional[str]
        destination: Optional[str]
        company_name: Optional[constr(min_length=1)]
        date_of_birth: Optional[str]
        attribute: Optional[str]
        phone: Optional[constr(regex=settings.PHONE_NUMBER)]
        email: Optional[EmailStr]
        visit_purpose: Optional[str]
        visit_start_date: Optional[str]
        visit_end_date: Optional[str]
        passport: Optional[EntityId]
        international_passport: Optional[EntityId]
        pass_id: Optional[EntityId]
        drive_license: Optional[EntityId]
        visitor_photo: Optional[EntityId]
        transport: Optional[EntityId]
        military_id: Optional[EntityId]
        claim: Optional[EntityId]

    class UpdateDto(BaseModel):
        first_name: Optional[constr(min_length=1)]
        last_name: Optional[constr(min_length=1)]
        middle_name: Optional[constr(min_length=1)]
        who_invited: Optional[str]
        destination: Optional[str]
        company_name: Optional[constr(min_length=1)]
        date_of_birth: Optional[str]
        attribute: Optional[str]
        phone: Optional[constr(regex=settings.PHONE_NUMBER)]
        email: Optional[EmailStr]
        visit_purpose: Optional[str]
        visit_start_date: Optional[str]
        visit_end_date: Optional[str]
        passport: Optional[EntityId]
        international_passport: Optional[EntityId]
        pass_id: Optional[EntityId]
        drive_license: Optional[EntityId]
        visitor_photo: Optional[EntityId]
        transport: Optional[EntityId]
        military_id: Optional[EntityId]
        claim: Optional[EntityId]


class VisitSessionDto:
    """
    Time which Visitor spend on object.
    It's enter time & exit time
    """
    class CreationDto(BaseModel):
        visitor: EntityId
        enter: Optional[str]
        exit: Optional[str]

    class UpdateDto(BaseModel):
        enter: Optional[str]
        exit: Optional[str]


class PassportDto:
    """Passport schema"""
    class CreationDto(BaseModel):
        number: int
        division_code: Optional[str]
        registration: Optional[str]
        date_of_birth: Optional[str]
        place_of_birth: Optional[str]
        gender: Optional[str]
        photo: Optional[EntityId]

    class UpdateDto(BaseModel):
        number: Optional[int]
        division_code: Optional[str]
        registration: Optional[str]
        date_of_birth: Optional[str]
        place_of_birth: Optional[str]
        gender: Optional[str]
        photo: Optional[EntityId]


class InternationalPassportDto:
    """International passport schema"""
    class CreationDto(BaseModel):
        number: int
        date_of_birth: Optional[str]
        date_of_issue: Optional[str]
        photo: Optional[EntityId]

    class UpdateDto(BaseModel):
        number: Optional[int]
        date_of_birth: Optional[str]
        date_of_issue: Optional[str]
        photo: Optional[EntityId]


class DriveLicenseDto:
    """Drive license schema"""
    class CreationDto(BaseModel):
        date_of_issue: Optional[str]
        expiration_date: Optional[str]
        place_of_issue: Optional[str]
        address_of_issue: Optional[str]
        number: int
        categories: Optional[str]
        photo: Optional[EntityId]

    class UpdateDto(BaseModel):
        date_of_issue: Optional[str]
        expiration_date: Optional[str]
        place_of_issue: Optional[str]
        address_of_issue: Optional[str]
        number: Optional[int]
        categories: Optional[str]
        photo: Optional[EntityId]


class VisitorPhotoDto:
    """Schema for all relative to Visitor's photos"""
    class CreationDto(BaseModel):
        signature: Optional[Json]
        webcam_img: Optional[conlist(bytes)]
        scan_img: Optional[conlist(bytes)]
        car_number_img: Optional[conlist(bytes)]
        add_watermark_image: Optional[bool] = False
        add_watermark_text: Optional[bool] = False
        watermark_id: Optional[int]
        watermark_position: Optional[WatermarkPosition]
        watermark_width: Optional[conint(gt=0, lt=800)] = 150
        watermark_height: Optional[conint(gt=0, lt=800)] = 150

    class UpdateDto(BaseModel):
        signature: Optional[Json]
        webcam_img: Optional[conlist(bytes)]
        scan_img: Optional[conlist(bytes)]
        car_number_img: Optional[conlist(bytes)]
        add_watermark_image: Optional[bool]
        add_watermark_text: Optional[bool]
        watermark_id: Optional[int]
        watermark_position: Optional[WatermarkPosition]
        watermark_width: Optional[conint(gt=0, lt=800)] = 150
        watermark_height: Optional[conint(gt=0, lt=800)] = 150


class WaterMarkDto:
    """Watermark schema"""
    class CreationDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]

    class UpdateDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]


class MilitaryIdDto:
    """Military id schema"""
    class CreationDto(BaseModel):
        number: constr(min_length=1)
        date_of_birth: Optional[str]
        place_of_issue: Optional[str]
        date_of_issue: Optional[str]
        place_of_birth: Optional[str]
        photo: Optional[EntityId]

    class UpdateDto(BaseModel):
        number: Optional[constr(min_length=1)]
        date_of_birth: Optional[str]
        place_of_issue: Optional[str]
        date_of_issue: Optional[str]
        place_of_birth: Optional[str]
        photo: Optional[EntityId]


class PassDto:
    """Pass schema"""
    class CreationDto(BaseModel):
        rfid: constr(min_length=1) | None
        pass_type: constr(min_length=1)
        valid_till_date: str
        valid: bool | None = True

    class UpdateDto(BaseModel):
        rfid: constr(min_length=1) | None
        pass_type: constr(min_length=1) | None
        valid_till_date: str | None
        valid: bool


class TransportDto:
    """Transport schema"""
    class CreationDto(BaseModel):
        model: Optional[str]
        number: str
        color: Optional[str]
        claims: conlist(item_type=EntityId, min_items=1)

        @validator('number')
        def number_to_upper(cls, value):
            return value.upper()

    class UpdateDto(BaseModel):
        model: Optional[str]
        number: Optional[str]
        color: Optional[str]
        claims: Optional[conlist(item_type=EntityId, min_items=1)]

        @validator('number')
        def number_to_upper(cls, value):
            return value.upper()


class ParkingTimeslotDto:
    """Schema for reserving time slots on parking"""
    class CreationDto(BaseModel):
        start: str
        end: str
        transport: EntityId
        parking_place: Optional[EntityId]

    class UpdateDto(BaseModel):
        start: Optional[str]
        end: Optional[str]
        transport: Optional[EntityId]
        parking_place: Optional[EntityId]


class BlackListDto:
    """Black list schema"""
    class CreationDto(BaseModel):
        visitor: EntityId
        level: Optional[str]

    class UpdateDto(BaseModel):
        visitor: Optional[EntityId]
        level: Optional[str]


class SystemSettingsDto(BaseModel):
    """Schema for system settings"""
    claimway_before_n_minutes: Optional[PositiveInt]
    max_systemuser_license: Optional[PositiveInt]
    max_photo_upload: Optional[NonNegativeInt]
    watermark_transparency: Optional[conint(ge=0, le=255)]
    watermark_format: Optional[constr(min_length=2, max_length=9)]
    watermark_font_size: Optional[PositiveInt]
    watermark_font_type: Optional[constr(min_length=1, max_length=32)]
    watermark_font_rgb_color: Optional[constr(min_length=5, max_length=14)]
    days_before_archive: Optional[PositiveInt]
    max_parking_time_hours: Optional[PositiveInt]
    parking_timeslot_interval: Optional[PositiveInt]

    @validator("watermark_format")
    def to_upper(cls, value):
        return value.upper()

    def __str__(self):
        return self.__class__.__name__
