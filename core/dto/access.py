from typing import Optional
from pydantic import BaseModel, conlist, EmailStr, constr, NonNegativeInt

import settings


EntityId = int
EntityName = str


class SystemUser:
    class CreationDto(BaseModel):
        first_name: constr(min_length=1)
        last_name: constr(min_length=1)
        middle_name: Optional[constr(min_length=1)]
        username: constr(min_length=1)
        password: str
        phone: Optional[constr(regex=settings.PHONE_NUMBER)]
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
        phone: Optional[constr(regex=settings.PHONE_NUMBER)]
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


class Role:
    class CreationDto(BaseModel):
        name: constr(min_length=1)

    class UpdateDto(BaseModel):
        name: constr(min_length=1)


class Scopes(BaseModel):
    roles: conlist(item_type=EntityId, min_items=1)
