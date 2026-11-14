"""Retornos diarios y estimación de μ, Σ, rf a partir de un panel de precios.

Ver docs/03-motor-financiero.md §3. `core/` es puro: recibe `DataFrame`s y
devuelve dataclasses, sin acceso a red ni a Supabase.

Todos los activos del catálogo son ETF que cotizan en el mismo calendario
(bolsa de EE.UU.), por lo que los retornos diarios quedan alineados sin
remuestrear.
"""

from dataclasses import dataclass

import pandas as pd

DIAS_ANIO = 252


@dataclass(frozen=True)
class Estimacion:
    """Estimación de μ, Σ y rf sobre una ventana de retornos diarios."""

    tickers: list[str]
    mu: pd.Series
    sigma: pd.DataFrame
    rf: float
    n_obs: int
    fecha_fin: pd.Timestamp


def retornos_diarios(precios: pd.DataFrame) -> pd.DataFrame:
    """Retorno simple diario `r_t = P_t / P_{t-1} - 1`.

    Se descartan filas con cualquier `NaN`, lo que alinea los tickers a su
    fecha común (el activo de historia más corta fija el inicio).
    """
    return precios.sort_index().pct_change().dropna(how="any")


def estimar(
    precios: pd.DataFrame,
    rf: float,
    ventana_dias: int,
    min_dias: int,
) -> Estimacion:
    """Estima μ (anualizada ×252) y Σ (covarianza muestral anualizada ×252) sobre los
    últimos `ventana_dias` retornos diarios, exigiendo `>= min_dias`
    observaciones *por ticker* (antes de alinear a fecha común).

    `rf` se recibe ya anualizado y en decimal (tasa de la última fecha).
    """
    retornos_por_ticker = precios.sort_index().pct_change()
    n_validos = retornos_por_ticker.notna().sum()

    cortos = n_validos[n_validos < min_dias].index.tolist()
    if cortos:
        raise ValueError(f"Historia insuficiente (< {min_dias} días de retornos) para: {cortos}")

    retornos = retornos_por_ticker.dropna(how="any").tail(ventana_dias)

    tickers = list(precios.columns)
    mu = DIAS_ANIO * retornos.mean()
    # Covarianza muestral (ddof=1), igual que `daily_returns.cov() * 252` de los scripts del curso.
    sigma = pd.DataFrame(
        DIAS_ANIO * retornos.cov().to_numpy(), index=tickers, columns=tickers
    )

    return Estimacion(
        tickers=tickers,
        mu=mu,
        sigma=sigma,
        rf=rf,
        n_obs=len(retornos),
        fecha_fin=retornos.index[-1],
    )
