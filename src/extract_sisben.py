from pathlib import Path
import pandas as pd
import requests


def extract_sisben_data(output_dir="data/staging"):
    """Extrae datos del Sisbén enfocados en ODS 2 desde la API de datos.gov.co."""
    # Endpoint de Socrata con límite de registros
    api_url = "https://www.datos.gov.co/resource/hq2v-5umk.json?$limit=5000"

    print(f"Consultando API: {api_url}")
    response = requests.get(api_url)

    # Validar respuesta HTTP
    response.raise_for_status()

    # Convertir JSON a DataFrame
    data = response.json()
    df = pd.DataFrame(data)

    print(f"Extracción exitosa. Registros traídos: {len(df)} | Columnas: {df.shape[1]}")

    # Guardar staging raw en formato Parquet
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / "raw_sisben.parquet"
    df.to_parquet(file_path, index=False)
    print(f"Datos crudos guardados en: {file_path}")

    return df


if __name__ == "__main__":
    extract_sisben_data()