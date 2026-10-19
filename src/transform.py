import pandas as pd


# =============================================================
# CONSTANTES DE LA FUENTE API (Sisbén)
# =============================================================

# Umbral mínimo de registros muestrales para publicar una razón
# (DQ-A8). Es una convención estadística, no un valor ajustado
# a los datos actuales.
UMBRAL_MUESTRA = 30

# El Sisbén codifica la zona como 1 o 2; el ICBF usa texto.
MAPA_ZONA_SISBEN = {
    1: "CABECERA",
    2: "RESTO",
}

COLUMNAS_API = {"cod_mpio", "zona", "grupo", "sum_fex", "count", "corte"}


# =============================================================
# FUENTE 1: ICBF (archivo)
# =============================================================

def transformar(df):
    """
    Transformación y preparación del dataset.

    Responsabilidades:
    - Estandarizar categorías y textos.
    - Corregir tipos de datos.
    - Preparar identificadores.
    - Preparar valores faltantes.
    - Crear atributos derivados justificados.
    - Derivar la llave de integración con la API del Sisbén.

    No realiza agregaciones ni cálculos de KPIs.

    Las transformaciones llevan el ID de la tabla de la sección 13
    (T1 a T9). Las reglas de calidad (dominios, coherencia de
    códigos, cobertura de la llave) se evalúan en las compuertas
    de validación y no se corrigen aquí.
    """

    df = df.copy()

    # =========================================================
    # 1. IDENTIFICADORES (T1)
    # =========================================================

    # Los códigos territoriales son identificadores.
    # Se mantienen como enteros porque no presentan
    # información decimal ni valores faltantes.
    df["Codigo Departamento UDS"] = pd.to_numeric(
        df["Codigo Departamento UDS"],
        errors="raise"
    ).astype("Int64")

    df["Codigo Municipio UDS"] = pd.to_numeric(
        df["Codigo Municipio UDS"],
        errors="raise"
    ).astype("Int64")

    df["Codigo CentroZonal UDS"] = pd.to_numeric(
        df["Codigo CentroZonal UDS"],
        errors="raise"
    ).astype("Int64")

    df["Codigo Unidad Servicio"] = pd.to_numeric(
        df["Codigo Unidad Servicio"],
        errors="raise"
    ).astype("Int64")


    # =========================================================
    # 2. VIGENCIA (T2)
    # =========================================================

    # No es una fecha. Es un identificador de vigencia
    # y actualmente contiene un único año.
    df["Vigencia"] = pd.to_numeric(
        df["Vigencia"],
        errors="raise"
    ).astype("Int64")


    # =========================================================
    # 3. VARIABLE NUMÉRICA PRINCIPAL (T3)
    # =========================================================

    df["Beneficiarios"] = pd.to_numeric(
        df["Beneficiarios"],
        errors="raise"
    )

    # Validación de la medida
    if (df["Beneficiarios"] < 0).any():
        raise ValueError(
            "La variable Beneficiarios contiene valores negativos."
        )

    if df["Beneficiarios"].isna().any():
        raise ValueError(
            "La variable Beneficiarios contiene valores nulos."
        )

    # Los beneficiarios representan cantidades enteras.
    df["Beneficiarios"] = df["Beneficiarios"].astype("Int64")


    # =========================================================
    # 4. ESTANDARIZACIÓN DE VARIABLES CATEGÓRICAS (T4)
    # =========================================================

    columnas_categoricas = [
        "Departamento UDS",
        "Municipio UDS",
        "Centro Zonal UDS",
        "Unidad Servicio",
        "Estado UDS",
        "Modalidad",
        "Nombre Servicio",
        "Tipo de Beneficiario",
        "Sexo",
        "Rango Edad",
        "Grupo Etnico",
        "Presenta Discapacidad",
        "Zona Ubicacion Beneficiario",
        "Pais Nacimiento",
        "Estado Atención"
    ]

    for columna in columnas_categoricas:

        df[columna] = (
            df[columna]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.upper()
        )


    # =========================================================
    # 5. NORMALIZACIÓN DE ESTADO DE ATENCIÓN (T5)
    # =========================================================

    # El origen utiliza:
    # 1 = A
    # 2 = I
    # además de A e I.
    mapa_estado_atencion = {
        "1": "A",
        "2": "I",
        "A": "A",
        "I": "I"
    }

    df["Estado Atención"] = (
        df["Estado Atención"]
        .replace(mapa_estado_atencion)
    )


    # Validar que no aparezcan categorías inesperadas
    estados_validos = {"A", "I"}

    estados_encontrados = set(
        df["Estado Atención"]
        .dropna()
        .unique()
    )

    estados_invalidos = estados_encontrados - estados_validos

    if estados_invalidos:
        raise ValueError(
            f"Valores inesperados en Estado Atención: "
            f"{estados_invalidos}"
        )


    # =========================================================
    # 6. CATEGORÍAS FALTANTES (T6)
    # =========================================================

    # Estos faltantes sí se conservan explícitamente como
    # categoría analítica.
    df["Zona Ubicacion Beneficiario"] = (
        df["Zona Ubicacion Beneficiario"]
        .fillna("SIN INFORMACIÓN")
    )

    df["Pais Nacimiento"] = (
        df["Pais Nacimiento"]
        .fillna("SIN INFORMACIÓN")
    )

    df["Rango Edad"] = (
        df["Rango Edad"]
        .fillna("SIN INFORMACIÓN")
    )


    # Modalidad NO se imputa porque presenta una proporción
    # muy alta de valores faltantes y no se utilizará como
    # variable analítica principal.
    #
    # Se conserva para trazabilidad.


    # =========================================================
    # 7. ATRIBUTO DERIVADO JUSTIFICADO (T7)
    # =========================================================

    # R3 requiere trabajar con el tipo de servicio.
    # Se deriva a partir de Nombre Servicio porque Modalidad
    # presenta demasiados valores faltantes.

    def clasificar_servicio(nombre):

        if pd.isna(nombre):
            return "SIN INFORMACIÓN"

        nombre = str(nombre)

        if "HCB" in nombre:
            return "HCB"

        if "MAI" in nombre:
            return "MAI"

        if "CENTRO DE DESARROLLO INFANTIL" in nombre:
            return "CENTRO DE DESARROLLO INFANTIL"

        if "JARDIN" in nombre:
            return "JARDÍN"

        if "EDUCACION INICIAL" in nombre:
            return "EDUCACIÓN INICIAL"

        if "SEMILLAS DE VIDA" in nombre:
            return "SEMILLAS DE VIDA"

        if "CRIC" in nombre:
            return "SERVICIO PROPIO"

        return "OTROS"

    df["Tipo Servicio"] = (
        df["Nombre Servicio"]
        .apply(clasificar_servicio)
    )


    # =========================================================
    # 7b. LLAVE DE INTEGRACIÓN CON LA API (T8)
    # =========================================================

    # El código DANE de municipio tiene 5 caracteres. El ICBF lo
    # entrega como entero y pierde el cero inicial (5001 en lugar
    # de 05001). Se deriva una columna de texto de 5 caracteres
    # para unir con cod_mpio del Sisbén. El código original se
    # conserva. Si el resultado no tiene 5 dígitos, no se corrige:
    # lo detecta la validación de datos preparados.
    df["Codigo Municipio DANE"] = (
        df["Codigo Municipio UDS"]
        .astype("string")
        .str.zfill(5)
    )


    # =========================================================
    # 8. TIPOS CATEGÓRICOS
    # =========================================================

    # Se convierten las variables categóricas al tipo
    # category para reducir memoria y dejar explícita
    # su naturaleza.
    for columna in columnas_categoricas + ["Tipo Servicio"]:
        df[columna] = df[columna].astype("category")
        
    # =========================================================
    # 9. SELECCIÓN DEL DATASET DEFINITIVO (T9)
    # =========================================================
    
    def dataset_definitivo(df):

        columnas_definitivas = [
            # Identificación territorial
            "Codigo Departamento UDS",
            "Departamento UDS",
            "Codigo Municipio UDS",
            "Municipio UDS",
            "Codigo Municipio DANE",
            "Codigo CentroZonal UDS",
            "Centro Zonal UDS",

            # Identificación del servicio
            "Codigo Unidad Servicio",
            "Unidad Servicio",
            "Estado UDS",
            "Nombre Servicio",
            "Tipo Servicio",
            "Tipo de Beneficiario",

            # Características del beneficiario
            "Sexo",
            "Rango Edad",
            "Grupo Etnico",
            "Presenta Discapacidad",
            "Zona Ubicacion Beneficiario",
            "Pais Nacimiento",
            "Estado Atención",

            # Referencia temporal (se conserva para trazabilidad
            # y para documentar el desfase con el corte del Sisbén)
            "Vigencia",

            # Medida principal
            "Beneficiarios"
        ]

        return df[columnas_definitivas].copy()

    
    df = dataset_definitivo(df)

    return df


# =============================================================
# FUENTE 2: API Sisbén (DNP Sisbén Personas)
# =============================================================

def transformar_sisben(df):
    """
    Transformación de la extracción agregada de la API.

    Entrada: columnas cod_mpio, zona, grupo, sum_fex, count y corte,
    todas como texto.

    Responsabilidades:
    - Convertir tipos (T10).
    - Armonizar la zona con el vocabulario del ICBF (T11).
    - Marcar, sin eliminar, los pares con muestra insuficiente (T12).
    - Renombrar al lenguaje del modelo dimensional (T13).

    No modifica datos para que una validación pase: el formato del
    código y los dominios se validan antes, en la compuerta
    API Raw Validation.
    """

    df = df.copy()

    faltantes = COLUMNAS_API - set(df.columns)
    if faltantes:
        raise ValueError(f"Columnas ausentes en la API: {faltantes}")

    # =========================================================
    # 1. TIPOS (T10)
    # =========================================================

    # El código DANE es un identificador: se conserva como texto
    # de 5 caracteres, sin corregirlo aquí.
    df["cod_mpio"] = df["cod_mpio"].astype("string").str.strip()

    df["zona"] = pd.to_numeric(df["zona"], errors="raise").astype("Int64")

    # sum_fex es la suma de factores de expansión (población
    # estimada): admite decimales.
    df["sum_fex"] = pd.to_numeric(df["sum_fex"], errors="raise")

    df["count"] = pd.to_numeric(df["count"], errors="raise").astype("Int64")

    for columna in ["grupo", "corte"]:
        df[columna] = (
            df[columna]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    # =========================================================
    # 2. ARMONIZACIÓN DE LA ZONA (T11)
    # =========================================================

    # Un código desconocido no se adivina.
    zonas_invalidas = set(df["zona"].dropna().unique()) - set(MAPA_ZONA_SISBEN)

    if zonas_invalidas:
        raise ValueError(
            f"Valores inesperados en zona: {zonas_invalidas}"
        )

    df["nombre_zona"] = df["zona"].map(MAPA_ZONA_SISBEN)

    # =========================================================
    # 3. MARCA DE MUESTRA SUFICIENTE (T12)
    # =========================================================

    # Se marca, no se elimina. La exclusión ocurre al calcular
    # la razón de R6 y R7.
    df["muestra_suficiente"] = df["count"] >= UMBRAL_MUESTRA

    # =========================================================
    # 4. NOMBRES DEL MODELO DIMENSIONAL (T13)
    # =========================================================

    df = df.rename(columns={
        "cod_mpio": "codigo_municipio_dane",
        "zona": "codigo_zona_sisben",
        "sum_fex": "poblacion_ponderada",
        "count": "registros_muestrales",
        "corte": "corte_fuente",
    })

    columnas_definitivas = [
        "codigo_municipio_dane",
        "codigo_zona_sisben",
        "nombre_zona",
        "grupo",
        "poblacion_ponderada",
        "registros_muestrales",
        "corte_fuente",
        "muestra_suficiente",
    ]

    return df[columnas_definitivas].copy()


# =============================================================
# PUNTO DE ENTRADA ÚNICO
# =============================================================

def transformar_fuentes(df_icbf_raw, df_api_raw):
    """
    Transforma las dos fuentes y devuelve (df_icbf, df_api).

    Cada rama se transforma de forma independiente: la integración
    ocurre después, en dimensional_model.construir_modelo(), a
    través de las dimensiones conformadas. Aquí no se unen.
    """
    df_icbf = transformar(df_icbf_raw)
    df_api = transformar_sisben(df_api_raw)
    return df_icbf, df_api