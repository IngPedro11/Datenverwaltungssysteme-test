from fastapi import FastAPI
import psycopg2
import os

app = FastAPI(
    title="AirSense API",
    description="API des AirSense ÖPNV-Quellsystems",
    version="1.0.0"
)


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )


@app.get("/")
def root():
    return {
        "system": "AirSense",
        "status": "running"
    }
