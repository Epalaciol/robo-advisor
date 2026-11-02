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

# Paleta categórica (modo oscuro), orden fijo; los 4 primeros son los colores del logo MFT.
PALETA_CATEGORICA = [
    "#8a5cf5",  # 1 violeta (marca MFT)
    "#e8761e",  # 2 naranja (marca MFT)
    "#1fa79a",  # 3 verde azulado (marca MFT)
    "#e9a93a",  # 4 dorado (marca MFT)
    "#3987e5",  # 5 azul
    "#d55181",  # 6 magenta
    "#e66767",  # 7 rojo
]
# Un color por activo en la frontera (12 tonos distinguibles sobre fondo oscuro).
PALETA_ACTIVOS = [
    "#4fc3f7", "#f06292", "#aed581", "#ffb74d", "#ba68c8", "#4db6ac",
    "#fff176", "#ff8a65", "#7986cb", "#a1887f", "#81c784", "#e57373",
]  # fmt: skip
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
    nube_no_eficientes: pd.DataFrame | None = None,
    rama_ineficiente: pd.DataFrame | None = None,
    a_usuario: float | None = None,
) -> go.Figure:
    """Frontera eficiente, activos individuales, mínima varianza, tangente, CAL
    y (opcional) el punto del portafolio completo del usuario, la nube de
    portafolios factibles no eficientes (`nube_no_eficientes`, de
    `core.markowitz.portafolios_aleatorios`), la rama no eficiente
    (`rama_ineficiente`, de `core.markowitz.rama_ineficiente`) que junto con
    `frontera_df` completa la forma de "bala" (hipérbola) de Markowitz, y la
    curva de indiferencia del usuario (`a_usuario`) tangente a la CAL en su
    portafolio completo.

    "Emphasis": todo lo anterior es contexto en gris; el tangente y el
    portafolio del usuario llevan los únicos dos colores vivos — son la
    historia que el gráfico cuenta.
    """
    fig = go.Figure()

    if nube_no_eficientes is not None and not nube_no_eficientes.empty:
        fig.add_trace(
            go.Scatter(
                x=nube_no_eficientes["sigma"],
                y=nube_no_eficientes["retorno"],
                mode="markers",
                name="Carteras no eficientes (posibles, pero no óptimas)",
                marker={"color": COLOR_CONTEXTO, "size": 4, "opacity": 0.35},
                hoverinfo="skip",
            )
        )

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

    if rama_ineficiente is not None and not rama_ineficiente.empty:
        # Misma hipérbola que la frontera eficiente, pero del lado dominado:
        # completa la forma de "bala" (el mínimo de varianza es la punta).
        fig.add_trace(
            go.Scatter(
                x=rama_ineficiente["sigma"],
                y=rama_ineficiente["retorno"],
                mode="lines",
                name="Frontera (rama no eficiente, dominada)",
                line={"color": COLOR_CONTEXTO, "width": 2, "dash": "dot"},
                hovertemplate="σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
            )
        )

    sigma_activos = np.sqrt(np.diag(sigma.to_numpy()))
    for i, ticker in enumerate(mu.index):
        color = PALETA_ACTIVOS[i % len(PALETA_ACTIVOS)]
        fig.add_trace(
            go.Scatter(
                x=[sigma_activos[i]],
                y=[mu.iloc[i]],
                mode="markers+text",
                text=[ticker],
                textposition="top center",
                textfont={"color": color, "size": 12},
                name=ticker,
                legend="legend2",
                marker={
                    "color": color,
                    "size": 11,
                    "symbol": "circle",
                    "line": {"color": "#1a1a19", "width": 1},
                },
                hovertemplate=f"{ticker}: σ=%{{x:.1%}}, retorno=%{{y:.1%}}<extra></extra>",
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

    # Rango visible de ejes a partir de los datos reales — SIN incluir la CAL,
    # que se dibuja después recortada a este mismo rango. Antes la CAL se
    # extendía 1.2x más allá del dato más lejano y ese punto, lejísimos,
    # quedaba igual incluido en el gráfico: al hacer zoom-out o "reset axes"
    # Plotly reencuadraba para mostrarlo entero y la vista útil se arruinaba.
    sigmas_reales = np.concatenate(
        [
            frontera_df["sigma"].to_numpy(),
            sigma_activos,
            [port_min_var.sigma, port_tangente.sigma],
            [punto_usuario[0]] if punto_usuario is not None else [],
        ]
    )
    retornos_reales = np.concatenate(
        [
            frontera_df["retorno"].to_numpy(),
            mu.to_numpy(),
            [port_min_var.retorno, port_tangente.retorno],
            [punto_usuario[1]] if punto_usuario is not None else [],
        ]
    )
    # Escala inicial predeterminada: encuadra activos, frontera, tangente y tu
    # portafolio (no la nube ni la rama dominada). "Reset axes" vuelve aquí.
    sigma_max_visible = float(sigmas_reales.max()) * 1.15
    margen_y = (float(retornos_reales.max()) - float(retornos_reales.min())) * 0.15
    retorno_min_visible = float(retornos_reales.min()) - margen_y
    retorno_max_visible = float(retornos_reales.max()) + margen_y

    fig.add_trace(
        go.Scatter(
            x=[0, sigma_max_visible],
            y=[cal_intercepto, cal_intercepto + cal_pendiente * sigma_max_visible],
            mode="lines",
            name="CAL (con el activo libre de riesgo)",
            line={"color": COLOR_CAL, "dash": "dot", "width": 2},
            hovertemplate="σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>",
        )
    )

    if punto_usuario is not None and a_usuario is not None:
        # Curva de indiferencia U = er - 0.5*A*σ² que pasa por el portafolio
        # completo del usuario, despejada como er(σ) = U + 0.5*A*σ². Si y* es
        # interior (0<y*<1) es tangente a la CAL justo en ese punto — es la
        # definición de "el mejor punto sobre la CAL dado tu A". Se recorta al
        # mismo rango de ejes que el resto (ver nota sobre sigma_max_visible):
        # crece cuadrático en σ y un rango no recortado la dispararía fuera
        # de la vista útil.
        u_usuario = _utilidad(punto_usuario[1], punto_usuario[0], a_usuario)
        sigmas_curva = np.linspace(0, sigma_max_visible, 100)
        fig.add_trace(
            go.Scatter(
                x=sigmas_curva,
                y=u_usuario + 0.5 * a_usuario * sigmas_curva**2,
                mode="lines",
                name="Tu curva de utilidad (tangente a la CAL)",
                line={"color": COLOR_PORTAFOLIO_USUARIO, "dash": "dash", "width": 1.5},
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
        xaxis_range=[0, sigma_max_visible],
        yaxis_range=[retorno_min_visible, retorno_max_visible],
        height=680,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        # Leyendas abajo: el gráfico usa todo el ancho; clic en un ítem oculta/muestra,
        # doble clic aísla esa serie.
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.17,
            "xanchor": "center",
            "x": 0.5,
            "font": {"size": 11},
        },
        # Segunda leyenda, solo para los activos: una fila de colores con su ticker.
        legend2={
            "title": {"text": "Activos", "side": "left"},
            "orientation": "h",
            "yanchor": "top",
            "y": -0.36,
            "xanchor": "center",
            "x": 0.5,
            "font": {"size": 12},
        },
        hovermode="closest",
        dragmode="zoom",
    )
    return fig


def figura_composicion(pesos: pd.Series, titulo: str) -> go.Figure:
    """Gráfico de dona con el peso de cada activo (suma 100%).

    Cada activo conserva el color que tiene en la frontera (según su posición en
    `pesos`); "Libre de riesgo" lleva siempre el gris neutro. Los pesos ~0 no se
    dibujan.
    """
    etiquetas, valores, colores = [], [], []
    for posicion, (etiqueta, valor) in enumerate(pesos.items()):
        if valor <= 0.0005:
            continue
        es_libre_de_riesgo = "libre de riesgo" in str(etiqueta).lower() or etiqueta == "RF"
        etiquetas.append(str(etiqueta))
        valores.append(float(valor))
        colores.append(
            COLOR_LIBRE_DE_RIESGO
            if es_libre_de_riesgo
            else PALETA_ACTIVOS[posicion % len(PALETA_ACTIVOS)]
        )

    fig = go.Figure(
        go.Pie(
            labels=etiquetas,
            values=valores,
            hole=0.55,
            sort=False,
            direction="clockwise",
            marker={"colors": colores, "line": {"color": "#1a1a19", "width": 2}},
            texttemplate="%{label}<br>%{percent:.0%}",
            textposition="outside",
            hovertemplate="%{label}: %{percent:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        title=titulo,
        height=380,
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
    )
    return fig


def figura_valor_vs_benchmark(
    valor_portafolio: pd.Series,
    valor_benchmark: pd.Series | None,
    nombre_benchmark: str,
) -> go.Figure:
    """Curva de valor (base 100) del portafolio desde `fecha_base`, frente al
    benchmark si hay datos. "Emphasis": el portafolio del usuario lleva el
    único color vivo; el benchmark es contexto en gris.
    """
    fig = go.Figure()

    if valor_benchmark is not None and not valor_benchmark.empty:
        fig.add_trace(
            go.Scatter(
                x=valor_benchmark.index,
                y=valor_benchmark,
                mode="lines",
                name=nombre_benchmark,
                line={"color": COLOR_CONTEXTO, "width": 2},
                hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=valor_portafolio.index,
            y=valor_portafolio,
            mode="lines",
            name="Tu portafolio",
            line={"color": COLOR_PORTAFOLIO_USUARIO, "width": 2.5},
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Valor desde que armaste tu portafolio (base 100)",
        xaxis_title=None,
        yaxis_title="Valor (base 100)",
        height=380,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    return fig
