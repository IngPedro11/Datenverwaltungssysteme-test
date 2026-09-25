#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos sintéticos para el sistema CityMove (Dresden, Sajonia).

Pensado para un schema Postgres `citymove` con columnas
`GENERATED ALWAYS AS IDENTITY`: los IDs los genera Postgres solo (no se
fuerzan con OVERRIDING SYSTEM VALUE). Para que las FK sigan cuadrando,
el script primero vacía las tablas con `TRUNCATE ... RESTART IDENTITY
CASCADE` y luego inserta las filas exactamente en el mismo orden en que
se generaron en Python (sin incluir la columna id) — así el ID que
asigna la IDENTITY coincide con el que usamos internamente para las
referencias.

Rellena las tablas:
    - Modell
    - Fahrzeug
    - Linie
    - Haltestelle
    - Linien_Haltestelle
    - Fahrt
    - Fahrplan
    - Fahrt_Haltestelle
    - Fahrgastaufkommen
    - Stoerung

Cada Linie tiene una secuencia fija y realista de Haltestellen (ida y
vuelta). Cada Fahrt (viaje concreto en una fecha) recorre esa secuencia
generando su Fahrplan (horario planeado), Fahrt_Haltestelle (horario
real, solo si el viaje ya se realizó), Fahrgastaufkommen (pasajeros por
parada) y, ocasionalmente, una Stoerung.

Uso:
    python3 generate_citymove_data.py

Solo usa la librería estándar de Python (no requiere pip install).
Genera CSV (uno por tabla) + un script SQL listo para Postgres.
"""

import csv
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 1. STADTTEILE REALES DE DRESDEN CON BOUNDING BOX APROXIMADO (lat/lon)
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
FAHRZEUG_HERSTELLER = ["Bombardier", "Siemens", "Alstom", "Mercedes-Benz",
                        "MAN", "Solaris", "Iveco"]
FAHRZEUGTYPEN = ["Straßenbahn", "Bus", "Gelenkbus", "Niederflurbus"]
STATUS_FAHRZEUG = ["aktiv", "aktiv", "aktiv", "wartung", "außer Betrieb"]

LINIENNUMMERN_TRAM = ["1", "2", "3", "4", "6", "7", "8", "9", "10", "11", "12", "13"]
LINIENNUMMERN_BUS = ["61", "62", "64", "70", "74", "75", "76", "80", "85", "86", "87", "90", "94", "97"]

STATUS_FAHRT_WEIGHTS = [("durchgeführt", 70), ("geplant", 22), ("ausgefallen", 8)]
FAHRTRICHTUNGEN = ["Hinfahrt", "Rückfahrt"]

STOERUNG_TYPEN = ["Verspätung", "Technischer Defekt", "Unfall", "Wetterbedingt", "Signalstörung"]

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
            f.write(f"INSERT INTO citymove.{tabla} ({cols_sql}) VALUES ({valores});\n")


def escribir_truncate(nombre_archivo, tablas):
    tablas_qualificadas = ", ".join(f"citymove.{t}" for t in tablas)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("-- Vaciar tablas y reiniciar las IDENTITY antes de cargar los datos\n")
        f.write(f"TRUNCATE TABLE {tablas_qualificadas} RESTART IDENTITY CASCADE;\n")


# ---------------------------------------------------------------------------
# 4. GENERACIÓN DE DATOS
# ---------------------------------------------------------------------------
def generar_datos(n_haltestellen, n_linien, n_modelle, n_fahrzeuge, n_fahrten):
    ahora = datetime.now()

    # --- Haltestelle ---
    haltestellen = []
    for i in range(1, n_haltestellen + 1):
        stadtteil = random.choice(STADTTEIL_NOMBRES)
        lat, lon = coordenada_unica(stadtteil)
        nombre = f"Haltestelle {stadtteil} {i}"
        haltestellen.append((i, nombre, stadtteil, lat, lon))

    # --- Linie (+ secuencia de paradas por línea, sin repetir) ---
    linien = []
    ruta_por_linie = {}  # id_linie -> lista ordenada de id_haltestelle (Hinfahrt)
    liniennummern_usadas = set()
    pool_nummern = LINIENNUMMERN_TRAM + LINIENNUMMERN_BUS

    for i in range(1, n_linien + 1):
        verkehrsmittel = "Straßenbahn" if i <= n_linien // 2 else "Bus"
        pool = LINIENNUMMERN_TRAM if verkehrsmittel == "Straßenbahn" else LINIENNUMMERN_BUS
        candidatos = [n for n in pool if n not in liniennummern_usadas]
        liniennummer = random.choice(candidatos) if candidatos else str(100 + i)
        liniennummern_usadas.add(liniennummer)

        n_paradas = min(len(haltestellen), random.randint(6, 14))
        paradas = random.sample(range(1, n_haltestellen + 1), k=n_paradas)
        ruta_por_linie[i] = paradas

        origen = haltestellen[paradas[0] - 1][2]
        destino = haltestellen[paradas[-1] - 1][2]
        bezeichnung = f"Linie {liniennummer}: {origen} – {destino}"
        gueltig_ab = fecha_relativa(900, 900, ahora).date()
        gueltig_bis = None

        linien.append((i, liniennummer, bezeichnung, verkehrsmittel, gueltig_ab, gueltig_bis))

    # --- Linien_Haltestelle (Hinfahrt + Rückfahrt) ---
    linien_haltestelle = []
    lh_id = 1
    for id_linie, paradas in ruta_por_linie.items():
        for idx, id_h in enumerate(paradas, start=1):
            linien_haltestelle.append((lh_id, id_linie, id_h, idx, "Hinfahrt"))
            lh_id += 1
        for idx, id_h in enumerate(reversed(paradas), start=1):
            linien_haltestelle.append((lh_id, id_linie, id_h, idx, "Rückfahrt"))
            lh_id += 1

    # --- Modell (vehículo) ---
    modelle = []
    for i in range(1, n_modelle + 1):
        hersteller = random.choice(FAHRZEUG_HERSTELLER)
        typ = random.choice(FAHRZEUGTYPEN)
        bezeichnung = f"{hersteller.split()[0]} {typ} {random.choice(['S', 'X', 'C'])}{random.randint(1,9)}"
        baujahr = random.randint(2005, 2026)
        modelle.append((i, hersteller, bezeichnung, typ, baujahr))

    # --- Fahrzeug ---
    fahrzeuge = []
    for i in range(1, n_fahrzeuge + 1):
        id_modell, _, _, typ_modell, _ = random.choice(modelle)
        fahrzeugnummer = f"CM-{i:04d}"
        if typ_modell == "Straßenbahn":
            kapazitaet = random.randint(150, 220)
            antriebsart = "Strom"
        elif typ_modell == "Gelenkbus":
            kapazitaet = random.randint(100, 160)
            antriebsart = random.choice(["Diesel", "Hybrid", "Elektro"])
        else:
            kapazitaet = random.randint(60, 110)
            antriebsart = random.choice(["Diesel", "Hybrid", "Elektro"])
        inbetriebnahme = fecha_relativa(200, 2500, ahora).date()
        status = random.choice(STATUS_FAHRZEUG)
        fahrzeuge.append((i, id_modell, fahrzeugnummer, kapazitaet, antriebsart,
                           inbetriebnahme, status))

    # Mapear qué fahrzeuge son tranvía / bus según su modelo, para asignarlos
    # a líneas del tipo correspondiente
    modell_typ = {m[0]: m[3] for m in modelle}
    fahrzeuge_tram = [f for f in fahrzeuge if modell_typ[f[1]] == "Straßenbahn"]
    fahrzeuge_bus = [f for f in fahrzeuge if modell_typ[f[1]] != "Straßenbahn"]

    # --- Fahrt (viajes concretos) + Fahrplan + Fahrt_Haltestelle +
    #     Fahrgastaufkommen + Stoerung ---
    fahrten = []
    fahrplan = []
    fahrt_haltestelle = []
    fahrgastaufkommen = []
    stoerungen = []

    fahrplan_id = 1
    fh_id = 1
    fga_id = 1
    stoerung_id = 1

    for i in range(1, n_fahrten + 1):
        id_linie, liniennummer, _, verkehrsmittel, _, _ = random.choice(linien)
        pool_fahrzeuge = fahrzeuge_tram if verkehrsmittel == "Straßenbahn" else fahrzeuge_bus
        if not pool_fahrzeuge:
            pool_fahrzeuge = fahrzeuge
        id_fahrzeug, *_ = random.choice(pool_fahrzeuge)

        status_fahrt = elegir_con_peso(STATUS_FAHRT_WEIGHTS)
        fahrtrichtung = random.choice(FAHRTRICHTUNGEN)

        if status_fahrt == "geplant":
            momento_base = fecha_relativa(-14, -1, ahora)  # próximos 1-14 días
        else:
            momento_base = fecha_relativa(1, 180, ahora)  # últimos 6 meses
        datum = momento_base.date()

        fahrten.append((i, id_linie, id_fahrzeug, datum, fahrtrichtung, status_fahrt))

        paradas = ruta_por_linie[id_linie]
        secuencia = paradas if fahrtrichtung == "Hinfahrt" else list(reversed(paradas))

        # Hora base de salida del recorrido (entre 05:00 y 23:00)
        hora_inicio = momento_base.replace(
            hour=random.randint(5, 23), minute=random.choice([0, 10, 15, 20, 30, 40, 45, 50]),
            second=0,
        )
        tiempo_actual = hora_inicio
        total_paradas = len(secuencia)

        for idx, id_haltestelle in enumerate(secuencia):
            intervalo_min = random.randint(2, 6)
            if idx > 0:
                tiempo_actual = tiempo_actual + timedelta(minutes=intervalo_min)
            ankunft_geplant = tiempo_actual
            dwell_min = 0 if idx in (0, total_paradas - 1) else random.choice([0, 1, 1, 2])
            abfahrt_geplant = ankunft_geplant + timedelta(minutes=dwell_min)
            tiempo_actual = abfahrt_geplant

            fahrplan.append((fahrplan_id, i, id_haltestelle, ankunft_geplant, abfahrt_geplant))
            fahrplan_id += 1

            if status_fahrt == "durchgeführt":
                retraso_min = random.choice([0, 0, 0, 1, 2, 3, 5, 8]) if random.random() > 0.05 \
                    else random.randint(10, 25)
                ankunft_tat = ankunft_geplant + timedelta(minutes=retraso_min)
                abfahrt_tat = abfahrt_geplant + timedelta(minutes=retraso_min)
                fahrt_haltestelle.append((fh_id, i, id_haltestelle, ankunft_tat, abfahrt_tat))
                fh_id += 1

                if idx == 0:
                    aussteiger = 0
                    einsteiger = random.randint(0, 25)
                elif idx == total_paradas - 1:
                    aussteiger = random.randint(0, 25)
                    einsteiger = 0
                else:
                    aussteiger = random.randint(0, 20)
                    einsteiger = random.randint(0, 20)
                fahrgastaufkommen.append((fga_id, i, id_haltestelle, einsteiger, aussteiger))
                fga_id += 1

        # --- Stoerung: ocasional, o casi segura si el viaje fue "ausgefallen" ---
        probabilidad = 0.9 if status_fahrt == "ausgefallen" else 0.08
        if status_fahrt != "geplant" and random.random() < probabilidad:
            id_haltestelle_stoerung = random.choice(secuencia)
            typ = "Ausfall" if status_fahrt == "ausgefallen" else random.choice(STOERUNG_TYPEN)
            beginn = hora_inicio + timedelta(minutes=random.uniform(0, 30))
            dauer_min = random.randint(5, 45)
            ende = beginn + timedelta(minutes=dauer_min)
            beschreibung = f"{typ} auf Linie {liniennummer} ({fahrtrichtung})"
            stoerungen.append((stoerung_id, i, id_haltestelle_stoerung, typ, beginn, ende,
                                dauer_min, beschreibung))
            stoerung_id += 1

    return (haltestellen, linien, linien_haltestelle, modelle, fahrzeuge,
            fahrten, fahrplan, fahrt_haltestelle, fahrgastaufkommen, stoerungen)


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
    print("=== Generador de datos sintéticos — CityMove (Dresden) ===\n")
    print("Nota: cada 'Fahrt' genera automáticamente varias filas hijas")
    print("(Fahrplan, Fahrt_Haltestelle, Fahrgastaufkommen), así que con")
    print("pocos viajes ya se generan miles de filas en total.\n")

    n_haltestellen = pedir_entero("¿Cuántas Haltestellen querés generar?", 40)
    n_linien = pedir_entero("¿Cuántas Linien querés generar?", 10)
    n_modelle = pedir_entero("¿Cuántos Fahrzeugmodelle querés generar?", 8)
    n_fahrzeuge = pedir_entero("¿Cuántos Fahrzeuge querés generar?", 60)
    n_fahrten = pedir_entero("¿Cuántas Fahrten (viajes concretos) querés generar?", 300)

    print("\nGenerando datos...\n")
    (haltestellen, linien, linien_haltestelle, modelle, fahrzeuge, fahrten,
     fahrplan, fahrt_haltestelle, fahrgastaufkommen, stoerungen) = generar_datos(
        n_haltestellen, n_linien, n_modelle, n_fahrzeuge, n_fahrten
    )

    print("Escribiendo archivos CSV:")
    escribir_csv("citymove_haltestelle.csv",
                 ["id", "name", "stadtteil", "latitude", "longitude"], haltestellen)
    escribir_csv("citymove_linie.csv",
                 ["id", "liniennummer", "bezeichnung", "verkehrsmittel",
                  "gueltig_ab", "gueltig_bis"], linien)
    escribir_csv("citymove_linien_haltestelle.csv",
                 ["id", "id_linie", "id_haltestelle", "reihenfolge", "fahrtrichtung"],
                 linien_haltestelle)
    escribir_csv("citymove_modell.csv",
                 ["id", "hersteller", "bezeichnung", "fahrzeugtyp", "baujahr"], modelle)
    escribir_csv("citymove_fahrzeug.csv",
                 ["id", "id_modell", "fahrzeugnummer", "kapazitaet", "antriebsart",
                  "inbetriebnahme", "status"], fahrzeuge)
    escribir_csv("citymove_fahrt.csv",
                 ["id", "id_linie", "id_fahrzeug", "datum", "fahrtrichtung", "fahrten_status"],
                 fahrten)
    escribir_csv("citymove_fahrplan.csv",
                 ["id", "id_fahrt", "id_haltestelle", "ankunft_geplant", "abfahrt_geplant"],
                 fahrplan)
    escribir_csv("citymove_fahrt_haltestelle.csv",
                 ["id", "id_fahrt", "id_haltestelle", "ankunft_tatsaechlich",
                  "abfahrt_tatsaechlich"], fahrt_haltestelle)
    escribir_csv("citymove_fahrgastaufkommen.csv",
                 ["id", "id_fahrt", "id_haltestelle", "einsteiger", "aussteiger"],
                 fahrgastaufkommen)
    escribir_csv("citymove_stoerung.csv",
                 ["id", "id_fahrt", "id_haltestelle", "typ", "beginn", "ende",
                  "dauer_min", "beschreibung"], stoerungen)

    sql_file = "citymove_inserts.sql"
    tablas_en_orden = ["Haltestelle", "Linie", "Linien_Haltestelle", "Modell", "Fahrzeug",
                        "Fahrt", "Fahrplan", "Fahrt_Haltestelle", "Fahrgastaufkommen", "Stoerung"]
    escribir_truncate(sql_file, list(reversed(tablas_en_orden)))
    print(f"\nEscribiendo script SQL: {sql_file}")
    escribir_sql(sql_file, "Haltestelle",
                 ["id", "name", "stadtteil", "latitude", "longitude"], haltestellen)
    escribir_sql(sql_file, "Linie",
                 ["id", "liniennummer", "bezeichnung", "verkehrsmittel",
                  "gueltig_ab", "gueltig_bis"], linien)
    escribir_sql(sql_file, "Linien_Haltestelle",
                 ["id", "id_linie", "id_haltestelle", "reihenfolge", "fahrtrichtung"],
                 linien_haltestelle)
    escribir_sql(sql_file, "Modell",
                 ["id", "hersteller", "bezeichnung", "fahrzeugtyp", "baujahr"], modelle)
    escribir_sql(sql_file, "Fahrzeug",
                 ["id", "id_modell", "fahrzeugnummer", "kapazitaet", "antriebsart",
                  "inbetriebnahme", "status"], fahrzeuge)
    escribir_sql(sql_file, "Fahrt",
                 ["id", "id_linie", "id_fahrzeug", "datum", "fahrtrichtung", "fahrten_status"],
                 fahrten)
    escribir_sql(sql_file, "Fahrplan",
                 ["id", "id_fahrt", "id_haltestelle", "ankunft_geplant", "abfahrt_geplant"],
                 fahrplan)
    escribir_sql(sql_file, "Fahrt_Haltestelle",
                 ["id", "id_fahrt", "id_haltestelle", "ankunft_tatsaechlich",
                  "abfahrt_tatsaechlich"], fahrt_haltestelle)
    escribir_sql(sql_file, "Fahrgastaufkommen",
                 ["id", "id_fahrt", "id_haltestelle", "einsteiger", "aussteiger"],
                 fahrgastaufkommen)
    escribir_sql(sql_file, "Stoerung",
                 ["id", "id_fahrt", "id_haltestelle", "typ", "beginn", "ende",
                  "dauer_min", "beschreibung"], stoerungen)

    print("\n¡Listo! Resumen:")
    print(f"  Haltestellen:        {len(haltestellen)}")
    print(f"  Linien:              {len(linien)}")
    print(f"  Linien_Haltestelle:  {len(linien_haltestelle)}")
    print(f"  Modelle:             {len(modelle)}")
    print(f"  Fahrzeuge:           {len(fahrzeuge)}")
    print(f"  Fahrten:             {len(fahrten)}")
    print(f"  Fahrplan:            {len(fahrplan)}")
    print(f"  Fahrt_Haltestelle:   {len(fahrt_haltestelle)}")
    print(f"  Fahrgastaufkommen:   {len(fahrgastaufkommen)}")
    print(f"  Stoerungen:          {len(stoerungen)}")
    print(f"  Coordenadas únicas usadas: {len(coordenadas_usadas)}")


if __name__ == "__main__":
    main()
