"""Pipeline del Taller 2: informes de IRC → validación → curva Nelson-Siegel → Supabase.

Ejemplos:
    # Un día determinado (requisito del taller): betas, curva, TIR, decisión y DV01
    python -m roboadvisor.taller2.pipeline.update_tes --fecha 2026-10-02 --sin-supabase

    # Un archivo concreto (PDF/XLSX del IRC o el CSV del enunciado)
    python -m roboadvisor.taller2.pipeline.update_tes --archivo informe.pdf --sin-supabase

    # Rango (descarga lo que falte en data_local/tes/) y carga a Supabase
    python -m roboadvisor.taller2.pipeline.update_tes --desde 2026-10-05 --hasta 2026-11-13

    # Diario (GitHub Actions): últimos 15 días hábiles
    python -m roboadvisor.taller2.pipeline.update_tes --diario

Opciones del modelo: --umbral sigma|sigma_robusta|<pb>  --solo-sen  --ponderar-duracion  --tau
"""

import argparse
import datetime as dt
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ..config import ParametrosTES
from ..datos import informe as inf_mod
from .procesar import (
    CARPETA_EXPORTS,
    CARPETA_INFORMES,
    DiaTES,
    exportar_dia,
    obtener_informes,
    procesar,
    resumen,
)


def parametros_desde_args(a) -> ParametrosTES:
    p = ParametrosTES()
    umbral = a.umbral if a.umbral in ("sigma", "sigma_robusta") else float(a.umbral)
    return replace(
        p,
        tau=a.tau,
        umbral=umbral,
        usar_origen="SEN" if a.solo_sen else "todos",
        ponderacion="duracion" if a.ponderar_duracion else "ninguna",
    )


def agregar_opciones_modelo(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--tau", type=float, default=ParametrosTES.tau)
    ap.add_argument("--umbral", default="sigma", help="sigma | sigma_robusta | número en pb")
    ap.add_argument("--solo-sen", action="store_true", help="calibrar solo con tasas SEN")
    ap.add_argument("--ponderar-duracion", action="store_true")


def cargar_supabase(dias: list[DiaTES], params: ParametrosTES, modo: str, log=print) -> None:
    from roboadvisor.comun.cliente import cliente_servicio

    from ..datos.repositorio import RepositorioTES

    inicio = dt.datetime.now(dt.UTC)
    repo = RepositorioTES(cliente_servicio())
    cargados = 0
    for d in dias:
        if d.informe is None:
            continue
        repo.guardar_informe(d.informe, d.hallazgos, d.url)
        if d.resultado is not None and d.estado == "ok":
            repo.guardar_resultado(d.resultado, params)
            cargados += 1
    estados = pd.Series([d.estado for d in dias]).value_counts().to_dict()
    malos = sum(estados.get(e, 0) for e in ("error_validacion", "no_convergio", "error_lectura"))
    estado = "ok" if malos == 0 else ("parcial" if cargados else "error")
    repo.registrar_corrida(estado, modo, {"estados": estados, "cargados": cargados}, inicio)
    log(f"Supabase: {cargados} días con curva cargados (estado {estado}).")


def imprimir_dia(d: DiaTES) -> None:
    r = d.resultado
    c = r.calibracion
    print(f"\nInforme del {d.fecha:%d-%m-%Y} · {len(d.informe.filas)} papeles · {d.mensaje}")
    print(
        f"Betas: b0={c.betas.b0:.6f}  b1={c.betas.b1:.6f}  b2={c.betas.b2:.6f}  tau={c.tau}"
        f"  | SSE={c.sse:.6f}  RMSE={c.rmse:.4f}  ({c.n} papeles en la curva)"
    )
    print(f"Umbral: ±{r.umbral_pb:.2f} pb ({r.regla_umbral}) → {r.conteo_senales()}")
    for h in d.hallazgos:
        print(f"  [{h.codigo} {h.nivel}] {h.nemotecnico or ''} {h.mensaje}")
    cols = [
        "nemotecnico",
        "origen_tasa",
        "precio_sucio",
        "precio_estimado",
        "tir_observada",
        "tir_estimada",
        "spread_pb",
        "senal",
        "duracion_modificada",
        "dv01_cop",
    ]
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(r.tabla[cols].round(4).to_string(index=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Curva cero cupón TES (Nelson-Siegel) · Taller 2")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fecha", type=dt.date.fromisoformat)
    g.add_argument("--desde", type=dt.date.fromisoformat)
    g.add_argument("--archivo", type=Path, help="PDF/XLSX del IRC o CSV del enunciado")
    g.add_argument("--diario", action="store_true", help="últimos 15 días hábiles")
    ap.add_argument("--hasta", type=dt.date.fromisoformat, default=dt.date.today())
    ap.add_argument("--carpeta", type=Path, default=CARPETA_INFORMES)
    ap.add_argument("--sin-descarga", action="store_true", help="solo archivos de --carpeta")
    ap.add_argument("--sin-supabase", action="store_true", help="no cargar a Supabase")
    ap.add_argument("--exportar", type=Path, default=CARPETA_EXPORTS)
    agregar_opciones_modelo(ap)
    a = ap.parse_args(argv)
    params = parametros_desde_args(a)

    if a.archivo:
        inf = inf_mod.leer(a.archivo, a.fecha)
        dias = [DiaTES(inf.fecha, "leido", inf, mensaje=a.archivo.name)]
        modo = "manual"
    else:
        if a.fecha:
            desde = hasta = a.fecha
        elif a.diario:
            hasta = a.hasta
            desde = hasta - dt.timedelta(days=21)
        else:
            desde, hasta = a.desde, a.hasta
        dias = obtener_informes(desde, hasta, a.carpeta, descargar=not a.sin_descarga)
        modo = "diario" if a.diario else "manual"

    dias = procesar(dias, params)
    for d in dias:
        if d.estado == "ok":
            exportar_dia(d, a.exportar)
            if len(dias) == 1:
                imprimir_dia(d)
    print("\n" + resumen(dias).round(5).to_string(index=False))
    if not a.sin_supabase:
        cargar_supabase(dias, params, modo)
    malos = [d for d in dias if d.estado in ("error_validacion", "no_convergio", "error_lectura")]
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
