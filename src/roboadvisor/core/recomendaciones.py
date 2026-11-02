"""Recomendaciones con reglas fijas (sin IA). Ver docs/03 §9.

Todas llevan el aviso "Ejercicio académico; no constituye asesoría financiera."
y usan lenguaje de sugerencia ("considerar", "revisar"), nunca una orden de
compra/venta concreta.
"""

from dataclasses import dataclass, field

import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.multiplos import SenalMultiplo

AVISO_ACADEMICO = (
    "Ejercicio académico; no constituye asesoría de inversión ni recomendación de "
    "compra o venta de valores."
)

_ORDEN_SEVERIDAD = {"accion": 0, "aviso": 1, "info": 2}


@dataclass(frozen=True)
class Recomendacion:
    """Una recomendación con su severidad y los números que la sustentan."""

    id: str
    severidad: str  # "accion" | "aviso" | "info"
    ticker: str | None
    titulo: str
    detalle: str
    datos: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextoRecomendacion:
    """Insumos para generar recomendaciones sobre un portafolio guardado."""

    pesos_actuales: pd.Series
    pesos_optimos_hoy: pd.Series
    retornos_12m: pd.Series
    rf_12m: float
    vol_realizada: float | None
    sigma_objetivo: float
    senales_multiplos: list[SenalMultiplo]
    tickers_portafolio: list[str]
    antiguedad_dias: dict[str, int]
    params: ParametrosFinancieros


def _r1_deriva_pesos(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    umbral = ctx.params.umbral_desvio
    umbral_accion = 2 * umbral
    recomendaciones = []

    for ticker in ctx.pesos_actuales.index:
        actual = ctx.pesos_actuales[ticker]
        optimo = ctx.pesos_optimos_hoy.get(ticker, 0.0)
        desvio = abs(actual - optimo)
        if desvio <= umbral:
            continue

        severidad = "accion" if desvio > umbral_accion else "aviso"
        recomendaciones.append(
            Recomendacion(
                id="R1",
                severidad=severidad,
                ticker=ticker,
                titulo="Peso desviado del óptimo",
                detalle=(
                    f"El peso actual de {ticker} se desvió {desvio:.1%} de su peso "
                    "óptimo recalculado hoy. Se sugiere evaluar un rebalanceo."
                ),
                datos={"peso_actual": actual, "peso_optimo_hoy": optimo, "desvio": desvio},
            )
        )
    return recomendaciones


def _r2_activo_rezagado(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    recomendaciones = []
    for ticker, retorno in ctx.retornos_12m.items():
        peso_actual = ctx.pesos_actuales.get(ticker, 0.0)
        if retorno < ctx.rf_12m and peso_actual > ctx.params.min_peso_alerta:
            recomendaciones.append(
                Recomendacion(
                    id="R2",
                    severidad="aviso",
                    ticker=ticker,
                    titulo="Activo rezagado frente a la tasa libre de riesgo",
                    detalle=(
                        f"{ticker} rindió {retorno:.1%} en 12 meses, por debajo de la "
                        f"tasa libre de riesgo ({ctx.rf_12m:.1%}). Se sugiere revisar su posición."
                    ),
                    datos={
                        "retorno_12m": retorno,
                        "rf_12m": ctx.rf_12m,
                        "peso_actual": peso_actual,
                    },
                )
            )
    return recomendaciones


def _r3_fuera_de_perfil(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    if ctx.vol_realizada is None:
        return []

    limite = ctx.sigma_objetivo * (1 + ctx.params.tol_vol)
    if ctx.vol_realizada <= limite:
        return []

    return [
        Recomendacion(
            id="R3",
            severidad="accion",
            ticker=None,
            titulo="Volatilidad fuera del perfil de riesgo",
            detalle=(
                f"La volatilidad realizada ({ctx.vol_realizada:.1%}) supera en más de "
                f"{ctx.params.tol_vol:.0%} el objetivo de su perfil ({ctx.sigma_objetivo:.1%}). "
                "Se sugiere revisar la asignación del portafolio."
            ),
            datos={
                "vol_realizada": ctx.vol_realizada,
                "sigma_objetivo": ctx.sigma_objetivo,
                "limite": limite,
            },
        )
    ]


def _r4_multiplos(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    recomendaciones = []
    for senal in ctx.senales_multiplos:
        if senal.ticker not in ctx.tickers_portafolio:
            continue
        if senal.senal not in ("cara", "barata"):
            continue

        verbo = "subponderar" if senal.senal == "cara" else "sobreponderar"
        recomendaciones.append(
            Recomendacion(
                id="R4",
                severidad="info",
                ticker=senal.ticker,
                titulo=f"Señal de múltiplos: {senal.ticker} está {senal.senal}",
                detalle=(
                    f"El P/E de {senal.ticker} ({senal.pe:.1f}) está {senal.senal} frente a "
                    f"sus comparables (z={senal.z:.2f}). Se sugiere {verbo} ligeramente."
                ),
                datos={"pe": senal.pe, "z": senal.z, "tilt_sugerido": senal.tilt_sugerido},
            )
        )
    return recomendaciones


def _r5_datos_viejos(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    recomendaciones = []
    for ticker, dias in ctx.antiguedad_dias.items():
        if dias > ctx.params.dias_stale:
            recomendaciones.append(
                Recomendacion(
                    id="R5",
                    severidad="aviso",
                    ticker=ticker,
                    titulo="Datos de precio desactualizados",
                    detalle=(
                        f"El último precio de {ticker} tiene {dias} días hábiles de "
                        "antigüedad. Se sugiere verificar la fuente de datos."
                    ),
                    datos={"dias_antiguedad": dias, "umbral": ctx.params.dias_stale},
                )
            )
    return recomendaciones


def generar(ctx: ContextoRecomendacion) -> list[Recomendacion]:
    """Aplica las reglas R1–R5 (fijas, explicables) y agrega R0 si ninguna activó.

    Orden final: `accion` > `aviso` > `info`.
    """
    recomendaciones = [
        *_r1_deriva_pesos(ctx),
        *_r2_activo_rezagado(ctx),
        *_r3_fuera_de_perfil(ctx),
        *_r4_multiplos(ctx),
        *_r5_datos_viejos(ctx),
    ]

    if not recomendaciones:
        recomendaciones = [
            Recomendacion(
                id="R0",
                severidad="info",
                ticker=None,
                titulo="Todo en orden",
                detalle="Sin desviaciones relevantes frente a los parámetros del portafolio.",
                datos={},
            )
        ]

    recomendaciones.sort(key=lambda r: _ORDEN_SEVERIDAD[r.severidad])

    for r in recomendaciones:
        r.datos.setdefault("aviso", AVISO_ACADEMICO)

    return recomendaciones
