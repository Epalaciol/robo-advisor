"""Gráficos del informe del Taller 1 (matplotlib, a PNG)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .caso import CasoReferencia  # noqa: E402

AZUL, NARANJA, GRIS = "#1f4e79", "#d9822b", "#8a8a8a"


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
