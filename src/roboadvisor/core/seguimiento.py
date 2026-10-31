"""Seguimiento compra-y-mantiene de un portafolio guardado. Ver docs/03 §7.

Supuesto: **compra y mantiene** desde `fecha_base` — las cantidades iniciales
`q_i = V0·w_i / P_i(base)` se calculan una sola vez y no se rebalancean; los
pesos se dejan "derivar" con el precio. La parte libre de riesgo (`RF`) crece
día a día a la tasa vigente ese día (`rf_serie`, si se provee); si no hay
`rf_serie`, crece a la tasa fija `rf_base`. El rebalanceo es solo una
*recomendación* (E06), nunca se aplica aquí.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

TICKER_RF = "RF"
MIN_OBSERVACIONES = 2
MIN_OBSERVACIONES_SHARPE = 60
DIAS_HABILES_ANIO = 252


@dataclass(frozen=True)
class Seguimiento:
    """Resultado de valorar un portafolio desde su `fecha_base` hasta hoy."""

    valor: pd.Series
    retorno_acum: float | None
    retorno_anualizado: float | None
    vol_realizada: float | None
    max_drawdown: float | None
    sharpe_realizado: float | None
    pesos_actuales: pd.Series | None
    contribucion: pd.Series | None
    suficiente: bool


def _factor_crecimiento_rf(
    fechas: pd.DatetimeIndex, rf_base: float, rf_serie: pd.Series | None
) -> pd.Series:
    """Factor de crecimiento diario de la pata RF: `(1+rf_t)^(1/252)` para
    cada fecha, usando `rf_serie` (tasa vigente ese día, con `ffill`) o,
    si no se provee, la tasa fija `rf_base` para todo el período.
    """
    if rf_serie is None:
        tasas = pd.Series(rf_base, index=fechas)
    else:
        tasas = rf_serie.reindex(fechas).ffill().fillna(rf_base)
    return (1 + tasas) ** (1 / DIAS_HABILES_ANIO)


def valorar(
    pesos_completo: pd.Series,
    fecha_base: pd.Timestamp,
    rf_base: float,
    precios: pd.DataFrame,
    rf_serie: pd.Series | None = None,
    v0: float = 100.0,
) -> Seguimiento:
    """Valora compra-y-mantiene desde `fecha_base` con los pesos guardados.

    `pesos_completo` incluye los tickers de riesgo y la clave `"RF"` (peso
    libre de riesgo); `precios` trae solo los tickers de riesgo, diario,
    desde `fecha_base` en adelante.
    """
    precios_periodo = precios.loc[precios.index >= fecha_base].sort_index()
    fechas = precios_periodo.index

    tickers_riesgo = [t for t in pesos_completo.index if t != TICKER_RF]
    peso_rf = float(pesos_completo.get(TICKER_RF, 0.0))

    if len(fechas) < MIN_OBSERVACIONES:
        valor_base = pd.Series([v0], index=fechas[:1] if len(fechas) else [fecha_base])
        return Seguimiento(
            valor=valor_base,
            retorno_acum=None,
            retorno_anualizado=None,
            vol_realizada=None,
            max_drawdown=None,
            sharpe_realizado=None,
            pesos_actuales=pesos_completo,
            contribucion=None,
            suficiente=False,
        )

    precios_base = precios_periodo.iloc[0][tickers_riesgo]
    cantidades = v0 * pesos_completo[tickers_riesgo] / precios_base

    valor_riesgo = precios_periodo[tickers_riesgo].mul(cantidades, axis=1).sum(axis=1)

    factores_rf = _factor_crecimiento_rf(fechas, rf_base, rf_serie)
    valor_rf = pd.Series(index=fechas, dtype=float)
    valor_rf.iloc[0] = v0 * peso_rf
    for i in range(1, len(fechas)):
        valor_rf.iloc[i] = valor_rf.iloc[i - 1] * factores_rf.iloc[i]

    valor = valor_riesgo + valor_rf

    retorno_acum = float(valor.iloc[-1] / valor.iloc[0] - 1)

    dias_totales = (fechas[-1] - fechas[0]).days
    retorno_anualizado = (
        float((valor.iloc[-1] / valor.iloc[0]) ** (365 / dias_totales) - 1)
        if dias_totales >= 365
        else None
    )

    retornos_diarios = valor.pct_change().dropna()
    vol_realizada = float(retornos_diarios.std(ddof=1) * np.sqrt(DIAS_HABILES_ANIO))

    drawdown = valor / valor.cummax() - 1
    max_drawdown = float(drawdown.min())

    if len(retornos_diarios) >= MIN_OBSERVACIONES_SHARPE:
        rf_promedio = float(factores_rf.mean() ** DIAS_HABILES_ANIO - 1)
        sharpe_realizado = float(
            (retornos_diarios.mean() * DIAS_HABILES_ANIO - rf_promedio) / vol_realizada
        )
    else:
        sharpe_realizado = None

    valores_finales = {t: cantidades[t] * precios_periodo[t].iloc[-1] for t in tickers_riesgo}
    valores_finales[TICKER_RF] = valor_rf.iloc[-1]
    pesos_actuales = pd.Series(valores_finales) / valor.iloc[-1]

    valores_iniciales = {t: cantidades[t] * precios_base[t] for t in tickers_riesgo}
    valores_iniciales[TICKER_RF] = valor_rf.iloc[0]
    contribucion = pd.Series(
        {k: (valores_finales[k] - valores_iniciales[k]) / valor.iloc[0] for k in valores_finales}
    )

    return Seguimiento(
        valor=valor,
        retorno_acum=retorno_acum,
        retorno_anualizado=retorno_anualizado,
        vol_realizada=vol_realizada,
        max_drawdown=max_drawdown,
        sharpe_realizado=sharpe_realizado,
        pesos_actuales=pesos_actuales,
        contribucion=contribucion,
        suficiente=True,
    )


def valorar_benchmark(
    precios_benchmark: pd.Series,
    fecha_base: pd.Timestamp,
    v0: float = 100.0,
    nombre: str = "ACWI",
) -> Seguimiento:
    """Mismo cálculo de `valorar()` para un benchmark de un solo activo (100% riesgo)."""
    pesos_completo = pd.Series({nombre: 1.0, TICKER_RF: 0.0})
    precios = precios_benchmark.to_frame(name=nombre)
    return valorar(pesos_completo, fecha_base, rf_base=0.0, precios=precios, v0=v0)
