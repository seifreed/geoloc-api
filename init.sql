-- Torres celulares (formato OpenCelliD)
CREATE TABLE IF NOT EXISTS cells (
  radio   VARCHAR(8)  NOT NULL,   -- GSM/UMTS/LTE/NR
  mcc     SMALLINT    NOT NULL,
  mnc     SMALLINT    NOT NULL,   -- 'net' en el CSV
  area    INT         NOT NULL,   -- LAC / TAC
  cid     BIGINT      NOT NULL,
  lon     DOUBLE      NOT NULL,
  lat     DOUBLE      NOT NULL,
  `range` INT         DEFAULT 0,
  samples INT         DEFAULT 0,
  pt POINT  NOT NULL,             -- relleno por trigger; para /nearest
  PRIMARY KEY (radio, mcc, mnc, area, cid),
  SPATIAL INDEX (pt)
);
-- En MariaDB una columna generada no puede ser NOT NULL y el indice espacial lo exige,
-- asi que poblamos pt con un trigger (el loader sigue insertando solo lon/lat).
CREATE TRIGGER cells_pt BEFORE INSERT ON cells
  FOR EACH ROW SET NEW.pt = POINT(NEW.lon, NEW.lat);

-- APs WiFi (formato WiGLE / wardriving propio)
CREATE TABLE IF NOT EXISTS wifi (
  bssid VARCHAR(17) NOT NULL,     -- MAC AA:BB:CC:DD:EE:FF
  ssid  VARCHAR(64),
  lon   DOUBLE NOT NULL,
  lat   DOUBLE NOT NULL,
  pt POINT NOT NULL,              -- relleno por trigger; para /nearest
  PRIMARY KEY (bssid),
  SPATIAL INDEX (pt)
);
CREATE TRIGGER wifi_pt BEFORE INSERT ON wifi
  FOR EACH ROW SET NEW.pt = POINT(NEW.lon, NEW.lat);
