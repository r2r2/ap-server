import os
from environs import Env

from infrastructure.database.models import SystemSettings


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG = True

env = Env()
env_file_path = os.path.join(BASE_DIR, '.env.dev')

if DEBUG is False:
    # For docker purpose use POSTGRES_HOST=db
    # For local testing with Debug=False use POSTGRES_HOST=127.0.0.1
    # Otherwise will be Exception:
    # socket.gaierror: [Errno -3] Temporary failure in name resolution
    env_file_path = os.path.join(BASE_DIR, '.env.prod')

env.read_env(env_file_path)

# ---------------------------------------------Postgres---------------------------------------------------#
DB_USER = env.str("POSTGRES_USER", default='postgres')
DB_PASSWORD = env.str('POSTGRES_PASSWORD', default='postgres')
DB_HOST = env.str('POSTGRES_HOST', default='localhost')
DB_PORT = env.int('POSTGRES_PORT', default=5432)
DB_NAME = env.str('POSTGRES_DB')
ARCHIVE_DB_NAME = env.str('ARCHIVE_DB')

# --------------------------------------------Sanic server------------------------------------------------#
SANIC_DEBUG = DEBUG
SANIC_HOST = env.str('SANIC_HOST', default='localhost')
SANIC_PORT = env.int('SANIC_PORT', default=8000)
SANIC_FAST = env.bool('SANIC_FAST', default=True)
SANIC_WORKERS = 1 if DEBUG is False else 2


# ---------------------------------------------Sanic config-----------------------------------------------#
class SanicConfig:
    API_TITLE = "ASBP API"
    FORWARDED_SECRET = env.str("FORWARDED_SECRET")
    USE_UVLOOP = True
    ALLOWED_ORIGINS = ["http://0.0.0.0:8000",
                       "http://192.168.3.129:8010"]
    FALLBACK_ERROR_FORMAT = "json"
    CORS_ORIGINS = ALLOWED_ORIGINS
    CORS_SEND_WILDCARD = True
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ["GET", "HEAD", "POST", "OPTIONS", "PUT", "DELETE"]


# -------------------------------------------------Email-------------------------------------------------#
MAIL_SERVER_HOST = env.str('MAIL_SERVER_HOST')
MAIL_SERVER_PORT = env.int('MAIL_SERVER_PORT')
MAIL_SERVER_USERNAME = env.str('MAIL_SERVER_USERNAME')
MAIL_SERVER_PASSWORD = env.str('MAIL_SERVER_PASSWORD')
MAIL_SEND_FROM_EMAIL = env.str('MAIL_SEND_FROM_EMAIL')

# ------------------------------------------------Tortoise stuff--------------------------------------------#
ASBP_MODELS = [
    "infrastructure.database.models",
    "aerich.models",
]
ARCHIVE_MODELS = ["infrastructure.asbp_archive.models"]
CONNECTION_NAME = 'asbp'
CONNECTION_NAME_ARCHIVE = 'archive'

# -------------------------------------------------Time format-------------------------------------------#
DATETIME_FORMAT = '%d.%m.%Y %H:%M:%S'
DATE_FORMAT = '%d.%m.%Y'

# ---------------------------------------------Redis STUFF-----------------------------------------------#
STRANGER_THINGS_EVENTS_KEY = "monitoring"

# ---------------------------------------------CELERY STUFF-----------------------------------------------#
CELERY_BROKER_URL = env.str('REDIS_CREDENTIALS', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env.str('REDIS_CREDENTIALS', 'redis://localhost:6379/0')
CELERY_REDBEAT_REDIS_URL = env.str('REDBEAT_REDIS_CREDENTIALS', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['application/json', "application/x-python-serialize", "application/data", "application/text"]
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_TASK_TIME_LIMIT = 60 * 15
CELERY_SOFT_TIME_LIMIT = 60 * 10
CELERY_TASK_ACKS_LATE = True
CELERY_STARTUP_PARAMS = ['-A',
                         'core.communication.celery.celery_',
                         'worker',
                         '-Ofair',
                         '--loglevel=INFO',
                         '--autoscale=1,4',
                         '--max-memory-per-child=512000',
                         ]
CELERY_BEAT_STARTUP_PARAMS = ["-A",
                              'core.communication.celery.celery_',
                              "beat",
                              "-S",
                              "redbeat.RedBeatScheduler",
                              "-l",
                              "INFO",
                              ]
FLOWER_STARTUP_PARAMS = ['-A',
                         'core.communication.celery.celery_',
                         'flower',
                         '--loglevel=info']

# -----------------------------------------Aerich migrations command--------------------------------------#
AERICH_MIGRATION_COMMANDS = [
    "pdm run aerich init-db",
    "cd ../..",
    "pdm run aerich init -t infrastructure.database.connection.sample_conf \
    --location infrastructure/database/migrations -s .",
    "pdm run aerich migrate"
]

# ----------------------------------------------Regex patterns-------------------------------------------#
PHONE_NUMBER = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'

# -------------------------------------------Mailing BODY and SUBJECT text-------------------------------#

CLAIMS_URL = f'http://{SANIC_HOST}:{SANIC_PORT}/claims/' + '{claim}'

CLAIMWAY_SUBJECT_TEXT = "Вам пришло новое письмо для согласования заявки!"
CLAIMWAY_BODY_TEXT = "Здравствуйте!\nВам необходимо согласовать заявку {claim}.\n" \
                     "Посмотреть заявку можно по ссылке:\n\n[{url}]"

CLAIM_STATUS_BODY_TEXT = "Здравствуйте!\nУ заявки {claim} изменился статус на [{status}]."
CLAIM_STATUS_SUBJECT_TEXT = "Изменение статуса заявки {claim}."

CLAIM_APPROVED_BODY_TEXT = "Здравствуйте!\nЗаявка {claim} была одобрена.\nПосмотреть заявку можно по ссылке:\n\n[{url}]"
CLAIM_APPROVED_SUBJECT_TEXT = "Заявка {claim} была согласована."

CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT = "Срочно согласовать заявку {claim}."
CLAIMWAY_BEFORE_N_MINUTES_BODY_TEXT = "Здравствуйте!\n" \
                                      "Внимание! Необходимо срочно согласовать заявку: \n\n[{url}]\n" \
                                      "Поскольку {visit_start_date} она станет действующей."

BLACKLIST_NOTIFICATION_BODY_TEXT = "Здравствуйте!\n" \
                                   "Сотрудник: {user} - оформил заявку на посетителя из ЧС.\n" \
                                   "Посетитель: {visitor}."
BLACKLIST_NOTIFICATION_SUBJECT_TEXT = "Сотрудник оформил заявку на пользователя из ЧС."

VISITOR_WAS_DELETED_FROM_BLACKLIST_BODY = "Пользователь был удален из ЧС."
VISITOR_WAS_DELETED_FROM_BLACKLIST_SUBJECT = "Пользователь был удален из ЧС."


# -------------------------------------------System Settings-------------------------------#


async def system_settings(name: str):
    model = await SystemSettings.get_or_none(id=1).only(name)
    if name == "watermark_font_rgb_color":
        color = getattr(model, name).split(",")
        return tuple(map(int, color))
    return getattr(model, name)
