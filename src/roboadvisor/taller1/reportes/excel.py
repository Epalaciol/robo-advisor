# ruff: noqa: E501  (fórmulas de Excel largas)
"""Excel del Taller 1: valores calculados por el motor y fórmulas vivas en lo esencial.

Hojas: Resumen · Cuestionario · Universo · Retornos y Σ · Portafolio de riesgo · Frontera y CAL ·
Portafolio completo (y*, utilidad, con y sin tope, con fórmulas) · Composición completa · Betas y
duration · Múltiplos · Encuestas (puntaje, perfil, A e y* con fórmulas) · EDA.
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from roboadvisor.taller1.core.cuestionario import IDS_PREGUNTAS

from .caso import DURATIONS, TABLA_PERFILES, CasoReferencia, multiplos_referencia

ENCABEZADO = PatternFill("solid", fgColor="1F4E79")


def _tabla(
    ws, fila: int, columnas: list[str], filas: list[list], formato: dict | None = None
) -> int:
    for j, nombre in enumerate(columnas, start=1):
        c = ws.cell(fila, j, nombre)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), ENCABEZADO
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, datos in enumerate(filas, start=fila + 1):
        for j, v in enumerate(datos, start=1):
            c = ws.cell(i, j, v)
            if formato and columnas[j - 1] in formato:
                c.number_format = formato[columnas[j - 1]]
    return fila + len(filas) + 1


def _ancho(ws, ancho: int = 16) -> None:
    for j in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(j)].width = ancho
    ws.column_dimensions["A"].width = max(ws.column_dimensions["A"].width or 0, 28)


def generar_excel(
    c: CasoReferencia,
    ruta: str | Path,
    voluntarios: pd.DataFrame | None = None,
    fundamentales: pd.DataFrame | None = None,
) -> Path:
    ruta = Path(ruta)
    wb = Workbook()
    pct = "0.00%"

    ws = wb.active
    ws.title = "Resumen"
    ws["A1"], ws["A1"].font = "Taller 1 · Resumen del caso de referencia", Font(bold=True, size=14)
    filas = [
        ["Ventana de datos", f"{c.ventana[0]:%d-%m-%Y} a {c.ventana[1]:%d-%m-%Y}"],
        ["Observaciones diarias", c.est.n_obs],
        ["Tasa libre de riesgo (T-note 10 años)", c.rf],
        ["Retorno esperado del portafolio de riesgo", c.tangente.retorno],
        ["Desviación estándar del portafolio de riesgo", c.tangente.sigma],
        ["Ratio de Sharpe", c.tangente.sharpe],
        ["Peso máximo por activo", c.params.w_max],
        [
            "Aviso",
            "Ejercicio académico; no es asesoría financiera. El pasado no garantiza resultados.",
        ],
    ]
    _tabla(ws, 3, ["Concepto", "Valor"], filas)
    for r in (6, 7, 8, 10):  # filas con porcentajes (la 9 es el Sharpe)
        ws.cell(r, 2).number_format = pct
    ws.cell(9, 2).number_format = "0.000"
    _ancho(ws, 22)
    ws.column_dimensions["B"].width = 60

    ws = wb.create_sheet("Cuestionario")
    _tabla(
        ws, 1, ["Puntaje desde", "Puntaje hasta", "Perfil", "A"], [list(f) for f in TABLA_PERFILES]
    )
    ws["A8"] = "Puntaje = 1·(#a) + 2·(#b) + 3·(#c) sobre 9 preguntas (rango 9–27)."
    _ancho(ws)

    ws = wb.create_sheet("Universo")
    _tabla(
        ws,
        1,
        ["Ticker", "Descripción", "Retorno esperado", "Desv. estándar", "Primer dato"],
        [
            [
                t,
                c.universo[t],
                float(c.est.mu[t]),
                float(c.est.sigma.loc[t, t] ** 0.5),
                c.precios[t].first_valid_index().strftime("%Y-%m-%d"),
            ]
            for t in c.est.tickers
        ],
        {"Retorno esperado": pct, "Desv. estándar": pct},
    )
    _ancho(ws)
    ws.column_dimensions["B"].width = 42

    ws = wb.create_sheet("Retornos y Σ")
    ws["A1"] = "Retorno esperado anual (media diaria × 252) y covarianza anual (muestral × 252)"
    _tabla(ws, 3, ["Ticker", "μ"], [[t, float(c.est.mu[t])] for t in c.est.tickers], {"μ": pct})
    ini = 3 + len(c.est.tickers) + 3
    _tabla(
        ws,
        ini,
        ["Σ", *c.est.tickers],
        [[t, *[float(v) for v in c.est.sigma.loc[t]]] for t in c.est.tickers],
    )
    for r in range(ini + 1, ini + 1 + len(c.est.tickers)):
        for col in range(2, 2 + len(c.est.tickers)):
            ws.cell(r, col).number_format = "0.0000"
    _ancho(ws, 11)

    ws = wb.create_sheet("Portafolio de riesgo")
    w = c.tangente.w
    _tabla(
        ws,
        1,
        ["Ticker", "Tangente (óptimo)", "Mínima varianza"],
        [[t, float(w[t]), float(c.min_var.w[t])] for t in c.est.tickers],
        {"Tangente (óptimo)": pct, "Mínima varianza": pct},
    )
    n = len(c.est.tickers)
    r0 = n + 3
    ws.cell(r0, 1, "Retorno esperado")
    ws.cell(r0, 2, f"=SUMPRODUCT(B2:B{n + 1},'Retornos y Σ'!B4:B{n + 3})").number_format = pct
    ws.cell(r0 + 1, 1, "Desviación estándar (valor del motor)")
    ws.cell(r0 + 1, 2, c.tangente.sigma).number_format = pct
    ws.cell(r0 + 2, 1, "Ratio de Sharpe = (E(Rp) − rf) / σp")
    ws.cell(r0 + 2, 2, f"=(B{r0}-Resumen!$B$6)/B{r0 + 1}").number_format = "0.000"
    _ancho(ws, 20)

    ws = wb.create_sheet("Frontera y CAL")
    f = c.frontera
    _tabla(
        ws,
        1,
        ["Desv. estándar", "Retorno", "CAL: rf + S*·σ"],
        [
            [float(s), float(r), f"=Resumen!$B$6+Resumen!$B$9*A{i}"]
            for i, (s, r) in enumerate(zip(f["sigma"], f["retorno"], strict=True), start=2)
        ],
        {"Desv. estándar": pct, "Retorno": pct, "CAL: rf + S*·σ": pct},
    )
    _ancho(ws, 18)

    ws = wb.create_sheet("Portafolio completo")
    ws["A1"] = (
        "y* = (E(Rp) − rf) / (A·σp²), recortado a [0, 1] (sin apalancamiento). U = E(Rc) − ½·A·σc²"
    )
    cols = [
        "A", "y* sin recorte", "y*", "% libre de riesgo", "E(Rc)", "σc", "Utilidad",
        "Préstamo sin tope (y*−1)", "E(Rc) sin tope", "σc sin tope", "Utilidad sin tope",
        "Pérdida si P cae 20 % (sin tope)",
    ]  # fmt: skip
    filas = []
    for i, a in enumerate(c.escenarios["a"], start=4):
        filas.append(
            [
                int(a),
                f"=(Resumen!$B$7-Resumen!$B$6)/(A{i}*Resumen!$B$8^2)",
                f"=MIN(MAX(B{i},0),1)",
                f"=1-C{i}",
                f"=Resumen!$B$6+C{i}*(Resumen!$B$7-Resumen!$B$6)",
                f"=C{i}*Resumen!$B$8",
                f"=E{i}-0.5*A{i}*F{i}^2",
                f"=MAX(B{i}-1,0)",
                f"=Resumen!$B$6+B{i}*(Resumen!$B$7-Resumen!$B$6)",
                f"=B{i}*Resumen!$B$8",
                f"=I{i}-0.5*A{i}*J{i}^2",
                f"=-0.2*B{i}",
            ]
        )
    _tabla(ws, 3, cols, filas, {k: pct for k in cols[1:]})
    ws["A10"] = (
        "Para A ≤ 4 la fórmula da y* > 1: la persona querría pedir prestado a rf para invertir más "
        "de 100 % en P. El aplicativo no apalanca: se limita a 100 % (columna C)."
    )
    _ancho(ws, 18)

    ws = wb.create_sheet("Composición completa")
    ws["A1"] = "Peso de cada activo en el portafolio completo = y* × peso en P (fórmulas)."
    n_t = len(c.est.tickers)
    a_cols = list(c.escenarios["a"])
    filas = []
    for k, t in enumerate(c.est.tickers, start=4):
        filas.append(
            [t]
            + [
                f"='Portafolio de riesgo'!B{k - 2}*'Portafolio completo'!C{j}"
                for j in range(4, 4 + len(a_cols))
            ]
        )
    filas.append(
        ["Libre de riesgo"] + [f"='Portafolio completo'!D{j}" for j in range(4, 4 + len(a_cols))]
    )
    filas.append(
        ["Total"]
        + [
            f"=SUM({get_column_letter(j)}4:{get_column_letter(j)}{4 + n_t})"
            for j in range(2, 2 + len(a_cols))
        ]
    )
    _tabla(
        ws,
        3,
        ["Activo", *[f"A = {int(a)}" for a in a_cols]],
        filas,
        {f"A = {int(a)}": pct for a in a_cols},
    )
    _ancho(ws, 14)

    ws = wb.create_sheet("Betas y duration")
    _tabla(
        ws,
        1,
        ["Ticker (acciones)", "Beta vs ACWI"],
        [[t, float(b)] for t, b in c.betas.items()],
        {"Beta vs ACWI": "0.00"},
    )
    r0 = len(c.betas) + 4
    _tabla(
        ws, r0, ["Ticker (renta fija)", "Duration (años)"], [[t, d] for t, d in DURATIONS.items()]
    )
    ws.cell(r0 + 6, 1, "Beta del portafolio (parte accionaria)")
    ws.cell(r0 + 6, 2, c.beta_port["beta_normalizada"]).number_format = "0.00"
    ws.cell(r0 + 7, 1, "Duration del portafolio (parte renta fija)")
    peso_bonos = float(c.tangente.w.reindex(list(DURATIONS)).fillna(0).sum())
    ws.cell(
        r0 + 7,
        2,
        c.duration_port["duration_rf_normalizada"] if peso_bonos > 0.005 else "N/A (sin bonos)",
    )
    ws.cell(r0 + 7, 2).number_format = "0.00"
    _ancho(ws, 24)

    if fundamentales is not None and not fundamentales.empty:
        _hoja_multiplos(wb, c, fundamentales)
    _hoja_encuestas(wb, voluntarios)
    if voluntarios is not None and not voluntarios.empty:
        _hoja_eda(wb, voluntarios)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta


def _hoja_multiplos(wb, c: CasoReferencia, fundamentales: pd.DataFrame) -> None:
    m = multiplos_referencia(c, fundamentales)
    ws = wb.create_sheet("Múltiplos")
    ws["A1"] = f"P/E de la foto semanal del {m['fecha']:%Y-%m-%d} (Yahoo Finance). Referencia ACWI:"
    ws["F1"] = m["pe_acwi"]
    ws["A2"] = (
        f"P/E relativo = P/E / P/E ACWI; < {c.params.pe_relativo_barata} barata (+{c.params.tilt_multiplos:.1%}), "
        f"> {c.params.pe_relativo_cara} cara (−{c.params.tilt_multiplos:.1%}); luego se renormaliza."
    )
    t = m["tabla"]
    filas = [
        [
            r.ticker, r.pe, f"=1/B{i}", f"=B{i}/$F$1", r.dividend_yield,
            f'=IF(D{i}<{c.params.pe_relativo_barata},"barata",IF(D{i}>{c.params.pe_relativo_cara},"cara","neutral"))',
            r.peso_neutral, r.peso_ajustado,
        ]
        for i, r in enumerate(t.itertuples(), start=5)
    ]  # fmt: skip
    _tabla(
        ws, 4,
        ["ETF", "P/E", "1/PE", "P/E relativo", "Dividend yield", "Señal", "Peso neutral", "Peso sugerido"],
        filas,
        {"1/PE": "0.00%", "P/E relativo": "0.00", "Dividend yield": "0.00%", "Peso neutral": "0.00%",
         "Peso sugerido": "0.00%", "P/E": "0.0"},
    )  # fmt: skip
    _ancho(ws, 15)


def _hoja_encuestas(wb, voluntarios: pd.DataFrame | None) -> None:
    """Todas las encuestas (anonimizadas) con puntaje, perfil, A e y* calculados con fórmulas."""
    ws = wb.create_sheet("Encuestas")
    if voluntarios is None or voluntarios.empty:
        ws["A1"] = "Pendiente: ver entregas/taller-1/datos/voluntarios_plantilla.csv"
        return
    extra = [x for x in voluntarios.columns if x not in ("alias", "rango_edad", *IDS_PREGUNTAS)]
    cols = ["Alias", "Edad", *[x.upper() for x in IDS_PREGUNTAS], "Puntaje", "Perfil", "A",
            "y* (con tope)", "y* fórmula", *extra]  # fmt: skip
    filas = []
    for i, (_, r) in enumerate(voluntarios.iterrows(), start=2):
        rango = f"C{i}:K{i}"
        filas.append(
            [
                r["alias"], r["rango_edad"], *[r[q] for q in IDS_PREGUNTAS],
                f'=COUNTIF({rango},"a")+2*COUNTIF({rango},"b")+3*COUNTIF({rango},"c")',
                f'=LOOKUP(L{i},{{9,13,17,21,25}},{{"Conservador","Conservador a Moderado","Moderado","Moderado a Agresivo","Agresivo"}})',
                f"=LOOKUP(L{i},{{9,13,17,21,25}},{{8,6,4,3,1}})",
                f"=MIN(MAX(P{i},0),1)",
                f"=(Resumen!$B$7-Resumen!$B$6)/(N{i}*Resumen!$B$8^2)",
                *[r[x] for x in extra],
            ]
        )  # fmt: skip
    _tabla(ws, 1, cols, filas, {"y* (con tope)": "0.0%", "y* fórmula": "0.0%"})
    _ancho(ws, 9)
    for col in range(17, 17 + len(extra)):
        ws.column_dimensions[get_column_letter(col)].width = 22


def _hoja_eda(wb, voluntarios: pd.DataFrame) -> None:
    from . import eda

    d = eda.preparar(voluntarios)
    ws = wb.create_sheet("EDA")
    ws["A1"], ws["A1"].font = "Análisis exploratorio de las encuestas", Font(bold=True, size=13)
    perf = eda.tabla_perfiles(d)
    fila = _tabla(
        ws, 3, ["Perfil", "Puntaje", "A", "Personas (fórmula)", "%"],
        [[r.Perfil, r.Puntaje, r.A, f"=COUNTIF(Encuestas!$N:$N,C{i})", f"=D{i}/SUM($D$4:$D$8)"]
         for i, r in enumerate(perf.itertuples(), start=4)],
        {"%": "0%"},
    )  # fmt: skip
    items = eda.tabla_items(d)
    fila = _tabla(
        ws, fila + 2, ["Pregunta", "a", "b", "c", "Media (1–3)"],
        [[r.Pregunta, r.a, r.b, r.c, r._5] for r in items.itertuples()],
        {"a": "0%", "b": "0%", "c": "0%", "Media (1–3)": "0.00"},
    )  # fmt: skip
    alfa, ir = eda.cronbach(d)
    ws.cell(fila + 2, 1, "Alfa de Cronbach (9 ítems)").font = Font(bold=True)
    ws.cell(fila + 2, 2, alfa).number_format = "0.00"
    fila = _tabla(
        ws, fila + 4, ["Pregunta", "Correlación ítem-resto", "α sin el ítem"],
        [[r.Pregunta, r._2, r._3] for r in ir.itertuples()],
        {"Correlación ítem-resto": "0.00", "α sin el ítem": "0.00"},
    )  # fmt: skip
    asoc = eda.asociaciones(d)
    _tabla(
        ws, fila + 2, list(asoc.columns), asoc.astype(object).values.tolist(),
        {"Estadístico": "0.00", "p": "0.000", "p ajustado (BH)": "0.000"},
    )  # fmt: skip
    _ancho(ws, 16)
    ws.column_dimensions["A"].width = 34
