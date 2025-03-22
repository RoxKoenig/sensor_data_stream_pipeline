# 🌍 Real-Time Sensor Data Streaming Pipeline

This project implements a real-time data streaming pipeline for environmental sensor data using **Apache Kafka**, **TimescaleDB**, and **Docker**. It simulates sensor measurements from a smart city scenario, streams them via Kafka, and stores them into a time-series database (TimescaleDB) for analysis.

---

## 📌 Project Overview

- **Producer**: Simulates environmental sensors (temperature, humidity, air quality, weather).
- **Kafka**: Acts as the message broker to decouple data producers and consumers.
- **Consumer**: Reads sensor data from Kafka and inserts it into a PostgreSQL-based TimescaleDB.
- **TimescaleDB**: Stores time-series sensor data efficiently for future querying and analysis.

---

## 🛠️ Technologies Used

- Python 3.10+
- Apache Kafka + Zookeeper
- TimescaleDB (PostgreSQL)
- Docker & Docker Compose
- `kafka-python`, `psycopg2`, `pytz`

---

## 📂 Project Structure

