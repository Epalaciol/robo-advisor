"""Corre el motor financiero (`core/`) sobre precios reales descargados a
`data_local/` (ver `scripts/descargar_precios_prueba.py`). Sirve para validar
el motor con datos de mercado reales sin necesitar Supabase.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.markowitz import cal, min_varianza, tangente
from roboadvisor.core.portafolio_completo import componer
from roboadvisor.core.retornos import estimar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_PRECIOS = RAIZ / "data_local" / "precios.csv"
RUTA_RF = RAIZ / "data_local" / "rf.csv"
BENCHMARK = "ACWI"


def main() -> None:
    if not RUTA_PRECIOS.exists() or not RUTA_RF.exists():
        raise SystemExit(
            f"Faltan {RUTA_PRECIOS.name}/{RUTA_RF.name} en data_local/. "
            "Corre primero: python scripts/descargar_precios_prueba.py"
        )

    params = ParametrosFinancieros()

    crudo = pd.read_csv(RUTA_PRECIOS, parse_dates=["fecha"])
    precios = crudo.pivot(index="fecha", columns="ticker", values="adj_close").sort_index()
    tickers_riesgo = [t for t in precios.columns if t != BENCHMARK]

    rf_df = pd.read_csv(RUTA_RF, parse_dates=["fecha"])
    rf = float(rf_df["tasa_anual"].iloc[-1])

    est = estimar(precios[tickers_riesgo], rf, params.ventana_meses, params.min_meses)
    print(f"Estimación: {est.n_meses} meses, rf={est.rf:.2%}, fecha_fin={est.fecha_fin.date()}")

    port_min_var = min_varianza(est, params.w_max)
    print("\nMínima varianza:")
    print(port_min_var.w.round(4))
    print(f"  retorno={port_min_var.retorno:.2%} sigma={port_min_var.sigma:.2%}")

    port_tangente = tangente(est, params.w_max)
    print("\nTangente (óptimo de riesgo):")
    print(port_tangente.w.round(4))
    print(
        f"  retorno={port_tangente.retorno:.2%} sigma={port_tangente.sigma:.2%} "
        f"sharpe={port_tangente.sharpe:.3f}"
    )
    if port_tangente.advertencia:
        print(f"  advertencia: {port_tangente.advertencia}")

    pendiente, intercepto = cal(port_tangente, est.rf)
    print(f"\nCAL: E(r) = {intercepto:.4f} + {pendiente:.4f}·sigma")

    print("\nPortafolio completo por perfil (A):")
    for a in (8, 6, 4, 3, 1):
        completo = componer(port_tangente, est.rf, a)
        print(
            f"  A={a}: y*={completo.y:.3f} retorno={completo.retorno:.2%} "
            f"sigma={completo.sigma:.2%} utilidad={completo.utilidad:.4f}"
        )


if __name__ == "__main__":
    main()
