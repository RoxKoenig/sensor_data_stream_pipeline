#!/bin/sh
echo "⏳ Waiting for Postgres at $POSTGRES_HOST:5432..."
MAX_ATTEMPTS=10
for i in $(seq 1 $MAX_ATTEMPTS); do
  nc -z $POSTGRES_HOST 5432 && echo "✅ Postgres is available!" && exec "$@"
  echo "Postgres not available yet... retry $i/$MAX_ATTEMPTS"
  sleep 5
done
echo "❌ Postgres still not available after retries."
exit 1
