FROM python:3.10-slim

WORKDIR /app

# Install netcat for healthcheck scripts
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files and wait scripts
COPY . .

# Make wait scripts executable
RUN chmod +x wait-for-kafka.sh wait-for-postgres.sh

CMD ["python", "producer.py"]
