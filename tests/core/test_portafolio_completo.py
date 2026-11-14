import pandas as pd
import pytest

from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.portafolio_completo import componer, y_star


def _port_riesgo(retorno=0.12, sigma=0.20) -> Portafolio:
    w = pd.Series({"A": 0.6, "B": 0.4})
    return Portafolio(w=w, retorno=retorno, sigma=sigma, sharpe=(retorno - 0.02) / sigma)


def test_y_star_no_decreciente_al_bajar_a():
    port = _port_riesgo()
    valores_y = []
    for a in [8, 6, 4, 3, 1]:
        _, y = y_star(port.retorno, port.sigma, rf=0.02, a=a)
        valores_y.append(y)
    # A decrece en la lista -> y debe ser no decreciente
    assert all(valores_y[i] <= valores_y[i + 1] for i in range(len(valores_y) - 1))


def test_y_star_cero_si_retorno_esperado_menor_que_rf():
    _, y = y_star(er_p=0.01, sigma_p=0.20, rf=0.02, a=4)
    assert y == 0.0


def test_y_star_marca_apalancamiento_si_excede_uno():
    port = _port_riesgo(retorno=0.30, sigma=0.05)
    completo = componer(port, rf=0.02, a=1)
    y_sin_recorte, _ = y_star(port.retorno, port.sigma, rf=0.02, a=1)
    assert y_sin_recorte > 1
    assert completo.apalancamiento_requerido is True
    assert completo.y == 1.0


def test_componer_retorno_y_utilidad_consistentes():
    port = _port_riesgo()
    a = 4
    completo = componer(port, rf=0.02, a=a)

    assert completo.peso_rf == pytest.approx(1 - completo.y)
    assert completo.retorno == pytest.approx(0.02 + completo.y * (port.retorno - 0.02))
    assert completo.sigma == pytest.approx(completo.y * port.sigma)
    assert completo.utilidad == pytest.approx(completo.retorno - 0.5 * a * completo.sigma**2)
    assert completo.pesos_completo["A"] == pytest.approx(completo.y * 0.6)


def test_escenarios_por_a_estan_sobre_la_cal_y_ordenados():
    from roboadvisor.core.portafolio_completo import escenarios_por_a

    port = _port_riesgo()
    df = escenarios_por_a(port, rf=0.02, valores_a=[8, 6, 4, 3, 1])
    assert list(df["a"]) == [8, 6, 4, 3, 1]
    assert df["y"].is_monotonic_increasing
    # todos sobre la CAL: E = rf + Sharpe * sigma
    sharpe = (port.retorno - 0.02) / port.sigma
    assert (df["retorno"] - (0.02 + sharpe * df["sigma"])).abs().max() < 1e-9
    assert (df["peso_rf"] + df["y"] - 1).abs().max() < 1e-12
