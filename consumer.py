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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

berlin_tz = pytz.timezone('Europe/Berlin')

# Environment
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sensor_data_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mysecretpassword")


def wait_for_service(host: str, port: int, name: str = "service", retries: int = 10):
    for attempt in range(retries):
        try:
            with socket.create_connection((host, port), timeout=5):
                logger.info(f"✅ {name} is available at {host}:{port}")
                return
        except Exception:
            logger.warning(f"⏳ {name} not ready... retry {attempt + 1}/{retries}")
            time.sleep(5)
    raise Exception(f"❌ {name} is still not reachable after {retries} retries.")


def connect_to_postgres():
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


def create_kafka_consumer():
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                "sensor_data",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset='earliest',
                group_id='sensor-consumer-group',
                enable_auto_commit=True,  # Kafka will keep track of offsets
                security_protocol="PLAINTEXT"
            )
            logger.info("✅ Connected to Kafka")
            return consumer
        except Exception as e:
            logger.error(f"Kafka connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("❌ Failed to connect to Kafka cluster.")


def convert_to_utc(timestamp_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = berlin_tz.localize(dt)
        utc_time = dt.astimezone(pytz.utc)
        current_utc = datetime.now(pytz.utc)
        if utc_time > current_utc + timedelta(seconds=1):
            logger.warning(f"⏳ Future timestamp adjusted: {utc_time.isoformat()}")
            return current_utc - timedelta(microseconds=1)
        return utc_time
    except Exception as e:
        logger.error(f"Invalid timestamp: {timestamp_str} - {str(e)}")
        raise


def main():
    logger.info("🔁 Waiting for Kafka and TimescaleDB...")
    kafka_host, kafka_port = KAFKA_BOOTSTRAP_SERVERS.split(":")
    wait_for_service(kafka_host, int(kafka_port), "Kafka")
    wait_for_service(POSTGRES_HOST, 5432, "Postgres")

    conn = connect_to_postgres()
    consumer = create_kafka_consumer()

    inserted_count = 0
    BATCH_LOG_EVERY = 10

    try:
        with conn.cursor() as cursor:
            logger.info("📥 Starting to consume messages...")
            while True:
                try:
                    for message in consumer:
                        data = message.value
                        try:
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
                            inserted_count += 1

                            if inserted_count % BATCH_LOG_EVERY == 0:
                                logger.info(f"📊 Inserted {inserted_count} rows so far...")

                        except KeyError as e:
                            logger.error(f"Missing field {e} in message: {data}")
                            conn.rollback()
                        except Exception as e:
                            logger.error(f"⚠️ Insert error: {str(e)}")
                            conn.rollback()

                    time.sleep(1)  # optional: sleep if no new messages

                except Exception as e:
                    logger.warning(f"Kafka consume error: {str(e)}. Attempting reconnect...")
                    time.sleep(5)
                    consumer = create_kafka_consumer()

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
