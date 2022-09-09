from typing import Type

from pydantic import BaseModel
from sanic import Request
from sanic.exceptions import NotFound
from sanic.response import HTTPResponse, json
from sanic.views import HTTPMethodView

from application.access.access import (ClaimToZoneAccess, ClaimWayAccess,
                                       ParkingAccess, ParkingPlaceAccess,
                                       RoleAccess, ScopeConstructorAccess,
                                       SystemUserAccess, ZoneAccess, BuildingAccess, DivisionAccess, OrganisationAccess,
                                       JobTitleAccess)
from application.access.base_access import BaseAccess
from core.dto import access, validate
from core.dto.access import EntityId
from core.dto.service import ScopeConstructor
from core.server.auth import protect
from core.utils.limit_offset import get_limit_offset


class BaseAccessController(HTTPMethodView):
    enabled_scopes: list[str] | str
    entity_name: str
    identity_type: Type
    post_dto: Type[BaseModel]
    put_dto: Type[BaseModel]
    access_type: Type[BaseAccess]

    @staticmethod
    def validate(dto_type: Type[BaseModel], request: Request) -> Type[BaseModel]:
        return validate(dto_type, request)

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
        if entity is None:
            limit, offset = await get_limit_offset(request)
            models = await request.app.ctx.access_registry.get(self.access_type).read_all(limit, offset)
            return json([await model.values_dict() for model in models])

        model = await request.app.ctx.access_registry.get(self.access_type).read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True, fk_fields=True, o2o_fields=True))
        else:
            raise NotFound()

    @protect()
    async def post(self, request: Request, user: EntityId) -> HTTPResponse:
        dto = self.validate(self.post_dto, request)
        model = await request.app.ctx.access_registry.get(self.access_type).create(user, dto)
        return json(await model.values_dict())

    @protect()
    async def put(self, request: Request, user: EntityId, entity: EntityId = None) -> HTTPResponse:
        dto = self.validate(self.put_dto, request)
        return json(await request.app.ctx.access_registry.get(self.access_type).update(user, entity, dto))

    @protect()
    async def delete(self, request: Request, user: EntityId, entity: EntityId = None) -> HTTPResponse:
        return json(await request.app.ctx.access_registry.get(self.access_type).delete(user, entity))


class ScopeConstructorController(BaseAccessController):
    entity_name = 'set-scopes'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = None
    put_dto = ScopeConstructor.UpdateDto
    access_type = ScopeConstructorAccess

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
        if entity is None:
            limit, offset = await get_limit_offset(request)
            models = await request.app.ctx.access_registry.get(self.access_type).read_all(limit, offset)
            return json([await model.values_dict(m2m_fields=True) for model in models])

        model = await request.app.ctx.access_registry.get(self.access_type).read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True))
        else:
            raise NotFound()

    @protect()
    async def put(self, request: Request, user: EntityId, entity: EntityId = None) -> HTTPResponse:
        dto = self.validate(self.put_dto, request)
        return json(await request.app.ctx.access_registry.get(self.access_type).update(user, entity, dto, request))


class SystemUserController(BaseAccessController):
    entity_name = 'users'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.SystemUser.CreationDto
    put_dto = access.SystemUser.UpdateDto
    access_type = SystemUserAccess


class ZoneController(BaseAccessController):
    entity_name = 'zones'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.Zone.CreationDto
    put_dto = access.Zone.UpdateDto
    access_type = ZoneAccess


class ClaimWayController(BaseAccessController):
    entity_name = 'claimways'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.ClaimWay.CreationDto
    put_dto = access.ClaimWay.UpdateDto
    access_type = ClaimWayAccess

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
        if entity is None:
            limit, offset = await get_limit_offset(request)
            models = await request.app.ctx.access_registry.get(self.access_type).read_all(limit, offset)
            return json([await model.values_dict(m2m_fields=True) for model in models])

        model = await request.app.ctx.access_registry.get(self.access_type).read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True, fk_fields=True, o2o_fields=True))
        else:
            raise NotFound()


class ClaimToZoneController(BaseAccessController):
    entity_name = 'claimtozones'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.ClaimToZone.CreationDto
    put_dto = access.ClaimToZone.UpdateDto
    access_type = ClaimToZoneAccess


class ParkingPlaceController(BaseAccessController):
    entity_name = 'parkingplaces'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.ParkingPlace.CreationDto
    put_dto = access.ParkingPlace.UpdateDto
    access_type = ParkingPlaceAccess


class ParkingPlaceBulkCreateDeleteController(BaseAccessController):
    entity_name = 'parkingplaces/mass-create-delete'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.ParkingPlace.BulkCreateDto
    put_dto = None
    access_type = ParkingPlaceAccess

    @protect()
    async def post(self, request: Request, user: EntityId) -> HTTPResponse:
        dto = self.validate(self.post_dto, request)
        models = await request.app.ctx.access_registry.get(self.access_type).mass_create(user, dto)
        return json({"parking_places": [await model.values_dict() for model in models]})

    @protect()
    async def delete(self, request: Request, user: EntityId, entity: EntityId = None) -> HTTPResponse:
        return json(await request.app.ctx.access_registry.get(self.access_type).mass_delete())


class ParkingController(BaseAccessController):
    entity_name = 'parkings'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.Parking.CreationDto
    put_dto = access.Parking.UpdateDto
    access_type = ParkingAccess


class RoleController(BaseAccessController):
    entity_name = 'roles'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.Role.CreationDto
    put_dto = access.Role.UpdateDto
    access_type = RoleAccess


class BuildingController(BaseAccessController):
    entity_name = 'buildings'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.BuildingDto.CreationDto
    put_dto = access.BuildingDto.UpdateDto
    access_type = BuildingAccess


class DivisionController(BaseAccessController):
    entity_name = 'divisions'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.DivisionDto.CreationDto
    put_dto = access.DivisionDto.UpdateDto
    access_type = DivisionAccess


class OrganisationController(BaseAccessController):
    entity_name = 'organisations'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.OrganisationDto.CreationDto
    put_dto = access.OrganisationDto.UpdateDto
    access_type = OrganisationAccess


class JobTitleController(BaseAccessController):
    entity_name = 'job-titles'
    enabled_scopes = ["root", "Администратор"]
    identity_type = int
    post_dto = access.JobTitleDto.CreationDto
    put_dto = access.JobTitleDto.UpdateDto
    access_type = JobTitleAccess
