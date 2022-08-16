import base64
import pandas as pd
from itertools import zip_longest
from io import BytesIO
from datetime import datetime, timedelta

from application.service.web_push import WebPushController
from dateutil.parser import parse
from typing import Union
from tortoise.transactions import atomic
from tortoise.queryset import Q

import settings
from infrastructure.database.models import (SystemUser,
                                            Claim,
                                            ClaimWay,
                                            Pass,
                                            ClaimWayApproval,
                                            Visitor,
                                            BlackList, PushSubscription)
from application.exceptions import InconsistencyError
from application.service.base_service import BaseService
from core.dto.access import EntityId
from core.dto.service import ClaimDto, EmailStruct, VisitorDto
from core.communication.event import NotifyUsersInClaimWayEvent, NotifyUsersInClaimWayBeforeNminutesEvent, Event
from core.plugins.plugins_wrap import AddPlugins


class ClaimService(BaseService):
    target_model = Claim

    class EventName:
        @staticmethod
        async def time_before_for_claim_way_2(claim_way2: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers before N minutes in Claim.claim_way_2"""
            return NotifyUsersInClaimWayBeforeNminutesEvent(
                await ClaimService.build_email_struct(claim_way2, claim=claim, claim_way_2=True, time_before=True))

        @staticmethod
        async def notify_claim_way_2(claim_way: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers in Claim.claim_way_2"""
            return NotifyUsersInClaimWayEvent(
                await ClaimService.build_email_struct(claim_way, claim=claim, claim_way_2=True))

        @staticmethod
        async def status_changed_claim_way_2(claim_way2: ClaimWay, claim: Claim, status: str) -> Event:
            """Notify SystemUsers in Claim.claim_way_2 about changing status in Claim.status"""
            return NotifyUsersInClaimWayEvent(
                await ClaimService.build_email_struct(claim_way2, claim=claim, status=status, claim_way_2=True))

        @staticmethod
        async def claim_approved_claim_way_2(claim_way2: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers in Claim.claim_way_2 when Claim.approved==True"""
            return NotifyUsersInClaimWayEvent(
                await ClaimService.build_email_struct(claim_way2, claim=claim, claim_way_2=True, approved=True))

        @staticmethod
        async def time_before_for_claim_way(claim_way: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers before N minutes in Claim.claim_way"""
            return NotifyUsersInClaimWayBeforeNminutesEvent(
                await ClaimService.build_email_struct(claim_way, claim=claim, time_before=True))

        @staticmethod
        async def notify_claim_way(claim_way: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers in Claim.claim_way"""
            return NotifyUsersInClaimWayEvent(await ClaimService.build_email_struct(claim_way, claim=claim))

        @staticmethod
        async def status_changed_claim_way(claim_way: ClaimWay, claim: Claim, status: str) -> Event:
            """Notify SystemUsers in Claim.claim_way about changing status in Claim.status"""
            return NotifyUsersInClaimWayEvent(
                await ClaimService.build_email_struct(claim_way, claim=claim, status=status))

        @staticmethod
        async def claim_approved_claim_way(claim_way: ClaimWay, claim: Claim) -> Event:
            """Notify SystemUsers in Claim.claim_way when Claim.approved==True"""
            return NotifyUsersInClaimWayEvent(
                await ClaimService.build_email_struct(claim_way, claim=claim, approved=True))

    @staticmethod
    async def build_email_struct(claim_way: ClaimWay,
                                 claim: Claim,
                                 claim_way_2: bool = False,
                                 approved: bool = False,
                                 time_before: bool = False,
                                 status: str = None) -> EmailStruct:
        """Collect system_users from ClaimWay and build EmailStruct"""
        system_users = claim_way.__dict__.get('_system_users')

        url = settings.CLAIMS_URL.format(claim=claim.id)
        text = settings.CLAIMWAY_BODY_TEXT.format(claim=claim.id, url=url)
        subject = settings.CLAIMWAY_SUBJECT_TEXT

        time_to_send = time_to_expire = None
        if time_before:
            # Notify SystemUsers in ClaimWay before N minutes before Visitor come
            if time_to_send_notify := await ClaimService.calculate_time_to_send_notify(claim):
                time_to_send, time_to_expire = time_to_send_notify
                visit_start_date = datetime.strftime(time_to_expire, settings.DATETIME_FORMAT)
                text = settings.CLAIMWAY_BEFORE_N_MINUTES_BODY_TEXT.format(url=url, visit_start_date=visit_start_date)
                subject = settings.CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT.format(claim=claim.id)

        if status:
            # if status in claim was changed
            text = settings.CLAIM_STATUS_BODY_TEXT.format(claim=claim.id, status=status)
            subject = settings.CLAIM_STATUS_SUBJECT_TEXT.format(claim=claim.id)

        if approved:
            # when claim was approved
            text = settings.CLAIM_APPROVED_BODY_TEXT.format(claim=claim.id, url=url)
            subject = settings.CLAIM_APPROVED_SUBJECT_TEXT.format(claim=claim.id)

        emails = [user.email for user in system_users]

        email_struct = EmailStruct(email=emails,
                                   text=text,
                                   subject=subject,
                                   time_to_send=time_to_send,
                                   time_to_expire=time_to_expire,
                                   claim=claim.id,
                                   claim_way_2=claim_way_2)
        # Send web push notifications
        subscriptions = await PushSubscription.filter(system_user__id__in=system_users)
        await WebPushController.trigger_push_notifications_for_subscriptions(subscriptions, subject, text)

        return email_struct

    @staticmethod
    async def calculate_time_to_send_notify(claim: Claim) -> Union[tuple[datetime, datetime], None]:
        """
        Calculating time for sending notification to users, who didn't approve claim.
        Also, calc expire time for Celery task.
        """
        minutes: int = await settings.system_settings("claimway_before_n_minutes")

        if time_to_expire := await Visitor.filter(claim=claim.id, deleted=False).first().values("visit_start_date"):
            if time_to_expire["visit_start_date"]:
                time_to_expire = time_to_expire["visit_start_date"].astimezone()
                time_to_send = time_to_expire - timedelta(minutes=minutes)
                return time_to_send, time_to_expire

    @atomic(settings.CONNECTION_NAME)
    async def create_claimway_approval(self,
                                       claim_way: ClaimWay,
                                       claim: Claim,
                                       claim_way_2: ClaimWay = None) -> None:
        """Creating ClaimWayApproval for SystemUsers in ClaimWay."""
        sys_users = await claim_way.system_users.all()

        sys_users2 = list()
        if claim_way_2:
            sys_users2 = await claim_way_2.system_users.all()

        users: list[SystemUser] = sys_users + sys_users2
        for user in users:
            await ClaimWayApproval.create(system_user=user, claim=claim)

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: ClaimDto.CreationDto) -> Claim:
        pass_id = await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None
        claim_way = await ClaimWay.get_or_none(id=dto.claim_way).prefetch_related(
            "system_users") if dto.claim_way else None
        claim_way2 = await ClaimWay.get_or_none(id=dto.claim_way_2).prefetch_related(
            "system_users") if dto.claim_way_2 else None

        kwrgs = {field: value for field, value in dto.dict().items()
                 if field not in ("pass_id", "claim_way", "claim_way_2", "approved") and value}

        if claim_way:
            if pass_id is not None:
                raise InconsistencyError(message=f"You can't assign Pass to Claim if claim has ClaimWay to approve. "
                                                 f"First claim should be approved.")
            claim = await Claim.create(**kwrgs, claim_way=claim_way, claim_way_2=claim_way2)
            await self.create_claimway_approval(claim_way, claim, claim_way2)

            if claim_way2:
                self.notify(await self.EventName.time_before_for_claim_way_2(claim_way2, claim))

            self.notify(await self.EventName.notify_claim_way(claim_way, claim))
            self.notify(await self.EventName.time_before_for_claim_way(claim_way, claim))
        else:
            claim = await Claim.create(**kwrgs, pass_id=pass_id)
        return claim

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: ClaimDto.UpdateDto) -> Claim:
        notification_counter = 0
        claim: Claim = await self.read(entity_id)  # type: ignore
        if claim is None:
            raise InconsistencyError(message=f"Claim with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if field in ("claim_way", "claim_way_2") and value:
                claim_way = await ClaimWay.get_or_none(id=value).prefetch_related(
                    "system_users")
                if claim_way is None:
                    raise InconsistencyError(message=f"ClaimWay with id={value} doesn't exist.")
                setattr(claim, field, claim_way)

                if field == "claim_way":
                    self.notify(await self.EventName.notify_claim_way(claim_way, claim))
                    self.notify(await self.EventName.time_before_for_claim_way(claim_way, claim))
                    notification_counter += 1

                elif field == "claim_way_2":
                    if claim.claim_way_approved:
                        self.notify(await self.EventName.notify_claim_way_2(claim_way, claim))
                    self.notify(await self.EventName.time_before_for_claim_way_2(claim_way, claim))

                await self.create_claimway_approval(claim_way, claim)

        pass_id = await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None
        if pass_id is None and dto.pass_id:
            raise InconsistencyError(message=f"Pass with id={dto.pass_id} doesn't exist.")

        if claim.claim_way:
            # Trying to assign Pass to Claim.
            # If claim_way was assigned - check for Claim.approved==True
            if pass_id is not None and claim.approved:
                setattr(claim, "pass_id", pass_id)
            elif pass_id is not None and not claim.approved:
                raise InconsistencyError(message=f"Claim id={entity_id} should be approved before assign Pass to it.")
        else:
            # If no claim_way - just set Pass to this Claim
            if pass_id is not None:
                setattr(claim, "pass_id", pass_id)

        if dto.is_in_blacklist is not None:
            setattr(claim, "is_in_blacklist", False if dto.is_in_blacklist is False else True)
            if dto.is_in_blacklist:
                visitor = await Visitor.get_or_none(claim=claim.id)
                await BlackList.create(visitor=visitor)

        if dto.pnd_agreement is not None:
            setattr(claim, "pnd_agreement", False if dto.pnd_agreement is False else True)

        setattr(claim, "pass_type", getattr(dto, "pass_type", claim.pass_type))
        setattr(claim, "information", getattr(dto, "information", claim.information))

        if dto.status:
            setattr(claim, "status", dto.status)
            # If changing sensitive fields notify related users in ClaimWay
            if claim.claim_way is not None:
                claim_way = await ClaimWay.get_or_none(id=claim.claim_way.id).prefetch_related("system_users")

                if notification_counter == 0:
                    self.notify(await self.EventName.status_changed_claim_way(claim_way, claim, dto.status))

                if claim.claim_way_2:
                    claim_way2 = await ClaimWay.get_or_none(id=claim.claim_way_2.id).prefetch_related("system_users")
                    if claim.claim_way_approved:
                        self.notify(await self.EventName.status_changed_claim_way_2(claim_way2, claim, dto.status))
        await claim.save()
        return claim

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)

    @atomic(settings.CONNECTION_NAME)
    async def system_user_approve_claim(self, system_user: SystemUser, entity: EntityId,
                                        dto: ClaimDto.ApproveDto) -> ClaimWayApproval:
        """Current user approve claim."""
        claim_approve = await ClaimWayApproval.filter(system_user=system_user.id, claim=entity).first()
        if claim_approve is None:
            raise InconsistencyError(message=f"No claimway to approve for this user: {system_user}.")

        claim_way1 = await ClaimWay.filter(claims=entity).prefetch_related("system_users")
        claim_way2 = await ClaimWay.filter(claims2=entity).prefetch_related("system_users")

        if not (claim_ways := claim_way1 + claim_way2):
            raise InconsistencyError(message=f"There is no claimways for claim with id={entity}")

        for claim_way in claim_ways:
            users_in_claimway = await claim_way.system_users.all()

            if system_user in users_in_claimway:
                setattr(claim_approve, "approved", dto.approved)
                setattr(claim_approve, "comment", dto.comment)
                await claim_approve.save()
                await self._check_if_claim_approved_by_all_users(claim_way, entity)

        return claim_approve

    @atomic(settings.CONNECTION_NAME)
    async def _check_if_claim_approved_by_all_users(self, claim_way: ClaimWay, entity: EntityId) -> None:
        """
        Check how many users not approved claim.
        If all approved - set Claim.approved to True
        and send notification to users.
        """
        claim = await Claim.get_or_none(id=entity)
        if claim is None:
            raise InconsistencyError(message=f"Claim with id={entity} doesn't exist.")

        users_in_claim_way_not_approve = await SystemUser.filter(
            Q(claim_ways=claim_way.id) &
            Q(claim_way_approval__claim=entity) &
            (Q(claim_way_approval__approved=False) | Q(claim_way_approval__approved=None))
        )

        if len(users_in_claim_way_not_approve) == 0:
            setattr(claim, "claim_way_approved", True)

            if claim.claim_way_2:
                claim_way2 = await ClaimWay.get_or_none(id=claim.claim_way_2_id).prefetch_related("system_users")

                users_in_claim_way_2_not_approve = await claim_way2.filter(
                    Q(claims2__claim_way_approval__claim=entity) & (
                            Q(claims2__claim_way_approval__approved=False) |
                            Q(claims2__claim_way_approval__approved=None)
                    )
                )
                if not claim.claim_way_2_notified and users_in_claim_way_2_not_approve:
                    # Notifying users in claim_way_2 only once
                    self.notify(await self.EventName.notify_claim_way_2(claim_way2, claim))
                    setattr(claim, "claim_way_2_notified", True)

                if len(users_in_claim_way_2_not_approve) == 0:
                    setattr(claim, "approved", True)
                    setattr(claim, "status", "Отработана")
                    self.notify(await self.EventName.claim_approved_claim_way_2(claim_way2, claim))
                    self.notify(await self.EventName.claim_approved_claim_way(claim_way, claim))
                else:
                    setattr(claim, "approved", False)
            else:
                setattr(claim, "approved", True)
                setattr(claim, "status", "Отработана")
                self.notify(await self.EventName.claim_approved_claim_way(claim_way, claim))
        else:
            setattr(claim, "claim_way_approved", False)
            setattr(claim, "approved", False)
        await claim.save()

    @atomic(settings.CONNECTION_NAME)
    async def upload_excel(self, system_user: SystemUser, dto: ClaimDto.GroupVisitDto) -> dict[str, str]:
        """Uploading excel file in xls/xlsx/xlsm/xltx/xltm formats."""
        file_contents = base64.b64decode(dto.excel_file)
        file_io = BytesIO(file_contents)
        visitors = list()
        with pd.ExcelFile(file_io) as xls:
            for sheet in xls.sheet_names:
                to_dto = await self.work_with_sheet(xls, sheet)
                for visitor in to_dto:
                    if visitor_dto := await self.check_visitor_dto(visitor):
                        visitor_to_model = await self.create_visitor(visitor_dto)
                        visitors.append(visitor_to_model)
        return {"message": f"Visitors with id={[visitor.id for visitor in visitors]} were successfully created."}

    async def work_with_sheet(self, xls: pd.ExcelFile, sheet: str) -> tuple[tuple, ...]:
        """Collecting values from each column and save it to tuples."""
        data_frame = pd.read_excel(xls, sheet, dtype={"ФИО": str,
                                                      "Телефон": str,
                                                      "Почта": str,
                                                      "Название компании": str,
                                                      "Время визита": str})
        fio = phone = email = company_name = visit_start_date = tuple()
        for column, values in data_frame.items():
            match column:
                case str(x) if x.lower() == "фио":
                    fio = tuple(values)
                case "Телефон":
                    phone = tuple(values)
                case "Почта":
                    email = tuple(values)
                case "Название компании":
                    company_name = tuple(values)
                case "Время визита":
                    visit_start_date = tuple(values)
        if not fio:
            raise InconsistencyError(message=f"Excel file must have column name 'ФИО'."
                                             f"And you should provide visitors with First, Last, Middle names.")
        to_dto = tuple(
            zip_longest(fio, phone, email, company_name, visit_start_date)
        )
        return to_dto

    async def check_visitor_dto(self, visitor: tuple[str | float]) -> VisitorDto.CreationDto | None:
        """
        Preparing data for DTO validation.
        For creating Visitor user must provide visitors with at least first_name and last_name.
        If visitor has only first_name or it's empty value, so we just skipping this row.
        """
        to_model = dict()
        match visitor[0]:  # ФИО
            case str(value) if len(value.split()) == 3:
                first_name, last_name, middle_name = value.split()
                to_model.update(
                    {"first_name": first_name, "last_name": last_name, "middle_name": middle_name})
            case str(value) if len(value.split()) == 2:
                first_name, last_name = value.split()
                to_model.update({"first_name": first_name, "last_name": last_name})
            case _:
                # if None or only first_name -> ignore this row
                return

        match visitor[1]:  # Телефон
            case str(value):
                to_model.update({"phone": value})

        match visitor[2]:  # Почта
            case str(value):
                to_model.update({"email": value})

        match visitor[3]:  # Название компании
            case str(value):
                to_model.update({"company_name": value})

        match visitor[4]:  # Время визита
            case str(value):
                to_model.update({"visit_start_date": value})

        return VisitorDto.CreationDto(**to_model)

    async def create_visitor(self, visitor_dto: VisitorDto.CreationDto) -> Visitor:
        """If provided, convert str value of visit_start_date to datetime object."""
        match visitor_dto.dict():
            case {"visit_start_date": value} if value:
                setattr(visitor_dto, "visit_start_date", parse(value))
        visitor = await Visitor.create(**visitor_dto.dict())
        return visitor
