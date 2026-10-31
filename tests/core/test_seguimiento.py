import pandas as pd
import pytest

from roboadvisor.core.seguimiento import valorar


def _precios(valores: list[float], ticker="X", fecha_base="2024-01-02") -> pd.DataFrame:
    fechas = pd.date_range(fecha_base, periods=len(valores), freq="D")
    return pd.DataFrame({ticker: valores}, index=fechas)


def test_precios_constantes_y_rf_cero_da_valor_constante():
    precios = _precios([100.0, 100.0, 100.0])
    pesos = pd.Series({"X": 1.0, "RF": 0.0})
    seg = valorar(pesos, precios.index[0], rf_base=0.0, precios=precios)

    assert seg.suficiente
    assert seg.valor.round(6).nunique() == 1
    assert seg.retorno_acum == pytest.approx(0.0)
    assert seg.max_drawdown == pytest.approx(0.0)


def test_un_solo_activo_100_por_ciento_replica_su_retorno():
    precios = _precios([100.0, 110.0, 121.0])
    pesos = pd.Series({"X": 1.0, "RF": 0.0})
    seg = valorar(pesos, precios.index[0], rf_base=0.0, precios=precios)

    assert seg.retorno_acum == pytest.approx(0.21)
    pd.testing.assert_series_equal(seg.valor, precios["X"], check_names=False)


def test_50_por_ciento_rf_al_5_por_ciento_crece_segun_formula():
    precios = _precios([100.0] * 10, ticker="X")
    pesos = pd.Series({"X": 0.5, "RF": 0.5})
    seg = valorar(pesos, precios.index[0], rf_base=0.05, precios=precios)

    t = 9  # 10 observaciones, día 0 a día 9
    valor_rf_esperado = 50.0 * (1.05) ** (t / 252)
    valor_esperado = 50.0 + valor_rf_esperado  # la parte de riesgo no se mueve (precio constante)

    assert seg.valor.iloc[-1] == pytest.approx(valor_esperado, rel=1e-9)


def test_suficiente_false_con_una_observacion():
    precios = _precios([100.0])
    pesos = pd.Series({"X": 1.0, "RF": 0.0})
    seg = valorar(pesos, precios.index[0], rf_base=0.0, precios=precios)

    assert seg.suficiente is False
    assert seg.retorno_acum is None
    assert seg.vol_realizada is None
    assert seg.sharpe_realizado is None


def test_max_drawdown_serie_conocida():
    precios = _precios([100.0, 120.0, 90.0, 110.0])
    pesos = pd.Series({"X": 1.0, "RF": 0.0})
    seg = valorar(pesos, precios.index[0], rf_base=0.0, precios=precios)

    assert seg.max_drawdown == pytest.approx(-0.25)
