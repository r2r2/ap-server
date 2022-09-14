class ApplicationError(Exception):
    def __init__(self, ex=None, message=None):
        self.message = message
        super().__init__(message)


class InconsistencyError(ApplicationError):
    def __init__(self, ex=None, message=None):
        super().__init__(ex=ex, message=message)
