"""Construcción pura del registro de portafolio (sin red, fácil de probar).

El cálculo financiero vive en `core/`; esta función solo empaqueta sus
resultados en el formato que espera `portafolios.insert(...)`.
"""

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.portafolio_completo import PortafolioCompleto
from roboadvisor.core.retornos import Estimacion


def armar_registro_portafolio(
    user_id: str,
    encuesta_id: str,
    a_usado: float,
    perfil_usado: str,
    est: Estimacion,
    port_riesgo: Portafolio,
    port_completo: PortafolioCompleto,
    params: ParametrosFinancieros,
    fecha_base: str,
) -> dict:
    """Payload para `portafolios.insert(...)`: tickers ordenados, pesos que
    suman 1 (±redondeo), `y_star` en `[0, 1]`.
    """
    tickers_ordenados = sorted(port_riesgo.w.index)
    pesos_riesgo = {t: round(float(port_riesgo.w[t]), 6) for t in tickers_ordenados}
    pesos_completo = {
        t: round(float(port_completo.pesos_completo[t]), 6) for t in tickers_ordenados
    }

    return {
        "user_id": user_id,
        "encuesta_id": encuesta_id,
        "a_usado": a_usado,
        "perfil_usado": perfil_usado,
        "tickers": tickers_ordenados,
        "pesos_riesgo": pesos_riesgo,
        "y_star": round(float(port_completo.y), 6),
        "peso_rf": round(float(port_completo.peso_rf), 6),
        "pesos_completo": pesos_completo,
        "metricas": {
            "retorno_riesgo": port_riesgo.retorno,
            "sigma_riesgo": port_riesgo.sigma,
            "sharpe_riesgo": port_riesgo.sharpe,
            "retorno_completo": port_completo.retorno,
            "sigma_completo": port_completo.sigma,
            "utilidad": port_completo.utilidad,
            "apalancamiento_requerido": port_completo.apalancamiento_requerido,
        },
        "parametros": {
            "ventana_dias": params.ventana_dias,
            "min_dias": params.min_dias,
            "w_min": params.w_min,
            "w_max": params.w_max,
            "rf": est.rf,
            "n_obs_usadas": est.n_obs,
        },
        "fecha_base": fecha_base,
    }
