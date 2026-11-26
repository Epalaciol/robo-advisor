# ruff: noqa: E501  (texto del informe: prosa larga)
"""Informe PDF del Taller 2 (Markdown → PDF con pandoc + xelatex) para el 2-oct-2026."""

import datetime as dt
import subprocess
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import ParametrosTES  # noqa: E402
from ..core.analisis import ResultadoTES, analizar  # noqa: E402
from ..core.flujos import flujos_papel  # noqa: E402
from ..core.modelos import Papel  # noqa: E402
from ..core.nelson_siegel import spot  # noqa: E402
from ..core.rendimientos import aproximacion_precio, dv01_analitico  # noqa: E402

URL_APP = "https://mft-investements.streamlit.app/"
URL_REPO = "https://github.com/Epalaciol/robo-advisor"
COLOR = {"Comprar": "#2E7D32", "Vender": "#C62828", "Mantener": "#8a8a8a"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]  # fmt: skip
INTEGRANTES = [
    "Sebastian Duarte Uran",
    "Paulina Jaramillo Restrepo",
    "Juan David Londoño Grajales",
    "Juan Luis Orrego Henao",
    "Esteban Palacio Londoño",
]
PAPEL_EJEMPLO = "TFIT16180930"  # flujos paso a paso
PAPEL_CONVEXIDAD = "TFIT34130358"  # el más largo: donde más se nota la convexidad


def _n(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _pct(x: float, d: int = 2) -> str:
    return f"{_n(x * 100, d)} %"


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, disable_numparse=True)


def _fecha(f: dt.date) -> str:
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


# ------------------------------------------------------------------ gráficos


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


def grafico_dv01(r: ResultadoTES, ruta: Path) -> Path:
    tab = r.tabla
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.scatter(tab["duracion_modificada"], tab["dv01_cop"] / 1e3, color="#1F3864", s=24)
    for _, f in tab.iterrows():
        if f["plazo_anos"] > 10:
            ax.annotate(f["nemotecnico"], (f["duracion_modificada"], f["dv01_cop"] / 1e3),
                        fontsize=6, xytext=(3, 3), textcoords="offset points")  # fmt: skip
    ax.set_xlabel("Duración modificada (años)")
    ax.set_ylabel("DV01 por 1.000'000.000 COP de nominal (miles de COP)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


# ------------------------------------------------------------------ tablas auxiliares


def _nombre_umbral(x) -> str:
    nombres = {"sigma": "1 desviación estándar (base)", "sigma_robusta": "σ robusta (1,4826·MAD)"}
    return nombres.get(str(x)) or f"Fijo {_n(float(x), 0)} pb"


def _tabla_flujos(r: ResultadoTES, nemo: str) -> pd.DataFrame:
    f = r.flujos[r.flujos["nemotecnico"] == nemo]
    return pd.DataFrame(
        {
            "Fecha del flujo": f["fecha_flujo"].astype(str),
            "Flujo": [_n(x) for x in f["flujo"]],
            "Días (sin 29-feb)": f["dias"].astype(str),
            "t (años)": [_n(x, 4) for x in f["anos"]],
            "Tasa spot S(t)": [_pct(x, 3) for x in f["tasa_spot"]],
            "Factor de descuento": [_n(x, 6) for x in f["factor_descuento"]],
            "Valor presente": [_n(x, 4) for x in f["valor_presente"]],
        }
    )


def _tabla_convexidad(r: ResultadoTES, papeles: Sequence[Papel]) -> tuple[str, pd.DataFrame]:
    p = next(x for x in papeles if x.nemotecnico == PAPEL_CONVEXIDAD)
    fila = r.tabla.set_index("nemotecnico").loc[PAPEL_CONVEXIDAD]
    f = flujos_papel(p, r.fecha)
    filas = aproximacion_precio(float(fila["tir_observada"]), f)
    return p.nemotecnico, pd.DataFrame(
        {
            "Δ TIR": [f"{x['cambio_pb']:+.0f} pb" for x in filas],
            "ΔP/P exacto": [_pct(x["exacto"]) for x in filas],
            "Solo duración": [_pct(x["duracion"]) for x in filas],
            "Duración + conv.": [_pct(x["duracion_convexidad"]) for x in filas],
            "Error D (pb)": [_n((x["duracion"] - x["exacto"]) * 1e4, 1) for x in filas],
            "Error D + C (pb)": [
                _n((x["duracion_convexidad"] - x["exacto"]) * 1e4, 1) for x in filas
            ],
        }
    )


def _max_dif_dv01(r: ResultadoTES, papeles: Sequence[Papel]) -> float:
    tab = r.tabla.set_index("nemotecnico")
    rel = []
    for p in papeles:
        y = float(tab.loc[p.nemotecnico, "tir_observada"])
        a = dv01_analitico(y, flujos_papel(p, r.fecha), p.precio_sucio)
        rel.append(abs(tab.loc[p.nemotecnico, "dv01_cop"] / a - 1))
    return max(rel)


# ------------------------------------------------------------------ cuerpo


def construir_markdown(
    r: ResultadoTES,
    sens: pd.DataFrame,
    figs: dict[str, Path],
    hoy: dt.date,
    papeles: Sequence[Papel],
    sens_tau: pd.DataFrame | None = None,
) -> str:
    b, tau, cal = r.calibracion.betas, r.calibracion.tau, r.calibracion
    tab = r.tabla
    cont = r.conteo_senales()
    n_c, n_v, n_m = cont.get("Comprar", 0), cont.get("Vender", 0), cont.get("Mantener", 0)
    vender = ", ".join(tab.loc[tab["senal"] == "Vender", "nemotecnico"])
    comprar = ", ".join(tab.loc[tab["senal"] == "Comprar", "nemotecnico"]) or "ninguno"
    n_tco = int((tab["cupon"] == 0).sum())
    n_tf = len(tab) - n_tco
    nominal_total = float(sum(p.valor_nominal_mm or 0 for p in papeles))
    tir_vs_pub = (tab["tir_observada"] - tab["tasa_informe"]) / 1e-4
    sen = tab["origen_tasa"] == "SEN"
    dur_dif = (tab["duracion_macaulay"] - tab["duracion_informe"]).abs().max()
    dv_min, dv_max = tab.loc[tab["dv01_cop"].idxmin()], tab.loc[tab["dv01_cop"].idxmax()]
    corto = float(spot(1e-6, b, tau))

    t_res = pd.DataFrame(
        {
            "Nemotécnico": tab["nemotecnico"],
            "Vence": tab["vencimiento"].astype(str),
            "Cupón %": [_n(x) for x in tab["cupon"]],
            "Sucio obs.": [_n(x, 3) for x in tab["precio_sucio"]],
            "Precio curva": [_n(x, 3) for x in tab["precio_estimado"]],
            "TIR obs.": [_pct(x) for x in tab["tir_observada"]],
            "TIR est.": [_pct(x) for x in tab["tir_estimada"]],
            "Spread pb": [_n(x, 1) for x in tab["spread_pb"]],
            "Decisión": tab["senal"],
        }
    )
    t_dur = pd.DataFrame(
        {
            "Nemotécnico": tab["nemotecnico"],
            "Dur. Macaulay": [_n(x) for x in tab["duracion_macaulay"]],
            "Dur. informe IRC": [_n(x) for x in tab["duracion_informe"]],
            "Dur. modificada": [_n(x) for x in tab["duracion_modificada"]],
            "Convexidad": [_n(x) for x in tab["convexidad"]],
            "DV01 (COP)": [_n(x, 0) for x in tab["dv01_cop"]],
        }
    )
    spots = pd.DataFrame(
        {"Plazo": ["1 año", "2 años", "5 años", "10 años", "20 años", "30 años"],
         "Tasa cero cupón": [_pct(spot(float(p), b, tau)) for p in (1, 2, 5, 10, 20, 30)]}
    )  # fmt: skip
    s = sens[sens["umbral"].astype(str) == "sigma"]
    sens_t = pd.DataFrame(
        {
            "Calibración": s["calibracion"],
            "β0": [_pct(x) for x in s["b0"]],
            "β1": [_pct(x) for x in s["b1"]],
            "β2": [_pct(x) for x in s["b2"]],
            "Umbral (pb)": [_n(x, 1) for x in s["umbral_pb"]],
            "Comprar": s["comprar"].astype(str),
            "Vender": s["vender"].astype(str),
            "Mantener": s["mantener"].astype(str),
        }
    )
    u = sens[sens["calibracion"] == "Excel (todos, sin ponderar)"]
    sens_u = pd.DataFrame(
        {
            "Regla de umbral": [_nombre_umbral(x) for x in u["umbral"]],
            "Umbral (pb)": [_n(x, 1) for x in u["umbral_pb"]],
            "Comprar": u["comprar"].astype(str),
            "Vender": u["vender"].astype(str),
            "Mantener": u["mantener"].astype(str),
        }
    )
    tau_md = ""
    if sens_tau is not None and len(sens_tau):
        tt = sens_tau[sens_tau["tau"].isin([1.0, 2.0, 3.7, 5.0, 8.0])]
        tau_md = _md(
            pd.DataFrame(
                {
                    "τ": [_n(x, 1) for x in tt["tau"]],
                    "β0": [_pct(x) for x in tt["b0"]],
                    "β1": [_pct(x) for x in tt["b1"]],
                    "β2": [_pct(x) for x in tt["b2"]],
                    "Suma de errores²": [_n(x, 3) for x in tt["sse"]],
                }
            )
        )
    otra = "Act/365" if r.conteo_dias == "NL/365" else "NL/365"
    r_act = analizar(papeles, r.fecha, ParametrosTES(conteo_dias=otra))
    ta = r_act.tabla
    tir_act_pub = float(
        ((ta["tir_observada"] - ta["tasa_informe"]) / 1e-4)[ta["origen_tasa"] == "SEN"].abs().max()
    )
    filas_conv = []
    for nombre, rr in ((f"{r.conteo_dias} (este informe)", r), (f"{otra}", r_act)):
        cc = rr.conteo_senales()
        tt = rr.tabla
        filas_conv.append(
            {
                "Conteo de días": nombre,
                "β0": _pct(rr.calibracion.betas.b0),
                "β1": _pct(rr.calibracion.betas.b1),
                "β2": _pct(rr.calibracion.betas.b2),
                "Máx. dif. TIR vs. SEN (pb)": _n(
                    float(
                        ((tt["tir_observada"] - tt["tasa_informe"]) / 1e-4)[
                            tt["origen_tasa"] == "SEN"
                        ]
                        .abs()
                        .max()
                    ),
                    2,
                ),
                "Umbral (pb)": _n(rr.umbral_pb, 1),
                "C / V / M": f"{cc.get('Comprar', 0)} / {cc.get('Vender', 0)} / {cc.get('Mantener', 0)}",
            }
        )
    t_conv = pd.DataFrame(filas_conv)
    s1 = tab.set_index("nemotecnico")["senal"]
    s2 = ta.set_index("nemotecnico")["senal"]
    dif_s = [n for n in s1.index if s1[n] != s2[n]]
    cambia_conv = (
        "; ".join(
            f"el {n} ({_n(tab.set_index('nemotecnico').loc[n, 'spread_pb'], 1)} pb) es *{s1[n]}* con {r.conteo_dias} y *{s2[n]}* con {otra}"
            for n in dif_s
        )
        if dif_s
        else "ninguno"
    )
    nemo_cx, t_cx = _tabla_convexidad(r, papeles)
    fe = tab.set_index("nemotecnico").loc[PAPEL_EJEMPLO]
    fl_ej = r.flujos[r.flujos["nemotecnico"] == PAPEL_EJEMPLO]
    dif_dv = _max_dif_dv01(r, papeles)
    autores = "\n".join(f"  - {x}" for x in INTEGRANTES)

    return f"""---
title: "Taller 2 · Curva cero cupón de TES con Nelson-Siegel, TIR, decisión y DV01"
subtitle: "Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026"
author:
{autores}
  - "Profesor: Juan Carlos Botero Ramírez"
date: "{_fecha(hoy)}"
lang: es
geometry: margin=2.2cm
fontsize: 10pt
mainfont: Arial
colorlinks: true
toc: true
toc-depth: 2
numbersections: true
header-includes:
  - \\usepackage{{float}}
  - \\floatplacement{{figure}}{{H}}
  - \\usepackage{{etoolbox}}
  - \\AtBeginEnvironment{{longtable}}{{\\small}}
---

\\newpage

# Resumen ejecutivo {{-}}

Construimos un código en Python que, para **cualquier día**, toma el *Informe Diario de Deuda Pública* de
[www.irc.gov.co](https://www.irc.gov.co/440), calibra los betas de **Nelson-Siegel**, calcula la **curva cero
cupón**, valora cada TES tasa fija en pesos que se transó ese día, calcula su **TIR observada** (con el precio de
mercado) y su **TIR estimada** (con el precio que da la curva), y decide si hay una oportunidad de **comprar,
vender o mantener**. Además calcula **duración, convexidad y DV01 por cada 1.000'000.000 COP (mil millones de pesos)** de nominal.

Con las transacciones del **2 de octubre de 2026** (la tabla del enunciado: {len(tab)} papeles, {n_tco} TCO y {n_tf}
TFIT/TFVT):

- **Betas:** β0 = **{_pct(b.b0)}**, β1 = **{_pct(b.b1)}**, β2 = **{_pct(b.b2)}**, con τ = {_n(tau, 1)} (como el Excel del
  profesor) y la convención de días del mercado de TES (sin 29 de febrero). La curva es **creciente**: parte de {_pct(corto)} en el muy corto plazo y se acerca a {_pct(b.b0)} en el largo.
- **Decisión** (umbral ±{_n(r.umbral_pb, 1)} pb, una desviación estándar de las diferencias del día):
  **{n_c} comprar · {n_v} vender · {n_m} mantener**. Vender: {vender}. Comprar: {comprar}.
- **DV01:** va de {_n(dv_min["dv01_cop"], 0)} COP ({dv_min["nemotecnico"]}) a **{_n(dv_max["dv01_cop"], 0)} COP** ({dv_max["nemotecnico"]})
  por punto básico y por 1.000'000.000 COP de nominal.
- **Validación:** la TIR calculada con el precio publicado da exactamente la tasa SEN de IRC (diferencia máxima
  {_n(tir_vs_pub[sen].abs().max(), 2)} pb), y con la convención de días del profesor el motor reproduce su *Modelo Nelson
  Siegel.xlsx* (error < $10^{{-10}}$) y el Excel del grupo (betas a $5\\times10^{{-9}}$).
- **Más allá del enunciado:** el mismo código corre solo cada día hábil y publica la curva en una página
  **pública, sin registro**. **Lo invitamos a visitarla** para ver la curva cero cupón de cada día desde el
  21-sep-2026 y cómo ha cambiado: <{URL_APP}> → "T2 Curva TES" (sección 4.2).

> **Aviso:** ejercicio académico. Las decisiones del modelo no constituyen una recomendación de inversión.

# Metodología

**Flujo.** Para un día *d*:

1. *Datos:* informe de IRC del día *d* → tabla "Tasa Fija en Pesos" (vencimiento, cupón, precio limpio y sucio,
   tasa publicada, duración y nominal) → validaciones.
2. *Flujos:* calendario de pagos de cada papel y su plazo *t* en años.
3. *Curva:* betas de Nelson-Siegel que mejor explican los precios sucios de todos los papeles (Solver).
4. *Por papel:* precio con la curva → TIR estimada; precio de mercado → TIR observada; diferencia en pb → decisión.
5. *Riesgo:* duración de Macaulay y modificada, convexidad y DV01 por 1.000'000.000 COP de nominal.

**Herramientas.** **Python** hace los cálculos (numpy, scipy en lugar del Solver, pandas), este informe y el Excel; las
mismas funciones alimentan la aplicación, así los números coinciden. El **Excel** adjunto repite el modelo con
fórmulas vivas para revisarlo celda por celda. Un **proceso automático** (GitHub Actions) descarga el informe de
cada día y guarda los resultados en una **base de datos en la nube** (Supabase) que lee la página pública. Se usó
**inteligencia artificial** (un asistente de programación) para construir el código; los cálculos son fórmulas fijas.

**Supuestos** (los del *Modelo Nelson Siegel.xlsx*, salvo el conteo de días):

| Supuesto | Valor | Por qué |
|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| Papeles | TES tasa fija en pesos con vencimiento posterior al día del informe | Es la tabla que indica el enunciado |
| Cupón | Anual, en el aniversario del vencimiento; los TCO no pagan cupón | Convención de los TES |
| Plazo | *t* = días / 365 desde la fecha del informe, **sin contar los 29 de febrero** (NL/365) | Convención del mercado de TES: reproduce la tasa SEN de IRC. El Excel del profesor usa días calendario (sección 3.4) |
| Tasas | Efectivas anuales; descuento $(1+S(t))^{{-t}}$ | Igual al Excel del profesor |
| τ | {_n(tau, 1)} fijo | Igual al Excel del profesor; la sensibilidad está en la sección 3.3 |
| Función objetivo | $\\sum$ (precio sucio observado − precio con la curva)², sin ponderar | La celda que minimiza el Solver del Excel |
| Decisión | Umbral = 1 desviación estándar de las diferencias del día | Separa lo "normal" de lo que se sale de la curva |
| DV01 | Nominal de 1.000'000.000 COP (mil millones de pesos) = $10^9$ COP | Lo pide el enunciado |

## Datos del informe de IRC

El *Informe Diario de Deuda Pública* trae, para cada TES transado o valorado, el nemotécnico, la fecha de
vencimiento, el cupón, el precio limpio y el sucio, la tasa y su origen (**SEN**: sale de operaciones del día en el
sistema del Banco de la República; **VAL**: tasa de valoración vigente publicada por el proveedor de precios
PRECIA), la duración y el saldo en circulación (valor nominal, en millones de COP). El informe trae además una
tabla de TES en UVR, que no se usa: el enunciado pide la tabla "Tasa Fija en Pesos". Para el 2-oct se usó **la tabla del enunciado** ({len(tab)} filas; nominal total {_n(nominal_total, 0)} millones,
igual al total del informe). Antes de calcular se revisa que la suma de nominales cuadre con el total, que la fecha
del nemotécnico coincida con el vencimiento y que el cupón corrido (sucio − limpio) sea coherente con el cupón.

## Flujos de cada papel

Un TES paga su cupón (en % del nominal) cada año en el aniversario de su vencimiento y 100 al final; un TCO
paga solo 100 al vencimiento. El plazo de cada flujo se mide en días **sin contar los 29 de febrero**, que es la
convención del mercado de TES (base 365/365, *NL/365*): un año tiene siempre 365 días. Ejemplo, **{PAPEL_EJEMPLO}** (cupón {_n(fe["cupon"])} %, vence {fe["vencimiento"]}):

{_md(_tabla_flujos(r, PAPEL_EJEMPLO))}

La suma de los valores presentes, **{_n(fl_ej["valor_presente"].sum(), 4)}**, es el precio sucio que da la curva; el de
mercado es {_n(fe["precio_sucio"], 3)}.

## La curva Nelson-Siegel

La tasa cero cupón (spot) a plazo *t* años es

$$S(t)=\\beta_0+\\beta_1\\,\\frac{{1-e^{{-t/\\tau}}}}{{t/\\tau}}+\\beta_2\\left[\\frac{{1-e^{{-t/\\tau}}}}{{t/\\tau}}-e^{{-t/\\tau}}\\right],
\\qquad FD(t)=(1+S(t))^{{-t}}, \\qquad P=\\sum_k F_k\\,FD(t_k).$$

- **β0 (nivel):** la tasa de largo plazo; $S(t)\\to\\beta_0$ cuando $t\\to\\infty$.
- **β1 (pendiente):** $S(0)=\\beta_0+\\beta_1$; si β1 < 0 la curva es creciente.
- **β2 (curvatura):** crea una joroba (β2 > 0) o un valle (β2 < 0) en plazos medios, con su máximo efecto
  cerca de $t\\approx1{{,}}79\\,\\tau$.
- **τ:** dónde ocurre la transición entre corto y largo plazo.

## Calibración (el Solver)

Se buscan β0, β1 y β2 que minimizan $\\sum_i (P_i^{{obs}}-P_i^{{NS}})^2$ sobre todos los papeles del día, con τ fijo. Se usa el
método de mínimos cuadrados no lineales de scipy (`least_squares`, que cumple el papel del Solver de Excel) desde varios puntos de partida, entre ellos los betas
del Excel del profesor, y se conserva la mejor solución. Para el 2-oct la suma de errores² es **{_n(cal.sse, 4)}**
(error cuadrático medio de {_n(cal.rmse, 3)} por cada 100 de precio).

## TIR observada, TIR estimada y decisión

- **TIR observada** $y^{{obs}}$: la tasa que iguala los flujos del papel a su **precio sucio de mercado**,
  $P^{{obs}}=\\sum_k F_k (1+y^{{obs}})^{{-t_k}}$.
- **TIR estimada** $y^{{est}}$: la tasa que iguala los mismos flujos al **precio que da la curva** cero cupón,
  $P^{{NS}}=\\sum_k F_k (1+y^{{est}})^{{-t_k}}$. Es la TIR "justa" según el resto del mercado.
- **Spread** $=(y^{{obs}}-y^{{est}})\\times 10.000$ pb. Con $\\sigma$ = desviación estándar de los spreads del día:

| Spread | Lectura | Decisión |
|---|---|---|
| > +σ | El papel rinde más de lo que indica la curva: está **barato** | **Comprar** |
| < −σ | Rinde menos de lo que indica la curva: está **caro** | **Vender** |
| entre −σ y +σ | Dentro de lo normal | **Mantener** |

## Duración, convexidad y DV01

Con la TIR observada *y* y $VP_k=F_k(1+y)^{{-t_k}}$:

$$D_{{Mac}}=\\frac{{\\sum_k t_k\\,VP_k}}{{P}},\\qquad D^*=\\frac{{D_{{Mac}}}}{{1+y}},\\qquad C=\\frac{{\\sum_k t_k(t_k+1)\\,VP_k}}{{P\\,(1+y)^2}},$$

$$DV01=\\big[P(y-\\tfrac12\\,\\text{{pb}})-P(y+\\tfrac12\\,\\text{{pb}})\\big]\\cdot\\frac{{N}}{{100}}\\;\\approx\\;N\\cdot\\frac{{P}}{{100}}\\cdot D^*\\cdot 0{{,}}0001,
\\qquad N=\\text{{1.000'000.000 COP}}=10^9.$$

El DV01 es cuántos COP gana (pierde) una posición de 1.000'000.000 COP (mil millones de pesos) de nominal si la TIR baja (sube) 1 pb. Se
calcula revaluando el bono y se verifica contra la fórmula con la duración modificada (diferencia relativa
máxima {dif_dv:.0e}).

# Resultados del 2 de octubre de 2026

## La curva cero cupón

β0 = **{_pct(b.b0, 4)}**, β1 = **{_pct(b.b1, 4)}**, β2 = **{_pct(b.b2, 4)}**, τ = {_n(tau, 1)}.

![Curva cero cupón y TIR observada de cada papel (color = decisión)]({figs["curva"].name}){{width=88%}}

{_md(spots)}

La curva es **creciente y poco empinada**: unos {_n((spot(30.0, b, tau) - spot(1.0, b, tau)) / 1e-4, 0)} pb entre 1 y 30 años. β1 < 0 da la
pendiente positiva y β2 > 0 una leve joroba en plazos medios. La mayor desviación es la del TFIT08031127
(1 año), muy por debajo de la curva; los TCO que vencen entre enero y junio de 2027 y el TFIT 2050 también quedan por debajo.

## TIR observada vs. estimada y decisión

{_md(t_res)}

![Spread de cada papel frente al umbral de ±{_n(r.umbral_pb, 1)} pb]({figs["spreads"].name}){{width=88%}}

**Lectura.** Con umbral ±{_n(r.umbral_pb, 1)} pb el modelo marca **{n_v} papeles para vender** ({vender}) y **{n_c} para comprar**.
El caso más claro es el **TFIT08031127**: su TIR observada ({_pct(tab.set_index("nemotecnico").loc["TFIT08031127", "tir_observada"])}) está unos
{_n(abs(tab.set_index("nemotecnico").loc["TFIT08031127", "spread_pb"]), 0)} pb por debajo de lo que indica la curva; en todos los informes revisados (21-sep a 6-nov) este papel cotiza muy por debajo de la curva, así
que la señal refleja una característica persistente del papel más que una oportunidad pasajera. Los
otros "vender" son TCO que vencen entre enero y junio de 2027, cuyo precio sale en su mayoría del proveedor (VAL) y no de operaciones
del día, y el TFIT31261050, el único TFIT largo con precio VAL.

**TIR observada vs. tasa publicada por IRC.** Para los {int(sen.sum())} papeles con tasa SEN, la TIR calculada con el precio sucio
coincide con la tasa publicada por IRC (diferencia máxima {_n(tir_vs_pub[sen].abs().max(), 2)} pb; el TFIT34130358, por ejemplo, da
{_pct(tab.set_index("nemotecnico").loc["TFIT34130358", "tir_observada"], 3)} como el informe). Esto confirma que se usa la misma convención de días del mercado. En los TCO
con tasa VAL la diferencia llega a {_n(tir_vs_pub[~sen].abs().max(), 0)} pb en el más corto por otra razón: la tasa VAL es la de valoración
de PRECIA y no sale del precio publicado. Por eso la TIR observada se calcula siempre desde el precio, igual que en
el Excel del profesor.

## Duración, convexidad y DV01 por 1.000'000.000 COP

{_md(t_dur)}

La duración de Macaulay calculada coincide con la que publica IRC (diferencia máxima {_n(dur_dif, 3)} años). El DV01
crece con la duración modificada y con el precio: un TFIT con cupón alto y precio sobre la par (TFIT34130358,
TFIT23250746) tiene más DV01 que uno más largo pero muy por debajo de la par (TFIT31261050).

![DV01 por 1.000'000.000 COP de nominal frente a la duración modificada]({figs["dv01"].name}){{width=80%}}

**Cómo leerlo.** Si la TIR del {dv_max["nemotecnico"]} sube 1 pb, una posición de 1.000'000.000 COP de nominal pierde unos
{_n(dv_max["dv01_cop"], 0)} COP; si sube 100 pb, alrededor de 100 veces eso (menos por la convexidad).

## Duración y convexidad: qué tan buena es la aproximación

Para el papel más largo, **{nemo_cx}**, se compara el cambio exacto de precio (revaluando el bono) con las
aproximaciones $\\Delta P/P\\approx-D^*\\Delta y$ y $\\Delta P/P\\approx-D^*\\Delta y+\\tfrac12 C(\\Delta y)^2$:

{_md(t_cx)}

(Errores en puntos básicos de precio: aproximación − exacto.) La duración sola **subestima el precio en ambos
sentidos**: se queda corta en la subida cuando la tasa baja y exagera la caída cuando la tasa sube, porque el precio
es convexo en la tasa. Al sumar la convexidad el error baja de unos 45–50 pb a unos 3 pb con ±100 pb. Por eso, para movimientos grandes,
el DV01 no basta y conviene mirar también la convexidad.

# Qué tan sensible es la decisión

## Al método de calibración

{_md(sens_t)}

Ponderar por duración (que aproxima minimizar errores de **tasa** en vez de precio) o calibrar solo con las tasas SEN
mueve los betas, sobre todo β2 (la curvatura), y cambia qué papeles quedan fuera del umbral.

## Al umbral

{_md(sens_u)}

## A τ

{tau_md}

La suma de errores² casi no cambia entre τ = 1 y τ = 8: τ = {_n(tau, 1)} es razonable y los betas son estables.

## A la convención de días

El *Modelo Nelson Siegel.xlsx* del profesor mide el plazo en días calendario / 365 (*Act/365*); el mercado de TES, y
este informe, usan días sin contar los 29 de febrero (*NL/365*), que es con lo que IRC calcula el precio a partir de
la tasa. Con días calendario, cada 29 de febrero hasta el vencimiento alarga un poco los plazos y baja la TIR: el
TFIT34130358 daría {_pct(r_act.tabla.set_index("nemotecnico").loc["TFIT34130358", "tir_observada"], 3)} en vez del {_pct(tab.set_index("nemotecnico").loc["TFIT34130358", "tir_observada"], 3)} publicado. El efecto es nulo en los papeles que
vencen antes del 29-feb-2028 y de hasta {_n(tir_act_pub, 1)} pb en los demás (es mayor en el TFIT 2028, porque un día de
más pesa más en un plazo corto).

{_md(t_conv)}

Como la TIR observada y la estimada se calculan con la misma convención, el spread se mueve poco y solo cambia un
papel cercano al umbral: {cambia_conv}.

**Conclusión.** La señal depende del método y del umbral: se presenta como una **ayuda para priorizar el análisis**
de papeles que se salen de la curva, no como una orden de operación.

# Cómo se usa para un día determinado

## Desde el código

El mismo código corre para cualquier fecha publicada por IRC:

```
pip install -e ".[reportes]"
python -m roboadvisor.taller2.pipeline.update_tes --fecha 2026-10-02 --sin-supabase
python -m roboadvisor.taller2.pipeline.update_tes --archivo informe.pdf --sin-supabase
```

El primero descarga el informe de esa fecha de www.irc.gov.co; el segundo usa un PDF (o la tabla en CSV) ya
descargado. Ambos imprimen los betas y guardan en `exports/taller2/<fecha>/` la tabla por papel (TIR, decisión,
duración, convexidad, DV01), los flujos, la curva de 1 a 10.950 días y los parámetros.

## Vea las curvas de otros días en la página web

Este informe muestra un solo día, pero el modelo **se sigue ejecutando**. Un proceso automático (GitHub Actions)
corre cada día hábil: descarga los informes de IRC que falten, los valida, calibra la curva (partiendo de los betas
del día anterior, como se haría con el Solver) y guarda el resultado en la base de datos. **Lo invitamos a ver el
resultado en la página pública, sin necesidad de registrarse:**

> **<{URL_APP}> → página "T2 Curva TES"**

Allí puede:

1. **Escoger la fecha del informe** en la lista desplegable (por defecto, el último día disponible) y ver los betas,
   la **curva cero cupón** de ese día con la TIR observada de cada papel y su decisión.
2. En **"Tabla por papel"**, revisar para esa fecha la TIR observada y estimada, el spread, la decisión, la duración,
   la convexidad y el DV01 por 1.000'000.000 COP de nominal, y descargarla en CSV.
3. En **"Historia"**, comparar las **curvas de todos los días superpuestas**, la evolución de β0, β1 y β2 y de las
   tasas cero cupón a 1, 5 y 10 años desde el 21-sep-2026.
4. En **"Cómo leer esto"**, un resumen de la metodología.

IRC publica con algunos días de rezago, así que la página se actualiza **a diario**, no en tiempo real. Si IRC
pasa varios días sin publicar, la página muestra el último informe disponible y avisa cuántos días hábiles tiene.

# Validación

- **Tasa SEN de IRC:** con la convención del mercado (sin 29 de febrero) la TIR del precio publicado coincide con la
  tasa SEN en los {int(sen.sum())} papeles (diferencia máxima {_n(tir_vs_pub[sen].abs().max(), 2)} pb). En los 32 informes del 21-sep al 6-nov
  coincide a menos de 0,1 pb en 526 de 531 observaciones SEN (con días calendario, solo en 44); las 5 excepciones
  son precios con rezago del informe (22 y 23-oct, 21-sep), documentados en la validación.
- **Modelo Nelson Siegel.xlsx (profesor, 17-mar-2026):** con sus betas y su conteo de días (días calendario) el
  motor reproduce el precio de los papeles con error menor a $10^{{-10}}$.
- **Excel y script del grupo (2-oct, días calendario):** betas con diferencia máxima $4{{,}}6\\times10^{{-9}}$; precio
  estimado con diferencia menor a $10^{{-7}}$, TIR menor a $10^{{-8}}$, spread menor a 0,001 pb y DV01 relativo menor a $10^{{-8}}$.
- **PDF real del 2-oct:** al correr `update_tes --fecha 2026-10-02` con el informe descargado de IRC se leen los
  mismos {len(tab)} papeles y se obtienen los mismos betas y decisiones que con la tabla del enunciado.
- **Lectura de los PDF de IRC:** se probó con los **33 informes** publicados entre el 21-sep y el 6-nov-2026. En los
  32 que tienen texto, cada valor leído (nominal, cupón, precios, duración, tasas, origen y variación; 939 filas) se
  comparó con una segunda extracción hecha con otro motor de PDF: **cero diferencias**, y la suma de nominales cuadra
  con el total del informe (salvo diferencias de 2–3 millones por redondeo de la fuente). Se encontraron y se
  tratan anomalías de la fuente: totales que difieren por redondeo, un TCO publicado con cupón 1 %, un informe
  que es una imagen sin texto y un cupón que se paga el día del informe (detalle en `docs/taller-2/09-validacion.md`).
- **Pruebas automáticas** (`tests/taller2/`): DV01 por revaluación = fórmula con duración, duración = la publicada
  por IRC, la aproximación con convexidad mejora la de duración, y la tabla del 2-oct cuadra con el total del informe.

# Conclusiones

1. Con tres parámetros (β0, β1, β2) y τ fijo, Nelson-Siegel describe bien la curva de TES del 2-oct: un error
   cuadrático medio de {_n(cal.rmse, 2)} por cada 100 de precio para {len(tab)} papeles de 18 días a 31 años.
2. La curva cero cupón del 2-oct es creciente, de {_pct(spot(1.0, b, tau))} a 1 año a {_pct(spot(30.0, b, tau))} a 30 años.
3. Comparar la TIR observada con la estimada separa los papeles que se salen de la curva: {n_v} para vender y
   {n_c} para comprar con umbral de una desviación estándar; la lista cambia con el umbral y el método.
4. El riesgo de tasa crece con el plazo: el DV01 por 1.000'000.000 COP de nominal va de {_n(dv_min["dv01_cop"], 0)} COP en el {dv_min["nemotecnico"]} a
   {_n(dv_max["dv01_cop"], 0)} COP en el {dv_max["nemotecnico"]}, y para cambios grandes de tasa la convexidad corrige de forma visible la duración.
5. El mismo código sirve para cualquier día: la curva de cada día publicado por IRC desde el 21-sep se puede consultar en
   <{URL_APP}> → "T2 Curva TES".

# Limitaciones

- τ fijo en {_n(tau, 1)}; el ajuste minimiza errores de **precio**, por lo que los TCO (duración baja) pesan poco en
  la calibración aunque su TIR se desvíe.
- Muchos precios del informe son de valoración (VAL) y no de operaciones del día; algunos días traen precios con
  rezago. La decisión debería mirarse junto con el origen de la tasa.
- La decisión es estática (un día) y no considera liquidez, costos de transacción ni el carry.
- La curva se calibra con TES tasa fija en pesos; no incluye UVR ni otros emisores.

"""


def generar_pdf(
    r: ResultadoTES,
    sens: pd.DataFrame,
    carpeta: str | Path,
    hoy: dt.date,
    papeles: Sequence[Papel],
    sens_tau: pd.DataFrame | None = None,
) -> Path:
    carpeta = Path(carpeta)
    figs_dir = carpeta / "figuras"
    figs_dir.mkdir(parents=True, exist_ok=True)
    figs = {
        "curva": grafico_curva(r, figs_dir / "curva.png"),
        "spreads": grafico_spreads(r, figs_dir / "spreads.png"),
        "dv01": grafico_dv01(r, figs_dir / "dv01.png"),
    }
    md = carpeta / "_informe.md"
    md.write_text(construir_markdown(r, sens, figs, hoy, papeles, sens_tau), encoding="utf-8")
    salida = carpeta / "Taller2_Informe.pdf"
    subprocess.run(
        [
            "pandoc",
            md.name,
            "-o",
            salida.name,
            "--pdf-engine=xelatex",
            "--resource-path=figuras",
            "--columns=200",
        ],  # fmt: skip
        cwd=carpeta,
        check=True,
    )
    md.unlink()
    return salida
