"""Descarga precios reales de Yahoo a un archivo local (`data_local/`, ignorado
por git) para probar el motor financiero (`core/`) y el modo mock de la app con
datos de mercado reales, sin necesitar Supabase.

Solo ETFs (incluye el benchmark `ACWI`); el catálogo ya no tiene acciones individuales.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.data import yahoo
from roboadvisor.data.semillas import leer_catalogo

RAIZ = Path(__file__).resolve().parent.parent
DATA_LOCAL = RAIZ / "data_local"

BENCHMARK = "ACWI"
NO_ETF: set[str] = set()  # el catálogo ya es solo ETF; se deja por si se agrega otro tipo
ANIOS_HISTORIA = 10


def tickers_etf() -> list[str]:
    """Tickers `activo=true` del catálogo que son ETF (excluye `NO_ETF`)."""
    catalogo = leer_catalogo()
    return sorted(
        {a["ticker"] for a in catalogo if a["activo"] and a["ticker"] not in NO_ETF}
    )


def main() -> None:
    DATA_LOCAL.mkdir(exist_ok=True)

    tickers = tickers_etf()
    if BENCHMARK not in tickers:
        tickers.append(BENCHMARK)
    desde = pd.Timestamp.today().normalize() - pd.DateOffset(years=ANIOS_HISTORIA)

    print(f"Descargando {len(tickers)} ETF ({ANIOS_HISTORIA} años) desde {desde.date()}:")
    print(f"  {tickers}")
    precios = yahoo.descargar_precios(tickers, desde)
    ruta_precios = DATA_LOCAL / "precios.csv"
    precios.to_csv(ruta_precios, index=False)
    print(f"Guardadas {len(precios)} filas en {ruta_precios}")

    tickers_sin_datos = sorted(set(tickers) - set(precios["ticker"].unique()))
    if tickers_sin_datos:
        print(f"Sin datos de Yahoo para: {tickers_sin_datos}")

    print("Descargando tasa libre de riesgo (T-note 10 años, ^TNX)...")
    rf = yahoo.descargar_rf(pd.Timestamp.today().normalize() - pd.DateOffset(years=1))
    ruta_rf = DATA_LOCAL / "rf.csv"
    rf.to_csv(ruta_rf, index=False)
    print(f"Guardadas {len(rf)} filas en {ruta_rf}")


if __name__ == "__main__":
    main()
