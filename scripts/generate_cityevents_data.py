#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synthetic data generator for the CityEvents system (Dresden, Saxony).

Designed for the PostgreSQL `cityevents` schema with columns using
`GENERATED ALWAYS AS IDENTITY`.

IDs are generated automatically by PostgreSQL. The script does not force
identity values with `OVERRIDING SYSTEM VALUE`.

To keep foreign keys consistent, the script first empties the tables using
`TRUNCATE ... RESTART IDENTITY CASCADE` and then inserts the generated rows
in exactly the same order in which they were created in Python.

The generated data is internally assigned sequential IDs starting from 1.
Because the identity sequences are restarted before insertion, PostgreSQL
will generate the same IDs used internally for foreign-key references.

Populates the following German database tables:

    - Veranstaltungstyp
    - Veranstalter
    - Veranstaltungsort
    - Besucher
    - Veranstaltung
    - Veranstaltungstermin
    - Ticket
    - Einlass
    - Stoerung

Usage:

    python3 generate_cityevents_data.py

The script uses only the Python standard library.
No external packages are required.

The script generates:
    - One CSV file per table
    - One PostgreSQL-ready SQL INSERT script
"""

import csv
import random
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 1. REAL DRESDEN DISTRICTS WITH APPROXIMATE BOUNDING BOXES
#    Latitude/longitude ranges are used to keep the generated locations
#    geographically consistent with Dresden.
# ---------------------------------------------------------------------------

STADTTEILE = {
    "Altstadt": (51.045, 51.060, 13.725, 13.745),
    "Innere Neustadt": (51.058, 51.068, 13.735, 13.755),
    "Äußere Neustadt": (51.063, 51.075, 13.735, 13.758),
    "Pieschen": (51.075, 51.090, 13.700, 13.730),
    "Trachau": (51.085, 51.100, 13.700, 13.730),
    "Klotzsche": (51.110, 51.135, 13.750, 13.800),
    "Loschwitz": (51.055, 51.075, 13.790, 13.830),
    "Blasewitz": (51.035, 51.055, 13.775, 13.810),
    "Striesen": (51.030, 51.050, 13.760, 13.790),
    "Gruna": (51.020, 51.035, 13.760, 13.790),
    "Seidnitz": (51.020, 51.035, 13.790, 13.820),
    "Johannstadt": (51.040, 51.055, 13.745, 13.770),
    "Südvorstadt": (51.020, 51.040, 13.720, 13.745),
    "Plauen": (51.010, 51.030, 13.700, 13.725),
    "Löbtau": (51.035, 51.050, 13.680, 13.705),
    "Cotta": (51.045, 51.065, 13.670, 13.700),
    "Leuben": (51.005, 51.025, 13.800, 13.830),
    "Prohlis": (50.995, 51.015, 13.780, 13.805),
    "Cossebaude": (51.075, 51.095, 13.620, 13.660),
    "Weixdorf": (51.130, 51.155, 13.800, 13.840),
}

STADTTEIL_NAMES = list(STADTTEILE.keys())

STREETS = [
    "Hauptstraße",
    "Bahnhofstraße",
    "Bautzner Straße",
    "Königsbrücker Straße",
    "Schandauer Straße",
    "Tharandter Straße",
    "Rothenburger Straße",
    "Bergstraße",
    "Wiener Straße",
    "Grunaer Straße",
    "Kesselsdorfer Straße",
    "Leipziger Straße",
    "Pillnitzer Landstraße",
    "Fritz-Löffler-Straße",
    "Marktplatz",
    "Elbufer",
    "Am Stadtpark",
    "Ringstraße",
    "Gartenstraße",
]


# ---------------------------------------------------------------------------
# 2. CATALOGS FOR CONSISTENT DATA GENERATION
#
# Database values intentionally remain in German because the database
# represents events and organizations in Dresden, Germany.
# ---------------------------------------------------------------------------

VERANSTALTUNGSTYPEN = [
    "Konzert",
    "Festival",
    "Messe",
    "Sportevent",
    "Theateraufführung",
    "Weihnachtsmarkt",
    "Stadtfest",
    "Konferenz",
    "Filmvorführung",
    "Flohmarkt",
]

ORGANISATIONSTYPEN = [
    "Verein",
    "Stadtverwaltung",
    "Privatunternehmen",
    "Kulturinstitution",
    "Universität",
    "Stiftung",
]

VERANSTALTER_FIXED = [
    ("Dresdner Philharmonie", "Kulturinstitution"),
    ("Semperoper Dresden", "Kulturinstitution"),
    ("Stadt Dresden – Kulturamt", "Stadtverwaltung"),
    ("Kulturpalast Dresden e.V.", "Verein"),
    ("Messe Dresden GmbH", "Privatunternehmen"),
    ("TU Dresden – Studentenwerk", "Universität"),
    ("Stiftung Frauenkirche Dresden", "Stiftung"),
    ("Dresden Marketing GmbH", "Privatunternehmen"),
]

VERANSTALTER_PREFIXES = [
    "Kulturverein",
    "Sportverein",
    "Förderverein",
    "Initiative",
    "Gesellschaft für Kultur",
]

VENUE_NAME_TEMPLATES = [
    "Stadthalle {district}",
    "Konzertsaal {district}",
    "Sportplatz {district}",
    "Festwiese {district}",
    "Marktplatz {district}",
    "Theater {district}",
    "Messehalle {district}",
    "Freilichtbühne {district}",
    "Gemeindesaal {district}",
    "Open-Air-Gelände {district}",
    "Kulturhaus {district}",
    "Arena {district}",
]

BESUCHER_CUSTOMER_TYPES = [
    "Privatperson",
    "Privatperson",
    "Privatperson",
    "Firma",
    "Vereinsmitglied",
    "Student",
]

TICKET_TYPES = {
    # Ticket type: (minimum price, maximum price)
    "Normal": (10, 40),
    "Ermaessigt": (5, 20),
    "VIP": (40, 120),
    "Gruppe": (8, 25),
}

TICKET_STATUSES = [
    "bezahlt",
    "bezahlt",
    "bezahlt",
    "storniert",
    "reserviert",
]

EINLASS_STATUSES = [
    "eingelassen",
    "eingelassen",
    "eingelassen",
    "eingelassen",
    "verweigert",
]

STOERUNG_TYPES = [
    "Technisch",
    "Wetter",
    "Sicherheit",
    "Gesundheitsnotfall",
    "Sonstiges",
]

TERMIN_STATUS_WEIGHTS = [
    ("abgeschlossen", 55),
    ("geplant", 30),
    ("abgesagt", 8),
    ("laufend", 7),
]


# ---------------------------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------------------------

USED_COORDINATES = set()


def generate_unique_coordinates(district):
    """
    Generate a unique latitude/longitude pair inside the selected
    Dresden district bounding box.
    """

    lat_min, lat_max, lon_min, lon_max = STADTTEILE[district]

    for _ in range(200):
        latitude = round(random.uniform(lat_min, lat_max), 6)
        longitude = round(random.uniform(lon_min, lon_max), 6)

        if (latitude, longitude) not in USED_COORDINATES:
            USED_COORDINATES.add((latitude, longitude))
            return latitude, longitude

    raise RuntimeError(
        f"Could not generate a unique coordinate for '{district}' "
        "after 200 attempts."
    )


def choose_weighted(pairs):
    """
    Select one value from a list of (value, weight) pairs.
    """

    values = [value for value, _ in pairs]
    weights = [weight for _, weight in pairs]

    return random.choices(
        values,
        weights=weights,
        k=1,
    )[0]


def generate_relative_date(days_min, days_max, current_time=None):
    """
    Return a datetime relative to the current time.

    Positive day values generate dates in the past.
    Negative day values generate dates in the future.
    """

    current_time = current_time or datetime.now()

    days = random.uniform(days_min, days_max)

    moment = current_time - timedelta(days=days)

    return moment.replace(microsecond=0)


def escape_sql_value(value):
    """
    Convert a Python value into a PostgreSQL-compatible SQL literal.
    """

    if value is None:
        return "NULL"

    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, datetime):
        return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"

    if hasattr(value, "isoformat"):
        return f"'{value.isoformat()}'"

    text_value = str(value).replace("'", "''")

    return f"'{text_value}'"


def write_csv(file_name, columns, rows):
    """
    Write generated rows to a UTF-8 CSV file.
    """

    with open(
        file_name,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  -> {file_name} ({len(rows)} rows)")


def write_sql(file_name, table_name, columns, rows):
    """
    Append PostgreSQL INSERT statements for one table.

    The first column is assumed to be the identity column and is therefore
    excluded from the INSERT statements.
    """

    columns_without_id = columns[1:]

    with open(
        file_name,
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            f"\n-- {table_name} ({len(rows)} rows)\n"
        )

        sql_columns = ", ".join(columns_without_id)

        for row in rows:

            sql_values = ", ".join(
                escape_sql_value(value)
                for value in row[1:]
            )

            file.write(
                f"INSERT INTO cityevents.{table_name} "
                f"({sql_columns}) "
                f"VALUES ({sql_values});\n"
            )


def write_truncate(file_name, table_names):
    """
    Write the TRUNCATE statement that empties all tables and restarts
    PostgreSQL identity sequences.
    """

    qualified_tables = ", ".join(
        f"cityevents.{table_name}"
        for table_name in table_names
    )

    with open(
        file_name,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "-- Empty tables and restart the IDENTITY sequences "
            "before loading the generated data.\n"
        )

        file.write(
            f"TRUNCATE TABLE {qualified_tables} "
            "RESTART IDENTITY CASCADE;\n"
        )


# ---------------------------------------------------------------------------
# 4. DATA GENERATION
# ---------------------------------------------------------------------------

def generate_data(
    number_of_venues,
    number_of_organizers,
    number_of_events,
    number_of_dates,
    number_of_visitors,
    number_of_tickets,
):
    """
    Generate all CityEvents data while maintaining consistent
    primary-key and foreign-key relationships.
    """

    current_time = datetime.now()

    # -----------------------------------------------------------------------
    # Veranstaltungstyp
    # -----------------------------------------------------------------------

    veranstaltungstypen = [
        (index + 1, event_type)
        for index, event_type in enumerate(VERANSTALTUNGSTYPEN)
    ]

    # -----------------------------------------------------------------------
    # Veranstalter
    # -----------------------------------------------------------------------

    veranstalter = []

    for index, (name, organization_type) in enumerate(
        VERANSTALTER_FIXED,
        start=1,
    ):
        veranstalter.append(
            (
                index,
                name,
                organization_type,
            )
        )

    for index in range(
        len(VERANSTALTER_FIXED) + 1,
        number_of_organizers + 1,
    ):

        district = random.choice(STADTTEIL_NAMES)

        prefix = random.choice(
            VERANSTALTER_PREFIXES
        )

        name = f"{prefix} {district}"

        organization_type = random.choice(
            ORGANISATIONSTYPEN
        )

        veranstalter.append(
            (
                index,
                name,
                organization_type,
            )
        )

    # -----------------------------------------------------------------------
    # Veranstaltungsort
    # -----------------------------------------------------------------------

    orte = []

    district_counters = {}

    for index in range(1, number_of_venues + 1):

        district = random.choice(
            STADTTEIL_NAMES
        )

        district_counters[district] = (
            district_counters.get(district, 0) + 1
        )

        latitude, longitude = generate_unique_coordinates(
            district
        )

        name = random.choice(
            VENUE_NAME_TEMPLATES
        ).format(
            district=district
        )

        street = random.choice(
            STREETS
        )

        house_number = random.randint(
            1,
            150
        )

        address = (
            f"{street} {house_number}, {district}"
        )

        capacity = random.choice(
            [
                80,
                150,
                300,
                500,
                800,
                1500,
                3000,
                8000,
                20000,
            ]
        )

        orte.append(
            (
                index,
                name,
                district,
                address,
                latitude,
                longitude,
                capacity,
            )
        )

    # -----------------------------------------------------------------------
    # Besucher
    # -----------------------------------------------------------------------

    besucher = []

    for index in range(
        1,
        number_of_visitors + 1,
    ):

        customer_type = random.choice(
            BESUCHER_CUSTOMER_TYPES
        )

        registration_date = generate_relative_date(
            30,
            2000,
            current_time,
        ).date()

        besucher.append(
            (
                index,
                customer_type,
                registration_date,
            )
        )

    # -----------------------------------------------------------------------
    # Veranstaltung
    # -----------------------------------------------------------------------

    veranstaltungen = []

    adjectives = [
        "Große",
        "Traditionelle",
        "Internationale",
        "Regionale",
        "Jährliche",
        "Besondere",
        "Offene",
    ]

    for index in range(
        1,
        number_of_events + 1,
    ):

        event_type_id, event_type = random.choice(
            veranstaltungstypen
        )

        organizer_id, organizer_name, _ = random.choice(
            veranstalter
        )

        name = (
            f"{random.choice(adjectives)} "
            f"{event_type} "
            f"{random.randint(2023, 2026)}"
        )

        description = (
            f"{event_type} organisiert von "
            f"{organizer_name} in Dresden."
        )

        veranstaltungen.append(
            (
                index,
                name,
                event_type_id,
                organizer_id,
                description,
            )
        )

    # -----------------------------------------------------------------------
    # Veranstaltungstermin
    # -----------------------------------------------------------------------

    termine = []

    for index in range(
        1,
        number_of_dates + 1,
    ):

        event_id, _, _, _, _ = random.choice(
            veranstaltungen
        )

        venue_id, _, _, _, _, _, _ = random.choice(
            orte
        )

        status = choose_weighted(
            TERMIN_STATUS_WEIGHTS
        )

        if status == "geplant":

            planned_start = generate_relative_date(
                -180,
                -1,
                current_time,
            )

        elif status == "laufend":

            planned_start = generate_relative_date(
                0,
                0.2,
                current_time,
            )

        else:

            planned_start = generate_relative_date(
                1,
                365,
                current_time,
            )

        duration_hours = random.choice(
            [
                1,
                2,
                3,
                4,
                6,
                8,
            ]
        )

        planned_end = (
            planned_start
            + timedelta(hours=duration_hours)
        )

        if status == "abgeschlossen":

            start_offset = random.randint(
                -15,
                30,
            )

            actual_start = (
                planned_start
                + timedelta(minutes=start_offset)
            )

            actual_end = (
                planned_end
                + timedelta(
                    minutes=random.randint(-15, 45)
                )
            )

        elif status == "laufend":

            actual_start = (
                planned_start
                + timedelta(
                    minutes=random.randint(-10, 10)
                )
            )

            actual_end = None

        else:

            actual_start = None
            actual_end = None

        termine.append(
            (
                index,
                event_id,
                venue_id,
                planned_start,
                planned_end,
                actual_start,
                actual_end,
                status,
            )
        )

    # -----------------------------------------------------------------------
    # Ticket
    # -----------------------------------------------------------------------

    sellable_dates = [
        date
        for date in termine
        if date[7] != "abgesagt"
    ]

    tickets = []

    if sellable_dates:

        random_weights = [
            random.random()
            for _ in sellable_dates
        ]

        weight_sum = sum(
            random_weights
        )

        quantities = [
            max(
                1,
                round(
                    number_of_tickets
                    * (weight / weight_sum)
                ),
            )
            for weight in random_weights
        ]

        difference = (
            number_of_tickets
            - sum(quantities)
        )

        index = 0

        while (
            difference != 0
            and sellable_dates
        ):

            position = (
                index
                % len(sellable_dates)
            )

            if difference > 0:

                quantities[position] += 1
                difference -= 1

            else:

                if quantities[position] > 1:

                    quantities[position] -= 1
                    difference += 1

            index += 1

        ticket_id = 1

        for event_date, quantity in zip(
            sellable_dates,
            quantities,
        ):

            (
                date_id,
                _,
                _,
                planned_start,
                _,
                _,
                _,
                _,
            ) = event_date

            for _ in range(quantity):

                visitor_id, _, registration_date = random.choice(
                    besucher
                )

                ticket_type = random.choice(
                    list(TICKET_TYPES.keys())
                )

                price_min, price_max = TICKET_TYPES[
                    ticket_type
                ]

                price = round(
                    random.uniform(
                        price_min,
                        price_max,
                    ),
                    2,
                )

                days_before = random.uniform(
                    1,
                    120,
                )

                purchase_time = (
                    planned_start
                    - timedelta(
                        days=days_before
                    )
                )

                registration_datetime = datetime.combine(
                    registration_date,
                    datetime.min.time(),
                )

                if purchase_time < registration_datetime:

                    purchase_time = (
                        registration_datetime
                        + timedelta(
                            hours=random.uniform(
                                1,
                                48,
                            )
                        )
                    )

                ticket_status = random.choice(
                    TICKET_STATUSES
                )

                tickets.append(
                    (
                        ticket_id,
                        date_id,
                        visitor_id,
                        ticket_type,
                        price,
                        purchase_time,
                        ticket_status,
                    )
                )

                ticket_id += 1

    # -----------------------------------------------------------------------
    # Einlass
    # Only for paid tickets belonging to events that have started.
    # -----------------------------------------------------------------------

    einlass = []

    entry_id = 1

    date_by_id = {
        event_date[0]: event_date
        for event_date in termine
    }

    for ticket in tickets:

        (
            ticket_id,
            date_id,
            _,
            _,
            _,
            _,
            ticket_status,
        ) = ticket

        event_date = date_by_id[
            date_id
        ]

        event_status = event_date[7]

        if (
            ticket_status == "bezahlt"
            and event_status in (
                "abgeschlossen",
                "laufend",
            )
        ):

            # Not every person who paid for a ticket attends.
            if random.random() < 0.85:

                actual_start = event_date[5]

                if actual_start is None:
                    actual_start = event_date[3]

                entry_time = (
                    actual_start
                    + timedelta(
                        minutes=random.randint(
                            -30,
                            20,
                        )
                    )
                )

                entry_status = random.choice(
                    EINLASS_STATUSES
                )

                einlass.append(
                    (
                        entry_id,
                        ticket_id,
                        entry_time,
                        entry_status,
                    )
                )

                entry_id += 1

    # -----------------------------------------------------------------------
    # Stoerung
    # Generate incidents for a fraction of events that have started.
    # -----------------------------------------------------------------------

    stoerungen = []

    incident_id = 1

    for event_date in termine:

        (
            date_id,
            _,
            _,
            planned_start,
            planned_end,
            actual_start,
            actual_end,
            status,
        ) = event_date

        if (
            status in (
                "abgeschlossen",
                "laufend",
            )
            and random.random() < 0.15
        ):

            number_of_incidents = random.randint(
                1,
                2,
            )

            reference_start = (
                actual_start
                or planned_start
            )

            reference_end = (
                actual_end
                or planned_end
            )

            event_duration_minutes = max(
                1,
                (
                    reference_end
                    - reference_start
                ).total_seconds()
                / 60,
            )

            for _ in range(
                number_of_incidents
            ):

                incident_type = random.choice(
                    STOERUNG_TYPES
                )

                duration_minutes = random.randint(
                    5,
                    60,
                )

                start_offset = random.uniform(
                    0,
                    event_duration_minutes,
                )

                incident_start = (
                    reference_start
                    + timedelta(
                        minutes=start_offset
                    )
                )

                incident_end = (
                    incident_start
                    + timedelta(
                        minutes=duration_minutes
                    )
                )

                description = (
                    f"{incident_type} während der Veranstaltung."
                )

                stoerungen.append(
                    (
                        incident_id,
                        date_id,
                        incident_type,
                        incident_start,
                        incident_end,
                        description,
                    )
                )

                incident_id += 1

    return (
        veranstaltungstypen,
        veranstalter,
        orte,
        besucher,
        veranstaltungen,
        termine,
        tickets,
        einlass,
        stoerungen,
    )


# ---------------------------------------------------------------------------
# 5. INTERACTIVE MAIN PROGRAM
# ---------------------------------------------------------------------------

def ask_integer(message, default_value):
    """
    Ask the user for a positive integer.

    If the user enters nothing or an invalid value, the default is used.
    """

    user_input = input(
        f"{message} [{default_value}]: "
    ).strip()

    if user_input == "":
        return default_value

    try:
        return max(
            1,
            int(user_input),
        )

    except ValueError:

        print(
            "  Invalid value. The default value will be used."
        )

        return default_value


def main():
    print(
        "=== Synthetic Data Generator — CityEvents (Dresden) ===\n"
    )

    number_of_venues = ask_integer(
        "How many Veranstaltungsorte do you want to generate?",
        20,
    )

    number_of_organizers = ask_integer(
        "How many Veranstalter do you want to generate?",
        15,
    )

    number_of_events = ask_integer(
        "How many Veranstaltungen do you want to generate?",
        40,
    )

    number_of_dates = ask_integer(
        "How many Veranstaltungstermine do you want to generate?",
        80,
    )

    number_of_visitors = ask_integer(
        "How many Besucher do you want to generate?",
        200,
    )

    number_of_tickets = ask_integer(
        "How many Tickets in total do you want to generate?",
        1000,
    )

    print(
        "\nGenerating data...\n"
    )

    (
        veranstaltungstypen,
        veranstalter,
        orte,
        besucher,
        veranstaltungen,
        termine,
        tickets,
        einlass,
        stoerungen,
    ) = generate_data(
        number_of_venues,
        number_of_organizers,
        number_of_events,
        number_of_dates,
        number_of_visitors,
        number_of_tickets,
    )

    # -----------------------------------------------------------------------
    # Write CSV files
    # -----------------------------------------------------------------------

    print(
        "Writing CSV files:"
    )

    write_csv(
        "cityevents_veranstaltungstyp.csv",
        [
            "id",
            "bezeichnung",
        ],
        veranstaltungstypen,
    )

    write_csv(
        "cityevents_veranstalter.csv",
        [
            "id",
            "name",
            "organisationstyp",
        ],
        veranstalter,
    )

    write_csv(
        "cityevents_veranstaltungsort.csv",
        [
            "id",
            "name",
            "stadtteil",
            "adresse",
            "latitude",
            "longitude",
            "kapazitaet",
        ],
        orte,
    )

    write_csv(
        "cityevents_besucher.csv",
        [
            "id",
            "kundentyp",
            "registrierungsdatum",
        ],
        besucher,
    )

    write_csv(
        "cityevents_veranstaltung.csv",
        [
            "id",
            "name",
            "id_typ",
            "id_veranstalter",
            "beschreibung",
        ],
        veranstaltungen,
    )

    write_csv(
        "cityevents_veranstaltungstermin.csv",
        [
            "id",
            "id_veranstaltung",
            "id_veranstaltungsort",
            "beginn_geplant",
            "ende_geplant",
            "beginn_tatsaechlich",
            "ende_tatsaechlich",
            "status",
        ],
        termine,
    )

    write_csv(
        "cityevents_ticket.csv",
        [
            "id",
            "id_termin",
            "id_besucher",
            "tickettyp",
            "preis",
            "kaufzeitpunkt",
            "status",
        ],
        tickets,
    )

    write_csv(
        "cityevents_einlass.csv",
        [
            "id",
            "id_ticket",
            "einlasszeitpunkt",
            "einlass_status",
        ],
        einlass,
    )

    write_csv(
        "cityevents_stoerung.csv",
        [
            "id",
            "id_termin",
            "typ",
            "beginn",
            "ende",
            "beschreibung",
        ],
        stoerungen,
    )

    # -----------------------------------------------------------------------
    # Write PostgreSQL SQL script
    # -----------------------------------------------------------------------

    sql_file = "cityevents_inserts.sql"

    table_names_in_insert_order = [
        "Veranstaltungstyp",
        "Veranstalter",
        "Veranstaltungsort",
        "Besucher",
        "Veranstaltung",
        "Veranstaltungstermin",
        "Ticket",
        "Einlass",
        "Stoerung",
    ]

    # TRUNCATE is written first.
    # CASCADE handles foreign-key dependencies.
    write_truncate(
        sql_file,
        list(
            reversed(
                table_names_in_insert_order
            )
        ),
    )

    print(
        f"\nWriting SQL script: {sql_file}"
    )

    write_sql(
        sql_file,
        "Veranstaltungstyp",
        [
            "id",
            "bezeichnung",
        ],
        veranstaltungstypen,
    )

    write_sql(
        sql_file,
        "Veranstalter",
        [
            "id",
            "name",
            "organisationstyp",
        ],
        veranstalter,
    )

    write_sql(
        sql_file,
        "Veranstaltungsort",
        [
            "id",
            "name",
            "stadtteil",
            "adresse",
            "latitude",
            "longitude",
            "kapazitaet",
        ],
        orte,
    )

    write_sql(
        sql_file,
        "Besucher",
        [
            "id",
            "kundentyp",
            "registrierungsdatum",
        ],
        besucher,
    )

    write_sql(
        sql_file,
        "Veranstaltung",
        [
            "id",
            "name",
            "id_typ",
            "id_veranstalter",
            "beschreibung",
        ],
        veranstaltungen,
    )

    write_sql(
        sql_file,
        "Veranstaltungstermin",
        [
            "id",
            "id_veranstaltung",
            "id_veranstaltungsort",
            "beginn_geplant",
            "ende_geplant",
            "beginn_tatsaechlich",
            "ende_tatsaechlich",
            "status",
        ],
        termine,
    )

    write_sql(
        sql_file,
        "Ticket",
        [
            "id",
            "id_termin",
            "id_besucher",
            "tickettyp",
            "preis",
            "kaufzeitpunkt",
            "status",
        ],
        tickets,
    )

    write_sql(
        sql_file,
        "Einlass",
        [
            "id",
            "id_ticket",
            "einlasszeitpunkt",
            "einlass_status",
        ],
        einlass,
    )

    write_sql(
        sql_file,
        "Stoerung",
        [
            "id",
            "id_termin",
            "typ",
            "beginn",
            "ende",
            "beschreibung",
        ],
        stoerungen,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    print(
        "\nDone! Summary:"
    )

    print(
        f"  Veranstaltungstypen:   {len(veranstaltungstypen)}"
    )

    print(
        f"  Veranstalter:           {len(veranstalter)}"
    )

    print(
        f"  Veranstaltungsorte:     {len(orte)}"
    )

    print(
        f"  Besucher:               {len(besucher)}"
    )

    print(
        f"  Veranstaltungen:        {len(veranstaltungen)}"
    )

    print(
        f"  Veranstaltungstermine:  {len(termine)}"
    )

    print(
        f"  Tickets:                {len(tickets)}"
    )

    print(
        f"  Einlass:                {len(einlass)}"
    )

    print(
        f"  Stoerungen:             {len(stoerungen)}"
    )

    print(
        f"  Unique coordinates used: {len(USED_COORDINATES)}"
    )


if __name__ == "__main__":
    main()
