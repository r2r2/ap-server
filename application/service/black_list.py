from tortoise.transactions import atomic

import settings
from application.exceptions import InconsistencyError
from application.service.base_service import BaseService
from core.communication.celery.sending_emails import \
    create_email_struct_for_sec_officers
from core.communication.event import (NotifyVisitorInBlackListEvent,
                                      SendWebPushEvent)
from core.dto.access import EntityId
from core.dto.service import BlackListDto, EmailStruct, WebPush
from infrastructure.database.models import (AbstractBaseModel, BlackList,
                                            PushSubscription, SystemUser,
                                            Visitor)


class BlackListService(BaseService):
    target_model = BlackList

    async def collect_target_users(self, visitor: Visitor, user: SystemUser) -> EmailStruct:
        email_struct, security_officers = await create_email_struct_for_sec_officers(visitor, user)
        # Send web push notifications
        subscriptions = await PushSubscription.filter(system_user__id__in=[user.id for user in security_officers])
        data = WebPush.ToCelery(subscriptions=subscriptions, title=email_struct.subject, body=email_struct.text)
        self.notify(SendWebPushEvent(data=data))
        return email_struct

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: BlackListDto.CreationDto) -> AbstractBaseModel:
        visitor = await Visitor.get_or_none(id=dto.visitor)
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={dto.visitor} does not exist."
                                             "You should provide valid Visitor for BlackList")
        if await BlackList.exists(visitor=visitor.id):
            raise InconsistencyError(message=f"Visitor with id={dto.visitor} already in BlackList.")

        black_list = await BlackList.create(visitor=visitor,
                                            level=dto.level)

        self.notify(NotifyVisitorInBlackListEvent(await self.collect_target_users(visitor, user=system_user)))

        return black_list

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: BlackListDto.UpdateDto) -> BlackList:
        black_list = await BlackList.get_or_none(id=entity_id).prefetch_related('visitor')
        if black_list is None:
            raise InconsistencyError(message=f"BlackList with id={entity_id} does not exist.")
        visitor = black_list.visitor

        for field, value in dto.dict().items():
            if value:
                if field == "visitor":
                    # setattr(black_list, field, visitor)
                    continue
                else:
                    setattr(black_list, field, value)

        await black_list.save()
        self.notify(NotifyVisitorInBlackListEvent(await self.collect_target_users(visitor, user=system_user)))

        return black_list

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        black_list = await BlackList.get_or_none(id=entity_id).prefetch_related("visitor")
        if black_list is None:
            raise InconsistencyError(message=f"BlackList with id={entity_id} does not exist.")

        visitor = black_list.visitor
        self.notify(NotifyVisitorInBlackListEvent(await self.collect_target_users(visitor, user=system_user)))

        await black_list.delete()
        return entity_id
