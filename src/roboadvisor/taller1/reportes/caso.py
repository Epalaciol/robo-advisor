"""Caso de referencia del Taller 1: 11 ETF → portafolio de riesgo óptimo → portafolio completo.

Función pura sobre DataFrames (sin red ni Supabase): recibe precios y tasa libre de riesgo y
devuelve todo lo que necesitan el Excel y el PDF. Usa exactamente el motor de la app (`core`).
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.taller1.config import ParametrosFinancieros
from roboadvisor.taller1.core.cuestionario import PERFILES, puntuar
from roboadvisor.taller1.core.markowitz import Portafolio, cal, frontera, min_varianza, tangente
from roboadvisor.taller1.core.portafolio_completo import (
    PortafolioCompleto,
    componer,
    escenarios_por_a,
)
from roboadvisor.taller1.core.retornos import Estimacion, estimar, retornos_diarios
from roboadvisor.taller1.core.riesgo import beta_portafolio, betas, duration_portafolio
from roboadvisor.taller1.core.seleccion import estadisticas_activos, seleccion_referencia

# 11 ETF (el número que menciona el enunciado), uno o dos por cada clase de activo pedida.
UNIVERSO_REFERENCIA: dict[str, str] = {
    "SPY": "Acciones EE.UU. (S&P 500)",
    "QQQ": "Acciones EE.UU. (Nasdaq 100)",
    "EFA": "Acciones EAFE (desarrollados ex-EE.UU.)",
    "EEM": "Acciones mercados emergentes",
    "ILF": "Acciones Latinoamérica",
    "LQD": "Renta fija grado de inversión EE.UU.",
    "IEF": "Bonos del Tesoro EE.UU. 7-10 años",
    "HYG": "Renta fija alto rendimiento (HY) EE.UU.",
    "EMB": "Renta fija emergente en USD",
    "VNQ": "REIT (finca raíz EE.UU.)",
    "GLD": "Oro",
}
# Duration (años) de los ETF de renta fija, tomadas del catálogo `supabase/seed/activos.csv`.
DURATIONS: dict[str, float] = {"LQD": 8.4, "IEF": 7.5, "HYG": 3.5, "EMB": 7.0}
BENCHMARK = "ACWI"
VALORES_A = [8, 6, 4, 3, 1]


@dataclass(frozen=True)
class CasoReferencia:
    params: ParametrosFinancieros
    universo: dict[str, str]
    est: Estimacion
    tangente: Portafolio
    min_var: Portafolio
    frontera: pd.DataFrame
    cal_pendiente: float
    rf: float
    escenarios: pd.DataFrame  # una fila por A (8, 6, 4, 3, 1)
    betas: pd.Series  # β de cada ETF de renta variable frente a ACWI
    beta_port: dict
    duration_port: dict
    precios: pd.DataFrame
    ventana: tuple[pd.Timestamp, pd.Timestamp]


def calcular_caso(
    precios: pd.DataFrame, rf: float, params: ParametrosFinancieros | None = None
) -> CasoReferencia:
    """Calcula el caso con el motor de la app. `precios`: fecha × ticker (incluye ACWI)."""
    params = params or ParametrosFinancieros()
    tickers = list(UNIVERSO_REFERENCIA)
    est = estimar(precios[tickers], rf, params.ventana_dias, params.min_dias)
    tang = tangente(est, params.w_max, params.w_min)
    minv = min_varianza(est, params.w_max, params.w_min)
    fr = frontera(est, params.w_max, w_min=params.w_min)
    pendiente, _ = cal(tang, rf)
    esc = escenarios_por_a(tang, rf, VALORES_A)

    ret = (
        retornos_diarios(precios[[*tickers, BENCHMARK]]).dropna(how="any").tail(params.ventana_dias)
    )
    acciones = [t for t in tickers if t not in DURATIONS and t not in ("GLD", "VNQ")]
    b = betas(ret[acciones], ret[BENCHMARK])
    dur = pd.Series(DURATIONS)
    return CasoReferencia(
        params=params,
        universo=dict(UNIVERSO_REFERENCIA),
        est=est,
        tangente=tang,
        min_var=minv,
        frontera=fr,
        cal_pendiente=pendiente,
        rf=rf,
        escenarios=esc,
        betas=b,
        beta_port=beta_portafolio(b, tang.w),
        duration_port=duration_portafolio(dur, tang.w),
        precios=precios,
        ventana=(ret.index[0], ret.index[-1]),
    )


def portafolio_de_voluntario(caso: CasoReferencia, respuestas: dict[str, str]) -> dict:
    """Puntaje → perfil → A → portafolio completo de un voluntario."""
    r = puntuar(respuestas)
    pc: PortafolioCompleto = componer(caso.tangente, caso.rf, r.a)
    return {
        "puntaje": r.puntaje,
        "perfil": r.etiqueta,
        "a": r.a,
        "y": pc.y,
        "peso_rf": pc.peso_rf,
        "retorno": pc.retorno,
        "sigma": pc.sigma,
        "utilidad": pc.utilidad,
    }


TABLA_PERFILES = [(a, b, etiqueta, A) for a, b, _clave, etiqueta, A in PERFILES]


@dataclass(frozen=True)
class SeleccionPerfil:
    """La selección de 11 activos que sugiere la app para un A y su resultado con Markowitz."""

    a: int
    perfil: str
    tickers: list[str]
    vol_media: float  # volatilidad media anual de los 11 activos
    ret_medio: float  # retorno medio histórico anual de los 11 activos
    retorno: float | None = None  # portafolio de riesgo óptimo (tangente) de esa selección
    sigma: float | None = None
    sharpe: float | None = None
    y: float | None = None
    retorno_completo: float | None = None
    n_obs: int | None = None  # retornos diarios en común usados (los activos jóvenes la acortan)


def selecciones_por_perfil(
    precios: pd.DataFrame, catalogo: list[dict], rf: float, params: ParametrosFinancieros
) -> list[SeleccionPerfil]:
    """Aplica la regla de `core/seleccion.py` a cada perfil del cuestionario (A = 8, 6, 4, 3, 1)."""
    activos = {a["ticker"]: a for a in catalogo if a["activo"] and a["rol"] == "invertible"}
    cols = [t for t in activos if t in precios.columns]
    stats = estadisticas_activos(precios[cols], params.ventana_dias)
    stats["clase"] = [activos[t]["clase"] for t in stats.index]
    stats["nombre"] = [activos[t]["nombre"] for t in stats.index]
    etiquetas = {a: e for _mn, _mx, _k, e, a in PERFILES}
    salida = []
    for a in VALORES_A:
        tickers = seleccion_referencia(a, stats, params)
        base = {
            "a": a,
            "perfil": etiquetas[a],
            "tickers": tickers,
            "vol_media": float(stats.loc[tickers, "sigma"].mean()),
            "ret_medio": float(stats.loc[tickers, "mu"].mean()),
        }
        try:
            est = estimar(precios[tickers], rf, params.ventana_dias, params.min_dias)
            tang = tangente(est, params.w_max, params.w_min)
            comp = componer(tang, rf, a)
            base |= {
                "retorno": tang.retorno,
                "sigma": tang.sigma,
                "sharpe": tang.sharpe,
                "y": comp.y,
                "retorno_completo": comp.retorno,
                "n_obs": est.n_obs,
            }
        except ValueError:
            pass  # historia insuficiente para optimizar esa selección
        salida.append(SeleccionPerfil(**base))
    return salida
