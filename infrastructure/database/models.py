from enum import Enum
from typing import TypeVar

from tortoise import fields
from tortoise.models import Model


class AbstractBaseModel(Model):
    """Базовая модель"""
    id = fields.IntField(pk=True)

    async def values_dict(self, m2m_fields: bool = False, fk_fields: bool = False,
                          backward_fk_fields: bool = False, o2o_fields: bool = False) -> dict:
        t_d = {}
        for k, v in self.__dict__.items():
            if isinstance(v, bytes):
                v = v.decode("utf-8", 'replace')
            if not k.startswith('_'):
                t_d.update({k: v})
        if fk_fields:
            for field in self._meta.fk_fields:
                if model_attr := getattr(self, field):
                    if model := await model_attr:
                        t_d.update({field: await model.values_dict()})
        if m2m_fields:
            for field in self._meta.m2m_fields:
                t_d.update({field: [await i.values_dict() for i in await getattr(self, field) if i]})
                if m2m_fields:
                    for field in self._meta.m2m_fields:
                        models = getattr(self, field)
                        if not models._fetched:
                            if not m2m_fields:
                                continue
                            models = await models
                        t_d.update({field: [await i.values_dict() for i in models if i]})
        if backward_fk_fields:
            for field in self._meta.backward_fk_fields:
                model = getattr(self, field)
                if isinstance(model, fields.ReverseRelation):
                    model = await model.all()
                if model:
                    t_d.update({field: [await i.values_dict() for i in model if i]})
        if o2o_fields:
            for field in self._meta.o2o_fields:
                if model_attr := getattr(self, field):
                    if model := await model_attr:
                        t_d.update({field: await model.values_dict()})

        return t_d

    class Meta:
        abstract = True


MODEL = TypeVar("MODEL", bound=AbstractBaseModel)


class TimestampMixin:
    """Общий миксин даты создания и изменения"""
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)


class FakeDeleted:
    """Помечает объект удаленным, вместо удаления"""
    deleted = fields.BooleanField(default=False)


# ------------------------------------USER---------------------------------

class SystemUser(AbstractBaseModel, TimestampMixin, FakeDeleted):
    """Сотрудник компании"""
    first_name = fields.CharField(max_length=36, description="Имя")
    last_name = fields.CharField(max_length=36, description="Фамилия")
    middle_name = fields.CharField(max_length=36, null=True, description="Отчество")
    username = fields.CharField(max_length=36, unique=True, index=True)
    password = fields.TextField()
    salt = fields.TextField()
    last_login = fields.DatetimeField(default=None, null=True)
    last_logout = fields.DatetimeField(default=None, null=True)
    expire_session_delta = fields.IntField(default=86400)
    phone = fields.CharField(max_length=24, null=True, index=True)
    email = fields.CharField(max_length=36, null=True, index=True)
    cabinet_number = fields.CharField(max_length=12, null=True, description="Номер кабинета")
    department_name = fields.CharField(max_length=255, null=True, description="Название отдела")
    scopes: fields.ManyToManyRelation["Role"] = fields.ManyToManyField(
        'asbp.Role', related_name='scopes', through='systemuser_scopes'
    )

    claim_ways: fields.ManyToManyRelation["ClaimWay"]
    claim_way_approval: fields.ReverseRelation["ClaimWayApproval"]
    system_user_session: fields.ReverseRelation["SystemUserSession"]
    active_dir: fields.ReverseRelation["ActiveDir"]
    stranger_things: fields.ReverseRelation["StrangerThings"]
    push_subscription: fields.ReverseRelation["PushSubscription"]
    claims: fields.ReverseRelation["Claim"]

    def __str__(self) -> str:
        return f"{self.username}: {self.first_name} {self.last_name}"

    def to_dict(self) -> dict:
        return {"user_id": self.id, "username": self.username,
                "scopes": [i.name for i in self.scopes]}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SystemUserSession(AbstractBaseModel):
    """Данные сессии сотрудника компании"""
    user: fields.ForeignKeyNullableRelation["SystemUser"] = fields.ForeignKeyField(
        "asbp.SystemUser", null=True, on_delete=fields.CASCADE
    )
    expire_time = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    logout_time = fields.DatetimeField(null=True)
    user_agent = fields.TextField(null=True)
    salt = fields.TextField()
    nonce = fields.TextField()
    tag = fields.TextField()


class Role(AbstractBaseModel, TimestampMixin):
    """Роли пользователей для согласований"""
    name = fields.CharField(max_length=255, description='Название роли')

    scopes: fields.ManyToManyRelation["SystemUser"]
    claim_ways: fields.ManyToManyRelation["ClaimWay"]
    enable_scopes: fields.ManyToManyRelation["EnableScope"]

    def __str__(self) -> str:
        return f"{self.name}"


class EnableScope(AbstractBaseModel, TimestampMixin):
    """Доступные роли для конкретного роута"""
    name = fields.CharField(max_length=64, description="Название роута")
    scopes: fields.ManyToManyRelation["Role"] = fields.ManyToManyField(
        'asbp.Role', related_name='enable_scopes', through='enablescope_role'
    )

    def __str__(self) -> str:
        return f"{self.name}-> {[scope.name for scope in self.scopes]}"


class ActiveDir(AbstractBaseModel):
    """Данные пользователя из Active Directory"""
    user: fields.ForeignKeyRelation["SystemUser"] = fields.ForeignKeyField(
        "asbp.SystemUser", on_delete=fields.CASCADE, related_name='user'
    )
    sid = fields.CharField(max_length=128, null=True, description='SID пользователя')


# ------------------------------------VISITOR---------------------------------


class Visitor(AbstractBaseModel, TimestampMixin, FakeDeleted):
    """Посетитель"""
    first_name = fields.CharField(max_length=24, description="Имя")
    last_name = fields.CharField(max_length=24, description="Фамилия")
    middle_name = fields.CharField(max_length=24, null=True, description="Отчество")
    who_invited = fields.CharField(max_length=255, null=True, description='Кто пригласил?')
    destination = fields.CharField(max_length=128, null=True, description='Куда идет?')
    company_name = fields.CharField(max_length=255, null=True, description="организация посетителя")
    date_of_birth = fields.DateField(description='Дата рождения', null=True)
    attribute = fields.CharField(max_length=64, null=True, description="признак (иностранец)")
    phone = fields.CharField(max_length=24, null=True, index=True)
    email = fields.CharField(max_length=36, null=True, index=True)
    visit_purpose = fields.CharField(max_length=255, null=True, description="цель посещения")
    visit_start_date = fields.DatetimeField(null=True, description="дата или период посещения")
    visit_end_date = fields.DatetimeField(null=True, description="дата или период посещения")

    passport: fields.OneToOneNullableRelation["Passport"] = fields.OneToOneField(
        'asbp.Passport', on_delete=fields.CASCADE, related_name='visitor', null=True, index=True
    )
    international_passport: fields.OneToOneNullableRelation["InternationalPassport"] = fields.OneToOneField(
        "asbp.InternationalPassport", on_delete=fields.CASCADE, related_name="visitor", null=True, index=True
    )
    pass_id: fields.ForeignKeyNullableRelation["Pass"] = fields.ForeignKeyField(
        'asbp.Pass', on_delete=fields.CASCADE, related_name='visitor', null=True
    )
    drive_license: fields.OneToOneNullableRelation["DriveLicense"] = fields.OneToOneField(
        'asbp.DriveLicense', on_delete=fields.CASCADE, related_name='visitor', null=True, index=True
    )
    visitor_photo: fields.ForeignKeyNullableRelation["VisitorPhoto"] = fields.ForeignKeyField(
        'asbp.VisitorPhoto', on_delete=fields.CASCADE, related_name='visitors', null=True
    )
    transport: fields.ForeignKeyNullableRelation["Transport"] = fields.ForeignKeyField(
        'asbp.Transport', on_delete=fields.CASCADE, related_name='visitors', null=True
    )
    military_id: fields.OneToOneNullableRelation["MilitaryId"] = fields.OneToOneField(
        'asbp.MilitaryId', on_delete=fields.CASCADE, related_name='visitor', null=True, index=True
    )
    claim: fields.ForeignKeyNullableRelation["Claim"] = fields.ForeignKeyField(
        'asbp.Claim', on_delete=fields.CASCADE, related_name='visitors', null=True
    )

    black_lists: fields.ReverseRelation["BlackList"]
    visit_session: fields.ReverseRelation["VisitSession"]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name} {self.middle_name}"


class VisitSession(AbstractBaseModel, TimestampMixin):
    """Время посещения"""
    visitor: fields.ForeignKeyRelation["Visitor"] = fields.ForeignKeyField(
        'asbp.Visitor', on_delete=fields.CASCADE, related_name='visit_session', index=True
    )
    enter = fields.DatetimeField(description='Зашел на территорию', null=True)
    exit = fields.DatetimeField(description='Вышел с территории', null=True)


class Passport(AbstractBaseModel, TimestampMixin):
    """Данные паспорта"""
    number = fields.BigIntField(description='Номер паспорта', unique=True, index=True)
    division_code = fields.CharField(max_length=7, description='Код подразделения', null=True)
    registration = fields.CharField(max_length=255, description='Прописка', null=True)
    date_of_birth = fields.DateField(description='Дата рождения', null=True)
    place_of_birth = fields.CharField(max_length=255, description='Место рождения', null=True)
    place_of_issue = fields.CharField(max_length=255, null=True, description='Орган выдавший паспорт')
    gender = fields.CharField(max_length=8, description='Пол', null=True)
    photo: fields.OneToOneNullableRelation["VisitorPhoto"] = fields.OneToOneField(
        "asbp.VisitorPhoto", on_delete=fields.CASCADE, null=True, related_name="passport", index=True
    )

    visitor: fields.ReverseRelation["Visitor"]

    def __str__(self) -> str:
        return f"Номер паспорта: {self.number}"


class InternationalPassport(AbstractBaseModel, TimestampMixin):
    """Заграничный паспорт"""
    number = fields.BigIntField(description='Номер паспорта', unique=True, index=True)
    date_of_birth = fields.DateField(description='Дата рождения', null=True)
    date_of_issue = fields.DateField(null=True, description='Дата выдачи')
    photo: fields.OneToOneNullableRelation["VisitorPhoto"] = fields.OneToOneField(
        "asbp.VisitorPhoto", on_delete=fields.CASCADE, null=True, related_name="international_passport", index=True
    )

    visitor: fields.ReverseRelation["Visitor"]

    def __str__(self):
        return f"Номер заграничного паспорта: {self.number}"


class DriveLicense(AbstractBaseModel, TimestampMixin):
    """Водительское удостоверение"""
    date_of_issue = fields.DateField(null=True, description='Дата выдачи водительского удостоверения')
    expiration_date = fields.DateField(null=True, description='Дата окончания действия водительского удостоверения')
    place_of_issue = fields.CharField(max_length=255, null=True,
                                      description='Орган выдавший водительское удостоверение')
    address_of_issue = fields.CharField(
        max_length=255, null=True, description='Регион, где было выдано водительское удостоверение'
    )
    number = fields.BigIntField(unique=True, max_length=24, index=True, description='Номер водительского удостоверения')
    categories = fields.CharField(max_length=16, null=True, description='Открытые категории')
    photo: fields.OneToOneNullableRelation["VisitorPhoto"] = fields.OneToOneField(
        "asbp.VisitorPhoto", on_delete=fields.CASCADE, null=True, related_name="drive_license", index=True
    )

    visitor: fields.ReverseRelation["Visitor"]

    def __str__(self) -> str:
        return f"Номер водительского удостоверения: {self.number}"


class MilitaryId(AbstractBaseModel, TimestampMixin):
    """Военный билет"""
    number = fields.CharField(max_length=16, index=True, description='Номер военного билета')
    date_of_birth = fields.DateField(description='Дата рождения', null=True)
    place_of_issue = fields.CharField(max_length=255, null=True, description='Орган выдавший военный билет')
    date_of_issue = fields.DateField(null=True, description='Дата выдачи военного билета')
    place_of_birth = fields.CharField(max_length=255, description='Место рождения', null=True)
    photo: fields.OneToOneNullableRelation["VisitorPhoto"] = fields.OneToOneField(
        "asbp.VisitorPhoto", on_delete=fields.CASCADE, null=True, related_name="militaryid", index=True
    )

    visitor: fields.ReverseRelation["Visitor"]

    def __str__(self) -> str:
        return f"{self.number}"


class WatermarkPosition(Enum):
    """Расположение водяного знака на картинке"""
    UPPER_LEFT = "UPPER_LEFT"
    UPPER_RIGHT = "UPPER_RIGHT"
    LOWER_LEFT = "LOWER_LEFT"
    LOWER_RIGHT = "LOWER_RIGHT"
    CENTER = "CENTER"


class VisitorPhoto(AbstractBaseModel, TimestampMixin):
    """Фото посетителя"""
    signature = fields.JSONField(null=True)
    webcam_img = fields.BinaryField(null=True, description='Фото с веб-камеры')
    scan_img = fields.BinaryField(null=True, description='Скан документа')
    car_number_img = fields.BinaryField(null=True, description='Фото номера транспорта')
    add_watermark_image = fields.BooleanField(default=False, null=True)
    add_watermark_text = fields.BooleanField(default=False, null=True)
    watermark_id = fields.IntField(null=True)
    watermark_position = fields.CharEnumField(
        enum_type=WatermarkPosition, null=True, description="Позиция водяного знака на картинке"
    )
    watermark_width = fields.SmallIntField(null=True, description="Ширина водяного знака")
    watermark_height = fields.SmallIntField(null=True, description="Высота водяного знака")

    visitors: fields.ReverseRelation["Visitor"]
    drive_license: fields.ReverseRelation["DriveLicense"]
    militaryid: fields.ReverseRelation["MilitaryId"]
    international_passport: fields.ReverseRelation["InternationalPassport"]
    passport: fields.ReverseRelation["Passport"]


# ------------------------------------CLAIM---------------------------------

class Claim(AbstractBaseModel, TimestampMixin):
    """Заявка на пропуск"""
    claim_way: fields.ForeignKeyNullableRelation["ClaimWay"] = fields.ForeignKeyField(
        'asbp.ClaimWay', on_delete=fields.CASCADE, related_name='claims', null=True
    )
    claim_way_2: fields.ForeignKeyNullableRelation["ClaimWay"] = fields.ForeignKeyField(
        'asbp.ClaimWay', on_delete=fields.CASCADE, related_name='claims2', null=True
    )
    pass_id: fields.ForeignKeyNullableRelation["Pass"] = fields.ForeignKeyField(
        'asbp.Pass', on_delete=fields.CASCADE, related_name='claims', null=True, index=True
    )
    system_user: fields.ForeignKeyRelation["SystemUser"] = fields.ForeignKeyField(
        'asbp.SystemUser', on_delete=fields.CASCADE, related_name="claims"
    )
    pass_type = fields.CharField(max_length=64, description='Тип пропуска (разовый/временный/материальный)')
    approved = fields.BooleanField(default=False, description='Заявка одобрена?')
    claim_way_approved = fields.BooleanField(null=True, description="Основной маршрут согласования")
    claim_way_2_notified = fields.BooleanField(null=True, description="Отправить оповещение второму маршруту")
    is_in_blacklist = fields.BooleanField(default=False, description='В черном списке?')
    pnd_agreement = fields.BooleanField(default=False, description='Согласие на обработку ПНД')
    information = fields.CharField(max_length=255, null=True, description='Любая информация о заявке')
    status = fields.CharField(max_length=128, description='Статус заявки(действующая/отработана/просрочена)')

    claim_to_zones: fields.ReverseRelation["ClaimToZone"]
    transports: fields.ManyToManyRelation["Transport"]
    visitors: fields.ReverseRelation["Visitor"]
    claim_way_approval: fields.ReverseRelation["ClaimWayApproval"]


class Pass(AbstractBaseModel, TimestampMixin):
    """Пропуск"""
    rfid = fields.CharField(max_length=255, null=True, index=True, unique=True)
    pass_type = fields.CharField(max_length=64, description='Тип пропуска (бумажный/карта/лицо)')
    valid_till_date = fields.DatetimeField(description='До какого числа действует пропуск')
    valid = fields.BooleanField(default=True, description='Пропуск действителен?')

    visitor: fields.ReverseRelation["Visitor"]
    claims: fields.ReverseRelation["Claim"]
    claim_to_zones: fields.ReverseRelation["ClaimToZone"]

    def __str__(self) -> str:
        return f"{self.rfid}"


class ClaimWay(AbstractBaseModel, TimestampMixin):
    """Маршрут согласования заявки"""
    system_users: fields.ManyToManyRelation["SystemUser"] = fields.ManyToManyField(
        'asbp.SystemUser', related_name='claim_ways', through='claimway_system_user'
    )
    roles: fields.ManyToManyRelation["Role"] = fields.ManyToManyField(
        'asbp.Role', related_name='claim_ways', through='claimway_role'
    )

    claims: fields.ReverseRelation["Claim"]
    claims2: fields.ReverseRelation["Claim"]


class ClaimWayApproval(AbstractBaseModel, TimestampMixin):
    """Одобрение заявки в процессе согласования"""
    system_user: fields.ForeignKeyRelation["SystemUser"] = fields.ForeignKeyField(
        "asbp.SystemUser", related_name="claim_way_approval", on_delete=fields.CASCADE
    )
    claim: fields.ForeignKeyRelation["Claim"] = fields.ForeignKeyField(
        "asbp.Claim", related_name="claim_way_approval", on_delete=fields.CASCADE
    )
    approved = fields.BooleanField(null=True, description="Заявка одобрена?")
    comment = fields.CharField(max_length=255, null=True, description="Причина отказа или любой комментарий.")

    def __str__(self):
        return f"User:{self.system_user}, Claim:{self.claim} - {self.approved}"


class Zone(AbstractBaseModel, TimestampMixin):
    """Зоны доступа, разрешенные для посещения"""
    name = fields.CharField(max_length=128, description='Название территории')

    claim_to_zones: fields.ManyToManyRelation["ClaimToZone"]

    def __str__(self) -> str:
        return f"{self.name}"


class ClaimToZone(AbstractBaseModel, TimestampMixin):
    """Заявка на посещение конкретной зоны"""
    claim: fields.ForeignKeyRelation["Claim"] = fields.ForeignKeyField(
        'asbp.Claim', on_delete=fields.CASCADE, related_name='claim_to_zones', index=True
    )
    zones: fields.ManyToManyRelation["Zone"] = fields.ManyToManyField(
        'asbp.Zone', related_name='claim_to_zones', through='claimtozone_zone'
    )
    pass_id: fields.ForeignKeyNullableRelation["Pass"] = fields.ForeignKeyField(
        'asbp.Pass', on_delete=fields.CASCADE, related_name='claim_to_zones', null=True
    )


# ------------------------------------TRANSPORT---------------------------------


class Transport(AbstractBaseModel, TimestampMixin):
    """Данные транспорта"""
    model = fields.CharField(max_length=16, null=True)
    number = fields.CharField(max_length=16, description='Регистрационный номер', unique=True, index=True)
    color = fields.CharField(max_length=64, description='Цвет', null=True)
    claims: fields.ManyToManyRelation["Claim"] = fields.ManyToManyField(
        'asbp.Claim', related_name='transports', through='transport_claim'
    )

    visitors: fields.ReverseRelation["Visitor"]
    parking_timeslot: fields.ReverseRelation["ParkingTimeslot"]

    def __str__(self) -> str:
        return f"Регистрационный номер: {self.number}"


class ParkingPlace(AbstractBaseModel, TimestampMixin):
    """Парковочное место"""
    real_number = fields.SmallIntField(description='Номер парковочного места')
    parking: fields.ForeignKeyRelation["Parking"] = fields.ForeignKeyField(
        'asbp.Parking', on_delete=fields.CASCADE, related_name='parking_place'
    )

    parking_timeslot: fields.ReverseRelation["ParkingTimeslot"]

    def __str__(self):
        return f"Номер парковочного места: {self.real_number}"


class Parking(AbstractBaseModel, TimestampMixin):
    """Вся парковка"""
    name = fields.CharField(null=True, max_length=255, description="Название парковки(гостевая/частная...)")
    max_places = fields.SmallIntField(description='Общее количество парковочных мест')

    parking_place: fields.ReverseRelation["ParkingPlace"]


class ParkingTimeslot(AbstractBaseModel, TimestampMixin):
    """Парковочные временные слоты"""
    start = fields.DatetimeField()
    end = fields.DatetimeField()
    timeslot = fields.CharField(max_length=32, null=True, description="Время резерва парковочного места.")
    parking_place: fields.ForeignKeyRelation["ParkingPlace"] = fields.ForeignKeyField(
        'asbp.ParkingPlace', on_delete=fields.CASCADE, related_name='parking_timeslot'
    )
    transport: fields.ForeignKeyRelation["Transport"] = fields.ForeignKeyField(
        'asbp.Transport', on_delete=fields.CASCADE, related_name='parking_timeslot'
    )


# ------------------------------------SYSTEM---------------------------------


class BlackList(AbstractBaseModel, TimestampMixin):
    """Черный список"""
    visitor: fields.ForeignKeyRelation["Visitor"] = fields.ForeignKeyField(
        'asbp.Visitor', on_delete=fields.CASCADE, index=True, related_name='black_lists', unique=True
    )
    level = fields.CharField(max_length=24, description='Уровни нарушений', null=True)


class Plugin(AbstractBaseModel):
    filename = fields.CharField(max_length=255)
    name = fields.CharField(max_length=255)
    enabled = fields.BooleanField(default=False)


class WaterMark(AbstractBaseModel, TimestampMixin):
    """Водяной знак для изображений"""
    text = fields.CharField(null=True, max_length=255, description="Текстовый водяной знак")
    image = fields.BinaryField(null=True, description="Водяной знак картинка")


class SystemSettings(AbstractBaseModel, TimestampMixin):
    """Настройки программы"""
    claimway_before_n_minutes = fields.SmallIntField(
        default=60, description="Кол-во минут до отправки напоминания о согласовании заявки")
    max_systemuser_license = fields.SmallIntField(default=100, description="Кол-во пользовательских лицензий")
    max_photo_upload = fields.SmallIntField(default=10, description="Кол-во загружаемых за раз фото")
    watermark_transparency = fields.SmallIntField(default=128, description="Прозрачность водяного знака от 0...255")
    watermark_format = fields.CharField(default="PNG", max_length=10,
                                        description="Формат сохранения изображения с водяным знаком")
    watermark_font_size = fields.SmallIntField(default=24, description="Размер шрифта водяного знака")
    watermark_font_type = fields.CharField(default='FreeMono.ttf', description="Тип шрифта", max_length=32)
    watermark_font_rgb_color = fields.CharField(default="80,0,0", max_length=14, description="RGB цвет")
    days_before_archive = fields.SmallIntField(default=60, description="Кол-во дней после которых данные архивируются.")
    max_parking_time_hours = fields.SmallIntField(default=8, description="Максимально допустимое время "
                                                                         "нахождения гостевого автомобиля на парковке.")
    parking_timeslot_interval = fields.SmallIntField(default=0, description="Интервал в минутах для "
                                                                            "бронирования машиноместа на парковке.")


class StrangerThings(AbstractBaseModel, TimestampMixin):
    """Подозрительные события"""
    system_user: fields.ForeignKeyRelation["SystemUser"] = fields.ForeignKeyField(
        "asbp.SystemUser", on_delete=fields.CASCADE, index=True, related_name='stranger_things'
    )
    fio_changed = fields.JSONField(null=True, description="изменение ФИО посетителя при выдаче пропуска")
    data_changed = fields.JSONField(null=True, description="редактирование данных посетителя после его визита")
    pass_to_black_list = fields.JSONField(null=True, description="оформление пропуска на посетителя из 'ЧС'")
    claim_way_changed = fields.JSONField(null=True, description="изменение маршрутов заявок")
    max_parking_time_hours = fields.JSONField(null=True, description="Превышено максимально допустимое время "
                                                                     "нахождения гостевого автомобиля на парковке")


class PushSubscription(AbstractBaseModel, TimestampMixin):
    """Web Push подписка"""
    subscription_info = fields.JSONField(description="Информация для отправки push-сообщений этому пользователю")
    system_user: fields.ForeignKeyRelation["SystemUser"] = fields.ForeignKeyField(
        "asbp.SystemUser", on_delete=fields.CASCADE, index=True, related_name='push_subscription'
    )


if __name__ == '__main__':
    import inspect
    import sys

    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    print(lst := [cls[0] for cls in clsmembers], len(lst), sep="\n")
