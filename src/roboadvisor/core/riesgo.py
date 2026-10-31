"""Beta, duration y métricas de riesgo del portafolio. Ver docs/03 §6."""

import pandas as pd

from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.retornos import Estimacion


def betas(retornos_activos: pd.DataFrame, retornos_benchmark: pd.Series) -> pd.Series:
    """β_i = Cov(r_i, r_m) / Var(r_m) por columna, misma ventana de retornos."""
    var_m = retornos_benchmark.var(ddof=1)
    covarianzas = retornos_activos.apply(lambda col: col.cov(retornos_benchmark))
    return covarianzas / var_m


def beta_portafolio(betas_: pd.Series, pesos_riesgo: pd.Series) -> dict:
    """Beta del portafolio ponderada solo sobre la parte de renta variable
    (tickers presentes en `betas_`), normalizada por su peso conjunto, y la
    contribución de esa beta al total del portafolio.

    Devuelve `{"beta_normalizada": float, "contribucion_total": float}`.
    """
    tickers_equity = betas_.index.intersection(pesos_riesgo.index)
    peso_equity = pesos_riesgo.loc[tickers_equity].sum()

    if peso_equity == 0:
        return {"beta_normalizada": 0.0, "contribucion_total": 0.0}

    numerador = pesos_riesgo.loc[tickers_equity] @ betas_.loc[tickers_equity]
    beta_normalizada = float(numerador / peso_equity)
    return {
        "beta_normalizada": beta_normalizada,
        "contribucion_total": beta_normalizada * float(peso_equity),
    }


def duration_portafolio(durations: pd.Series, pesos_riesgo: pd.Series) -> dict:
    """Duration del portafolio ponderada solo sobre la parte de renta fija
    (tickers presentes en `durations`), normalizada por su peso conjunto, y
    la contribución de esa duration al total del portafolio.

    Devuelve `{"duration_rf_normalizada": float, "contribucion_total": float}`.
    """
    tickers_rf = durations.index.intersection(pesos_riesgo.index)
    peso_rf = pesos_riesgo.loc[tickers_rf].sum()

    if peso_rf == 0:
        return {"duration_rf_normalizada": 0.0, "contribucion_total": 0.0}

    numerador = pesos_riesgo.loc[tickers_rf] @ durations.loc[tickers_rf]
    duration_normalizada = float(numerador / peso_rf)
    return {
        "duration_rf_normalizada": duration_normalizada,
        "contribucion_total": duration_normalizada * float(peso_rf),
    }


def metricas(port: Portafolio, est: Estimacion) -> dict:
    """Resumen de retorno, σ y Sharpe de un portafolio ya optimizado."""
    return {"retorno": port.retorno, "sigma": port.sigma, "sharpe": port.sharpe}


def contribucion_riesgo(w: pd.Series, sigma: pd.DataFrame) -> pd.Series:
    """Contribución de cada activo a la varianza del portafolio: `w_i·(Σw)_i / σ_p²`.

    La serie resultante suma 1.
    """
    w_arr = w.to_numpy()
    sigma_arr = sigma.to_numpy()
    sigma_p2 = float(w_arr @ sigma_arr @ w_arr)
    contribucion = w_arr * (sigma_arr @ w_arr) / sigma_p2
    return pd.Series(contribucion, index=w.index)
