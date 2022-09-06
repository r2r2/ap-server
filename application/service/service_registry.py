from typing import Dict, Type

from pyee.asyncio import AsyncIOEventEmitter

from application.service.base_service import BaseService
from application.service.black_list import BlackListService
from application.service.claim import ClaimService
from application.service.parking import ParkingTimeslotService
from application.service.system_settings import SystemSettingsService
from application.service.visitor import (DriveLicenseService,
                                         InternationalPassportService,
                                         MilitaryIdService, PassportService,
                                         PassService, TransportService,
                                         VisitorPhotoService, VisitorService,
                                         VisitSessionService, WaterMarkService)
from infrastructure.database.layer import DbLayer


class ServiceRegistry:
    __slots__ = "registry"
    db_manager = DbLayer()

    def __init__(self, emitter: AsyncIOEventEmitter):

        self.registry: Dict[Type[BaseService], BaseService] = {
            VisitorService: VisitorService(self.db_manager, emitter),
            ClaimService: ClaimService(self.db_manager, emitter),
            PassportService: PassportService(self.db_manager, emitter),
            MilitaryIdService: MilitaryIdService(self.db_manager, emitter),
            VisitSessionService: VisitSessionService(self.db_manager, emitter),
            DriveLicenseService: DriveLicenseService(self.db_manager, emitter),
            PassService: PassService(self.db_manager, emitter),
            TransportService: TransportService(self.db_manager, emitter),
            BlackListService: BlackListService(self.db_manager, emitter),
            VisitorPhotoService: VisitorPhotoService(self.db_manager, emitter),
            WaterMarkService: WaterMarkService(self.db_manager, emitter),
            ParkingTimeslotService: ParkingTimeslotService(self.db_manager, emitter),
            InternationalPassportService: InternationalPassportService(self.db_manager, emitter),
            SystemSettingsService: SystemSettingsService(self.db_manager, emitter),
        }

    def get(self, service: Type[BaseService]) -> BaseService:
        assert service in self.registry
        return self.registry.get(service)
