from aerich import Command
from loguru import logger
from sanic import Sanic
from tortoise import BaseDBAsyncClient, Tortoise
from tortoise.transactions import atomic

import settings
from application.service.scope_constructor import init_scopes
from core.utils.encrypt import encrypt_password
from infrastructure.database.connection import sample_conf
from infrastructure.database.models import (BlackList, Claim, ClaimToZone,
                                            ClaimWay, ClaimWayApproval,
                                            DriveLicense, MilitaryId, Parking,
                                            ParkingPlace, ParkingTimeslot,
                                            Pass, Passport, Role,
                                            SystemSettings, SystemUser,
                                            Transport, Visitor, VisitSession,
                                            Zone)


@atomic(settings.CONNECTION_NAME)
async def fill_with_default_data() -> None:
    from faker import Faker

    fake = Faker("ru_RU")

    await SystemSettings.create(
        claimway_before_n_minutes=60,
        max_systemuser_license=100,
        max_photo_upload=10,
        watermark_transparency=128,
        watermark_font_size=24,
        watermark_font_type='FreeMono.ttf',
        watermark_font_rgb_color="80,0,0",
        days_before_archive=60,
        max_parking_time_hours=8,
        parking_timeslot_interval=10,
    )
    root_role = await Role.create(name='root')
    admin_role = await Role.create(name='Администратор')
    applicant_role = await Role.create(name='Заявитель')  # Роль, позволяющая оформить заявку на посещение
    security_officer_role = await Role.create(name="Сотрудник службы безопасности")  # Роль, имеющая возможность просмотра событий по заявкам
    operator_role = await Role.create(name="Оператор Бюро пропусков")  # Имеющий полномочия оформлять пропуска на вход. Заявки на оформление пропуска поступают Оператору через Систему

    crypted_password, salt = encrypt_password("123456")

    root = await SystemUser.create(first_name='firstName',
                                   last_name='lastName',
                                   username="root",
                                   password=crypted_password,
                                   salt=salt,
                                   email="test@test.com")
    await root.scopes.add(root_role, admin_role, security_officer_role)

    amount = 1000
    number = [fake.unique.random_int(min=10 ** 9, max=10 ** 10 - 2) for _ in range(amount)]

    parking = await Parking.create(name="гостевая", max_places=amount)
    await Parking.create(name="частная", max_places=50)

    for i in range(amount):
        start_time = fake.date_time_this_month(before_now=False, after_now=True)
        end_time = fake.date_time_between(start_date=start_time, end_date="+20d")

        sys_user = await SystemUser.create(first_name=fake.first_name(),
                                           last_name=fake.last_name(),
                                           middle_name=fake.middle_name(),
                                           phone="7499" + str(fake.random.randint(10 ** 6, 10 ** 7 - 1)),
                                           email=fake.email(),
                                           username=fake.user_name() + str(fake.random.randint(1, 999)),
                                           password=crypted_password,
                                           salt=salt,
                                           cabinet_number=fake.building_number(),
                                           department_name=fake.word())

        await sys_user.scopes.add(fake.random.choice([applicant_role, operator_role, security_officer_role]))

        passport = await Passport.create(number=number[i],
                                         place_of_birth=fake.city(),
                                         place_of_issue=f"ОВД {fake.city()}",
                                         division_code=fake.postcode(),
                                         date_of_birth=fake.date_of_birth(minimum_age=18),
                                         registration=fake.address(),
                                         gender=fake.random.choice(["МУЖ", "ЖЕН"]))

        drive_license = await DriveLicense.create(number=int(str(number[i])[::-1]),
                                                  date_of_issue=fake.date_this_decade(),
                                                  expiration_date=fake.date_this_decade(before_today=False,
                                                                                        after_today=True),
                                                  place_of_issue=fake.address(),
                                                  address_of_issue=fake.address(),
                                                  categories=fake.random.choice(["A", "B", "C", "D", "E"]))

        military_id = await MilitaryId.create(number=fake.aba(),
                                              date_of_birth=fake.date_of_birth(),
                                              place_of_issue=fake.street_address(),
                                              date_of_issue=fake.date_this_century(),
                                              place_of_birth=fake.city())

        claim_way = await ClaimWay.create()
        await claim_way.roles.add(admin_role)
        await claim_way.system_users.add(root, sys_user)

        claim = await Claim.create(pass_type=fake.random.choice(["разовый", "временный", "материальный"]),
                                   status=fake.random.choice(["действующая", "отработана", "просрочена"]),
                                   claim_way=claim_way,
                                   information=fake.sentence(nb_words=10),
                                   system_user=sys_user)

        await ClaimWayApproval.create(system_user=root, claim=claim)
        await ClaimWayApproval.create(system_user=sys_user, claim=claim)

        parking_place = await ParkingPlace.create(real_number=i + 1, parking=parking)
        transport = await Transport.create(number=fake.license_plate() + str(i),
                                           color=fake.color_name())
        await transport.claims.add(claim)

        start = fake.date_time_this_month(before_now=False, after_now=True)
        end = fake.date_time_between(start_date=start, end_date="+2d")
        timeslot = end - start
        await ParkingTimeslot.create(parking_place=parking_place,
                                     transport=transport,
                                     start=start,
                                     end=end,
                                     timeslot=str(timeslot))

        visitor = await Visitor.create(first_name=fake.first_name(),
                                       last_name=fake.last_name(),
                                       middle_name=fake.middle_name(),
                                       who_invited=fake.name(),
                                       email=fake.email(),
                                       phone="8916" + str(fake.random.randint(10 ** 6, 10 ** 7 - 1)),
                                       visit_purpose=fake.bs(),
                                       passport=passport,
                                       military_id=military_id,
                                       drive_license=drive_license,
                                       transport=transport,
                                       claim=claim,
                                       company_name=fake.large_company(),
                                       visit_start_date=start_time,
                                       visit_end_date=end_time,
                                       destination=fake.word())

        await VisitSession.create(visitor=visitor, enter=start_time)

        pass_id = await Pass.create(pass_type=fake.random.choice(["бумажный", "карта", "лицо"]),
                                    valid_till_date=end_time,
                                    rfid=fake.random.randint(10 ** 6, 10 ** 7 - 1))
        await ClaimToZone.create(claim=claim, pass_id=pass_id)

        if i & 1 and i < amount // 2:
            await BlackList.create(level=fake.random.choice(["Зелёный", "Жёлтый", "Красный"]),
                                   visitor=visitor)

    await Zone.bulk_create([
        Zone(name='reception'),
        Zone(name='parking'),
        Zone(name='2nd floor'),
        Zone(name="laboratory")
    ])


async def make_migrations() -> None:
    """Making initial migrations"""
    import subprocess

    logger.info("Making migrations...")
    subprocess.run(settings.AERICH_MIGRATION_COMMANDS, shell=True)
    logger.info("Initial migrations has finished.")


async def setup_db(conn: BaseDBAsyncClient, app: Sanic, conn_archive: BaseDBAsyncClient) -> None:
    row_count, rows = await conn.execute_query(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'asbp'")

    await conn_archive.execute_query(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'archive'")

    if not row_count:
        await conn_archive.execute_script("CREATE SCHEMA IF NOT EXISTS archive;")
        await conn.execute_script("CREATE SCHEMA IF NOT EXISTS asbp;")
        logger.info("Creating initial database.")
        await Tortoise.generate_schemas()
        await fill_with_default_data()
        await init_scopes(app)
        await make_migrations()
    else:
        if settings.DEBUG is True:
            command = Command(tortoise_config=sample_conf,
                              app="asbp",
                              location=f"{settings.BASE_DIR}/infrastructure/database/migrations/")
            await command.init()
            await command.migrate()
            logger.info("Applying migrations...")

            await Tortoise.close_connections()
        pass
