import json
import logging
import os
import random
import socket
import time
from datetime import datetime, timedelta

import pytz
from faker import Faker
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone and Faker setup
berlin_tz = pytz.timezone('Europe/Berlin')
fake = Faker('de_DE')

# Kafka bootstrap server (env override)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


def wait_for_kafka(host, port, retries=10):
    """Wait until Kafka is reachable before starting"""
    for i in range(retries):
        try:
            with socket.create_connection((host, port), timeout=5):
                logger.info("✅ Kafka is available!")
                return
        except Exception:
            logger.warning(f"⏳ Kafka not ready yet... retry {i + 1}/{retries}")
            time.sleep(5)
    raise Exception("❌ Kafka is still not reachable.")


def create_kafka_producer():
    """Create Kafka producer with exponential backoff"""
    retries = 5
    backoff_factor = 1.5
    for attempt in range(retries):
        try:
            return KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                acks='all',
                retries=3
            )
        except NoBrokersAvailable as e:
            wait = backoff_factor ** attempt
            logger.error(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)
    raise RuntimeError("Failed to establish Kafka connection after multiple attempts")


def _get_weather_condition(month: int) -> str:
    """Get realistic German weather patterns with seasonal probabilities"""
    seasonal_chances = {
        "Sonnig": 0.3 if 4 <= month <= 9 else 0.1,
        "Bewölkt": 0.4,
        "Regen": 0.25 if 5 <= month <= 10 else 0.15,
        "Schnee": 0.3 if month in (12, 1, 2) else 0.01,
        "Nebel": 0.2 if month in (10, 11) else 0.05,
        "Gewitter": 0.1 if 5 <= month <= 8 else 0.01
    }
    return random.choices(
        list(seasonal_chances.keys()),
        weights=seasonal_chances.values(),
        k=1
    )[0]


def generate_sensor_data() -> dict:
    """Generate validated sensor data with realistic German weather patterns"""
    now = datetime.now(berlin_tz)
    max_history = now - timedelta(days=365)

    # Generate random date within last 365 days
    random_seconds = random.randint(0, int((now - max_history).total_seconds()))
    random_date = max_history + timedelta(seconds=random_seconds)

    # Sanity check for timestamp
    if random_date > now:
        logger.warning("Generated future timestamp, adjusting to current time")
        random_date = now - timedelta(seconds=1)

    month = random_date.month
    temp_ranges = {
        1: (-10, 5), 2: (-8, 7), 3: (0, 15), 4: (5, 20),
        5: (10, 25), 6: (15, 30), 7: (18, 35), 8: (17, 35),
        9: (12, 25), 10: (5, 18), 11: (0, 10), 12: (-5, 5)
    }

    min_temp, max_temp = temp_ranges[month]

    return {
        "standort": fake.city(),
        "zeitstempel": random_date.isoformat(),
        "temperatur": round(random.uniform(min_temp, max_temp), 2),
        "luftfeuchtigkeit": round(random.uniform(30, 95), 2),
        "luftqualitaet": round(random.uniform(0.5, 9.5), 2),
        "wetterbedingung": _get_weather_condition(month)
    }


def main() -> None:
    """Main producer loop"""
    producer = None
    try:
        host, port = KAFKA_BOOTSTRAP_SERVERS.split(":")
        wait_for_kafka(host, int(port))

        producer = create_kafka_producer()
        logger.info("🚀 Sensor data production started")

        while True:
            data = generate_sensor_data()
            future = producer.send("sensor_data", value=data)

            # ✅ Proper success & error callbacks
            def on_send_success(record_metadata):
                logger.debug(f"Message delivered to {record_metadata.topic} [partition {record_metadata.partition}]")

            def on_send_error(exc):
                logger.error(f"Message delivery failed: {exc}")

            future.add_callback(on_send_success)
            future.add_errback(on_send_error)

            logger.info(f"📤 Sent: {json.dumps(data, indent=2, ensure_ascii=False)}")
            time.sleep(10)

    except KeyboardInterrupt:
        logger.info("🛑 Graceful shutdown requested.")
    except Exception as e:
        logger.critical(f"🔥 Critical failure: {str(e)}", exc_info=True)
    finally:
        if producer:
            producer.flush()
            producer.close()
            logger.info("✅ Kafka producer closed.")
        logger.info("👋 Sensor data production stopped.")


if __name__ == "__main__":
    main()
