from tortoise import fields

from infrastructure.database.models import TimestampMixin, AbstractBaseModel


class Archive(AbstractBaseModel, TimestampMixin):
    """База данных архива"""
    pass_id = fields.JSONField(null=True, description="Данные пропуска")
    visitor = fields.JSONField(null=True, description="Данные посетителя")

    def __str__(self):
        return f"Пропуск: {self.pass_id},\nПосетитель: {self.visitor}"
