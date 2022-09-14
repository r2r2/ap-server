# from datetime import datetime, timedelta
# from typing import Optional, Union
#
# from tortoise.queryset import Q
# from tortoise.transactions import atomic
# from web_foundation.utils.helpers import validate_datetime
#
# from asbp_app import settings
#
#
# from web_foundation.environment.resources.database.model_loader import EntityId
# from web_foundation.environment.services.service import Service
#
# from application.exceptions import InconsistencyError
# from application.service.base_service import BaseService
# from asbp_app.api.dto.service import ParkingTimeslotDto
# from asbp_app.enviroment.event.event import MaxParkingTimeHoursExceededEvent
# from asbp_app.utils.system import get_system_settings
#
# # from core.dto.service import ParkingTimeslotDto
# # from infrastructure.database.models import (ParkingPlace, ParkingTimeslot,
# #                                             StrangerThings, SystemUser,
# #                                             Transport)
# from asbp_app.enviroment.infrastructure.database.models import ParkingTimeslot, SystemUser, Transport, \
#     SystemSettingsTypes, ParkingPlace
#
#
# class ParkingTimeslotService(Service):
#     target_model = ParkingTimeslot
#
#     @atomic()
#     async def create(self, system_user: SystemUser, dto: ParkingTimeslotDto.CreationDto) -> ParkingTimeslot:
#         transport = await Transport.get_or_none(id=dto.transport)
#         if transport is None:
#             raise InconsistencyError(message=f"Transport with id={dto.transport} does not exist.")
#
#         minutes: int = await get_system_settings(SystemSettingsTypes.PARKING_TIMESLOT_INTERVAL)
#         start = datetime.fromisoformat(validate_datetime(dto.start))
#         end = datetime.fromisoformat(validate_datetime(dto.end)) + timedelta(minutes=minutes)
#         timeslot = end - start
#         await self.check_time_interval(timeslot)
#
#         if dto.parking_place:
#             parking_place = await self.get_parking_place(dto.parking_place)
#             await self.get_timeslots(start, end, parking_place)
#         else:
#             timeslots = await self.get_timeslots(start, end)
#             parking_place = await self.get_available_parking_place(timeslots, start, end)
#
#         parking_timeslot = await ParkingTimeslot.create(start=start,
#                                                         end=end,
#                                                         timeslot=str(timeslot),
#                                                         parking_place=parking_place,
#                                                         transport=transport)
#         await self.emmit_event(
#             MaxParkingTimeHoursExceededEvent(await self.data_to_event(system_user.id, parking_timeslot.id)))
#
#         return parking_timeslot
#
#     @atomic()
#     async def update(self, system_user: SystemUser, entity_id: EntityId,
#                      dto: ParkingTimeslotDto.UpdateDto) -> ParkingTimeslot:
#         parking_timeslot = await ParkingTimeslot.get_or_none(id=entity_id)
#         if parking_timeslot is None:
#             raise InconsistencyError(message=f"Parking timeslot with id={entity_id} does not exist.")
#
#         transport = await Transport.get_or_none(id=dto.transport)
#         if transport is None:
#             raise InconsistencyError(message=f"Transport with id={dto.transport} does not exist.")
#
#         minutes: int = await get_system_settings(SystemSettingsTypes.PARKING_TIMESLOT_INTERVAL)
#
#         start = datetime.fromisoformat(validate_datetime(dto.start))\
#             if dto.start else getattr(parking_timeslot, "start")
#         end = getattr(parking_timeslot, "end") \
#             if not dto.end else datetime.fromisoformat(validate_datetime(dto.end)) + timedelta(minutes=minutes)
#
#         timeslot: timedelta = end - start
#         await self.check_time_interval(timeslot)
#
#         if dto.parking_place:
#             parking_place = await self.get_parking_place(dto.parking_place)
#             await self.get_timeslots(start, end, parking_place, parking_timeslot)
#         else:
#             timeslots = await self.get_timeslots(start, end)
#             parking_place = await self.get_available_parking_place(timeslots, start, end)
#
#         setattr(parking_timeslot, "start", start)
#         setattr(parking_timeslot, "end", end)
#         setattr(parking_timeslot, "timeslot", str(timeslot))
#         setattr(parking_timeslot, "parking_place", parking_place)
#         setattr(parking_timeslot, "transport", transport)
#
#         await parking_timeslot.save()
#         return parking_timeslot
#
#     @atomic()
#     async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
#         return await super().delete(system_user, entity_id)
#
#     async def get_parking_place(self, _id: EntityId) -> ParkingPlace:
#         parking_place = await ParkingPlace.get_or_none(id=_id)
#         if parking_place is None:
#             raise InconsistencyError(message=f"Parking place with id={_id} doesn't exist.")
#         return parking_place
#
#     async def check_time_interval(self, timeslot: timedelta) -> None:
#         """Check if booking interval not more than SystemSettings.max_parking_time_hours"""
#         max_parking_time_hours: int = await get_system_settings(SystemSettingsTypes.MAX_PARKING_TIME_HOURS)
#         if timeslot > timedelta(hours=max_parking_time_hours):
#             raise InconsistencyError(message=f"Time interval shouldn't be more than {max_parking_time_hours} hours. "
#                                              f"Chosen interval = {str(timeslot)}")
#
#
#     async def get_timeslots(self, start: datetime, end: datetime,
#                             parking_place: ParkingPlace = None,
#                             parking_timeslot: ParkingTimeslot = None) -> list[Optional[ParkingTimeslot]]:
#         """Searching for timeslots with or without parking place, depends on provided time intervals"""
#         p_t = parking_timeslot if parking_timeslot else ParkingTimeslot
#
#         if parking_place:
#             timeslots = await p_t.filter(
#                 Q(parking_place=parking_place) & Q(
#                     Q(start__gte=start, end__lte=end) |
#                     Q(start__lte=start, end__gte=start) |
#                     Q(start__lte=end, end__gte=end) |
#                     Q(start__lte=start, end__gte=end)
#                 )
#             )
#             if timeslots:
#                 raise InconsistencyError(message=f"For parking place: {parking_place}. "
#                                                  f"This time interval:\n"
#                                                  f"{start} - "
#                                                  f"{end} already booked")
#             return timeslots
#
#         timeslots = await p_t.filter(
#             Q(start__gte=start, end__lte=end) |
#             Q(start__lte=start, end__gte=start) |
#             Q(start__lte=end, end__gte=end) |
#             Q(start__lte=start, end__gte=end)
#         )
#         return timeslots
#
#     async def get_available_parking_place(self, timeslots: list[Optional[ParkingTimeslot]],
#                                           start: datetime, end: datetime) -> ParkingPlace:
#         """Returning Any available free ParkingPlace, which is not intersect with given timeslot"""
#         parking_place = await ParkingPlace.filter(
#             Q(parking_timeslot=None) |
#             ~Q(id__in=[_.parking_place_id for _ in timeslots])
#         ).first()
#         if not parking_place:
#             raise InconsistencyError(message=f"There is no available parking place for this time interval:\n"
#                                              f"{start} - "
#                                              f"{end}")
#         return parking_place
#
#     async def data_to_event(self, system_user: EntityId,
#                             parking_timeslot: EntityId) -> dict[str, Union[str, EntityId, datetime]]:
#         """Preparing data for MaxParkingTimeHoursExceededEvent"""
#         max_parking_time_hours: int = await settings.system_settings("max_parking_time_hours")
#         time_to_send: datetime = datetime.now().astimezone() + timedelta(hours=max_parking_time_hours)
#         data = {
#             "system_user": system_user,
#             "parking_timeslot": parking_timeslot,
#             "time_to_send": time_to_send,
#             "message": "Превышено максимально допустимое время нахождения гостевого автомобиля на парковке."
#         }
#         return data
#
#     @staticmethod
#     @atomic()
#     async def create_strangerthings_sse_event(data: dict[str, Union[str, EntityId, dict]]) -> None:
#         """
#         Saving new event to DB.
#         Then calling @post_save(StrangerThings) signal and publish it to SSE.
#         """
#         system_user = await SystemUser.get_or_none(id=data.pop("system_user"))
#         parking_timeslot = await ParkingTimeslot.get_or_none(id=data.pop("parking_timeslot"))
#         transport = await Transport.get_or_none(id=getattr(parking_timeslot, "transport_id"))
#         parking_place = await ParkingPlace.get_or_none(id=getattr(parking_timeslot, "parking_place_id"))
#         data.update(
#             {
#                 "parking_timeslot": await parking_timeslot.values_dict(),
#                 "transport": await transport.values_dict(),
#                 "parking_place": await parking_place.values_dict()
#             }
#         )
#
#         await StrangerThings.create(system_user=system_user, max_parking_time_hours=data)
