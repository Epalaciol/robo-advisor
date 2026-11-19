"""Gráficos del informe del Taller 1 (matplotlib, a PNG)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .caso import CasoReferencia  # noqa: E402

AZUL, NARANJA, GRIS = "#1f4e79", "#d9822b", "#8a8a8a"
# Correlaciones: roja (negativa) → blanca (cero) → verde (alta)
MAPA_CORRELACION = matplotlib.colors.LinearSegmentedColormap.from_list(
    "rojo_blanco_verde", ["#c0392b", "#ffffff", "#1e8449"]
)


def _guardar(fig, ruta: Path) -> Path:
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def frontera_y_cal(c: CasoReferencia, ruta: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    sig = np.sqrt(np.diag(c.est.sigma.to_numpy()))
    ax.scatter(sig, c.est.mu, color=GRIS, s=26, label="Cada ETF")
    for t, x, y in zip(c.est.tickers, sig, c.est.mu, strict=True):
        ax.annotate(t, (x, y), textcoords="offset points", xytext=(4, 3), fontsize=7, color=GRIS)
    ax.plot(
        c.frontera["sigma"], c.frontera["retorno"], color=AZUL, lw=2, label="Frontera eficiente"
    )
    xs = np.linspace(0, c.tangente.sigma * 1.25, 50)
    ax.plot(xs, c.rf + c.cal_pendiente * xs, color=NARANJA, lw=2, label="CAL óptima")
    ax.scatter(
        [c.tangente.sigma],
        [c.tangente.retorno],
        color=NARANJA,
        s=70,
        zorder=5,
        label="Portafolio de riesgo óptimo",
    )
    ax.scatter(
        [c.min_var.sigma], [c.min_var.retorno], color=AZUL, s=45, zorder=5, label="Mínima varianza"
    )
    ax.scatter([0], [c.rf], color="black", s=35, zorder=5, label="Activo libre de riesgo")
    ax.set_xlabel("Riesgo (desviación estándar anual)")
    ax.set_ylabel("Retorno esperado anual")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="lower right")
    return _guardar(fig, ruta)


def pesos_optimos(c: CasoReferencia, ruta: Path) -> Path:
    w = c.tangente.w.sort_values()
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.barh(w.index, w.to_numpy(), color=AZUL)
    for i, v in enumerate(w.to_numpy()):
        ax.text(v + 0.005, i, f"{v:.1%}", va="center", fontsize=8)
    ax.set_xlabel("Peso en el portafolio de riesgo óptimo")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlim(0, max(0.5, w.max() + 0.08))
    return _guardar(fig, ruta)


def completo_por_perfil(c: CasoReferencia, ruta: Path) -> Path:
    e = c.escenarios
    etiquetas = [f"A = {int(a)}" for a in e["a"]]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(etiquetas, e["y"], color=AZUL, label="En el portafolio de riesgo (y*)")
    ax.bar(
        etiquetas, 1 - e["y"], bottom=e["y"], color=NARANJA, label="En el activo libre de riesgo"
    )
    for i, v in enumerate(e["y"]):
        ax.text(i, v / 2, f"{v:.0%}", ha="center", color="white", fontsize=9)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(fontsize=7, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.12))
    return _guardar(fig, ruta)


def correlaciones(c: CasoReferencia, ruta: Path) -> Path:
    """Matriz de correlaciones de los retornos diarios de los 11 ETF (misma ventana)."""
    s = c.est.sigma.to_numpy()
    d = np.sqrt(np.diag(s))
    corr = s / np.outer(d, d)
    t = list(c.est.tickers)
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(corr, cmap=MAPA_CORRELACION, vmin=-1, vmax=1)
    ax.set_xticks(range(len(t)))
    ax.set_yticks(range(len(t)))
    ax.set_xticklabels(t, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(t, fontsize=8)
    for i in range(len(t)):
        for j in range(len(t)):
            ax.text(j, i, f"{corr[i, j]:.2f}".replace(".", ","), ha="center", va="center",
                    fontsize=6.5, color="white" if abs(corr[i, j]) > 0.6 else "black")  # fmt: skip
    fig.colorbar(im, ax=ax, shrink=0.8, label="Correlación")
    return _guardar(fig, ruta)


def desempeno(c: CasoReferencia, ruta: Path) -> Path:
    """Valor de $100 invertidos al inicio de la ventana: cada ETF y el portafolio óptimo."""
    tickers = list(c.est.tickers)
    r = c.precios[tickers].sort_index().pct_change().dropna(how="any").tail(c.est.n_obs)
    base = (1 + r).cumprod() * 100
    optimo = (1 + (r * c.tangente.w.reindex(tickers).fillna(0)).sum(axis=1)).cumprod() * 100
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for t in tickers:
        ax.plot(base.index, base[t], color=GRIS, lw=0.8, alpha=0.6)
        ax.annotate(t, (base.index[-1], base[t].iloc[-1]), fontsize=6, color=GRIS,
                    xytext=(3, 0), textcoords="offset points", va="center")  # fmt: skip
    ax.plot(optimo.index, optimo, color=NARANJA, lw=2.2, label="Portafolio de riesgo óptimo")
    ax.axhline(100, color="black", lw=0.6)
    ax.set_ylabel("Valor de $100 invertidos (USD)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="upper left")
    return _guardar(fig, ruta)


def indiferencia(c: CasoReferencia, ruta: Path) -> Path:
    """CAL, frontera y la curva de indiferencia tangente de cada A, en dos escalas.

    Izquierda: detalle alrededor de P. Derecha (zoom out): la CAL prolongada con el punto que cada
    perfil escogería **sin** el tope de 100 % (círculo vacío, apalancado) frente al punto que se le
    asigna con el tope (círculo lleno, en P). Curva de indiferencia: `E(r) = U* + ½·A·σ²`.
    """
    colores = {8: "#1f4e79", 6: "#4f81bd", 4: "#7f7f7f", 3: "#f2a65a", 1: "#c0504d"}
    t = c.tangente
    puntos = []
    for r in c.escenarios.itertuples():
        a = int(r.a)
        y_libre = (t.retorno - c.rf) / (a * t.sigma**2)
        puntos.append(
            (a, r, y_libre, y_libre * t.sigma, c.rf + c.cal_pendiente * y_libre * t.sigma)
        )
    s_max = max(p[3] for p in puntos) * 1.12
    fig, (izq, der) = plt.subplots(1, 2, figsize=(9.6, 4.4))
    for ax, x_max, detalle in ((izq, max(0.32, t.sigma * 1.6), True), (der, s_max, False)):
        xs = np.linspace(0, x_max, 300)
        ax.plot(
            c.frontera["sigma"],
            c.frontera["retorno"],
            color=GRIS,
            lw=1.5,
            label="Frontera eficiente",
        )
        ax.plot(xs, c.rf + c.cal_pendiente * xs, color="black", lw=1.3, label="CAL")
        ax.scatter([t.sigma], [t.retorno], color="black", s=35, zorder=5)
        ax.annotate(
            "P", (t.sigma, t.retorno), xytext=(5, -11), textcoords="offset points", fontsize=8
        )
        for a, r, y_libre, s_libre, e_libre in puntos:
            u = c.rf + t.sharpe**2 / (2 * a)
            if detalle:
                ax.plot(xs, u + 0.5 * a * xs**2, color=colores[a], lw=1, ls="--")
            ax.scatter([r.sigma], [r.retorno], color=colores[a], s=45, zorder=6,
                       label=f"A = {a}: y* = {r.y:.0%}" if detalle else None)  # fmt: skip
            if y_libre > 1:
                if s_libre <= x_max:
                    ax.scatter([s_libre], [e_libre], facecolors="white", edgecolors=colores[a],
                               s=55, lw=1.6, zorder=6)  # fmt: skip
                if not detalle:
                    flecha = {"arrowstyle": "<-", "color": colores[a], "lw": 1.2}
                    ax.annotate("", xy=(s_libre, e_libre), xytext=(r.sigma, r.retorno),
                                arrowprops=flecha)  # fmt: skip
                    ax.annotate(f"A = {a}: y* real = {y_libre:.0%}\n(limitado a 100 %)",
                                (s_libre, e_libre), xytext=(-8, 6), textcoords="offset points",
                                ha="right", fontsize=7, color=colores[a])  # fmt: skip
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, (c.rf + c.cal_pendiente * x_max) * (1.05 if not detalle else 1.0))
        if detalle:
            ax.set_ylim(0, max(0.30, t.retorno * 1.5))
        ax.set_xlabel("Riesgo (desviación estándar anual)")
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.grid(alpha=0.25)
    izq.set_ylabel("Retorno esperado anual")
    izq.set_title("Detalle: elección de cada perfil", fontsize=9)
    der.set_title("Zoom out: y* real (vacío) frente a y* limitado (lleno)", fontsize=9)
    izq.legend(fontsize=6.5, loc="upper left")
    return _guardar(fig, ruta)


def composicion_por_perfil(comp, ruta: Path) -> Path:
    """Barras apiladas: en qué activos queda el 100 % del dinero de cada perfil."""
    colores = [matplotlib.colormaps["tab20"](i) for i in range(0, 20, 2)] + [
        matplotlib.colormaps["tab20"](i) for i in range(1, 20, 2)
    ]  # un color distinto por activo (hasta 20)
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    base = np.zeros(comp.shape[1])
    for (activo, fila), color in zip(comp.iterrows(), colores * 3, strict=False):
        es_rf = activo.startswith("Libre")
        ax.bar(comp.columns, fila.to_numpy(), bottom=base, color="#b0b0b0" if es_rf else color,
               label=activo, hatch="//" if es_rf else None, edgecolor="white")  # fmt: skip
        for i, v in enumerate(fila.to_numpy()):
            if v >= 0.06:
                ax.text(i, base[i] + v / 2, f"{v:.0%}", ha="center", va="center", fontsize=7,
                        color="white")  # fmt: skip
        base += fila.to_numpy()
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    return _guardar(fig, ruta)
