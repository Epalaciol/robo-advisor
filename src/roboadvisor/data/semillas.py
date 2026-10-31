"""Normalización del catálogo semilla (`supabase/seed/activos.csv`).

Compartido entre `scripts/cargar_catalogo.py` (Supabase real) y el cliente
mock (`cliente_mock.py`, para correr la app sin Supabase).
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
SEED_CSV = RAIZ / "supabase" / "seed" / "activos.csv"
COLUMNAS_BOOLEANAS = ["es_renta_fija", "activo"]


def leer_catalogo(ruta_csv: Path = SEED_CSV) -> list[dict]:
    """Lee el CSV y normaliza tipos: booleanos y vacíos (`duration`, `region`...) → `None`."""
    df = pd.read_csv(ruta_csv)
    for col in COLUMNAS_BOOLEANAS:
        df[col] = df[col].astype(str).str.strip().str.lower() == "true"

    filas = df.to_dict(orient="records")
    for fila in filas:
        for clave, valor in fila.items():
            if isinstance(valor, float) and pd.isna(valor):
                fila[clave] = None
    return filas
