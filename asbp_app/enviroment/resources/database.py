import os
from datetime import datetime
from typing import Dict, List

import loguru
from tortoise import BaseDBAsyncClient
from tortoise.transactions import atomic
from web_foundation.environment.resources.database.database import DatabaseResource
from web_foundation.environment.workers.web.ext.router import DictRouter
from web_foundation.kernel.abstract.dependency import Dependency
from web_foundation.utils.crypto import BaseCrypto

from asbp_app.config import Config
from asbp_app.enviroment.infrastructure.database.models import *


@atomic()
async def create_roles(routing: dict):
    roles = await UserRole.all()
    existed_roles_names = [role.name for role in roles]
    roles_to_create = []
    for app_route in routing.get("apps"):
        for endpoint, versions in app_route.get("endpoints").items():
            for version, params in versions.items():
                scope = params.pop('scope', None)
                if not scope:
                    continue
                endp_handler = params.get("handler")
                for meth_name, param in params.items():
                    if not isinstance(param, dict):
                        continue
                    handler = param.get('handler') if param.get('handler') else endp_handler
                    base_name = handler.__name__
                    if base_name in existed_roles_names:
                        continue
                    if scope == 'access':
                        if base_name.endswith("__read") or base_name.endswith("__edit"):
                            roles_to_create.append(UserRole(name=base_name, route=endpoint))
                            existed_roles_names.append(base_name)
                            continue
                        if meth_name.lower() == 'get':
                            role_name = base_name + "__read"
                            if role_name in existed_roles_names:
                                continue
                            roles_to_create.append(UserRole(name=role_name, route=endpoint))
                            existed_roles_names.append(role_name)
                        if meth_name.lower() in ['post', 'patch', 'delete']:
                            role_name = base_name + "__edit"
                            if role_name in existed_roles_names:
                                continue
                            roles_to_create.append(UserRole(name=role_name, route=endpoint))
                            existed_roles_names.append(role_name)

                    elif scope == 'service':
                        roles_to_create.append(UserRole(name=base_name, route=endpoint))
                        existed_roles_names.append(base_name)
    await UserRole.bulk_create(roles_to_create)
    root_group, created = await UserRoleGroup.update_or_create(name="root")
    await root_group.roles.add(*roles)


@atomic()
async def create_settings():
    # ----------- EMAIL ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.EMAIL_HOST,
                                value="smtp.timeweb.ru",
                                category=SystemSettingsCategory.EMAIL_SERVICE)
    await SystemSettings.create(name=SystemSettingsTypes.EMAIL_PORT,
                                value=465,
                                category=SystemSettingsCategory.EMAIL_SERVICE)
    await SystemSettings.create(name=SystemSettingsTypes.EMAIL_USER,
                                value="noreply@asbp.ru",
                                category=SystemSettingsCategory.EMAIL_SERVICE)
    await SystemSettings.create(name=SystemSettingsTypes.EMAIL_PASS,
                                value="password",
                                category=SystemSettingsCategory.EMAIL_SERVICE)
    await SystemSettings.create(name=SystemSettingsTypes.EMAIL_SENDER,
                                value="noreply@asbp.ru",
                                category=SystemSettingsCategory.EMAIL_SERVICE)

    # ----------- CLAIM ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.CLAIM_URL,
                                value="http://0.0.0.0:8000/claims/{claim}",
                                category=SystemSettingsCategory.CLAIM)
    await SystemSettings.create(name=SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES,
                                value=60,
                                category=SystemSettingsCategory.CLAIM)

    # ----------- NOTIFICATIONS ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.CLAIMWAY_SUBJECT_TEXT,
                                value="Вам пришло новое письмо для согласования заявки!",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.CLAIMWAY_BODY_TEXT,
                                value="Здравствуйте!\nВам необходимо согласовать заявку {claim}.\n"
                                      "Посмотреть заявку можно по ссылке:\n\n[{url}]",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    await SystemSettings.create(name=SystemSettingsTypes.CLAIM_STATUS_BODY_TEXT,
                                value="Здравствуйте!\nУ заявки {claim} изменился статус на [{status}].",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.CLAIM_STATUS_SUBJECT_TEXT,
                                value="Изменение статуса заявки {claim}.",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    await SystemSettings.create(name=SystemSettingsTypes.CLAIM_APPROVED_BODY_TEXT,
                                value="Здравствуйте!\nЗаявка {claim} была одобрена.\n"
                                      "Посмотреть заявку можно по ссылке:\n\n[{url}]",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.CLAIM_APPROVED_SUBJECT_TEXT,
                                value="Заявка {claim} была согласована.",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    await SystemSettings.create(name=SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT,
                                value="Срочно согласовать заявку {claim}.",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.CLAIMWAY_BEFORE_N_MINUTES_BODY_TEXT,
                                value="Здравствуйте!\n"
                                      "Внимание! Необходимо срочно согласовать заявку: \n\n[{url}]\n"
                                      "Поскольку {visit_start_date} она станет действующей.",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    await SystemSettings.create(name=SystemSettingsTypes.BLACKLIST_NOTIFICATION_BODY_TEXT,
                                value="Здравствуйте!\n"
                                      "Сотрудник: {user} - оформил заявку на посетителя из ЧС.\n"
                                      "Посетитель: {visitor}.",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.BLACKLIST_NOTIFICATION_SUBJECT_TEXT,
                                value="Сотрудник оформил заявку на пользователя из ЧС.",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    await SystemSettings.create(name=SystemSettingsTypes.VISITOR_WAS_DELETED_FROM_BLACKLIST_BODY,
                                value="Пользователь был удален из ЧС.",
                                category=SystemSettingsCategory.NOTIFICATIONS)
    await SystemSettings.create(name=SystemSettingsTypes.VISITOR_WAS_DELETED_FROM_BLACKLIST_SUBJECT,
                                value="Пользователь был удален из ЧС.",
                                category=SystemSettingsCategory.NOTIFICATIONS)

    # ----------- RESTRICTIONS ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.MAX_USER_LICENSE,
                                value=100,
                                category=SystemSettingsCategory.RESTRICTIONS)
    await SystemSettings.create(name=SystemSettingsTypes.MAX_PHOTO_UPLOAD,
                                value=10,
                                category=SystemSettingsCategory.RESTRICTIONS)
    await SystemSettings.create(name=SystemSettingsTypes.MAX_PARKING_TIME_HOURS,
                                value=8,
                                category=SystemSettingsCategory.RESTRICTIONS)
    await SystemSettings.create(name=SystemSettingsTypes.PARKING_TIMESLOT_INTERVAL,
                                value=0,
                                category=SystemSettingsCategory.RESTRICTIONS)
    await SystemSettings.create(name=SystemSettingsTypes.DAYS_BEFORE_ARCHIVE,
                                value=60,
                                category=SystemSettingsCategory.RESTRICTIONS)

    # ----------- WATERMARK ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.WATERMARK_TRANSPARENCY,
                                value=128,
                                category=SystemSettingsCategory.WATERMARK)
    await SystemSettings.create(name=SystemSettingsTypes.WATERMARK_FORMAT,
                                value="PNG",
                                category=SystemSettingsCategory.WATERMARK)
    await SystemSettings.create(name=SystemSettingsTypes.WATERMARK_FONT_SIZE,
                                value=24,
                                category=SystemSettingsCategory.WATERMARK)
    await SystemSettings.create(name=SystemSettingsTypes.WATERMARK_FONT_TYPE,
                                value='FreeMono.ttf',
                                category=SystemSettingsCategory.WATERMARK)
    await SystemSettings.create(name=SystemSettingsTypes.WATERMARK_FONT_RGB_COLOR,
                                value="80,0,0",
                                category=SystemSettingsCategory.WATERMARK)

    # ----------- WEB_PUSH ---------------- #
    await SystemSettings.create(name=SystemSettingsTypes.VAPID_PRIVATE_KEY,
                                value="OX_52Uf3XDjjuHbJHIP7wXKXu_u56Y_K5ZoffhiZR3c",
                                category=SystemSettingsCategory.WEB_PUSH)
    await SystemSettings.create(name=SystemSettingsTypes.VAPID_PUBLIC_KEY,
                                value="BDu6tBfNIhThUj5epb8P9nvQsuMQuF_7C8PeKPtW_GPM6nzHTyHLuuRm0_cMdLYZDhWXIsECK-9CXZB6i_s6BOA",
                                category=SystemSettingsCategory.WEB_PUSH)
    await SystemSettings.create(name=SystemSettingsTypes.VAPID_CLAIM_EMAIL,
                                value="mailto:test@test.test",
                                category=SystemSettingsCategory.WEB_PUSH)




async def fill_with_default_data():
    await create_settings()
    # from faker import Faker

    # fake = Faker("ru_RU")

    # await SystemSettings.create(
    #     claimway_before_n_minutes=60,
    #     max_systemuser_license=100,
    #     max_photo_upload=10,
    #     watermark_transparency=128,
    #     watermark_font_size=24,
    #     watermark_font_type='FreeMono.ttf',
    #     watermark_font_rgb_color="80,0,0",
    #     days_before_archive=60,
    #     max_parking_time_hours=8,
    #     parking_timeslot_interval=10,
    # )
    # root_role = await Role.create(name='root')
    # admin_role = await Role.create(name='Администратор')
    # applicant_role = await Role.create(name='Заявитель')  # Роль, позволяющая оформить заявку на посещение
    # security_officer_role = await Role.create(
    #     name="Сотрудник службы безопасности")  # Роль, имеющая возможность просмотра событий по заявкам
    # operator_role = await Role.create(
    #     name="Оператор Бюро пропусков")  # Имеющий полномочия оформлять пропуска на вход. Заявки на оформление пропуска поступают Оператору через Систему

    crypted_password, salt = BaseCrypto.encrypt_password("123456")

    root = await SystemUser.create(first_name='firstName',
                                   last_name='lastName',
                                   username="root",
                                   password=crypted_password,
                                   salt=salt,
                                   email="test@test.com")
    # await root.scopes.add(root_role, admin_role, security_officer_role)

    # amount = 1000
    # number = [fake.unique.random_int(min=10 ** 9, max=10 ** 10 - 2) for _ in range(amount)]
    #
    # parking = await Parking.create(name="гостевая", max_places=amount)
    # await Parking.create(name="частная", max_places=50)
    #
    # for i in range(amount):
    #     start_time = fake.date_time_this_month(before_now=False, after_now=True)
    #     end_time = fake.date_time_between(start_date=start_time, end_date="+20d")
    #
    #     sys_user = await SystemUser.create(first_name=fake.first_name(),
    #                                        last_name=fake.last_name(),
    #                                        middle_name=fake.middle_name(),
    #                                        phone="7499" + str(fake.random.randint(10 ** 6, 10 ** 7 - 1)),
    #                                        email=fake.email(),
    #                                        username=fake.user_name() + str(fake.random.randint(1, 999)),
    #                                        password=crypted_password,
    #                                        salt=salt,
    #                                        cabinet_number=fake.building_number(),
    #                                        department_name=fake.word())
    #
    #     await sys_user.scopes.add(fake.random.choice([applicant_role, operator_role, security_officer_role]))
    #
    #     passport = await Passport.create(number=number[i],
    #                                      place_of_birth=fake.city(),
    #                                      place_of_issue=f"ОВД {fake.city()}",
    #                                      division_code=fake.postcode(),
    #                                      date_of_birth=fake.date_of_birth(minimum_age=18),
    #                                      registration=fake.address(),
    #                                      gender=fake.random.choice(["МУЖ", "ЖЕН"]))
    #
    #     drive_license = await DriveLicense.create(number=int(str(number[i])[::-1]),
    #                                               date_of_issue=fake.date_this_decade(),
    #                                               expiration_date=fake.date_this_decade(before_today=False,
    #                                                                                     after_today=True),
    #                                               place_of_issue=fake.address(),
    #                                               address_of_issue=fake.address(),
    #                                               categories=fake.random.choice(["A", "B", "C", "D", "E"]))
    #
    #     military_id = await MilitaryId.create(number=fake.aba(),
    #                                           date_of_birth=fake.date_of_birth(),
    #                                           place_of_issue=fake.street_address(),
    #                                           date_of_issue=fake.date_this_century(),
    #                                           place_of_birth=fake.city())
    #
    #     claim_way = await ClaimWay.create()
    #     await claim_way.roles.add(admin_role)
    #     await claim_way.system_users.add(root, sys_user)
    #
    #     claim = await Claim.create(pass_type=fake.random.choice(["разовый", "временный", "материальный"]),
    #                                status=fake.random.choice(["действующая", "отработана", "просрочена"]),
    #                                claim_way=claim_way,
    #                                information=fake.sentence(nb_words=10),
    #                                system_user=sys_user)
    #
    #     await ClaimWayApproval.create(system_user=root, claim=claim)
    #     await ClaimWayApproval.create(system_user=sys_user, claim=claim)
    #
    #     parking_place = await ParkingPlace.create(real_number=i + 1, parking=parking)
    #     transport = await Transport.create(number=fake.license_plate() + str(i),
    #                                        color=fake.color_name())
    #     await transport.claims.add(claim)
    #
    #     start = fake.date_time_this_month(before_now=False, after_now=True)
    #     end = fake.date_time_between(start_date=start, end_date="+2d")
    #     timeslot = end - start
    #     await ParkingTimeslot.create(parking_place=parking_place,
    #                                  transport=transport,
    #                                  start=start,
    #                                  end=end,
    #                                  timeslot=str(timeslot))
    #
    #     visitor = await Visitor.create(first_name=fake.first_name(),
    #                                    last_name=fake.last_name(),
    #                                    middle_name=fake.middle_name(),
    #                                    who_invited=fake.name(),
    #                                    email=fake.email(),
    #                                    phone="8916" + str(fake.random.randint(10 ** 6, 10 ** 7 - 1)),
    #                                    visit_purpose=fake.bs(),
    #                                    passport=passport,
    #                                    military_id=military_id,
    #                                    drive_license=drive_license,
    #                                    transport=transport,
    #                                    claim=claim,
    #                                    company_name=fake.large_company(),
    #                                    visit_start_date=start_time,
    #                                    visit_end_date=end_time,
    #                                    destination=fake.word())
    #
    #     await VisitSession.create(visitor=visitor, enter=start_time)
    #
    #     pass_id = await Pass.create(pass_type=fake.random.choice(["бумажный", "карта", "лицо"]),
    #                                 valid_till_date=end_time,
    #                                 rfid=fake.random.randint(10 ** 6, 10 ** 7 - 1))
    #     await ClaimToZone.create(claim=claim, pass_id=pass_id)
    #
    #     if i & 1 and i < amount // 2:
    #         await BlackList.create(level=fake.random.choice(["Зелёный", "Жёлтый", "Красный"]),
    #                                visitor=visitor,
    #                                comment=fake.sentence(nb_words=10))
    #
    # await Zone.bulk_create([
    #     Zone(name='reception'),
    #     Zone(name='parking'),
    #     Zone(name='2nd floor'),
    #     Zone(name="laboratory")
    # ])


class AsbpDatabaseResource(DatabaseResource):
    routing: Dependency[dict]

    def __init__(self, modules: List[str], router: Dependency[dict]):
        super().__init__(modules)
        self.routing = router

    async def init(self, config: Config, **kwargs) -> BaseDBAsyncClient:
        con = await super(AsbpDatabaseResource, self).init(config)
        await create_roles(self.routing())
        return con

    # async def init(self, app_name: str, db_config: Dict, modules: List[str],
    #                engine: str = 'tortoise.backends.asyncpg', routing: dict = None) -> BaseDBAsyncClient:
    #

    async def fill_db_data(self):
        await create_roles(self.routing())
        # TODO "fill_with_default_data" call
        await fill_with_default_data()
        # await self.conn.execute_query(
        #     "create index opened_ticket on eq.ticket (completed_at) where completed_at is NULL;")
        # await self.conn.execute_query("create index opened_issue on eq.issue (closed) where closed = False;")
