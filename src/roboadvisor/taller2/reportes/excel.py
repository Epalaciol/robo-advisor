"""Excel del Taller 2 con fórmulas vivas (sigue la lógica del Excel del profesor, corregida).

Hojas:
- Parametros: β0, β1, β2, τ, nominal DV01, umbral y la celda SSE (lista para Solver:
  minimizar Parametros!B9 cambiando B3:B5, sin restringir el signo).
- Resultados: un papel por fila; precio estimado, TIR observada y estimada (XIRR), diferencia
  en pb, decisión, duración, convexidad y DV01 por $1.000 millones.
- Flujos: bloque por papel (fecha de valoración con −precio + flujos), tasa spot, factor de
  descuento y valor presente con fórmulas; de aquí salen el precio estimado y las XIRR.
  Conteo NL/365 (mercado de TES): Días = fecha − valoración − 29 de febrero del período. Como
  XIRR cuenta días calendario, se aplica sobre la "fecha ajustada" = valoración + Días, así XIRR
  devuelve la TIR en NL/365 (con Act/365 la fecha ajustada es la misma fecha del flujo).
- Curva: 1 a 10.950 días con la fórmula Nelson-Siegel.
- Sensibilidad (opcional): tabla de valores.
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from ..config import NOMINAL_DV01
from ..core.flujos import bisiestos_entre

NEGRITA = Font(bold=True)
ENCABEZADO = PatternFill("solid", fgColor="DDE4F0")
ENTRADA = PatternFill("solid", fgColor="FFF4CC")


def _spot(celda_t: str) -> str:
    b0, b1, b2, tau = "Parametros!$B$3", "Parametros!$B$4", "Parametros!$B$5", "Parametros!$B$6"
    x = f"({celda_t}/{tau})"
    carga = f"((1-EXP(-{x}))/{x})"
    return f"={b0}+{b1}*{carga}+{b2}*({carga}-EXP(-{x}))"


def _encabezado(ws, fila: int, titulos: list[str]) -> None:
    for j, t in enumerate(titulos, start=1):
        c = ws.cell(fila, j, t)
        c.font = NEGRITA
        c.fill = ENCABEZADO


def generar_excel(resultado, ruta: str | Path, sensibilidad: pd.DataFrame | None = None) -> Path:
    r = resultado
    c = r.calibracion
    wb = Workbook()

    # ------------------------------------------------------------------ Parametros
    p = wb.active
    p.title = "Parametros"
    filas = [
        ("Fecha de valoración", r.fecha),
        ("β0", c.betas.b0),
        ("β1", c.betas.b1),
        ("β2", c.betas.b2),
        ("τ (fijo)", c.tau),
        ("Nominal DV01 (COP) = $1.000 millones", NOMINAL_DV01),
        ("Umbral decisión (pb)", r.umbral_pb),
        ("SSE = Σ (sucio − estimado)²", None),
        ("RMSE", None),
        ("Regla del umbral", r.regla_umbral),
        ("Papeles usados en la curva", c.usar_origen),
        ("Conteo de días", r.conteo_dias),
    ]
    for i, (k, v) in enumerate(filas, start=2):
        p.cell(i, 1, k).font = NEGRITA
        p.cell(i, 2, v)
    for celda in ("B3", "B4", "B5", "B6", "B8"):
        p[celda].fill = ENTRADA
    p["B2"].number_format = "yyyy-mm-dd"
    p["D3"] = "Solver: minimizar B9 cambiando B3:B5 (sin restringir a no negativos)."
    p["D8"] = "Umbral = 1 desviación estándar de las diferencias (STDEV.S), editable."
    p.column_dimensions["A"].width = 38
    p.column_dimensions["B"].width = 18

    # ------------------------------------------------------------------ Flujos
    fl = wb.create_sheet("Flujos")
    _encabezado(
        fl,
        1,
        [
            "Bono",
            "Nemotécnico",
            "Fecha",
            "Flujo",
            "Días",
            "Años",
            "Tasa spot",
            "Factor desc.",
            "Valor presente",
            "Valores XIRR obs.",
            "Valores XIRR est.",
            "29 de febrero en el período",
            "Fecha ajustada (XIRR)",
        ],
    )
    nl = r.conteo_dias == "NL/365"
    t = r.tabla.reset_index(drop=True)
    fila = 2
    bloques = {}
    n_res = len(t)
    for i, papel in t.iterrows():
        fr = i + 2  # fila del papel en Resultados
        ff = r.flujos[r.flujos["bono"] == papel["bono"]]
        inicio = fila
        fl.cell(fila, 1, int(papel["bono"]))
        fl.cell(fila, 2, papel["nemotecnico"])
        fl.cell(fila, 3, "=Parametros!$B$2").number_format = "yyyy-mm-dd"
        fl.cell(fila, 10, f"=-Resultados!F{fr}")
        fl.cell(fila, 11, f"=-Resultados!H{fr}")
        fl.cell(fila, 13, "=Parametros!$B$2").number_format = "yyyy-mm-dd"
        fila += 1
        for _, f in ff.iterrows():
            fl.cell(fila, 1, int(papel["bono"]))
            fl.cell(fila, 2, papel["nemotecnico"])
            fl.cell(
                fila, 3, pd.Timestamp(f["fecha_flujo"]).to_pydatetime()
            ).number_format = "yyyy-mm-dd"
            fl.cell(fila, 4, float(f["flujo"]))
            fecha_f = pd.Timestamp(f["fecha_flujo"]).date()
            fl.cell(fila, 12, bisiestos_entre(r.fecha, fecha_f) if nl else 0)
            fl.cell(fila, 5, f"=C{fila}-Parametros!$B$2-L{fila}")
            fl.cell(fila, 13, f"=Parametros!$B$2+E{fila}").number_format = "yyyy-mm-dd"
            fl.cell(fila, 6, f"=E{fila}/365")
            fl.cell(fila, 7, _spot(f"F{fila}"))
            fl.cell(fila, 8, f"=1/(1+G{fila})^F{fila}")
            fl.cell(fila, 9, f"=D{fila}*H{fila}")
            fl.cell(fila, 10, f"=D{fila}")
            fl.cell(fila, 11, f"=D{fila}")
            fila += 1
        bloques[i] = (inicio, fila - 1)
        fila += 1  # fila en blanco entre papeles

    # ------------------------------------------------------------------ Resultados
    rs = wb.create_sheet("Resultados", 1)
    _encabezado(
        rs,
        1,
        [
            "Nemotécnico",
            "Vencimiento",
            "Origen tasa",
            "Cupón (%)",
            "Precio limpio",
            "Precio sucio",
            "Duración informe",
            "Precio estimado",
            "TIR observada",
            "TIR estimada",
            "Dif. (pb)",
            "Decisión",
            "Error²",
            "Duración Macaulay",
            "Duración modificada",
            "Convexidad",
            "DV01 por $1.000 millones (COP)",
            "DV01 revaluación (COP)",
        ],
    )
    for i, papel in t.iterrows():
        fr = i + 2
        a, b = bloques[i]
        rs.cell(fr, 1, papel["nemotecnico"])
        rs.cell(
            fr, 2, pd.Timestamp(papel["vencimiento"]).to_pydatetime()
        ).number_format = "yyyy-mm-dd"
        rs.cell(fr, 3, papel["origen_tasa"])
        rs.cell(fr, 4, float(papel["cupon"]))
        rs.cell(fr, 5, float(papel["precio_limpio"]))
        rs.cell(fr, 6, float(papel["precio_sucio"]))
        rs.cell(
            fr, 7, None if pd.isna(papel["duracion_informe"]) else float(papel["duracion_informe"])
        )
        rs.cell(fr, 8, f"=SUM(Flujos!I{a + 1}:I{b})")
        rs.cell(fr, 9, f"=XIRR(Flujos!J{a}:J{b},Flujos!M{a}:M{b})")
        rs.cell(fr, 10, f"=XIRR(Flujos!K{a}:K{b},Flujos!M{a}:M{b})")
        rs.cell(fr, 11, f"=(I{fr}-J{fr})*10000")
        rs.cell(
            fr,
            12,
            f'=IF(K{fr}>Parametros!$B$8,"Comprar",IF(K{fr}<-Parametros!$B$8,"Vender","Mantener"))',
        )
        rs.cell(fr, 13, f"=(F{fr}-H{fr})^2")
        rs.cell(fr, 14, float(papel["duracion_macaulay"]))
        rs.cell(fr, 15, f"=N{fr}/(1+I{fr})")
        rs.cell(fr, 16, float(papel["convexidad"]))
        rs.cell(fr, 17, f"=O{fr}*F{fr}/100*Parametros!$B$7*0.0001")
        rs.cell(fr, 18, float(papel["dv01_cop"]))
        for col, fmt in (
            (9, "0.0000%"),
            (10, "0.0000%"),
            (11, "0.00"),
            (17, "#,##0"),
            (18, "#,##0"),
        ):
            rs.cell(fr, col).number_format = fmt
    ultima = n_res + 1
    p["B8"] = (
        f"=_xlfn.STDEV.S(Resultados!K2:K{ultima})" if r.regla_umbral == "sigma" else r.umbral_pb
    )
    p["B9"] = f"=SUM(Resultados!M2:M{ultima})"
    p["B10"] = f"=SQRT(B9/{n_res})"
    for col in range(1, 19):
        rs.column_dimensions[get_column_letter(col)].width = 15
    rs.freeze_panes = "B2"

    # ------------------------------------------------------------------ Curva
    cv = wb.create_sheet("Curva")
    _encabezado(cv, 1, ["Días", "Años", "Tasa spot"])
    for d in range(1, 10_951):
        fila = d + 1
        cv.cell(fila, 1, d)
        cv.cell(fila, 2, f"=A{fila}/365")
        cv.cell(fila, 3, _spot(f"B{fila}"))

    if sensibilidad is not None:
        sh = wb.create_sheet("Sensibilidad")
        _encabezado(sh, 1, list(sensibilidad.columns))
        for i, fila_s in enumerate(sensibilidad.itertuples(index=False), start=2):
            for j, v in enumerate(fila_s, start=1):
                sh.cell(i, j, v if not isinstance(v, float) else float(v))

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta
