import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.riesgo import (
    beta_portafolio,
    betas,
    contribucion_riesgo,
    duration_portafolio,
)


@pytest.fixture
def benchmark_sintetico():
    rng = np.random.default_rng(1)
    return pd.Series(rng.normal(0.01, 0.04, size=60))


def test_beta_de_si_mismo_es_uno(benchmark_sintetico):
    r = betas(pd.DataFrame({"M": benchmark_sintetico}), benchmark_sintetico)
    assert r["M"] == pytest.approx(1.0)


def test_beta_de_el_doble_del_benchmark_es_dos(benchmark_sintetico):
    doble = benchmark_sintetico * 2
    r = betas(pd.DataFrame({"X2": doble}), benchmark_sintetico)
    assert r["X2"] == pytest.approx(2.0)


def test_beta_no_correlacionado_es_cercana_a_cero(benchmark_sintetico):
    rng = np.random.default_rng(99)
    no_correlacionado = pd.Series(rng.normal(0.0, 0.03, size=60))
    r = betas(pd.DataFrame({"Y": no_correlacionado}), benchmark_sintetico)
    assert abs(r["Y"]) < 0.3


def test_beta_portafolio_normalizada_y_contribucion():
    betas_equity = pd.Series({"A": 1.2, "B": 0.8})
    pesos = pd.Series({"A": 0.3, "B": 0.2, "BONO": 0.5})

    r = beta_portafolio(betas_equity, pesos)
    peso_equity = 0.5
    beta_esperada = (0.3 * 1.2 + 0.2 * 0.8) / peso_equity

    assert r["beta_normalizada"] == pytest.approx(beta_esperada)
    assert r["contribucion_total"] == pytest.approx(beta_esperada * peso_equity)


def test_duration_portafolio_50_50_con_4_y_8():
    durations = pd.Series({"BONO_A": 4.0, "BONO_B": 8.0})
    pesos = pd.Series({"BONO_A": 0.25, "BONO_B": 0.25, "ACCION": 0.5})

    r = duration_portafolio(durations, pesos)
    assert r["duration_rf_normalizada"] == pytest.approx(6.0)
    assert r["contribucion_total"] == pytest.approx(6.0 * 0.5)


def test_contribucion_riesgo_suma_uno():
    w = pd.Series({"A": 0.6, "B": 0.4})
    sigma = pd.DataFrame([[0.04, 0.01], [0.01, 0.09]], index=["A", "B"], columns=["A", "B"])
    contrib = contribucion_riesgo(w, sigma)
    assert contrib.sum() == pytest.approx(1.0)
