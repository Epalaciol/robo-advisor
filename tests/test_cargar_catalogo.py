from scripts.cargar_catalogo import cargar_filas


def test_cargar_filas_normaliza_tipos():
    filas = cargar_filas()
    assert len(filas) == 23

    por_ticker = {f["ticker"]: f for f in filas}

    tes = por_ticker["TES_COP"]
    assert tes["es_renta_fija"] is True
    assert tes["activo"] is False
    assert tes["duration"] == 5.0

    gxg = por_ticker["EC"]
    assert gxg["es_renta_fija"] is False
    assert gxg["activo"] is True
    assert gxg["duration"] is None
