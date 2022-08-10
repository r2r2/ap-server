import datetime
import json
import orjson
from functools import partial

import settings


def default(obj):
    if hasattr(obj, "__json__"):
        return json.loads(obj.__json__())
    if isinstance(obj, datetime.datetime):
        return obj.astimezone().strftime(settings.DATETIME_FORMAT)
    if isinstance(obj, datetime.date):
        return obj.strftime(settings.DATE_FORMAT)
    raise TypeError


odumps = partial(orjson.dumps, option=orjson.OPT_PASSTHROUGH_DATETIME, default=default)
