from typing import List, Type, Union

from pydantic import BaseModel
from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic

import settings
from core.dto.access import EntityId
from core.utils.error_format import integrity_error_format
from infrastructure.database.layer import DbLayer
from infrastructure.database.models import MODEL, AbstractBaseModel, SystemUser
from infrastructure.database.repository import EntityRepository


class BaseAccess:
    __slots__ = 'target_model'
    target_model: Type[MODEL]

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, _dto: BaseModel, **kwargs) -> MODEL:
        if hasattr(_dto, "name"):
            await EntityRepository.check_exist(self.target_model, name=_dto.name)
        entity_kwargs = {field: value for field, value in _dto.dict().items() if value}
        try:
            entity = await self.target_model.create(**entity_kwargs)
        except IntegrityError as exception:
            integrity_error_format(exception)
        return entity

    async def read(self, _id: EntityId) -> MODEL:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)
        return await self.target_model.get_or_none(id=_id).prefetch_related(*related_fields)

    async def read_all(self,
                       limit: int = 0,
                       offset: int = 0) -> list[MODEL] | MODEL:
        related_fields = await DbLayer.extract_relatable_fields(self.target_model)
        query = self.target_model.all().prefetch_related(*related_fields)
        return await query.limit(limit).offset(offset)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: BaseModel) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(self.target_model, entity_id)
        entity = await DbLayer.get_optional_view(self.target_model, entity_id)
        for field, value in dto.dict().items():
            if value:
                setattr(entity, field, value)
        await entity.save()
        return entity_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(self.target_model, entity_id)
        entity = await DbLayer.get_optional_view(self.target_model, entity_id)
        await entity.delete()
        return entity_id
