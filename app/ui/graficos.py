"""Gráficos Plotly reutilizables (frontera+CAL, pesos, utilidad).

Todos los números ya vienen calculados de `core/`; estas funciones solo
grafican, no implementan fórmulas. Ejes en %, legibles en claro/oscuro.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.utilidad import utilidad as _utilidad

ER_ILUSTRATIVO = 0.08  # solo para el gráfico explicativo de U vs σ, no es un cálculo real


def figura_utilidad_vs_sigma(a: float, er: float = ER_ILUSTRATIVO) -> go.Figure:
    """Curva ilustrativa `U = er − ½·A·σ²` para el `A` del usuario, a un `er` fijo."""
    sigmas = np.linspace(0.01, 0.40, 50)
    utilidades = [_utilidad(er, float(s), a) for s in sigmas]

    fig = go.Figure(go.Scatter(x=sigmas, y=utilidades, mode="lines"))
    fig.update_layout(
        title=f"Utilidad vs σ (ilustrativo, A={a}, E(r)={er:.0%})",
        xaxis_title="σ (desviación estándar)",
        yaxis_title="Utilidad U",
        xaxis_tickformat=".0%",
    )
    return fig


def figura_frontera(
    frontera_df: pd.DataFrame,
    port_min_var: Portafolio,
    port_tangente: Portafolio,
    cal_pendiente: float,
    cal_intercepto: float,
    mu: pd.Series,
    sigma: pd.DataFrame,
    punto_usuario: tuple[float, float] | None = None,
) -> go.Figure:
    """Frontera eficiente, activos individuales, mínima varianza, tangente, CAL
    y (opcional) el punto del portafolio completo del usuario.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=frontera_df["sigma"],
            y=frontera_df["retorno"],
            mode="lines",
            name="Frontera eficiente",
            line={"color": "#1f77b4"},
        )
    )

    sigma_activos = np.sqrt(np.diag(sigma.to_numpy()))
    fig.add_trace(
        go.Scatter(
            x=sigma_activos,
            y=mu.to_numpy(),
            mode="markers+text",
            text=list(mu.index),
            textposition="top center",
            name="Activos individuales",
            marker={"color": "gray", "symbol": "x"},
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[port_min_var.sigma],
            y=[port_min_var.retorno],
            mode="markers",
            name="Mínima varianza",
            marker={"color": "#2a9d8f", "size": 12},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[port_tangente.sigma],
            y=[port_tangente.retorno],
            mode="markers",
            name="Tangente (óptimo de riesgo)",
            marker={"color": "#d62828", "size": 14, "symbol": "star"},
        )
    )

    sigma_max = (
        max(float(frontera_df["sigma"].max()), port_tangente.sigma, sigma_activos.max()) * 1.2
    )
    fig.add_trace(
        go.Scatter(
            x=[0, sigma_max],
            y=[cal_intercepto, cal_intercepto + cal_pendiente * sigma_max],
            mode="lines",
            name="CAL",
            line={"color": "black", "dash": "dot"},
        )
    )

    if punto_usuario is not None:
        fig.add_trace(
            go.Scatter(
                x=[punto_usuario[0]],
                y=[punto_usuario[1]],
                mode="markers",
                name="Tu portafolio completo",
                marker={"color": "#f4a261", "size": 16, "symbol": "diamond"},
            )
        )

    fig.update_layout(
        title="Frontera eficiente, tangente y CAL",
        xaxis_title="σ (anual)",
        yaxis_title="Retorno esperado (anual)",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
    )
    return fig


def figura_pesos(pesos: pd.Series, titulo: str) -> go.Figure:
    """Barras horizontales con los pesos de un portafolio (ej. incluye "RF")."""
    pesos_ordenados = pesos.sort_values(ascending=True)
    fig = go.Figure(
        go.Bar(x=pesos_ordenados.to_numpy(), y=list(pesos_ordenados.index), orientation="h")
    )
    fig.update_layout(title=titulo, xaxis_title="Peso", xaxis_tickformat=".0%")
    return fig
