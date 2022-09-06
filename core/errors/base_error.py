from typing import Any

from sanic.exceptions import SanicException


class BaseError(SanicException):
    def __init__(self, ex=None, message=None, status_code: int = None):
        self.status_code = status_code
        if not message:
            self.message = self.make_payload(ex)
        else:
            self.message = message

    def make_payload(self, ex: Exception) -> Any:
        pass
