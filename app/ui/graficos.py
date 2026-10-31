"""Gráficos Plotly reutilizables (frontera+CAL, composición, utilidad).

Todos los números ya vienen calculados de `core/`; estas funciones solo
grafican, no implementan fórmulas.

Paleta categórica (modo oscuro) y reglas de la skill `dataviz` del proyecto:
orden fijo de tonos, "emphasis" para resaltar el portafolio del usuario sobre
el resto (contexto en gris), leyenda siempre presente con >=2 series, texto
nunca con el color de la serie, line fija del CAL con un color visible sobre
fondo oscuro (antes era negro: invisible, ese era el bug reportado).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.utilidad import utilidad as _utilidad

ER_ILUSTRATIVO = 0.08  # solo para el gráfico explicativo de U vs σ, no es un cálculo real

# Paleta categórica de referencia (modo oscuro), orden fijo. Ver skill dataviz § palette.md.
PALETA_CATEGORICA = [
    "#3987e5",  # 1 azul
    "#d95926",  # 2 naranja
    "#199e70",  # 3 aqua
    "#c98500",  # 4 amarillo
    "#d55181",  # 5 magenta
    "#9085e9",  # 6 violeta
    "#e66767",  # 7 rojo
]
COLOR_LIBRE_DE_RIESGO = "#8a8a85"  # gris neutro: "seguro", no es una categoría de riesgo
COLOR_CONTEXTO = "#6b6a63"  # gris para lo que es contexto, no la historia (frontera, activos...)
COLOR_CAL = "#a9a9a0"  # gris claro, visible sobre fondo oscuro (antes: negro, invisible)
COLOR_TANGENTE = PALETA_CATEGORICA[0]
COLOR_PORTAFOLIO_USUARIO = PALETA_CATEGORICA[1]


def figura_utilidad_vs_sigma(a: float, er: float = ER_ILUSTRATIVO) -> go.Figure:
    """Curva ilustrativa `U = er − ½·A·σ²` para el `A` del usuario, a un `er` fijo."""
    sigmas = np.linspace(0.01, 0.40, 50)
    utilidades = [_utilidad(er, float(s), a) for s in sigmas]

    fig = go.Figure(
        go.Scatter(x=sigmas, y=utilidades, mode="lines", line={"color": PALETA_CATEGORICA[0]})
    )
    fig.update_layout(
        title=f"Utilidad vs σ (ilustrativo, A={a}, E(r)={er:.0%})",
        xaxis_title="σ (desviación estándar)",
        yaxis_title="Utilidad U",
        xaxis_tickformat=".0%",
        showlegend=False,
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

    "Emphasis": todo lo anterior es contexto en gris; el tangente y el
    portafolio del usuario llevan los únicos dos colores vivos — son la
    historia que el gráfico cuenta.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=frontera_df["sigma"],
            y=frontera_df["retorno"],
            mode="lines",
            name="Frontera eficiente",
            line={"color": COLOR_CONTEXTO, "width": 2},
            hovertemplate="σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
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
            textfont={"color": COLOR_CONTEXTO},
            name="Activos elegidos",
            marker={"color": COLOR_CONTEXTO, "size": 9, "symbol": "circle"},
            hovertemplate="%{text}: σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[port_min_var.sigma],
            y=[port_min_var.retorno],
            mode="markers",
            name="Mínima varianza",
            marker={
                "color": COLOR_CONTEXTO,
                "size": 11,
                "symbol": "circle-open",
                "line": {"width": 2},
            },
            hovertemplate="Mínima varianza: σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
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
            name="CAL (con el activo libre de riesgo)",
            line={"color": COLOR_CAL, "dash": "dot", "width": 2},
            hovertemplate="σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[port_tangente.sigma],
            y=[port_tangente.retorno],
            mode="markers",
            name="Tangente (óptimo de riesgo)",
            marker={
                "color": COLOR_TANGENTE,
                "size": 16,
                "symbol": "star",
                "line": {"color": "#1a1a19", "width": 1},
            },
            hovertemplate="Tangente: σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
        )
    )

    if punto_usuario is not None:
        fig.add_trace(
            go.Scatter(
                x=[punto_usuario[0]],
                y=[punto_usuario[1]],
                mode="markers+text",
                text=["Tu portafolio"],
                textposition="bottom center",
                textfont={"color": COLOR_PORTAFOLIO_USUARIO, "size": 13},
                name="Tu portafolio completo",
                marker={
                    "color": COLOR_PORTAFOLIO_USUARIO,
                    "size": 20,
                    "symbol": "diamond",
                    "line": {"color": "#1a1a19", "width": 1},
                },
                hovertemplate="Tu portafolio: σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Riesgo vs. retorno de tu portafolio",
        xaxis_title="σ — qué tanto varía el valor en un año (riesgo)",
        yaxis_title="Retorno esperado por año",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.35},
    )
    return fig


def figura_composicion(pesos: pd.Series, titulo: str) -> go.Figure:
    """Barra apilada al 100% (una sola barra, segmentos proporcionales): la
    forma más clara para mostrar que un portafolio suma el 100%.

    "Libre de riesgo" siempre lleva el gris neutro (es "plata segura", no una
    categoría de riesgo); los demás activos toman la paleta categórica en
    orden fijo.
    """
    fig = go.Figure()
    indice_color = 0

    for etiqueta, valor in pesos.items():
        if valor <= 0.0005:
            continue  # activos con peso ~0 no aportan nada visible; no gastan color ni leyenda

        es_libre_de_riesgo = "libre de riesgo" in str(etiqueta).lower() or etiqueta == "RF"
        if es_libre_de_riesgo:
            color = COLOR_LIBRE_DE_RIESGO
        else:
            color = PALETA_CATEGORICA[indice_color % len(PALETA_CATEGORICA)]
            indice_color += 1

        texto = f"{etiqueta}<br>{valor:.0%}" if valor >= 0.06 else ""
        fig.add_trace(
            go.Bar(
                name=str(etiqueta),
                x=[valor],
                y=[""],
                orientation="h",
                marker={"color": color, "line": {"color": "#1a1a19", "width": 2}},
                text=texto,
                textposition="inside",
                insidetextanchor="middle",
                textfont={"color": "white", "size": 12},
                hovertemplate=f"{etiqueta}: {valor:.1%}<extra></extra>",
            )
        )

    fig.update_layout(
        title=titulo,
        barmode="stack",
        xaxis={"tickformat": ".0%", "range": [0, 1], "title": None},
        yaxis={"visible": False},
        height=220,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.5},
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
    )
    return fig
