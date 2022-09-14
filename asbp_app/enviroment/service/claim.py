import base64
import datetime
from io import BytesIO
from itertools import zip_longest

import pandas as pd
from dateutil.parser import parse
from tortoise.queryset import Q
from tortoise.transactions import atomic
from web_foundation.environment.services.service import Service
from web_foundation.errors.app.application import InconsistencyError

from asbp_app.api.dto.access import EntityId, VisitorDto
from asbp_app.api.dto.service import ClaimStatus, ClaimDto
from asbp_app.enviroment.event.event import NotifyUsersInClaimWayEvent
from asbp_app.enviroment.infrastructure.database.models import Claim, ClaimWay, SystemUser, \
    ClaimWayApproval, Visitor
from asbp_app.utils.mailing import create_email_struct


class ClaimService(Service):
    target_model = Claim

    @staticmethod
    async def check_if_claim_expired(data: ClaimStatus) -> None:
        """Set status Просрочена, if calim wasn't approve until Visitor.visit_start_date."""
        if (claim := await Claim.get_or_none(id=data.claim)) and (datetime.datetime.now() > data.time_to_expire):
            setattr(claim, "status", "Просрочена")

    @atomic()
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
                    await self.emmit_event(
                        NotifyUsersInClaimWayEvent(await create_email_struct(claim_way2, claim=claim)))
                    setattr(claim, "claim_way_2_notified", True)

                if len(users_in_claim_way_2_not_approve) == 0:
                    setattr(claim, "approved", True)
                    setattr(claim, "status", "Отработана")
                    await self.emmit_event(
                        NotifyUsersInClaimWayEvent(
                                    await create_email_struct(claim_way2, claim=claim, approved=True)))
                    await self.emmit_event(
                        NotifyUsersInClaimWayEvent(
                                    await create_email_struct(claim_way, claim=claim, approved=True)))
                else:
                    setattr(claim, "approved", False)
            else:
                setattr(claim, "approved", True)
                setattr(claim, "status", "Отработана")
                await self.emmit_event(NotifyUsersInClaimWayEvent(
                    await create_email_struct(claim_way, claim=claim, claim_way_2=True, approved=True)))
        else:
            setattr(claim, "claim_way_approved", False)
            setattr(claim, "approved", False)
        await claim.save()

    @atomic()
    async def upload_excel(self, dto: ClaimDto.GroupVisitDto) -> dict[str, str]:
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
