# from typing import Type
#
# from pydantic import BaseModel
# from sanic import Request
# from sanic.exceptions import NotFound
# from sanic.response import HTTPResponse, json
# from sanic.views import HTTPMethodView
#
# import settings
# from application.exceptions import InconsistencyError
# from application.service.base_service import BaseService
# from application.service.black_list import BlackListService
# from application.service.claim import ClaimService
# from application.service.parking import ParkingTimeslotService
# from application.service.system_settings import SystemSettingsService
# from application.service.visitor import (DriveLicenseService,
#                                          InternationalPassportService,
#                                          MilitaryIdService, PassportService,
#                                          PassService, TransportService,
#                                          VisitorPhotoService, VisitorService,
#                                          VisitSessionService, WaterMarkService)
# from core.dto import validate
# from core.dto.access import EntityId
# from core.dto.service import (BlackListDto, ClaimDto, DriveLicenseDto,
#                               InternationalPassportDto, MilitaryIdDto,
#                               ParkingTimeslotDto, PassDto, PassportDto,
#                               SystemSettingsDto, TransportDto, VisitorDto,
#                               VisitorPhotoDto, VisitSessionDto, WaterMarkDto)
# from core.server.auth import protect
# from asbp_app.utils.limit_offset import get_limit_offset
# from infrastructure.database.models import (MODEL, BlackList, Claim,
#                                             ClaimWayApproval, DriveLicense,
#                                             InternationalPassport, MilitaryId,
#                                             ParkingTimeslot, Pass, Passport,
#                                             SystemSettings, SystemUser,
#                                             Transport, Visitor, VisitorPhoto,
#                                             VisitSession, WaterMark)
#

# class ClaimController:
#     returned_model = Claim
#
#     # class Create(BaseServiceController):
#     #     enabled_scopes = ["root", "Администратор"]
#     #     target_route = "/claims"
#     #     target_service = ClaimService
#     #     post_dto = ClaimDto.CreationDto
#
#         # @protect(retrive_user=False)
#         # async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
#         #     if entity is None:
#         #         limit, offset = await get_limit_offset(request)
#         #         models = await request.app.ctx.service_registry.get(self.target_service).read_all(limit, offset)
#         #         total: int = await Claim.all().count()
#         #         return json([await model.values_dict(m2m_fields=True, fk_fields=True,
#         #                                              o2o_fields=True, backward_fk_fields=True) for model in models] + [
#         #                         {"total": total}])
#         #     model = await request.app.ctx.service_registry.get(self.target_service).read(entity)
#         #     if model:
#         #         return json(await model.values_dict(m2m_fields=True, fk_fields=True,
#         #                                             o2o_fields=True, backward_fk_fields=True))
#         #     else:
#         #         raise NotFound()
#
#     # class Update(BaseServiceController):
#     #     enabled_scopes = ["root", "Администратор"]
#     #     target_route = "/claims/<entity:int>"
#     #     target_service = ClaimService
#     #     put_dto = ClaimDto.UpdateDto
#
#     # class ApproveClaim(BaseServiceController):
#     #     returned_model = ClaimWayApproval
#     #     enabled_scopes = ["root", "Администратор"]
#     #     target_route = "/claims/<entity:int>/approve"
#     #     target_service = ClaimService
#     #     put_dto = ClaimDto.ApproveDto
#     #
#     #     @protect()
#     #     async def put(self, request: Request, system_user: SystemUser, entity: EntityId) -> HTTPResponse:
#     #         dto = self.validate(self.put_dto, request)
#     #         service_name: ClaimService = request.app.ctx.service_registry.get(self.target_service)
#     #         model = await service_name.system_user_approve_claim(system_user, entity, dto)  # type: ignore
#     #         return json(await model.values_dict())
#
#     class UploadExcelClaim(BaseServiceController):
#         enabled_scopes = ["root", "Администратор"]
#         target_route = "/claims/upload-excel"
#         target_service = ClaimService
#         post_dto = ClaimDto.GroupVisitDto
#
#         @protect(retrive_user=False)
#         async def get(self, request: Request, entity: EntityId | None = None) -> HTTPResponse:
#             with open(f"{settings.BASE_DIR}/static/sample_excel.txt", "rb") as f:
#                 data = f.read().decode(encoding="utf-8")
#                 return json(data)
#
#         @protect()
#         async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
#             dto = self.validate(self.post_dto, request)
#             service_name: ClaimService = request.app.ctx.service_registry.get(self.target_service)
#             model = await service_name.upload_excel(system_user, dto)
#             return json(model)


# class VisitorController:
#     returned_model = Visitor

    # class Create(BaseServiceController):
    #     enabled_scopes = ["root", "Администратор"]
    #     target_route = "/visitors"
    #     post_dto = VisitorDto.CreationDto
    #     target_service = VisitorService
    #
    # class Update(BaseServiceController):
    #     enabled_scopes = ["root", "Администратор"]
    #     target_route = "/visitors/<entity:int>"
    #     put_dto = VisitorDto.UpdateDto
    #     target_service = VisitorService
    #
    # class VisitInfo(BaseServiceController):
    #     """Данные о конкретном посещении."""
    #     enabled_scopes = ["root", "Администратор"]
    #     target_route = "/visitors/<entity:int>/visit-info"
    #     target_service = VisitorService
    #
    #     @protect(retrive_user=False)
    #     async def get(self, request: Request, entity: EntityId | None = None) -> HTTPResponse:
    #         visit_info = await request.app.ctx.service_registry.get(self.target_service).get_info_about_current_visit(
    #             entity)
    #         return json(visit_info)

#
# class VisitSessionController:
#     returned_model = VisitSession
#
#     class Create(BaseServiceController):
#         target_route = "/visitsessions"
#         enabled_scopes = ["root", "Администратор"]
#         target_service = VisitSessionService
#         post_dto = VisitSessionDto.CreationDto
#
#     class Update(BaseServiceController):
#         target_route = "/visitsessions/<entity:int>"
#         enabled_scopes = ["root", "Администратор"]
#         target_service = VisitSessionService
#         put_dto = VisitSessionDto.UpdateDto


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



