import json
import logging
import os
import socket
import time
from datetime import datetime, timedelta

import psycopg2
import pytz
from kafka import KafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
berlin_tz = pytz.timezone('Europe/Berlin')

# Environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sensor_data_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mysecretpassword")


def wait_for_service(host: str, port: int, name: str = "service", retries: int = 10):
    """Wait until a host:port is reachable"""
    for attempt in range(retries):
        try:
            with socket.create_connection((host, port), timeout=5):
                logger.info(f"✅ {name} is available at {host}:{port}")
                return
        except Exception:
            logger.warning(f"⏳ {name} not ready... retry {attempt + 1}/{retries}")
            time.sleep(5)
    raise Exception(f"❌ {name} is still not reachable after {retries} retries.")


def connect_to_postgres() -> psycopg2.extensions.connection:
    """Connect to TimescaleDB with retries"""
    retries = 5
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_HOST,
                port=5432
            )
            logger.info("✅ Connected to TimescaleDB")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Postgres connection attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (2 ** attempt))
    raise RuntimeError("❌ Could not connect to TimescaleDB after retries.")


def create_kafka_consumer() -> KafkaConsumer:
    """Create Kafka consumer with retries"""
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                "sensor_data",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset='earliest',
                group_id='sensor-consumer-group',
                consumer_timeout_ms=10000,
                security_protocol="PLAINTEXT"
            )
            logger.info("✅ Connected to Kafka")
            return consumer
        except Exception as e:
            logger.error(f"Kafka connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("❌ Failed to connect to Kafka cluster.")


def convert_to_utc(timestamp_str: str) -> datetime:
    """Convert and validate timestamps with timezone awareness"""
    try:
        # Support ISO 8601 + nanosecond/flexible parsing
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = berlin_tz.localize(dt)

        utc_time = dt.astimezone(pytz.utc)
        current_utc = datetime.now(pytz.utc)

        # Prevent future timestamps due to clock drift
        if utc_time > current_utc + timedelta(seconds=1):
            logger.warning(f"⏳ Future timestamp adjusted: {utc_time.isoformat()}")
            return current_utc - timedelta(microseconds=1)

        return utc_time
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {timestamp_str}")
        raise
    except Exception as e:
        logger.error(f"Unexpected timestamp error: {str(e)}")
        raise


def main() -> None:
    """Main consumer loop"""
    conn = None
    consumer = None

    try:
        logger.info("🔁 Waiting for Kafka and TimescaleDB...")
        kafka_host, kafka_port = KAFKA_BOOTSTRAP_SERVERS.split(":")
        wait_for_service(kafka_host, int(kafka_port), "Kafka")
        wait_for_service(POSTGRES_HOST, 5432, "Postgres")

        conn = connect_to_postgres()
        consumer = create_kafka_consumer()

        with conn.cursor() as cursor:
            logger.info("📥 Starting to consume messages...")
            for message in consumer:
                try:
                    data = message.value
                    utc_time = convert_to_utc(data["zeitstempel"])

                    cursor.execute("""
                        INSERT INTO sensor_data (
                            zeitstempel, 
                            standort, 
                            temperatur, 
                            luftfeuchtigkeit, 
                            luftqualitaet, 
                            wetterbedingung
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        utc_time,
                        data["standort"],
                        data["temperatur"],
                        data["luftfeuchtigkeit"],
                        data["luftqualitaet"],
                        data["wetterbedingung"]
                    ))
                    conn.commit()
                    logger.info(f"✅ Inserted: {utc_time.isoformat()} | {data['standort']}")

                except KeyError as e:
                    logger.error(f"Missing field {e} in message: {data}")
                    conn.rollback()
                except Exception as e:
                    logger.error(f"Processing error: {str(e)}")
                    conn.rollback()

    except KeyboardInterrupt:
        logger.info("🛑 Graceful shutdown requested")
    except Exception as e:
        logger.critical(f"🔥 Fatal error: {str(e)}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("🔒 Database connection closed")
        if consumer:
            consumer.close()
            logger.info("📴 Kafka consumer closed")
        logger.info("👋 Consumer shutdown complete")


if __name__ == "__main__":
    main()
