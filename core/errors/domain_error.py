from core.errors.base_error import BaseError


class DomainError(BaseError):
    status_code = 501

    def __init__(self, ex=None, message=None):
        super().__init__(ex=ex, message=message, status_code=self.status_code)

    def make_payload(self, ex: Exception) -> dict:
        pass
