
CREATE SCHEMA bikeshare;

-- 1. Zuerst: Tabellen ohne Foreign Keys

CREATE TABLE bikeshare.Fahrradmodell (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hersteller VARCHAR(50),
    bezeichnung VARCHAR(50),
    fahrradtyp VARCHAR(30),
    baujahr INT
);

CREATE TABLE bikeshare.Station (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    stadtteil VARCHAR(100),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    kapazitaet INT
);

CREATE TABLE bikeshare.Kunde (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registrierungsdatum DATE,
    kundentyp VARCHAR(30)
);

CREATE TABLE bikeshare.Tarif (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung VARCHAR(50),
    grundgebuehr DECIMAL(10,2),
    preis_pro_minute DECIMAL(10,2),
    gueltig_ab DATE,
    gueltig_bis DATE
);


-- 2. Zweitens: Fahrrad

CREATE TABLE bikeshare.Fahrrad (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_modell INT,
    inventarnummer VARCHAR(30),
    anschaffungsdatum DATE,
    status VARCHAR(20),

    FOREIGN KEY (id_modell)
        REFERENCES bikeshare.Fahrradmodell(id)
);


-- 3. Drittens: Fahrt

CREATE TABLE bikeshare.Fahrt (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_kunde INT,
    id_fahrrad INT,
    id_startstation INT,
    id_zielstation INT,
    id_tarif INT,
    startzeit TIMESTAMP,
    endzeit TIMESTAMP,
    fahrtdauer_min INT,
    status VARCHAR(20),

    FOREIGN KEY (id_kunde)
        REFERENCES bikeshare.Kunde(id),

    FOREIGN KEY (id_fahrrad)
        REFERENCES bikeshare.Fahrrad(id),

    FOREIGN KEY (id_startstation)
        REFERENCES bikeshare.Station(id),

    FOREIGN KEY (id_zielstation)
        REFERENCES bikeshare.Station(id),

    FOREIGN KEY (id_tarif)
        REFERENCES bikeshare.Tarif(id)
);

-- 4. Viertens: Zahlung

CREATE TABLE bikeshare.Zahlung (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrt INT,
    zahlungszeitpunkt TIMESTAMP,
    betrag DECIMAL(10,2),
    zahlungsart VARCHAR(30),
    status VARCHAR(20),

    FOREIGN KEY (id_fahrt)
        REFERENCES bikeshare.Fahrt(id)
);


-- 4. Viertens: Wartung

CREATE TABLE bikeshare.Wartung (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_fahrrad INT,
    beginn TIMESTAMP,
    ende TIMESTAMP,
    wartungsart VARCHAR(50),
    kosten DECIMAL(10,2),
    beschreibung VARCHAR(255),

    FOREIGN KEY (id_fahrrad)
        REFERENCES bikeshare.Fahrrad(id)

);
