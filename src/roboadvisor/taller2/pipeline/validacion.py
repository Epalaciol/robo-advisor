"""Validación del Taller 2 en dos fases (docs/taller-2/09-validacion.md).

Fase 1 — "hasta el 2-oct": trae los informes de unos días antes del 2-oct-2026 y el propio 2-oct,
y verifica que el 2-oct dé lo mismo que la tabla del enunciado, el Excel del grupo
(Libro-taller2.xlsx) y el script del grupo (taller2_nelson_siegel.py).

Fase 2 — "el resto": trae del 5-oct en adelante, verifica continuidad de la curva día a día
y genera las gráficas (betas en el tiempo, tasas a 1/5/10 años, curvas superpuestas, decisiones).

    python -m roboadvisor.taller2.pipeline.validacion fase1 [--cargar]
    python -m roboadvisor.taller2.pipeline.validacion fase2 [--cargar]

Escribe exports/taller2/validacion/faseN.html y faseN.md. Código de salida 0 si todo pasa.
"""

import argparse
import dataclasses
import datetime as dt
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import ParametrosTES
from ..core.analisis import analizar
from ..core.flujos import flujos
from ..core.modelos import Betas
from ..core.nelson_siegel import precio, spot
from ..datos import informe as inf_mod
from .procesar import (
    CARPETA_EXPORTS,
    CARPETA_INFORMES,
    RAIZ,
    DiaTES,
    exportar_dia,
    obtener_informes,
    procesar,
    resumen,
)
from .update_tes import agregar_opciones_modelo, cargar_supabase, parametros_desde_args

FECHA_TALLER = dt.date(2026, 10, 2)
REFERENCIAS = RAIZ / "docs" / "taller-2" / "referencias"
FIXTURES = RAIZ / "tests" / "taller2" / "fixtures"
CSV_ENUNCIADO = FIXTURES / "tes_2026-10-02.csv"
EXCEL_GRUPO = REFERENCIAS / "Libro-taller2.xlsx"
PY_GRUPO = REFERENCIAS / "taller2_nelson_siegel.py"
EXCEL_PROFESOR = FIXTURES / "modelo_excel_2026-03-17.json"


@dataclass
class Chequeo:
    codigo: str
    descripcion: str
    estado: str  # PASA | FALLA | AVISO | OMITIDO
    detalle: str = ""
    tabla: pd.DataFrame | None = field(default=None, repr=False)


# --------------------------------------------------------------------------- comparaciones
def comparar_con_enunciado(dia: DiaTES) -> Chequeo:
    ref = inf_mod.leer_csv(CSV_ENUNCIADO)
    a = {f.nemotecnico: f for f in dia.informe.filas}
    b = {f.nemotecnico: f for f in ref.filas}
    faltan, sobran = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    difs = []
    campos = [
        "valor_nominal_mm",
        "cupon",
        "precio_limpio",
        "precio_sucio",
        "duracion",
        "tasa_pub",
        "origen_tasa",
        "tasa_prev",
        "origen_prev",
        "var_pb",
        "vencimiento",
    ]
    for n in sorted(set(a) & set(b)):
        for c in campos:
            x, y = getattr(a[n], c), getattr(b[n], c)
            igual = x == y if not isinstance(x, float) else abs(x - y) < 1e-9
            if not igual:
                difs.append({"nemotecnico": n, "campo": c, "informe": x, "enunciado": y})
    ok = not faltan and not sobran and not difs
    det = f"{len(a)} papeles leídos vs {len(b)} del enunciado"
    if faltan:
        det += f"; faltan {faltan}"
    if sobran:
        det += f"; sobran {sobran}"
    if difs:
        det += f"; {len(difs)} campos distintos"
    return Chequeo(
        "C2",
        "Tabla del 2-oct = tabla del enunciado",
        "PASA" if ok else "FALLA",
        det,
        pd.DataFrame(difs) if difs else None,
    )


def comparar_con_excel_grupo(dia: DiaTES) -> list[Chequeo]:
    import openpyxl

    if not EXCEL_GRUPO.exists():
        return [
            Chequeo("C3", "Comparación con Libro-taller2.xlsx", "OMITIDO", "no está el archivo")
        ]
    ws = openpyxl.load_workbook(EXCEL_GRUPO, data_only=True)["Hoja1"]
    filas = []
    for i in range(3, 3 + 60):
        nemo = ws[f"B{i}"].value
        if not isinstance(nemo, str) or not nemo.startswith("T"):
            break
        filas.append(
            {
                "nemotecnico": nemo,
                "precio_estimado_xl": ws[f"H{i}"].value,
                "tir_observada_xl": ws[f"I{i}"].value,
                "tir_estimada_xl": ws[f"J{i}"].value,
                "spread_pb_xl": ws[f"K{i}"].value,
                "decision_xl": ws[f"L{i}"].value,
                "dv01_xl": ws[f"Q{i}"].value,
            }
        )
    xl = pd.DataFrame(filas)
    umbral_xl = ws["N3"].value
    betas_xl = np.array([ws["B35"].value, ws["C35"].value, ws["D35"].value], dtype=float)
    r = dia.resultado
    t = r.tabla.merge(xl, on="nemotecnico", how="outer", indicator=True)
    out = []
    b = np.array(r.calibracion.betas.como_tupla())
    db = float(np.max(np.abs(b - betas_xl)))
    out.append(
        Chequeo(
            "C3a",
            "Betas = Excel del grupo (B35:D35)",
            "PASA" if db < 1e-6 else "FALLA",
            f"máx |Δβ| = {db:.2e}; Python {np.round(b, 6)} · Excel {np.round(betas_xl, 6)}",
        )
    )
    solo = t[t["_merge"] != "both"]
    comparaciones = [
        ("precio_estimado", "precio_estimado_xl", 1e-6, "precio estimado"),
        ("tir_observada", "tir_observada_xl", 1e-6, "TIR observada (XIRR)"),
        ("tir_estimada", "tir_estimada_xl", 1e-6, "TIR estimada (XIRR)"),
        ("spread_pb", "spread_pb_xl", 0.01, "diferencia en pb"),
    ]
    det = []
    peor = 0.0
    for py, x, tol, nombre in comparaciones:
        d = float((t[py] - pd.to_numeric(t[x])).abs().max())
        det.append(f"{nombre}: {d:.2e}")
        peor = max(peor, d / tol)
    d_dv01 = float(((t["dv01_excel_cop"] - t["dv01_xl"]) / t["dv01_xl"]).abs().max())
    det.append(f"DV01 variante Excel (rel.): {d_dv01:.2e}")
    ok = peor <= 1 and d_dv01 < 1e-6 and solo.empty
    out.append(
        Chequeo(
            "C3b",
            "Precios, TIR, spreads y DV01 = Excel del grupo",
            "PASA" if ok else "FALLA",
            "; ".join(det),
        )
    )
    # Decisiones: el Excel compara contra $O$3 (vacía) en vez de N3 → umbral 0
    du = abs(r.umbral_pb - umbral_xl) if r.regla_umbral == "sigma" else None
    esperado_xl = np.where(
        t["spread_pb_xl"] > 0, "Comprar", np.where(t["spread_pb_xl"] < 0, "Vender", "Mantener")
    )
    bug = bool((t["decision_xl"] == esperado_xl).all())
    corregido = np.where(
        t["spread_pb_xl"] > umbral_xl,
        "Comprar",
        np.where(t["spread_pb_xl"] < -umbral_xl, "Vender", "Mantener"),
    )
    iguales = bool((t["senal"] == corregido).all()) if r.regla_umbral == "sigma" else None
    texto = (
        f"Umbral 1σ: Python {r.umbral_pb:.4f} pb · Excel N3 {umbral_xl:.4f} pb. "
        + (
            "La columna L del Excel compara contra $O$3 (vacía) → umbral 0: "
            f"{int((t['decision_xl'] == 'Comprar').sum())} Comprar / "
            f"{int((t['decision_xl'] == 'Vender').sum())} Vender / 0 Mantener. "
            if bug
            else ""
        )
        + ("Con N3 (corregido) las decisiones coinciden con Python en los 29." if iguales else "")
    )
    estado = "PASA" if (iguales and du is not None and du < 1e-6) else "AVISO"
    out.append(Chequeo("C3c", "Decisión comprar/vender/mantener vs Excel", estado, texto))
    tabla = t[
        [
            "nemotecnico",
            "spread_pb",
            "spread_pb_xl",
            "senal",
            "decision_xl",
            "dv01_cop",
            "dv01_excel_cop",
            "dv01_xl",
        ]
    ].copy()
    tabla["decision_xl_corregida"] = corregido
    out[-1].tabla = tabla
    return out


def _cargar_py_grupo():
    spec = importlib.util.spec_from_file_location("taller2_grupo", PY_GRUPO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def comparar_con_py_grupo(dia: DiaTES, pdf: Path | None) -> list[Chequeo]:
    if not PY_GRUPO.exists():
        return [Chequeo("C4", "Comparación con taller2_nelson_siegel.py", "OMITIDO", "no está")]
    mod = _cargar_py_grupo()
    out = []
    # (a) Motor: mismos datos (los del informe leído por nosotros) en el .py
    df = pd.DataFrame(
        [
            {
                "vencimiento": f.vencimiento,
                "nemotecnico": f.nemotecnico,
                "nominal": f.valor_nominal_mm,
                "cupon": f.cupon,
                "limpio": f.precio_limpio,
                "sucio": f.precio_sucio,
                "duracion_inf": f.duracion,
                "tasa_inf": f.tasa_pub * 100,
                "mercado": f.origen_tasa,
            }
            for f in dia.informe.filas
        ]
    )
    original = mod.leer_informe
    mod.leer_informe = lambda ruta, fecha=None: (df.copy(), dia.fecha)
    try:
        m = mod.correr_modelo("datos-en-memoria", dia.fecha)
    finally:
        mod.leer_informe = original
    res = m["resultados"].rename(columns={"decision": "decision_py"})
    t = dia.resultado.tabla.merge(res, on="nemotecnico", suffixes=("", "_py"))
    db = float(
        np.max(
            np.abs(np.array(m["betas"]) - np.array(dia.resultado.calibracion.betas.como_tupla()))
        )
    )
    d_tir = float(
        max(
            (t["tir_observada"] - t["tir_observada_py"]).abs().max(),
            (t["tir_estimada"] - t["tir_estimada_py"]).abs().max(),
        )
    )
    d_dv = float(((t["dv01_cop"] - t["dv01_revaluacion"]) / t["dv01_cop"]).abs().max())
    iguales = bool((t["senal"] == t["decision_py"]).all())
    ok = db < 1e-5 and d_tir < 1e-6 and d_dv < 1e-6 and iguales and len(t) == len(df)
    out.append(
        Chequeo(
            "C4a",
            "Motor = .py del grupo (mismos datos)",
            "PASA" if ok else "FALLA",
            f"máx |Δβ| {db:.1e} (Nelder-Mead vs least_squares); máx |ΔTIR| {d_tir:.1e}; "
            f"DV01 rel. {d_dv:.1e}; decisiones iguales: {iguales}; umbral .py {m['umbral']:.4f}",
        )
    )
    # (b) Lector de PDF del .py: ¿lee todas las filas?
    if pdf is None:
        out.append(Chequeo("C4b", "Lector de PDF del .py", "OMITIDO", "no hay PDF del 2-oct"))
    else:
        try:
            df_py, f_py = mod.leer_pdf(pdf)
            faltan = sorted(set(df["nemotecnico"]) - set(df_py["nemotecnico"]))
            estado = "PASA" if not faltan and f_py == dia.fecha else "AVISO"
            out.append(
                Chequeo(
                    "C4b",
                    "Lector de PDF del .py lee los mismos papeles",
                    estado,
                    f".py leyó {len(df_py)} de {len(df)}; le faltan {faltan or 'ninguno'}",
                )
            )
        except Exception as e:  # noqa: BLE001
            out.append(Chequeo("C4b", "Lector de PDF del .py", "AVISO", f"falló: {e}"))
    return out


def chequeo_convencion_mercado(dia: DiaTES, tol_pb: float = 0.1) -> Chequeo:
    """Con NL/365 la TIR del precio sucio publicado debe dar la tasa SEN de IRC."""
    t = dia.resultado.tabla
    sen = t[t["origen_tasa"] == "SEN"]
    d = float(((sen["tir_observada"] - sen["tasa_informe"]) / 1e-4).abs().max())
    return Chequeo(
        "C8",
        f"TIR del precio = tasa SEN publicada (conteo {dia.resultado.conteo_dias})",
        "PASA" if d <= tol_pb else "AVISO",
        f"{len(sen)} papeles SEN; máx |Δ| = {d:.3f} pb (tolerancia {tol_pb} pb)",
    )


def comparar_con_excel_profesor() -> Chequeo:
    datos = json.loads(EXCEL_PROFESOR.read_text())
    b = Betas(*datos["betas"])
    fecha = dt.date.fromisoformat(datos["fecha_calculo"])
    peor_sano, peor_roto = 0.0, 0.0
    for p in datos["papeles"]:
        f = flujos(dt.date.fromisoformat(p["vencimiento"]), p["cupon"], fecha, conteo="Act/365")
        pe = precio(f, b, datos["tau"])
        if p["excel_roto"]:
            peor_roto = max(peor_roto, abs(pe - p["precio_estimado_correcto"]))
        else:
            peor_sano = max(peor_sano, abs(pe - p["precio_estimado_excel"]))
    ok = peor_sano < 1e-8 and peor_roto < 1e-8
    return Chequeo(
        "C5",
        "Precio = Excel del profesor (17-mar, 24 papeles sanos + 2 corregidos)",
        "PASA" if ok else "FALLA",
        f"máx error {peor_sano:.1e} / {peor_roto:.1e}",
    )


def chequeo_cobertura(dias: list[DiaTES]) -> Chequeo:
    r = resumen(dias)
    malos = r[r["estado"].isin(["error_validacion", "no_convergio", "error_lectura"])]
    no_pub = r[r["estado"] == "no_publicado"]["fecha"].tolist()
    sin_texto = r[r["estado"] == "sin_texto"]["fecha"].tolist()
    det = f"{int((r['estado'] == 'ok').sum())} días ok de {len(r)} hábiles"
    if sin_texto:
        det += f"; PDF sin texto extraíble, día omitido: {[str(x) for x in sin_texto]}"
    if no_pub:
        det += f"; sin informe (festivo o no publicado): {[str(x) for x in no_pub]}"
    if not malos.empty:
        det += f"; con error: {malos[['fecha', 'estado', 'mensaje']].to_dict('records')}"
    return Chequeo(
        "C1",
        "Cada día hábil: leído, validado y calibrado",
        "FALLA"
        if not malos.empty or not (r["estado"] == "ok").any()
        else ("AVISO" if sin_texto else "PASA"),
        det,
        r,
    )


def chequeo_continuidad(dias: list[DiaTES], salto_pb=50.0, rmse_max=1.5) -> Chequeo:
    ok = [d for d in dias if d.estado == "ok"]
    filas, avisos = [], []
    for d in ok:
        c = d.resultado.calibracion
        fila = {"fecha": d.fecha, "rmse": c.rmse}
        for plazo in (1, 5, 10):
            fila[f"spot_{plazo}a"] = spot(float(plazo), c.betas, c.tau)
        filas.append(fila)
    df = pd.DataFrame(filas)
    if len(df) >= 2:
        for plazo in (1, 5, 10):
            salto = df[f"spot_{plazo}a"].diff().abs() * 1e4
            for i in salto.index[salto > salto_pb]:
                avisos.append(f"{df.loc[i, 'fecha']}: spot {plazo}a cambió {salto[i]:.0f} pb")
    for _, f in df[df["rmse"] > rmse_max].iterrows() if not df.empty else []:
        avisos.append(f"{f['fecha']}: RMSE {f['rmse']:.2f} > {rmse_max}")
    return Chequeo(
        "C6",
        f"Continuidad: saltos diarios < {salto_pb:.0f} pb y RMSE < {rmse_max}",
        "PASA" if not avisos else "AVISO",
        "; ".join(avisos) or "sin saltos",
        df,
    )


# ---------------------------------------------------------------------------------- reporte
def escribir_reporte(nombre: str, titulo: str, chequeos: list[Chequeo], figuras, dias) -> Path:
    carpeta = CARPETA_EXPORTS / "validacion"
    carpeta.mkdir(parents=True, exist_ok=True)
    md = [
        f"# {titulo}",
        "",
        f"Generado: {dt.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "| Código | Chequeo | Estado | Detalle |",
        "|---|---|---|---|",
    ]
    md += [f"| {c.codigo} | {c.descripcion} | **{c.estado}** | {c.detalle} |" for c in chequeos]
    (carpeta / f"{nombre}.md").write_text("\n".join(md), encoding="utf-8")
    colores = {"PASA": "#2E7D32", "FALLA": "#C62828", "AVISO": "#B26A00", "OMITIDO": "#777"}
    partes = [
        "<html><head><meta charset='utf-8'><title>" + titulo + "</title>",
        "<style>body{font-family:system-ui;margin:24px;max-width:1200px} table{border-collapse:"
        "collapse;font-size:13px} td,th{border:1px solid #ddd;padding:4px 8px}</style></head>"
        f"<body><h1>{titulo}</h1><table><tr><th>Código</th><th>Chequeo</th><th>Estado</th>"
        "<th>Detalle</th></tr>",
    ]
    for c in chequeos:
        partes.append(
            f"<tr><td>{c.codigo}</td><td>{c.descripcion}</td><td style='color:"
            f"{colores[c.estado]};font-weight:bold'>{c.estado}</td><td>{c.detalle}</td></tr>"
        )
    partes.append("</table>")
    for i, (t, fig) in enumerate(figuras):
        partes.append(f"<h2>{t}</h2>")
        partes.append(fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    for c in chequeos:
        if c.tabla is not None and not c.tabla.empty:
            partes.append(f"<h3>{c.codigo} · detalle</h3>")
            partes.append(c.tabla.round(6).to_html(index=False))
    partes.append("<h2>Resumen por día</h2>" + resumen(dias).round(6).to_html(index=False))
    partes.append("</body></html>")
    ruta = carpeta / f"{nombre}.html"
    ruta.write_text("\n".join(partes), encoding="utf-8")
    return ruta


# ------------------------------------------------------------------------------------- fases
def fase1(a, params: ParametrosTES) -> int:
    from ..reportes import graficas

    print(f"FASE 1 · {a.desde} → {a.hasta} (validación contra el 2-oct)")
    dias = obtener_informes(a.desde, a.hasta, a.carpeta, descargar=not a.sin_descarga)
    if FECHA_TALLER <= a.hasta and not any(d.fecha == FECHA_TALLER and d.informe for d in dias):
        print("  ! No hay PDF del 2-oct: se usa la tabla del enunciado (CSV) para ese día")
        dias = [d for d in dias if d.fecha != FECHA_TALLER]
        inf = inf_mod.leer_csv(CSV_ENUNCIADO)
        dias.append(DiaTES(FECHA_TALLER, "leido", inf, mensaje="CSV del enunciado"))
    dias = procesar(dias, params)
    for d in dias:
        if d.estado == "ok":
            exportar_dia(d)
    chequeos = [chequeo_cobertura(dias)]
    d2 = next((d for d in dias if d.fecha == FECHA_TALLER and d.estado == "ok"), None)
    figuras = []
    if d2 is None:
        chequeos.append(Chequeo("C2", "Día 2-oct procesado", "FALLA", "no se pudo procesar"))
    else:
        pdf = None if d2.informe.via == "csv" else a.carpeta / f"informe_{FECHA_TALLER}.pdf"
        if pdf is not None and not pdf.exists():
            pdf = next((p for p in a.carpeta.glob("*.pdf") if d2.informe.fuente == p.name), None)
        chequeos.append(comparar_con_enunciado(d2))
        chequeos.append(chequeo_convencion_mercado(d2))
        # El Excel y el .py del grupo cuentan días calendario (Act/365, como el Excel del profesor):
        # para compararse con ellos se recalcula el 2-oct con esa convención.
        d2_act = dataclasses.replace(
            d2,
            resultado=analizar(
                d2.informe.papeles(), d2.fecha, dataclasses.replace(params, conteo_dias="Act/365")
            ),
        )
        chequeos += comparar_con_excel_grupo(d2_act)
        chequeos += comparar_con_py_grupo(d2_act, pdf)
        figuras += [
            ("Curva cero cupón 2-oct-2026 y TIR observadas", graficas.figura_curva(d2.resultado)),
            ("Spread TIR observada − estimada (pb)", graficas.figura_spreads(d2.resultado)),
        ]
    chequeos.append(comparar_con_excel_profesor())
    chequeos.append(chequeo_continuidad(dias))
    ok_dias = [d for d in dias if d.estado == "ok"]
    if len(ok_dias) > 1:
        figuras.append(
            ("Curvas de los días de la fase 1", graficas.figura_curvas_superpuestas(ok_dias))
        )
    ruta = escribir_reporte(
        "fase1", "Taller 2 · Validación fase 1 (hasta el 2-oct-2026)", chequeos, figuras, dias
    )
    return _cerrar(chequeos, ruta, a, dias, params, "fase1")


def fase2(a, params: ParametrosTES) -> int:
    from ..reportes import graficas

    print(f"FASE 2 · {a.desde} → {a.hasta} (resto de días y gráficas)")
    dias = obtener_informes(a.desde, a.hasta, a.carpeta, descargar=not a.sin_descarga)
    previos = None
    f1 = CARPETA_EXPORTS / FECHA_TALLER.isoformat() / "parametros.csv"
    if f1.exists():  # encadenar con el 2-oct de la fase 1
        p = pd.read_csv(f1).set_index("parametro")["valor"]
        previos = Betas(float(p["b0"]), float(p["b1"]), float(p["b2"]))
    dias = procesar(dias, params, previos)
    for d in dias:
        if d.estado == "ok":
            exportar_dia(d)
    ok_dias = [d for d in dias if d.estado == "ok"]
    chequeos = [chequeo_cobertura(dias), chequeo_continuidad(dias)]
    figuras = []
    if ok_dias:
        figuras = [
            ("Betas en el tiempo", graficas.figura_betas_tiempo(ok_dias)),
            ("Tasas spot a 1, 5 y 10 años", graficas.figura_spot_plazos(ok_dias)),
            ("Curvas superpuestas", graficas.figura_curvas_superpuestas(ok_dias)),
            ("Decisiones por papel y día", graficas.figura_mapa_senales(ok_dias)),
            (
                f"Curva del último día ({ok_dias[-1].fecha})",
                graficas.figura_curva(ok_dias[-1].resultado),
            ),
        ]
        chequeos.append(Chequeo("C7", "Gráficas generadas", "PASA", f"{len(figuras)} gráficas"))
    ruta = escribir_reporte(
        "fase2", "Taller 2 · Validación fase 2 (del 5-oct en adelante)", chequeos, figuras, dias
    )
    return _cerrar(chequeos, ruta, a, dias, params, "fase2")


def _cerrar(chequeos, ruta, a, dias, params, modo) -> int:
    print()
    for c in chequeos:
        print(f"  [{c.estado:7}] {c.codigo} {c.descripcion} — {c.detalle}")
    falla = any(c.estado == "FALLA" for c in chequeos)
    print(f"\nReporte: {ruta}")
    if a.cargar:
        if falla:
            print("No se carga a Supabase: hay chequeos que FALLAN.")
        else:
            cargar_supabase(dias, params, modo)
            verificar_supabase(dias)
    return 1 if falla else 0


def verificar_supabase(dias: list[DiaTES]) -> None:
    """Relee lo cargado con el cliente anon (como la página pública) y compara."""
    from roboadvisor.comun.cliente import cliente_anon

    from ..datos.repositorio import RepositorioTES

    repo = RepositorioTES(cliente_anon())
    fechas = set(repo.fechas())
    esperadas = {d.fecha for d in dias if d.estado == "ok"}
    faltan = sorted(esperadas - fechas)
    print(
        f"Supabase (anon): {len(esperadas & fechas)}/{len(esperadas)} días visibles"
        + (f"; faltan {faltan}" if faltan else "")
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validación del Taller 2 en dos fases")
    ap.add_argument("fase", choices=["fase1", "fase2"])
    ap.add_argument("--desde", type=dt.date.fromisoformat)
    ap.add_argument("--hasta", type=dt.date.fromisoformat)
    ap.add_argument("--carpeta", type=Path, default=CARPETA_INFORMES)
    ap.add_argument("--sin-descarga", action="store_true")
    ap.add_argument("--cargar", action="store_true", help="si todo pasa, cargar a Supabase")
    agregar_opciones_modelo(ap)
    a = ap.parse_args(argv)
    if a.fase == "fase1":
        a.desde = a.desde or dt.date(2026, 9, 21)
        a.hasta = a.hasta or FECHA_TALLER
    else:
        a.desde = a.desde or dt.date(2026, 10, 5)
        a.hasta = a.hasta or dt.date.today()
    params = parametros_desde_args(a)
    return (fase1 if a.fase == "fase1" else fase2)(a, params)


if __name__ == "__main__":
    sys.exit(main())
