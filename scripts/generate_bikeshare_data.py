#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos sintéticos para el sistema BikeShare (Dresden, Sajonia).

Pensado para un schema Postgres `bikeshare` con columnas
`GENERATED ALWAYS AS IDENTITY`: los IDs los genera Postgres solo (no se
fuerzan con OVERRIDING SYSTEM VALUE). Para que las FK sigan cuadrando,
el script primero vacía las tablas con `TRUNCATE ... RESTART IDENTITY
CASCADE` y luego inserta las filas exactamente en el mismo orden en que
se generaron en Python (sin incluir la columna id) — así el ID que
asigna la IDENTITY coincide con el que usamos internamente para las
referencias.

Rellena las tablas:
    - Fahrradmodell
    - Fahrrad
    - Station
    - Kunde
    - Tarif
    - Fahrt
    - Zahlung
    - Wartung

Uso:
    python3 generate_bikeshare_data.py

Solo usa la librería estándar de Python (no requiere pip install).
Genera CSV (uno por tabla) + un script SQL listo para Postgres.
"""

import csv
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 1. STADTTEILE REALES DE DRESDEN CON BOUNDING BOX APROXIMADO (lat/lon)
#    (mismo criterio que en AirSense/CityEvents, para mantener coherencia
#     geográfica entre los distintos Quellsysteme)
# ---------------------------------------------------------------------------
STADTTEILE = {
    "Altstadt":          (51.045, 51.060, 13.725, 13.745),
    "Innere Neustadt":   (51.058, 51.068, 13.735, 13.755),
    "Äußere Neustadt":   (51.063, 51.075, 13.735, 13.758),
    "Pieschen":          (51.075, 51.090, 13.700, 13.730),
    "Trachau":           (51.085, 51.100, 13.700, 13.730),
    "Klotzsche":         (51.110, 51.135, 13.750, 13.800),
    "Loschwitz":         (51.055, 51.075, 13.790, 13.830),
    "Blasewitz":         (51.035, 51.055, 13.775, 13.810),
    "Striesen":          (51.030, 51.050, 13.760, 13.790),
    "Gruna":             (51.020, 51.035, 13.760, 13.790),
    "Seidnitz":          (51.020, 51.035, 13.790, 13.820),
    "Johannstadt":       (51.040, 51.055, 13.745, 13.770),
    "Südvorstadt":       (51.020, 51.040, 13.720, 13.745),
    "Plauen":            (51.010, 51.030, 13.700, 13.725),
    "Löbtau":            (51.035, 51.050, 13.680, 13.705),
    "Cotta":             (51.045, 51.065, 13.670, 13.700),
    "Leuben":            (51.005, 51.025, 13.800, 13.830),
    "Prohlis":           (50.995, 51.015, 13.780, 13.805),
    "Cossebaude":        (51.075, 51.095, 13.620, 13.660),
    "Weixdorf":          (51.130, 51.155, 13.800, 13.840),
}
STADTTEIL_NOMBRES = list(STADTTEILE.keys())

# ---------------------------------------------------------------------------
# 2. CATÁLOGOS PARA GENERAR DATOS COHERENTES
# ---------------------------------------------------------------------------
FAHRRAD_HERSTELLER = ["Trek", "Cube", "Giant", "Riese & Müller", "Diamant",
                       "Kalkhoff", "Winora", "Bergamont"]
FAHRRAD_BEZEICHNUNGEN = ["CityCruiser", "UrbanRide", "StreetLine", "EcoMove",
                          "PowerPedal", "FlexiBike", "MetroGlide", "ActiveLine"]
FAHRRADTYPEN = ["Stadtrad", "E-Bike", "Mountainbike", "Lastenrad", "Rennrad", "Klapprad"]

STATUS_FAHRRAD = ["aktiv", "aktiv", "aktiv", "wartung", "defekt", "ausgemustert"]
KUNDENTYP = ["Privatperson", "Privatperson", "Privatperson", "Student", "Firma", "Tourist"]

ZAHLUNGSARTEN = ["Kreditkarte", "PayPal", "Lastschrift", "App-Guthaben"]
STATUS_ZAHLUNG_WEIGHTS = [("bezahlt", 85), ("ausstehend", 8), ("fehlgeschlagen", 7)]
STATUS_FAHRT_WEIGHTS = [("abgeschlossen", 80), ("storniert", 10), ("laufend", 10)]

WARTUNGSARTEN = ["Reparatur", "Inspektion", "Reinigung", "Ersatzteiltausch"]

# Catálogo fijo de Tarife (no se pregunta, son parámetros comerciales estables)
TARIFE_CATALOGO = [
    # bezeichnung, grundgebuehr, preis_pro_minute, gueltig_ab (dias atras), gueltig_bis
    ("Kurzzeittarif", 1.00, 0.12, 1500, None),
    ("Tagestarif",    8.00, 0.00, 1500, None),
    ("Wochentarif",  18.00, 0.00, 1200, None),
    ("Monatsabo",    24.90, 0.00, 900, None),
    ("Jahresabo",   180.00, 0.00, 600, None),
]

# ---------------------------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------------------------
coordenadas_usadas = set()


def coordenada_unica(stadtteil):
    lat_min, lat_max, lon_min, lon_max = STADTTEILE[stadtteil]
    for _ in range(200):
        lat = round(random.uniform(lat_min, lat_max), 6)
        lon = round(random.uniform(lon_min, lon_max), 6)
        if (lat, lon) not in coordenadas_usadas:
            coordenadas_usadas.add((lat, lon))
            return lat, lon
    raise RuntimeError(
        f"No se pudo generar una coordenada única para '{stadtteil}' tras 200 intentos."
    )


def elegir_con_peso(pares):
    valores = [v for v, _ in pares]
    pesos = [w for _, w in pares]
    return random.choices(valores, weights=pesos, k=1)[0]


def fecha_relativa(dias_min, dias_max, ahora=None):
    """datetime = ahora - dias (dias negativos => fecha futura)."""
    ahora = ahora or datetime.now()
    dias = random.uniform(dias_min, dias_max)
    return (ahora - timedelta(days=dias)).replace(microsecond=0)


def sql_escape(valor):
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, datetime):
        return f"'{valor.strftime('%Y-%m-%d %H:%M:%S')}'"
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"


def escribir_csv(nombre_archivo, columnas, filas):
    with open(nombre_archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columnas)
        writer.writerows(filas)
    print(f"  -> {nombre_archivo} ({len(filas)} filas)")


def escribir_sql(nombre_archivo, tabla, columnas, filas):
    """INSERT sin columna id: la asigna GENERATED ALWAYS AS IDENTITY."""
    columnas_sin_id = columnas[1:]
    with open(nombre_archivo, "a", encoding="utf-8") as f:
        f.write(f"\n-- {tabla} ({len(filas)} filas)\n")
        cols_sql = ", ".join(columnas_sin_id)
        for fila in filas:
            valores = ", ".join(sql_escape(v) for v in fila[1:])
            f.write(f"INSERT INTO bikeshare.{tabla} ({cols_sql}) VALUES ({valores});\n")


def escribir_truncate(nombre_archivo, tablas):
    tablas_qualificadas = ", ".join(f"bikeshare.{t}" for t in tablas)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("-- Vaciar tablas y reiniciar las IDENTITY antes de cargar los datos\n")
        f.write(f"TRUNCATE TABLE {tablas_qualificadas} RESTART IDENTITY CASCADE;\n")


# ---------------------------------------------------------------------------
# 4. GENERACIÓN DE DATOS
# ---------------------------------------------------------------------------
def generar_datos(n_modelle, n_fahrraeder, n_stationen, n_kunden, n_fahrten):
    ahora = datetime.now()

    # --- Fahrradmodell ---
    modelle = []
    for i in range(1, n_modelle + 1):
        hersteller = random.choice(FAHRRAD_HERSTELLER)
        bezeichnung = random.choice(FAHRRAD_BEZEICHNUNGEN)
        typ = random.choice(FAHRRADTYPEN)
        baujahr = random.randint(2018, 2026)
        modelle.append((i, hersteller, bezeichnung, typ, baujahr))

    # --- Fahrrad ---
    fahrraeder = []
    for i in range(1, n_fahrraeder + 1):
        id_modell, *_ = random.choice(modelle)
        inventarnummer = f"BS-{i:05d}"
        anschaffung = fecha_relativa(60, 1800, ahora).date()
        status = random.choice(STATUS_FAHRRAD)
        fahrraeder.append((i, id_modell, inventarnummer, anschaffung, status))

    # --- Station ---
    stationen = []
    for i in range(1, n_stationen + 1):
        stadtteil = random.choice(STADTTEIL_NOMBRES)
        lat, lon = coordenada_unica(stadtteil)
        nombre = f"BikeShare Station {stadtteil} {i}"
        kapazitaet = random.choice([10, 15, 20, 25, 30, 40])
        stationen.append((i, nombre, stadtteil, lat, lon, kapazitaet))

    # --- Kunde ---
    kunden = []
    for i in range(1, n_kunden + 1):
        registrierung = fecha_relativa(1, 1800, ahora).date()
        kundentyp = random.choice(KUNDENTYP)
        kunden.append((i, registrierung, kundentyp))

    # --- Tarif (catálogo fijo) ---
    tarife = []
    for i, (bezeichnung, grundgebuehr, preis_min, dias_ab, dias_bis) in enumerate(
            TARIFE_CATALOGO, start=1):
        gueltig_ab = fecha_relativa(dias_ab, dias_ab, ahora).date()
        gueltig_bis = None if dias_bis is None else fecha_relativa(dias_bis, dias_bis, ahora).date()
        tarife.append((i, bezeichnung, grundgebuehr, preis_min, gueltig_ab, gueltig_bis))

    # --- Fahrt (tabla masiva) ---
    fahrten = []
    for i in range(1, n_fahrten + 1):
        id_kunde, *_ = random.choice(kunden)
        id_fahrrad, *_ = random.choice(fahrraeder)
        id_startstation, *_ = random.choice(stationen)
        id_zielstation, *_ = random.choice(stationen)
        while id_zielstation == id_startstation:
            id_zielstation, *_ = random.choice(stationen)
        id_tarif, *_ = random.choice(tarife)

        status = elegir_con_peso(STATUS_FAHRT_WEIGHTS)
        if status == "laufend":
            startzeit = fecha_relativa(0, 0.02, ahora)  # empezó hace pocos minutos
            fahrtdauer = None
            endzeit = None
        else:
            startzeit = fecha_relativa(0, 180, ahora)
            fahrtdauer = random.randint(3, 90)
            endzeit = startzeit + timedelta(minutes=fahrtdauer)

        fahrten.append((i, id_kunde, id_fahrrad, id_startstation, id_zielstation,
                         id_tarif, startzeit, endzeit, fahrtdauer, status))

    # --- Zahlung (solo para Fahrten abgeschlossen) ---
    zahlungen = []
    tarif_por_id = {t[0]: t for t in tarife}
    zahlung_id = 1
    for fahrt in fahrten:
        (f_id, _, _, _, _, id_tarif, _, endzeit, fahrtdauer, status) = fahrt
        if status == "abgeschlossen":
            _, _, grundgebuehr, preis_min, _, _ = tarif_por_id[id_tarif]
            betrag = round(float(grundgebuehr) + float(preis_min) * fahrtdauer, 2)
            zahlungszeitpunkt = endzeit + timedelta(minutes=random.uniform(0, 5))
            zahlungsart = random.choice(ZAHLUNGSARTEN)
            status_zahlung = elegir_con_peso(STATUS_ZAHLUNG_WEIGHTS)
            zahlungen.append((zahlung_id, f_id, zahlungszeitpunkt, betrag,
                               zahlungsart, status_zahlung))
            zahlung_id += 1

    # --- Wartung (0 a 3 por Fahrrad) ---
    wartungen = []
    wartung_id = 1
    for fahrrad in fahrraeder:
        (f_id, _, _, anschaffung, _) = fahrrad
        dias_desde_anschaffung = max(1, (ahora.date() - anschaffung).days)
        for _ in range(random.randint(0, 3)):
            beginn = fecha_relativa(0, dias_desde_anschaffung, ahora)
            duracion_h = random.randint(1, 24)
            ende = beginn + timedelta(hours=duracion_h)
            wartungsart = random.choice(WARTUNGSARTEN)
            kosten = round(random.uniform(15, 500), 2)
            beschreibung = f"{wartungsart} an Fahrrad {f_id}"
            wartungen.append((wartung_id, f_id, beginn, ende, wartungsart, kosten, beschreibung))
            wartung_id += 1

    return modelle, fahrraeder, stationen, kunden, tarife, fahrten, zahlungen, wartungen


# ---------------------------------------------------------------------------
# 5. MAIN INTERACTIVO
# ---------------------------------------------------------------------------
def pedir_entero(mensaje, valor_default):
    entrada = input(f"{mensaje} [{valor_default}]: ").strip()
    if entrada == "":
        return valor_default
    try:
        return max(1, int(entrada))
    except ValueError:
        print("  Valor no válido, se usará el valor por defecto.")
        return valor_default


def main():
    print("=== Generador de datos sintéticos — BikeShare (Dresden) ===\n")

    n_modelle = pedir_entero("¿Cuántos Fahrradmodelle querés generar?", 8)
    n_fahrraeder = pedir_entero("¿Cuántos Fahrräder querés generar?", 150)
    n_stationen = pedir_entero("¿Cuántas Stationen querés generar?", 25)
    n_kunden = pedir_entero("¿Cuántos Kunden querés generar?", 300)
    n_fahrten = pedir_entero("¿Cuántas Fahrten en total querés generar?", 1000)

    print("\nGenerando datos...\n")
    (modelle, fahrraeder, stationen, kunden, tarife, fahrten, zahlungen,
     wartungen) = generar_datos(n_modelle, n_fahrraeder, n_stationen, n_kunden, n_fahrten)

    print("Escribiendo archivos CSV:")
    escribir_csv("bikeshare_fahrradmodell.csv",
                 ["id", "hersteller", "bezeichnung", "fahrradtyp", "baujahr"], modelle)
    escribir_csv("bikeshare_fahrrad.csv",
                 ["id", "id_modell", "inventarnummer", "anschaffungsdatum", "status"], fahrraeder)
    escribir_csv("bikeshare_station.csv",
                 ["id", "name", "stadtteil", "latitude", "longitude", "kapazitaet"], stationen)
    escribir_csv("bikeshare_kunde.csv",
                 ["id", "registrierungsdatum", "kundentyp"], kunden)
    escribir_csv("bikeshare_tarif.csv",
                 ["id", "bezeichnung", "grundgebuehr", "preis_pro_minute",
                  "gueltig_ab", "gueltig_bis"], tarife)
    escribir_csv("bikeshare_fahrt.csv",
                 ["id", "id_kunde", "id_fahrrad", "id_startstation", "id_zielstation",
                  "id_tarif", "startzeit", "endzeit", "fahrtdauer_min", "status"], fahrten)
    escribir_csv("bikeshare_zahlung.csv",
                 ["id", "id_fahrt", "zahlungszeitpunkt", "betrag", "zahlungsart", "status"],
                 zahlungen)
    escribir_csv("bikeshare_wartung.csv",
                 ["id", "id_fahrrad", "beginn", "ende", "wartungsart", "kosten", "beschreibung"],
                 wartungen)

    sql_file = "bikeshare_inserts.sql"
    tablas_en_orden = ["Fahrradmodell", "Fahrrad", "Station", "Kunde", "Tarif",
                        "Fahrt", "Zahlung", "Wartung"]
    escribir_truncate(sql_file, list(reversed(tablas_en_orden)))
    print(f"\nEscribiendo script SQL: {sql_file}")
    escribir_sql(sql_file, "Fahrradmodell",
                 ["id", "hersteller", "bezeichnung", "fahrradtyp", "baujahr"], modelle)
    escribir_sql(sql_file, "Fahrrad",
                 ["id", "id_modell", "inventarnummer", "anschaffungsdatum", "status"], fahrraeder)
    escribir_sql(sql_file, "Station",
                 ["id", "name", "stadtteil", "latitude", "longitude", "kapazitaet"], stationen)
    escribir_sql(sql_file, "Kunde",
                 ["id", "registrierungsdatum", "kundentyp"], kunden)
    escribir_sql(sql_file, "Tarif",
                 ["id", "bezeichnung", "grundgebuehr", "preis_pro_minute",
                  "gueltig_ab", "gueltig_bis"], tarife)
    escribir_sql(sql_file, "Fahrt",
                 ["id", "id_kunde", "id_fahrrad", "id_startstation", "id_zielstation",
                  "id_tarif", "startzeit", "endzeit", "fahrtdauer_min", "status"], fahrten)
    escribir_sql(sql_file, "Zahlung",
                 ["id", "id_fahrt", "zahlungszeitpunkt", "betrag", "zahlungsart", "status"],
                 zahlungen)
    escribir_sql(sql_file, "Wartung",
                 ["id", "id_fahrrad", "beginn", "ende", "wartungsart", "kosten", "beschreibung"],
                 wartungen)

    print("\n¡Listo! Resumen:")
    print(f"  Fahrradmodelle: {len(modelle)}")
    print(f"  Fahrräder:      {len(fahrraeder)}")
    print(f"  Stationen:      {len(stationen)}")
    print(f"  Kunden:         {len(kunden)}")
    print(f"  Tarife:         {len(tarife)}")
    print(f"  Fahrten:        {len(fahrten)}")
    print(f"  Zahlungen:      {len(zahlungen)}")
    print(f"  Wartungen:      {len(wartungen)}")
    print(f"  Coordenadas únicas usadas: {len(coordenadas_usadas)}")


if __name__ == "__main__":
    main()
