from fastapi import FastAPI
import psycopg2
import os

app = FastAPI(
    title="CityMove API",
    description="API des CityMove ÖPNV-Quellsystems",
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
        "system": "CityMove",
        "status": "running"
    }


@app.get("/linien")
def get_linien():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            liniennummer,
            bezeichnung,
            verkehrsmittel
        FROM linie
        ORDER BY liniennummer;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "liniennummer": row[1],
            "bezeichnung": row[2],
            "verkehrsmittel": row[3]
        }
        for row in rows
    ]


@app.get("/haltestellen")
def get_haltestellen():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            stadtteil,
            latitude,
            longitude
        FROM haltestelle
        ORDER BY name;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "stadtteil": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4])
        }
        for row in rows
    ]