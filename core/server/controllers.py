from typing import Optional, List, Type, Union
from pydantic import BaseModel
from sanic import Request
from sanic.exceptions import NotFound
from sanic.response import HTTPResponse, json
from sanic.views import HTTPMethodView

from application.access.access import (SystemUserAccess,
                                       ZoneAccess,
                                       ClaimWayAccess,
                                       ClaimToZoneAccess,
                                       ParkingPlaceAccess,
                                       ParkingAccess,
                                       RoleAccess,
                                       ScopeConstructorAccess)
from application.access.base_access import BaseAccess
from core.dto import validate, access
from core.dto.access import EntityId
from core.server.auth import protect
from core.dto.service import ScopeConstructor


class BaseAccessController(HTTPMethodView):
    enabled_scopes: Union[List[str], str]
    entity_name: str
    identity_type: Type
    post_dto: BaseModel
    put_dto: BaseModel
    access_type: BaseAccess

    @staticmethod
    def validate(dto_type: BaseModel, request: Request) -> BaseModel:
        return validate(dto_type, request)

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None
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
    async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None
            models = await request.app.ctx.access_registry.get(self.access_type).read_all(limit, offset)
            return json([await model.values_dict(m2m_fields=True) for model in models])

        model = await request.app.ctx.access_registry.get(self.access_type).read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True))
        else:
            raise NotFound()

    @protect()
    async def put(self, request: Request, user: EntityId, entity: EntityId = None) -> HTTPResponse:
        dto = self.validate(self.put_dto, request)  # type: ignore
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
    async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None
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
        dto = self.validate(self.post_dto, request)  # type: ignore
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
