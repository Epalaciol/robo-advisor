import numpy as np
import pandas as pd
import pytest

from roboadvisor.taller1.config import ParametrosFinancieros
from roboadvisor.taller1.core.seleccion import (
    es_apalancado,
    estadisticas_activos,
    peso_retorno,
    seleccion_referencia,
)

P = ParametrosFinancieros()


def _candidatos(n_por_clase: int = 3, n_obs: int = 500) -> pd.DataFrame:
    """Catálogo sintético: 6 clases; dentro de cada clase, retorno y volatilidad crecientes."""
    filas = {}
    for i, clase in enumerate(["rf_a", "rf_b", "rv_a", "rv_b", "reit", "cripto"]):
        for j in range(n_por_clase):
            base = 0.02 + 0.04 * i  # las clases "altas" rinden y fluctúan más
            filas[f"{clase}{j}"] = {
                "clase": clase,
                "nombre": f"ETF {clase}{j}",
                "mu": base + 0.01 * j,
                "sigma": 0.03 + 0.05 * i + 0.01 * j,
                "n": n_obs,
            }
    return pd.DataFrame.from_dict(filas, orient="index")


def test_peso_retorno_es_continuo_y_acotado():
    assert peso_retorno(1, P) == 1.0 and peso_retorno(8, P) == 0.0
    assert peso_retorno(0.2, P) == 1.0 and peso_retorno(20, P) == 0.0  # se acota al rango
    valores = [peso_retorno(a, P) for a in (1, 2, 3.5, 5, 6.2, 8)]
    assert valores == sorted(valores, reverse=True)


def test_a_menor_mas_retorno_a_mayor_menos_volatilidad():
    c = _candidatos()
    res = {a: seleccion_referencia(a, c, P) for a in (1, 3, 4.5, 6, 8)}
    mu = {a: c.loc[t, "mu"].mean() for a, t in res.items()}
    sig = {a: c.loc[t, "sigma"].mean() for a, t in res.items()}
    assert mu[1] > mu[8] and sig[1] > sig[8]
    assert list(mu.values()) == sorted(mu.values(), reverse=True)
    assert list(sig.values()) == sorted(sig.values(), reverse=True)


def test_selecciona_hasta_11_distintos_con_tope_por_clase():
    c = _candidatos(n_por_clase=4)
    sel = seleccion_referencia(4, c, P)
    assert len(sel) == 11 == len(set(sel))
    por_clase = c.loc[sel, "clase"].value_counts()
    assert por_clase.max() <= P.sel_max_por_clase and len(por_clase) >= P.sel_n_clases


def test_excluye_apalancados_y_activos_con_poca_historia():
    c = _candidatos()
    c.loc["cripto2", "nombre"] = "ProShares UltraPro QQQ (3x Nasdaq 100)"
    c.loc["rv_b0", "n"] = P.min_dias - 1
    sel = seleccion_referencia(1, c, P)
    assert "cripto2" not in sel and "rv_b0" not in sel


@pytest.mark.parametrize(
    "nombre,esperado",
    [
        ("ProShares UltraPro QQQ (3x Nasdaq 100)", True),
        ("Direxion Technology Bull 3X", True),
        ("ProShares Ultra Bloomberg Crude Oil (2x)", True),
        ("SPDR S&P 500 ETF", False),
        ("iShares Core US Aggregate Bond ETF", False),
    ],
)
def test_detecta_apalancados_por_nombre(nombre, esperado):
    assert es_apalancado(nombre) is esperado


def test_pocos_candidatos_devuelve_los_que_haya_y_vacio_si_no_hay():
    c = _candidatos(n_por_clase=1)
    assert len(seleccion_referencia(4, c.head(4), P)) == 4
    assert seleccion_referencia(4, c.assign(n=0), P) == []


def test_estadisticas_activos_anualiza():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2024-01-01", periods=400)
    ret = rng.normal(0.0005, 0.01, size=(400, 2))
    precios = pd.DataFrame(100 * np.cumprod(1 + ret, axis=0), index=idx, columns=["A", "B"])
    est = estadisticas_activos(precios, 300)
    assert (est["n"] == 300).all()
    assert est["sigma"].between(0.10, 0.22).all()  # ≈ 0,01 · √252 ≈ 0,16
