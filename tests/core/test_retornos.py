import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.retornos import estimar, retornos_diarios


def test_retornos_diarios_simples():
    fechas = pd.bdate_range("2024-01-01", periods=4)
    precios = pd.DataFrame({"X": [100, 110, 99, 110]}, index=fechas)
    r = retornos_diarios(precios)
    assert list(r["X"].round(4)) == [0.1, -0.1, 0.1111]


def test_estimar_calcula_mu_sigma_rf(estimacion_sintetica):
    est = estimacion_sintetica
    assert est.rf == 0.02
    assert set(est.tickers) == {"ACT_A", "ACT_B", "ACT_C", "ACT_D", "ACT_E"}
    assert len(est.mu) == 5
    assert est.sigma.shape == (5, 5)
    assert est.n_obs == 1260


def test_estimar_error_con_historia_corta():
    rng = np.random.default_rng(0)
    fechas = pd.bdate_range("2020-01-01", periods=1000)
    precios = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.0005, 0.01, size=(1000, 2)), axis=0),
        index=fechas,
        columns=["CORTO", "LARGO"],
    )
    precios.loc[precios.index[:700], "CORTO"] = np.nan  # solo 299 retornos válidos

    with pytest.raises(ValueError, match="CORTO"):
        estimar(precios, rf=0.02, ventana_dias=1260, min_dias=504)


def test_sigma_es_covarianza_muestral_anualizada(panel_precios_sintetico):
    est = estimar(panel_precios_sintetico, rf=0.02, ventana_dias=1260, min_dias=252)
    retornos = panel_precios_sintetico.pct_change().dropna().tail(1260)
    esperado = 252 * retornos.cov().to_numpy()
    assert est.sigma.to_numpy() == pytest.approx(esperado)
    assert est.mu.to_numpy() == pytest.approx(252 * retornos.mean().to_numpy())
