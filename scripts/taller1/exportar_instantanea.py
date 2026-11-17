"""Exporta de Supabase (solo lectura) la instantánea de datos que usan los informes del Taller 1.

Escribe `data_local/taller1/precios.csv` y `rf.csv` con todo el catálogo activo y el benchmark,
ya con las conversiones de moneda del pipeline. Así `python -m roboadvisor.taller1.reportes`
se repite offline con los mismos números. Usa `service_role` (solo lectura); correr desde la
máquina del administrador, nunca desde la app.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.comun.cliente import cliente_servicio
from roboadvisor.comun.paginacion import leer_todo

DESTINO = Path(__file__).resolve().parents[2] / "data_local" / "taller1"


def main() -> None:
    c = cliente_servicio()
    activos = c.table("activos").select("ticker").eq("activo", True).execute().data
    tickers = sorted(a["ticker"] for a in activos)
    filas = []
    for t in tickers:  # por ticker: evita paginar un volumen enorme de una sola vez
        filas += leer_todo(
            lambda t=t: (
                c.table("precios")
                .select("ticker, fecha, close, adj_close, volumen")
                .eq("ticker", t)
                .order("fecha")
            )
        )
    precios = pd.DataFrame(filas)
    rf = pd.DataFrame(
        leer_todo(lambda: c.table("tasa_libre_riesgo").select("fecha, tasa_anual").order("fecha"))
    )
    DESTINO.mkdir(parents=True, exist_ok=True)
    precios.to_csv(DESTINO / "precios.csv", index=False)
    rf.to_csv(DESTINO / "rf.csv", index=False)
    print(f"{len(tickers)} activos, {len(precios)} precios hasta {precios['fecha'].max()}")
    print(f"{len(rf)} tasas libres de riesgo hasta {rf['fecha'].max()}")


if __name__ == "__main__":
    main()
