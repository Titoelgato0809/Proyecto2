import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUTA_CREATE_DW = PROJECT_ROOT / "sql" / "create_dw.sql"

load_dotenv(PROJECT_ROOT / ".env")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "icbf_primera_infancia_dw")


def crear_engine(incluir_base_de_datos: bool = True):
    """Crea el engine de SQLAlchemy para conectarse a PostgreSQL.

    Si incluir_base_de_datos=False, se conecta a la base por defecto
    'postgres'.
    """
    db_target = DB_NAME if incluir_base_de_datos else "postgres"
    base = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{db_target}"
    return create_engine(base)


def crear_esquema():
    """Crea la base de datos si no existe y ejecuta sql/create_dw.sql."""
    if not RUTA_CREATE_DW.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo DDL en: {RUTA_CREATE_DW}"
        )

    # 1. Crear la base de datos si no existe
    engine_maint = crear_engine(incluir_base_de_datos=False).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    with engine_maint.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
        )
        if not result.scalar():
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"Base de datos '{DB_NAME}' creada.")
    engine_maint.dispose()

    # 2. Ejecutar script DDL en la base de datos del proyecto
    with open(RUTA_CREATE_DW, "r", encoding="utf-8") as f:
        script_sql = f.read()

    engine_dw = crear_engine(incluir_base_de_datos=True)
    sentencias = [s.strip() for s in script_sql.split(";") if s.strip()]

    with engine_dw.begin() as conexion:
        for sentencia in sentencias:
            conexion.execute(text(sentencia))

    engine_dw.dispose()
    print("Esquema del Data Warehouse creado (o ya existente).")


def save_to_csv(df, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, sep=";", index=False)
    print(f"Archivo CSV guardado en: {file_path}")
    print(f"Total de filas guardadas: {df.shape[0]}")


def save_to_postgres(df, table_name):
    """Inserta un DataFrame completo en la tabla indicada del Data Warehouse en PostgreSQL."""
    engine = crear_engine(incluir_base_de_datos=True)

    try:
        df.to_sql(table_name, engine, if_exists="append", index=False)

        print(f"Datos guardados en PostgreSQL: tabla {table_name}")
        print(f"Total de filas cargadas: {df.shape[0]}")

    except Exception as e:
        print(f"ERROR al guardar la tabla '{table_name}' en PostgreSQL: {e}")
        raise

    finally:
        engine.dispose()


def reset_schema():
    """Vacía los datos de las tablas (TRUNCATE) reiniciando llaves primarias sin borrar la estructura."""
    tablas = [
        "fact_atencion",
        "dim_geography",
        "dim_service_unit",
        "dim_service",
        "dim_beneficiary_profile",
        "dim_attention_status",
    ]
    engine = crear_engine(incluir_base_de_datos=True)
    tablas_str = ", ".join(tablas)

    with engine.begin() as conn:
        try:
            conn.execute(
                text(f"TRUNCATE TABLE {tablas_str} RESTART IDENTITY CASCADE;")
            )
        except Exception as e:
            print(f"Aviso en reset_schema: {e}")

    engine.dispose()
    print(
        "Tablas vaciadas y secuencias reiniciadas correctamente (estructura conservada)."
    )