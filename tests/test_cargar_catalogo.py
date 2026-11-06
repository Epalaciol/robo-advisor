from scripts.cargar_catalogo import cargar_filas


def test_cargar_filas_normaliza_tipos():
    filas = cargar_filas()
    assert len(filas) == 32

    por_ticker = {f["ticker"]: f for f in filas}

    tes = por_ticker["TES_COP"]
    assert tes["es_renta_fija"] is True
    assert tes["activo"] is False
    assert tes["duration"] == 5.0

    spy = por_ticker["SPY"]
    assert spy["es_renta_fija"] is False
    assert spy["activo"] is True
    assert spy["duration"] is None
