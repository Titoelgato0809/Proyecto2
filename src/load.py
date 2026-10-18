import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUTA_CREATE_DW = PROJECT_ROOT / "sql" / "create_dw.sql"

load_dotenv(PROJECT_ROOT / ".env")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "icbf_primera_infancia_dw")


def crear_engine(incluir_base_de_datos: bool = True):
    """
    Crea el engine de SQLAlchemy para conectarse a MySQL.
    Si incluir_base_de_datos=False, se conecta al servidor MySQL
    sin seleccionar ninguna base (necesario antes de que la base
    de datos exista).
    """
    base = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
    if incluir_base_de_datos:
        base += f"/{DB_NAME}"
    return create_engine(base)


def crear_esquema():
    """
    Ejecuta sql/create_dw.sql para crear la base de datos y las
    tablas (dimensiones + hechos) si no existen todavía.
    """
    if not RUTA_CREATE_DW.exists():
        raise FileNotFoundError(f"No se encontró el archivo DDL en: {RUTA_CREATE_DW}")

    with open(RUTA_CREATE_DW, "r", encoding="utf-8") as f:
        script_sql = f.read()

    engine = crear_engine(incluir_base_de_datos=False)
    sentencias = [s.strip() for s in script_sql.split(";") if s.strip()]

    with engine.begin() as conexion:
        for sentencia in sentencias:
            conexion.execute(text(sentencia))

    engine.dispose()
    print("Esquema del Data Warehouse creado (o ya existente).")


def save_to_csv(df, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, sep=";", index=False)
    print(f"Archivo CSV guardado en: {file_path}")
    print(f"Total de filas guardadas: {df.shape[0]}")


def save_to_mysql(df, table_name):
    """
    Inserta un DataFrame completo en la tabla indicada del Data
    Warehouse, usando crear_engine() (conexión real a MySQL),
    no una ruta de archivo.
    """
    engine = crear_engine(incluir_base_de_datos=True)

    try:
        df.to_sql(
            table_name,
            engine,
            if_exists='append'z,
            index=False
        )

        print(f"Datos guardados en MySQL: tabla {table_name}")
        print(f"Total de filas cargadas: {df.shape[0]}")

    except Exception as e:
        print(f"ERROR al guardar la tabla '{table_name}' en MySQL: {e}")
        raise

    finally:
        engine.dispose()


def reset_schema():
    """
    Vacía los datos de las tablas (TRUNCATE) sin borrar su estructura,
    para poder correr el ETL varias veces sin errores de duplicados
    ni perder las PK/FK/UNIQUE definidas en create_dw.sql.
    """
    tablas = [
        "fact_atencion",
        "dim_geography",
        "dim_service_unit",
        "dim_service",
        "dim_beneficiary_profile",
        "dim_attention_status",
    ]
    engine = crear_engine(incluir_base_de_datos=True)
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for tabla in tablas:
            try:
                conn.execute(text(f"TRUNCATE TABLE {tabla}"))
            except Exception:
                pass  # si la tabla aún no existe (primera vez), no pasa nada
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    engine.dispose()
    print("Tablas vaciadas correctamente (estructura conservada).")
    
    