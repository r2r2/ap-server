from typing import Union, Optional
from itertools import zip_longest
from sanic import Sanic, Request, HTTPResponse, json
from sanic.views import HTTPMethodView
from sanic.exceptions import NotFound
from datetime import datetime, timedelta
from tortoise.transactions import atomic

import settings
from core.utils.loggining import logger
from infrastructure.database.models import SystemUser, Visitor, Pass
from infrastructure.asbp_archive.models import Archive
from core.server.auth import protect
from core.dto.access import EntityId


class ArchiveController(HTTPMethodView):
    enabled_scopes = ["root", "Администратор"]

    @protect(retrive_user=False)
    async def get(self, request: Request, entity: Optional[EntityId] = None) -> HTTPResponse:
        if entity is None:
            limit = request.args.get("limit")
            offset = request.args.get("offset")
            limit = int(limit) if limit and limit.isdigit() else None
            offset = int(offset) if offset and offset.isdigit() else None

            query = Archive.all()
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

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
    async def collect_visitors(time_delta: datetime) -> Union[list[Visitor], None]:
        visitors = await Visitor.filter(modified_at__lte=time_delta, deleted=True)
        return visitors

    @staticmethod
    async def collect_passes(time_delta: datetime) -> Union[list[Pass], None]:
        passes = await Pass.filter(modified_at__lte=time_delta, valid_till_date__lte=time_delta)
        return passes

    @staticmethod
    @atomic(settings.CONNECTION_NAME_ARCHIVE)
    async def archive_data(visitors: Union[list[Visitor], None],
                           passes: Union[list[Pass], None]) -> None:
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
    async def delete_old(visitors: Union[list[Visitor], None],
                         passes: Union[list[Pass], None]) -> None:
        """Deleting data, which was archived, from main DB."""
        [await visitor.delete() for visitor in visitors]
        [await pass_id.delete() for pass_id in passes]


def init_archive_routes(app: Sanic):
    app.add_route(ArchiveController.as_view(), "/archive")
    app.add_route(ArchiveController.as_view(), "/archive/<entity:int>")
