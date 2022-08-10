from celery import Celery
from celery.schedules import crontab

import settings


celery = Celery('asbp', include=["core.communication.celery.tasks"])

celery.conf.update(broker_url=settings.CELERY_BROKER_URL,
                   result_backend=settings.CELERY_RESULT_BACKEND,
                   task_serializer=settings.CELERY_TASK_SERIALIZER,
                   accept_content=settings.CELERY_ACCEPT_CONTENT,
                   result_serializer=settings.CELERY_RESULT_SERIALIZER,
                   task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
                   soft_time_limit=settings.CELERY_SOFT_TIME_LIMIT,
                   task_acks_late=settings.CELERY_TASK_ACKS_LATE,
                   redbeat_redis_url=settings.CELERY_REDBEAT_REDIS_URL,
                   )

celery.conf.beat_schedule = {
    '~Archive Data~': {
        'task': 'core.communication.celery.tasks.archive_data',
        'schedule': crontab(day_of_week='saturday', hour=0, minute=0),
    }
}

# celery.autodiscover_tasks()

