from typing import Type, List, Union, overload

from application.exceptions import InconsistencyError
from core.dto.access import EntityId
from core.errors import DomainError
from infrastructure.database.layer import DbLayer
from infrastructure.database.models import AbstractBaseModel


class EntityRepository:
    @staticmethod
    @overload
    async def get(target_model: Type[AbstractBaseModel], entity_id: EntityId) -> AbstractBaseModel:
        ...

    @staticmethod
    @overload
    async def get(target_model: Type[AbstractBaseModel], entity_id: List[EntityId]) -> List[AbstractBaseModel]:
        ...

    @staticmethod
    async def get(target_model: Type[AbstractBaseModel],
                  entity_id: Union[EntityId, List[EntityId]]) -> Union[AbstractBaseModel, List[AbstractBaseModel]]:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        if isinstance(entity_id, list):
            assert len(entity_id) > 0
            objects = await DbLayer.get_optional_view(target_model, entity_id)
            if len(objects) < len(entity_id):
                raise DomainError(message=f"Some of requested {target_model.__name__} were not found")
            return objects
        else:
            entity = await DbLayer.get_optional_view(target_model, _id=entity_id)
            if not entity:
                raise DomainError(message=f"{target_model.__name__} does not exist")
            return entity

    @staticmethod
    async def check_exist(target_model: Type[AbstractBaseModel] = None, **kwargs):
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        if await DbLayer.contains_by_kwargs(target_model, **kwargs):
            raise InconsistencyError(message=f"{target_model.__name__} already exists")

    @staticmethod
    async def check_not_exist_or_delete(target_model: Type[AbstractBaseModel], entity_id: EntityId):
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        entity = await target_model.get_or_none(id=entity_id)
        if entity is None:
            raise InconsistencyError(message=f"Such {target_model.__name__} does not exist")
        if hasattr(entity, "deleted") and entity.deleted:
            raise InconsistencyError(message=f"This {target_model.__name__} is already marked as deleted")
