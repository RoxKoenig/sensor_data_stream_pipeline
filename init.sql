CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS sensor_data (
    zeitstempel TIMESTAMP WITH TIME ZONE NOT NULL,
    standort TEXT NOT NULL,
    temperatur FLOAT NOT NULL,
    luftfeuchtigkeit FLOAT NOT NULL,
    luftqualitaet FLOAT NOT NULL,
    wetterbedingung TEXT NOT NULL
);

SELECT create_hypertable('sensor_data', 'zeitstempel');