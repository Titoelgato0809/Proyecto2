-- =========================================================
-- DIMENSIÓN GEOGRAFÍA
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_geography (
    geography_key SERIAL PRIMARY KEY,

    codigo_departamento_uds INT NOT NULL,
    departamento_uds VARCHAR(100) NOT NULL,

    codigo_municipio_uds INT NOT NULL,
    municipio_uds VARCHAR(150) NOT NULL,

    codigo_centrozonal_uds INT NOT NULL,
    centro_zonal_uds VARCHAR(150) NOT NULL
);


-- =========================================================
-- DIMENSIÓN UNIDAD DE SERVICIO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_service_unit (
    service_unit_key SERIAL PRIMARY KEY,

    codigo_unidad_servicio BIGINT NOT NULL,
    unidad_servicio VARCHAR(255) NOT NULL,
    estado_uds VARCHAR(30) NOT NULL
);


-- =========================================================
-- DIMENSIÓN SERVICIO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_service (
    service_key SERIAL PRIMARY KEY,

    nombre_servicio VARCHAR(255) NOT NULL,
    tipo_servicio VARCHAR(100) NOT NULL
);


-- =========================================================
-- DIMENSIÓN PERFIL DEL BENEFICIARIO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_beneficiary_profile (
    beneficiary_profile_key SERIAL PRIMARY KEY,

    sexo VARCHAR(5) NOT NULL,
    rango_edad VARCHAR(50) NOT NULL,
    grupo_etnico VARCHAR(100) NOT NULL,
    presenta_discapacidad VARCHAR(5) NOT NULL,
    zona_ubicacion VARCHAR(30) NOT NULL,
    tipo_beneficiario VARCHAR(150) NOT NULL,
    pais_nacimiento VARCHAR(100) NOT NULL
);


-- =========================================================
-- DIMENSIÓN ESTADO DE ATENCIÓN
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_attention_status (
    attention_status_key SERIAL PRIMARY KEY,

    estado_atencion VARCHAR(50) NOT NULL,
    descripcion VARCHAR(100) NOT NULL
);


-- =========================================================
-- TABLA DE HECHOS
-- =========================================================

CREATE TABLE IF NOT EXISTS fact_atencion (
    fact_key SERIAL PRIMARY KEY,

    geography_key INT NOT NULL,
    service_unit_key INT NOT NULL,
    service_key INT NOT NULL,
    beneficiary_profile_key INT NOT NULL,
    attention_status_key INT NOT NULL,

    total_beneficiarios INT NOT NULL,

    FOREIGN KEY (geography_key)
        REFERENCES dim_geography(geography_key),

    FOREIGN KEY (service_unit_key)
        REFERENCES dim_service_unit(service_unit_key),

    FOREIGN KEY (service_key)
        REFERENCES dim_service(service_key),

    FOREIGN KEY (beneficiary_profile_key)
        REFERENCES dim_beneficiary_profile(beneficiary_profile_key),

    FOREIGN KEY (attention_status_key)
        REFERENCES dim_attention_status(attention_status_key)
);