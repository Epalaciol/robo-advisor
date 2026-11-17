"""`python -m roboadvisor.taller2.reportes` → PDF y Excel del 2-oct-2026 en `entregas/taller-2/`."""

import argparse
import datetime as dt
from pathlib import Path

from roboadvisor.comun.readme_pdf import readme_a_pdf

from ..core.analisis import analizar, sensibilidad
from ..datos.informe import leer_csv
from .excel import generar_excel
from .informe import generar_pdf

RAIZ = Path(__file__).resolve().parents[4]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, default=RAIZ / "entregas" / "taller-2")
    ap.add_argument(
        "--tabla", type=Path, default=RAIZ / "tests" / "taller2" / "fixtures" / "tes_2026-10-02.csv"
    )
    a = ap.parse_args()
    inf = leer_csv(a.tabla)
    papeles = inf.papeles()
    r = analizar(papeles, inf.fecha)
    sens = sensibilidad(papeles, inf.fecha)
    a.salida.mkdir(parents=True, exist_ok=True)
    print("Excel:", generar_excel(r, a.salida / "Taller2_2026-10-02.xlsx", sens))
    print("PDF:  ", generar_pdf(r, sens, a.salida, dt.date.today()))

    if (a.salida / "README.md").exists():
        print(
            "README:", readme_a_pdf(a.salida / "README.md", a.salida / "README_Taller2.pdf", RAIZ)
        )


if __name__ == "__main__":
    main()
