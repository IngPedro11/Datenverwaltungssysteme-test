CREATE SCHEMA citymove;

CREATE TABLE citymove.Modell (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hersteller VARCHAR(50),
    bezeichnung VARCHAR(50),
    fahrzeugtyp VARCHAR(30),
    baujahr INT
);

CREATE TABLE citymove.Linie (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    liniennummer VARCHAR(10),
    bezeichnung VARCHAR(100),
    verkehrsmittel VARCHAR(20),
    gueltig_ab DATE,
    gueltig_bis DATE
);

CREATE TABLE citymove.Haltestelle (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    stadtteil VARCHAR(100),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7)
);

CREATE TABLE citymove.Fahrzeug (
    id INT GENERATED ALWAYS AS IDENTITY  PRIMARY KEY,
    id_modell INT,
    fahrzeugnummer VARCHAR(20),
    kapazitaet INT,
    antriebsart VARCHAR(30),
    inbetriebnahme DATE,
    status VARCHAR(20),

    FOREIGN KEY (id_modell)
        REFERENCES citymove.Modell(id)
);

CREATE TABLE citymove.Linien_Haltestelle (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_linie INT,
    id_haltestelle INT,
    reihenfolge INT,
    fahrtrichtung VARCHAR(50),

    FOREIGN KEY (id_linie)
        REFERENCES citymove.Linie(id),

    FOREIGN KEY (id_haltestelle)
        REFERENCES citymove.Haltestelle(id)
);

CREATE TABLE citymove.Fahrt (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_linie INT,
    id_fahrzeug INT,
    datum DATE,
    fahrtrichtung VARCHAR(50),
    fahrten_status VARCHAR(20),

    FOREIGN KEY (id_linie)
        REFERENCES citymove.Linie(id),

    FOREIGN KEY (id_fahrzeug)
        REFERENCES citymove.Fahrzeug(id)
);

CREATE TABLE citymove.Fahrplan (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrt INT,
    id_haltestelle INT,
    ankunft_geplant TIMESTAMP,
    abfahrt_geplant TIMESTAMP,

    FOREIGN KEY (id_fahrt)
        REFERENCES citymove.Fahrt(id),

    FOREIGN KEY (id_haltestelle)
        REFERENCES citymove.Haltestelle(id)
);

CREATE TABLE citymove.Fahrt_Haltestelle (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrt INT,
    id_haltestelle INT,
    ankunft_tatsaechlich TIMESTAMP,
    abfahrt_tatsaechlich TIMESTAMP,

    FOREIGN KEY (id_fahrt)
        REFERENCES citymove.Fahrt(id),

    FOREIGN KEY (id_haltestelle)
        REFERENCES citymove.Haltestelle(id)
);

CREATE TABLE citymove.Fahrgastaufkommen (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrt INT,
    id_haltestelle INT,
    einsteiger INT,
    aussteiger INT,

    FOREIGN KEY (id_fahrt)
        REFERENCES citymove.Fahrt(id),

    FOREIGN KEY (id_haltestelle)
        REFERENCES citymove.Haltestelle(id)
);

CREATE TABLE citymove.Stoerung (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrt INT,
    id_haltestelle INT,
    typ VARCHAR(50),
    beginn TIMESTAMP,
    ende TIMESTAMP,
    dauer_min INT,
    beschreibung VARCHAR(255),

    FOREIGN KEY (id_fahrt)
        REFERENCES citymove.Fahrt(id),

    FOREIGN KEY (id_haltestelle)
        REFERENCES citymove.Haltestelle(id)
);
