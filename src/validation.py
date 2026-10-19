"""
Compuerta 3: validación de datos preparados (Prepared Data Validation).

Se ejecuta DESPUÉS de transformar y de construir el modelo:

    df_icbf, df_api = transformar_fuentes(raw_icbf, raw_api)
    tablas, reporte = construir_modelo(df_icbf, df_api)
    validate_prepared(df_icbf, df_api, tablas, reporte, raw_icbf, raw_api)

Evalúa tres bloques con Great Expectations:

    1. ICBF preparado        (reglas DQ-P / DQ-I sobre el dataset transformado)
    2. API preparada         (reglas DQ-A sobre el dataset transformado)
    3. Integración y modelo  (reglas DQ-I: cobertura de llave, integridad
                              referencial, unicidad del grano, reconciliación)

Política de severidad:
    critical -> detiene la rama (se lanza PreparedValidationError)
    warning  -> continúa; queda documentado en el resultado
    info     -> solo se monitorea

Principio: la validación detecta, no corrige. Nada de lo que se hace aquí
modifica los datos.
"""

from pathlib import Path
import sys

import pandas as pd
import great_expectations as gx


# ---------------------------------------------------------
# Dominios válidos (dato ya transformado)
# ---------------------------------------------------------

SEXO = ["M", "H", "I"]
ESTADO_ATENCION = ["A", "I"]
ESTADO_UDS = ["ACTIVA", "INACTIVA"]
SI_NO = ["SI", "NO"]
ZONAS_ICBF = ["CABECERA", "RESTO", "SIN INFORMACIÓN"]
TIPOS_SERVICIO = [
    "HCB", "MAI", "CENTRO DE DESARROLLO INFANTIL", "JARDÍN",
    "EDUCACIÓN INICIAL", "SEMILLAS DE VIDA", "SERVICIO PROPIO",
    "OTROS", "SIN INFORMACIÓN",
]
ZONAS_API = ["CABECERA", "RESTO"]
GRUPOS_API = ["A", "B"]
CORTE_ESPERADO = "SIV_2022"
UMBRAL_MUESTRA = 30
REGEX_DANE = r"^\d{5}$"

# Cobertura de la llave (DQ-I1). Por debajo de 95 % el defecto es de llave
# y no de excepción administrativa. Entre 95 % y 100 % es advertencia.
COBERTURA_CRITICA = 95.0
COBERTURA_ADVERTENCIA = 100.0
# Zona sin información (DQ-I2): R7 excluye estos registros; un 1 % no
# cambia su lectura y un valor mayor sí.
UMBRAL_ZONA_SIN_INFO = 1.0


class PreparedValidationError(Exception):
    """Al menos una expectativa crítica falló: la rama se detiene."""


# ---------------------------------------------------------
# Ejecución de una suite (mismos pasos que validations_icbf)
# ---------------------------------------------------------

def _ejecutar_suite(nombre, df, expectativas):
    """
    Crea contexto, fuente, asset, batch, suite, validation definition
    y checkpoint, y ejecuta. Devuelve el resultado de la validación.
    """

    # Categorías -> texto: GX evalúa conjuntos de valores sobre texto
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype) == "category":
            df[c] = df[c].astype("object")

    context = gx.get_context(mode="ephemeral")

    data_source = context.data_sources.add_pandas(
        name=f"{nombre}_pandas_source"
    )
    data_asset = data_source.add_dataframe_asset(name=f"{nombre}_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        name=f"whole_{nombre}_dataframe"
    )

    suite = context.suites.add_or_update(
        gx.ExpectationSuite(name=f"{nombre}_suite")
    )
    for expectativa in expectativas:
        suite.add_expectation(expectativa)

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"{nombre}_validation_definition",
            data=batch_definition,
            suite=suite,
        )
    )

    validation_result = validation_definition.run(
        batch_parameters={"dataframe": df},
        result_format={"result_format": "SUMMARY"},
    )

    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name=f"{nombre}_validation_checkpoint",
            validation_definitions=[validation_definition],
            actions=[],
            result_format={"result_format": "SUMMARY"},
        )
    )
    checkpoint.run(batch_parameters={"dataframe": df})

    return validation_result


def _resumir(nombre, validation_result):
    """Imprime el resumen y clasifica las fallas por severidad."""

    print(f"\n=== {nombre} ===")
    print("Overall success:", validation_result.success)
    print("Expectations evaluated:", len(validation_result.results))

    fallas = {"critical": [], "warning": [], "info": []}

    for result in validation_result.results:
        expectation = result.expectation
        severidad = str(
            getattr(expectation, "severity", "critical")
        ).split(".")[-1].lower()

        if not result.success:
            fallas.setdefault(severidad, []).append({
                "bloque": nombre,
                "expectativa": type(expectation).__name__,
                "columna": getattr(expectation, "column", None),
                "unexpected_count": result.result.get("unexpected_count", 0),
                "unexpected_percent":
                    result.result.get("unexpected_percent", 0),
                "observed_value": result.result.get("observed_value"),
            })

            print(
                f"  FALLA [{severidad}] "
                f"{type(expectation).__name__} "
                f"columna={getattr(expectation, 'column', None)} "
                f"inesperados={result.result.get('unexpected_count', 0)}"
            )

    return fallas


# ---------------------------------------------------------
# Atajos para declarar expectativas
# ---------------------------------------------------------

E = gx.expectations


def _no_nulo(col, sev="critical", mostly=1.0):
    return E.ExpectColumnValuesToNotBeNull(
        column=col, mostly=mostly, severity=sev)


def _en_conjunto(col, valores, sev="critical", mostly=1.0):
    return E.ExpectColumnValuesToBeInSet(
        column=col, value_set=valores, mostly=mostly, severity=sev)


def _entre(col, minimo=None, maximo=None, sev="critical", mostly=1.0,
           estricto_min=False):
    kwargs = dict(column=col, mostly=mostly, severity=sev)
    if minimo is not None:
        kwargs["min_value"] = minimo
    if maximo is not None:
        kwargs["max_value"] = maximo
    if estricto_min:
        kwargs["strict_min"] = True
    return E.ExpectColumnValuesToBeBetween(**kwargs)


# =========================================================
# BLOQUE 1. ICBF PREPARADO
# =========================================================

def _validar_icbf_preparado(df_icbf):
    df = df_icbf.copy()

    # Columna solo de validación: el prefijo del código DANE debe coincidir
    # con el código de departamento (DQ-P2). No se escribe en los datos.
    df["_prefijo_coherente"] = (
        df["Codigo Municipio DANE"].astype("string").str[:2]
        == df["Codigo Departamento UDS"].astype("string").str.zfill(2)
    )

    # Duplicados exactos del grano de la fuente (DQ-P7)
    columnas_grano = [c for c in df_icbf.columns if c != "Beneficiarios"]
    df["_duplicado_exacto"] = df.duplicated(columnas_grano, keep=False)

    expectativas = [
        # --- Identificadores (T1) -----------------------------------
        _no_nulo("Codigo Departamento UDS"),
        _no_nulo("Codigo Municipio UDS"),
        _no_nulo("Codigo CentroZonal UDS"),
        _no_nulo("Codigo Unidad Servicio"),
        _entre("Codigo Departamento UDS", minimo=0),
        _entre("Codigo Municipio UDS", minimo=0),
        _entre("Codigo Unidad Servicio", minimo=0),

        # --- Llave de integración (T8): código DANE de 5 dígitos ----
        _no_nulo("Codigo Municipio DANE"),
        E.ExpectColumnValuesToMatchRegex(
            column="Codigo Municipio DANE", regex=REGEX_DANE,
            mostly=1.0, severity="critical"),
        _en_conjunto("_prefijo_coherente", [True]),

        # --- Vigencia (T2) ------------------------------------------
        _no_nulo("Vigencia"),
        # Más de una vigencia rompería el supuesto de alineación temporal
        E.ExpectColumnUniqueValueCountToBeBetween(
            column="Vigencia", min_value=1, max_value=1,
            severity="warning"),

        # --- Medida (T3) --------------------------------------------
        _no_nulo("Beneficiarios"),
        _entre("Beneficiarios", minimo=0),

        # --- Estandarización y dominios (T4, T5, T6) ----------------
        _en_conjunto("Estado Atención", ESTADO_ATENCION),
        _en_conjunto("Zona Ubicacion Beneficiario", ZONAS_ICBF),
        _en_conjunto("Sexo", SEXO),
        _no_nulo("Rango Edad"),            # T6: ya no admite nulos
        _no_nulo("Pais Nacimiento"),       # T6: ya no admite nulos
        _no_nulo("Zona Ubicacion Beneficiario"),
        _en_conjunto("Estado UDS", ESTADO_UDS, sev="warning"),
        _en_conjunto("Presenta Discapacidad", SI_NO, sev="warning"),
        _no_nulo("Grupo Etnico"),
        _no_nulo("Tipo de Beneficiario"),

        # --- Atributo derivado (T7) ---------------------------------
        _no_nulo("Tipo Servicio"),
        _en_conjunto("Tipo Servicio", TIPOS_SERVICIO),

        # --- Grano de la fuente (DQ-P7) -----------------------------
        _en_conjunto("_duplicado_exacto", [False], sev="warning"),
    ]

    return _resumir(
        "icbf_preparado", _ejecutar_suite("icbf_prep", df, expectativas))


# =========================================================
# BLOQUE 2. API PREPARADA
# =========================================================

def _validar_api_preparada(df_api):
    df = df_api.copy()

    # T12: la marca debe ser coherente con el umbral
    df["_marca_consistente"] = (
        df["muestra_suficiente"]
        == (df["registros_muestrales"] >= UMBRAL_MUESTRA)
    )

    expectativas = [
        # --- Llave (T10) --------------------------------------------
        _no_nulo("codigo_municipio_dane"),
        E.ExpectColumnValuesToMatchRegex(
            column="codigo_municipio_dane", regex=REGEX_DANE,
            mostly=1.0, severity="critical"),

        # --- Zona armonizada (T11) ----------------------------------
        _no_nulo("nombre_zona"),
        _en_conjunto("nombre_zona", ZONAS_API),
        _en_conjunto("codigo_zona_sisben", [1, 2]),

        # --- Dominios -----------------------------------------------
        _en_conjunto("grupo", GRUPOS_API),

        # --- Medidas (T10) ------------------------------------------
        _no_nulo("poblacion_ponderada"),
        _entre("poblacion_ponderada", minimo=0, estricto_min=True),
        _no_nulo("registros_muestrales"),
        _entre("registros_muestrales", minimo=1),

        # --- Corte único ---------------------------------------------
        _en_conjunto("corte_fuente", [CORTE_ESPERADO]),
        E.ExpectColumnUniqueValueCountToBeBetween(
            column="corte_fuente", min_value=1, max_value=1,
            severity="critical"),

        # --- Marca de muestra (T12) ---------------------------------
        _no_nulo("muestra_suficiente"),
        _en_conjunto("_marca_consistente", [True]),

        # --- Grano (DQ-A5) ------------------------------------------
        E.ExpectCompoundColumnsToBeUnique(
            column_list=["codigo_municipio_dane", "nombre_zona", "grupo"],
            severity="critical"),
    ]

    return _resumir(
        "api_preparada", _ejecutar_suite("api_prep", df, expectativas))


# =========================================================
# BLOQUE 3. INTEGRACIÓN Y MODELO
# =========================================================

def _fk_huerfanas(hecho, columna, dim):
    return int((~hecho[columna].isin(dim[columna])).sum())


def calcular_metricas_integracion(df_icbf, df_api, tablas, reporte,
                                  raw_icbf=None, raw_api=None):
    """Una fila con todas las métricas de integración y reconciliación."""

    fa = tablas["fact_atencion"]
    fp = tablas["fact_vulnerable_population"]

    m = {}

    # DQ-I1 / DQ-I2
    m["pct_beneficiarios_con_cruce"] = reporte["pct_beneficiarios_con_cruce"]
    m["pct_zona_sin_informacion"] = (
        reporte["pct_beneficiarios_zona_sin_informacion"])
    m["municipios_solo_api"] = len(reporte["municipios_solo_api"])

    # DQ-I3: integridad referencial
    fks_atencion = {
        "geography_key": "dim_geography",
        "service_unit_key": "dim_service_unit",
        "service_key": "dim_service",
        "beneficiary_profile_key": "dim_beneficiary_profile",
        "attention_status_key": "dim_attention_status",
        "municipality_key": "dim_municipality",
        "zone_key": "dim_zone",
    }
    m["fk_huerfanas_fact_atencion"] = sum(
        _fk_huerfanas(fa, k, tablas[d]) for k, d in fks_atencion.items())

    fks_pob = {
        "municipality_key": "dim_municipality",
        "zone_key": "dim_zone",
        "sisben_group_key": "dim_sisben_group",
    }
    m["fk_huerfanas_fact_poblacion"] = sum(
        _fk_huerfanas(fp, k, tablas[d]) for k, d in fks_pob.items())

    m["llaves_nulas_fact_atencion"] = int(
        fa[list(fks_atencion)].isna().sum().sum())
    m["llaves_nulas_fact_poblacion"] = int(
        fp[list(fks_pob)].isna().sum().sum())

    # DQ-I4: unicidad del grano
    m["grano_duplicado_fact_atencion"] = int(
        fa.duplicated(list(fks_atencion)).sum())
    m["grano_duplicado_fact_poblacion"] = int(
        fp.duplicated(list(fks_pob)).sum())

    # DQ-I5: reconciliación (preparado -> hechos)
    m["diff_beneficiarios_fuente_vs_hecho"] = abs(
        int(df_icbf["Beneficiarios"].sum())
        - int(fa["total_beneficiarios"].sum()))
    m["diff_poblacion_fuente_vs_hecho"] = abs(
        float(df_api["poblacion_ponderada"].sum())
        - float(fp["poblacion_ponderada"].sum()))
    m["diff_filas_api_vs_hecho"] = abs(len(df_api) - len(fp))

    # Reconciliación (crudo -> preparado): la transformación no pierde filas
    if raw_icbf is not None:
        m["diff_filas_icbf_raw_vs_prep"] = abs(len(raw_icbf) - len(df_icbf))
        m["diff_beneficiarios_raw_vs_prep"] = abs(
            int(pd.to_numeric(raw_icbf["Beneficiarios"]).sum())
            - int(df_icbf["Beneficiarios"].sum()))
    if raw_api is not None:
        m["diff_filas_api_raw_vs_prep"] = abs(len(raw_api) - len(df_api))
        m["diff_poblacion_raw_vs_prep"] = abs(
            float(pd.to_numeric(raw_api["sum_fex"]).sum())
            - float(df_api["poblacion_ponderada"].sum()))

    # DQ-I6: dominio de las dimensiones nuevas
    m["miembros_dim_zone"] = len(tablas["dim_zone"])
    m["miembros_dim_sisben_group"] = len(tablas["dim_sisben_group"])
    m["codigos_duplicados_dim_municipality"] = int(
        tablas["dim_municipality"]["codigo_municipio_dane"]
        .duplicated().sum())
    m["codigos_invalidos_dim_municipality"] = int(
        (~tablas["dim_municipality"]["codigo_municipio_dane"]
         .astype("string").str.fullmatch(REGEX_DANE)).sum())

    return pd.DataFrame([m])


def _informativas(df_icbf, df_api):
    """Métricas solo de monitoreo (severidad informativa)."""

    total = df_icbf["Beneficiarios"].sum()
    otros = df_icbf.loc[
        df_icbf["Tipo Servicio"].astype("string") == "OTROS",
        "Beneficiarios"].sum()
    sin_rango = df_icbf.loc[
        df_icbf["Rango Edad"].astype("string") == "SIN INFORMACIÓN",
        "Beneficiarios"].sum()
    sin_pais = df_icbf.loc[
        df_icbf["Pais Nacimiento"].astype("string") == "SIN INFORMACIÓN",
        "Beneficiarios"].sum()

    return {
        "pct_beneficiarios_tipo_servicio_otros": float(otros / total * 100),
        "pct_beneficiarios_rango_edad_sin_informacion":
            float(sin_rango / total * 100),
        "pct_beneficiarios_pais_sin_informacion":
            float(sin_pais / total * 100),
        "pares_municipio_zona_grupo_muestra_insuficiente":
            int((~df_api["muestra_suficiente"]).sum()),
        "pct_pares_muestra_insuficiente":
            float((~df_api["muestra_suficiente"]).mean() * 100),
    }


def _validar_integracion(df_icbf, df_api, tablas, reporte,
                         raw_icbf, raw_api):
    metricas = calcular_metricas_integracion(
        df_icbf, df_api, tablas, reporte, raw_icbf, raw_api)

    cero = ["fk_huerfanas_fact_atencion", "fk_huerfanas_fact_poblacion",
            "llaves_nulas_fact_atencion", "llaves_nulas_fact_poblacion",
            "grano_duplicado_fact_atencion",
            "grano_duplicado_fact_poblacion",
            "diff_beneficiarios_fuente_vs_hecho",
            "diff_filas_api_vs_hecho",
            "codigos_duplicados_dim_municipality",
            "codigos_invalidos_dim_municipality"]
    cero += [c for c in metricas.columns if c.startswith("diff_")
             and c not in cero and c != "diff_poblacion_fuente_vs_hecho"
             and c != "diff_poblacion_raw_vs_prep"]

    expectativas = [_entre(c, minimo=0, maximo=0) for c in cero]

    # Las sumas decimales se comparan con tolerancia de redondeo
    for c in ["diff_poblacion_fuente_vs_hecho", "diff_poblacion_raw_vs_prep"]:
        if c in metricas.columns:
            expectativas.append(_entre(c, minimo=0, maximo=1e-6))

    expectativas += [
        # DQ-I1: cobertura de la llave
        _entre("pct_beneficiarios_con_cruce",
               minimo=COBERTURA_CRITICA, sev="critical"),
        _entre("pct_beneficiarios_con_cruce",
               minimo=COBERTURA_ADVERTENCIA, sev="warning"),

        # DQ-I2: zona sin información
        _entre("pct_zona_sin_informacion",
               maximo=UMBRAL_ZONA_SIN_INFO, sev="warning"),

        # Municipios que existen solo en la API (nombre desconocido)
        _entre("municipios_solo_api", minimo=0, maximo=0, sev="warning"),

        # DQ-I6: dimensiones nuevas
        _entre("miembros_dim_zone", minimo=3, maximo=3),
        _entre("miembros_dim_sisben_group", minimo=2, maximo=2),
    ]

    fallas = _resumir(
        "integracion_y_modelo",
        _ejecutar_suite("integracion", metricas, expectativas))

    return fallas, metricas


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def validate_prepared(df_icbf, df_api, tablas, reporte,
                      raw_icbf=None, raw_api=None,
                      detener_en_critica=True):
    """
    Ejecuta los tres bloques y aplica la política de severidad.

    Devuelve un dict con fallas por severidad, las métricas de integración
    y las métricas informativas.
    """

    fallas = {"critical": [], "warning": [], "info": []}

    f_icbf = _validar_icbf_preparado(df_icbf)
    f_api = _validar_api_preparada(df_api)
    f_int, metricas = _validar_integracion(
        df_icbf, df_api, tablas, reporte, raw_icbf, raw_api)

    for bloque in (f_icbf, f_api, f_int):
        for sev, lista in bloque.items():
            fallas.setdefault(sev, []).extend(lista)

    informativas = _informativas(df_icbf, df_api)

    print("\n=== Métricas informativas ===")
    for k, v in informativas.items():
        print(f"  {k}: {v}")

    print("\n=== Resultado de la compuerta ===")
    print("Críticas :", len(fallas["critical"]))
    print("Advertencias:", len(fallas["warning"]))

    resultado = {
        "fallas": fallas,
        "metricas_integracion": metricas.iloc[0].to_dict(),
        "metricas_informativas": informativas,
        "aprobada": len(fallas["critical"]) == 0,
    }

    if detener_en_critica and fallas["critical"]:
        raise PreparedValidationError(
            f"{len(fallas['critical'])} expectativas críticas fallaron: "
            + "; ".join(
                f"{f['bloque']}:{f['expectativa']}({f['columna']})"
                for f in fallas["critical"]))

    return resultado


# ---------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------

if __name__ == "__main__":

    RAIZ = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(RAIZ / "src"))

    from extract import extraer_datos, RUTA_RAW
    from transform import transformar_fuentes
    from dimensional_model import construir_modelo

    raw_icbf = extraer_datos(RUTA_RAW)
    raw_api = pd.read_parquet(
        RAIZ / "Data" / "staging" / "raw_sisben_agregado.parquet")

    df_icbf, df_api = transformar_fuentes(raw_icbf, raw_api)
    tablas, reporte = construir_modelo(df_icbf, df_api)

    validate_prepared(
        df_icbf, df_api, tablas, reporte, raw_icbf, raw_api)