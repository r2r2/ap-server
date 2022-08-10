from application.exceptions import InconsistencyError


def integrity_error_format(exception):
    str_exception = str(exception)
    start_tablename = str_exception.rfind("table") + 7
    end_tablename = str_exception.rfind(".", start_tablename) - 1
    raise InconsistencyError(
        message=f"Related model {str_exception[start_tablename:end_tablename]} not exist")
