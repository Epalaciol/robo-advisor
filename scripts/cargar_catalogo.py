"""Carga (upsert, idempotente) `supabase/seed/activos.csv` en la tabla `activos`.

Usa `service_role` (ignora RLS): solo correr desde la máquina del
administrador o el pipeline, nunca desde la app. Requiere `SUPABASE_URL` y
`SUPABASE_SERVICE_ROLE_KEY` en `.env`.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.data.cliente import cliente_servicio

RAIZ = Path(__file__).resolve().parent.parent
SEED_CSV = RAIZ / "supabase" / "seed" / "activos.csv"
COLUMNAS_BOOLEANAS = ["es_renta_fija", "activo"]


def cargar_filas(ruta_csv: Path = SEED_CSV) -> list[dict]:
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


def main() -> None:
    filas = cargar_filas()
    cliente = cliente_servicio()
    resultado = cliente.table("activos").upsert(filas, on_conflict="ticker").execute()
    print(f"Catálogo cargado: {len(resultado.data)} filas (upsert sobre 'ticker').")


if __name__ == "__main__":
    main()
