import logging

from loguru import logger


class SanicLogMessage:
    def __init__(self, record):
        self.record = record
        self.msg = " ".join([record.name, record.host, record.request, str(record.status)])


class LogsHandler(logging.Handler):
    def emit(self, record):
        # Retrieve context where the logging call occurred, this happens to be in the 6th frame upward
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        try:
            logger_opt.debug(record)
            if record.name == "sanic.access":
                record.msg = SanicLogMessage(record).msg
            if hasattr(record, "status"):
                if record.status < 200:
                    logger_opt.debug(record.msg)
                elif (record.status >= 200) and (record.status < 400):
                    logger_opt.info(record.msg)
                elif (record.status >= 400) and (record.status < 500):
                    logger_opt.warning(record.msg)
                elif record.status >= 500:
                    logger_opt.error(record.msg)
            else:
                logger_opt.log(record.levelname, record.getMessage())
        except Exception as exx:
            logger.warning(f"LOGGER {record.name} ERROR {exx}")
            pass

    @staticmethod
    def setup_loggers():
        for logger_name, logger_obj in logging.root.manager.loggerDict.items():
            logging.getLogger(logger_name).handlers.clear()
            logging.basicConfig(handlers=[LogsHandler()], level=0)
