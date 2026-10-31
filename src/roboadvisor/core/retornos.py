"""Retornos mensuales y estimación de μ, Σ, rf a partir de un panel de precios.

Ver docs/03-motor-financiero.md §3. `core/` es puro: recibe `DataFrame`s y
devuelve dataclasses, sin acceso a red ni a Supabase.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.covariance import LedoitWolf


@dataclass(frozen=True)
class Estimacion:
    """Estimación de μ, Σ y rf sobre una ventana de retornos mensuales."""

    tickers: list[str]
    mu: pd.Series
    sigma: pd.DataFrame
    rf: float
    n_meses: int
    fecha_fin: pd.Timestamp


def retornos_mensuales(precios: pd.DataFrame) -> pd.DataFrame:
    """Cierre de mes (`resample("ME").last()`) → retorno simple mensual.

    `r_t = P_t / P_{t-1} - 1`. Se descartan filas con cualquier `NaN`, lo que
    alinea los tickers a su fecha común.
    """
    precios_mensuales = precios.resample("ME").last()
    retornos = precios_mensuales.pct_change()
    return retornos.dropna(how="any")


def estimar(
    precios: pd.DataFrame,
    rf: float,
    ventana_meses: int,
    min_meses: int,
) -> Estimacion:
    """Estima μ (anualizada ×12) y Σ (anualizada ×12, Ledoit-Wolf) sobre los
    últimos `ventana_meses` retornos mensuales, exigiendo `>= min_meses`
    observaciones *por ticker* (antes de alinear a fecha común).

    `rf` se recibe ya anualizado y en decimal (tasa de la última fecha).
    """
    precios_mensuales = precios.resample("ME").last()
    retornos_por_ticker = precios_mensuales.pct_change()
    n_validos = retornos_por_ticker.notna().sum()

    cortos = n_validos[n_validos < min_meses].index.tolist()
    if cortos:
        raise ValueError(
            f"Historia insuficiente (< {min_meses} meses de retornos) para: {cortos}"
        )

    retornos = retornos_por_ticker.dropna(how="any").tail(ventana_meses)

    tickers = list(precios.columns)
    mu = 12 * retornos.mean()
    sigma_valores = 12 * LedoitWolf().fit(retornos.to_numpy()).covariance_
    sigma = pd.DataFrame(sigma_valores, index=tickers, columns=tickers)

    return Estimacion(
        tickers=tickers,
        mu=mu,
        sigma=sigma,
        rf=rf,
        n_meses=len(retornos),
        fecha_fin=retornos.index[-1],
    )
