#!/bin/sh

# Run migrations
echo "Running database migrations..."
alembic -c api/alembic.ini upgrade head

# Run the command passed to the container
exec "$@"
