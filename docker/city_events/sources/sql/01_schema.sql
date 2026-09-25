CREATE SCHEMA cityevents;


-- 1. Zuerst: Tabellen ohne Foreign Keys

CREATE TABLE cityevents.Veranstaltungstyp (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung VARCHAR(50)
);

CREATE TABLE cityevents.Veranstalter (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    organisationstyp VARCHAR(50)
);

CREATE TABLE cityevents.Veranstaltungsort (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    stadtteil VARCHAR(100),
    adresse VARCHAR(150),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    kapazitaet INT
);

CREATE TABLE cityevents.Besucher (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kundentyp VARCHAR(30),
    registrierungsdatum DATE
);


-- 2. Zweitens: Veranstaltung

CREATE TABLE cityevents.Veranstaltung (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    id_typ BIGINT,
    id_veranstalter BIGINT,
    beschreibung VARCHAR(255),

    FOREIGN KEY (id_typ)
        REFERENCES cityevents.Veranstaltungstyp(id),

    FOREIGN KEY (id_veranstalter)
        REFERENCES cityevents.Veranstalter(id)
);


-- 3. Drittens: Veranstaltungstermin

CREATE TABLE cityevents.Veranstaltungstermin (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_veranstaltung BIGINT,
    id_veranstaltungsort BIGINT,
    beginn_geplant TIMESTAMP,
    ende_geplant TIMESTAMP,
    beginn_tatsaechlich TIMESTAMP,
    ende_tatsaechlich TIMESTAMP,
    status VARCHAR(30),

    FOREIGN KEY (id_veranstaltung)
        REFERENCES cityevents.Veranstaltung(id),

    FOREIGN KEY (id_veranstaltungsort)
        REFERENCES cityevents.Veranstaltungsort(id)
);


-- 4. Viertens: Ticket

CREATE TABLE cityevents.Ticket (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_termin BIGINT,
    id_besucher BIGINT,
    tickettyp VARCHAR(30),
    preis DECIMAL(10,2),
    kaufzeitpunkt TIMESTAMP,
    status VARCHAR(20),

    FOREIGN KEY (id_termin)
        REFERENCES cityevents.Veranstaltungstermin(id),

    FOREIGN KEY (id_besucher)
        REFERENCES cityevents.Besucher(id)
);


-- 5. Fünftens: Einlass

CREATE TABLE cityevents.Einlass (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ticket BIGINT,
    einlasszeitpunkt TIMESTAMP,
    einlass_status VARCHAR(20),

    FOREIGN KEY (id_ticket)
        REFERENCES cityevents.Ticket(id)
);


-- 6. Sechstens: Stoerung

CREATE TABLE cityevents.Stoerung (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_termin BIGINT,
    typ VARCHAR(50),
    beginn TIMESTAMP,
    ende TIMESTAMP,
    beschreibung VARCHAR(255),

    FOREIGN KEY (id_termin)
        REFERENCES cityevents.Veranstaltungstermin(id)
);
