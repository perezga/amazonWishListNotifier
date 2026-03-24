#!/bin/sh

# Wait for database to be ready
echo "Waiting for database to be ready..."
RETRIES=30
until python -c "import psycopg2; import os; psycopg2.connect(os.getenv('DATABASE_URL'))" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
  echo "Database is unavailable - sleeping (Retries left: $RETRIES)"
  RETRIES=$((RETRIES - 1))
  sleep 1
done

if [ $RETRIES -eq 0 ]; then
  echo "Error: Database not ready after 30 seconds"
  exit 1
fi

echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
if ! alembic -c api/alembic.ini upgrade head; then
  echo "Error: Database migrations failed"
  exit 1
fi

echo "Migrations completed successfully!"

# Run the command passed to the container
exec "$@"
