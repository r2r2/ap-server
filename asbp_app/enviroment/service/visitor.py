from datetime import datetime
from typing import Type

from web_foundation.environment.resources.database.models import AbstractDbModel
from web_foundation.environment.services.service import Service

from tortoise import exceptions
from tortoise.transactions import atomic
from web_foundation.errors.app.application import InconsistencyError
from web_foundation.utils.helpers import validate_date, validate_datetime

from asbp_app import settings
from asbp_app.api.dto.access import EntityId
from asbp_app.api.dto.service import EmailStruct, WebPush
from asbp_app.enviroment.celery.sending_emails import create_email_struct_for_sec_officers
from asbp_app.enviroment.event.event import SendWebPushEvent, NotifyVisitorInBlackListEvent, \
    NotifyUsersInClaimWayBeforeNminutesEvent
from asbp_app.enviroment.infrastructure.database.access_loaders import BaseAccessLoader
from asbp_app.utils.mailing import create_email_struct
from asbp_app.enviroment.infrastructure.database.models import VisitSession, Visitor, PushSubscription, Claim, Passport, \
    InternationalPassport, Pass, DriveLicense, MilitaryId, Transport, VisitorPhoto, BlackList, StrangerThings, \
    SystemUser, ClaimWay


class VisitorService(Service):

    @staticmethod
    async def get_info_about_current_visit(entity_id: EntityId) -> dict[str, dict | list[dict] | str | None]:
        """Return info about visitor's visit"""
        visitor: Visitor = await Visitor.get_or_none(id=entity_id).prefetch_related("visit_session")
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={entity_id} doesn't exist.")

        visit_info = {
            "pass": await Pass.filter(visitor=entity_id).values() if visitor.pass_id else None,
            "visit_info": await VisitSession.filter(visitor=visitor.id).values("enter", "exit") if visitor.visit_session else None,
            "who_invited": visitor.who_invited,
            "destination": visitor.destination,
            "documents": {
                "passport": await Passport.filter(visitor=entity_id).values() if visitor.passport else None,
                "international_passport": await InternationalPassport.filter(visitor=entity_id).values() if visitor.international_passport else None,
                "drive_license": await DriveLicense.filter(visitor=entity_id).values() if visitor.drive_license else None,
                "military_id": await MilitaryId.filter(visitor=entity_id).values() if visitor.military_id else None,
            }
        }
        # visit_info = await visitor.values_dict(m2m_fields=True, fk_fields=True, backward_fk_fields=True,
        #                                        o2o_fields=True)

        return visit_info

