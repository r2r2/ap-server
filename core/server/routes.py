from typing import Union, List, Optional, Type

import settings
from pydantic import BaseModel
from sanic import Request
from sanic.exceptions import NotFound
from sanic.response import HTTPResponse, json
from sanic.views import HTTPMethodView

from application.service.parking import ParkingTimeslotService
from application.service.black_list import BlackListService
from application.service.system_settings import SystemSettingsService
from core.dto import validate
from core.server.auth import protect
from core.dto.access import EntityId
from core.dto.service import (ClaimDto,
                              VisitorDto,
                              PassportDto,
                              MilitaryIdDto,
                              VisitSessionDto,
                              DriveLicenseDto,
                              PassDto,
                              TransportDto,
                              BlackListDto,
                              VisitorPhotoDto,
                              WaterMarkDto,
                              ParkingTimeslotDto,
                              InternationalPassportDto,
                              SystemSettingsDto)
from infrastructure.database.models import (AbstractBaseModel,
                                            SystemUser,
                                            Claim,
                                            Visitor,
                                            Passport,
                                            MilitaryId,
                                            VisitSession,
                                            DriveLicense,
                                            Pass,
                                            Transport,
                                            BlackList,
                                            VisitorPhoto,
                                            WaterMark,
                                            ParkingTimeslot,
                                            InternationalPassport,
                                            SystemSettings,
                                            ClaimWayApproval)
from application.service.base_service import BaseService
from application.service.claim import ClaimService
from application.service.visitor import (VisitorService,
                                         PassportService,
                                         MilitaryIdService,
                                         VisitSessionService,
                                         DriveLicenseService,
                                         PassService,
                                         TransportService,
                                         VisitorPhotoService,
                                         WaterMarkService,
                                         InternationalPassportService)
from application.exceptions import InconsistencyError


class BaseServiceController(HTTPMethodView):
    enabled_scopes: Union[List[str], str]
    target_route: str
    target_service: BaseService
    returned_model: AbstractBaseModel
    post_dto: BaseModel
    put_dto: BaseModel

    @staticmethod
    def validate(dto_type: BaseModel | Type[BaseModel], request: Request) -> BaseModel:
        return validate(dto_type, request)

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None
            models = await request.app.ctx.service_registry.get(self.target_service).read_all(limit, offset)
            return json([await model.values_dict() for model in models])

        model = await request.app.ctx.service_registry.get(self.target_service).read(entity)
        if model:
            return json(await model.values_dict(m2m_fields=True, fk_fields=True,
                                                o2o_fields=True, backward_fk_fields=True))
        else:
            raise NotFound()

    @protect()
    async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
        dto = self.validate(self.post_dto, request)
        service_name: BaseServiceController.target_service = request.app.ctx.service_registry.get(self.target_service)
        model = await service_name.create(system_user, dto)
        return json(await model.values_dict())

    @protect()
    async def put(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
        dto = self.validate(self.put_dto, request)
        service_name: BaseServiceController.target_service = request.app.ctx.service_registry.get(self.target_service)
        model = await service_name.update(system_user, entity, dto)
        return json(await model.values_dict())

    @protect()
    async def delete(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
        service_name: BaseServiceController.target_service = request.app.ctx.service_registry.get(self.target_service)
        model = await service_name.delete(system_user, entity)
        return json(model)


class ClaimController:
    returned_model = Claim

    class Create(BaseServiceController):
        enabled_scopes = ["root", "Администратор"]
        target_route = "/claims"
        target_service = ClaimService
        post_dto = ClaimDto.CreationDto

        @protect(retrive_user=False)
        async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
            if entity is None:
                limit = request.args.get("limit")
                offset = request.args.get("offset")
                limit = int(limit) if limit and limit.isdigit() else None
                offset = int(offset) if offset and offset.isdigit() else None
                models = await request.app.ctx.service_registry.get(self.target_service).read_all(limit, offset)
                return json([await model.values_dict(m2m_fields=True, fk_fields=True,
                                                     o2o_fields=True, backward_fk_fields=True) for model in models])

            model = await request.app.ctx.service_registry.get(self.target_service).read(entity)
            if model:
                return json(await model.values_dict(m2m_fields=True, fk_fields=True,
                                                    o2o_fields=True, backward_fk_fields=True))
            else:
                raise NotFound()

    class Update(BaseServiceController):
        enabled_scopes = ["root", "Администратор"]
        target_route = "/claims/<entity:int>"
        target_service = ClaimService
        put_dto = ClaimDto.UpdateDto

    class ApproveClaim(BaseServiceController):
        returned_model = ClaimWayApproval
        enabled_scopes = ["root", "Администратор"]
        target_route = "/claims/<entity:int>/approve"
        target_service = ClaimService
        put_dto = ClaimDto.ApproveDto

        @protect()
        async def put(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
            dto = self.validate(self.put_dto, request)
            service_name: ClaimService = request.app.ctx.service_registry.get(self.target_service)
            model = await service_name.system_user_approve_claim(system_user, entity, dto)  # type: ignore
            return json(await model.values_dict())

    class UploadExcelClaim(BaseServiceController):
        enabled_scopes = ["root", "Администратор"]
        target_route = "/claims/upload-excel"
        target_service = ClaimService
        post_dto = ClaimDto.GroupVisitDto

        @protect(retrive_user=False)
        async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
            with open(f"{settings.BASE_DIR}/static/sample_excel.txt", "rb") as f:
                data = f.read().decode(encoding="utf-8")
                return json(data)

        @protect()
        async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
            dto = self.validate(self.post_dto, request)
            service_name: ClaimService = request.app.ctx.service_registry.get(self.target_service)
            model = await service_name.upload_excel(system_user, dto)
            return json(model)

        @protect()
        async def put(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
            raise InconsistencyError(message=f"PUT request is prohibited for this route.")

        @protect()
        async def delete(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
            raise InconsistencyError(message=f"DELETE request is prohibited for this route.")


class VisitorController:
    returned_model = Visitor

    class Create(BaseServiceController):
        enabled_scopes = ["root", "Администратор"]
        target_route = "/visitors"
        post_dto = VisitorDto.CreationDto
        target_service = VisitorService

    class Update(BaseServiceController):
        enabled_scopes = ["root", "Администратор"]
        target_route = "/visitors/<entity:int>"
        put_dto = VisitorDto.UpdateDto
        target_service = VisitorService

    class VisitInfo(BaseServiceController):
        """Данные о конкретном посещении."""
        enabled_scopes = ["root", "Администратор"]
        target_route = "/visitors/<entity:int>/visit-info"
        target_service = VisitorService

        @protect(retrive_user=False)
        async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
            visit_info = await request.app.ctx.service_registry.get(self.target_service).get_info_about_current_visit(
                entity)
            return json(visit_info)


class PassportController:
    returned_model = Passport

    class Create(BaseServiceController):
        target_route = "/passports"
        enabled_scopes = ["root", "Администратор"]
        target_service = PassportService
        post_dto = PassportDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/passports/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = PassportService
        put_dto = PassportDto.UpdateDto


class InternationalPassportController:
    returned_model = InternationalPassport

    class Create(BaseServiceController):
        target_route = "/international-passports"
        enabled_scopes = ["root", "Администратор"]
        target_service = InternationalPassportService
        post_dto = InternationalPassportDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/international-passports/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = InternationalPassportService
        put_dto = InternationalPassportDto.UpdateDto


class MilitaryIdController:
    returned_model = MilitaryId

    class Create(BaseServiceController):
        target_route = "/militaryids"
        enabled_scopes = ["root", "Администратор"]
        target_service = MilitaryIdService
        post_dto = MilitaryIdDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/militaryids/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = MilitaryIdService
        put_dto = MilitaryIdDto.UpdateDto


class VisitSessionController:
    returned_model = VisitSession

    class Create(BaseServiceController):
        target_route = "/visitsessions"
        enabled_scopes = ["root", "Администратор"]
        target_service = VisitSessionService
        post_dto = VisitSessionDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/visitsessions/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = VisitSessionService
        put_dto = VisitSessionDto.UpdateDto


class DriveLicenseController:
    returned_model = DriveLicense

    class Create(BaseServiceController):
        target_route = "/drivelicenses"
        enabled_scopes = ["root", "Администратор"]
        target_service = DriveLicenseService
        post_dto = DriveLicenseDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/drivelicenses/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = DriveLicenseService
        put_dto = DriveLicenseDto.UpdateDto


class PassController:
    returned_model = Pass

    class Create(BaseServiceController):
        target_route = "/passes"
        enabled_scopes = ["root", "Администратор"]
        target_service = PassService
        post_dto = PassDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/passes/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = PassService
        put_dto = PassDto.UpdateDto


class TransportController:
    returned_model = Transport

    class Create(BaseServiceController):
        target_route = "/transports"
        enabled_scopes = ["root", "Администратор"]
        target_service = TransportService
        post_dto = TransportDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/transports/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = TransportService
        put_dto = TransportDto.UpdateDto


class ParkingTimeslotController:
    returned_model = ParkingTimeslot

    class Create(BaseServiceController):
        target_route = "/parking-timeslots"
        enabled_scopes = ["root", "Администратор"]
        target_service = ParkingTimeslotService
        post_dto = ParkingTimeslotDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/parking-timeslots/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = ParkingTimeslotService
        put_dto = ParkingTimeslotDto.UpdateDto


class BlackListController:
    returned_model = BlackList

    class Create(BaseServiceController):
        target_route = "/blacklists"
        enabled_scopes = ["root", "Администратор"]
        target_service = BlackListService
        post_dto = BlackListDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/blacklists/<entity:int>"
        enabled_scopes = ["root", "Администратор"]
        target_service = BlackListService
        put_dto = BlackListDto.UpdateDto


class VisitorPhotoController:
    returned_model = VisitorPhoto

    class Create(BaseServiceController):
        target_route = "/visitorphotos"
        enabled_scopes = ['root', "Администратор"]
        target_service = VisitorPhotoService
        post_dto = VisitorPhotoDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/visitorphotos/<entity:int>"
        enabled_scopes = ['root', "Администратор"]
        target_service = VisitorPhotoService
        put_dto = VisitorPhotoDto.UpdateDto


class WaterMarkController:
    returned_model = WaterMark

    class Create(BaseServiceController):
        target_route = "/watermarks"
        enabled_scopes = ['root', "Администратор"]
        target_service = WaterMarkService
        post_dto = WaterMarkDto.CreationDto

    class Update(BaseServiceController):
        target_route = "/watermarks/<entity:int>"
        enabled_scopes = ['root', "Администратор"]
        target_service = WaterMarkService
        put_dto = WaterMarkDto.UpdateDto


class SystemSettingsController(BaseServiceController):
    returned_model = SystemSettings
    target_route = "/system-settings"
    enabled_scopes = ['root', "Администратор"]
    target_service = SystemSettingsService
    put_dto = SystemSettingsDto

    @protect()
    async def post(self, request: Request, user: EntityId) -> InconsistencyError:
        raise InconsistencyError(message="Creating new settings is prohibited.")

    @protect()
    async def put(self, request: Request, system_user: SystemUser) -> HTTPResponse:
        dto = self.validate(self.put_dto, request)  # type: ignore
        service_name: SystemSettingsService = request.app.ctx.service_registry.get(self.target_service)
        model = await service_name.update(system_user, dto)  # type: ignore
        return json(await model.values_dict())

    @protect()
    async def delete(self, request: Request, user: EntityId, entity: EntityId = None) -> InconsistencyError:
        raise InconsistencyError(message="Deleting settings is prohibited.")
