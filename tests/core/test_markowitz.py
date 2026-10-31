import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.markowitz import (
    TOL,
    cal,
    frontera,
    min_varianza,
    portafolios_aleatorios,
    tangente,
)
from roboadvisor.core.retornos import Estimacion


def _estimacion_dos_activos_no_correlacionados() -> Estimacion:
    tickers = ["A", "B"]
    mu = pd.Series([0.08, 0.10], index=tickers)
    sigma = pd.DataFrame([[0.04, 0.0], [0.0, 0.09]], index=tickers, columns=tickers)
    return Estimacion(
        tickers=tickers,
        mu=mu,
        sigma=sigma,
        rf=0.02,
        n_meses=60,
        fecha_fin=pd.Timestamp("2024-12-31"),
    )


def test_min_varianza_dos_activos_formula_cerrada():
    est = _estimacion_dos_activos_no_correlacionados()
    port = min_varianza(est, w_max=1.0)

    sigma1_sq, sigma2_sq = 0.04, 0.09
    w1_esperado = sigma2_sq / (sigma1_sq + sigma2_sq)

    assert port.w["A"] == pytest.approx(w1_esperado, abs=1e-4)
    assert port.w["B"] == pytest.approx(1 - w1_esperado, abs=1e-4)
    assert port.w.sum() == pytest.approx(1.0, abs=TOL)


def test_pesos_suman_uno_y_respetan_w_max(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40

    for port in (min_varianza(est, w_max), tangente(est, w_max)):
        assert port.w.sum() == pytest.approx(1.0, abs=1e-6)
        assert (port.w >= -1e-6).all()
        assert (port.w <= w_max + 1e-6).all()

    front = frontera(est, w_max, n_puntos=10)
    for pesos in front["pesos"]:
        valores = np.array(list(pesos.values()))
        assert valores.sum() == pytest.approx(1.0, abs=1e-6)
        assert (valores >= -1e-6).all()
        assert (valores <= w_max + 1e-6).all()


def test_tangente_sharpe_mayor_o_igual_que_portafolios_aleatorios(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40
    port_tangente = tangente(est, w_max)

    rng = np.random.default_rng(123)
    mu = est.mu.to_numpy()
    sigma = est.sigma.to_numpy()
    n = len(mu)

    mejor_sharpe_aleatorio = -np.inf
    intentos = 0
    aceptados = 0
    while aceptados < 5000 and intentos < 200_000:
        intentos += 1
        w = rng.dirichlet(np.ones(n))
        if (w > w_max).any():
            continue
        aceptados += 1
        retorno = w @ mu
        sigma_p = np.sqrt(w @ sigma @ w)
        sharpe = (retorno - est.rf) / sigma_p
        mejor_sharpe_aleatorio = max(mejor_sharpe_aleatorio, sharpe)

    assert port_tangente.sharpe >= mejor_sharpe_aleatorio - 1e-3


def test_frontera_sigma_no_decreciente_en_rama_eficiente(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40
    front = frontera(est, w_max, n_puntos=40)

    sigmas = front["sigma"].to_numpy()
    diffs = np.diff(sigmas)
    assert (diffs >= -1e-4).all()

    port_min_var = min_varianza(est, w_max)
    assert sigmas[0] == pytest.approx(port_min_var.sigma, abs=1e-3)


def test_cal_pasa_por_rf_y_por_el_tangente(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40
    port_tangente = tangente(est, w_max)
    pendiente, intercepto = cal(port_tangente, est.rf)

    assert intercepto == est.rf
    assert pendiente == pytest.approx(port_tangente.sharpe)

    retorno_en_cero = intercepto + pendiente * 0
    assert retorno_en_cero == pytest.approx(est.rf)

    retorno_en_tangente = intercepto + pendiente * port_tangente.sigma
    assert retorno_en_tangente == pytest.approx(port_tangente.retorno, abs=1e-6)


def test_determinismo_dos_corridas_mismos_pesos(estimacion_sintetica):
    est = estimacion_sintetica
    w1 = tangente(est, 0.40).w
    w2 = tangente(est, 0.40).w
    pd.testing.assert_series_equal(w1, w2)


def test_portafolios_aleatorios_son_factibles_y_deterministas(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40

    nube1 = portafolios_aleatorios(est, w_max, n=200)
    nube2 = portafolios_aleatorios(est, w_max, n=200)

    assert set(nube1.columns) == {"retorno", "sigma"}
    assert len(nube1) >= 150  # tolerancia: el rechazo por w_max puede descartar algunos
    assert (nube1["sigma"] >= 0).all()
    pd.testing.assert_frame_equal(nube1, nube2)


def test_portafolios_aleatorios_caen_dentro_o_sobre_la_frontera(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40

    nube = portafolios_aleatorios(est, w_max, n=300)
    port_min_var = min_varianza(est, w_max)

    # ninguno debería tener menor sigma que la mínima varianza (con tolerancia numérica)
    assert (nube["sigma"] >= port_min_var.sigma - 1e-3).all()
