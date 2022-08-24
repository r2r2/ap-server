from datetime import datetime
from typing import Type
from tortoise.expressions import Q
from tortoise.fields import Field
from tortoise.fields.relational import RelationalField
from tortoise.queryset import QuerySetSingle, QuerySet

from core.dto.access import EntityId
from infrastructure.database.models import SystemUserSession, SystemUser, MODEL


class SystemUserDbLayer:

    @staticmethod
    async def get_user_scopes(user_id: EntityId) -> list[str] | None:
        """
        :param
        :param

        :return: None.
        :raises
        """
        user: SystemUser = await SystemUser.get_or_none(id=user_id, ).select_related()
        scopes = await user.scopes.all()
        if not user or not scopes:
            return []
        return [scope.name for scope in scopes]

    @staticmethod
    async def create_session(user: SystemUser, user_agent: str) -> SystemUserSession:
        """
        :param
        :param

        :return: None.
        :raises
        """
        return await SystemUserSession.create(user=user, user_agent=user_agent)

    @staticmethod
    async def get_session_id(user_id: int, agent: str):
        sessions = await SystemUserSession.filter(user_id=user_id, user_agent=agent)
        need_id = sessions[-1].id
        for ses in sessions:
            if ses.id != need_id:
                await ses.delete()
        return need_id

    @staticmethod
    async def get_system_user(username: str) -> SystemUser:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        return await SystemUser.get_or_none(username=username)

    @staticmethod
    async def update_last_login(user_id: int, time: datetime) -> None:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        await SystemUser.filter(id=user_id).update(last_login=time)

    @staticmethod
    async def update_last_logout(user_id: int, time: datetime) -> None:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        await SystemUser.filter(id=user_id).update(last_logout=time)


class DbLayer(SystemUserDbLayer):
    def __init__(self):
        pass

    @staticmethod
    async def extract_relatable_fields(model: Type[MODEL]) -> list[str]:
        return [field for field, sheme in model._meta.fields_map.items() if
                sheme.__class__.__base__ == RelationalField]

    @staticmethod
    async def contains_by_id(model: Type[MODEL], _id: int) -> bool:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        return await model.exists(id=_id)

    @staticmethod
    async def contains_by_kwargs(model: Type[MODEL], **kwargs) -> bool:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        return await model.exists(**kwargs)

    @staticmethod
    async def get_optional_view(model: Type[MODEL], _id: int | list[int],
                                columns: list[Field] = None) -> MODEL | list[MODEL] | None:
        # TODO: Add docks
        """
        :param
        :param

        :return: None.
        :raises
        """
        if isinstance(_id, list):
            query: QuerySet = model.filter(Q(id__in=_id))
        else:
            query: QuerySetSingle = model.get_or_none(id=_id)
        if columns is None:
            related = await DbLayer.extract_relatable_fields(model)
            return await query.prefetch_related(*related)
        else:
            cols: list[str] = [col.model_field_name for col in columns]
            rows = await query.values(*cols)
            if isinstance(rows, list):
                return [model(**row) for row in rows]
            return model(**rows)
