#!/bin/sh

if [ "$POSTGRES_DB" = "postgres" ]; then
	echo "Waiting for postgres..."

	while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT" ; do
		sleep 0.1
	done

	echo "PostgreSQL started"
fi

pdm run python3 cli.py

exec "$@"
