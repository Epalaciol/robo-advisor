"""Descarga precios reales de Yahoo a un archivo local (`data_local/`, ignorado
por git) para probar el motor financiero (`core/`) con datos de mercado reales,
sin necesitar Supabase. Ver `scripts/demo_motor_real.py`.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.data import yahoo

RAIZ = Path(__file__).resolve().parent.parent
DATA_LOCAL = RAIZ / "data_local"

TICKERS_PRUEBA = ["SPY", "EFA", "EMB", "LQD", "VNQ", "GLD"]
BENCHMARK = "ACWI"
ANIOS_HISTORIA = 6


def main() -> None:
    DATA_LOCAL.mkdir(exist_ok=True)

    tickers = [*TICKERS_PRUEBA, BENCHMARK]
    desde = pd.Timestamp.today().normalize() - pd.DateOffset(years=ANIOS_HISTORIA)

    print(f"Descargando precios de {tickers} desde {desde.date()}...")
    precios = yahoo.descargar_precios(tickers, desde)
    ruta_precios = DATA_LOCAL / "precios.csv"
    precios.to_csv(ruta_precios, index=False)
    print(f"Guardadas {len(precios)} filas en {ruta_precios}")

    print("Descargando tasa libre de riesgo (^IRX)...")
    rf = yahoo.descargar_rf(pd.Timestamp.today().normalize() - pd.DateOffset(years=1))
    ruta_rf = DATA_LOCAL / "rf.csv"
    rf.to_csv(ruta_rf, index=False)
    print(f"Guardadas {len(rf)} filas en {ruta_rf}")


if __name__ == "__main__":
    main()
