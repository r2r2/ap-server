from sanic.exceptions import NotFound
from web_foundation.environment.workers.web.ext.request_handler import InputContext
from web_foundation.environment.workers.web.utils.access import exec_access

from asbp_app.container import AppContainer
from asbp_app.enviroment.infrastructure.database.access_loaders import *


async def access_system_user(context: InputContext, container: AppContainer):
    return await exec_access(context, SystemUser, middleware=SystemUserLoader)


async def access_zone(context: InputContext, container: AppContainer):
    return await exec_access(context, Zone, middleware=BaseAccessLoader)


async def access_claim(context: InputContext, container: AppContainer):
    if context.request.method in ("POST", "PATCH"):
        context.r_kwargs['emmit_func'] = container.auth_service.emmit_event
    return await exec_access(context, Claim, middleware=ClaimLoader, fetch_fields=[
        'claim_way',
        'claim_way_2',
        'pass_id',
        'user_identity',
        'claim_to_zones',
        'transports',
        'visitors',
        'claim_way_approval',
    ])


async def access_claim_way(context: InputContext, container: AppContainer):
    return await exec_access(context, ClaimWay, middleware=ClaimWayLoader)


async def access_claim_to_zone(context: InputContext, container: AppContainer):
    return await exec_access(context, ClaimToZone, middleware=ClaimToZoneLoader)


async def access_parking_place(context: InputContext, container: AppContainer):
    return await exec_access(context, ParkingPlace, middleware=ParkingPlaceLoader)


# async def access_parking_place_bulk(context: InputContext, container):  # TODO need bulk create / delete??
#     return await None


async def access_parking(context: InputContext, container: AppContainer):
    return await exec_access(context, Parking, middleware=ParkingLoader)


async def access_role(context: InputContext, container: AppContainer):
    return await exec_access(context, UserRole, middleware=BaseAccessLoader)


async def access_role_group(context: InputContext, container: AppContainer):
    return await exec_access(context, UserRoleGroup, middleware=RoleGroupLoader)


async def access_building(context: InputContext, container: AppContainer):
    return await exec_access(context, Building, middleware=BaseAccessLoader)


async def access_division(context: InputContext, container: AppContainer):
    return await exec_access(context, Division, middleware=DivisionLoader)


async def access_organization(context: InputContext, container: AppContainer):
    return await exec_access(context, Organisation, middleware=BaseAccessLoader)


async def access_job_title(context: InputContext, container: AppContainer):
    return await exec_access(context, JobTitle, middleware=BaseAccessLoader)


async def access_document(context: InputContext, container: AppContainer):
    if "passport" in context.request.url:
        return await exec_access(context, Passport, middleware=PersonalDocumentLoader)
    elif "international_passport" in context.request.url:
        return await exec_access(context, InternationalPassport, middleware=PersonalDocumentLoader)
    elif "drive_licence" in context.request.url:
        return await exec_access(context, DriveLicense, middleware=PersonalDocumentLoader)
    elif "military_id" in context.request.url:
        return await exec_access(context, MilitaryId, middleware=PersonalDocumentLoader)
    else:
        raise NotFound()


async def access_transport(context: InputContext, container: AppContainer):
    return await exec_access(context, JobTitle, middleware=BaseAccessLoader)


async def access_black_list(context: InputContext, container: AppContainer):
    black_list = await exec_access(context, BlackList, middleware=BlackListLoader, fetch_fields=["visitor"])
    await BlackListLoader.emmit_events(visitor=black_list.visitor,
                                       user=context.identity.user,
                                       emmit_func=container.some_service.emmit_event)  # TODO
    return black_list


async def access_system_settings(context: InputContext, container: AppContainer):
    return await exec_access(context, SystemSettings, middleware=BaseAccessLoader)


async def access_push_subscription(context: InputContext, container: AppContainer):
    return await exec_access(context, PushSubscription, middleware=WebPushLoader)


async def access_stranger_things(context: InputContext, container: AppContainer):
    return await exec_access(context, StrangerThings, middleware=BaseAccessLoader)


async def access_watermark(context: InputContext, container: AppContainer):
    return await exec_access(context, WaterMark, middleware=BaseAccessLoader)


async def access_visitor(context: InputContext, container: AppContainer):
    if context.request.method in ("POST", "PATCH"):
        context.r_kwargs['emmit_func'] = container.auth_service.emmit_event
    return await exec_access(context, Visitor, middleware=None)


async def access_visitor_photo(context: InputContext, container: AppContainer):
    return await exec_access(context, VisitorPhoto, middleware=VisitorPhotoLoader)


async def access_visitor_session(context: InputContext, container: AppContainer):
    return await exec_access(context, VisitSession, middleware=BaseAccessLoader)


async def access_parking_time_slot(context: InputContext, container: AppContainer):
    if context.request.method in ("POST", "PATCH"):
        context.r_kwargs['emmit_func'] = container.auth_service.emmit_event
    return await exec_access(context, ParkingTimeslot, middleware=ParkingTimeslotLoader)


async def access_pass(context: InputContext, container: AppContainer):
    return await exec_access(context, Pass, middleware=PassLoader)


async def access_archive(context: InputContext, container: AppContainer):
    pass
