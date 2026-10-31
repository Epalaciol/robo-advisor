"""Optimización de Markowitz: mínima varianza, tangente, frontera y CAL.

Ver docs/03-motor-financiero.md §4. Restricciones: `Σw = 1`, `0 ≤ w_i ≤ w_max`
(con `w_max` efectivo ajustado a `max(w_max, 1/n)` si el solicitado era
inalcanzable). Solver: `scipy.optimize.minimize(method="SLSQP")`.
Tolerancia numérica documentada: `TOL = 1e-6` (holgura en pruebas de pesos
y restricciones; `ftol`/`maxiter` del solver están fijados para resultados
deterministas y sin warnings de SciPy no controlados).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

from roboadvisor.core.retornos import Estimacion

TOL = 1e-6


@dataclass(frozen=True)
class Portafolio:
    """Un portafolio de riesgo: pesos, retorno, σ, Sharpe y advertencia opcional."""

    w: pd.Series
    retorno: float
    sigma: float
    sharpe: float
    advertencia: str | None = None


def _w_max_efectivo(w_max: float, n: int) -> tuple[float, str | None]:
    minimo = 1 / n
    if w_max < minimo:
        return minimo, f"w_max ajustado de {w_max:.4f} a {minimo:.4f} (= 1/{n})"
    return w_max, None


def _metricas(
    w: np.ndarray, mu: np.ndarray, sigma: np.ndarray, rf: float
) -> tuple[float, float, float]:
    retorno = float(w @ mu)
    sigma_p = float(np.sqrt(w @ sigma @ w))
    sharpe = (retorno - rf) / sigma_p if sigma_p > 0 else 0.0
    return retorno, sigma_p, sharpe


def _resolver_min_varianza(
    mu: np.ndarray, sigma: np.ndarray, w_max_eff: float, objetivo_retorno: float | None = None
) -> np.ndarray:
    n = len(mu)
    x0 = np.full(n, 1 / n)
    bounds = [(0.0, w_max_eff)] * n
    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if objetivo_retorno is not None:
        restricciones.append({"type": "eq", "fun": lambda w: w @ mu - objetivo_retorno})

    resultado = minimize(
        lambda w: w @ sigma @ w,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=restricciones,
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not resultado.success:
        raise RuntimeError(f"Optimización de mínima varianza no convergió: {resultado.message}")
    w = np.clip(resultado.x, 0, w_max_eff)
    return w / w.sum()


def _con_advertencia(port: Portafolio, aviso: str) -> Portafolio:
    advertencia = f"{aviso}; {port.advertencia}" if port.advertencia else aviso
    return Portafolio(
        w=port.w,
        retorno=port.retorno,
        sigma=port.sigma,
        sharpe=port.sharpe,
        advertencia=advertencia,
    )


def min_varianza(est: Estimacion, w_max: float) -> Portafolio:
    """Portafolio de mínima varianza global: `min wᵀΣw` s.t. `Σw=1`, `0≤w≤w_max`."""
    mu = est.mu.to_numpy()
    sigma = est.sigma.to_numpy()
    n = len(mu)
    w_max_eff, nota = _w_max_efectivo(w_max, n)

    w = _resolver_min_varianza(mu, sigma, w_max_eff)
    retorno, sigma_p, sharpe = _metricas(w, mu, sigma, est.rf)

    return Portafolio(
        w=pd.Series(w, index=est.tickers),
        retorno=retorno,
        sigma=sigma_p,
        sharpe=sharpe,
        advertencia=nota,
    )


def tangente(est: Estimacion, w_max: float) -> Portafolio:
    """Portafolio tangente (óptimo de riesgo): `max (wᵀμ − rf) / √(wᵀΣw)`.

    Si ningún activo supera a `rf` (no hay Sharpe positivo alcanzable), se
    devuelve el de mínima varianza con `advertencia`.
    """
    mu = est.mu.to_numpy()
    sigma = est.sigma.to_numpy()
    n = len(mu)
    w_max_eff, nota = _w_max_efectivo(w_max, n)

    if not (est.mu > est.rf).any():
        aviso = "Ningún activo supera a rf: se devuelve mínima varianza"
        return _con_advertencia(min_varianza(est, w_max), aviso)

    x0 = np.full(n, 1 / n)
    bounds = [(0.0, w_max_eff)] * n
    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def sharpe_negativo(w: np.ndarray) -> float:
        _, sigma_p, sharpe = _metricas(w, mu, sigma, est.rf)
        return -sharpe if sigma_p > 0 else 0.0

    resultado = minimize(
        sharpe_negativo,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=restricciones,
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not resultado.success:
        raise RuntimeError(f"Optimización del tangente no convergió: {resultado.message}")

    w = np.clip(resultado.x, 0, w_max_eff)
    w = w / w.sum()
    retorno, sigma_p, sharpe = _metricas(w, mu, sigma, est.rf)

    if sharpe <= 0:
        aviso = "Sharpe del tangente <= 0: se devuelve mínima varianza"
        return _con_advertencia(min_varianza(est, w_max), aviso)

    return Portafolio(
        w=pd.Series(w, index=est.tickers),
        retorno=retorno,
        sigma=sigma_p,
        sharpe=sharpe,
        advertencia=nota,
    )


def _retorno_maximo_factible(mu: np.ndarray, w_max_eff: float) -> float:
    """Máximo `wᵀμ` alcanzable con `Σw=1`, `0≤w≤w_max` (programa lineal)."""
    n = len(mu)
    resultado = linprog(
        c=-mu,
        A_eq=[np.ones(n)],
        b_eq=[1.0],
        bounds=[(0.0, w_max_eff)] * n,
        method="highs",
    )
    if not resultado.success:
        raise RuntimeError(f"No se pudo hallar el retorno máximo factible: {resultado.message}")
    return float(-resultado.fun)


def frontera(est: Estimacion, w_max: float, n_puntos: int = 40) -> pd.DataFrame:
    """Frontera eficiente: para una malla de `n_puntos` retornos objetivo entre
    el retorno de mínima varianza y el máximo alcanzable, `min wᵀΣw` s.t. `wᵀμ=target`.

    Devuelve `DataFrame[retorno, sigma, pesos]` (una fila por punto; `pesos`
    es un `dict[ticker, peso]`).
    """
    mu = est.mu.to_numpy()
    sigma = est.sigma.to_numpy()
    n = len(mu)
    w_max_eff, _ = _w_max_efectivo(w_max, n)

    port_min_var = min_varianza(est, w_max)
    retorno_min = port_min_var.retorno
    retorno_max = _retorno_maximo_factible(mu, w_max_eff)

    objetivos = np.linspace(retorno_min, retorno_max, n_puntos)
    filas = []
    for objetivo in objetivos:
        w = _resolver_min_varianza(mu, sigma, w_max_eff, objetivo_retorno=objetivo)
        retorno, sigma_p, _ = _metricas(w, mu, sigma, est.rf)
        filas.append(
            {
                "retorno": retorno,
                "sigma": sigma_p,
                "pesos": dict(zip(est.tickers, w, strict=True)),
            }
        )
    return pd.DataFrame(filas)


def cal(port_tangente: Portafolio, rf: float) -> tuple[float, float]:
    """Capital Allocation Line óptima: `E(r) = rf + S*·σ`.

    Devuelve `(pendiente, intercepto) = (S*, rf)`.
    """
    return port_tangente.sharpe, rf


def portafolios_aleatorios(
    est: Estimacion, w_max: float, n: int = 400, semilla: int = 7
) -> pd.DataFrame:
    """Nube de portafolios factibles aleatorios (`Σw=1`, `0≤w≤w_max`), casi
    todos **no eficientes** (por debajo/dentro de la frontera). Es solo para
    graficar junto a `frontera()` y mostrar visualmente por qué la frontera es
    la frontera; no influye en ningún cálculo. Determinista (semilla fija).
    """
    mu = est.mu.to_numpy()
    sigma = est.sigma.to_numpy()
    n_activos = len(mu)
    w_max_eff, _ = _w_max_efectivo(w_max, n_activos)

    rng = np.random.default_rng(semilla)
    filas = []
    intentos = 0
    while len(filas) < n and intentos < n * 50:
        intentos += 1
        w = rng.dirichlet(np.ones(n_activos))
        if (w > w_max_eff + TOL).any():
            continue
        retorno, sigma_p, _ = _metricas(w, mu, sigma, est.rf)
        filas.append({"retorno": retorno, "sigma": sigma_p})

    return pd.DataFrame(filas, columns=["retorno", "sigma"])
