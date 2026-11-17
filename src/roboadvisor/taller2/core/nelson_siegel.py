"""Curva Nelson-Siegel (hoja `CalculoCurva` del Excel del profesor).

S(t) = β0 + β1·(1 − e^(−t/τ))/(t/τ) + β2·[(1 − e^(−t/τ))/(t/τ) − e^(−t/τ)]   (efectiva anual)
DF(t) = (1 + S(t))^(−t)        P_est = Σ flujo · DF(t)
Límites: S(0⁺) = β0 + β1 ; S(∞) = β0. La "joroba" de β2 está en t ≈ 1,7934·τ.
"""

import numpy as np
import pandas as pd

from .modelos import Betas, Flujos

T_MINIMO = 1e-10


def _carga(t: np.ndarray, tau: float) -> tuple[np.ndarray, np.ndarray]:
    x = np.maximum(np.asarray(t, dtype=float), T_MINIMO) / tau
    expo = np.exp(-x)
    return (1 - expo) / x, expo


def spot(t, betas: Betas, tau: float):
    """Tasa spot efectiva anual para el plazo t (años). Acepta escalar o arreglo."""
    carga, expo = _carga(t, tau)
    s = betas.b0 + betas.b1 * carga + betas.b2 * (carga - expo)
    return float(s) if np.ndim(t) == 0 else s


def descuento(t, betas: Betas, tau: float):
    t_arr = np.asarray(t, dtype=float)
    df = (1 + spot(t_arr, betas, tau)) ** (-t_arr)
    return float(df) if np.ndim(t) == 0 else df


def precio(f: Flujos, betas: Betas, tau: float) -> float:
    """Precio teórico (sucio) por $100 de facial con la curva."""
    return float(np.sum(f.montos * descuento(f.t, betas, tau)))


def curva(betas: Betas, tau: float, dias: int = 10_950, dias_ano: int = 365) -> pd.DataFrame:
    """Curva cero cupón de 1 a `dias` días (hoja DatosCurvaSpot)."""
    d = np.arange(1, dias + 1)
    t = d / dias_ano
    s = spot(t, betas, tau)
    return pd.DataFrame({"dias": d, "anos": t, "tasa_spot": s, "factor_descuento": (1 + s) ** -t})
