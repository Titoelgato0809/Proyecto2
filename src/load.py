"""
Carga al Data Warehouse en PostgreSQL.

Recibe el diccionario de tablas de dimensional_model.construir_modelo() y
lo carga en UNA transacción:

    1. Toma un candado de aplicación (advisory lock): dos cargas nunca
       corren a la vez, así que no hay deadlocks entre ejecuciones.
    2. Verifica que el esquema exista y coincida con los DataFrames.
    3. Vacía las tablas (DELETE, hijos antes que padres).
    4. Inserta dimensiones y luego hechos.
    5. Reconcilia dentro de la transacción (conteos y sumas). Si algo no
       cuadra, ROLLBACK: el DW queda como estaba.

Es segura de repetir: cada corrida deja el DW igual a la fuente, sin
duplicar filas. La carga NUNCA recrea el esquema; eso es una acción aparte
(crear_esquema) y destructiva.

Variables de entorno (.env, nunca versionado). Se prefieren las DW_* para
no confundir el DW con la base de metadatos de Airflow:
    DW_POSTGRES_HOST, DW_POSTGRES_PORT, DW_POSTGRES_USER,
    DW_POSTGRES_PASSWORD, DW_POSTGRES_DB
(si no existen, se usan POSTGRES_HOST/PORT/USER/PASSWORD/DB)
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


RAIZ = Path(__file__).resolve().parent.parent
RUTA_DDL = RAIZ / "sql" / "create_dw.sql"

# Orden de inserción: dimensiones primero, hechos al final.
# El borrado va en el orden inverso.
ORDEN_CARGA = [
    "dim_geography",
    "dim_service_unit",
    "dim_service",
    "dim_beneficiary_profile",
    "dim_attention_status",
    "dim_municipality",
    "dim_zone",
    "dim_sisben_group",
    "fact_atencion",
    "fact_vulnerable_population",
]

TAMANO_LOTE = 5000
CLAVE_CANDADO = 2026102101   # identifica "carga/DDL del DW" entre procesos


class LoadError(Exception):
    """La carga no cuadra con lo esperado: se hizo ROLLBACK."""


# ---------------------------------------------------------
# Conexión
# ---------------------------------------------------------

def _env(nombre, defecto=None):
    return os.getenv(f"DW_{nombre}") or os.getenv(nombre) or defecto


def _url(con_base=True):
    load_dotenv(RAIZ / ".env")
    load_dotenv()

    usuario = _env("POSTGRES_USER", "postgres")
    clave = (_env("POSTGRES_PASSWORD", "postgres") or "").strip("\"'")
    # Para crear la base se entra a la base de mantenimiento "postgres".
    base = _env("POSTGRES_DB", "postgres") if con_base else "postgres"

    # URL.create escapa @, :, / en la contraseña (un f-string no).
    return URL.create(
        "postgresql+psycopg2",
        username=usuario,
        password=clave,
        host=_env("POSTGRES_HOST", "postgres"),
        port=int(_env("POSTGRES_PORT", "5432")),
        database=base,
    )


def crear_engine(crear_base=False):
    """Engine hacia el DW. Con crear_base=True crea la base si no existe."""
    if crear_base:
        nombre = _env("POSTGRES_DB", "postgres")
        # CREATE DATABASE no puede correr dentro de una transacción.
        servidor = create_engine(
            _url(con_base=False), isolation_level="AUTOCOMMIT")
        with servidor.connect() as con:
            existe = con.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": nombre},
            ).scalar()
            if not existe:
                con.execute(text(f'CREATE DATABASE "{nombre}"'))
        servidor.dispose()

    return create_engine(_url(con_base=True), pool_pre_ping=True)


obtener_engine = crear_engine   # nombre usado en versiones anteriores


def _candado(con):
    """Serializa cargas y DDL; se libera solo al terminar la transacción."""
    con.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                {"k": CLAVE_CANDADO})


# ---------------------------------------------------------
# Esquema
# ---------------------------------------------------------

def crear_esquema(engine, ruta_ddl=RUTA_DDL):
    """
    Ejecuta sql/create_dw.sql. DESTRUCTIVO: elimina y recrea las diez
    tablas. Úselo la primera vez o cuando cambie el modelo.
    """
    sentencias = [
        s.strip() for s in
        "\n".join(
            linea for linea in ruta_ddl.read_text(encoding="utf-8").splitlines()
            if not linea.strip().startswith("--")
        ).split(";")
        if s.strip()
    ]
    with engine.begin() as con:
        _candado(con)
        for sentencia in sentencias:
            con.execute(text(sentencia))
    print(f"Esquema creado desde {ruta_ddl.name} "
          f"({len(sentencias)} sentencias).")


def _verificar_esquema(engine, tablas):
    """El esquema debe existir y tener las columnas de cada DataFrame."""
    inspector = inspect(engine)
    existentes = set(inspector.get_table_names())

    faltan = [t for t in ORDEN_CARGA if t not in existentes]
    if faltan:
        raise LoadError(
            f"Faltan tablas en PostgreSQL: {faltan}. "
            f"Ejecute crear_esquema() o cargar(..., recrear_esquema=True).")

    for nombre in ORDEN_CARGA:
        columnas_db = {c["name"] for c in inspector.get_columns(nombre)}
        columnas_df = set(tablas[nombre].columns)
        if columnas_db != columnas_df:
            raise LoadError(
                f"{nombre}: el esquema de PostgreSQL no coincide con el modelo. "
                f"Sobran en BD: {sorted(columnas_db - columnas_df)}; "
                f"faltan en BD: {sorted(columnas_df - columnas_db)}. "
                f"Use el sql/create_dw.sql del repositorio.")


def _verificar_entrada(tablas):
    """Todas las tablas deben venir y tener filas: si no, es una falla."""
    ausentes = [t for t in ORDEN_CARGA if t not in tablas]
    vacias = [t for t in ORDEN_CARGA
              if t in tablas and (tablas[t] is None or len(tablas[t]) == 0)]
    if ausentes or vacias:
        raise LoadError(
            f"Entrada inválida para la carga. Ausentes: {ausentes}; "
            f"vacías: {vacias}.")


# ---------------------------------------------------------
# Carga
# ---------------------------------------------------------

def _preparar(df):
    """pandas -> valores que PostgreSQL acepta (NA -> NULL)."""
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype) == "category":
            df[c] = df[c].astype("object")
    return df.astype(object).where(df.notna(), None)


def _insertar(con, nombre, df):
    _preparar(df).to_sql(
        nombre, con, if_exists="append", index=False,
        chunksize=TAMANO_LOTE, method="multi",
    )


def _reconciliar(con, tablas):
    """
    Compara, dentro de la transacción, lo que quedó en PostgreSQL con lo que
    se pretendía cargar. Cualquier diferencia lanza LoadError.
    """
    esperado = {n: len(tablas[n]) for n in ORDEN_CARGA}
    en_bd = {
        n: con.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar()
        for n in ORDEN_CARGA
    }
    distintos = {n: (esperado[n], en_bd[n])
                 for n in ORDEN_CARGA if esperado[n] != en_bd[n]}
    if distintos:
        raise LoadError(f"Conteos distintos (esperado, en BD): {distintos}")

    benef_bd = con.execute(text(
        "SELECT COALESCE(SUM(total_beneficiarios),0) "
        "FROM fact_atencion")).scalar()
    benef_df = int(tablas["fact_atencion"]["total_beneficiarios"].sum())
    if int(benef_bd) != benef_df:
        raise LoadError(
            f"Suma de beneficiarios distinta: BD={benef_bd}, "
            f"esperado={benef_df}")

    pob_bd = con.execute(text(
        "SELECT COALESCE(SUM(poblacion_ponderada),0) "
        "FROM fact_vulnerable_population")).scalar()
    pob_df = float(tablas["fact_vulnerable_population"]
                   ["poblacion_ponderada"].sum())
    if abs(float(pob_bd) - pob_df) > 0.01:
        raise LoadError(
            f"Suma de población distinta: BD={pob_bd}, esperado={pob_df}")

    return {"filas": en_bd,
            "total_beneficiarios": int(benef_bd),
            "poblacion_ponderada": float(pob_bd)}


def cargar(tablas, engine=None, recrear_esquema=False):
    """
    Carga las diez tablas en una sola transacción.

    tablas           -> dict nombre -> DataFrame (de construir_modelo)
    recrear_esquema  -> True ejecuta sql/create_dw.sql (destructivo).
                        Por defecto False: la carga nunca borra el esquema.
    Devuelve el resumen de reconciliación.
    """
    _verificar_entrada(tablas)
    engine = engine or crear_engine()

    if recrear_esquema:
        crear_esquema(engine)

    _verificar_esquema(engine, tablas)

    with engine.begin() as con:     # COMMIT al salir; ROLLBACK si falla
        _candado(con)

        # Vaciar: hechos antes que dimensiones (por las llaves foráneas)
        for nombre in reversed(ORDEN_CARGA):
            con.execute(text(f"DELETE FROM {nombre}"))

        # Insertar: dimensiones antes que hechos
        for nombre in ORDEN_CARGA:
            _insertar(con, nombre, tablas[nombre])
            print(f"  {nombre}: {len(tablas[nombre])} filas")

        resumen = _reconciliar(con, tablas)

    print("Carga confirmada (COMMIT).")
    return resumen


# ---------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(RAIZ / "src"))

    from extract import extraer_datos, RUTA_RAW
    from transform import transformar_fuentes
    from dimensional_model import construir_modelo
    from validation import validate_prepared

    recrear = "--recrear-esquema" in sys.argv

    raw_icbf = extraer_datos(RUTA_RAW)
    raw_api = pd.read_parquet(
        RAIZ / "data" / "staging" / "raw_sisben_agregado.parquet")

    df_icbf, df_api = transformar_fuentes(raw_icbf, raw_api)
    tablas, reporte = construir_modelo(df_icbf, df_api)

    # Compuerta 3: si hay una falla crítica, no se carga nada
    validate_prepared(df_icbf, df_api, tablas, reporte, raw_icbf, raw_api)

    print(cargar(tablas, engine=crear_engine(crear_base=True),
                 recrear_esquema=recrear))