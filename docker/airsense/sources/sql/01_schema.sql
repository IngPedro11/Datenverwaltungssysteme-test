CREATE SCHEMA airsense;


-- 1. Zuerst: Station

CREATE TABLE airsense.Station (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100),
    stadtteil VARCHAR(100),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    stations_typ VARCHAR(30),
    installationsdatum DATE,
    status VARCHAR(20)
);


-- 2. Zweitens: Sensor

CREATE TABLE airsense.Sensor (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_station BIGINT,
    sensortyp VARCHAR(50),
    hersteller VARCHAR(50),
    modell VARCHAR(50),
    einheit VARCHAR(20),
    installationsdatum DATE,
    status VARCHAR(20),

    FOREIGN KEY (id_station)
        REFERENCES airsense.Station(id)
);


-- 3. Drittens: Messung

CREATE TABLE airsense.Messung (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sensor BIGINT,
    messzeitpunkt TIMESTAMP,
    messwert DECIMAL(10,2),
    qualitaetsstatus VARCHAR(20),

    FOREIGN KEY (id_sensor)
        REFERENCES airsense.Sensor(id)
);


-- 4. Viertens: Sensorwartung

CREATE TABLE airsense.Sensorwartung (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sensor BIGINT,
    beginn TIMESTAMP,
    ende TIMESTAMP,
    wartungsart VARCHAR(50),
    kosten DECIMAL(10,2),
    beschreibung VARCHAR(255),

    FOREIGN KEY (id_sensor)
        REFERENCES airsense.Sensor(id)
);
