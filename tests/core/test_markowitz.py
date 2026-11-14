import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.markowitz import (
    TOL,
    cal,
    frontera,
    min_varianza,
    portafolios_aleatorios,
    rama_ineficiente,
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
        n_obs=1260,
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


def test_rama_ineficiente_completa_la_bala_y_esta_dominada(estimacion_sintetica):
    est = estimacion_sintetica
    w_max = 0.40
    rama = rama_ineficiente(est, w_max, n_puntos=40)
    port_min_var = min_varianza(est, w_max)

    assert not rama.empty
    assert {"retorno", "sigma", "pesos"}.issubset(rama.columns)

    # todos los retornos de la rama no eficiente son <= el de mínima varianza
    # (es la continuación hacia abajo de la hipérbola, desde la misma punta)
    assert (rama["retorno"].to_numpy() <= port_min_var.retorno + 1e-4).all()

    # sigma decrece (en valor absoluto) a medida que el retorno sube hacia la
    # punta: ordenando por retorno ascendente, sigma debe ser no-creciente
    rama_ordenada = rama.sort_values("retorno")
    sigmas = rama_ordenada["sigma"].to_numpy()
    assert (np.diff(sigmas) <= 1e-4).all()

    for pesos in rama["pesos"]:
        valores = np.array(list(pesos.values()))
        assert valores.sum() == pytest.approx(1.0, abs=1e-6)
        assert (valores >= -1e-6).all()
        assert (valores <= w_max + 1e-6).all()


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


def test_frontera_omite_puntos_que_no_convergen_y_sigue(estimacion_sintetica, monkeypatch):
    import roboadvisor.core.markowitz as markowitz_modulo

    est = estimacion_sintetica
    original = markowitz_modulo._resolver_min_varianza
    llamadas = {"n": 0}

    def falla_cada_tercera(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] % 3 == 0:
            raise RuntimeError("no convergió (simulado)")
        return original(*args, **kwargs)

    monkeypatch.setattr(markowitz_modulo, "_resolver_min_varianza", falla_cada_tercera)

    front = frontera(est, 0.40, n_puntos=12)
    assert 0 < len(front) < 12
    assert {"retorno", "sigma", "pesos"}.issubset(front.columns)


def test_frontera_lanza_error_claro_si_todos_los_puntos_fallan(estimacion_sintetica, monkeypatch):
    import roboadvisor.core.markowitz as markowitz_modulo

    est = estimacion_sintetica
    original = markowitz_modulo._resolver_min_varianza

    def falla_solo_en_la_malla(*args, **kwargs):
        # deja pasar la llamada inicial de min_varianza() (sin objetivo_retorno);
        # falla todos los puntos de la malla de la frontera.
        if kwargs.get("objetivo_retorno") is not None:
            raise RuntimeError("no convergió (simulado)")
        return original(*args, **kwargs)

    monkeypatch.setattr(markowitz_modulo, "_resolver_min_varianza", falla_solo_en_la_malla)

    with pytest.raises(RuntimeError, match="ningún punto"):
        frontera(est, 0.40, n_puntos=5)


def test_w_min_se_respeta_en_tangente_y_min_varianza(estimacion_sintetica):
    w_min = 0.10
    for port in (
        tangente(estimacion_sintetica, 0.5, w_min),
        min_varianza(estimacion_sintetica, 0.5, w_min),
    ):
        assert port.w.sum() == pytest.approx(1.0, abs=1e-6)
        assert (port.w >= w_min - 1e-6).all()
        assert (port.w <= 0.5 + 1e-6).all()


def test_w_min_cero_no_cambia_el_resultado(estimacion_sintetica):
    a = tangente(estimacion_sintetica, 0.4)
    b = tangente(estimacion_sintetica, 0.4, w_min=0.0)
    assert a.w.to_numpy() == pytest.approx(b.w.to_numpy(), abs=1e-9)


def test_w_min_inalcanzable_se_baja_a_uno_sobre_n(estimacion_sintetica):
    n = len(estimacion_sintetica.tickers)
    port = tangente(estimacion_sintetica, 1.0, w_min=0.5)  # 5 activos: máximo posible 20 %
    assert port.w.to_numpy() == pytest.approx(np.full(n, 1 / n), abs=1e-6)
    assert port.advertencia is not None


def test_w_min_restringe_sharpe_a_lo_sumo_igual(estimacion_sintetica):
    libre = tangente(estimacion_sintetica, 0.5)
    con_minimo = tangente(estimacion_sintetica, 0.5, w_min=0.10)
    assert con_minimo.sharpe <= libre.sharpe + 1e-9


def test_frontera_y_nube_respetan_w_min(estimacion_sintetica):
    w_min = 0.05
    f = frontera(estimacion_sintetica, 0.5, n_puntos=10, w_min=w_min)
    assert all(min(p.values()) >= w_min - 1e-5 for p in f["pesos"])
    assert not portafolios_aleatorios(estimacion_sintetica, 0.5, n=20, w_min=w_min).empty
