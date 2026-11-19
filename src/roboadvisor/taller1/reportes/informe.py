# ruff: noqa: E501  (texto del informe: prosa larga)
"""Informe PDF del Taller 1 (Markdown → PDF con pandoc + xelatex), explicado paso a paso.

Estructura: resumen · cumplimiento del enunciado · metodología · Parte 1 (aversión al riesgo y los
cinco voluntarios) · Parte 2 (Markowitz, CAL, portafolio completo, tope de 100 %, beta/duration,
múltiplos) · aplicativo · EDA de todas las encuestas · conclusiones · anexos.
"""

import datetime as dt
import subprocess
from pathlib import Path

import pandas as pd

from roboadvisor.taller1.core.cuestionario import IDS_PREGUNTAS, PREGUNTAS, puntuar
from roboadvisor.taller1.data.semillas import leer_catalogo

from . import eda as eda_mod
from . import graficos
from .caso import (
    BENCHMARK,
    DURATIONS,
    TABLA_PERFILES,
    UNIVERSO_REFERENCIA,
    CasoReferencia,
    composicion_completa,
    escenarios_extendidos,
    estadisticas_universo,
    multiplos_referencia,
    optimo_sin_apalancamiento,
    portafolio_de_voluntario,
    sharpe_catalogo_elegible,
)

URL_APP = "https://mft-investements.streamlit.app/"
URL_REPO = "https://github.com/Epalaciol/robo-advisor"
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
RANGOS_ENUNCIADO = ["25-34", "35-44", "45-54", "55-64", "65-74"]
CLASE_ETF = {
    "SMH": "Acciones EE.UU. (semiconductores)",
    "COLO": "Acciones Colombia",
    "QQQ": "Acciones EE.UU.",
    "EFA": "Acciones EAFE",
    "EEM": "Acciones emergentes",
    "ILF": "Acciones Latinoamérica",
    "LQD": "Renta fija IG EE.UU.",
    "HYG": "Renta fija HY EE.UU.",
    "EMB": "Renta fija resto del mundo (emergente)",
    "VNQ": "REIT",
    "GLD": "Materias primas (oro)",
}
ETIQUETA_FACTOR = eda_mod.ETIQUETA_FACTOR
APALANCADOS = {"TQQQ", "UPRO", "TNA", "TECL", "SOXL", "UCO"}


# ------------------------------------------------------------------ utilidades de formato


def _pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f} %".replace(".", ",")


def _num(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, disable_numparse=True)


def _fecha(f) -> str:
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def _medio_a(a: float) -> str:
    """½·A como texto corto: 8 → 4, 3 → 1,5, 1 → 0,5."""
    v = a / 2
    return str(int(v)) if v == int(v) else _num(v, 1)


# ------------------------------------------------------------------ Parte 1: los 5 voluntarios


def cinco_voluntarios(voluntarios: pd.DataFrame) -> pd.DataFrame:
    """Uno por rango del enunciado: el primero que completó la encuesta en ese rango.

    El exportador ordena por rango y fecha de registro y numera V1, V2…: el primer alias de
    cada rango es la persona que primero respondió (criterio objetivo, fijado de antemano).
    """
    v = voluntarios[voluntarios["rango_edad"].isin(RANGOS_ENUNCIADO)]
    primeros = v.groupby("rango_edad", sort=False).head(1).set_index("rango_edad")
    return primeros.loc[[r for r in RANGOS_ENUNCIADO if r in primeros.index]].reset_index()


def seccion_voluntarios(c: CasoReferencia, voluntarios: pd.DataFrame | None) -> str:
    if voluntarios is None or voluntarios.empty:
        return (
            "**Pendiente de completar.** Los resultados de los cinco voluntarios (uno por rango de "
            "edad) se agregan al correr el generador con el archivo `datos/voluntarios.csv`."
        )
    cinco = cinco_voluntarios(voluntarios)
    alias = list(cinco["alias"])
    resp = [{q: str(r[q]) for q in IDS_PREGUNTAS} for _, r in cinco.iterrows()]
    res = [puntuar(x) for x in resp]
    port = [portafolio_de_voluntario(c, x) for x in resp]

    def fila(nombre: str, valores: list[str]) -> dict:
        return {"": nombre, **dict(zip(alias, valores, strict=True))}

    filas = [fila("Rango de edad", list(cinco["rango_edad"]))]
    filas += [fila(eda_mod.ETIQUETA_PREGUNTA[q], [x[q] for x in resp]) for q in IDS_PREGUNTAS]
    filas += [
        fila(
            "Respuestas a / b / c",
            [f"{x.conteo['a']} / {x.conteo['b']} / {x.conteo['c']}" for x in res],
        ),
        fila(
            "Puntaje (1·a + 2·b + 3·c)",
            [
                f"{x.conteo['a']}+{2 * x.conteo['b']}+{3 * x.conteo['c']} = **{x.puntaje}**"
                for x in res
            ],
        ),
        fila("**Perfil**", [x.etiqueta for x in res]),
        fila("**A**", [f"**{x.a}**" for x in res]),
        fila("Función de utilidad", [f"$E(r) - {_medio_a(x.a)}\\sigma^2$" for x in res]),
        fila("En portafolio de riesgo (y*)", [_pct(p["y"], 0) for p in port]),
        fila("En libre de riesgo", [_pct(p["peso_rf"], 0) for p in port]),
        fila("Retorno esperado E(Rc)", [_pct(p["retorno"]) for p in port]),
        fila("Riesgo σc", [_pct(p["sigma"]) for p in port]),
        fila("Utilidad U", [_pct(p["utilidad"], 2) for p in port]),
    ]
    tabla = _md(pd.DataFrame(filas))

    factores = [f for f in ETIQUETA_FACTOR if f != "rango_edad" and f in cinco.columns]
    t = cinco.set_index("alias")[factores].replace("", "—").fillna("—").T
    t.index = [ETIQUETA_FACTOR[f] for f in t.index]
    tabla_factores = _md(t.reset_index(names="Factor"))

    faltan = [r for r in RANGOS_ENUNCIADO if r not in set(cinco["rango_edad"])]
    aviso = (
        f"\n\n> **Pendiente:** faltan voluntarios en los rangos {', '.join(faltan)}."
        if faltan
        else ""
    )
    lista = ", ".join(f"{a} ({r})" for a, r in zip(alias, cinco["rango_edad"], strict=True))
    perfiles_txt = "; ".join(
        f"{a} ({r}): *{x.etiqueta.lower()}*, $y^*$ = {_pct(p['y'], 0)}"
        for a, r, x, p in zip(alias, cinco["rango_edad"], res, port, strict=True)
    )
    sin_factores = [
        a
        for a in alias
        if (cinco.set_index("alias").loc[a, factores].astype(str).str.strip() == "").all()
    ]
    lectura = (
        f"{perfiles_txt}. La persona de mayor edad ({alias[-1]}) es la más aversa al riesgo; entre los otros "
        f"cuatro el perfil va de *{min(res[:-1], key=lambda x: x.puntaje).etiqueta.lower()}* a "
        f"*{max(res[:-1], key=lambda x: x.puntaje).etiqueta.lower()}* sin un patrón claro con la edad"
        + (
            f". {', '.join(sin_factores)} no diligenció los factores opcionales"
            if sin_factores
            else ""
        )
    )
    return f"""
Los cinco voluntarios del enunciado son **{lista}**. Criterio de selección, fijado antes de ver las
respuestas: en cada rango de edad se toma **la primera persona que completó la encuesta** en la
aplicación. Los alias son anónimos (V1…V{len(voluntarios)}, ordenados por rango de edad y fecha de registro);
no se publican nombres ni correos.

**Cálculo de A, paso a paso** (respuesta de cada voluntario a cada pregunta; a = 1, b = 2 y c = 3
puntos). Las filas finales anticipan su portafolio completo, con el mismo portafolio de riesgo
óptimo para todos:

{tabla}

**Información personal recolectada** (para entender qué moldea la aversión al riesgo):

{tabla_factores}

Lectura: {lectura}. Con cinco personas esto es solo un indicio; el análisis exploratorio (sección 5) lo revisa con las
{len(voluntarios)} encuestas recogidas.{aviso}
"""


# ------------------------------------------------------------------ cuerpo del informe


def construir_markdown(
    c: CasoReferencia,
    figuras: dict[str, Path],
    voluntarios: pd.DataFrame | None,
    fecha: dt.date,
    fundamentales: pd.DataFrame | None = None,
    eda: "eda_mod.ResultadosEDA | None" = None,
) -> str:
    t = c.tangente
    w = t.w
    activos = w[w > 0.0005].sort_values(ascending=False)
    tope = [x for x in activos.index if activos[x] >= c.params.w_max - 1e-4]
    est_u = estadisticas_universo(c)
    esc = escenarios_extendidos(c)
    sin_ap = optimo_sin_apalancamiento(c)
    comp = composicion_completa(c)
    ini, fin = c.ventana
    y8 = float(esc.loc[esc.a == 8, "y"].iloc[0])
    y6 = float(esc.loc[esc.a == 6, "y"].iloc[0])
    peso_bonos = float(w.reindex(list(DURATIONS)).fillna(0).sum())
    n_vol = 0 if voluntarios is None else len(voluntarios)
    origen = (
        voluntarios["origen_portafolio"]
        if voluntarios is not None and "origen_portafolio" in voluntarios
        else pd.Series(dtype=str)
    )

    universo = pd.DataFrame(
        {
            "Ticker": list(UNIVERSO_REFERENCIA),
            "ETF": list(UNIVERSO_REFERENCIA.values()),
            "Clase (enunciado)": [CLASE_ETF[x] for x in UNIVERSO_REFERENCIA],
        }
    )
    tabla_est = pd.DataFrame(
        {
            "Activo": est_u.index,
            "Retorno medio": [_pct(v) for v in est_u["retorno_medio"]],
            "σ anual": [_pct(v) for v in est_u["sigma"]],
            "Sharpe": [_num(v) for v in est_u["sharpe"]],
            "CAGR": [_pct(v) for v in est_u["cagr"]],
            "Caída máx.": [_pct(v, 0) for v in est_u["caida_maxima"]],
            "Peso en P": [_pct(w[x]) if x in w.index else "100 %" for x in est_u.index],
        }
    )
    optimo = pd.DataFrame(
        {
            "ETF": activos.index,
            "Clase": [CLASE_ETF[x] for x in activos.index],
            "Peso": [_pct(v) for v in activos.to_numpy()],
            "Retorno esperado": [_pct(c.est.mu[x]) for x in activos.index],
            "σ": [_pct(c.est.sigma.loc[x, x] ** 0.5) for x in activos.index],
        }
    )
    perfiles = pd.DataFrame(
        {
            "Puntaje": [f"{a}–{b}" for a, b, _e, _A in TABLA_PERFILES],
            "Perfil": [e for _a, _b, e, _A in TABLA_PERFILES],
            "A": [str(A) for *_x, A in TABLA_PERFILES],
            "Función de utilidad": [
                f"$U = E(r) - {_medio_a(A)}\\sigma^2$" for *_x, A in TABLA_PERFILES
            ],
        }
    )
    completo = pd.DataFrame(
        {
            "A": esc["a"].astype(int).astype(str),
            "y* de la fórmula": [_pct(v, 0) for v in esc["y_sin_recorte"]],
            "y* aplicado": [_pct(v, 0) for v in esc["y"]],
            "Libre de riesgo": [_pct(v, 0) for v in esc["peso_rf"]],
            "E(Rc)": [_pct(v) for v in esc["retorno"]],
            "σc": [_pct(v) for v in esc["sigma"]],
            "Utilidad": [_pct(v, 2) for v in esc["utilidad"]],
        }
    )
    tabla_comp = comp.map(_pct)
    tabla_comp.insert(0, "Activo", comp.index)
    altos = esc[esc["y_sin_recorte"] > 1]
    tabla_tope = pd.DataFrame(
        {
            "A": altos["a"].astype(int).astype(str),
            "y* real": [_pct(v, 0) for v in altos["y_sin_recorte"]],
            "Préstamo por $100 propios": [f"\\${v * 100:.0f}" for v in altos["prestamo_sin_tope"]],
            "E(Rc) sin tope": [_pct(v) for v in altos["retorno_sin_tope"]],
            "σc sin tope": [_pct(v) for v in altos["sigma_sin_tope"]],
            "U sin tope": [_pct(v, 2) for v in altos["utilidad_sin_tope"]],
            "U con tope": [_pct(v, 2) for v in altos["utilidad"]],
            "Si P cae 20 %": [_pct(-0.2 * v, 0) for v in altos["y_sin_recorte"]],
        }
    )
    fila_a1 = sin_ap[sin_ap["a"] == 1]
    a1 = fila_a1.iloc[0] if not fila_a1.empty else None
    y_a1 = float(esc.loc[esc.a == 1, "y_sin_recorte"].iloc[0]) if (esc.a == 1).any() else 1.0
    u_p_a1 = float(esc.loc[esc.a == 1, "utilidad"].iloc[0]) if (esc.a == 1).any() else 0.0
    if a1 is not None and a1["donde"] == "frontera":
        texto_frontera = (
            f"Con este universo y el tope de {_pct(c.params.w_max, 0)} por activo, esa frontera apenas se extiende "
            f"más allá de P: para A = 1 el mejor punto factible es su extremo (retorno {_pct(a1['retorno'])}, "
            f"σ {_pct(a1['sigma'])}, U {_pct(a1['utilidad'], 2)} frente a {_pct(u_p_a1, 2)} en P); para los demás sigue siendo P."
        )
    else:
        texto_frontera = (
            "Con este universo, para estos perfiles el mejor punto factible sigue siendo P."
        )

    betas = pd.DataFrame(
        {
            "Acción (ETF)": c.betas.index,
            "β frente a ACWI": [_num(v) for v in c.betas.to_numpy()],
            "Peso en P": [_pct(w.get(x, 0.0)) for x in c.betas.index],
        }
    )
    durs = pd.DataFrame(
        {
            "Bono (ETF)": list(DURATIONS),
            "Duration (años)": [_num(v, 1) for v in DURATIONS.values()],
            "CAGR en la ventana": [_pct(est_u.loc[x, "cagr"]) for x in DURATIONS],
            "Peso en P": [_pct(w.get(x, 0.0)) for x in DURATIONS],
        }
    )
    texto_duration = (
        "El portafolio óptimo **no incluye bonos**, así que la duration de su parte de renta fija es "
        "nula: en esta ventana la renta fija tuvo retornos negativos o bajos (subida de tasas) y Markowitz "
        "la descarta. Para el inversionista conservador, el papel de reducir el riesgo lo cumple el activo "
        "libre de riesgo (T-note), no los ETF de bonos."
        if peso_bonos < 0.005
        else f"Duration ponderada de la parte de renta fija: {_num(c.duration_port['duration_rf_normalizada'], 1)} años."
    )

    texto_mult, resumen_mult = seccion_multiplos(c, fundamentales)
    eleg = sharpe_catalogo_elegible(c, leer_catalogo())
    ret_d = c.precios.sort_index().pct_change().dropna(how="any").tail(c.est.n_obs)
    corr_spy_qqq = (
        float(ret_d["SPY"].corr(ret_d["QQQ"])) if {"SPY", "QQQ"} <= set(ret_d) else float("nan")
    )
    sharpe_spy = float(eleg["sharpe_individual"].get("SPY", float("nan")))
    mejores = est_u.drop(index="Óptimo")["sharpe"].sort_values(ascending=False)
    negativos = [x for x in est_u.drop(index="Óptimo").index if est_u.loc[x, "retorno_medio"] < 0]
    bonos_txt = ", ".join(x for x in DURATIONS)
    a_altos = " y ".join(str(int(a)) for a in altos["a"])
    dur_ej = max(DURATIONS, key=DURATIONS.get)
    seccion_eda = (
        construir_eda(eda, figuras)
        if eda is not None
        else "Sin encuestas en la instantánea de datos."
    )

    return f"""---
title: "Taller 1 · Aversión al riesgo, función de utilidad y portafolio óptimo de Markowitz"
subtitle: "Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026"
author:
  - Sebastian Duarte Uran
  - Paulina Jaramillo
  - Juan David Londoño
  - Juan Luis Orrego Henao
  - Esteban Palacio Londoño
  - "Profesor: Juan Carlos Botero Ramírez"
date: "{_fecha(fecha)}"
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
---

# Resumen ejecutivo {{-}}

Este informe documenta el procedimiento y los resultados del Taller 1: (i) el coeficiente de aversión
al riesgo **A** de cada encuestado con el formato del enunciado, (ii) el **portafolio óptimo de activos
riesgosos** con el modelo de Markowitz y (iii) el **portafolio completo** (riesgo + activo libre de
riesgo) de cada perfil. Todo se calcula con un aplicativo web, un *proto robo-advisor* que cualquier
persona puede usar: <{URL_APP}>. El código Python está en <{URL_REPO}>; el Excel adjunto repite los
cálculos para revisarlos en detalle.

- **Encuestas:** {n_vol} personas respondieron el formato en la aplicación; cinco de ellas, una por rango de
  edad del enunciado (25-34 a 65-74), son los voluntarios del taller.
- **Portafolio de riesgo óptimo** (11 ETF, {c.est.n_obs} días entre {ini:%d-%m-%Y} y {fin:%d-%m-%Y}): retorno
  esperado **{_pct(t.retorno)}**, desviación estándar **{_pct(t.sigma)}**, ratio de Sharpe **{_num(t.sharpe)}**, con
  {", ".join(f"{x} {_pct(activos[x], 0)}" for x in activos.index)}.
- **Portafolio completo:** un conservador (A = 8) invierte **{_pct(y8, 0)}** en el portafolio de riesgo y el resto
  en el activo libre de riesgo; A = 6, **{_pct(y6, 0)}**; A = 4, **{_pct(float(esc.loc[esc.a == 4, "y"].iloc[0]), 0)}**. Para A = {a_altos} la fórmula pide
  **más de 100 %** ({", ".join(_pct(v, 0) for v in altos["y_sin_recorte"])}), es decir, endeudarse; como el aplicativo no apalanca, se
  limita a 100 %. La sección 3.7 explica el valor real y cómo se interpreta.
- **Múltiplos:** {resumen_mult}
- **EDA:** la mitad de los encuestados es *moderada*; la mayor aversión aparece en los mayores de 65 años
  y en los jubilados, no en función de ingresos o educación.

> **Aviso:** ejercicio académico. No constituye asesoría de inversión. Los retornos pasados no
> garantizan retornos futuros.

# Metodología general

**Flujo.** El procedimiento tiene dos partes que se conectan solo a través de A:

1. *Parte 1 (la persona):* formato de 9 respuestas → puntaje (9–27) → perfil → **A**.
2. *Parte 2 (el mercado):* precios diarios → retornos → retorno esperado $\\mu$ y matriz de covarianzas
   $\\Sigma$ → frontera eficiente → **portafolio de riesgo óptimo P** (tangente, máximo Sharpe) → **CAL**.
3. *Unión:* con el A de cada persona, $y^* = \\dfrac{{E(R_P) - r_f}}{{A\\,\\sigma_P^2}}$ define cuánto va a P y cuánto al
   activo libre de riesgo → **portafolio completo** y su composición por activo.

El portafolio de riesgo óptimo **no depende de A**: es el mismo para todos (teorema de separación de
Tobin). A solo decide la mezcla entre P y el activo libre de riesgo.

**Herramientas y en qué aportó cada una.**

- **Python** hace todos los cálculos: estadística, optimización de Markowitz, gráficos, este informe y el
  Excel. Las mismas funciones sirven a la aplicación y al informe, así los números coinciden.
- **Una base de datos en la nube** guarda los precios, el catálogo de activos y, de forma segura, las
  encuestas y portafolios de cada usuario.
- **Una aplicación web** es la cara del robo-advisor: registro, encuesta, construcción y seguimiento del
  portafolio, desde el computador o el celular.
- **Un proceso automático** descarga los precios de mercado cada día hábil, sin intervención manual.
- **Inteligencia artificial**, como pide el enunciado, se usó para **construir** el aplicativo (un asistente de
  programación). Dentro de la aplicación, en cambio, los cálculos y las recomendaciones salen de fórmulas y
  reglas fijas, para que sean reproducibles y auditables.

**Supuestos principales.**

| Supuesto | Valor | Por qué |
|---|---|---|
| Moneda base | USD | Todos los ETF cotizan en USD; los activos en COP se convierten |
| Frecuencia y ventana | Retornos diarios, últimos {c.params.ventana_dias} días (≈ 5 años) | Suficientes datos para estimar $\\Sigma$ de 11 activos |
| Retorno esperado | Media histórica × 252 | Es el "retorno promedio histórico" del enunciado |
| Riesgo | Covarianza muestral × 252 | Como en clase |
| Tasa libre de riesgo | T-note de EE.UU. a 10 años: **{_pct(c.rf, 2)}** ({fin:%d-%m-%Y}) | Activo libre de riesgo en USD |
| Restricciones | Solo largos; máximo {_pct(c.params.w_max, 0)} por activo | Evita concentrar todo en uno o dos activos |
| Apalancamiento | No: $0 \\le y^* \\le 1$ | Un robo-advisor minorista no presta dinero |

Todos los números salen del mismo código Python que usa la aplicación (paquete
`roboadvisor.taller1.core`), aplicado a una **instantánea** de los datos guardada en el repositorio para que
el resultado se pueda repetir.

# Parte 1 · Aversión al riesgo y función de utilidad

## La función de utilidad

$$U = E(r) - \\tfrac{{1}}{{2}}\\,A\\,\\sigma^2$$

La utilidad sube con el retorno esperado $E(r)$ y baja con la varianza $\\sigma^2$; **A** mide cuánto
castiga el inversionista el riesgo. Ejemplo con el portafolio de riesgo óptimo de este informe
($E(r)$ = {_pct(t.retorno)}, $\\sigma$ = {_pct(t.sigma)}): para A = 1 la utilidad es {_pct(t.retorno - 0.5 * t.sigma**2, 2)}; para A = 8 es
{_pct(t.retorno - 4 * t.sigma**2, 2)}, por debajo de la tasa libre de riesgo ({_pct(c.rf, 2)}). Por eso el conservador
prefiere mezclar P con el activo libre de riesgo, y el agresivo no.

$U$ puede leerse como un **equivalente cierto**: el retorno seguro que el inversionista consideraría
igual de bueno que la inversión riesgosa. Las preguntas 5, 6 y 7 del formato son pequeñas *loterías*
que revelan esa preferencia.

## El instrumento: formato de medición de aversión al riesgo

Se usó el formato del enunciado sin cambios: 7 preguntas, la segunda con tres horizontes (5, 15 y 30
años), 9 respuestas en total (Anexo A). Cada respuesta *a* vale 1 punto, *b* 2 y *c* 3:

$$\\text{{Puntaje}} = 1\\cdot\\#a + 2\\cdot\\#b + 3\\cdot\\#c \\in [9,\\ 27]$$

{_md(perfiles)}

## Recolección de la información

Cada persona se registró en la aplicación con correo, un alias y su rango de edad, y aceptó el uso
académico de sus datos. Luego respondió el formato (sin ver su puntaje hasta enviarlo y sin poder
cambiarlo después) y, de forma opcional, siete factores personales: ocupación, ingresos, dependientes
económicos, nivel educativo, experiencia invirtiendo, horizonte de inversión y si tiene un colchón de
emergencia. No se pidieron nombre, cédula ni teléfono. Para este informe los datos se exportan
**anonimizados** (alias V1…V{n_vol}).

## Los cinco voluntarios

{seccion_voluntarios(c, voluntarios)}

# Parte 2 · Portafolio óptimo con Markowitz

## Universo de activos

El aplicativo ofrece un **catálogo de 34 activos** que cubre todas las clases del enunciado: acciones
de EE.UU. (SPY, QQQ, IWM y sectoriales), EAFE (EFA), emergentes (EEM, EWZ, FXI, KWEB), Colombia y Latam
(COLO, ILF), **TES de Colombia** (GXTESCOL, ETF de TES en COP convertido a USD), renta fija IG (LQD, AGG,
IEF, TLT, TIP), HY (HYG), global y emergente (BNDX, EMB), REIT (VNQ, VNQI), materias primas (GLD, URA) y
**criptoactivos** (IBIT, ETF de bitcoin). El usuario escoge entre 3 y 11 de ellos.

Para el análisis se usa un **portafolio de referencia de 11 ETF** (el número del enunciado), el mismo
para todos los perfiles:

{_md(universo)}

**Por qué estos 11.** Se escogieron con tres criterios:

1. *Cubrir las clases del enunciado:* acciones de EE.UU., Colombia, Latinoamérica, EAFE y emergentes; renta fija
   de grado de inversión, alto rendimiento y emergente; REIT y oro.
2. *Ser comparables:* sin apalancamiento y con al menos 5 años de historia diaria, para que la ventana común
   no se recorte.
3. *Maximizar el ratio de Sharpe del portafolio de riesgo.* Se calculó el portafolio óptimo con **los {eleg["n"]}
   activos del catálogo** que cumplen el criterio 2: su Sharpe máximo es **{_num(eleg["sharpe"])}**, el mismo que se
   obtiene con estos 11. Ningún otro activo elegible lo mejora.

Por eso se **retiró SPY** (S&P 500): su correlación con QQQ es {_num(corr_spy_qqq)} y no aporta Sharpe; y se incluyeron **SMH**
(semiconductores, el ETF de mayor Sharpe individual del catálogo) y **COLO** (acciones colombianas, que pide el
enunciado). Los ETF de TES (GXTESCOL, datos desde 2025-05) y de bitcoin (IBIT, desde 2024-01) son jóvenes:
incluirlos reduciría la estimación de **todos** los activos a uno o dos años y, en una ventana tan corta, el
Sharpe saldría artificialmente alto (se probó: 1,2 a 1,5). Siguen disponibles en la aplicación, que avisa al
usuario cuando acortan la ventana. Los ETF apalancados (2x, 3x) se excluyen.

**¿Es bajo un Sharpe de {_num(t.sharpe)}?** No para este periodo. La tasa libre de riesgo es alta ({_pct(c.rf, 2)}) y la ventana
incluye 2022, cuando acciones y bonos cayeron a la vez. En la misma ventana el S&P 500 (SPY) tuvo un Sharpe de
{_num(sharpe_spy)}. Con datos de 5 años, un Sharpe mayor que 1 solo aparece cuando se usan ventanas cortas o activos
escogidos *a posteriori*, y eso es sobreajuste.

## Datos

- **Precios:** cierre diario ajustado por dividendos y *splits* (Yahoo Finance), en USD. El ETF de TES en
  pesos se convierte con la tasa USD/COP del mismo día.
- **Ventana:** {c.est.n_obs} retornos diarios comunes a los 11 ETF, del {ini:%d-%m-%Y} al {fin:%d-%m-%Y}.
- **Tasa libre de riesgo:** rendimiento del T-note a 10 años (^TNX) del último día: {_pct(c.rf, 2)} anual.
- **Benchmark para las betas:** ACWI (MSCI All Country World).

## Estimación: retorno promedio histórico, riesgo y correlaciones

Retorno diario $r_t = P_t / P_{{t-1}} - 1$. Para cada activo:

$$\\mu_i = 252\\,\\bar r_i \\qquad \\Sigma_{{ij}} = 252\\,\\widehat{{\\mathrm{{Cov}}}}(r_i, r_j) \\qquad \\text{{Sharpe}}_i = \\frac{{\\mu_i - r_f}}{{\\sigma_i}}$$

La tabla agrega el **CAGR** (crecimiento anual compuesto realmente obtenido) y la **caída máxima** (peor
pérdida desde un máximo) como indicadores complementarios. La última fila es el portafolio óptimo P.

{_md(tabla_est)}

![Valor de 100 USD invertidos al inicio de la ventana en cada ETF y en P (los pesos de P se escogieron con estos mismos datos: es un resultado *dentro de muestra*)]({figuras["desempeno"].name}){{width=90%}}

![Correlaciones de los retornos diarios de los 11 ETF]({figuras["correlaciones"].name}){{width=70%}}

**Lectura.** Los mejores retornos ajustados por riesgo fueron los de {", ".join(f"{x} ({_num(v)})" for x, v in mejores.head(3).items())}.
{(", ".join(negativos) + " tuvieron retorno medio **negativo**") if negativos else "Ningún activo tuvo retorno negativo"}: la ventana incluye la mayor subida de tasas de
la Reserva Federal en 40 años, que golpeó a la renta fija ({bonos_txt}). El oro tiene baja correlación con las
acciones (verde claro en el mapa): aporta diversificación además de retorno. Las acciones de EE.UU. entre sí
(QQQ y SMH) están muy correlacionadas.

## El problema de optimización

**Portafolio de riesgo óptimo (tangente).** Maximiza el ratio de Sharpe:

$$\\max_{{w}} \\; \\frac{{w^\\top\\mu - r_f}}{{\\sqrt{{w^\\top\\Sigma\\, w}}}} \\quad \\text{{s.a.}} \\quad \\sum_i w_i = 1,\\quad 0 \\le w_i \\le {_num(c.params.w_max, 2)}$$

**Frontera eficiente.** Para una malla de retornos objetivo $R^*$ entre el de mínima varianza y el máximo
alcanzable: $\\min_w w^\\top\\Sigma w$ s.a. $w^\\top\\mu = R^*$ y las mismas restricciones. Se resuelve con SLSQP
(scipy), con varios puntos de partida y verificando la convergencia.

**CAL óptima.** Recta desde el activo libre de riesgo que toca la frontera en P:
$E(R_C) = r_f + \\text{{Sharpe}}_P\\,\\sigma_C$, con pendiente {_num(c.cal_pendiente, 3)}.

## Resultado: frontera eficiente, CAL y portafolio óptimo

![Frontera eficiente, CAL óptima, portafolio de riesgo óptimo (P) y de mínima varianza]({figuras["frontera"].name}){{width=90%}}

**Composición del portafolio de riesgo óptimo P:**

{_md(optimo)}

![Pesos del portafolio de riesgo óptimo en los 11 activos]({figuras["pesos"].name}){{width=70%}}

**Indicadores de P:** retorno promedio histórico (esperado) **{_pct(t.retorno)}**, desviación estándar
**{_pct(t.sigma)}** y ratio de Sharpe **{_num(t.sharpe)}** = ({_pct(t.retorno)} − {_pct(c.rf, 2)}) / {_pct(t.sigma)}. Es mayor que el de cualquier ETF
por separado (el mejor, GLD, tiene {_num(est_u.loc["GLD", "sharpe"])}): ese es el beneficio de diversificar. El portafolio de
mínima varianza tiene σ = {_pct(c.min_var.sigma)} y retorno {_pct(c.min_var.retorno)}.
{(" y ".join(tope) + f" llegan al tope de {_pct(c.params.w_max, 0)}: sin esa restricción el optimizador concentraría aún más en ellos, lo que reflejaría el desempeño reciente más que una expectativa razonable.") if tope else ""}
Los otros {11 - len(activos)} ETF quedan en 0 % porque en esta ventana no mejoran el Sharpe: su retorno es bajo para el
riesgo que agregan. Es la conocida sensibilidad de Markowitz a los retornos esperados históricos, y el costo
es un portafolio **concentrado** en {len(activos)} activos, con caída máxima de {_pct(est_u.loc["Óptimo", "caida_maxima"], 0)} en la ventana.

## Portafolio completo según el perfil

Para cada A, la fracción $y$ en el portafolio de riesgo maximiza
$U(y) = r_f + y\\,(E(R_P) - r_f) - \\tfrac{{1}}{{2}}A\\,y^2\\sigma_P^2$. Derivando e igualando a cero:

$$y^* = \\frac{{E(R_P) - r_f}}{{A\\,\\sigma_P^2}} = \\frac{{{_num(t.retorno, 4)} - {_num(c.rf, 4)}}}{{A \\times {_num(t.sigma, 4)}^2}} = \\frac{{{_num((t.retorno - c.rf) / t.sigma**2, 3)}}}{{A}}$$

El portafolio completo tiene $E(R_C) = r_f + y^*(E(R_P) - r_f)$ y $\\sigma_C = y^*\\sigma_P$:

{_md(completo)}

**Composición del portafolio completo** (lo que ve cada usuario en la aplicación): peso de cada activo
= $y^* \\times$ su peso en P; el resto va al activo libre de riesgo.

{_md(tabla_comp)}

![Composición del portafolio completo de cada perfil]({figuras["composicion"].name}){{width=85%}}

![Izquierda: curvas de indiferencia de cada perfil tangentes a la CAL. Derecha (zoom out): la CAL prolongada; los círculos vacíos muestran dónde quedaría cada perfil con su y* real y las flechas cómo el tope lo lleva a P]({figuras["indiferencia"].name}){{width=88%}}

## Perfiles con A baja: el tope de 100 % y el valor real de y*

Para A = {a_altos} la fórmula da $y^* > 1$. **Interpretación:** dado lo atractivo de P (Sharpe
{_num(t.sharpe)}), esas personas querrían invertir **más que todo su dinero** en él y pedir prestada la diferencia
a la tasa libre de riesgo (quedarían con $1 - y^* < 0$ en el activo libre de riesgo, es decir, con una
deuda). Con A = 1 el valor real es $y^*$ = **{_pct(y_a1, 0)}**: por cada 100 USD propios pediría prestados
{(y_a1 - 1) * 100:.0f} USD para invertir {y_a1 * 100:.0f} USD en P.

{_md(tabla_tope)}

**Por qué se limita a 100 %.**

1. *La fórmula supone que se puede pedir prestado a la tasa libre de riesgo.* Ningún banco presta a una
   persona a la tasa del Tesoro de EE.UU.; con una tasa de préstamo mayor la CAL se "quiebra" en P y
   apalancarse deja de ser tan atractivo.
2. *El riesgo se multiplica:* con apalancamiento una caída de 20 % en P se convierte en una pérdida de
   {", ".join(_pct(0.2 * v, 0) for v in altos["y_sin_recorte"])} del patrimonio (última columna), más posibles llamados al margen.
3. *Producto responsable:* el robo-advisor no ofrece crédito, así que $0 \\le y^* \\le 1$ es una restricción del
   modelo. Además, el {_pct(float((voluntarios["q6"] == "a").mean()), 0) if voluntarios is not None else "—"} de los encuestados dijo que *definitivamente no* tomaría un préstamo para invertir.

**Qué significa para la persona.** Con el tope, su mejor opción factible es $y = 1$ (100 % en P): una
solución de esquina. La pérdida de utilidad frente al valor sin tope crece a medida que A baja (ver las
columnas U de la tabla); es mayor para A = 1. Si no se puede pedir prestado, la teoría (Bodie, Kane y Marcus) indica que quien
quiere más riesgo debería moverse **por la frontera eficiente a la derecha de P**, hacia un portafolio de
riesgo más agresivo, en lugar de apalancarse. {texto_frontera} La aplicación muestra al usuario el
$y^*$ real y le avisa que fue limitado a 100 %.

## Beta de las acciones y duration de los bonos

**Beta** de cada ETF accionario frente al índice mundial ACWI, con la misma ventana:
$\\beta_i = \\mathrm{{Cov}}(r_i, r_{{ACWI}}) / \\mathrm{{Var}}(r_{{ACWI}})$.

{_md(betas)}

Beta ponderada de la parte accionaria de P: **{_num(c.beta_port["beta_normalizada"])}**: amplifica los movimientos del mercado
mundial. {c.betas.idxmax()} (β {_num(c.betas.max())}) es el componente más sensible al mercado y {c.betas.idxmin()} (β {_num(c.betas.min())}) el menos.

**Duration** (modificada, en años) de los ETF de renta fija, según el emisor (iShares), y su resultado en
la ventana:

{_md(durs)}

{texto_duration} Interpretación: con duration {_num(DURATIONS[dur_ej], 1)} ({dur_ej}), una subida de 1 punto porcentual en las
tasas reduce su precio ≈ {_num(DURATIONS[dur_ej], 1)} %.

## Análisis de múltiplos

{texto_mult}

# El aplicativo (proto robo-advisor)

Disponible en <{URL_APP}>. Flujo del usuario:

1. **Registro:** correo, alias, rango de edad y consentimiento.
2. **Encuesta:** las 9 preguntas del formato en tarjetas; al enviar se calculan el puntaje, el perfil (uno de
   los 5: conservador, conservador a moderado, moderado, moderado a agresivo y agresivo) y A.
3. **Constructor:** el usuario escoge entre 3 y 11 activos del catálogo (o carga el portafolio de
   referencia de 11 ETF), fija el peso máximo por activo y pulsa *Optimizar*. Ve la frontera eficiente, la
   CAL, su curva de indiferencia, el portafolio de riesgo óptimo, su $y^*$ (y si fue limitado a 100 %), la
   **composición de su portafolio completo**, la beta y la duration. Lo registra una sola vez.
4. **Mi portafolio:** en cada ingreso muestra cómo ha rendido con los precios nuevos, la composición al
   armarlo frente a hoy y recomendaciones con reglas fijas (rebalancear si un peso se desvía más de 5
   puntos, aviso si la volatilidad sube 25 %, señales de múltiplos).

**Arquitectura.** Streamlit (interfaz) → paquete Python `core` (cálculos puros, cubiertos por más de 170
pruebas automáticas) → Supabase (usuarios, encuestas, portafolios y precios). Cada usuario solo ve sus
datos (políticas de seguridad por fila). Los precios se actualizan solos cada día hábil.

**Los portafolios de los encuestados.** De las {n_vol} personas con encuesta, {int((origen == "propio").sum())} armaron su propio
portafolio en la aplicación; a las otras {int((origen == "asignado").sum())} el grupo les **asignó** el portafolio de riesgo de
referencia de este informe, con el $y^*$ de su propio A, para que todas puedan ver la composición de su
portafolio completo y su seguimiento. Esa diferencia queda marcada en los datos.

# Análisis exploratorio de las encuestas (EDA)

{seccion_eda}

# Conclusiones

1. El formato del enunciado clasifica a la mitad de los encuestados como **moderados** (A = 4) y los
   extremos son poco frecuentes. Los mayores de 65 años son los más aversos al riesgo; entre 18 y 64 años
   el puntaje no cambia de forma sistemática.
2. El portafolio de riesgo óptimo ({", ".join(f"{x} {_pct(activos[x], 0)}" for x in activos.index)}) tiene Sharpe {_num(t.sharpe)}, el máximo
   alcanzable con los {eleg["n"]} activos elegibles del catálogo. Es el mismo para todos; el perfil solo cambia la mezcla
   con el activo libre de riesgo: de {_pct(y8, 0)} en riesgo (conservador) a 100 % (los más agresivos).
3. Para A = {a_altos} la fórmula pide apalancarse ({", ".join(_pct(v, 0) for v in altos["y_sin_recorte"])}); el tope de 100 % es una decisión
   prudente, coherente con lo que declaran los encuestados.
4. Los múltiplos sugieren un ajuste táctico: {resumen_mult}

# Limitaciones

- Retornos esperados **históricos** (5 años): son inestables y empujan a concentrar en lo que más subió
  (el oro y los semiconductores en esta ventana). Un modelo de equilibrio (CAPM, Black-Litterman) o una ventana
  más larga darían pesos más diversificados.
- Sin apalancamiento, solo posiciones largas y tope de {_pct(c.params.w_max, 0)} por activo; moneda base USD.
- La muestra de encuestas es de conveniencia ({n_vol} personas cercanas al grupo, muchas jóvenes): sirve para
  explorar, no para generalizar a la población.
- Las durations son las publicadas por el emisor; los P/E de los ETF son agregados de Yahoo Finance.

# Anexo A · Formato de medición de aversión al riesgo {{-}}

{anexo_cuestionario()}

# Anexo B · Respuestas de todos los encuestados (anonimizadas) {{-}}

{anexo_respuestas(eda) if eda is not None else "—"}

# Anexo C · Cómo reproducir {{-}}

Los datos se exportan de Supabase en modo solo lectura (los datos personales no se versionan) y luego se
regeneran este PDF, sus figuras y el Excel:

```
python scripts/taller1/exportar_instantanea.py
python scripts/taller1/exportar_voluntarios.py
python -m roboadvisor.taller1.reportes
```


Código: <{URL_REPO}>. Cálculos en `taller1/core/`; este informe, el EDA y el Excel en
`taller1/reportes/` (dentro de `src/roboadvisor/`).
"""


def seccion_multiplos(c: CasoReferencia, fundamentales: pd.DataFrame | None) -> tuple[str, str]:
    """Texto de la sección de múltiplos y una frase de resumen."""
    if (
        fundamentales is None
        or fundamentales.empty
        or BENCHMARK not in set(fundamentales["ticker"])
    ):
        return (
            "No hay fotos de múltiplos en la instantánea de datos; ver la página *Mi portafolio* de la aplicación.",
            "sin datos de múltiplos.",
        )
    m = multiplos_referencia(c, fundamentales)
    mt = m["tabla"]
    tabla = pd.DataFrame(
        {
            "ETF": mt["ticker"],
            "P/E": [_num(v, 1) if pd.notna(v) else "—" for v in mt["pe"]],
            "1/PE": [_pct(v) if pd.notna(v) else "—" for v in mt["rendimiento_utilidades"]],
            "P/E relativo": [_num(v) if pd.notna(v) else "—" for v in mt["pe_relativo"]],
            "Div. yield": [_pct(v) if pd.notna(v) else "—" for v in mt["dividend_yield"]],
            "Señal": mt["senal"],
            "Peso neutral": [_pct(v) for v in mt["peso_neutral"]],
            "Peso sugerido": [_pct(v) for v in mt["peso_ajustado"]],
        }
    )
    aj = m["ajustado"]
    otros = [x for x in aj.index if x not in mt["ticker"].tolist() and aj[x] > 0.0005]
    caras = mt.loc[mt.senal == "cara", "ticker"].tolist()
    baratas = mt.loc[mt.senal == "barata", "ticker"].tolist()
    sin_dato = mt.loc[mt.senal == "sin_dato", "ticker"].tolist()
    ey_caras = [float(v) for v in mt.loc[mt.senal == "cara", "rendimiento_utilidades"]]
    bajo_rf = [x for x, v in zip(caras, ey_caras, strict=True) if v < c.rf]

    def _lista(xs: list[str]) -> str:
        return (
            " y ".join([", ".join(xs[:-1]), xs[-1]])
            if len(xs) > 1
            else (xs[0] if xs else "ninguno")
        )

    resumen = (
        f"{_lista(caras)} cotizan caros frente al mundo (P/E relativo > {_num(c.params.pe_relativo_cara)}) y {_lista(baratas)} baratos "
        f"(< {_num(c.params.pe_relativo_barata)}): se sugiere subponderar los primeros y sobreponderar los segundos."
    )
    texto = f"""
**Fuente y fecha.** P/E (precio / utilidad de los últimos 12 meses) y dividend yield de cada ETF según
Yahoo Finance (la misma información que publica investing.com), foto semanal del **{_fecha(m["fecha"])}**.
Referencia: el índice mundial **ACWI**, con P/E = **{_num(m["pe_acwi"], 1)}**.

**Regla.** P/E relativo = P/E del ETF / P/E de ACWI. Si es **menor que {_num(c.params.pe_relativo_barata)}**, el índice está *barato*
frente al mundo y se sugiere **sobreponderar** {_num(c.params.tilt_multiplos * 100, 1)} puntos; si es **mayor que {_num(c.params.pe_relativo_cara)}**, está *caro*
y se sugiere **subponderar** lo mismo. Luego se renormaliza para que el portafolio de riesgo siga sumando
100 %. No se recalcula Markowitz: es un ajuste táctico sobre el portafolio neutral.

{_md(tabla)}

El resto del portafolio sugerido queda en {", ".join(f"{x} {_pct(aj[x])}" for x in otros)}.

**Lectura.** {_lista(caras)} (tecnología y semiconductores de EE.UU.) cotizan con prima frente al mundo{": su rendimiento de utilidades (1/PE) es incluso menor que la tasa libre de riesgo (" + _pct(c.rf, 2) + "), lo que sugiere poca compensación por el riesgo accionario" if bajo_rf else ""}.
{_lista(baratas)} cotizan con descuento: el análisis de múltiplos recomienda **reducir la posición en {_lista([x for x in caras if mt.loc[mt.ticker == x, "peso_neutral"].iloc[0] > 0])}** y abrir
posiciones pequeñas en {_lista(baratas)}, al contrario de lo que dicta el pasado reciente (Markowitz las descarta
por su menor retorno histórico).{(" Yahoo Finance no publica P/E para " + _lista(sin_dato) + ", así que su peso no se ajusta.") if sin_dato else ""}

**Cuidado.** Un P/E menor no siempre significa "barato": también refleja la mezcla de sectores (tecnología
en QQQ y SMH; bancos y materias primas en ILF), el crecimiento esperado y el riesgo país. Por eso la
aplicación, además, compara cada activo **con su propio P/E histórico** (z-score robusto frente a la mediana);
esa señal necesita al menos {c.params.min_obs_pe} fotos semanales y hoy hay {m["fotos"]}, así que este informe usa la
comparación frente al índice mundial.
"""
    return texto, resumen


def anexo_cuestionario() -> str:
    partes = []
    for p in PREGUNTAS:
        numero = eda_mod.ETIQUETA_PREGUNTA[p.id].split(".")[0]
        ops = "\n".join(f"- **{k})** {v}" for k, v in p.opciones.items())
        partes.append(f"**{numero}.** {p.texto}\n\n{ops}")
    return "\n\n".join(partes)


def anexo_respuestas(r: "eda_mod.ResultadosEDA") -> str:
    d = r.datos
    t = d[["alias", "rango_edad", *IDS_PREGUNTAS, "puntaje", "a", "origen_portafolio"]].copy()
    t["rango_edad"] = t["rango_edad"].astype(str)
    t.columns = [
        "Alias",
        "Edad",
        "1",
        "2A",
        "2B",
        "2C",
        "3",
        "4",
        "5",
        "6",
        "7",
        "Puntaje",
        "A",
        "Portafolio",
    ]
    return _md(t.astype(str))


# ------------------------------------------------------------------ EDA


def construir_eda(r: "eda_mod.ResultadosEDA", figuras: dict[str, Path]) -> str:
    d = r.datos
    p = r.puntaje
    n = p["n"]
    it = r.items.set_index(r.items["Pregunta"].str.split(".").str[0])

    perf = r.perfiles.copy()
    perf["%"] = [_pct(v, 0) for v in perf["%"]]
    perf = perf.astype(str)

    ep = r.edad_perfil.copy()
    ep["Puntaje medio"] = [_num(v, 1) if pd.notna(v) else "—" for v in ep["Puntaje medio"]]
    ep = ep.reset_index(names="Edad").astype(str)

    items = r.items.copy()
    for k in ("a", "b", "c"):
        items[k] = [_pct(v, 0) for v in items[k]]
    items["Media (1–3)"] = [_num(v) for v in items["Media (1–3)"]]

    ir = r.item_resto.copy()
    ir["Correlación ítem-resto"] = [_num(v) for v in ir["Correlación ítem-resto"]]
    ir["α sin el ítem"] = [_num(v) for v in ir["α sin el ítem"]]

    asoc = r.asociaciones.copy()
    for k, dec in (("Estadístico", 2), ("p", 3), ("p ajustado (BH)", 3)):
        asoc[k] = [_num(v, dec) for v in asoc[k]]
    asoc = asoc.astype(str)

    lot = r.loteria.copy()
    lot["Valor esperado (M COP)"] = [_num(v, 1) for v in lot["Valor esperado (M COP)"]]
    lot["Desv. estándar (M COP)"] = [_num(v, 1) for v in lot["Desv. estándar (M COP)"]]
    lot["%"] = [_pct(v, 0) for v in lot["%"]]
    lot = lot.astype(str)

    def demog(f: str) -> str:
        v = d[f].astype(str).replace("", "sin dato")
        orden = eda_mod.ORDINALES.get(f)
        cuenta = v.value_counts()
        if orden:
            cuenta = cuenta.reindex([*orden, "sin dato"]).dropna()
        return "; ".join(f"{k} ({int(x)})" for k, x in cuenta.items())

    asoc_i = r.asociaciones.set_index("Factor")
    occ = eda_mod.resumen_por_factor(d, "ocupacion")
    exp = eda_mod.resumen_por_factor(d, "experiencia_invirtiendo_anios")
    hz = r.horizonte
    pf = r.portafolios
    propios = pf[pf["origen_portafolio"] == "propio"]
    elegidos = propios["activos_elegidos"].str.split(", ").explode().value_counts()
    con_apal = int(
        propios["activos_elegidos"].apply(lambda s: bool(set(s.split(", ")) & APALANCADOS)).sum()
    )
    q5 = r.item_resto[r.item_resto["Pregunta"].str.startswith("5.")].iloc[0]
    mayores = d[d["rango_edad"].astype(str).isin(["65-74", "75+"])]
    resto = d[~d["rango_edad"].astype(str).isin(["65-74", "75+"])]
    n_a = d["a"].value_counts()
    fechas = pd.to_datetime(d["fecha_encuesta"]) if "fecha_encuesta" in d else None
    periodo = (
        f"entre el {fechas.min():%d-%m-%Y} y el {fechas.max():%d-%m-%Y}"
        if fechas is not None
        else ""
    )
    media_occ = {k: _num(float(occ.loc[k, "Media"]), 1) for k in occ.index}
    ninguno_sig = bool((r.asociaciones["p ajustado (BH)"] >= 0.05).all())
    a_tope = sorted((a for a, v in r.y_sin_tope.items() if v > 1), reverse=True)
    a_casi = sorted((a for a, v in r.y_sin_tope.items() if 0.9 <= v <= 1), reverse=True)

    return f"""
## Objetivo y preguntas guía

El enunciado pide recoger información personal "con el propósito de entender cuáles son los factores que
pueden moldear un cierto nivel de aversión al riesgo". Con las **{n} encuestas** recogidas (más que los cinco
voluntarios exigidos) se exploran cuatro preguntas:

1. ¿Cómo se distribuyen el puntaje, el perfil y A en la muestra?
2. ¿Cómo se responde cada pregunta? ¿El formato mide de forma consistente un solo rasgo?
3. ¿Qué factores personales (edad, ocupación, ingresos, experiencia, horizonte…) se asocian con el puntaje?
4. ¿Qué implica esa distribución para el portafolio completo ($y^*$)?

**Metodología.** (i) Revisión de la calidad de los datos; (ii) estadística descriptiva univariada; (iii)
confiabilidad del formato con el **alfa de Cronbach** y la correlación ítem-resto; (iv) análisis bivariado
con pruebas **no paramétricas**, porque el puntaje es una escala discreta y los grupos son pequeños:
correlación de **Spearman** para factores ordinales, **Kruskal-Wallis** para nominales y **Mann-Whitney**
para binarios. Como se hacen ocho pruebas a la vez, los valores p se ajustan por **Benjamini-Hochberg**
(tasa de falsos descubrimientos). Nivel de significancia: 5 %. Con n = {n} todo hallazgo es exploratorio.

## Datos y calidad

- Fuente: base de datos de la aplicación; encuestas respondidas {periodo}. Se excluyen las cuentas de
  prueba del grupo.
- Las 9 respuestas son obligatorias: no hay faltantes. Los factores personales eran opcionales:

{_md(r.calidad.astype(str))}

Los faltantes (como máximo 3 por factor) solo se excluyen de la prueba de ese factor.

## Perfil de la muestra

- **Edad:** {demog("rango_edad")}.
- **Ocupación:** {demog("ocupacion")}.
- **Ingresos mensuales (COP):** {demog("rango_ingresos")}.
- **Nivel educativo:** {demog("nivel_educativo")}.
- **Experiencia invirtiendo:** {demog("experiencia_invirtiendo_anios")}.
- **Colchón de emergencia:** {demog("colchon_emergencia")}.

Es una muestra joven (el {_pct(d["rango_edad"].astype(str).isin(["18-24", "25-34"]).mean(), 0)} tiene menos de 35 años), en su mayoría empleada, con educación
superior y poca experiencia invirtiendo. Incluye rangos fuera del enunciado (18-24 y 75+), útiles para el
análisis.

## Distribución del puntaje y de los perfiles

![Distribución del puntaje (franjas: perfil del formato; línea: media)]({figuras["eda_puntaje"].name}){{width=88%}}

Puntaje medio **{_num(p["media"], 1)}** (mediana {_num(p["mediana"], 0)}, desviación estándar {_num(p["desv"], 1)}, rango {p["min"]}–{p["max"]},
rango intercuartílico {_num(p["q1"], 0)}–{_num(p["q3"], 0)}). La distribución es aproximadamente simétrica (asimetría
{_num(p["asimetria"])}; Shapiro-Wilk p = {_num(p["shapiro_p"], 2)}, no se rechaza la normalidad) y se concentra en el centro de la escala:

{_md(perf)}

![Perfil de riesgo por rango de edad]({figuras["eda_edad_perfil"].name}){{width=88%}}

{_md(ep)}

**Lectura.** La mitad de la muestra es *moderada*. Solo hay {int(n_a.get(8, 0))} conservadores (A = 8) y son precisamente las
personas de 65-74 años; el único encuestado de 75+ es *conservador a moderado*. El perfil *agresivo* (A = 1)
aparece {int(n_a.get(1, 0))} vez.

## Respuestas por pregunta

![Distribución de las respuestas a, b y c en cada pregunta]({figuras["eda_items"].name}){{width=92%}}

{_md(items)}

Hallazgos:

- **Ante caídas, la mayoría no vende** (pregunta 1: solo el {_pct(float(it.loc["1", "a"]), 0)} vendería). Pero ante una **subida**
  (pregunta 3) el {_pct(float(it.loc["3", "a"]), 0)} retiraría la ganancia: aversión a "devolver" lo ganado, coherente con el efecto
  disposición de las finanzas conductuales.
- **El préstamo es la pregunta más conservadora** (pregunta 6: el {_pct(float(it.loc["6", "a"]), 0)} *definitivamente no* se endeudaría
  para invertir). Este dato respalda el tope $y^* \\le 1$ del aplicativo.
- **Horizonte (pregunta 2).** En teoría, a más años hasta el objetivo, menos razones para vender. Pero la
  venta **sube** de {_pct(float(it.loc["2A", "a"]), 0)} (5 años) a {_pct(float(it.loc["2C", "a"]), 0)} (30 años). Solo {hz["monotonas"]} de {hz["n"]} personas responden de forma
  coherente (no bajan su respuesta al alargar el horizonte) y {hz["iguales"]} responden igual en los tres. Posibles
  causas: el horizonte de 30 años supera la expectativa de vida o de inversión de algunos encuestados, o la
  pregunta se leyó como "qué tan lejos está mi meta" y no como "cuánto tiempo tengo para recuperarme".

## Confiabilidad del formato

Si las 9 respuestas miden el mismo rasgo (la tolerancia al riesgo), deberían estar correlacionadas entre
sí. El **alfa de Cronbach** del formato es **{_num(r.alfa, 2)}**, aceptable (≥ 0,70):

$$\\alpha = \\frac{{k}}{{k-1}}\\left(1 - \\frac{{\\sum_i \\sigma^2_i}}{{\\sigma^2_{{total}}}}\\right),\\quad k = 9$$

{_md(ir)}

La **pregunta 5 (la lotería)** casi no se relaciona con el resto (correlación ítem-resto {_num(float(q5["Correlación ítem-resto"]), 2)}); sin
ella, alfa subiría a {_num(float(q5["α sin el ítem"]), 2)}. Sus opciones tienen valores esperados que crecen con el riesgo:

{_md(lot)}

Una persona neutral al riesgo escogería *c* (mayor valor esperado); escoger *a* revela que se sacrifica al
menos \\$1 M de valor esperado a cambio de certeza. Que esta pregunta no se alinee con las demás sugiere que
las personas razonan distinto ante un premio (una ganancia sin costo) que ante decisiones sobre su propio
ahorro, como predice la teoría prospectiva (Kahneman y Tversky).

## Factores asociados a la aversión al riesgo

![Puntaje según edad, ingresos, experiencia y horizonte (puntos: personas; rombo: media)]({figuras["eda_factores"].name}){{width=92%}}

{_md(asoc)}

*Estadístico:* ρ de Spearman (ordinales), H de Kruskal-Wallis (ocupación) y correlación biserial de rangos
(colchón de emergencia).

Hallazgos:

- **Ocupación** es el factor con la diferencia más clara (p = {_num(float(asoc_i.loc["Ocupación", "p"]), 3)}; ajustado
  {_num(float(asoc_i.loc["Ocupación", "p ajustado (BH)"]), 3)}, al límite): los **jubilados** tienen un puntaje medio de {media_occ.get("Jubilado/a", "—")} frente a
  {media_occ.get("Empleado/a", "—")} de los empleados. Sin ingresos laborales y con menos años para recuperar pérdidas, son más aversos.
- **Edad:** la relación **no es lineal** (ρ = {_num(float(asoc_i.loc["Edad", "Estadístico"]), 2)}). Entre 18 y 64 años el puntaje medio se mantiene entre 18 y 22
  (sube incluso en 55-64) y cae con fuerza desde los 65: los mayores de 65 promedian {_num(float(mayores["puntaje"].mean()), 1)} frente a
  {_num(float(resto["puntaje"].mean()), 1)} del resto. Es el patrón de ciclo de vida: la aversión aumenta al llegar el retiro. Por eso una
  correlación lineal (Spearman) no lo detecta.
- **Experiencia invirtiendo:** forma de U invertida: el puntaje sube de *sin experiencia* ({_num(float(exp.iloc[0]["Media"]), 1)}) a
  *3 a 5 años* y baja en quienes llevan más de 5 años. Con 2 o 3 personas en los extremos no es concluyente,
  pero sugiere que haber vivido crisis reales modera el apetito por riesgo.
- **Ingresos, educación, dependientes, horizonte y colchón de emergencia** no muestran relación (p > 0,2): en
  esta muestra tener más ingresos o un colchón de emergencia no hace a las personas más tolerantes al riesgo.
{f"- Ningún factor es significativo después del ajuste por pruebas múltiples: con n = {n} la potencia es baja y estas conclusiones son exploratorias." if ninguno_sig else ""}

![Correlaciones de Spearman entre preguntas, puntaje y factores ordinales]({figuras["eda_correlaciones"].name}){{width=80%}}

## Implicaciones para el portafolio completo

![Personas en cada A y su y*: aplicado (con tope) y el valor de la fórmula]({figuras["eda_ystar"].name}){{width=86%}}

Con el portafolio de riesgo de referencia, la fórmula pide endeudarse ($y^*$ > 100 %) a quienes tienen A = {", ".join(str(a) for a in a_tope)}:
el **{_pct(float(d["a"].isin(a_tope).mean()), 0)} de los encuestados**, que quedan totalmente invertidos en el portafolio de riesgo. El
{_pct(float(d["a"].isin(a_casi).mean()), 0)} (A = {", ".join(str(a) for a in a_casi)}) queda con {", ".join(_pct(r.y_por_a[a], 0) for a in a_casi)} en riesgo, y el resto combina el portafolio de riesgo con el
activo libre de riesgo. La paradoja: el {_pct(float(it.loc["6", "a"]), 0)} dijo que nunca se endeudaría para invertir, mientras la
fórmula le pediría endeudarse a una parte de ellos. El tope de 100 % es coherente con lo que las personas declaran.

**Portafolios guardados:** {len(propios)} personas armaron su propio portafolio y {len(pf) - len(propios)} recibieron el de referencia.
Activos más escogidos por quienes armaron el suyo: {", ".join(f"{k} ({v})" for k, v in elegidos.head(8).items())}.
{f"{con_apal} de ellas incluyeron ETF apalancados (TQQQ, UPRO…): conviene advertir más sobre estos productos." if con_apal else ""}

## Conclusiones del EDA

1. El formato produce una distribución centrada en *moderado*; los extremos son raros.
2. Es **razonablemente confiable** (α = {_num(r.alfa, 2)}), aunque la pregunta 5 (lotería) mide algo distinto y la 2C
   (30 años) se interpreta de forma inconsistente: son candidatas a revisión.
3. Lo que más se asocia con mayor aversión es **la etapa de vida** (65 años o más, jubilados), no los ingresos
   ni la educación.
4. La mayoría no tomaría crédito para invertir: el límite $y^* \\le 1$ del aplicativo es coherente con sus
   respuestas.
"""


def generar_pdf(
    c: CasoReferencia,
    carpeta: str | Path,
    voluntarios: pd.DataFrame | None,
    fecha: dt.date,
    fundamentales: pd.DataFrame | None = None,
) -> Path:
    carpeta = Path(carpeta)
    figs = carpeta / "figuras"
    figs.mkdir(parents=True, exist_ok=True)
    figuras = {
        "frontera": graficos.frontera_y_cal(c, figs / "frontera.png"),
        "pesos": graficos.pesos_optimos(c, figs / "pesos.png"),
        "completo": graficos.completo_por_perfil(c, figs / "completo.png"),
        "correlaciones": graficos.correlaciones(c, figs / "correlaciones.png"),
        "desempeno": graficos.desempeno(c, figs / "desempeno.png"),
        "indiferencia": graficos.indiferencia(c, figs / "indiferencia.png"),
        "composicion": graficos.composicion_por_perfil(
            composicion_completa(c), figs / "composicion.png"
        ),
    }
    eda = None
    if voluntarios is not None and not voluntarios.empty:
        esc = c.escenarios.set_index("a")
        eda = eda_mod.analizar(
            voluntarios,
            figs,
            {int(a): float(v) for a, v in esc["y"].items()},
            {int(a): float(v) for a, v in esc["y_sin_recorte"].items()},
        )
        figuras |= eda.figuras
    md = carpeta / "_informe.md"
    md.write_text(
        construir_markdown(c, figuras, voluntarios, fecha, fundamentales, eda), encoding="utf-8"
    )
    salida = carpeta / "Taller1_Informe.pdf"
    subprocess.run(
        ["pandoc", md.name, "-o", salida.name, "--pdf-engine=xelatex", "--resource-path=figuras"],
        cwd=carpeta,
        check=True,
    )
    md.unlink()
    return salida
