# ruff: noqa: E501  (texto del informe: prosa larga)
"""Informe PDF del Taller 1 (Markdown → PDF con pandoc + xelatex), explicado paso a paso."""

import datetime as dt
import subprocess
from pathlib import Path

import pandas as pd

from . import graficos
from .caso import (
    TABLA_PERFILES,
    UNIVERSO_REFERENCIA,
    CasoReferencia,
    SeleccionPerfil,
    portafolio_de_voluntario,
)

URL_APP = "https://mft-investements.streamlit.app/"
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
RANGOS_ENUNCIADO = ["25-34", "35-44", "45-54", "55-64", "65-74"]
COLUMNAS_RESPUESTAS = ["q1", "q2a", "q2b", "q2c", "q3", "q4", "q5", "q6", "q7"]


def _pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f} %".replace(".", ",")


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, disable_numparse=True)


ETIQUETA_FACTOR = {
    "ocupacion": "Ocupación",
    "rango_ingresos": "Ingresos (COP/mes)",
    "dependientes_economicos": "Dependientes",
    "nivel_educativo": "Educación",
    "experiencia_invirtiendo_anios": "Experiencia invirtiendo",
    "horizonte_principal_inversion": "Horizonte",
    "colchon_emergencia": "Colchón de emergencia",
}


def _factores_transpuestos(v: pd.DataFrame, factores: list[str]) -> str:
    """Una fila por factor y una columna por voluntario (cabe en la página)."""
    t = v.set_index("alias")[factores].replace("", "—").fillna("—").T
    t.index = [ETIQUETA_FACTOR.get(f, f) for f in t.index]
    return _md(t.reset_index(names="Factor"))


def seccion_voluntarios(c: CasoReferencia, voluntarios: pd.DataFrame | None) -> str:
    if voluntarios is None or voluntarios.empty:
        return (
            "**Pendiente de completar.** Los resultados de los cinco voluntarios (uno por rango de "
            "edad) se agregan al correr el generador con el archivo `datos/voluntarios.csv` "
            "(plantilla incluida en la carpeta de la entrega). Cada voluntario responde las nueve "
            "preguntas, la plataforma calcula su puntaje, su perfil y su coeficiente A, y con ese "
            "A se compone su portafolio completo."
        )
    filas = []
    for _, v in voluntarios.iterrows():
        r = portafolio_de_voluntario(c, {k: str(v[k]) for k in COLUMNAS_RESPUESTAS})
        filas.append(
            {
                "Voluntario": v["alias"],
                "Edad": v["rango_edad"],
                "Puntaje": r["puntaje"],
                "Perfil": r["perfil"],
                "A": r["a"],
                "En riesgo (y*)": _pct(r["y"], 0),
                "E(Rc)": _pct(r["retorno"]),
                "σc": _pct(r["sigma"]),
            }
        )
    tabla = _md(pd.DataFrame(filas))
    columnas_fijas = ["alias", "rango_edad", *COLUMNAS_RESPUESTAS, "activos_elegidos", "y_guardado"]
    factores = [
        col
        for col in voluntarios.columns
        if col not in columnas_fijas
        and voluntarios[col].fillna("").astype(str).str.strip().ne("").any()
    ]
    extra = ""
    if factores:
        extra = (
            "\n\n**Factores personales recolectados** (para entender qué moldea la aversión al "
            "riesgo; con tan pocas personas son indicios, no conclusiones estadísticas):\n\n"
            + _factores_transpuestos(voluntarios, factores)
        )
    elegidos = (
        voluntarios[["alias", "activos_elegidos", "y_guardado"]].fillna("")
        if {"activos_elegidos", "y_guardado"} <= set(voluntarios.columns)
        else None
    )
    if elegidos is not None and elegidos["activos_elegidos"].astype(str).str.strip().ne("").any():
        elegidos = elegidos.rename(
            columns={
                "alias": "Voluntario",
                "activos_elegidos": "Activos que eligió",
                "y_guardado": "y* guardado",
            }
        )
        extra += (
            "\n\n**Portafolios que armaron en la aplicación** (los voluntarios sin fila aún no "
            "han armado su portafolio):\n\n"
            + _md(elegidos[elegidos["Activos que eligió"].astype(str).str.strip().ne("")])
        )
    faltan = [r for r in RANGOS_ENUNCIADO if r not in set(voluntarios["rango_edad"])]
    if faltan:
        extra += (
            f"\n\n> **Pendiente:** el enunciado pide un voluntario por rango de edad; aún faltan los "
            f"rangos {', '.join(faltan)}."
        )
    return tabla + extra


def seccion_seleccion(selecciones: list[SeleccionPerfil] | None) -> str:
    if not selecciones:
        return ""
    filas = []
    for x in selecciones:
        filas.append(
            {
                "A": x.a,
                "Perfil": x.perfil,
                "Vol. media": _pct(x.vol_media, 0),
                "Retorno medio": _pct(x.ret_medio, 0),
                "Los 11 activos sugeridos": ", ".join(x.tickers),
            }
        )
    res = [
        {
            "A": x.a,
            "E(Rp)": _pct(x.retorno),
            "σp": _pct(x.sigma),
            "Sharpe": f"{x.sharpe:.2f}".replace(".", ","),
            "y*": _pct(x.y, 0),
            "E(Rc)": _pct(x.retorno_completo),
            "Días en común": x.n_obs,
        }
        for x in selecciones
        if x.retorno is not None
    ]
    return f"""
## Paso 1b · Qué 11 activos sugiere la aplicación según el perfil

En la aplicación, el botón **"Cargar selección de referencia para mi perfil"** propone un universo de
11 activos **con reglas, no con una lista fija** (así se adapta si cambia el comportamiento de los
activos). A es continuo (se acota entre 1 y 8):

1. Se descartan los activos con menos de un año de historia y los ETF apalancados o inversos.
2. Cada activo recibe un puntaje $w\\cdot pct(\\text{{retorno}}) + (1-w)\\cdot pct(-\\text{{volatilidad}})$, con
   $w=(8-A)/7$ y $pct$ = posición (percentil) del activo entre los elegibles. **A menor A** pesa más el
   retorno histórico (se acepta más riesgo); **a mayor A** pesa más la baja volatilidad.
3. Se toma el mejor activo de cada una de las 5 mejores clases (acciones, renta fija, REIT, oro,
   cripto…) y los cupos restantes por puntaje, con máximo 3 por clase.

Resultado con los datos de este informe:

{_md(pd.DataFrame(filas))}

Con Markowitz sobre cada selección (mismas restricciones: largos, máximo 40 % por activo):

{_md(pd.DataFrame(res))}

Las selecciones con IBIT o GXTESCOL.CL se estiman sobre menos días en común (esos ETF son jóvenes),
por eso su Sharpe se ve alto: es una limitación de los datos, que la aplicación advierte al usuario.
El portafolio de riesgo óptimo **no** depende de A (solo del universo y los datos); A define cuánto se
invierte en él (y\\*). Esta selección es solo un punto de partida: el usuario la puede modificar.
"""


def construir_markdown(
    c: CasoReferencia,
    figuras: dict[str, Path],
    voluntarios: pd.DataFrame | None,
    fecha: dt.date,
    selecciones: list[SeleccionPerfil] | None = None,
) -> str:
    w = c.tangente.w
    activos = w[w > 0.0005].sort_values(ascending=False)
    tope = [t for t in activos.index if activos[t] >= c.params.w_max - 1e-4]
    universo = pd.DataFrame(
        {
            "Ticker": list(UNIVERSO_REFERENCIA),
            "Qué es": list(UNIVERSO_REFERENCIA.values()),
            "Retorno esp.": [_pct(c.est.mu[t]) for t in UNIVERSO_REFERENCIA],
            "Riesgo (σ)": [_pct(c.est.sigma.loc[t, t] ** 0.5) for t in UNIVERSO_REFERENCIA],
        }
    )
    optimo = pd.DataFrame({"ETF": activos.index, "Peso": [_pct(v) for v in activos.to_numpy()]})
    esc = c.escenarios
    perfiles = pd.DataFrame(
        {
            "Puntaje": [f"{a}–{b}" for a, b, _e, _A in TABLA_PERFILES],
            "Perfil": [e for _a, _b, e, _A in TABLA_PERFILES],
            "A": [A for *_x, A in TABLA_PERFILES],
        }
    )
    completo = pd.DataFrame(
        {
            "A": esc["a"].astype(int),
            "y* sin recorte": [f"{v:.2f}".replace(".", ",") for v in esc["y_sin_recorte"]],
            "En riesgo (y*)": [_pct(v, 0) for v in esc["y"]],
            "En libre de riesgo": [_pct(v, 0) for v in esc["peso_rf"]],
            "E(Rc)": [_pct(v) for v in esc["retorno"]],
            "σc": [_pct(v) for v in esc["sigma"]],
            "Utilidad": [_pct(v) for v in esc["utilidad"]],
        }
    )
    ini, fin = c.ventana
    dur = c.duration_port["duration_rf_normalizada"]
    return f"""---
title: "Taller 1 · Aversión al riesgo y portafolio óptimo (Markowitz)"
subtitle: "Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026"
author: "Prof. Juan Carlos Botero Ramírez · Grupo MFT Investments"
date: "{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"
lang: es
geometry: margin=2.3cm
fontsize: 11pt
mainfont: Arial
colorlinks: true
---

# 1. Resumen

Este informe explica, paso a paso, cómo se obtiene (i) el grado de aversión al riesgo **A** de un
inversionista, (ii) su **portafolio de riesgo óptimo** con el modelo de Markowitz y (iii) su
**portafolio completo**, que reparte el dinero entre ese portafolio de riesgo y un activo libre de
riesgo. Todo está construido en una aplicación web (proto robo-advisor) que cualquier persona puede
probar: <{URL_APP}>.

**Resultado del caso de referencia** (11 ETF, datos hasta {fin:%d-%m-%Y}):

- El portafolio de riesgo óptimo tiene un retorno esperado de **{_pct(c.tangente.retorno)}**
  anual, una desviación estándar de **{_pct(c.tangente.sigma)}** y un ratio de Sharpe de
  **{c.tangente.sharpe:.2f}**.
- Un inversionista *conservador* (A = 8) pone **{_pct(float(esc.loc[esc.a == 8, "y"].iloc[0]), 0)}**
  de su dinero en ese portafolio de riesgo; uno *agresivo* (A = 1) pone el **100 %** (la app no
  permite apalancamiento).

> **Aviso:** ejercicio académico. No constituye asesoría de inversión. Los retornos pasados no
> garantizan retornos futuros.

# 2. Parte 1 · Aversión al riesgo (el coeficiente A)

La utilidad de un inversionista se mide con $U = E(r) - \\tfrac{{1}}{{2}} A \\sigma^2$: sube con el
retorno esperado y baja con el riesgo, y baja más cuanto mayor es **A** (más averso al riesgo).

**Cómo se obtiene A.** Cada persona responde el formato de nueve preguntas del enunciado (reacción
ante pérdidas y ganancias, horizonte, préstamos, etc.). Cada respuesta *a* vale 1 punto, *b* vale 2
y *c* vale 3; el puntaje total va de 9 a 27 y define el perfil:

{_md(perfiles)}

## Los cinco voluntarios

{seccion_voluntarios(c, voluntarios)}

# 3. Parte 2 · Portafolio óptimo (Markowitz)

## Paso 1 · El universo de activos

Se usan **11 ETF** (fondos que replican índices) que cubren las clases de activo del enunciado:
acciones de EE.UU., EAFE, emergentes y Latinoamérica; renta fija grado de inversión, high yield y
emergente; REIT y oro. (La app permite elegir entre más de 30 activos, incluidos TES de Colombia,
COLO y bitcoin.) Fuente de precios: Yahoo Finance, precios diarios ajustados por dividendos, en USD.

{_md(universo)}

Este universo de 11 ETF es el **caso de referencia** con el que se explican los pasos siguientes.
{seccion_seleccion(selecciones)}
## Paso 2 · Retornos, riesgos y correlaciones

Con los **{c.est.n_obs} retornos diarios** entre {ini:%d-%m-%Y} y {fin:%d-%m-%Y} (≈ 5 años) se calcula
el retorno esperado anual de cada ETF (media diaria × 252) y la matriz de covarianzas (covarianza
muestral × 252). La tasa libre de riesgo es el rendimiento del T-note de EE.UU. a 10 años:
**{_pct(c.rf, 2)}**.

## Paso 3 · Frontera eficiente y CAL óptima

La **frontera eficiente** reúne los portafolios con el máximo retorno posible para cada nivel de
riesgo. La **CAL** (línea de asignación de capital) es la recta que sale del activo libre de riesgo y
toca la frontera en un solo punto: el **portafolio de riesgo óptimo** (el de mayor ratio de Sharpe).
Restricciones: solo posiciones largas y máximo {_pct(c.params.w_max, 0)} por activo.

![Frontera eficiente, CAL y portafolio óptimo]({figuras["frontera"].name}){{width=95%}}

## Paso 4 · Composición del portafolio de riesgo óptimo

{_md(optimo)}

![Pesos del portafolio de riesgo óptimo]({figuras["pesos"].name}){{width=80%}}

Indicadores: retorno esperado **{_pct(c.tangente.retorno)}**, desviación estándar
**{_pct(c.tangente.sigma)}**, ratio de Sharpe **{c.tangente.sharpe:.2f}**
(= (retorno − tasa libre de riesgo) / desviación estándar).
{"Los activos " + ", ".join(tope) + f" llegan al tope de {_pct(c.params.w_max, 0)} por activo: el optimizador los quisiera aún más, por su buen desempeño histórico en la ventana; es una limitación de usar retornos pasados como si fueran el futuro." if tope else ""}

## Paso 5 · Portafolio completo según el perfil

La fracción que va al portafolio de riesgo es $y^* = \\dfrac{{E(R_p) - r_f}}{{A\\,\\sigma_p^2}}$,
acotada entre 0 y 1 (sin apalancamiento). El resto, $1-y^*$, va al activo libre de riesgo.

{_md(completo)}

![Dónde queda el dinero de cada perfil]({figuras["completo"].name}){{width=75%}}

Para A = 4, 3 y 1 la fórmula daría más de 100 % en riesgo (apalancamiento); como la app no
apalanca, se limita a 100 %.

## Paso 6 · Beta de las acciones y duration de los bonos

Beta frente al índice mundial ACWI (misma ventana): {", ".join(f"{t} {b:.2f}".replace(".", ",") for t, b in c.betas.items())}.
Beta ponderada de la parte accionaria del portafolio: **{c.beta_port["beta_normalizada"]:.2f}**.
Duration de los ETF de renta fija (años, del catálogo): LQD 8,4 · IEF 7,5 · HYG 3,5 · EMB 7,0. La
parte de renta fija del portafolio óptimo es {"nula" if dur == 0 else f"de duration {dur:.1f} años".replace(".", ",")}.

## Paso 7 · Análisis de múltiplos (acciones)

Para sugerir si conviene subir o bajar la posición en una acción o índice frente a lo que arroja el
portafolio neutral, la plataforma compara el **P/E de hoy de cada activo con su propio histórico**
(P/E alto frente a lo normal para él → "cara"; bajo → "barata"). La señal ajusta una sugerencia de
±2,5 puntos de peso; no recalcula Markowitz. Las señales vigentes se ven en la página *Mi portafolio*
de la aplicación, que acumula una foto semanal de los múltiplos (se necesitan al menos 12 para dar
señal).

# 4. El aplicativo (proto robo-advisor)

La aplicación <{URL_APP}> permite crear una cuenta (solo correo, alias y rango de edad), responder
el cuestionario una vez, armar el portafolio escogiendo entre 3 y 11 activos del catálogo, y ver su
composición completa con la frontera, la CAL y su curva de indiferencia. En cada ingreso muestra cómo
ha rendido con los precios nuevos y da recomendaciones con **reglas fijas** (sin inteligencia
artificial). Los precios se actualizan cada día hábil con un proceso automático.

# 5. Limitaciones

- Retornos y riesgos son **históricos** ({c.est.n_obs} días); el retorno esperado estimado así es
  muy inestable y empuja a concentrar en los activos que más subieron.
- Sin apalancamiento y solo posiciones largas; moneda base USD.
- Cinco voluntarios no dan significancia estadística.

# Anexo · Cómo reproducir

El código está en el repositorio. `python -m roboadvisor.taller1.reportes` regenera este PDF y el
Excel con los mismos números (datos en `data_local/taller1/`).
"""


def generar_pdf(
    c: CasoReferencia,
    carpeta: str | Path,
    voluntarios: pd.DataFrame | None,
    fecha: dt.date,
    selecciones: list[SeleccionPerfil] | None = None,
) -> Path:
    carpeta = Path(carpeta)
    figs = carpeta / "figuras"
    figs.mkdir(parents=True, exist_ok=True)
    figuras = {
        "frontera": graficos.frontera_y_cal(c, figs / "frontera.png"),
        "pesos": graficos.pesos_optimos(c, figs / "pesos.png"),
        "completo": graficos.completo_por_perfil(c, figs / "completo.png"),
    }
    md = carpeta / "_informe.md"
    md.write_text(construir_markdown(c, figuras, voluntarios, fecha, selecciones), encoding="utf-8")
    salida = carpeta / "Taller1_Informe.pdf"
    subprocess.run(
        ["pandoc", md.name, "-o", salida.name, "--pdf-engine=xelatex", "--resource-path=figuras"],
        cwd=carpeta,
        check=True,
    )
    md.unlink()
    return salida
