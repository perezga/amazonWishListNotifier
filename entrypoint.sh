#!/bin/sh

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Run the command passed to the container
exec "$@"
