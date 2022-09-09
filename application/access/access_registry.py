from typing import Dict, Type

from application.access.access import (ClaimToZoneAccess, ClaimWayAccess,
                                       ParkingAccess, ParkingPlaceAccess,
                                       RoleAccess, ScopeConstructorAccess,
                                       SystemUserAccess, ZoneAccess, BuildingAccess, DivisionAccess, OrganisationAccess,
                                       JobTitleAccess)
from application.access.base_access import BaseAccess


class AccessRegistry:
    __slots__ = 'registry'

    def __init__(self):
        self.registry: Dict[Type[BaseAccess], BaseAccess] = {
            SystemUserAccess: SystemUserAccess(),
            ZoneAccess: ZoneAccess(),
            ClaimWayAccess: ClaimWayAccess(),
            ClaimToZoneAccess: ClaimToZoneAccess(),
            ParkingPlaceAccess: ParkingPlaceAccess(),
            ParkingAccess: ParkingAccess(),
            RoleAccess: RoleAccess(),
            ScopeConstructorAccess: ScopeConstructorAccess(),
            BuildingAccess: BuildingAccess(),
            DivisionAccess: DivisionAccess(),
            OrganisationAccess: OrganisationAccess(),
            JobTitleAccess: JobTitleAccess(),
        }

    def get(self, access: Type[BaseAccess]) -> BaseAccess:
        """
        returns a BaseAccess instance to access in model
        :param access type
        :return: BaseAccess instance to access in model.
        :raises AssertionError
        """
        assert access in self.registry
        return self.registry.get(access)
