from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Ruta por defecto a la carpeta data/raw del proyecto
RUTA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "DatasetCompleto.csv"


# ============================================================
# EXTRACCIÓN
# ============================================================

def extraer_datos(ruta: Path | str) -> pd.DataFrame:
    """
    Extrae los datos de la fuente ICBF detectando automáticamente
    si el archivo es CSV o Excel (.xlsx).
    """
    ruta = Path(ruta)

    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo en la ruta: {ruta}"
        )

    print("Iniciando extracción de datos ICBF...")
    print(f"Archivo detectado: {ruta}")

    extension = ruta.suffix.lower()

    # 1. Si la extensión es .csv
    if extension == ".csv":
        print("Formato CSV detectado. Cargando con pandas.read_csv...")
        try:
            df = pd.read_csv(ruta, encoding="utf-8")
        except (UnicodeDecodeError, pd.errors.ParserError):
            # Formato alternativo común en datasets colombianos (separado por ';' y codificación Latin-1)
            df = pd.read_csv(ruta, encoding="latin-1", sep=";")

    # 2. Si la extensión es .xlsx o .xls
    elif extension in [".xlsx", ".xls"]:
        print("Formato Excel detectado. Cargando con pandas.read_excel...")
        try:
            df = pd.read_excel(ruta, engine="openpyxl")
        except ImportError:
            print("Advertencia: Motor 'openpyxl' no disponible, intentando con 'calamine'...")
            df = pd.read_excel(ruta, engine="calamine")

    else:
        raise ValueError(f"Formato de archivo no soportado: '{extension}'. Debe ser .csv o .xlsx")

    print("\nExtracción completada con éxito.")
    print(f"Filas procesadas: {df.shape[0]:,}")
    print(f"Columnas detectadas: {df.shape[1]}")

    return df


# ============================================================
# EJECUCIÓN DIRECTA (PRUEBAS LOCALES)
# ============================================================

if __name__ == "__main__":
    df = extraer_datos(RUTA_RAW)
    print("\nPrimeras 5 filas:")
    print(df.head())