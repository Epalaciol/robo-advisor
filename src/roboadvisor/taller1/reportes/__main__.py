"""`python -m roboadvisor.taller1.reportes` → PDF y Excel del Taller 1 en `entregas/taller-1/`."""

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd

from roboadvisor.comun.readme_pdf import readme_a_pdf

from .caso import calcular_caso
from .excel import generar_excel
from .informe import generar_pdf

RAIZ = Path(__file__).resolve().parents[4]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, default=RAIZ / "entregas" / "taller-1")
    ap.add_argument("--datos", type=Path, default=RAIZ / "data_local" / "taller1")
    ap.add_argument("--voluntarios", type=Path, default=None, help="CSV de voluntarios (opcional)")
    a = ap.parse_args()

    precios = (
        pd.read_csv(a.datos / "precios.csv", parse_dates=["fecha"])
        .pivot(index="fecha", columns="ticker", values="adj_close")
        .sort_index()
    )
    rf = float(pd.read_csv(a.datos / "rf.csv")["tasa_anual"].iloc[-1])
    caso = calcular_caso(precios, rf)
    ruta_vol = a.voluntarios or a.salida / "datos" / "voluntarios.csv"
    voluntarios = pd.read_csv(ruta_vol, dtype=str) if ruta_vol.exists() else None

    a.salida.mkdir(parents=True, exist_ok=True)
    print("Excel:", generar_excel(caso, a.salida / "Taller1.xlsx", voluntarios))
    print("PDF:  ", generar_pdf(caso, a.salida, voluntarios, dt.date.today()))

    if (a.salida / "README.md").exists():
        print(
            "README:", readme_a_pdf(a.salida / "README.md", a.salida / "README_Taller1.pdf", RAIZ)
        )


if __name__ == "__main__":
    main()
