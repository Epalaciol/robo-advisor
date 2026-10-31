import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.retornos import estimar, retornos_mensuales


def test_retornos_mensuales_simples():
    fechas = pd.date_range("2024-01-31", periods=4, freq="ME")
    precios = pd.DataFrame({"X": [100, 110, 99, 110]}, index=fechas)
    r = retornos_mensuales(precios)
    assert list(r["X"].round(4)) == [0.1, -0.1, 0.1111]


def test_estimar_calcula_mu_sigma_rf(estimacion_sintetica):
    est = estimacion_sintetica
    assert est.rf == 0.02
    assert set(est.tickers) == {"ACT_A", "ACT_B", "ACT_C", "ACT_D", "ACT_E"}
    assert len(est.mu) == 5
    assert est.sigma.shape == (5, 5)
    assert est.n_meses <= 60
    assert est.n_meses >= 36


def test_estimar_error_con_historia_corta():
    fechas = pd.date_range("2020-01-31", periods=20, freq="ME")
    rng = np.random.default_rng(0)
    precios = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.01, 0.03, size=(20, 2)), axis=0),
        index=fechas,
        columns=["CORTO", "LARGO"],
    )
    # Alarga "LARGO" con más historia previa, pero no "CORTO".
    fechas_largas = pd.date_range("2015-01-31", periods=80, freq="ME")
    precios_largo_completo = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.01, 0.03, size=(80, 1)), axis=0),
        index=fechas_largas,
        columns=["LARGO"],
    )
    panel = precios_largo_completo.join(precios[["CORTO"]], how="outer")

    with pytest.raises(ValueError, match="CORTO"):
        estimar(panel, rf=0.02, ventana_meses=60, min_meses=36)
