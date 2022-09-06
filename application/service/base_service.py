from typing import Type

from pydantic import BaseModel
from pyee.asyncio import AsyncIOEventEmitter
from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic

import settings
from core.communication.publisher import Publisher
from core.dto.access import EntityId
from core.utils.error_format import integrity_error_format
from infrastructure.database.layer import DbLayer
from infrastructure.database.models import MODEL, SystemUser
from infrastructure.database.repository import EntityRepository


class BaseService(Publisher):
    persistence: DbLayer
    target_model: Type[MODEL]

    def __init__(self, persistence: DbLayer, emitter: AsyncIOEventEmitter):
        super().__init__(emitter)
        self.persistence = persistence

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, _dto: Type[BaseModel], **kwargs) -> MODEL:
        if hasattr(_dto, "name"):
            await EntityRepository.check_exist(self.target_model, name=_dto.name)
        entity_kwargs = {field: value for field, value in _dto.dict().items() if value}
        try:
            entity = await self.target_model.create(**entity_kwargs)
        except IntegrityError as exception:
            integrity_error_format(exception)
        return entity  # noqa

    async def read(self, _id: EntityId) -> Type[MODEL] | None:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)
        return await self.target_model.get_or_none(id=_id).prefetch_related(*related_fields)

    async def read_all(self,
                       limit: int = 0,
                       offset: int = 0) -> list[MODEL]:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)
        query = self.target_model.all().prefetch_related(*related_fields)
        return await query.limit(limit).offset(offset)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(self.target_model, entity_id)
        entity = await DbLayer.get_optional_view(self.target_model, entity_id)
        await entity.delete()
        return entity_id
