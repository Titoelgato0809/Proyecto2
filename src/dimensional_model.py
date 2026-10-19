"""
Modelo dimensional refinado (Segunda Entrega).

Construye las dimensiones, las llaves sustitutas y las dos tablas de
hechos a partir de los DataFrames ya transformados:

    df_icbf -> salida de transform.transformar()
    df_api  -> salida de transform_api.transformar_sisben()

Esquema estrella con dimensiones conformadas:

    fact_atencion               (grano: servicio x perfil x estado x
                                 unidad de servicio x geografia x
                                 municipio x zona)
    fact_vulnerable_population  (grano: municipio x zona x grupo Sisben)

dim_municipality y dim_zone son compartidas por ambos hechos. El cruce
entre fuentes se hace por drill-across sobre esas dimensiones, nunca
uniendo un hecho con el otro (multiplicaria la poblacion).

Solo se almacenan medidas aditivas. Las razones (cobertura por 1.000
personas, brecha urbano-rural) se calculan en vistas o en el dashboard.
"""

import pandas as pd


# =============================================================
# CONSTANTES DEL MODELO
# =============================================================

ZONAS = [
    # (nombre_zona, codigo_zona_sisben)
    ("CABECERA", 1),
    ("RESTO", 2),
    ("SIN INFORMACIÓN", None),   # el Sisbén no tiene este valor
]

GRUPOS_SISBEN = [
    ("A", "Pobreza extrema"),
    ("B", "Pobreza moderada"),
]

# ASUMIDO: confirmar la descripción con el diccionario del ICBF.
ESTADOS_ATENCION = [
    ("A", "Atención activa"),
    ("I", "Atención inactiva"),
]

SIN_NOMBRE = "SIN NOMBRE"


# =============================================================
# UTILIDADES
# =============================================================

def _texto(serie):
    """Categoricas -> texto, para poder deduplicar y unir."""
    return serie.astype("string")


def _dimension(df, columnas, nombre_llave):
    """Dimension con llave sustituta determinista (1..n)."""
    dim = (
        df[columnas]
        .astype({c: "string" for c in columnas
                 if str(df[c].dtype) in ("category", "object")})
        .drop_duplicates()
        .sort_values(columnas, na_position="last")
        .reset_index(drop=True)
    )
    dim.insert(0, nombre_llave, range(1, len(dim) + 1))
    return dim


def _asignar_llave(hechos, dim, columnas, llave):
    """
    Une el hecho con la dimension por sus atributos naturales.
    Una llave sin dimension es un defecto de integridad: se detiene.
    """
    hechos = hechos.copy()
    for c in columnas:
        if str(hechos[c].dtype) in ("category", "object"):
            hechos[c] = hechos[c].astype("string")

    union = hechos.merge(
        dim[[llave] + columnas],
        on=columnas,
        how="left",
        validate="many_to_one",
    )
    if union[llave].isna().any():
        raise ValueError(
            f"{int(union[llave].isna().sum())} filas sin {llave}: "
            f"integridad referencial rota."
        )
    return union


# =============================================================
# DIMENSIONES DEL ICBF (sin cambios respecto a la primera entrega,
# salvo dim_beneficiary_profile, que ya no tiene la zona)
# =============================================================

def construir_dim_geography(df_icbf):
    return _dimension(
        df_icbf.rename(columns={
            "Codigo Departamento UDS": "codigo_departamento_uds",
            "Departamento UDS": "departamento_uds",
            "Codigo Municipio UDS": "codigo_municipio_uds",
            "Municipio UDS": "municipio_uds",
            "Codigo CentroZonal UDS": "codigo_centrozonal_uds",
            "Centro Zonal UDS": "centro_zonal_uds",
        }),
        ["codigo_departamento_uds", "departamento_uds",
         "codigo_municipio_uds", "municipio_uds",
         "codigo_centrozonal_uds", "centro_zonal_uds"],
        "geography_key",
    )


def construir_dim_service_unit(df_icbf):
    return _dimension(
        df_icbf.rename(columns={
            "Codigo Unidad Servicio": "codigo_unidad_servicio",
            "Unidad Servicio": "unidad_servicio",
            "Estado UDS": "estado_uds",
        }),
        ["codigo_unidad_servicio", "unidad_servicio", "estado_uds"],
        "service_unit_key",
    )


def construir_dim_service(df_icbf):
    return _dimension(
        df_icbf.rename(columns={
            "Nombre Servicio": "nombre_servicio",
            "Tipo Servicio": "tipo_servicio",
        }),
        ["nombre_servicio", "tipo_servicio"],
        "service_key",
    )


def construir_dim_beneficiary_profile(df_icbf):
    """Sin zona: la zona pasa a dim_zone (eje conformado)."""
    return _dimension(
        df_icbf.rename(columns={
            "Sexo": "sexo",
            "Rango Edad": "rango_edad",
            "Grupo Etnico": "grupo_etnico",
            "Presenta Discapacidad": "presenta_discapacidad",
            "Tipo de Beneficiario": "tipo_de_beneficiario",
            "Pais Nacimiento": "pais_nacimiento",
        }),
        ["sexo", "rango_edad", "grupo_etnico",
         "presenta_discapacidad", "tipo_de_beneficiario",
         "pais_nacimiento"],
        "beneficiary_profile_key",
    )


def construir_dim_attention_status():
    dim = pd.DataFrame(ESTADOS_ATENCION,
                       columns=["estado_atencion", "descripcion"])
    dim.insert(0, "attention_status_key", range(1, len(dim) + 1))
    return dim


# =============================================================
# DIMENSIONES NUEVAS (conformadas)
# =============================================================

def construir_dim_municipality(df_icbf, df_api):
    """
    Una fila por codigo DANE. Nombre y departamento salen del ICBF.
    Un codigo que existe solo en la API se carga como SIN NOMBRE y
    se reporta (no se inventa el nombre).
    """
    icbf = pd.DataFrame({
        "codigo_municipio_dane": _texto(df_icbf["Codigo Municipio DANE"]),
        "municipio": _texto(df_icbf["Municipio UDS"]),
        "codigo_departamento": _texto(
            df_icbf["Codigo Departamento UDS"]).str.zfill(2),
        "departamento": _texto(df_icbf["Departamento UDS"]),
    }).drop_duplicates()

    duplicados = icbf["codigo_municipio_dane"].duplicated(keep=False)
    if duplicados.any():
        raise ValueError(
            "Un mismo codigo DANE tiene mas de un nombre en el ICBF: "
            f"{sorted(icbf.loc[duplicados, 'codigo_municipio_dane'].unique())}"
        )

    solo_api = sorted(
        set(df_api["codigo_municipio_dane"]) -
        set(icbf["codigo_municipio_dane"])
    )
    api = pd.DataFrame({
        "codigo_municipio_dane": solo_api,
        "municipio": SIN_NOMBRE,
        "codigo_departamento": [c[:2] for c in solo_api],
        "departamento": SIN_NOMBRE,
    })

    dim = (
        pd.concat([icbf, api], ignore_index=True)
        .astype("string")
        .sort_values("codigo_municipio_dane")
        .reset_index(drop=True)
    )
    dim.insert(0, "municipality_key", range(1, len(dim) + 1))
    return dim


def construir_dim_zone():
    dim = pd.DataFrame(ZONAS, columns=["nombre_zona", "codigo_zona_sisben"])
    dim["codigo_zona_sisben"] = dim["codigo_zona_sisben"].astype("Int64")
    dim.insert(0, "zone_key", range(1, len(dim) + 1))
    return dim


def construir_dim_sisben_group():
    dim = pd.DataFrame(GRUPOS_SISBEN, columns=["grupo", "descripcion"])
    dim.insert(0, "sisben_group_key", range(1, len(dim) + 1))
    return dim


# =============================================================
# TABLAS DE HECHOS
# =============================================================

def construir_fact_atencion(df_icbf, dims):
    """
    Grano: una fila por combinacion de las siete llaves.
    Medida aditiva: total_beneficiarios.
    """
    h = df_icbf.rename(columns={
        "Codigo Departamento UDS": "codigo_departamento_uds",
        "Departamento UDS": "departamento_uds",
        "Codigo Municipio UDS": "codigo_municipio_uds",
        "Municipio UDS": "municipio_uds",
        "Codigo CentroZonal UDS": "codigo_centrozonal_uds",
        "Centro Zonal UDS": "centro_zonal_uds",
        "Codigo Unidad Servicio": "codigo_unidad_servicio",
        "Unidad Servicio": "unidad_servicio",
        "Estado UDS": "estado_uds",
        "Nombre Servicio": "nombre_servicio",
        "Tipo Servicio": "tipo_servicio",
        "Sexo": "sexo",
        "Rango Edad": "rango_edad",
        "Grupo Etnico": "grupo_etnico",
        "Presenta Discapacidad": "presenta_discapacidad",
        "Tipo de Beneficiario": "tipo_de_beneficiario",
        "Pais Nacimiento": "pais_nacimiento",
        "Estado Atención": "estado_atencion",
        "Zona Ubicacion Beneficiario": "nombre_zona",
        "Codigo Municipio DANE": "codigo_municipio_dane",
        "Beneficiarios": "total_beneficiarios",
    })

    specs = [
        ("dim_geography", "geography_key", [
            "codigo_departamento_uds", "departamento_uds",
            "codigo_municipio_uds", "municipio_uds",
            "codigo_centrozonal_uds", "centro_zonal_uds"]),
        ("dim_service_unit", "service_unit_key", [
            "codigo_unidad_servicio", "unidad_servicio", "estado_uds"]),
        ("dim_service", "service_key", [
            "nombre_servicio", "tipo_servicio"]),
        ("dim_beneficiary_profile", "beneficiary_profile_key", [
            "sexo", "rango_edad", "grupo_etnico",
            "presenta_discapacidad", "tipo_de_beneficiario",
            "pais_nacimiento"]),
        ("dim_attention_status", "attention_status_key",
            ["estado_atencion"]),
        ("dim_municipality", "municipality_key",
            ["codigo_municipio_dane"]),
        ("dim_zone", "zone_key", ["nombre_zona"]),
    ]

    for nombre_dim, llave, columnas in specs:
        h = _asignar_llave(h, dims[nombre_dim], columnas, llave)

    llaves = [s[1] for s in specs]
    fact = (
        h.groupby(llaves, as_index=False, dropna=False)
        ["total_beneficiarios"].sum()
    )
    fact.insert(0, "fact_key", range(1, len(fact) + 1))
    return fact[["fact_key"] + llaves + ["total_beneficiarios"]]


def construir_fact_vulnerable_population(df_api, dims):
    """
    Grano: municipio x zona x grupo Sisben, para un corte.
    Medidas aditivas: poblacion_ponderada y registros_muestrales.
    """
    h = df_api.rename(columns={})
    h = _asignar_llave(
        h, dims["dim_municipality"], ["codigo_municipio_dane"],
        "municipality_key")
    h = _asignar_llave(h, dims["dim_zone"], ["nombre_zona"], "zone_key")
    h = _asignar_llave(
        h, dims["dim_sisben_group"], ["grupo"], "sisben_group_key")

    llaves = ["municipality_key", "zone_key", "sisben_group_key"]
    if h.duplicated(llaves).any():
        raise ValueError(
            "Grano duplicado en fact_vulnerable_population "
            "(municipio x zona x grupo)."
        )

    fact = h[llaves + ["poblacion_ponderada",
                       "registros_muestrales",
                       "corte_fuente"]].copy()
    fact = fact.sort_values(llaves).reset_index(drop=True)
    fact.insert(0, "fact_population_key", range(1, len(fact) + 1))
    return fact


# =============================================================
# ORQUESTACION Y REPORTE DE INTEGRACION
# =============================================================

def reporte_integracion(df_icbf, df_api, dims, fact_atencion):
    """
    Mide lo que pide el contrato (13.1): registros sin cruce y
    zona sin informacion. Solo mide; la decision de detener o
    continuar la toma la validacion de datos preparados.
    """
    codigos_icbf = set(_texto(df_icbf["Codigo Municipio DANE"]))
    codigos_api = set(df_api["codigo_municipio_dane"])

    benef = (
        df_icbf.assign(_c=_texto(df_icbf["Codigo Municipio DANE"]))
        .groupby("_c")["Beneficiarios"].sum()
    )
    total = benef.sum()
    con_cruce = benef[benef.index.isin(codigos_api)].sum()

    zona_sin = df_icbf.loc[
        df_icbf["Zona Ubicacion Beneficiario"].astype("string")
        == "SIN INFORMACIÓN", "Beneficiarios"].sum()

    return {
        "municipios_icbf": len(codigos_icbf),
        "municipios_icbf_con_cruce": len(codigos_icbf & codigos_api),
        "municipios_icbf_sin_cruce": sorted(codigos_icbf - codigos_api),
        "municipios_solo_api": sorted(codigos_api - codigos_icbf),
        "pct_beneficiarios_con_cruce": float(con_cruce / total * 100),
        "pct_beneficiarios_zona_sin_informacion":
            float(zona_sin / total * 100),
        "total_beneficiarios_icbf": int(total),
        "total_beneficiarios_fact": int(
            fact_atencion["total_beneficiarios"].sum()),
    }


def construir_modelo(df_icbf, df_api):
    """Devuelve (tablas, reporte). tablas es un dict nombre -> DataFrame."""
    dims = {
        "dim_geography": construir_dim_geography(df_icbf),
        "dim_service_unit": construir_dim_service_unit(df_icbf),
        "dim_service": construir_dim_service(df_icbf),
        "dim_beneficiary_profile":
            construir_dim_beneficiary_profile(df_icbf),
        "dim_attention_status": construir_dim_attention_status(),
        "dim_municipality": construir_dim_municipality(df_icbf, df_api),
        "dim_zone": construir_dim_zone(),
        "dim_sisben_group": construir_dim_sisben_group(),
    }

    fact_atencion = construir_fact_atencion(df_icbf, dims)
    fact_pob = construir_fact_vulnerable_population(df_api, dims)

    tablas = {
        **dims,
        "fact_atencion": fact_atencion,
        "fact_vulnerable_population": fact_pob,
    }
    reporte = reporte_integracion(df_icbf, df_api, dims, fact_atencion)
    return tablas, reporte