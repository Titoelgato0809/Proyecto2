"""
Extracción de la API del Sisbén (DNP, datos.gov.co, recurso hq2v-5umk).

La agregación la hace el servidor (SODA): llega una fila por
municipio x zona x grupo (A y B), con la suma de fex y el conteo de
registros muestrales. No se descargan las filas de personas.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

API_URL = "https://www.datos.gov.co/resource/hq2v-5umk.json"

CONSULTA = {
    "$select": ("cod_mpio, zona, grupo, corte, "
                "sum(fex) as sum_fex, count(*) as count"),
    "$where": "grupo in ('A','B')",
    "$group": "cod_mpio, zona, grupo, corte",
    "$order": "cod_mpio, zona, grupo",
}

TAM_PAGINA = 50000
TIEMPO_ESPERA = (10, 120)   # (conexión, lectura) en segundos; la agregación
                            # sobre toda la base puede tardar en el servidor
MAX_INTENTOS = 4            # solo para fallas transitorias
ESPERA_BASE = 2             # segundos; crece 2, 4, 8
COLUMNAS_ESPERADAS = ["cod_mpio", "zona", "grupo", "corte", "sum_fex", "count"]


class ApiError(Exception):
    """Falla determinista (400, 404...): repetir no ayuda."""


def _pedir_pagina(sesion, offset):
    """GET de una página. Reintenta solo timeouts, conexión, 429 y 5xx."""
    params = {**CONSULTA, "$limit": TAM_PAGINA, "$offset": offset}

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            r = sesion.get(API_URL, params=params, timeout=TIEMPO_ESPERA)
        except (requests.Timeout, requests.ConnectionError) as e:
            error = f"{type(e).__name__}"
        else:
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                error = f"HTTP {r.status_code}"
            else:
                # 400/404/401/403: contrato o consulta mal formada
                raise ApiError(f"HTTP {r.status_code}: {r.text[:300]}")

        if intento == MAX_INTENTOS:
            raise ApiError(f"Sin respuesta tras {MAX_INTENTOS} intentos ({error})")
        espera = ESPERA_BASE ** intento
        print(f"  {error}; reintento {intento}/{MAX_INTENTOS - 1} en {espera}s")
        time.sleep(espera)


def extract_sisben_data(output_dir="data/staging"):
    """Extrae el Sisbén agregado (grupos A y B) y guarda el crudo en Parquet."""
    load_dotenv()
    sesion = requests.Session()
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        sesion.headers["X-App-Token"] = token

    inicio = datetime.now(timezone.utc)
    print(f"Consultando API: {API_URL}")

    filas, offset = [], 0
    while True:
        pagina = _pedir_pagina(sesion, offset)
        filas.extend(pagina)
        print(f"  offset {offset}: {len(pagina)} filas")
        if len(pagina) < TAM_PAGINA:
            break
        offset += TAM_PAGINA

    df = pd.DataFrame(filas)
    if df.empty:
        raise ApiError("La API devolvió 0 filas.")
    # Se deja el crudo tal cual llega (texto). Si falta una columna, la
    # compuerta cruda (DQ-A1) debe detener la rama, no esta función.

    salida = Path(output_dir)
    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / "raw_sisben_agregado.parquet"
    df.to_parquet(ruta, index=False)

    fin = datetime.now(timezone.utc)
    meta = {
        "batch_id": inicio.strftime("sisben_%Y%m%dT%H%M%SZ"),
        "extraido_en_utc": fin.isoformat(),
        "endpoint": API_URL,
        "consulta": CONSULTA,
        "filas": len(df),
        "paginas": offset // TAM_PAGINA + 1,
        "archivo": str(ruta),
        "con_token": bool(token),
    }
    (salida / "raw_sisben_agregado.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Extracción exitosa. Filas: {len(df)} | Columnas: {list(df.columns)}")
    print(f"Crudo guardado en: {ruta}")
    print(f"Lote: {meta['batch_id']}")
    return df


if __name__ == "__main__":
    extract_sisben_data()