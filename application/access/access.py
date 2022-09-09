from sanic import Request
from tortoise import exceptions
from tortoise.queryset import Q
from tortoise.transactions import atomic

import settings
from application.access.base_access import BaseAccess
from application.exceptions import InconsistencyError
from core.dto import access
from core.dto.access import EntityId
from core.dto.service import ScopeConstructor
from core.utils.crypto import BaseCrypto
from core.utils.license_count import SysUserLicenses
from infrastructure.database.models import (MODEL, Building, Claim,
                                            ClaimToZone, ClaimWay, Division,
                                            EnableScope, JobTitle,
                                            Organisation, Parking,
                                            ParkingPlace, Pass, Role,
                                            StrangerThings, SystemUser, Zone)
from infrastructure.database.repository import EntityRepository


class SystemUserAccess(BaseAccess):
    target_model = SystemUser

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.SystemUser.CreationDto) -> SystemUser:
        await EntityRepository.check_exist(self.target_model, username=dto.username, deleted=False)

        license_count: int = SysUserLicenses.role_count
        licenses: int = await settings.system_settings("max_systemuser_license")
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

            roles = await Role.filter(id__in=dto.scopes)
            await system_user.scopes.add(*roles)
            await SysUserLicenses.increment_count()
            return system_user

        except exceptions.ValidationError as ex:
            raise InconsistencyError(message=f"There is validation problem with {ex}.")

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.SystemUser.UpdateDto) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(SystemUser, entity_id)
        system_user = await SystemUser.get_or_none(id=entity_id)

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
                        roles = await Role.filter(id__in=value)
                        await system_user.scopes.clear()
                        await system_user.scopes.add(*roles)
                    else:
                        setattr(system_user, field, value)

            await system_user.save()
            return entity_id

        except exceptions.ValidationError as ex:
            raise InconsistencyError(message=f"There is validation problem with {ex}.")

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(SystemUser, entity_id)
        await SystemUser.filter(id=entity_id).update(deleted=True)
        await SysUserLicenses.decrement_count()
        return entity_id


class ZoneAccess(BaseAccess):
    target_model = Zone

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.Zone.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.Zone.UpdateDto) -> EntityId:
        return await super().update(system_user, entity_id, dto)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class ClaimWayAccess(BaseAccess):
    target_model = ClaimWay

    @staticmethod
    async def add_roles_and_users(claim_way: ClaimWay,
                                  dto: access.ClaimWay.CreationDto | access.ClaimWay.UpdateDto) -> None:
        """Add Roles and SystemUsers to ClaimWay"""
        if dto.system_users:
            sys_users = await SystemUser.filter(id__in=dto.system_users)
            if len(sys_users) != len(dto.system_users):
                raise InconsistencyError(message=f"Couldn't find some users with id={dto.system_users}.")
            await claim_way.system_users.clear()
            await claim_way.system_users.add(*sys_users)

        if dto.roles:
            roles = await Role.filter(id__in=dto.roles)
            if len(roles) != len(dto.roles):
                raise InconsistencyError(message=f"Couldn't find some roles with id={dto.roles}.")
            await claim_way.roles.clear()
            await claim_way.roles.add(*roles)

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.ClaimWay.CreationDto) -> ClaimWay:
        claim_way = await ClaimWay.create()
        await self.add_roles_and_users(claim_way, dto)
        return claim_way

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.ClaimWay.UpdateDto) -> EntityId:
        claim_way = await ClaimWay.get_or_none(id=entity_id)
        if claim_way is None:
            raise InconsistencyError(message=f"ClaimWay with id={entity_id} does not exist.")

        dct = {
            "before": await claim_way.values_dict(m2m_fields=True),
            "after": {}
        }

        await self.add_roles_and_users(claim_way, dto)
        dct["after"] = await claim_way.values_dict(m2m_fields=True)
        await StrangerThings.create(system_user=system_user, claim_way_changed=dct)

        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class ClaimToZoneAccess(BaseAccess):
    target_model = ClaimToZone

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.ClaimToZone.CreationDto) -> ClaimToZone:
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

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.ClaimToZone.UpdateDto) -> EntityId:
        claim_to_zone = await self.read(entity_id)
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
        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class RoleAccess(BaseAccess):
    target_model = Role

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.Role.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.Role.UpdateDto) -> EntityId:
        return await super().update(system_user, entity_id, dto)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class ScopeConstructorAccess(BaseAccess):
    target_model = EnableScope

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: ScopeConstructor.UpdateDto) -> MODEL:
        raise InconsistencyError(message="Creating new scopes is prohibited.")

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: ScopeConstructor.UpdateDto,
                     request: Request) -> EntityId:
        enable_scope = await EnableScope.get_or_none(id=entity_id).prefetch_related("scopes")
        if enable_scope is None:
            raise InconsistencyError(message=f"Scope with id={entity_id} doesn't exist.")

        roles = await Role.filter(Q(id__in=dto.scopes) | Q(name="root") | Q(name="Администратор"))
        if len(roles) != len(set(dto.scopes)) + 2:
            raise InconsistencyError(message=f"Some roles with id={dto.scopes} were not found.")

        await enable_scope.scopes.clear()
        await enable_scope.scopes.add(*roles)

        # Sending signal to update scopes in controller
        await request.app.dispatch(
            "controller.enabled_scopes.changed",
            context={"enable_scope_name": enable_scope.name,
                     "scopes": [scope.name for scope in await enable_scope.scopes.all()]}
        )
        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        raise InconsistencyError(message="Deleting scopes is prohibited.")


class ParkingAccess(BaseAccess):
    target_model = Parking

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.Parking.CreationDto) -> Parking:

        entity_kwargs = {field: value for field, value in dto.dict().items() if value}
        parking = await Parking.create(**entity_kwargs)

        for i in range(1, parking.max_places + 1):
            await ParkingPlace.create(real_number=i, parking=parking)

        return parking

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.Parking.UpdateDto) -> EntityId:
        parking = await Parking.get_or_none(id=entity_id)
        if parking is None:
            raise InconsistencyError(message=f"Parking with id={entity_id} does not exist")

        for field, value in dto.dict().items():
            if value:
                setattr(parking, field, value)

        if dto.max_places:
            await ParkingPlace.all().delete()
            for i in range(1, parking.max_places + 1):
                await ParkingPlace.create(real_number=i, parking=parking)

        await parking.save()
        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class ParkingPlaceAccess(BaseAccess):
    target_model = ParkingPlace

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.ParkingPlace.CreationDto) -> ParkingPlace:
        parking = await Parking.get_or_none(id=dto.parking)
        if parking is None:
            raise InconsistencyError(message=f"Parking with id={dto.parking} doesn't exist.")

        parking_place = await ParkingPlace.create(real_number=dto.real_number, parking=parking)
        return parking_place

    @atomic(settings.CONNECTION_NAME)
    async def update(self,
                     system_user: SystemUser,
                     entity_id: EntityId,
                     dto: access.ParkingPlace.UpdateDto) -> EntityId:
        parking_place = await self.read(entity_id)
        if parking_place is None:
            raise InconsistencyError(message=f"ParkingPlace with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                setattr(parking_place, field, value)

        await parking_place.save()
        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)

    @atomic(settings.CONNECTION_NAME)
    async def mass_create(self, system_user: SystemUser, dto: access.ParkingPlace.BulkCreateDto) -> list[ParkingPlace]:
        parking = await Parking.get_or_none(id=dto.parking)

        for i in range(1, parking.max_places + 1):
            await ParkingPlace.create(real_number=i, parking=parking)

        parking_places = await ParkingPlace.all()
        return parking_places

    @atomic(settings.CONNECTION_NAME)
    async def mass_delete(self) -> str:
        await ParkingPlace.all().delete()
        return "All parking places was deleted."


class BuildingAccess(BaseAccess):
    target_model = Building

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.BuildingDto.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.BuildingDto.UpdateDto) -> EntityId:
        return await super().update(system_user, entity_id, dto)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class DivisionAccess(BaseAccess):
    target_model = Division

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.DivisionDto.CreationDto) -> MODEL:
        subdivision = None
        if dto.subdivision:
            subdivision = await Division.get_or_none(id=dto.subdivision)

        entity = await Division.create(name=dto.name, email=dto.email,
                                       subdivision=subdivision if dto.subdivision else None)
        return entity

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: access.DivisionDto.UpdateDto) -> EntityId:
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

        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class OrganisationAccess(BaseAccess):
    target_model = Organisation

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.OrganisationDto.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: access.OrganisationDto.UpdateDto) -> EntityId:
        return await super().update(system_user, entity_id, dto)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class JobTitleAccess(BaseAccess):
    target_model = JobTitle

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: access.JobTitleDto.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: access.JobTitleDto.UpdateDto) -> EntityId:
        return await super().update(system_user, entity_id, dto)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)
