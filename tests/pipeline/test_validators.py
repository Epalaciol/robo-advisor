import pandas as pd

from roboadvisor.pipeline.validators import validar_precios

HOY = pd.Timestamp("2024-06-10")


def _precios(filas: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(filas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def _base(n=5, inicio="2024-06-03") -> pd.DataFrame:
    fechas = pd.bdate_range(inicio, periods=n)
    return _precios(
        [
            {"ticker": "X", "fecha": f, "close": 100.0, "adj_close": 100.0, "volumen": 1000}
            for f in fechas
        ]
    )


def test_precio_cero_o_negativo_es_error():
    df = _base()
    df.loc[0, "adj_close"] = 0.0
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert not r.valido
    assert any("adj_close" in e for e in r.errores)


def test_precio_nulo_es_error():
    df = _base()
    df.loc[0, "adj_close"] = None
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert not r.valido


def test_fecha_futura_es_error():
    df = _base(inicio="2024-06-03")
    df.loc[df.index[-1], "fecha"] = HOY + pd.Timedelta(days=5)
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert not r.valido
    assert any("futura" in e for e in r.errores)


def test_fecha_duplicada_es_error():
    df = _base()
    df.loc[1, "fecha"] = df.loc[0, "fecha"]
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert not r.valido
    assert any("duplicada" in e for e in r.errores)


def test_salto_extremo_renta_variable_es_advertencia_no_bloquea():
    df = _base(n=3, inicio="2024-06-03")
    df.loc[1, "adj_close"] = 200.0  # +100% vs 100 -> excede 60%
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert r.valido
    assert any("Salto diario" in a for a in r.advertencias)


def test_salto_extremo_renta_fija_umbral_mas_bajo():
    df = _base(n=3, inicio="2024-06-03")
    df.loc[1, "adj_close"] = 145.0  # +45% vs 100 -> excede 40% de renta fija
    r = validar_precios(df, es_renta_fija=True, fecha_corrida=HOY, dias_stale=5)
    assert r.valido
    assert any("Salto diario" in a for a in r.advertencias)


def test_dato_viejo_es_advertencia():
    df = _base(n=3, inicio="2024-05-01")
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert r.valido
    assert any("atraso" in a for a in r.advertencias)


def test_sin_datos_es_error():
    df = pd.DataFrame(columns=["ticker", "fecha", "close", "adj_close", "volumen"])
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert not r.valido
    assert r.errores == ["Sin datos"]


def test_caso_limpio_sin_advertencias():
    df = _base(n=3, inicio="2024-06-05")
    r = validar_precios(df, es_renta_fija=False, fecha_corrida=HOY, dias_stale=5)
    assert r.valido
    assert r.errores == []
    assert r.advertencias == []
