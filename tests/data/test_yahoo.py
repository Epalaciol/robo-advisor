import pandas as pd

from roboadvisor.data.yahoo import _extraer_cierres, parsear_descarga_precios


def _bruto_multiindice() -> pd.DataFrame:
    fechas = pd.date_range("2024-01-02", periods=3, freq="D")
    columnas = pd.MultiIndex.from_product(
        [["AAA", "BBB"], ["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
    )
    datos = {
        ("AAA", "Close"): [10.0, 11.0, 12.0],
        ("AAA", "Adj Close"): [9.5, 10.5, 11.5],
        ("AAA", "Volume"): [100, 110, 120],
        ("BBB", "Close"): [20.0, 21.0, float("nan")],
        ("BBB", "Adj Close"): [19.5, 20.5, float("nan")],
        ("BBB", "Volume"): [200, 210, 0],
    }
    df = pd.DataFrame(index=fechas, columns=columnas, dtype=float)
    for clave, valores in datos.items():
        df[clave] = valores
    return df


def test_parsea_formato_multiindice():
    bruto = _bruto_multiindice()
    resultado = parsear_descarga_precios(bruto, ["AAA", "BBB"])

    assert set(resultado.columns) == {"ticker", "fecha", "close", "adj_close", "volumen"}
    assert set(resultado["ticker"]) == {"AAA", "BBB"}

    aaa = resultado[resultado["ticker"] == "AAA"].sort_values("fecha")
    assert list(aaa["adj_close"]) == [9.5, 10.5, 11.5]

    # BBB solo tiene 2 filas válidas (la tercera es NaN y se descarta)
    bbb = resultado[resultado["ticker"] == "BBB"]
    assert len(bbb) == 2


def test_parsea_formato_plano_un_solo_ticker():
    fechas = pd.date_range("2024-01-02", periods=2, freq="D")
    bruto = pd.DataFrame(
        {"Close": [5.0, 5.5], "Adj Close": [4.9, 5.4], "Volume": [50, 55]}, index=fechas
    )
    resultado = parsear_descarga_precios(bruto, ["SOLO"])

    assert len(resultado) == 2
    assert (resultado["ticker"] == "SOLO").all()
    assert list(resultado["adj_close"]) == [4.9, 5.4]


def test_ticker_sin_columnas_se_omite():
    bruto = _bruto_multiindice()
    resultado = parsear_descarga_precios(bruto, ["AAA", "NO_EXISTE"])
    assert "NO_EXISTE" not in set(resultado["ticker"])


def test_extraer_cierres_multiindice_un_solo_ticker():
    # yfinance >= reciente devuelve MultiIndex (campo, ticker) incluso para un ticker
    fechas = pd.date_range("2024-01-02", periods=3, freq="D")
    columnas = pd.MultiIndex.from_product([["Close", "Open"], ["^TNX"]])
    bruto = pd.DataFrame([[4.0, 4.1], [4.2, 4.1], [4.1, 4.2]], index=fechas, columns=columnas)

    cierres = _extraer_cierres(bruto)
    assert list(cierres) == [4.0, 4.2, 4.1]


def test_extraer_cierres_columnas_planas():
    fechas = pd.date_range("2024-01-02", periods=2, freq="D")
    bruto = pd.DataFrame({"Close": [4.0, 4.1], "Open": [3.9, 4.0]}, index=fechas)

    cierres = _extraer_cierres(bruto)
    assert list(cierres) == [4.0, 4.1]
