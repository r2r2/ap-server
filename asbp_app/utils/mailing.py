from datetime import timedelta, datetime

from web_foundation.utils.helpers import validate_datetime

from asbp_app.api.dto.service import EmailStruct
from asbp_app.enviroment.infrastructure.database.models import ClaimWay, Claim, Visitor, SystemSettingsTypes
from asbp_app.utils.system import get_system_settings


async def calculate_time_to_send_notify(claim: Claim) -> tuple[datetime, datetime] | None:
    """
    Calculating time for sending notification to users, who didn't approve claim.
    Also, calc expire time for Celery task.
    """
    minutes: int = await get_system_settings(SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT)

    if time_to_expire := await Visitor.filter(claim=claim.id, deleted=False).first().values("visit_start_date"):
        if time_to_expire["visit_start_date"]:
            time_to_expire = time_to_expire["visit_start_date"].astimezone()
            time_to_send = time_to_expire - timedelta(minutes=minutes)
            return time_to_send, time_to_expire


async def create_email_struct(claim_way: ClaimWay,
                              claim: Claim,
                              claim_way_2: bool = False,
                              approved: bool = False,
                              time_before: bool = False,
                              status: str = None) -> EmailStruct:
    """Build EmailStruct"""
    system_users = claim_way.__dict__.get('_system_users')

    url = (await get_system_settings(SystemSettingsTypes.CLAIM_URL)).format(claim=claim.id)
    text = (await get_system_settings(SystemSettingsTypes.CLAIMWAY_BODY_TEXT)).format(claim=claim.id, url=url)
    subject = await get_system_settings(SystemSettingsTypes.CLAIMWAY_SUBJECT_TEXT)

    time_to_send = time_to_expire = None
    if time_before:
        # Notify SystemUsers in ClaimWay before N minutes before Visitor come
        if time_to_send_notify := await calculate_time_to_send_notify(claim):
            time_to_send, time_to_expire = time_to_send_notify
            visit_start_date = validate_datetime(time_to_expire)
            text = (await get_system_settings(SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES_BODY_TEXT)).format(url=url, visit_start_date=visit_start_date)
            subject = (await get_system_settings(SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT)).format(claim=claim.id)

    if status:
        # if status in claim was changed
        text = (await get_system_settings(SystemSettingsTypes.CLAIM_STATUS_BODY_TEXT)).format(claim=claim.id, status=status)
        subject = (await get_system_settings(SystemSettingsTypes.CLAIM_STATUS_SUBJECT_TEXT)).format(claim=claim.id)

    if approved:
        # when claim was approved
        text = (await get_system_settings(SystemSettingsTypes.CLAIM_APPROVED_BODY_TEXT)).format(claim=claim.id, url=url)
        subject = (await get_system_settings(SystemSettingsTypes.CLAIM_APPROVED_SUBJECT_TEXT)).format(claim=claim.id)

    emails = [user.email for user in system_users]

    email_struct = EmailStruct(email=emails,
                               text=text,
                               subject=subject,
                               time_to_send=time_to_send,
                               time_to_expire=time_to_expire,
                               claim=claim.id,
                               claim_way_2=claim_way_2)
    return email_struct
