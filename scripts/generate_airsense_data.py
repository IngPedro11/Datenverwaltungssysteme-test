#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""
Synthetic data generator for the AirSense system (Dresden, Saxony).

Populates the following tables:

    - Station
    - Sensor
    - Measurement
    - SensorMaintenance

Generates coordinates (latitude/longitude) consistent with real
Dresden districts (approximated using bounding boxes), without
repeating any coordinate, and exports the results to CSV files
and an SQL script containing INSERT statements.

Usage:

    python3 generate_airsense_data.py

Uses only the Python standard library (no pip install required).
"""

import csv
import random
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 1. REAL DRESDEN DISTRICTS WITH APPROXIMATE BOUNDING BOXES (lat/lon)
#
#    (approximate values based on the actual district boundaries,
#    sufficient for a coherent simulation, but not for geodetic use)
# ---------------------------------------------------------------------------

DISTRICTS = {
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

DISTRICT_NAMES = list(DISTRICTS.keys())


# ---------------------------------------------------------------------------
# 2. CATALOGS FOR GENERATING CONSISTENT DATA
# ---------------------------------------------------------------------------

STATION_TYPES = [
    "Traffic",
    "Background",
    "Industrial",
    "Residential",
    "Park",
]

STATION_STATUS = [
    "active",
    "active",
    "active",
    "maintenance",
    "inactive",
]  # weights: active is more common

SENSOR_TYPES = {
    # sensor_type: (unit, minimum_value, maximum_value)
    "PM2.5":            ("µg/m³", 0, 150),
    "PM10":             ("µg/m³", 0, 200),
    "NO2":              ("µg/m³", 0, 120),
    "O3":               ("µg/m³", 0, 180),
    "CO2":              ("ppm", 350, 1200),
    "Temperature":      ("°C", -10, 36),
    "Humidity":         ("%", 20, 100),
    "Noise":             ("dB", 30, 95),
}

SENSOR_MANUFACTURERS = [
    "Vaisala",
    "Aeroqual",
    "Sensirion",
    "Bosch Sensortec",
    "Thermo Fisher",
    "Envea",
    "OTT HydroMet",
    "Testo",
]

SENSOR_STATUS = [
    "active",
    "active",
    "active",
    "faulty",
    "maintenance",
]

QUALITY_STATUS = [
    "verified",
    "verified",
    "verified",
    "preliminary",
    "faulty",
]

MAINTENANCE_TYPES = [
    "Calibration",
    "Cleaning",
    "Repair",
    "Replacement",
    "Inspection",
]


# ---------------------------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------------------------

used_coordinates = set()


def generate_unique_coordinate(district):
    """Generate a (latitude, longitude) inside the district's bounding box without repetition."""

    lat_min, lat_max, lon_min, lon_max = DISTRICTS[district]

    for _ in range(200):  # enough attempts before giving up
        latitude = round(random.uniform(lat_min, lat_max), 6)
        longitude = round(random.uniform(lon_min, lon_max), 6)

        if (latitude, longitude) not in used_coordinates:
            used_coordinates.add((latitude, longitude))
            return latitude, longitude

    raise RuntimeError(
        f"Could not generate a unique coordinate for '{district}' "
        "after 200 attempts (too many stations for the area?)."
    )


def random_date(days_back_min, days_back_max):
    """Return a random datetime between today - max days and today - min days."""

    days = random.randint(days_back_min, days_back_max)
    base = datetime.now() - timedelta(days=days)

    return base.replace(
        hour=random.randint(0, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0,
    )


def sql_escape(value):
    """Format a Python value for use in an SQL INSERT statement."""

    if value is None:
        return "NULL"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, datetime):
        return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"

    text = str(value).replace("'", "''")
    return f"'{text}'"


def write_csv(filename, columns, rows):
    """Write data to a CSV file."""

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  -> {filename} ({len(rows)} rows)")


def write_sql(filename, table, columns, rows):
    """Append INSERT statements to an SQL file."""

    with open(filename, "a", encoding="utf-8") as file:
        file.write(f"\n-- {table} ({len(rows)} rows)\n")

        sql_columns = ", ".join(columns)

        for row in rows:
            values = ", ".join(sql_escape(value) for value in row)

            file.write(
                f"INSERT INTO {table} ({sql_columns}) "
                f"VALUES ({values});\n"
            )


# ---------------------------------------------------------------------------
# 4. DATA GENERATION
# ---------------------------------------------------------------------------

def generate_data(number_of_stations, number_of_measurements):

    stations = []
    # (id, name, district, latitude, longitude, type, installation, status)

    sensors = []
    # (id, station_id, sensor_type, manufacturer, model, unit, installation, status)

    measurements = []
    # (id, sensor_id, measurement_time, measurement_value, quality_status)

    maintenances = []
    # (id, sensor_id, start, end, maintenance_type, cost, description)

    sensor_id = 1
    station_counter_by_district = {}

    # -----------------------------------------------------------------------
    # Station
    # -----------------------------------------------------------------------

    for station_id in range(1, number_of_stations + 1):

        district = random.choice(DISTRICT_NAMES)

        station_counter_by_district[district] = (
            station_counter_by_district.get(district, 0) + 1
        )

        suffix = station_counter_by_district[district]

        latitude, longitude = generate_unique_coordinate(district)

        station_type = random.choice(STATION_TYPES)

        installation_date = random_date(200, 1800).date()
        # between approximately 7 months and 5 years ago

        status = random.choice(STATION_STATUS)

        name = f"Measurement Station {district} {suffix}"

        stations.append(
            (
                station_id,
                name,
                district,
                latitude,
                longitude,
                station_type,
                installation_date,
                status,
            )
        )

        # -------------------------------------------------------------------
        # Sensor(s) belonging to this station
        # -------------------------------------------------------------------

        number_of_sensors = random.randint(2, 5)

        sensor_types_for_station = random.sample(
            list(SENSOR_TYPES.keys()),
            k=min(number_of_sensors, len(SENSOR_TYPES)),
        )

        for sensor_type in sensor_types_for_station:

            unit, _, _ = SENSOR_TYPES[sensor_type]

            manufacturer = random.choice(SENSOR_MANUFACTURERS)

            model = (
                f"{manufacturer.split()[0][:3].upper()}-"
                f"{random.randint(100, 999)}"
            )

            max_sensor_installation_days = max(
                1,
                (datetime.now().date() - installation_date).days,
            )

            sensor_installation_date = random_date(
                0,
                max_sensor_installation_days,
            ).date()

            if sensor_installation_date < installation_date:
                sensor_installation_date = installation_date

            sensor_status = random.choice(SENSOR_STATUS)

            sensors.append(
                (
                    sensor_id,
                    station_id,
                    sensor_type,
                    manufacturer,
                    model,
                    unit,
                    sensor_installation_date,
                    sensor_status,
                )
            )

            # ---------------------------------------------------------------
            # Maintenance records for this sensor (0 to 3)
            # ---------------------------------------------------------------

            for _ in range(random.randint(0, 3)):

                days_since_installation = max(
                    1,
                    (datetime.now().date() - sensor_installation_date).days,
                )

                start = random_date(
                    0,
                    days_since_installation,
                )

                duration_hours = random.randint(1, 12)

                end = start + timedelta(hours=duration_hours)

                maintenance_type = random.choice(MAINTENANCE_TYPES)

                cost = round(random.uniform(50, 1800), 2)

                description = (
                    f"{maintenance_type} of {sensor_type} sensor "
                    f"at station {name}"
                )

                maintenances.append(
                    (
                        len(maintenances) + 1,
                        sensor_id,
                        start,
                        end,
                        maintenance_type,
                        cost,
                        description,
                    )
                )

            sensor_id += 1

    total_sensors = len(sensors)

    # -----------------------------------------------------------------------
    # Measurement: distribute number_of_measurements among all sensors
    # -----------------------------------------------------------------------

    weights = [
        random.random()
        for _ in range(total_sensors)
    ]

    weight_sum = sum(weights)

    quantities = [
        max(
            1,
            round(number_of_measurements * (weight / weight_sum))
        )
        for weight in weights
    ]

    # Fine adjustment so that the total is exactly number_of_measurements

    difference = number_of_measurements - sum(quantities)

    index = 0

    while difference != 0 and total_sensors > 0:

        if difference > 0:

            quantities[index % total_sensors] += 1
            difference -= 1

        else:

            if quantities[index % total_sensors] > 1:
                quantities[index % total_sensors] -= 1
                difference += 1

        index += 1

    measurement_id = 1

    for sensor_row, quantity in zip(sensors, quantities):

        sensor_id = sensor_row[0]
        sensor_type = sensor_row[2]

        _, minimum_value, maximum_value = SENSOR_TYPES[sensor_type]

        for _ in range(quantity):

            measurement_time = random_date(0, 180)
            # approximately the last 6 months

            value = round(
                random.uniform(minimum_value, maximum_value),
                2,
            )

            quality = random.choice(QUALITY_STATUS)

            measurements.append(
                (
                    measurement_id,
                    sensor_id,
                    measurement_time,
                    value,
                    quality,
                )
            )

            measurement_id += 1

    return stations, sensors, measurements, maintenances


# ---------------------------------------------------------------------------
# 5. INTERACTIVE MAIN
# ---------------------------------------------------------------------------

def ask_integer(message, default_value):

    entry = input(
        f"{message} [{default_value}]: "
    ).strip()

    if entry == "":
        return default_value

    try:
        return max(1, int(entry))

    except ValueError:

        print("  Invalid value, the default value will be used.")

        return default_value


def main():

    print(
        "=== Synthetic Data Generator — AirSense (Dresden) ===\n"
    )

    number_of_stations = ask_integer(
        "How many stations would you like to generate?",
        25,
    )

    number_of_measurements = ask_integer(
        "How many measurements in total would you like to generate?",
        1000,
    )

    print(
        f"\nGenerating {number_of_stations} stations and "
        f"{number_of_measurements} measurements...\n"
    )

    stations, sensors, measurements, maintenances = generate_data(
        number_of_stations,
        number_of_measurements,
    )

    # -----------------------------------------------------------------------
    # CSV files
    # -----------------------------------------------------------------------

    print("Writing CSV files:")

    write_csv(
        "airsense_station.csv",
        [
            "id",
            "name",
            "district",
            "latitude",
            "longitude",
            "station_type",
            "installation_date",
            "status",
        ],
        stations,
    )

    write_csv(
        "airsense_sensor.csv",
        [
            "id",
            "station_id",
            "sensor_type",
            "manufacturer",
            "model",
            "unit",
            "installation_date",
            "status",
        ],
        sensors,
    )

    write_csv(
        "airsense_measurement.csv",
        [
            "id",
            "sensor_id",
            "measurement_time",
            "measurement_value",
            "quality_status",
        ],
        measurements,
    )

    write_csv(
        "airsense_sensor_maintenance.csv",
        [
            "id",
            "sensor_id",
            "start",
            "end",
            "maintenance_type",
            "cost",
            "description",
        ],
        maintenances,
    )

    # -----------------------------------------------------------------------
    # SQL
    # -----------------------------------------------------------------------

    sql_file = "airsense_inserts.sql"

    # Clear the file if it already exists

    open(sql_file, "w", encoding="utf-8").close()

    print(f"\nWriting SQL script: {sql_file}")

    write_sql(
        sql_file,
        "Station",
        [
            "id",
            "name",
            "district",
            "latitude",
            "longitude",
            "station_type",
            "installation_date",
            "status",
        ],
        stations,
    )

    write_sql(
        sql_file,
        "Sensor",
        [
            "id",
            "station_id",
            "sensor_type",
            "manufacturer",
            "model",
            "unit",
            "installation_date",
            "status",
        ],
        sensors,
    )

    write_sql(
        sql_file,
        "Measurement",
        [
            "id",
            "sensor_id",
            "measurement_time",
            "measurement_value",
            "quality_status",
        ],
        measurements,
    )

    write_sql(
        sql_file,
        "SensorMaintenance",
        [
            "id",
            "sensor_id",
            "start",
            "end",
            "maintenance_type",
            "cost",
            "description",
        ],
        maintenances,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    print("\nDone! Summary:")

    print(f"  Stations:             {len(stations)}")
    print(f"  Sensors:              {len(sensors)}")
    print(f"  Measurements:         {len(measurements)}")
    print(f"  Sensor maintenances:  {len(maintenances)}")
    print(f"  Unique coordinates:   {len(used_coordinates)}")


if __name__ == "__main__":
    main()