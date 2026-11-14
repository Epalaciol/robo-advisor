import pandas as pd
import pytest

from roboadvisor.pipeline.monedas import convertir_a_usd


def _df(fechas, precio):
    return pd.DataFrame(
        {"ticker": "X.CL", "fecha": fechas, "close": precio, "adj_close": precio, "volumen": 1}
    )


def test_convierte_dividiendo_por_el_tipo_de_cambio():
    fechas = pd.DatetimeIndex(["2024-06-03", "2024-06-04"])
    fx = pd.Series([4000.0, 5000.0], index=fechas)
    salida = convertir_a_usd(_df(fechas, 40000.0), fx)
    assert salida["adj_close"].tolist() == pytest.approx([10.0, 8.0])
    assert salida["close"].tolist() == pytest.approx([10.0, 8.0])


def test_alinea_fx_con_ffill_si_faltan_fechas():
    fechas = pd.DatetimeIndex(["2024-06-03", "2024-06-04", "2024-06-05"])
    fx = pd.Series([4000.0, 4200.0], index=pd.DatetimeIndex(["2024-06-03", "2024-06-05"]))
    salida = convertir_a_usd(_df(fechas, 4000.0), fx)
    assert salida["adj_close"].tolist() == pytest.approx([1.0, 1.0, 4000 / 4200])


def test_descarta_filas_anteriores_al_primer_fx_y_no_muta_la_entrada():
    fechas = pd.DatetimeIndex(["2024-06-01", "2024-06-04"])
    fx = pd.Series([4000.0], index=pd.DatetimeIndex(["2024-06-03"]))
    entrada = _df(fechas, 4000.0)
    salida = convertir_a_usd(entrada, fx)
    assert len(salida) == 1
    assert (entrada["adj_close"] == 4000.0).all()
