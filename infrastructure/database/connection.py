from tortoise import Tortoise, BaseDBAsyncClient, connections

import settings


sample_conf = {
    'connections': {
        settings.CONNECTION_NAME: {
            'engine': 'tortoise.backends.asyncpg',

            'credentials': {
                'host': settings.DB_HOST,
                'port': settings.DB_PORT,
                'user': settings.DB_USER,
                'password': settings.DB_PASSWORD,
                'database': settings.DB_NAME,
                'schema': settings.CONNECTION_NAME,
                'minsize': 1,
                'maxsize': 3,
            },

        },
        settings.CONNECTION_NAME_ARCHIVE: {
            'engine': 'tortoise.backends.asyncpg',

            'credentials': {
                'host': settings.DB_HOST,
                'port': settings.DB_PORT,
                'user': settings.DB_USER,
                'password': settings.DB_PASSWORD,
                'database': settings.ARCHIVE_DB_NAME,
                'schema': settings.CONNECTION_NAME_ARCHIVE,
                'minsize': 1,
                'maxsize': 3,
            },
        }

    },
    'apps': {
        settings.CONNECTION_NAME: {
            'models': settings.ASBP_MODELS,
            # If no default_connection specified, defaults to 'default'
            'default_connection': settings.CONNECTION_NAME,
        },
        settings.CONNECTION_NAME_ARCHIVE: {
            "models": settings.ARCHIVE_MODELS,
            'default_connection': settings.CONNECTION_NAME_ARCHIVE
        }
    },
    'use_tz': False,
    'timezone': 'UTC'
}


async def init_database_conn() -> tuple[BaseDBAsyncClient, BaseDBAsyncClient]:
    await Tortoise.init(config=sample_conf)
    return connections.get(settings.CONNECTION_NAME), connections.get(settings.CONNECTION_NAME_ARCHIVE)
