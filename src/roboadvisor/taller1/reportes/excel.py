"""Excel del Taller 1: valores calculados por el motor y fórmulas vivas en lo esencial.

Hojas: Resumen · Cuestionario · Universo · Retornos y Σ · Portafolio de riesgo · Frontera y CAL ·
Portafolio completo (y*, utilidad y Sharpe con fórmulas) · Betas y duration · Voluntarios.
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .caso import DURATIONS, TABLA_PERFILES, CasoReferencia

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
    c: CasoReferencia, ruta: str | Path, voluntarios: pd.DataFrame | None = None
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
    cols = ["A", "y* sin recorte", "y*", "% libre de riesgo", "E(Rc)", "σc", "Utilidad"]
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
            ]
        )
    _tabla(ws, 3, cols, filas, {k: pct for k in cols[1:3] + cols[3:]})
    _ancho(ws, 18)

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
    ws.cell(r0 + 7, 2, c.duration_port["duration_rf_normalizada"]).number_format = "0.00"
    _ancho(ws, 24)

    ws = wb.create_sheet("Voluntarios")
    if voluntarios is None or voluntarios.empty:
        ws["A1"] = "Pendiente: ver entregas/taller-1/datos/voluntarios_plantilla.csv"
    else:
        _tabla(ws, 1, list(voluntarios.columns), voluntarios.astype(object).values.tolist())
    _ancho(ws, 18)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta
