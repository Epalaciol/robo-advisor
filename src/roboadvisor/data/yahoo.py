"""Descarga de precios, tasa libre de riesgo y fundamentales desde Yahoo Finance.

Único punto del repo que llama a `yfinance` (la app nunca lo hace, solo el
pipeline). Reintentos con espera creciente; nunca imprime claves (no las usa).
"""

import time

import pandas as pd
import yfinance as yf

REINTENTOS = 3
ESPERA_BASE_SEG = 2.0


def _con_reintentos(func, *args, **kwargs):
    ultimo_error: Exception | None = None
    for intento in range(REINTENTOS):
        try:
            return func(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 - se agrega contexto y se relanza
            ultimo_error = error
            if intento < REINTENTOS - 1:
                time.sleep(ESPERA_BASE_SEG * (intento + 1))
    mensaje = f"Yahoo Finance falló tras {REINTENTOS} intentos: {ultimo_error}"
    raise RuntimeError(mensaje) from ultimo_error


def parsear_descarga_precios(bruto: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Reacomoda el `DataFrame` (multi-índice o plano) de `yfinance.download()`
    a columnas planas `ticker, fecha, close, adj_close, volumen`.
    """
    es_multiindice = isinstance(bruto.columns, pd.MultiIndex)
    filas = []

    for ticker in tickers:
        if es_multiindice:
            if ticker not in bruto.columns.get_level_values(0):
                continue
            sub = bruto[ticker]
        else:
            sub = bruto

        sub = sub.dropna(how="all")
        for fecha, fila in sub.iterrows():
            adj_close = fila["Adj Close"] if "Adj Close" in sub.columns else fila["Close"]
            if pd.isna(adj_close):
                continue
            filas.append(
                {
                    "ticker": ticker,
                    "fecha": pd.Timestamp(fecha).normalize(),
                    "close": fila.get("Close"),
                    "adj_close": adj_close,
                    "volumen": fila.get("Volume"),
                }
            )

    return pd.DataFrame(filas, columns=["ticker", "fecha", "close", "adj_close", "volumen"])


def descargar_precios(tickers: list[str], desde: pd.Timestamp) -> pd.DataFrame:
    """Precios diarios (`close`, `adj_close`, `volumen`) de `tickers` desde `desde`."""
    bruto = _con_reintentos(
        yf.download,
        tickers,
        start=desde.date(),
        auto_adjust=False,
        group_by="ticker",
        progress=False,
    )
    return parsear_descarga_precios(bruto, tickers)


def _extraer_cierres(bruto: pd.DataFrame) -> pd.Series:
    """`Close` de un `DataFrame` de `yfinance.download()`, sea el índice de
    columnas plano o `MultiIndex` (yfinance usa `MultiIndex` incluso para un
    solo ticker en versiones recientes).
    """
    if isinstance(bruto.columns, pd.MultiIndex):
        cierres = bruto.xs("Close", axis=1, level=0).iloc[:, 0]
    else:
        cierres = bruto["Close"]
    return cierres.dropna()


def descargar_fx(par: str, desde: pd.Timestamp) -> pd.Series:
    """Tipo de cambio diario (`Close`) de un par de Yahoo, p. ej. `COP=X` (pesos por USD)."""
    bruto = _con_reintentos(yf.download, par, start=desde.date(), auto_adjust=False, progress=False)
    cierres = _extraer_cierres(bruto)
    cierres.index = pd.to_datetime(cierres.index).normalize()
    return cierres


def descargar_rf(desde: pd.Timestamp) -> pd.DataFrame:
    """Tasa libre de riesgo anual (`^IRX` / 100) desde `desde`."""
    bruto = _con_reintentos(
        yf.download, "^IRX", start=desde.date(), auto_adjust=False, progress=False
    )
    cierres = _extraer_cierres(bruto)
    return pd.DataFrame(
        {
            "fecha": pd.to_datetime(cierres.index).normalize(),
            "tasa_anual": cierres.to_numpy() / 100,
        }
    )


def descargar_fundamentales(ticker: str) -> dict | None:
    """`pe, pb, ev_ebitda, div_yield` de `ticker` (`None` si falta el dato o el ticker)."""
    info = _con_reintentos(lambda: yf.Ticker(ticker).info)
    if not info:
        return None
    return {
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "div_yield": info.get("dividendYield"),
    }
