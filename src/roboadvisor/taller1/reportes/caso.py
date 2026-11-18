"""Caso de referencia del Taller 1: 11 ETF → portafolio de riesgo óptimo → portafolio completo.

Función pura sobre DataFrames (sin red ni Supabase): recibe precios y tasa libre de riesgo y
devuelve todo lo que necesitan el Excel y el PDF. Usa exactamente el motor de la app (`core`).
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.taller1.config import UNIVERSO_REFERENCIA, ParametrosFinancieros
from roboadvisor.taller1.core.cuestionario import PERFILES, puntuar
from roboadvisor.taller1.core.markowitz import Portafolio, cal, frontera, min_varianza, tangente
from roboadvisor.taller1.core.portafolio_completo import (
    PortafolioCompleto,
    componer,
    escenarios_por_a,
)
from roboadvisor.taller1.core.retornos import Estimacion, estimar, retornos_diarios
from roboadvisor.taller1.core.riesgo import beta_portafolio, betas, duration_portafolio

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
