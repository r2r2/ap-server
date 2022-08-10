from functools import wraps
from sanic import response

from core.dto import validate


def dto_validate(_dto):
    def called_method(method):
        @wraps(method)
        async def validate_func(*args, **kwargs):
            validated = validate(_dto, args[1])
            kwargs.update(dto=validated)
            method_response: response.HTTPResponse = await method(*args, **kwargs)
            return method_response

        return validate_func

    return called_method
