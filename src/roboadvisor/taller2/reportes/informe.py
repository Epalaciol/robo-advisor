# ruff: noqa: E501  (texto del informe: prosa larga)
"""Informe PDF del Taller 2 (Markdown → PDF con pandoc + xelatex) para el 2-oct-2026."""

import datetime as dt
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..core.analisis import ResultadoTES  # noqa: E402
from ..core.nelson_siegel import spot  # noqa: E402

URL_APP = "https://mft-investements.streamlit.app/"
COLOR = {"Comprar": "#2E7D32", "Vender": "#C62828", "Mantener": "#8a8a8a"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]  # fmt: skip


def _n(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _pct(x: float, d: int = 2) -> str:
    return f"{_n(x * 100, d)} %"


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, disable_numparse=True)


def grafico_curva(r: ResultadoTES, ruta: Path) -> Path:
    b, tau = r.calibracion.betas, r.calibracion.tau
    t = np.linspace(0.02, 30, 300)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(
        t, spot(t, b, tau) * 100, color="#1F3864", lw=2, label="Curva cero cupón (Nelson-Siegel)"
    )
    tab = r.tabla
    for sen, col in COLOR.items():
        m = tab["senal"] == sen
        ax.scatter(
            tab.loc[m, "plazo_anos"],
            tab.loc[m, "tir_observada"] * 100,
            color=col,
            s=28,
            label=f"TIR observada · {sen}",
        )
    ax.set_xlabel("Plazo (años)")
    ax.set_ylabel("Tasa efectiva anual (%)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def grafico_spreads(r: ResultadoTES, ruta: Path) -> Path:
    tab = r.tabla
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.barh(tab["nemotecnico"], tab["spread_pb"], color=[COLOR[s] for s in tab["senal"]])
    ax.axvline(r.umbral_pb, color="black", ls="--", lw=0.8)
    ax.axvline(-r.umbral_pb, color="black", ls="--", lw=0.8)
    ax.set_xlabel("TIR observada − TIR estimada (puntos básicos); líneas = ± umbral")
    ax.tick_params(axis="y", labelsize=6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def construir_markdown(
    r: ResultadoTES, sens: pd.DataFrame, figs: dict[str, Path], hoy: dt.date
) -> str:
    b, tau, cal = r.calibracion.betas, r.calibracion.tau, r.calibracion
    tab = r.tabla
    cont = r.conteo_senales()
    t1 = pd.DataFrame(
        {
            "Nemotécnico": tab["nemotecnico"],
            "Vence": tab["vencimiento"].astype(str),
            "Cupón %": [_n(x) for x in tab["cupon"]],
            "Sucio": [_n(x, 3) for x in tab["precio_sucio"]],
            "TIR obs.": [_pct(x) for x in tab["tir_observada"]],
            "TIR est.": [_pct(x) for x in tab["tir_estimada"]],
            "Spread pb": [_n(x, 1) for x in tab["spread_pb"]],
            "Señal": tab["senal"],
        }
    )
    t2 = pd.DataFrame(
        {
            "Nemotécnico": tab["nemotecnico"],
            "Dur. Macaulay": [_n(x) for x in tab["duracion_macaulay"]],
            "Dur. modificada": [_n(x) for x in tab["duracion_modificada"]],
            "Convexidad": [_n(x) for x in tab["convexidad"]],
            "DV01 por $1.000 M (COP)": [_n(x, 0) for x in tab["dv01_cop"]],
        }
    )
    spots = pd.DataFrame(
        {"Plazo": ["1 año", "5 años", "10 años", "30 años"],
         "Tasa spot": [_pct(spot(float(p), b, tau)) for p in (1, 5, 10, 30)]}
    )  # fmt: skip
    s = sens[sens["umbral"].astype(str) == "sigma"] if "umbral" in sens else sens
    sens_t = pd.DataFrame(
        {
            "Calibración": s["calibracion"],
            "Umbral (pb)": [_n(x, 1) for x in s["umbral_pb"]],
            "Comprar": s["comprar"], "Vender": s["vender"], "Mantener": s["mantener"],
        }
    ) if {"comprar", "vender", "mantener"} <= set(s.columns) else pd.DataFrame()  # fmt: skip
    return f"""---
title: "Taller 2 · Curva cero cupón de TES (Nelson-Siegel)"
subtitle: "Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026"
author: "Prof. Juan Carlos Botero Ramírez · Grupo MFT Investments"
date: "{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"
lang: es
geometry: margin=2cm
fontsize: 10pt
mainfont: Arial
colorlinks: true
---

# 1. Qué se hizo

Se construyó un código que, para un día cualquiera, lee el **Informe Diario de Deuda Pública**
de [www.irc.gov.co](https://www.irc.gov.co/440), calibra los tres betas (β0, β1, β2) de la curva
**Nelson-Siegel**, calcula la **curva cero cupón**, la **TIR** de cada TES tasa fija en pesos
transado ese día y decide, comparando la TIR observada con la estimada, si hay una oportunidad de
**comprar, vender o mantener**. También calcula **duración, convexidad y DV01** por cada
$1.000 millones de valor nominal. Se probó con las transacciones del **2 de octubre de 2026**
(29 papeles). El mismo código alimenta la página pública de la aplicación: <{URL_APP}> (sección
"Taller 2 · Curva TES", sin necesidad de registrarse).

**Resultado del 2-oct:** β0 = {_pct(b.b0)}, β1 = {_pct(b.b1)}, β2 = {_pct(b.b2)}, τ = {_n(tau, 1)} (fijo, como en el
Excel del profesor). Umbral de decisión: ±{_n(r.umbral_pb, 1)} pb. Decisiones:
**{cont.get("Comprar", 0)} comprar · {cont.get("Vender", 0)} vender · {cont.get("Mantener", 0)} mantener**.

# 2. Metodología paso a paso

1. **Datos.** Para cada papel: vencimiento, cupón, precio limpio y sucio, tasa publicada y valor
   nominal. Se validan (suma de nominales contra el total del informe, nemotécnico contra fecha de
   vencimiento, cupón corrido) antes de usarlos.
2. **Flujos.** Cada TES paga cupones anuales en los aniversarios de su vencimiento y 100 al final.
   El tiempo de cada flujo es *t* = días / 365 desde la fecha del informe.
3. **Curva Nelson-Siegel.** La tasa spot a plazo *t* es
   $S(t)=\\beta_0+\\beta_1\\frac{{1-e^{{-t/\\tau}}}}{{t/\\tau}}+\\beta_2\\left[\\frac{{1-e^{{-t/\\tau}}}}{{t/\\tau}}-e^{{-t/\\tau}}\\right]$
   y el factor de descuento es $(1+S(t))^{{-t}}$.
4. **Calibración.** Se escogen β0, β1, β2 que minimizan la suma de cuadrados de
   (precio sucio observado − precio estimado con la curva), exactamente como el Solver del Excel
   del profesor. Resultado: suma de errores² = {_n(cal.sse, 4)}.
5. **TIR observada y estimada.** La observada es la tasa que iguala los flujos al precio sucio de
   mercado; la estimada, la que iguala los flujos al precio calculado con la curva.
6. **Decisión.** Spread = TIR observada − TIR estimada. Si el spread supera +σ (una desviación
   estándar de los spreads del día) el papel paga más de lo que la curva indica → **comprar**; si es
   menor que −σ → **vender**; en otro caso **mantener**.
7. **DV01.** Pesos que gana (o pierde) un nominal de $1.000 millones si la TIR baja 1 punto básico.

# 3. Resultados del 2 de octubre de 2026

![Curva cero cupón y TIR observada de cada papel]({figs["curva"].name}){{width=90%}}

{_md(spots)}

## TIR observada vs. estimada y decisión

{_md(t1)}

![Spread de cada papel frente al umbral]({figs["spreads"].name}){{width=90%}}

## Duración, convexidad y DV01 por $1.000 millones

{_md(t2)}

El DV01 se calcula siempre sobre un nominal de $1.000 millones = $10^9$ pesos.

# 4. Qué tan sensible es la decisión al método

{_md(sens_t) if len(sens_t) else "Ver hoja *Sensibilidad* del Excel."}

La señal depende del método de calibración y del umbral: se presenta como una **ayuda para
priorizar el análisis**, no como una orden de operación.

# 5. Cómo sabemos que está bien (validación)

- Con la tabla del enunciado, los betas coinciden con el Excel del grupo (diferencia máxima
  $4{{,}}6\\times 10^{{-9}}$), y precios, TIR, spreads y DV01 coinciden con diferencias menores a $10^{{-7}}$.
- El motor reproduce además el Excel del profesor (17-mar-2026) con error menor a $10^{{-10}}$.
- El lector de PDF se probó con **31 informes reales** de IRC (21-sep a 6-nov-2026); ver
  `docs/taller-2/09-validacion.md` para las anomalías de los datos que se encontraron y cómo se tratan.

# 6. La aplicación y su actualización automática

Un proceso automático (GitHub Actions) puede correr cada día hábil: descarga los informes que falten
de IRC, los valida, calibra la curva y guarda el resultado en la base de datos (Supabase). La página
pública lo lee y muestra siempre el último día disponible y la historia desde el 2-oct. IRC publica con
unos días de retraso, por eso el proceso revisa una ventana de días. No es información en tiempo real:
es actualización diaria. Todo el proceso es repetible (idempotente).

# 7. Limitaciones

- τ fijo en {_n(tau, 1)}; el ajuste minimiza errores de **precio**, no de tasa.
- Los papeles de muy corto plazo (TCO) pesan poco en el precio pero mucho en la TIR; algunos días
  el informe trae precios con rezago (documentado en la validación).
- Una sola fecha de prueba en el informe; la decisión es sensible al umbral.
"""


def generar_pdf(r: ResultadoTES, sens: pd.DataFrame, carpeta: str | Path, hoy: dt.date) -> Path:
    carpeta = Path(carpeta)
    figs_dir = carpeta / "figuras"
    figs_dir.mkdir(parents=True, exist_ok=True)
    figs = {
        "curva": grafico_curva(r, figs_dir / "curva.png"),
        "spreads": grafico_spreads(r, figs_dir / "spreads.png"),
    }
    md = carpeta / "_informe.md"
    md.write_text(construir_markdown(r, sens, figs, hoy), encoding="utf-8")
    salida = carpeta / "Taller2_Informe.pdf"
    subprocess.run(
        ["pandoc", md.name, "-o", salida.name, "--pdf-engine=xelatex", "--resource-path=figuras"],
        cwd=carpeta,
        check=True,
    )
    md.unlink()
    return salida
