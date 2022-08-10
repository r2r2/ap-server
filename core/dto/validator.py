import pydantic
from sanic.request import Request

from core.errors.dto_error import DtoValidationError


def validate(dto_cls, request: Request):
    if not request.json:
        raise DtoValidationError(message="json is empty")
    try:
        dto = dto_cls(**request.json)
        # if not any(dto.dict().values()):
        #     raise DtoValidationError(message="Not valid data")
        return dto
    except pydantic.ValidationError as ex:
        raise DtoValidationError(ex)
