from datetime import datetime, timedelta
from typing import Type, List, Union, Callable, Optional

from pydantic import BaseModel as PdModel, BaseModel
from tortoise import exceptions
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.models import MODEL
from tortoise.transactions import atomic
from web_foundation.environment.resources.database.model_loader import ModelLoader, AccessProtectIdentity, EntityId
from web_foundation.environment.resources.database.models import GenericDbType
from web_foundation.environment.resources.database.utils import integrity_error_format
from web_foundation.errors.app.application import InconsistencyError
from web_foundation.utils.crypto import BaseCrypto
from web_foundation.utils.helpers import validate_date, validate_datetime

from asbp_app.api.dto import access as access_dto
from asbp_app.api.dto.service import WebPush, ClaimStatus
from asbp_app.api.protectors import UserIdentity
from asbp_app.enviroment.celery.sending_emails import create_email_struct_for_sec_officers
from asbp_app.enviroment.event.event import SendWebPushEvent, NotifyVisitorInBlackListEvent, \
    NotifyUsersInClaimWayBeforeNminutesEvent, NotifyUsersInClaimWayEvent, ClaimStatusEvent, \
    MaxParkingTimeHoursExceededEvent
from asbp_app.enviroment.infrastructure.database.models import *
from asbp_app.enviroment.service.web_push import WebPushService
from asbp_app.utils.filter_uniq import create_filters
from asbp_app.utils.license_count import SysUserLicenses
from asbp_app.utils.mailing import create_email_struct, calculate_time_to_send_notify
from asbp_app.utils.system import get_system_settings
from asbp_app.utils.watermark import WaterMarkUtil


class BaseAccessLoader(ModelLoader):

    @staticmethod
    async def get_or_raise_deleted(target_model: GenericDbType, entity_id: EntityId):
        entity = await ModelLoader.get_entity(target_model, entity_id=entity_id)
        if hasattr(entity, "deleted") and entity.deleted:
            raise InconsistencyError(message=f"This {target_model.__name__} is already marked as deleted")
        return entity

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: AccessProtectIdentity, dto: PdModel,
                     **kwargs) -> GenericDbType:
        entity_kwargs = {field: value for field, value in dto.dict().items() if value is not None}
        try:
            entity = None
            if hasattr(dto, "name"):
                filters = create_filters(model, dto)
                if hasattr(model, "deleted"):
                    entity_kwargs['deleted'] = False
                    if await model.exists(name=dto.name, deleted=False):
                        raise InconsistencyError(message=f"{model.__name__} already exists")
                entity = await model.get_or_none(**filters)
                if entity:
                    await entity.update_from_dict(entity_kwargs).save()
            if not entity:
                entity = await model.create(**entity_kwargs)
        except IntegrityError as exception:
            raise integrity_error_format(exception)
        except ValueError as exception:
            raise InconsistencyError(exception)
        return entity

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity, dto: PdModel,
                     **kwargs) -> GenericDbType:
        entity = await cls.get_or_raise_deleted(model, entity_id)
        entity_kwargs = {field: value for field, value in dto.dict().items() if value is not None}
        for field, value in entity_kwargs.items():
            setattr(entity, field, value)
        try:
            await entity.save(update_fields=list(entity_kwargs.keys()))
        except IntegrityError as exception:
            raise integrity_error_format(exception)
        except ValueError as exception:
            raise InconsistencyError(exception)
        return entity

    @classmethod
    @atomic()
    async def delete(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     **kwargs) -> GenericDbType:
        entity = await cls.get_or_raise_deleted(model, entity_id)
        if hasattr(entity, "deleted"):
            await model.filter(id=entity_id).update(deleted=True)
        else:
            await entity.delete()
        return entity


class SystemUserLoader(BaseAccessLoader):
    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.SystemUser.CreationDto,
                     **kwargs) -> GenericDbType:
        if await model.exists(username=dto.username, deleted=False):
            raise InconsistencyError(message=f"{model.__name__} already exists")

        license_count: int = SysUserLicenses.role_count
        licenses: int = await get_system_settings(SystemSettingsTypes.MAX_USER_LICENSE)
        if license_count >= licenses:
            raise InconsistencyError(message=f"You've reached max available license {licenses}."
                                             f"Now you have {license_count} active licenses.")

        crypted_password, salt = BaseCrypto.encrypt_password(dto.password)

        try:
            entity_kwargs = {field: value for field, value in dto.dict().items()
                             if field not in ("salt", "password", "scopes")}

            system_user = await SystemUser.create(**entity_kwargs,
                                                  password=crypted_password,
                                                  salt=salt)

            roles = await UserRoleGroup.filter(id__in=dto.roles)
            await system_user.role_group.add(*roles)
            await SysUserLicenses.increment_count()
            return system_user

        except exceptions.ValidationError as ex:
            raise InconsistencyError(message=f"There is validation problem with {ex}.")

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.SystemUser.UpdateDto, **kwargs) -> GenericDbType:
        system_user: SystemUser = await cls.get_or_raise_deleted(model, entity_id)

        if dto.password:
            crypted_password, salt = BaseCrypto.encrypt_password(dto.password)
            system_user.password = crypted_password
            system_user.salt = salt

        try:
            for field, value in dto.dict().items():
                if value:
                    if field in ("password", "salt"):
                        continue
                    elif field == "scopes":
                        roles = await UserRoleGroup.filter(id__in=value)
                        await system_user.role_group.clear()
                        await system_user.role_group.add(*roles)
                    else:
                        setattr(system_user, field, value)

            await system_user.save()
            return entity_id

        except exceptions.ValidationError as ex:
            raise InconsistencyError(message=f"There is validation problem with {ex}.")

    @classmethod
    @atomic()
    async def delete(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     **kwargs) -> GenericDbType:
        user: SystemUser = await cls.get_or_raise_deleted(model, entity_id)
        if user is None:
            raise InconsistencyError(message="Such user does not exist")
        if not await model.filter(id=entity_id, deleted=False).update(deleted=True):
            raise InconsistencyError(message="This user is already marked as deleted")
        await SysUserLicenses.decrement_count()
        return user


class RoleGroupLoader(BaseAccessLoader):

    @staticmethod
    async def get_roles(user: SystemUser, roles_id: List[EntityId]):
        roles = await UserRole.filter(id__in=roles_id)
        if len(roles) != len(roles_id):
            raise InconsistencyError(message="Some roles not found")
        forbidden_roles = set(roles) - set(user.role_group.roles)
        if forbidden_roles:
            raise InconsistencyError(
                message=f"""You can"t create group with roles: {", ".join(r.name for r in forbidden_roles)}""")
        return roles

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.RoleGroup.CreationDto,
                     **kwargs) -> AbstractDbModel:
        roles = await cls.get_roles(protection.user, dto.roles_id)
        dto.roles_id = None
        role_group: UserRoleGroup = await BaseAccessLoader.create(model, protection, dto, **kwargs)
        if not role_group.roles._fetched:
            await role_group.fetch_related("roles")
        if role_group.roles:
            await role_group.roles.clear()
        await role_group.roles.add(*roles)
        role_group = await model.get(id=role_group.id).prefetch_related("roles")
        return role_group

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.RoleGroup.UpdateDto) -> AbstractDbModel:
        roles = None
        if dto.roles_id:
            roles = await cls.get_roles(protection.user, dto.roles_id)
            dto.roles_id = None

        role_group = await BaseAccessLoader.update(model=model, protection=protection,
                                                   entity_id=entity_id, dto=dto)
        if roles:
            await role_group.roles.add(*roles)
            role_group = await model.get(id=role_group.id).prefetch_related("roles")
        return role_group

    @classmethod
    @atomic()
    async def delete(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity) -> EntityId:
        role_group = await BaseAccessLoader.get_or_raise_deleted(model, entity_id)

        users_with_group = await SystemUser.filter(role_group_id=entity_id, deleted=False)
        if users_with_group:
            users_id = ", ".join([str(user.id) for user in users_with_group])
            raise InconsistencyError(
                message=f"Can't delete group with active users ({users_id})")

        await model.filter(id=entity_id).update(deleted=True)
        return role_group


class ClaimLoader(BaseAccessLoader):

    @staticmethod
    async def create_claimway_approval(claim_way: ClaimWay,
                                       claim: Claim,
                                       claim_way_2: ClaimWay = None) -> None:
        """Creating ClaimWayApproval for SystemUsers in ClaimWay."""
        sys_users = await claim_way.system_users.all()

        sys_users2 = list()
        if claim_way_2:
            sys_users2 = await claim_way_2.system_users.all()

        users: list[SystemUser] = sys_users + sys_users2
        approval_way = []
        for user in users:
            approval_way.append(ClaimWayApproval(system_user=user, claim=claim))
        await ClaimWayApproval.bulk_create(approval_way)

    @staticmethod
    async def prepare_data_for_claim_status(claim: Claim) -> ClaimStatus | None:
        """Prepare data for event base on Visitor.visit_start_date."""
        if time_to_claim := await calculate_time_to_send_notify(claim):
            _, time_to_expire = time_to_claim
            data = ClaimStatus(
                claim=claim.id,
                time_to_expire=time_to_expire
            )
            return data

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.Claim.CreationDto,
                     **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        pass_id = await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None
        claim_way = await ClaimWay.get_or_none(id=dto.claim_way).prefetch_related(
            "system_users") if dto.claim_way else None
        claim_way2 = await ClaimWay.get_or_none(id=dto.claim_way_2).prefetch_related(
            "system_users") if dto.claim_way_2 else None

        kwrgs = {field: value for field, value in dto.dict().items()
                 if field not in ("pass_id", "claim_way", "claim_way_2", "approved") and value}

        if claim_way:
            if pass_id is not None:
                raise InconsistencyError(message=f"You can't assign Pass to Claim if claim has ClaimWay to approve. "
                                                 f"First claim should be approved.")
            claim = await Claim.create(**kwrgs, claim_way=claim_way, claim_way_2=claim_way2,
                                       system_user=protection.user)
            await cls.create_claimway_approval(claim_way, claim, claim_way2)

            if claim_way2:
                await emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                    await create_email_struct(claim_way, claim=claim, time_before=True, claim_way_2=True)
                ))

            await emmit_func(NotifyUsersInClaimWayEvent(await create_email_struct(claim_way, claim=claim)))
            await emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                await create_email_struct(claim_way, claim=claim, time_before=True)))
        else:
            claim = await Claim.create(**kwrgs, pass_id=pass_id, system_user=protection.user)

        if data := await cls.prepare_data_for_claim_status(claim):
            await emmit_func(ClaimStatusEvent(data))
        return claim

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.Claim.UpdateDto, **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        notification_counter = 0
        claim: Claim = await Claim.get_or_none(id=entity_id)
        if claim is None:
            raise InconsistencyError(message=f"Claim with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if field in ("claim_way", "claim_way_2") and value:
                claim_way = await ClaimWay.get_or_none(id=value).prefetch_related(
                    "system_users")
                if claim_way is None:
                    raise InconsistencyError(message=f"ClaimWay with id={value} doesn't exist.")
                setattr(claim, field, claim_way)

                if field == "claim_way":
                    await emmit_func(NotifyUsersInClaimWayEvent(await create_email_struct(claim_way, claim=claim)))
                    await emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                        await create_email_struct(claim_way, claim=claim, time_before=True)))
                    notification_counter += 1

                elif field == "claim_way_2":
                    if claim.claim_way_approved:
                        await emmit_func(NotifyUsersInClaimWayEvent(await create_email_struct(claim_way, claim=claim,
                                                                                              claim_way_2=True)))
                    await emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                        await create_email_struct(claim_way, claim=claim, time_before=True, claim_way_2=True)))

                await cls.create_claimway_approval(claim_way, claim)

        pass_id = await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None
        if pass_id is None and dto.pass_id:
            raise InconsistencyError(message=f"Pass with id={dto.pass_id} doesn't exist.")

        if claim.claim_way:
            # Trying to assign Pass to Claim.
            # If claim_way was assigned - check for Claim.approved==True
            if pass_id is not None and claim.approved:
                setattr(claim, "pass_id", pass_id)
            elif pass_id is not None and not claim.approved:
                raise InconsistencyError(message=f"Claim id={entity_id} should be approved before assign Pass to it.")
        else:
            # If no claim_way - just set Pass to this Claim
            if pass_id is not None:
                setattr(claim, "pass_id", pass_id)

        if dto.is_in_blacklist is not None:
            setattr(claim, "is_in_blacklist", False if dto.is_in_blacklist is False else True)
            if dto.is_in_blacklist:
                visitor = await Visitor.get_or_none(claim=claim.id)
                await BlackList.create(visitor=visitor)

        if dto.pnd_agreement is not None:
            setattr(claim, "pnd_agreement", False if dto.pnd_agreement is False else True)

        setattr(claim, "pass_type", getattr(dto, "pass_type", claim.pass_type))
        setattr(claim, "information", getattr(dto, "information", claim.information))
        setattr(claim, "system_user", protection.user)

        if dto.status:
            setattr(claim, "status", dto.status)
            # If changing sensitive fields notify related users in ClaimWay
            if claim.claim_way is not None:
                claim_way = await ClaimWay.get_or_none(id=claim.claim_way.id).prefetch_related("system_users")

                if notification_counter == 0:
                    await emmit_func(NotifyUsersInClaimWayEvent(
                        await create_email_struct(claim_way, claim=claim, status=dto.status)))

                if claim.claim_way_2:
                    claim_way2 = await ClaimWay.get_or_none(id=claim.claim_way_2.id).prefetch_related("system_users")
                    if claim.claim_way_approved:
                        await emmit_func(NotifyUsersInClaimWayEvent(
                            await create_email_struct(claim_way2, claim=claim, status=dto.status, claim_way_2=True)))
        await claim.save()
        return claim


class ClaimWayLoader(BaseAccessLoader):

    @staticmethod
    async def add_roles_and_users(claim_way: ClaimWay,
                                  dto: access_dto.ClaimWay.CreationDto | access_dto.ClaimWay.UpdateDto) -> None:
        """Add Roles and SystemUsers to ClaimWay"""
        if dto.system_users:
            sys_users = await SystemUser.filter(id__in=dto.system_users)
            if len(sys_users) != len(dto.system_users):
                raise InconsistencyError(message=f"Couldn't find some users with id={dto.system_users}.")
            await claim_way.system_users.clear()
            await claim_way.system_users.add(*sys_users)

        if dto.roles:
            roles = await UserRole.filter(id__in=dto.roles)
            if len(roles) != len(dto.roles):
                raise InconsistencyError(message=f"Couldn't find some roles with id={dto.roles}.")
            await claim_way.role_group.clear()
            await claim_way.role_group.add(*roles)

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.ClaimWay.CreationDto,
                     **kwargs) -> GenericDbType:
        claim_way = await ClaimWay.create()
        await cls.add_roles_and_users(claim_way, dto)
        return claim_way

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.ClaimWay.UpdateDto, **kwargs) -> GenericDbType:

        claim_way = await ClaimWay.get_or_none(id=entity_id)
        if claim_way is None:
            raise InconsistencyError(message=f"ClaimWay with id={entity_id} does not exist.")

        way_dict = {
            "before": await claim_way.values_dict(m2m_fields=True),
            "after": {}
        }

        await cls.add_roles_and_users(claim_way, dto)
        way_dict["after"] = await claim_way.values_dict(m2m_fields=True)
        await StrangerThings.create(system_user=protection.user, claim_way_changed=way_dict)
        return claim_way


class ClaimToZoneLoader(BaseAccessLoader):
    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.ClaimToZone.CreationDto,
                     **kwargs) -> GenericDbType:
        claim = await Claim.get_or_none(id=dto.claim)
        if claim is None:
            raise InconsistencyError(message=f"Claim with id={dto.claim} does not exist.")

        pass_id = None
        if dto.pass_id:
            pass_id = await Pass.get_or_none(id=dto.pass_id)
            if pass_id is None:
                raise InconsistencyError(message=f"Pass with id={dto.pass_id} does not exist.")

        claim_to_zone = await ClaimToZone.create(claim=claim,
                                                 pass_id=pass_id)

        zones = await Zone.filter(id__in=dto.zones)
        await claim_to_zone.zones.add(*zones)

        return claim_to_zone

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.ClaimToZone.UpdateDto, **kwargs) -> GenericDbType:
        claim_to_zone = await ClaimToZone.get_or_none(id=dto.claim)
        if claim_to_zone is None:
            raise InconsistencyError(message=f"ClaimToZone with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                if field == "pass_id":
                    pass_id = await Pass.get_or_none(id=value)
                    if pass_id is None:
                        raise InconsistencyError(message=f"Pass with id={value} does not exist.")
                    setattr(claim_to_zone, field, pass_id)

                elif field == "claim":
                    claim = await Claim.get_or_none(id=value)
                    if claim is None:
                        raise InconsistencyError(message=f"Claim with id={value} does not exist.")
                    setattr(claim_to_zone, field, claim)

                elif field == "zones":
                    zones = await Zone.filter(id__in=value)
                    if len(zones) != len(value):
                        raise InconsistencyError(message=f"Zone with id={value} does not exist.")
                    await claim_to_zone.zones.add(*zones)
        await claim_to_zone.save()
        return claim_to_zone


class ParkingLoader(BaseAccessLoader):
    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.Parking.CreationDto,
                     **kwargs) -> GenericDbType:

        entity_kwargs = {field: value for field, value in dto.dict().items() if value}
        parking = await Parking.create(**entity_kwargs)
        place_to_create = []
        for i in range(1, parking.max_places + 1):
            place_to_create.append(ParkingPlace(real_number=i, parking=parking))
        await ParkingPlace.bulk_create(place_to_create)

        return parking

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.Parking.UpdateDto, **kwargs) -> GenericDbType:
        parking = await Parking.get_or_none(id=entity_id)
        if parking is None:
            raise InconsistencyError(message=f"Parking with id={entity_id} does not exist")

        for field, value in dto.dict().items():
            if value:
                setattr(parking, field, value)

        place_to_create = []
        if dto.max_places:
            await ParkingPlace.all().delete()
            for i in range(1, parking.max_places + 1):
                place_to_create.append(ParkingPlace(real_number=i, parking=parking))
        await ParkingPlace.bulk_create(place_to_create)

        await parking.save()
        return parking


class ParkingPlaceLoader(BaseAccessLoader):
    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.ParkingPlace.CreationDto,
                     **kwargs) -> GenericDbType:
        parking = await Parking.get_or_none(id=dto.parking)
        if parking is None:
            raise InconsistencyError(message=f"Parking with id={dto.parking} doesn't exist.")

        parking_place = await ParkingPlace.create(real_number=dto.real_number, parking=parking)
        return parking_place

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.Parking.UpdateDto, **kwargs) -> GenericDbType:
        parking_place = await ParkingPlace.get_or_none(id=entity_id)
        if parking_place is None:
            raise InconsistencyError(message=f"ParkingPlace with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                setattr(parking_place, field, value)

        await parking_place.save()
        return parking_place


class DivisionLoader(BaseAccessLoader):
    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.DivisionDto.CreationDto,
                     **kwargs) -> GenericDbType:

        if dto.subdivision:
            subdivision = await Division.get_or_none(id=dto.subdivision)
        else:
            subdivision = None
        entity = await Division.create(name=dto.name, email=dto.email, subdivision=subdivision)
        return entity

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.DivisionDto.UpdateDto, **kwargs) -> GenericDbType:

        division = await Division.get_or_none(id=entity_id)
        if division is None:
            raise InconsistencyError(message=f"Division with id={entity_id} doesn't exist.")

        for field, value in dto.dict().items():
            if value:
                if field == "subdivision":
                    subdivision = await Division.get_or_none(id=value)
                    if subdivision is None:
                        raise InconsistencyError(message=f"Division with id={value} doesn't exist.")
                    setattr(division, field, subdivision)
                else:
                    setattr(division, field, value)

        return division


# class PassportLoader(BaseAccessLoader):
#
#     @staticmethod
#     async def extract_relatable_fields(model: AbstractDbModel) -> List[str]:
#         return [field for field, sheme in model._meta.fields_map.items() if
#                 sheme.__class__.__base__ == RelationalField]
#
#     @staticmethod
#     async def get_optional_view(model: Type[AbstractDbModel], _id: Union[int, List[int]],
#                                 columns: List[Field] = None) -> Union[AbstractDbModel, List[AbstractDbModel], None]:
#
#         if isinstance(_id, list):
#             query: QuerySet = model.filter(Q(id__in=_id))
#         else:
#             query: QuerySetSingle = model.get_or_none(id=_id)
#         if columns is None:
#             related = await PassportLoader.extract_relatable_fields(model)
#             return await query.prefetch_related(*related)
#         else:
#             cols: List[str] = [col.model_field_name for col in columns]
#             rows = await query.values(*cols)
#             if isinstance(rows, list):
#                 return [model(**row) for row in rows]
#             return model(**rows)


class PersonalDocumentLoader(BaseAccessLoader):

    @classmethod
    async def set_params_for_document(cls, dto: BaseModel, target_model: MODEL = None) -> dict | None:
        """
        POST: If target_model is not transferred, create dict (return dict).
        PUT: Receives target_model and sets attributes (return None).
        """
        if target_model is None:
            kwrgs = dict()
            for field, value in dto.dict().items():
                if value:
                    if "date" in field:
                        kwrgs.update({field: validate_date(value, check_gt_now=False)})
                    elif field == "photo":
                        kwrgs.update({field: await VisitorPhoto.get_or_none(id=value)})
                    else:
                        kwrgs.update({field: value})
            return kwrgs

        for field, value in dto.dict().items():
            if value:
                if "date" in field:

                    setattr(target_model, field, validate_date(value, check_gt_now=False))
                elif field == "photo":
                    setattr(target_model, field, await VisitorPhoto.get_or_none(id=value))
                else:
                    setattr(target_model, field, value)

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity,
                     dto: access_dto.MilitaryIdDto.CreationDto |
                          access_dto.PassportDto.CreationDto |
                          access_dto.InternationalPassportDto.CreationDto |
                          access_dto.DriveLicenseDto.CreationDto,
                     **kwargs) -> GenericDbType:

        already_exists = await model.exists(number=dto.number)
        if already_exists:
            raise InconsistencyError(message=f"{model.__class__.__name__} with number={dto.number} already exists.")
        set_param = await cls.set_params_for_document(dto)
        document = await model.create(**set_param)
        return document

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.MilitaryIdDto.UpdateDto |
                          access_dto.PassportDto.UpdateDto |
                          access_dto.InternationalPassportDto.UpdateDto |
                          access_dto.DriveLicenseDto.UpdateDto,
                     **kwargs) -> GenericDbType:

        document = await model.get_or_none(id=entity_id)
        if document is None:
            raise InconsistencyError(message=f"{model.__class__.__name__} with id={entity_id} does not exist.")

        await cls.set_params_for_document(dto, document)

        await document.save()
        return document


class TransportLoader(BaseAccessLoader):

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.TransportDto.CreationDto,
                     **kwargs) -> GenericDbType:
        if await model.exists(number=dto.number):
            raise InconsistencyError(message=f"{model.__name__} already exists")

        claims = await Claim.filter(id__in=dto.claims)

        transport = await Transport.create(model=dto.model,
                                           number=dto.number,
                                           color=dto.color,
                                           claims=claims)

        return transport

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.TransportDto.UpdateDto, **kwargs) -> GenericDbType:

        transport = await Transport.get_or_none(id=entity_id)
        if transport is None:
            raise InconsistencyError(message=f"Transport with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                if field == "claims":
                    claims = await Claim.filter(id__in=value)
                    await transport.claims.add(*claims)
                else:
                    setattr(transport, field, value)

        await transport.save()
        return transport


class BlackListLoader(BaseAccessLoader):

    @staticmethod
    async def emmit_events(visitor: Visitor, user: SystemUser, emmit_func: Callable):
        email_struct, security_officers = await create_email_struct_for_sec_officers(visitor, user)
        # Send web push notifications
        subscriptions = await PushSubscription.filter(system_user__id__in=[user.id for user in security_officers])
        data = WebPush.ToCelery(subscriptions=subscriptions, title=email_struct.subject, body=email_struct.text,
                                url=None)
        await emmit_func(SendWebPushEvent(data=data))
        await emmit_func(NotifyVisitorInBlackListEvent(email_struct))

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.BlackListDto.CreationDto,
                     **kwargs) -> GenericDbType:
        visitor = await Visitor.get_or_none(id=dto.visitor)
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={dto.visitor} does not exist."
                                             "You should provide valid Visitor for BlackList")
        if await BlackList.exists(visitor=visitor.id):
            raise InconsistencyError(message=f"Visitor with id={dto.visitor} already in BlackList.")

        kwrgs = {field: value for field, value in dto.dict().items() if field != "visitor"}

        black_list = await BlackList.create(visitor=visitor, **kwrgs)

        return black_list


class WebPushLoader(BaseAccessLoader):

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: PdModel,
                     **kwargs) -> GenericDbType:
        subscription, _ = await PushSubscription.get_or_create(system_user=protection.user,
                                                               subscription_info=dto.dict())
        return subscription
        return {
            "status": "success",
            "result": {
                "id": subscription.id,
                "subscription_info": subscription.subscription_info
            }
        }  # TODO WHY??!


class VisitorLoader(BaseAccessLoader):

    @staticmethod
    async def get_visitor_fk_relations(
            dto: access_dto.VisitorDto.CreationDto | access_dto.VisitorDto.UpdateDto
    ) -> dict[str, Type[AbstractDbModel] | None]:

        """Trying to get Visitor's documents, transports, claims and returning them as a dict"""
        fk_relations = {
            "passport": await Passport.get_or_none(id=dto.passport) if dto.passport else None,
            "international_passport": await InternationalPassport.get_or_none(id=dto.international_passport)
            if dto.international_passport else None,
            "pass_id": await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None,
            "drive_license": await DriveLicense.get_or_none(id=dto.drive_license) if dto.drive_license else None,
            "military_id": await MilitaryId.get_or_none(id=dto.military_id) if dto.military_id else None,
            "transport": await Transport.get_or_none(id=dto.transport) if dto.transport else None,
            "claim": await Claim.get_or_none(id=dto.claim).prefetch_related() if dto.claim else None,
            "visitor_photo": await VisitorPhoto.get_or_none(id=dto.visitor_photo) if dto.visitor_photo else None,
            "user": await SystemUser.get_or_none(id=dto.user) if dto.user else None,
        }
        return fk_relations

    @staticmethod
    async def check_for_suspicious_actions(system_user: SystemUser, visitor: Visitor,
                                           dto: access_dto.VisitorDto.UpdateDto, visitor_in_blacklist: bool) -> None:
        """Check for "suspicious" actions and save it to StrangerThings."""
        if visitor.pass_id and any((dto.first_name, dto.last_name, dto.middle_name)):
            # If changing FIO after pass_id has been assigned, save this event
            dct = {"before": await visitor.values_dict(),
                   "after": {key: value for key, value in dto.dict().items()
                             if key in ("first_name", "last_name", "middle_name") and value}}
            await StrangerThings.create(system_user=system_user, fio_changed=dct)

        if end_visit := await VisitSession.filter(visitor=visitor.id).order_by("-exit").first():
            # If changing Visitor data after visit, save this event
            time_now = datetime.now().astimezone()
            if end_visit.exit and time_now > end_visit.exit:
                dct = {"before": await visitor.values_dict(),
                       "after": {key: value for key, value in dto.dict().items() if value}}
                await StrangerThings.create(system_user=system_user, data_changed=dct)

        if visitor_in_blacklist:
            visitor_black_list_dict = {"visitor": await visitor.values_dict(),
                                       "visitor_in_blacklist": visitor_in_blacklist}
            await StrangerThings.create(system_user=system_user, pass_to_black_list=visitor_black_list_dict)

    @staticmethod
    async def notify_sec_officers(visitor: Visitor, user: SystemUser, emmit_func: Callable):
        email_struct, security_officers = await create_email_struct_for_sec_officers(visitor, user)
        # Send web push notifications
        subscriptions = await PushSubscription.filter(system_user__id__in=[user.id for user in security_officers])
        data = WebPush.ToCelery(subscriptions=subscriptions, title=email_struct.subject, body=email_struct.text,
                                url=None)
        await emmit_func(SendWebPushEvent(data=data))
        await emmit_func(NotifyVisitorInBlackListEvent(email_struct))

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.VisitorDto.CreationDto,
                     **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        if dto.passport and await Visitor.exists(passport=dto.passport, deleted=False):
            raise InconsistencyError(message="This visitor already exists.")

        fk_relations = await cls.get_visitor_fk_relations(dto)  # TODO rewrite CreationDto

        entity_kwargs = {
            field: value for field, value in dto.dict().items()
            if not (field in fk_relations or "date" in field)
        }

        date_of_birth = validate_date(dto.date_of_birth)
        visit_start_date = validate_datetime(dto.date_of_birth)
        visit_end_date = validate_datetime(dto.date_of_birth)

        # TODO :check buisness loginc with black list
        visitor = await Visitor.create(**entity_kwargs,
                                       **fk_relations,  # TODO remove after rewrite CreationDto
                                       date_of_birth=date_of_birth,
                                       visit_start_date=visit_start_date,
                                       visit_end_date=visit_end_date)
        visitor_in_black_list = await BlackList.exists(visitor=visitor)
        if visitor_in_black_list:
            await cls.notify_sec_officers(visitor=visitor, user=protection.user, emmit_func=emmit_func)

        if claim := fk_relations["claim"]:
            claim_way = await ClaimWay.get_or_none(claims=claim.id).prefetch_related(
                "system_users") if claim.claim_way else None
            if claim_way:
                await emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                    await create_email_struct(claim_way, claim=claim, time_before=True)))

        return visitor

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.VisitorDto.UpdateDto, **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        visitor = await Visitor.get_or_none(id=entity_id).prefetch_related("visit_session", "claim")
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={entity_id} does not exist.")

        visitor_in_black_list = await BlackList.exists(visitor=visitor)
        # if visitor_in_black_list:
        #     self.notify(
        #         NotifyVisitorInBlackListEvent(await self.collect_target_users(visitor, user=system_user)))

        fk_relations = await cls.get_visitor_fk_relations(dto)

        await cls.check_for_suspicious_actions(protection.user, visitor, dto, visitor_in_black_list)

        try:
            for field, value in dto.dict().items():
                if value:
                    if field == "pass_id" and visitor_in_black_list:
                        raise InconsistencyError(message=f"Visitor with id={entity_id} is in BlackList")

                    if field in fk_relations:
                        setattr(visitor, field, fk_relations.get(field))

                    elif field.startswith("date"):
                        setattr(visitor, field, validate_date(value))

                    elif field.endswith("date"):
                        setattr(visitor, field, validate_datetime(value))
                    else:
                        setattr(visitor, field, value)

            await visitor.save()

            if claim := fk_relations["claim"]:
                claim_way = await ClaimWay.get_or_none(id=claim.claim_way_id).prefetch_related(
                    "system_users") if claim.claim_way else None
                if claim_way:
                    emmit_func(NotifyUsersInClaimWayBeforeNminutesEvent(
                        await create_email_struct(claim_way, claim=claim, time_before=True)))

            if fk_relations["pass_id"] and visitor.claim and visitor.claim.system_user_id != protection.user.id:
                await WebPushService.create_web_push(user_id=[visitor.claim.system_user_id],
                                                     title=f"Выдан пропуск для {visitor}.",
                                                     body=f"{protection.user} назначил пропуск №{visitor.pass_id} посетителю {visitor}.",
                                                     url=None,
                                                     emmit_func=emmit_func)

            return visitor

        except exceptions.IntegrityError as ex:
            raise InconsistencyError(message=f"{ex}")


class VisitorPhotoLoader(BaseAccessLoader):

    @staticmethod
    async def convert_list_img_to_byte_string(
            dto: access_dto.VisitorPhotoDto.CreationDto | access_dto.VisitorPhotoDto.UpdateDto) -> None:
        """Receive images as list of bytes and convert it to byte string with separator"""
        separator = b"$"
        max_photo_to_upload: int = await get_system_settings(SystemSettingsTypes.MAX_PHOTO_UPLOAD)

        for field, value in dto.dict().items():
            if value:
                if isinstance(value, list):
                    if len(value) > max_photo_to_upload:
                        raise InconsistencyError(message=f"You can't upload more than {max_photo_to_upload} images.")
                    setattr(dto, field, separator.join(value))
                elif field.startswith("add_"):
                    setattr(dto, field, False)

    @classmethod
    async def work_with_images(cls,
                               dto: access_dto.VisitorPhotoDto.CreationDto | access_dto.VisitorPhotoDto.UpdateDto
                               ) -> None:
        """
        If watermark is True -> applying watermark to images
        and then convert them to byte string with separator
        """
        if dto.add_watermark_image:
            await WaterMarkUtil.apply_watermark(dto, w_type="image")

        if dto.add_watermark_text:
            await WaterMarkUtil.apply_watermark(dto, w_type="text")

        await cls.convert_list_img_to_byte_string(dto)

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity,
                     dto: access_dto.VisitorPhotoDto.CreationDto,
                     **kwargs) -> GenericDbType:

        if any((dto.webcam_img, dto.scan_img, dto.car_number_img)):
            await cls.work_with_images(dto)

        visitor_photo = await VisitorPhoto.create(**dto.dict())

        return visitor_photo

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.VisitorPhotoDto.UpdateDto, **kwargs) -> GenericDbType:
        visitor_photo = await VisitorPhoto.get_or_none(id=entity_id)
        if visitor_photo is None:
            raise InconsistencyError(message=f"VisitorPhoto with id={entity_id} does not exist.")

        if any((dto.webcam_img, dto.scan_img, dto.car_number_img)):
            await cls.work_with_images(dto)

        entity_kwargs = {field: value for field, value in dto.dict().items() if value}

        await visitor_photo.update_from_dict({**entity_kwargs})
        await visitor_photo.save()
        return visitor_photo


class ParkingTimeslotLoader(BaseAccessLoader):

    @staticmethod
    async def get_parking_place(_id: EntityId) -> ParkingPlace:
        parking_place = await ParkingPlace.get_or_none(id=_id)
        if parking_place is None:
            raise InconsistencyError(message=f"Parking place with id={_id} doesn't exist.")
        return parking_place

    @staticmethod
    async def check_time_interval(timeslot: timedelta) -> None:
        """Check if booking interval not more than SystemSettings.max_parking_time_hours"""
        max_parking_time_hours: int = await get_system_settings(SystemSettingsTypes.MAX_PARKING_TIME_HOURS)
        if timeslot > timedelta(hours=max_parking_time_hours):
            raise InconsistencyError(message=f"Time interval shouldn't be more than {max_parking_time_hours} hours. "
                                             f"Chosen interval = {str(timeslot)}")

    @staticmethod
    async def get_timeslots(start: datetime, end: datetime,
                            parking_place: ParkingPlace = None,
                            parking_timeslot: ParkingTimeslot = None) -> list[Optional[ParkingTimeslot]]:
        """Searching for timeslots with or without parking place, depends on provided time intervals"""
        p_t = parking_timeslot if parking_timeslot else ParkingTimeslot

        if parking_place:
            timeslots = await p_t.filter(
                Q(parking_place=parking_place) & Q(
                    Q(start__gte=start, end__lte=end) |
                    Q(start__lte=start, end__gte=start) |
                    Q(start__lte=end, end__gte=end) |
                    Q(start__lte=start, end__gte=end)
                )
            )
            if timeslots:
                raise InconsistencyError(message=f"For parking place: {parking_place}. "
                                                 f"This time interval:\n"
                                                 f"{start} - "
                                                 f"{end} already booked")
            return timeslots

        timeslots = await p_t.filter(
            Q(start__gte=start, end__lte=end) |
            Q(start__lte=start, end__gte=start) |
            Q(start__lte=end, end__gte=end) |
            Q(start__lte=start, end__gte=end)
        )
        return timeslots

    @staticmethod
    @atomic()
    async def create_strangerthings_sse_event(data: dict[str, Union[str, EntityId, dict]]) -> None:
        """
        Saving new event to DB.
        Then calling @post_save(StrangerThings) signal and publish it to SSE.
        """
        system_user = await SystemUser.get_or_none(id=data.pop("system_user"))
        parking_timeslot = await ParkingTimeslot.get_or_none(id=data.pop("parking_timeslot"))
        transport = await Transport.get_or_none(id=getattr(parking_timeslot, "transport_id"))
        parking_place = await ParkingPlace.get_or_none(id=getattr(parking_timeslot, "parking_place_id"))
        data.update(
            {
                "parking_timeslot": await parking_timeslot.values_dict(),
                "transport": await transport.values_dict(),
                "parking_place": await parking_place.values_dict()
            }
        )

        await StrangerThings.create(system_user=system_user, max_parking_time_hours=data)

    @staticmethod
    async def get_available_parking_place(timeslots: list[Optional[ParkingTimeslot]],
                                          start: datetime, end: datetime) -> ParkingPlace:
        """Returning Any available free ParkingPlace, which is not intersect with given timeslot"""
        parking_place = await ParkingPlace.filter(
            Q(parking_timeslot=None) |
            ~Q(id__in=[_.parking_place_id for _ in timeslots])
        ).first()
        if not parking_place:
            raise InconsistencyError(message=f"There is no available parking place for this time interval:\n"
                                             f"{start} - "
                                             f"{end}")
        return parking_place

    @staticmethod
    async def data_to_event(system_user: EntityId,
                            parking_timeslot: EntityId) -> dict[str, Union[str, EntityId, datetime]]:
        """Preparing data for MaxParkingTimeHoursExceededEvent"""
        max_parking_time_hours: int = await get_system_settings(SystemSettingsTypes.MAX_PARKING_TIME_HOURS)
        time_to_send: datetime = datetime.now().astimezone() + timedelta(hours=max_parking_time_hours)
        data = {
            "system_user": system_user,
            "parking_timeslot": parking_timeslot,
            "time_to_send": time_to_send,
            "message": "Превышено максимально допустимое время нахождения гостевого автомобиля на парковке."
        }
        return data

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity,
                     dto: access_dto.ParkingTimeslotDto.CreationDto,
                     **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        transport = await Transport.get_or_none(id=dto.transport)
        if transport is None:
            raise InconsistencyError(message=f"Transport with id={dto.transport} does not exist.")

        minutes: int = await get_system_settings(SystemSettingsTypes.PARKING_TIMESLOT_INTERVAL)
        start = datetime.fromisoformat(validate_datetime(dto.start))
        end = datetime.fromisoformat(validate_datetime(dto.end)) + timedelta(minutes=minutes)
        timeslot = end - start
        await cls.check_time_interval(timeslot)

        if dto.parking_place:
            parking_place = await cls.get_parking_place(dto.parking_place)
            await cls.get_timeslots(start, end, parking_place)
        else:
            timeslots = await cls.get_timeslots(start, end)
            parking_place = await cls.get_available_parking_place(timeslots, start, end)

        parking_timeslot = await ParkingTimeslot.create(start=start,
                                                        end=end,
                                                        timeslot=str(timeslot),
                                                        parking_place=parking_place,
                                                        transport=transport)
        await emmit_func(
            MaxParkingTimeHoursExceededEvent(await cls.data_to_event(protection.user.id, parking_timeslot.id)))

        return parking_timeslot

    @classmethod
    @atomic()
    async def update(cls, model: GenericDbType, entity_id: EntityId, protection: UserIdentity,
                     dto: access_dto.ParkingTimeslotDto.UpdateDto, **kwargs) -> GenericDbType:
        emmit_func = kwargs.pop("emmit_func", None)
        parking_timeslot = await ParkingTimeslot.get_or_none(id=entity_id)
        if parking_timeslot is None:
            raise InconsistencyError(message=f"Parking timeslot with id={entity_id} does not exist.")

        transport = await Transport.get_or_none(id=dto.transport)
        if transport is None:
            raise InconsistencyError(message=f"Transport with id={dto.transport} does not exist.")

        minutes: int = await get_system_settings(SystemSettingsTypes.PARKING_TIMESLOT_INTERVAL)

        start = datetime.fromisoformat(validate_datetime(dto.start)) \
            if dto.start else getattr(parking_timeslot, "start")
        end = getattr(parking_timeslot, "end") \
            if not dto.end else datetime.fromisoformat(validate_datetime(dto.end)) + timedelta(minutes=minutes)

        timeslot: timedelta = end - start
        await cls.check_time_interval(timeslot)

        if dto.parking_place:
            parking_place = await cls.get_parking_place(dto.parking_place)
            await cls.get_timeslots(start, end, parking_place, parking_timeslot)
        else:
            timeslots = await cls.get_timeslots(start, end)
            parking_place = await cls.get_available_parking_place(timeslots, start, end)

        setattr(parking_timeslot, "start", start)
        setattr(parking_timeslot, "end", end)
        setattr(parking_timeslot, "timeslot", str(timeslot))
        setattr(parking_timeslot, "parking_place", parking_place)
        setattr(parking_timeslot, "transport", transport)

        await parking_timeslot.save()
        return parking_timeslot


class PassLoader(BaseAccessLoader):

    @staticmethod
    async def generate_rfid() -> int:
        pass_id = await Pass.filter().order_by("-rfid").first()
        if not pass_id:
            return 1
        return pass_id.rfid + 1

    @classmethod
    @atomic()
    async def create(cls, model: GenericDbType, protection: UserIdentity, dto: access_dto.PassDto.CreationDto,
                     **kwargs) -> GenericDbType:
        if not dto.rfid:
            rfid = await cls.generate_rfid()
            setattr(dto, "rfid", rfid)
            dto.rfid = rfid
        return await BaseAccessLoader.create(model, protection, dto, **kwargs)
