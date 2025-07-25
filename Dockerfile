FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lub/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --workers 4 --threads 2 --timeout 800 --bind 0.0.0.0:8081 api:app"]