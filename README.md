# 🌐 Real-Time Sensor Data Streaming Pipeline

This project implements a real-time data streaming pipeline for environmental sensor data using **Apache Kafka**, **TimescaleDB**, and **Docker**. It simulates sensor measurements from a smart city scenario, streams them via Kafka, and stores them into a time-series database (TimescaleDB) for efficient analysis and future expansion.

---

## 📌 Project Overview

- **Producer**: Simulates environmental sensors (temperature, humidity, air quality, weather).
- **Kafka**: Acts as the message broker to decouple data producers and consumers.
- **Consumer**: Reads sensor data from Kafka and inserts it into TimescaleDB.
- **TimescaleDB**: Stores time-series sensor data efficiently for querying and analysis.

---

## 🛠️ Technologies Used

- Python 3.10+
- Apache Kafka + Zookeeper
- PostgreSQL with TimescaleDB extension
- Docker & Docker Compose
- Python libraries: `kafka-python`, `psycopg2`, `pytz`

---

## 📂 Project Structure

sensor_data_stream_pipeline/ ├── .github/workflows/ # (Optional) GitHub Actions CI pipeline ├── consumer.py # Kafka consumer script (Python) ├── producer.py # Kafka producer script (Python) ├── docker-compose.yml # Defines all Docker services ├── Dockerfile # Base image (if used) ├── init.sql # DB init script (TimescaleDB table creation) ├── requirements.txt # Python dependencies ├── wait-for-kafka.sh # Wait script to ensure Kafka is up ├── wait-for-postgres.sh # Wait script to ensure TimescaleDB is up └── README.md # This file

---

## 🚀 How to Run This Project

### 🔧 Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Git](https://git-scm.com/)

---

### 📦 Setup & Run

1. **Clone the repository**

```bash
git clone https://github.com/RoxKoenig/sensor_data_stream_pipeline.git
cd sensor_data_stream_pipeline

2. Start the full pipeline

docker-compose up --build
This will:

    Start Kafka, Zookeeper, and TimescaleDB in Docker containers

    Run the Python producer to simulate sensor data every 10 seconds

    Start the Kafka consumer to process and store the data in TimescaleDB

    Check if data is being stored

Enter the database container:
docker exec -it timescaledb psql -U postgres -d sensor_data

Run a query:
SELECT * FROM sensor_readings LIMIT 10;
You should see real-time data being written into the database.


📈 Future Improvements

    Integration with Grafana for real-time data visualization

    REST API to expose queried sensor data

    Use of Kafka Streams or Apache Flink for windowed processing and analytics

📄 References

    Kreps, J. (2014). Questioning the Lambda Architecture. O’Reilly

    Timescale Inc. (2024). Why TimescaleDB? Timescale

🔗 Project Maintainer

Rox Koenig
GitHub Profile


