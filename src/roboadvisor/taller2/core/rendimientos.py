"""TIR, duración, convexidad y DV01 (con la misma base días/365 que `TIR.NO.PER`/XIRR).

VP(y) = Σ flujo · (1 + y)^(−t)
Duración Macaulay D = Σ t·VP / P ; modificada D* = D / (1 + y)
Convexidad C = Σ t(t+1)·VP / (P·(1 + y)²)
DV01 = N/100 · [P(y − ½pb) − P(y + ½pb)]   (pesos que gana N de nominal si la TIR baja 1 pb)
"""

import numpy as np
from scipy.optimize import brentq

from ..config import NOMINAL_DV01, PB
from .modelos import Betas, Flujos
from .nelson_siegel import precio


def valor_presente(y: float, f: Flujos) -> float:
    return float(np.sum(f.montos * (1 + y) ** (-f.t)))


def tir(precio_: float, f: Flujos) -> float:
    """Tasa efectiva anual que iguala los flujos al precio (equivale a TIR.NO.PER de Excel)."""
    return float(brentq(lambda y: valor_presente(y, f) - precio_, -0.5, 2.0, xtol=1e-14))


def duracion_macaulay(y: float, f: Flujos) -> float:
    vp = f.montos * (1 + y) ** (-f.t)
    return float(np.sum(f.t * vp) / np.sum(vp))


def duracion_modificada(y: float, f: Flujos) -> float:
    return duracion_macaulay(y, f) / (1 + y)


def convexidad(y: float, f: Flujos) -> float:
    vp = f.montos * (1 + y) ** (-f.t)
    return float(np.sum(f.t * (f.t + 1) * vp) / (np.sum(vp) * (1 + y) ** 2))


def dv01(y: float, f: Flujos, nominal: int = NOMINAL_DV01) -> float:
    """DV01 por revaluación (±½ pb) para `nominal` pesos de valor nominal."""
    return (valor_presente(y - PB / 2, f) - valor_presente(y + PB / 2, f)) * nominal / 100


def dv01_analitico(y: float, f: Flujos, precio_: float, nominal: int = NOMINAL_DV01) -> float:
    """N · (P/100) · D* · 1 pb."""
    return nominal * (precio_ / 100) * duracion_modificada(y, f) * PB


def dv01_curva(f: Flujos, betas: Betas, tau: float, nominal: int = NOMINAL_DV01) -> float:
    """DV01 ante un desplazamiento paralelo de 1 pb de toda la curva spot (β0 ± ½ pb)."""
    arriba = Betas(betas.b0 + PB / 2, betas.b1, betas.b2)
    abajo = Betas(betas.b0 - PB / 2, betas.b1, betas.b2)
    return (precio(f, abajo, tau) - precio(f, arriba, tau)) * nominal / 100


def aproximacion_precio(
    y: float, f: Flujos, cambios=(-0.01, -0.005, 0.005, 0.01)
) -> list[dict[str, float]]:
    """ΔP/P exacto vs. aproximación por duración y por duración + convexidad."""
    p0 = valor_presente(y, f)
    dm, c = duracion_modificada(y, f), convexidad(y, f)
    return [
        {
            "cambio_pb": dy / PB,
            "exacto": valor_presente(y + dy, f) / p0 - 1,
            "duracion": -dm * dy,
            "duracion_convexidad": -dm * dy + 0.5 * c * dy**2,
        }
        for dy in cambios
    ]
