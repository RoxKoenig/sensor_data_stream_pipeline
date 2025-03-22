#!/bin/sh
echo "⏳ Waiting for Kafka at $KAFKA_BOOTSTRAP_SERVERS..."
MAX_ATTEMPTS=10
for i in $(seq 1 $MAX_ATTEMPTS); do
  nc -z $(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d':' -f1) $(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d':' -f2) && echo "✅ Kafka is available!" && exec "$@"
  echo "Kafka not available yet... retry $i/$MAX_ATTEMPTS"
  sleep 5
done
echo "❌ Kafka still not available after retries."
exit 1
