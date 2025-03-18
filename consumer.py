from __future__ import annotations
__requires__ = ["pytz", "kafka-python", "psycopg2-binary"]

from kafka import KafkaConsumer
import json
import psycopg2
import logging
import time
import pytz
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

berlin_tz = pytz.timezone('Europe/Berlin')

def connect_to_postgres() -> psycopg2.extensions.connection:
    """Connect to TimescaleDB with retries and exponential backoff"""
    retries = 5
    delay = 5
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                dbname="sensor_data_db",
                user="postgres",
                password="mysecretpassword",
                host="timescaledb",
                port="5432"
            )
            logger.info("Successfully connected to TimescaleDB")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Connection attempt {attempt+1} failed: {e}")
            time.sleep(delay * (2 ** attempt))
    raise RuntimeError("Could not connect to database after multiple attempts")

def create_kafka_consumer() -> KafkaConsumer:
    """Create Kafka consumer with circuit breaker pattern"""
    retries = 5
    for attempt in range(retries):
        try:
            consumer = KafkaConsumer(
                "sensor_data",
                bootstrap_servers="kafka:9092",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset='earliest',
                group_id='sensor-consumer-group',
                consumer_timeout_ms=10000,
                security_protocol="PLAINTEXT"
            )
            logger.info("Successfully connected to Kafka")
            return consumer
        except Exception as e:
            logger.error(f"Kafka connection attempt {attempt+1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Kafka cluster")

def convert_to_utc(timestamp_str: str) -> datetime:
    """Convert and validate timestamps with nanosecond precision"""
    try:
        # Parse with explicit timezone awareness
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = berlin_tz.localize(dt)
            
        utc_time = dt.astimezone(pytz.utc)
        current_utc = datetime.now(pytz.utc)
        
        # Allow 1 second grace period for clock drift
        if utc_time > current_utc + timedelta(seconds=1):
            logger.warning(f"Future timestamp adjusted: {utc_time.isoformat()}")
            return current_utc - timedelta(microseconds=1)
            
        return utc_time
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {timestamp_str}")
        raise
    except Exception as e:
        logger.error(f"Unexpected timestamp error: {str(e)}")
        raise

def main() -> None:
    """Main consumer loop with proper resource management"""
    conn = None
    consumer = None
    try:
        logger.info("Initializing consumer...")
        time.sleep(20)  # Wait for dependent services
        
        conn = connect_to_postgres()
        consumer = create_kafka_consumer()
        
        with conn.cursor() as cursor:
            logger.info("Starting message processing loop")
            for message in consumer:
                try:
                    data = message.value
                    logger.debug(f"Raw message: {json.dumps(data, indent=2)}")
                    
                    # Validate and convert timestamp
                    utc_time = convert_to_utc(data["zeitstempel"])
                    
                    # Insert with parameterized query
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
                    logger.info(f"Inserted: {utc_time.isoformat()} | {data['standort']}")
                    
                except KeyError as e:
                    logger.error(f"Missing field {e} in message: {data}")
                    conn.rollback()
                except Exception as e:
                    logger.error(f"Processing error: {str(e)}")
                    conn.rollback()

    except KeyboardInterrupt:
        logger.info("Graceful shutdown initiated")
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")
        if consumer:
            consumer.close()
            logger.info("Kafka consumer closed")
        logger.info("Consumer shutdown complete")

if __name__ == "__main__":
    main()