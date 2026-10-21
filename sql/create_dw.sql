-- =====================================================================
-- Data Warehouse ICBF + Sisbén (Segunda Entrega) - PostgreSQL
-- Esquema estrella con dimensiones conformadas (dim_municipality y
-- dim_zone son compartidas por los dos hechos).
--
-- ATENCIÓN: este script ELIMINA y recrea las diez tablas. Reemplaza el
-- esquema de la primera entrega (fact_atencion y dim_beneficiary_profile
-- cambiaron). Las cargas posteriores NO lo ejecutan: usan DELETE.
-- =====================================================================

DROP TABLE IF EXISTS fact_vulnerable_population CASCADE;
DROP TABLE IF EXISTS fact_atencion CASCADE;
DROP TABLE IF EXISTS dim_sisben_group CASCADE;
DROP TABLE IF EXISTS dim_zone CASCADE;
DROP TABLE IF EXISTS dim_municipality CASCADE;
DROP TABLE IF EXISTS dim_attention_status CASCADE;
DROP TABLE IF EXISTS dim_beneficiary_profile CASCADE;
DROP TABLE IF EXISTS dim_service CASCADE;
DROP TABLE IF EXISTS dim_service_unit CASCADE;
DROP TABLE IF EXISTS dim_geography CASCADE;

-- ---------------------------------------------------------------------
-- Dimensiones del ICBF
-- ---------------------------------------------------------------------

CREATE TABLE dim_geography (
    geography_key           INTEGER      NOT NULL,
    codigo_departamento_uds INTEGER      NOT NULL,
    departamento_uds        VARCHAR(150),
    codigo_municipio_uds    INTEGER      NOT NULL,
    municipio_uds           VARCHAR(150),
    codigo_centrozonal_uds  INTEGER      NOT NULL,
    centro_zonal_uds        VARCHAR(255),
    CONSTRAINT pk_dim_geography PRIMARY KEY (geography_key)
);

CREATE TABLE dim_service_unit (
    service_unit_key        INTEGER      NOT NULL,
    codigo_unidad_servicio  BIGINT       NOT NULL,
    unidad_servicio         VARCHAR(255),
    estado_uds              VARCHAR(30),
    CONSTRAINT pk_dim_service_unit PRIMARY KEY (service_unit_key)
);

CREATE TABLE dim_service (
    service_key             INTEGER      NOT NULL,
    nombre_servicio         VARCHAR(255),
    tipo_servicio           VARCHAR(60),
    CONSTRAINT pk_dim_service PRIMARY KEY (service_key)
);

-- La zona ya NO está aquí: pasó a dim_zone (eje conformado).
CREATE TABLE dim_beneficiary_profile (
    beneficiary_profile_key INTEGER      NOT NULL,
    sexo                    VARCHAR(20),
    rango_edad              VARCHAR(100),
    grupo_etnico            VARCHAR(255),
    presenta_discapacidad   VARCHAR(20),
    tipo_de_beneficiario    VARCHAR(255),
    pais_nacimiento         VARCHAR(255),
    CONSTRAINT pk_dim_beneficiary_profile PRIMARY KEY (beneficiary_profile_key)
);

CREATE TABLE dim_attention_status (
    attention_status_key    INTEGER      NOT NULL,
    estado_atencion         CHAR(1)      NOT NULL,
    descripcion             VARCHAR(60),
    CONSTRAINT pk_dim_attention_status PRIMARY KEY (attention_status_key),
    CONSTRAINT uq_attention_status UNIQUE (estado_atencion)
);

-- ---------------------------------------------------------------------
-- Dimensiones nuevas (conformadas)
-- ---------------------------------------------------------------------

CREATE TABLE dim_municipality (
    municipality_key        INTEGER      NOT NULL,
    codigo_municipio_dane   CHAR(5)      NOT NULL,
    municipio               VARCHAR(150),
    codigo_departamento     CHAR(2)      NOT NULL,
    departamento            VARCHAR(150),
    CONSTRAINT pk_dim_municipality PRIMARY KEY (municipality_key),
    CONSTRAINT uq_municipality_dane UNIQUE (codigo_municipio_dane),
    CONSTRAINT ck_municipality_dane CHECK (codigo_municipio_dane ~ '^[0-9]{5}$')
);

CREATE TABLE dim_zone (
    zone_key                INTEGER      NOT NULL,
    nombre_zona             VARCHAR(30)  NOT NULL,
    codigo_zona_sisben      SMALLINT,              -- NULL en SIN INFORMACIÓN
    CONSTRAINT pk_dim_zone PRIMARY KEY (zone_key),
    CONSTRAINT uq_zone_nombre UNIQUE (nombre_zona)
);

CREATE TABLE dim_sisben_group (
    sisben_group_key        INTEGER      NOT NULL,
    grupo                   CHAR(1)      NOT NULL,
    descripcion             VARCHAR(60),
    CONSTRAINT pk_dim_sisben_group PRIMARY KEY (sisben_group_key),
    CONSTRAINT uq_sisben_grupo UNIQUE (grupo)
);

-- ---------------------------------------------------------------------
-- Hechos
-- ---------------------------------------------------------------------

-- Grano: una fila por combinación de las siete llaves.
CREATE TABLE fact_atencion (
    fact_key                INTEGER NOT NULL,
    geography_key           INTEGER NOT NULL,
    service_unit_key        INTEGER NOT NULL,
    service_key             INTEGER NOT NULL,
    beneficiary_profile_key INTEGER NOT NULL,
    attention_status_key    INTEGER NOT NULL,
    municipality_key        INTEGER NOT NULL,
    zone_key                INTEGER NOT NULL,
    total_beneficiarios     INTEGER NOT NULL,
    CONSTRAINT pk_fact_atencion PRIMARY KEY (fact_key),
    CONSTRAINT uq_fact_atencion_grano UNIQUE (
        geography_key, service_unit_key, service_key,
        beneficiary_profile_key, attention_status_key,
        municipality_key, zone_key),
    CONSTRAINT ck_fa_beneficiarios CHECK (total_beneficiarios >= 0),
    CONSTRAINT fk_fa_geography FOREIGN KEY (geography_key)
        REFERENCES dim_geography (geography_key),
    CONSTRAINT fk_fa_service_unit FOREIGN KEY (service_unit_key)
        REFERENCES dim_service_unit (service_unit_key),
    CONSTRAINT fk_fa_service FOREIGN KEY (service_key)
        REFERENCES dim_service (service_key),
    CONSTRAINT fk_fa_profile FOREIGN KEY (beneficiary_profile_key)
        REFERENCES dim_beneficiary_profile (beneficiary_profile_key),
    CONSTRAINT fk_fa_status FOREIGN KEY (attention_status_key)
        REFERENCES dim_attention_status (attention_status_key),
    CONSTRAINT fk_fa_municipality FOREIGN KEY (municipality_key)
        REFERENCES dim_municipality (municipality_key),
    CONSTRAINT fk_fa_zone FOREIGN KEY (zone_key)
        REFERENCES dim_zone (zone_key)
);

-- Grano: municipio x zona x grupo Sisbén, para un corte.
CREATE TABLE fact_vulnerable_population (
    fact_population_key     INTEGER       NOT NULL,
    municipality_key        INTEGER       NOT NULL,
    zone_key                INTEGER       NOT NULL,
    sisben_group_key        INTEGER       NOT NULL,
    poblacion_ponderada     NUMERIC(16,4) NOT NULL,
    registros_muestrales    INTEGER       NOT NULL,
    corte_fuente            VARCHAR(20)   NOT NULL,
    CONSTRAINT pk_fact_vulnerable_population PRIMARY KEY (fact_population_key),
    CONSTRAINT uq_fact_poblacion_grano UNIQUE (
        municipality_key, zone_key, sisben_group_key),
    CONSTRAINT ck_fp_poblacion CHECK (poblacion_ponderada > 0),
    CONSTRAINT ck_fp_registros CHECK (registros_muestrales >= 1),
    CONSTRAINT fk_fp_municipality FOREIGN KEY (municipality_key)
        REFERENCES dim_municipality (municipality_key),
    CONSTRAINT fk_fp_zone FOREIGN KEY (zone_key)
        REFERENCES dim_zone (zone_key),
    CONSTRAINT fk_fp_group FOREIGN KEY (sisben_group_key)
        REFERENCES dim_sisben_group (sisben_group_key)
);

-- Índices sobre las llaves foráneas de los hechos (PostgreSQL no los crea
-- automáticamente; aceleran los joins del dashboard y las vistas).
CREATE INDEX ix_fa_geography     ON fact_atencion (geography_key);
CREATE INDEX ix_fa_service_unit  ON fact_atencion (service_unit_key);
CREATE INDEX ix_fa_service       ON fact_atencion (service_key);
CREATE INDEX ix_fa_profile       ON fact_atencion (beneficiary_profile_key);
CREATE INDEX ix_fa_municipality  ON fact_atencion (municipality_key);
CREATE INDEX ix_fa_zone          ON fact_atencion (zone_key);
CREATE INDEX ix_fp_zone          ON fact_vulnerable_population (zone_key);
CREATE INDEX ix_fp_group         ON fact_vulnerable_population (sisben_group_key);