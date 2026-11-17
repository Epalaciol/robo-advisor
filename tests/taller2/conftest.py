from pathlib import Path

import pytest

from roboadvisor.taller2.core.analisis import analizar
from roboadvisor.taller2.datos.informe import leer_csv

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REFERENCIAS = Path(__file__).resolve().parents[2] / "docs" / "taller-2" / "referencias"


@pytest.fixture(scope="session")
def informe_2oct():
    return leer_csv(FIXTURES / "tes_2026-10-02.csv")


@pytest.fixture(scope="session")
def resultado_2oct(informe_2oct):
    return analizar(informe_2oct.papeles(), informe_2oct.fecha)
