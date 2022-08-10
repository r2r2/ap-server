from pydantic import BaseModel, Json, conlist, constr, conint, EmailStr, validator, PositiveInt, NonNegativeInt
from typing import Optional
from datetime import datetime

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


class Auth:
    class LoginDto(BaseModel):
        username: constr(min_length=1)
        password: str


class ScopeConstructor:
    class UpdateDto(BaseModel):
        scopes: conlist(item_type=EntityId, min_items=1)


class ClaimDto:
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
    class CreationDto(BaseModel):
        visitor: EntityId
        enter: Optional[str]
        exit: Optional[str]

    class UpdateDto(BaseModel):
        enter: Optional[str]
        exit: Optional[str]


class PassportDto:
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
    class CreationDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]

    class UpdateDto(BaseModel):
        text: Optional[str]
        image: Optional[bytes]


class MilitaryIdDto:
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
    class CreationDto(BaseModel):
        rfid: Optional[int]
        pass_type: constr(min_length=1)
        valid_till_date: str
        valid: Optional[bool] = True

    class UpdateDto(BaseModel):
        rfid: Optional[int]
        pass_type: Optional[constr(min_length=1)]
        valid_till_date: Optional[str]
        valid: bool


class TransportDto:
    class CreationDto(BaseModel):
        model: Optional[str]
        number: str
        color: Optional[str]
        claims: conlist(item_type=EntityId, min_items=1)

        @validator('number')
        def number_to_upper(cls, v):
            return v.upper()

    class UpdateDto(BaseModel):
        model: Optional[str]
        number: Optional[str]
        color: Optional[str]
        claims: Optional[conlist(item_type=EntityId, min_items=1)]

        @validator('number')
        def number_to_upper(cls, v):
            return v.upper()


class ParkingTimeslotDto:
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
    class CreationDto(BaseModel):
        visitor: EntityId
        level: Optional[str]

    class UpdateDto(BaseModel):
        visitor: Optional[EntityId]
        level: Optional[str]


class SystemSettingsDto(BaseModel):
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
    def _to_upper(cls, v):
        return v.upper()
