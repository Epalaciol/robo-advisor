import csv
from pathlib import Path

import pytest

from roboadvisor.taller1.core.seleccion import SELECCION_POR_A, seleccion_referencia

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed" / "activos.csv"


def _catalogo_activo() -> set[str]:
    with open(SEED, encoding="utf-8") as fh:
        return {
            f["ticker"]
            for f in csv.DictReader(fh)
            if f["rol"] == "invertible" and f["activo"] == "true"
        }


@pytest.mark.parametrize("a", [8, 6, 4, 3, 1])
def test_cada_perfil_tiene_11_activos_distintos_del_catalogo(a):
    sel = seleccion_referencia(a)
    assert len(sel) == 11 == len(set(sel))
    assert set(sel) <= _catalogo_activo()


def test_los_perfiles_conservadores_llevan_mas_renta_fija_y_los_agresivos_cripto():
    renta_fija = {"BNDX", "TIP", "AGG", "IEF", "LQD", "HYG", "EMB"}
    n_rf = {a: len(renta_fija & set(sel)) for a, sel in SELECCION_POR_A.items()}
    assert n_rf[8] > n_rf[6] >= n_rf[4] > n_rf[3] > n_rf[1]
    assert "IBIT" in SELECCION_POR_A[1] and "IBIT" not in SELECCION_POR_A[8]


def test_a_intermedio_usa_el_perfil_mas_cercano():
    assert seleccion_referencia(7) in (list(SELECCION_POR_A[8]), list(SELECCION_POR_A[6]))
    assert seleccion_referencia(3.9) == list(SELECCION_POR_A[4])
    assert seleccion_referencia(0.5) == list(SELECCION_POR_A[1])
