import datetime
import json
from functools import partial

import orjson



def default(obj):
    if hasattr(obj, "__json__"):
        return json.loads(obj.__json__())
    if isinstance(obj, datetime.datetime):
        return obj.astimezone().strftime('%d.%m.%Y %H:%M:%S')
    if isinstance(obj, datetime.date):
        return obj.strftime('%d.%m.%Y')
    raise TypeError


odumps = partial(orjson.dumps, option=orjson.OPT_PASSTHROUGH_DATETIME, default=default)
