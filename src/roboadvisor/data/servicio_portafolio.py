"""Orquesta repositorios + `core` para producir el resumen de "Mi portafolio".

Única función que combina acceso a datos y motor financiero (E10, ver
docs/03 §7 y docs/planificacion/E10-app-mi-portafolio.md); testable con
repositorios falsos (duck-typing: cualquier objeto con los mismos métodos
que `RepositorioUsuario`/`RepositorioMercado` sirve).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.markowitz import Portafolio, tangente
from roboadvisor.core.multiplos import SenalMultiplo, senales_multiplos
from roboadvisor.core.recomendaciones import ContextoRecomendacion, Recomendacion, generar
from roboadvisor.core.retornos import DIAS_ANIO, estimar, retornos_diarios
from roboadvisor.core.seguimiento import Seguimiento, valorar, valorar_benchmark


@dataclass(frozen=True)
class ResumenPortafolio:
    """Todo lo que necesita `pages/3_Mi_portafolio.py` para renderizar."""

    perfil: dict
    encuesta: dict
    portafolio: dict
    fecha_base: pd.Timestamp
    dias_desde_base: int
    ultima_fecha_precio: str | None
    seguimiento: Seguimiento
    seguimiento_benchmark: Seguimiento | None
    benchmark: str
    pesos_iniciales: pd.Series
    pesos_actuales_riesgo: pd.Series
    retorno_esperado: float
    sigma_esperado: float
    tangente_hoy: Portafolio | None
    recomendaciones: list[Recomendacion]
    senales_multiplos: list[SenalMultiplo]
    evolucion_activos: pd.DataFrame  # precio de cada activo desde la fecha base, base 100


def _pesos_actuales_riesgo(seguimiento: Seguimiento) -> pd.Series:
    """Pesos actuales (deriva) normalizados solo sobre la parte de riesgo
    (sin `RF`), para comparar contra el tangente de hoy (que también suma 1)."""
    if not seguimiento.suficiente or seguimiento.pesos_actuales is None:
        return pd.Series(dtype=float)
    actuales = seguimiento.pesos_actuales.drop(labels=["RF"], errors="ignore")
    total = actuales.sum()
    return actuales / total if total > 0 else pd.Series(dtype=float)


def construir_resumen(
    repo_usuario,
    repo_mercado,
    params: ParametrosFinancieros,
    hoy: pd.Timestamp | None = None,
) -> ResumenPortafolio:
    """Arma el `ResumenPortafolio` del usuario autenticado en `repo_usuario`.

    Lanza `ValueError` si falta perfil, encuesta o portafolio (la página debe
    verificar `estado_usuario()` antes y redirigir; esto es un resguardo).
    """
    hoy = (hoy or pd.Timestamp.today()).normalize()

    perfil = repo_usuario.obtener_perfil()
    encuesta = repo_usuario.obtener_encuesta()
    portafolio = repo_usuario.obtener_portafolio()
    if perfil is None or encuesta is None or portafolio is None:
        raise ValueError("Falta perfil, encuesta o portafolio guardado para este usuario.")

    tickers = list(portafolio["tickers"])
    fecha_base = pd.Timestamp(portafolio["fecha_base"])
    w_max_usado = float(portafolio["parametros"]["w_max"])
    w_min_usado = float(portafolio["parametros"].get("w_min", 0.0))  # portafolios previos: 0
    benchmark = params.benchmark

    catalogo = {a["ticker"]: a for a in repo_mercado.listar_catalogo()}
    equity_tickers = [t for t in tickers if not catalogo.get(t, {}).get("es_renta_fija", False)]

    precios = repo_mercado.precios([*tickers, benchmark], fecha_base.date().isoformat())

    # Historia larga (independiente de `fecha_base`) para recalcular hoy la
    # estimación/tangente, igual que haría el Constructor si se armara hoy.
    desde_historia = (hoy - pd.DateOffset(months=params.meses_historia)).date().isoformat()
    precios_historia = repo_mercado.precios([*tickers, benchmark], desde_historia)

    pesos_completo = pd.Series({k: float(v) for k, v in portafolio["pesos_completo"].items()})
    pesos_completo["RF"] = float(portafolio["peso_rf"])
    rf_creacion = float(portafolio["parametros"]["rf"])

    seguimiento = valorar(pesos_completo, fecha_base, rf_creacion, precios[tickers])

    seguimiento_benchmark = None
    if benchmark in precios.columns and precios[benchmark].notna().any():
        seguimiento_benchmark = valorar_benchmark(
            precios[benchmark].dropna(), fecha_base, nombre=benchmark
        )

    precios_periodo = precios.loc[precios.index >= fecha_base, tickers].dropna(how="all")
    evolucion_activos = (
        precios_periodo / precios_periodo.iloc[0] * 100 if len(precios_periodo) else precios_periodo
    )

    pesos_iniciales = pd.Series({k: float(v) for k, v in portafolio["pesos_riesgo"].items()})
    pesos_actuales_riesgo = _pesos_actuales_riesgo(seguimiento)

    rf_hoy = repo_mercado.rf_ultima()
    tangente_hoy: Portafolio | None = None
    try:
        est_hoy = estimar(precios_historia[tickers], rf_hoy, params.ventana_dias, params.min_dias)
        tangente_hoy = tangente(est_hoy, w_max_usado, w_min_usado)
    except ValueError:
        tangente_hoy = None  # historia insuficiente hoy (raro, pero posible con catálogo corto)

    retornos_d = retornos_diarios(precios_historia[tickers]).tail(DIAS_ANIO)
    retornos_12m = (1 + retornos_d).prod() - 1 if len(retornos_d) else pd.Series(dtype=float)

    antiguedad_dias: dict[str, int] = {}
    for t in tickers:
        if t in precios_historia.columns and precios_historia[t].notna().any():
            ultima = precios_historia[t].dropna().index.max()
            antiguedad_dias[t] = int(np.busday_count(ultima.date(), hoy.date()))

    fundamentales = (
        repo_mercado.fundamentales_ultimos(equity_tickers)
        if equity_tickers
        else pd.DataFrame(columns=["ticker", "fecha", "pe"])
    )
    senales = (
        senales_multiplos(fundamentales, equity_tickers, params, hoy) if equity_tickers else []
    )

    recomendaciones: list[Recomendacion] = []
    if tangente_hoy is not None:
        ctx = ContextoRecomendacion(
            pesos_actuales=pesos_actuales_riesgo,
            pesos_optimos_hoy=tangente_hoy.w,
            retornos_12m=retornos_12m,
            rf_12m=rf_hoy,
            vol_realizada=seguimiento.vol_realizada,
            sigma_objetivo=float(portafolio["metricas"]["sigma_completo"]),
            senales_multiplos=senales,
            tickers_portafolio=tickers,
            antiguedad_dias=antiguedad_dias,
            params=params,
        )
        recomendaciones = generar(ctx)

    return ResumenPortafolio(
        perfil=perfil,
        encuesta=encuesta,
        portafolio=portafolio,
        fecha_base=fecha_base,
        dias_desde_base=(hoy - fecha_base).days,
        ultima_fecha_precio=repo_mercado.ultima_fecha_precios(),
        seguimiento=seguimiento,
        seguimiento_benchmark=seguimiento_benchmark,
        benchmark=benchmark,
        pesos_iniciales=pesos_iniciales,
        pesos_actuales_riesgo=pesos_actuales_riesgo,
        retorno_esperado=float(portafolio["metricas"]["retorno_completo"]),
        sigma_esperado=float(portafolio["metricas"]["sigma_completo"]),
        tangente_hoy=tangente_hoy,
        recomendaciones=recomendaciones,
        senales_multiplos=senales,
        evolucion_activos=evolucion_activos,
    )
