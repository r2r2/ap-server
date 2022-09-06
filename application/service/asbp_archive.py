from datetime import datetime, timedelta
from itertools import zip_longest

from sanic import HTTPResponse, Request, Sanic, json
from sanic.exceptions import NotFound
from sanic.views import HTTPMethodView
from tortoise.transactions import atomic

import settings
from core.dto.access import EntityId
from core.server.auth import protect
from core.utils.limit_offset import get_limit_offset
from core.utils.loggining import logger
from infrastructure.asbp_archive.models import Archive
from infrastructure.database.models import Pass, SystemUser, Visitor


class ArchiveController(HTTPMethodView):
    enabled_scopes = ["root", "Администратор"]

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: EntityId = None) -> HTTPResponse:
        if entity is None:
            limit, offset = await get_limit_offset(request)
            query = Archive.all().limit(limit).offset(offset)
            return json([await model.values_dict() for model in await query])

        if model := await Archive.get_or_none(id=entity):
            return json(await model.values_dict())
        else:
            raise NotFound()

    @protect()
    async def post(self, request: Request, system_user: SystemUser) -> HTTPResponse:
        """Calling ArchiveController.do_archive() for archiving old data from main DB"""
        if await self.do_archive():
            return json({"message": "Data was successfully archived."})

        return json({"message": "No data to archive."})

    @staticmethod
    async def do_archive() -> bool:
        """
        Collect appropriate data from main DB and transfer it to Archive DB, if needed.
        Put data, which "older" than time_delta days, to Archive DB.
        Returning bool for post() method.
        """
        days: int = await settings.system_settings("days_before_archive")
        time_delta = datetime.now().astimezone() - timedelta(days=days)
        visitors = await ArchiveController.collect_visitors(time_delta)
        passes = await ArchiveController.collect_passes(time_delta)
        if visitors or passes:
            await ArchiveController.archive_data(visitors, passes)
            await ArchiveController.delete_old(visitors, passes)
            return True
        return False

    @staticmethod
    async def collect_visitors(time_delta: datetime) -> list[Visitor] | None:
        visitors = await Visitor.filter(modified_at__lte=time_delta, deleted=True)
        return visitors

    @staticmethod
    async def collect_passes(time_delta: datetime) -> list[Pass] | None:
        passes = await Pass.filter(modified_at__lte=time_delta, valid_till_date__lte=time_delta)
        return passes

    @staticmethod
    @atomic(settings.CONNECTION_NAME_ARCHIVE)
    async def archive_data(visitors: list[Visitor] | None,
                           passes: list[Pass] | None) -> None:
        """Creating a new entry in Archive DB."""
        for visitor, pass_id in list(zip_longest(visitors, passes)):
            await Archive.create(
                visitor=await visitor.values_dict(m2m_fields=True, fk_fields=True, backward_fk_fields=True,
                                                  o2o_fields=True) if visitor else None,
                pass_id=await pass_id.values_dict(m2m_fields=True, fk_fields=True, backward_fk_fields=True,
                                                  o2o_fields=True) if pass_id else None
            )
        logger.info("Data was successfully archived.")

    @staticmethod
    @atomic(settings.CONNECTION_NAME)
    async def delete_old(visitors: list[Visitor] | None,
                         passes: list[Pass] | None) -> None:
        """Deleting data, which was archived, from main DB."""
        [await visitor.delete() for visitor in visitors]
        [await pass_id.delete() for pass_id in passes]


def init_archive_routes(app: Sanic) -> None:
    app.add_route(ArchiveController.as_view(), "/archive", methods=["GET", "POST"])
    app.add_route(ArchiveController.as_view(), "/archive/<entity:int>", methods=["GET"])
