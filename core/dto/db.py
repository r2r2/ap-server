from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from core.dto.access import EntityId, EntityName
from infrastructure.database import models


@dataclass()
class DefaultModificationInfo:
    __slots__ = ('created_by_entity',
                 'modified_by_entity',
                 'created_by_id',
                 'modified_by_id',
                 'modified_on',
                 'created_on'
                 )

    created_by_entity: Optional[EntityName]
    created_by_id: Optional[EntityId]
    created_on: Optional[datetime]

    modified_by_entity: EntityName
    modified_by_id: EntityId
    modified_on: datetime

    @staticmethod
    def on_system_user_creation(system_user: models.SystemUser):
        return DefaultModificationInfo(models.SystemUser.__name__,
                                       system_user.id,
                                       datetime.now(),
                                       models.SystemUser.__name__,
                                       system_user.id,
                                       datetime.now())

    @staticmethod
    def on_system_user_update(system_user: models.SystemUser):
        return DefaultModificationInfo(modified_by_entity=models.SystemUser.__name__,
                                       modified_by_id=system_user.id,
                                       modified_on=datetime.now())

    def asdict(self):
        return asdict(self)
