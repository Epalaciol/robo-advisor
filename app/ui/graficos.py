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
    escenarios: pd.DataFrame | None = None,
    curvas_por_a: bool = False,
) -> go.Figure:
    """Frontera eficiente, activos individuales, mínima varianza, tangente, CAL
    y (opcional) el punto del portafolio completo del usuario, la nube de
    portafolios factibles no eficientes (`nube_no_eficientes`, de
    `core.markowitz.portafolios_aleatorios`), la rama no eficiente
    (`rama_ineficiente`, de `core.markowitz.rama_ineficiente`) que junto con
    `frontera_df` completa la forma de "bala" (hipérbola) de Markowitz, y la
    curva de indiferencia del usuario (`a_usuario`), **tangente a la CAL** en el
    punto óptimo `y*` sin recortar (si `y* > 1` ese punto requeriría apalancamiento
    y se marca aparte: el portafolio del usuario queda en `y = 1`). `escenarios`
    (de `core.portafolio_completo.escenarios_por_a`) dibuja sobre la CAL dónde
    quedaría el mismo portafolio con otros `A`; `curvas_por_a` agrega la curva
    de indiferencia de cada uno.

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
    # Si el óptimo sin tope (apalancado) queda cerca, se encuadra para ver la tangencia.
    extra_sigma: list[float] = []
    extra_retorno: list[float] = []
    if a_usuario is not None:
        y_raw0 = max(
            (port_tangente.retorno - cal_intercepto) / (a_usuario * port_tangente.sigma**2), 0.0
        )
        if 1 < y_raw0 <= 2:
            extra_sigma = [y_raw0 * port_tangente.sigma]
            extra_retorno = [cal_intercepto + y_raw0 * (port_tangente.retorno - cal_intercepto)]
    sigmas_reales = np.concatenate(
        [
            frontera_df["sigma"].to_numpy(),
            sigma_activos,
            [port_min_var.sigma, port_tangente.sigma],
            [punto_usuario[0]] if punto_usuario is not None else [],
            extra_sigma,
        ]
    )
    retornos_reales = np.concatenate(
        [
            frontera_df["retorno"].to_numpy(),
            mu.to_numpy(),
            [port_min_var.retorno, port_tangente.retorno],
            [punto_usuario[1]] if punto_usuario is not None else [],
            extra_retorno,
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

    rf = cal_intercepto
    prima = port_tangente.retorno - rf

    def _optimo_sin_tope(a: float) -> tuple[float, float, float]:
        """Punto de la CAL donde la curva de indiferencia de `a` es tangente:
        `y_raw = (E_p − rf)/(A·σ_p²)`, sin recortar; devuelve (y_raw, σ, E)."""
        y_raw = max(prima / (a * port_tangente.sigma**2), 0.0)
        return y_raw, y_raw * port_tangente.sigma, rf + y_raw * prima

    def _curva(a: float, nombre: str, color: str, ancho: float, dash: str, mostrar_ley: bool):
        # er(σ) = U* + ½·A·σ², con U* la utilidad en el punto tangente a la CAL
        _, sig_opt, er_opt = _optimo_sin_tope(a)
        u_opt = _utilidad(er_opt, sig_opt, a)
        sigmas_curva = np.linspace(0, sigma_max_visible, 100)
        fig.add_trace(
            go.Scatter(
                x=sigmas_curva,
                y=u_opt + 0.5 * a * sigmas_curva**2,
                mode="lines",
                name=nombre,
                showlegend=mostrar_ley,
                line={"color": color, "dash": dash, "width": ancho},
                hovertemplate=f"{nombre}: σ=%{{x:.1%}}, retorno=%{{y:.1%}}<extra></extra>",
            )
        )

    if curvas_por_a and escenarios is not None and not escenarios.empty:
        for k, fila in escenarios.reset_index(drop=True).iterrows():
            _curva(
                float(fila["a"]),
                f"Curva A={fila['a']:g}",
                PALETA_CATEGORICA[k % len(PALETA_CATEGORICA)],
                1.2,
                "dot",
                False,
            )

    if a_usuario is not None:
        _curva(
            a_usuario,
            "Tu curva de utilidad (tangente a la CAL)",
            COLOR_PORTAFOLIO_USUARIO,
            1.8,
            "dash",
            True,
        )
        y_raw, sig_opt, er_opt = _optimo_sin_tope(a_usuario)
        if y_raw > 1 + 1e-9 and sig_opt <= sigma_max_visible:
            fig.add_trace(
                go.Scatter(
                    x=[sig_opt],
                    y=[er_opt],
                    mode="markers",
                    name="Óptimo sin tope (requeriría apalancamiento)",
                    marker={
                        "color": COLOR_PORTAFOLIO_USUARIO,
                        "size": 16,
                        "symbol": "diamond-open",
                        "line": {"width": 2},
                    },
                    hovertemplate=(
                        f"Óptimo sin tope: {y_raw:.0%} en riesgo, "
                        "σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>"
                    ),
                )
            )

    if escenarios is not None and not escenarios.empty:
        tope = escenarios[escenarios["y"] >= 1 - 1e-9]
        libres = escenarios[escenarios["y"] < 1 - 1e-9]
        for k, (_, fila) in enumerate(libres.iterrows()):
            fig.add_trace(
                go.Scatter(
                    x=[fila["sigma"]],
                    y=[fila["retorno"]],
                    mode="markers",
                    name=f"A={fila['a']:g} · {fila['y']:.0%} en riesgo",
                    marker={
                        "color": PALETA_CATEGORICA[(k + 4) % len(PALETA_CATEGORICA)],
                        "size": 11,
                        "line": {"color": "#1a1a19", "width": 1},
                    },
                    hovertemplate=(
                        f"A={fila['a']:g}: {fila['y']:.0%} en riesgo, "
                        "σ=%{x:.1%}, retorno=%{y:.1%}<extra></extra>"
                    ),
                )
            )
        if not tope.empty:
            etiqueta = ", ".join(f"{a:g}" for a in tope["a"])
            fig.add_trace(
                go.Scatter(
                    x=[port_tangente.sigma],
                    y=[port_tangente.retorno],
                    mode="markers",
                    name=f"A={etiqueta} · 100% en riesgo (tope)",
                    marker={
                        "color": COLOR_CAL,
                        "size": 22,
                        "symbol": "circle-open",
                        "line": {"width": 2},
                    },
                    hoverinfo="skip",
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


MODO_BASE_100 = "Base 100"
MODO_PORCENTAJE = "Porcentaje (%)"


def _convertir(serie: pd.Series, modo: str) -> pd.Series:
    """Base 100 → tal cual; porcentaje → variación desde la fecha base (`valor − 100`)."""
    return serie if modo == MODO_BASE_100 else serie - 100


def figura_comportamiento(
    valor_portafolio: pd.Series,
    valor_benchmark: pd.Series | None,
    nombre_benchmark: str,
    evolucion_activos: pd.DataFrame | None = None,
    modo: str = MODO_BASE_100,
) -> go.Figure:
    """Evolución desde la fecha base: portafolio, benchmark y (opcional) cada activo.

    `modo`: "Base 100" (el valor parte de 100) o "Porcentaje (%)" (variación acumulada
    desde la fecha base). "Emphasis": el portafolio lleva el color vivo; el benchmark es
    gris; los activos usan sus colores y líneas finas para explicar de dónde sale el
    resultado del portafolio.
    """
    en_porcentaje = modo == MODO_PORCENTAJE
    fmt_hover = "%{x|%Y-%m-%d}: %{y:+.1f}%" if en_porcentaje else "%{x|%Y-%m-%d}: %{y:.1f}"
    fig = go.Figure()

    if evolucion_activos is not None and not evolucion_activos.empty:
        for i, ticker in enumerate(evolucion_activos.columns):
            serie = _convertir(evolucion_activos[ticker].dropna(), modo)
            fig.add_trace(
                go.Scatter(
                    x=serie.index,
                    y=serie,
                    mode="lines",
                    name=ticker,
                    line={"color": PALETA_ACTIVOS[i % len(PALETA_ACTIVOS)], "width": 1.2},
                    opacity=0.8,
                    hovertemplate=f"{ticker} {fmt_hover}<extra></extra>",
                )
            )

    if valor_benchmark is not None and not valor_benchmark.empty:
        serie = _convertir(valor_benchmark, modo)
        fig.add_trace(
            go.Scatter(
                x=serie.index,
                y=serie,
                mode="lines",
                name=nombre_benchmark,
                line={"color": COLOR_CONTEXTO, "width": 2, "dash": "dot"},
                hovertemplate=f"{nombre_benchmark} {fmt_hover}<extra></extra>",
            )
        )

    serie = _convertir(valor_portafolio, modo)
    fig.add_trace(
        go.Scatter(
            x=serie.index,
            y=serie,
            mode="lines",
            name="Tu portafolio",
            line={"color": COLOR_PORTAFOLIO_USUARIO, "width": 3},
            hovertemplate=f"Tu portafolio {fmt_hover}<extra></extra>",
        )
    )

    referencia = 0 if en_porcentaje else 100
    fig.add_hline(y=referencia, line={"color": COLOR_CONTEXTO, "width": 1, "dash": "dash"})
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Variación acumulada (%)" if en_porcentaje else "Valor (base 100)",
        yaxis_ticksuffix="%" if en_porcentaje else "",
        height=460,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0},
        hovermode="x unified",
    )
    return fig


def figura_valor_vs_benchmark(
    valor_portafolio: pd.Series,
    valor_benchmark: pd.Series | None,
    nombre_benchmark: str,
) -> go.Figure:
    """Curva de valor (base 100) del portafolio frente al benchmark."""
    return figura_comportamiento(valor_portafolio, valor_benchmark, nombre_benchmark)
