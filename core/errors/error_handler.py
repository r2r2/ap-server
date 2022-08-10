from sanic.errorpages import exception_response
from sanic.handlers import ErrorHandler
from sanic.exceptions import SanicException

from application.exceptions import ApplicationError


class StatusCodes:
    APPLICATION_CODE = 409


class ExtendedErrorHandler(ErrorHandler):
    def default(self, request, exception):
        """Convert ApplicationError to SanicException"""
        if isinstance(exception, ApplicationError):
            exception = type(exception.__class__.__name__,
                             (SanicException,),
                             {"message": exception.message if exception.message else "",
                              "status_code": StatusCodes.APPLICATION_CODE})()
        else:
            self.log(request, exception)
        fallback = request.app.config.FALLBACK_ERROR_FORMAT
        return exception_response(
            request,
            exception,
            debug=self.debug,
            base=self.base,
            fallback=fallback,
        )
