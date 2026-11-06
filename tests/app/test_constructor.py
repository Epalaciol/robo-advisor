import pandas as pd
from ui.constructor import armar_registro_portafolio

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.portafolio_completo import componer
from roboadvisor.core.retornos import Estimacion

PARAMS = ParametrosFinancieros()


def _estimacion() -> Estimacion:
    tickers = ["B", "A", "C"]
    mu = pd.Series([0.08, 0.10, 0.06], index=tickers)
    sigma = pd.DataFrame(
        [[0.04, 0.0, 0.0], [0.0, 0.09, 0.0], [0.0, 0.0, 0.02]], index=tickers, columns=tickers
    )
    return Estimacion(
        tickers=tickers,
        mu=mu,
        sigma=sigma,
        rf=0.02,
        n_obs=1260,
        fecha_fin=pd.Timestamp("2024-12-31"),
    )


def _port_riesgo(est: Estimacion) -> Portafolio:
    w = pd.Series({"B": 0.3, "A": 0.5, "C": 0.2})
    retorno = float(w @ est.mu)
    sigma_p = float((w.to_numpy() @ est.sigma.to_numpy() @ w.to_numpy()) ** 0.5)
    return Portafolio(w=w, retorno=retorno, sigma=sigma_p, sharpe=(retorno - est.rf) / sigma_p)


def test_armar_registro_portafolio_tipos_y_sumas():
    est = _estimacion()
    port_riesgo = _port_riesgo(est)
    port_completo = componer(port_riesgo, est.rf, a=4)

    payload = armar_registro_portafolio(
        user_id="user-1",
        encuesta_id="encuesta-1",
        a_usado=4,
        perfil_usado="moderado",
        est=est,
        port_riesgo=port_riesgo,
        port_completo=port_completo,
        params=PARAMS,
        fecha_base="2024-12-31",
    )

    assert payload["tickers"] == sorted(payload["tickers"])
    assert payload["tickers"] == ["A", "B", "C"]

    suma_pesos_riesgo = sum(payload["pesos_riesgo"].values())
    assert abs(suma_pesos_riesgo - 1.0) < 1e-6

    assert 0.0 <= payload["y_star"] <= 1.0
    assert abs(payload["y_star"] + payload["peso_rf"] - 1.0) < 1e-6

    assert payload["user_id"] == "user-1"
    assert payload["encuesta_id"] == "encuesta-1"
    assert payload["a_usado"] == 4
    assert payload["perfil_usado"] == "moderado"
    assert payload["fecha_base"] == "2024-12-31"
    assert isinstance(payload["metricas"], dict)
    assert isinstance(payload["parametros"], dict)
    assert payload["parametros"]["w_max"] == PARAMS.w_max
