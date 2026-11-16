"""Gráficas del Taller 2 (Plotly). Las usan la página pública y el reporte de validación."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..core.modelos import Betas
from ..core.nelson_siegel import spot

COLOR_SENAL = {"Comprar": "#2E7D32", "Vender": "#C62828", "Mantener": "#9E9E9E"}
SIMBOLO_ORIGEN = {"SEN": "circle", "VAL": "triangle-up"}
COLOR_CURVA = "#1F3864"


def _plantilla(fig: go.Figure, titulo_x: str, titulo_y: str, tema: str = "claro") -> go.Figure:
    fig.update_layout(
        template="plotly_white" if tema == "claro" else "plotly_dark",
        xaxis_title=titulo_x,
        yaxis_title=titulo_y,
        legend={"orientation": "h", "y": -0.2},
        margin={"l": 60, "r": 20, "t": 30, "b": 60},
        height=480,
    )
    if tema == "claro":
        fig.update_layout(paper_bgcolor="white", plot_bgcolor="white", font_color="#222")
    return fig


def figura_curva_desde(
    betas: Betas, tau: float, tabla: pd.DataFrame | None, titulo: str = "", tema="claro"
) -> go.Figure:
    """Curva spot NS (0–30 años) y los papeles: TIR observada por plazo, color = decisión."""
    t = np.linspace(0.01, 30, 600)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=t,
            y=spot(t, betas, tau) * 100,
            mode="lines",
            name="Curva cero cupón (NS)",
            line={"color": COLOR_CURVA if tema == "claro" else "#9db4ff", "width": 2.5},
        )
    )
    if tabla is not None and not tabla.empty:
        for senal, color in COLOR_SENAL.items():
            for origen, simbolo in SIMBOLO_ORIGEN.items():
                sel = tabla[(tabla["senal"] == senal) & (tabla["origen_tasa"] == origen)]
                if sel.empty:
                    continue
                fig.add_trace(
                    go.Scatter(
                        x=sel["plazo_anos"],
                        y=sel["tir_observada"] * 100,
                        mode="markers",
                        name=f"{senal} ({origen})",
                        marker={
                            "color": color,
                            "symbol": simbolo,
                            "size": 9,
                            "line": {"width": 1, "color": "white"},
                        },
                        customdata=np.stack(
                            [sel["nemotecnico"], sel["tir_estimada"] * 100, sel["spread_pb"]],
                            axis=-1,
                        ),
                        hovertemplate="%{customdata[0]}<br>Plazo %{x:.2f} años<br>"
                        "TIR obs %{y:.3f}%<br>TIR est %{customdata[1]:.3f}%<br>"
                        "Spread %{customdata[2]:.1f} pb<extra></extra>",
                    )
                )
    fig.update_layout(title=titulo or None)
    return _plantilla(fig, "Plazo (años)", "Tasa (% efectivo anual)", tema)


def figura_curva(resultado, tema="claro") -> go.Figure:
    c = resultado.calibracion
    return figura_curva_desde(c.betas, c.tau, resultado.tabla, tema=tema)


def figura_spreads(resultado, tema="claro") -> go.Figure:
    t = resultado.tabla
    u = resultado.umbral_pb
    fig = go.Figure(
        go.Bar(
            x=t["nemotecnico"],
            y=t["spread_pb"],
            marker_color=t["senal"].map(COLOR_SENAL),
            hovertemplate="%{x}<br>%{y:.1f} pb<extra></extra>",
        )
    )
    for y in (u, -u):
        fig.add_hline(y=y, line_dash="dash", line_color="#555", annotation_text=f"{y:+.1f} pb")
    return _plantilla(fig, "", "TIR observada − TIR estimada (pb)", tema)


def _curvas_df(dias) -> pd.DataFrame:
    filas = []
    for d in dias:
        c = d.resultado.calibracion
        filas.append(
            {
                "fecha": d.fecha,
                "b0": c.betas.b0,
                "b1": c.betas.b1,
                "b2": c.betas.b2,
                "tau": c.tau,
                "rmse": c.rmse,
            }
        )
    return pd.DataFrame(filas)


def figura_betas_tiempo(dias_o_df, tema="claro") -> go.Figure:
    df = dias_o_df if isinstance(dias_o_df, pd.DataFrame) else _curvas_df(dias_o_df)
    fig = go.Figure()
    nombres = {
        "b0": "β0 (nivel, largo plazo)",
        "b1": "β1 (pendiente: corto − largo)",
        "b2": "β2 (curvatura)",
    }
    for col, nombre in nombres.items():
        fig.add_trace(go.Scatter(x=df["fecha"], y=df[col] * 100, mode="lines+markers", name=nombre))
    return _plantilla(fig, "Fecha del informe", "Puntos porcentuales", tema)


def figura_spot_plazos(dias_o_df, plazos=(1, 5, 10), tema="claro") -> go.Figure:
    df = dias_o_df if isinstance(dias_o_df, pd.DataFrame) else _curvas_df(dias_o_df)
    fig = go.Figure()
    for p in plazos:
        y = [spot(float(p), Betas(r.b0, r.b1, r.b2), r.tau) * 100 for r in df.itertuples()]
        fig.add_trace(go.Scatter(x=df["fecha"], y=y, mode="lines+markers", name=f"{p} año(s)"))
    return _plantilla(fig, "Fecha del informe", "Tasa spot (%)", tema)


def figura_curvas_superpuestas(dias_o_df, max_curvas: int = 12, tema="claro") -> go.Figure:
    df = dias_o_df if isinstance(dias_o_df, pd.DataFrame) else _curvas_df(dias_o_df)
    if len(df) > max_curvas:
        idx = np.unique(np.linspace(0, len(df) - 1, max_curvas).round().astype(int))
        df = df.iloc[idx]
    t = np.linspace(0.01, 30, 300)
    fig = go.Figure()
    n = len(df)
    for i, r in enumerate(df.itertuples()):
        alfa = 0.35 + 0.65 * (i + 1) / n
        fig.add_trace(
            go.Scatter(
                x=t,
                y=spot(t, Betas(r.b0, r.b1, r.b2), r.tau) * 100,
                mode="lines",
                name=str(r.fecha),
                opacity=alfa,
            )
        )
    return _plantilla(fig, "Plazo (años)", "Tasa spot (%)", tema)


def figura_mapa_senales(dias, tema="claro") -> go.Figure:
    filas = [
        {
            "fecha": str(d.fecha),
            "nemotecnico": n,
            "valor": {"Comprar": 1, "Mantener": 0, "Vender": -1}[s],
        }
        for d in dias
        for n, s in zip(d.resultado.tabla["nemotecnico"], d.resultado.tabla["senal"], strict=True)
    ]
    df = pd.DataFrame(filas).pivot(index="nemotecnico", columns="fecha", values="valor")
    orden = sorted(df.index, key=lambda x: (x[-2:], x[-4:-2], x[-6:-4]))
    df = df.loc[orden]
    fig = go.Figure(
        go.Heatmap(
            z=df.values,
            x=df.columns,
            y=df.index,
            zmin=-1,
            zmax=1,
            colorscale=[[0, COLOR_SENAL["Vender"]], [0.5, "#E0E0E0"], [1, COLOR_SENAL["Comprar"]]],
            colorbar={"tickvals": [-1, 0, 1], "ticktext": ["Vender", "Mantener", "Comprar"]},
        )
    )
    fig.update_layout(height=max(420, 18 * len(df)))
    return _plantilla(fig, "Fecha del informe", "", tema)
