from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, NonNegativeInt, conlist, constr, validator, PositiveInt, conint, AnyUrl, Json
from datetime import time as d_time
from datetime import date as d_date

# import settings
from web_foundation.environment.resources.database.model_loader import EntityId
from web_foundation.utils.helpers import validate_datetime

from asbp_app.enviroment.infrastructure.database.models import SystemSettingsTypes, system_settings_type_typing, \
    WatermarkPosition

PHONE_NUMBER = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'


class SystemUser:
    class CreationDto(BaseModel):
        first_name: constr(min_length=1)
        last_name: constr(min_length=1)
        middle_name: Optional[constr(min_length=1)]
        username: constr(min_length=1)
        password: str
        phone: Optional[constr(regex=PHONE_NUMBER)]
        email: Optional[EmailStr]
        cabinet_number: Optional[str]
        department_name: Optional[str]
        scopes: conlist(item_type=EntityId, min_items=1)
        expire_session_delta: Optional[int] = 86400

    class UpdateDto(BaseModel):
        username: Optional[constr(min_length=1)]
        password: Optional[str]
        first_name: Optional[constr(min_length=1)]
        last_name: Optional[constr(min_length=1)]
        middle_name: Optional[constr(min_length=1)]
        phone: Optional[constr(regex=PHONE_NUMBER)]
        email: Optional[EmailStr]
        cabinet_number: Optional[str]
        department_name: Optional[str]
        scopes: Optional[conlist(item_type=EntityId, min_items=1)]
        expire_session_delta: Optional[int] = 86400


class Zone:
    class CreationDto(BaseModel):
        name: constr(min_length=1)

    class UpdateDto(BaseModel):
        name: constr(min_length=1)


# class ScopeConstructor:
#     """Updating roles for users"""
#
#     class UpdateDto(BaseModel):
#         scopes: conlist(item_type=EntityId, min_items=1)


class Claim:
    """Claim schema"""

    class CreationDto(BaseModel):
        pass_type: constr(min_length=1)
        claim_way: Optional[EntityId]
        claim_way_2: Optional[EntityId]
        pass_id: Optional[EntityId]
        is_in_blacklist: Optional[bool] = False
        pnd_agreement: Optional[bool] = False
        information: Optional[str]
        status: constr(min_length=1) | None = "Действующая"
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


class ClaimWay:
    class CreationDto(BaseModel):
        system_users: Optional[conlist(item_type=EntityId, min_items=1)]
        roles: Optional[conlist(item_type=EntityId, min_items=1)]

    class UpdateDto(BaseModel):
        system_users: Optional[conlist(item_type=EntityId, min_items=1)]
        roles: Optional[conlist(item_type=EntityId, min_items=1)]


class ClaimToZone:
    class CreationDto(BaseModel):
        claim: EntityId
        zones: conlist(item_type=EntityId, min_items=1)
        pass_id: Optional[EntityId]

    class UpdateDto(BaseModel):
        claim: Optional[EntityId]
        zones: Optional[conlist(item_type=EntityId, min_items=1)]
        pass_id: Optional[EntityId]


class ParkingPlace:
    class CreationDto(BaseModel):
        real_number: NonNegativeInt
        parking: EntityId

    class UpdateDto(BaseModel):
        real_number: Optional[NonNegativeInt]
        parking: Optional[EntityId]

    class BulkCreateDto(BaseModel):
        parking: EntityId


class Parking:
    class CreationDto(BaseModel):
        name: Optional[str]
        max_places: NonNegativeInt

    class UpdateDto(BaseModel):
        name: Optional[str]
        max_places: Optional[NonNegativeInt]


class RoleGroup:
    class CreationDto(BaseModel):
        name: str
        roles_id: list[EntityId]

    class UpdateDto(BaseModel):
        name: Optional[str]
        roles_id: Optional[list[EntityId]]


# class Scopes(BaseModel):
#     roles: conlist(item_type=EntityId, min_items=1)


class BuildingDto:
    class CreationDto(BaseModel):
        name: str
        entrance: str | None
        floor: str | None
        room: str | None
        kpp: str | None

    class UpdateDto(BaseModel):
        name: str | None
        entrance: str | None
        floor: str | None
        room: str | None
        kpp: str | None


class DivisionDto:
    class CreationDto(BaseModel):
        name: str
        email: EmailStr | None
        subdivision: EntityId | None

    class UpdateDto(BaseModel):
        name: str | None
        email: EmailStr | None
        subdivision: EntityId | None


class OrganisationDto:
    class CreationDto(BaseModel):
        short_name: str
        full_name: str | None
        email: EmailStr | None

    class UpdateDto(BaseModel):
        short_name: str | None
        full_name: str | None
        email: EmailStr | None


class JobTitleDto:
    class CreationDto(BaseModel):
        name: str

    class UpdateDto(BaseModel):
        name: str


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


class BlackListDto:
    """Black list schema"""

    class CreationDto(BaseModel):
        visitor: EntityId
        level: str | None
        comment: str
        photo: bytes | None

    class UpdateDto(BaseModel):
        # visitor: EntityId | None
        level: str | None
        comment: str
        photo: bytes | None


class WebPush:
    """Web Push schema"""

    class CreationDto(BaseModel):
        endpoint: AnyUrl
        keys: dict[Literal["p256dh", "auth"], str]
        expiration_time: str | None


# class SystemSettingsDto:
#     class UpdateDto(BaseModel):
#         """Schema for system settings"""
#         claimway_before_n_minutes: Optional[PositiveInt]
#         max_systemuser_license: Optional[PositiveInt]
#         max_photo_upload: Optional[NonNegativeInt]
#         watermark_transparency: Optional[conint(ge=0, le=255)]
#         watermark_format: Optional[constr(min_length=2, max_length=9)]
#         watermark_font_size: Optional[PositiveInt]
#         watermark_font_type: Optional[constr(min_length=1, max_length=32)]
#         watermark_font_rgb_color: Optional[constr(min_length=5, max_length=14)]
#         days_before_archive: Optional[PositiveInt]
#         max_parking_time_hours: Optional[PositiveInt]
#         parking_timeslot_interval: Optional[PositiveInt]
#         visitor_middle_name: dict[str, bool] | None
#         visitor_company_name: dict[str, bool] | None
#         visitor_attribute: dict[str, bool] | None
#         visitor_date_of_birth: dict[str, bool] | None
#         pass_type: dict[str, bool] | None
#         pass_valid_till_date: dict[str, bool] | None
#         transport_model: dict[str, bool] | None
#         transport_number: dict[str, bool] | None
#         transport_color: dict[str, bool] | None
#         document: dict[str, bool] | None
#         document_number: dict[str, bool] | None
#         document_registration: dict[str, bool] | None
#
#         @validator("watermark_format")
#         def to_upper(cls, value):
#             return value.upper()
#
#         def __str__(self):
#             return self.__class__.__name__

class SystemSettings:
    class UpdateDto(BaseModel):
        name: SystemSettingsTypes
        value: str | int | float | d_time

        @validator("value")
        def valide_value(cls, v, values, **kwargs):
            value_type = system_settings_type_typing.get(values['name'])
            if value_type == d_time:
                v = d_time.fromisoformat(v)
            else:
                v = value_type(v)
            return v


class WaterMarkDto:
    """Watermark schema"""

    class CreationDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]

    class UpdateDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]


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
        phone: Optional[constr(regex=PHONE_NUMBER)]
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
        system_user: Optional[EntityId]

    class UpdateDto(BaseModel):
        first_name: Optional[constr(min_length=1)]
        last_name: Optional[constr(min_length=1)]
        middle_name: Optional[constr(min_length=1)]
        who_invited: Optional[str]
        destination: Optional[str]
        company_name: Optional[constr(min_length=1)]
        date_of_birth: Optional[str]
        attribute: Optional[str]
        phone: Optional[constr(regex=PHONE_NUMBER)]
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
        user: Optional[EntityId]


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


class VisitSession:
    """
    Time which Visitor spend on object.
    It's enter time & exit time
    """

    class CreationDto(BaseModel):
        visitor_id: EntityId
        enter: Optional[str]
        exit: Optional[str]

    class UpdateDto(BaseModel):
        enter: Optional[str]
        exit: Optional[str]


class PassDto:
    """Pass schema"""

    class CreationDto(BaseModel):
        rfid: constr(min_length=1) | None
        pass_type: constr(min_length=1)
        valid_till_date: str
        valid: bool | None = True

        @validator("valid_till_date")
        def valid_date(cls, v):
            return validate_datetime(v)

    class UpdateDto(BaseModel):
        rfid: constr(min_length=1) | None
        pass_type: constr(min_length=1) | None
        valid_till_date: str | None
        valid: bool

        @validator("valid_till_date")
        def valid_date(cls, v):
            return validate_datetime(v)


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
