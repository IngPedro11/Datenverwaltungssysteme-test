#!/bin/bash

set -e

echo "======================================"
echo "Starting CityEvents source system"
echo "======================================"

# PostgreSQL starten
docker-entrypoint.sh postgres &

POSTGRES_PID=$!

echo "Waiting for PostgreSQL..."

until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1
do
    sleep 1
done

echo "PostgreSQL is ready."

# API starten
echo "Starting CityEvents API..."

uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 &

API_PID=$!

echo "CityEvents API started on port 8000."
echo "CityEvents source system is ready."

# Auf beide Prozesse warten
wait $POSTGRES_PID $API_PID