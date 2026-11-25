"""Pipeline local, validación fase 1 (Excel y .py del grupo), Excel exportado y página."""

import datetime as dt
import shutil
import subprocess
from pathlib import Path

import openpyxl
import pytest

from roboadvisor.taller2.datos.informe import escribir_csv
from roboadvisor.taller2.pipeline import validacion
from roboadvisor.taller2.pipeline.procesar import DiaTES, dias_habiles, procesar
from roboadvisor.taller2.reportes.excel import generar_excel

from .conftest import REFERENCIAS


def test_dias_habiles():
    d = dias_habiles(dt.date(2026, 10, 2), dt.date(2026, 10, 6))
    assert d == [dt.date(2026, 10, 2), dt.date(2026, 10, 5), dt.date(2026, 10, 6)]


def test_procesar_marca_errores_y_encadena(informe_2oct):
    import dataclasses

    malo = dataclasses.replace(informe_2oct, fecha=dt.date(2026, 10, 1), total_nominal_mm=1)
    dias = procesar(
        [DiaTES(malo.fecha, "leido", malo), DiaTES(informe_2oct.fecha, "leido", informe_2oct)]
    )
    assert [d.estado for d in dias] == ["error_validacion", "ok"]


def test_update_tes_con_archivo_csv(tmp_path, informe_2oct):
    from roboadvisor.taller2.pipeline import update_tes

    ruta = tmp_path / "enunciado.csv"
    escribir_csv(informe_2oct, ruta)
    codigo = update_tes.main(
        ["--archivo", str(ruta), "--sin-supabase", "--exportar", str(tmp_path / "out")]
    )
    assert codigo == 0
    assert (tmp_path / "out" / "2026-10-02" / "resultado.csv").exists()


@pytest.mark.skipif(
    not (REFERENCIAS / "Libro-taller2.xlsx").exists(), reason="faltan las referencias del grupo"
)
def test_fase1_sin_pdf_compara_con_excel_y_py_del_grupo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(validacion, "CARPETA_EXPORTS", tmp_path)
    vacia = tmp_path / "pdfs"
    vacia.mkdir()
    codigo = validacion.main(["fase1", "--sin-descarga", "--carpeta", str(vacia)])
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    for c in ("C2", "C3a", "C3b", "C4a", "C5"):
        assert f"[PASA   ] {c}" in salida
    assert "$O$3" in salida  # el error de la columna L del Excel del grupo queda documentado
    assert (tmp_path / "validacion" / "fase1.html").exists()


def test_excel_exportado_tiene_formulas(tmp_path, resultado_2oct):
    ruta = generar_excel(resultado_2oct, tmp_path / "t2.xlsx")
    wb = openpyxl.load_workbook(ruta)
    assert wb.sheetnames[:4] == ["Parametros", "Resultados", "Flujos", "Curva"]
    rs = wb["Resultados"]
    assert rs["I2"].value.startswith("=XIRR(") and rs["H2"].value.startswith("=SUM(")
    assert wb["Parametros"]["B8"].value.startswith("=_xlfn.STDEV.S(")
    assert wb["Curva"].max_row == 10_951


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice no está instalado")
def test_excel_recalculado_coincide_con_python(tmp_path, resultado_2oct):
    ruta = generar_excel(resultado_2oct, tmp_path / "t2.xlsx")
    salida = tmp_path / "recalc"
    subprocess.run(
        [
            "soffice",
            "--headless",
            "--calc",
            "--convert-to",
            "xlsx",
            "--outdir",
            str(salida),
            str(ruta),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )
    wb = openpyxl.load_workbook(salida / "t2.xlsx", data_only=True)
    rs = wb["Resultados"]
    assert wb["Parametros"]["B9"].value == pytest.approx(resultado_2oct.calibracion.sse, rel=1e-9)
    for i, fila in resultado_2oct.tabla.iterrows():
        r = i + 2
        assert rs.cell(r, 8).value == pytest.approx(fila["precio_estimado"], abs=1e-9)
        assert rs.cell(r, 9).value == pytest.approx(fila["tir_observada"], abs=1e-9)
        assert rs.cell(r, 12).value == fila["senal"]


def test_pagina_publica_abre_sin_sesion_en_modo_mock(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("MOCK_DATA", "true")
    raiz = Path(__file__).resolve().parents[2]
    at = AppTest.from_file(str(raiz / "app" / "pages" / "4_T2_Curva_TES.py"), default_timeout=120)
    at.run()
    assert not at.exception
    assert any("Taller 2" in t.value for t in at.title)
    assert len(at.dataframe[0].value) == 29


def test_informe_markdown_del_taller2(informe_2oct, resultado_2oct, tmp_path):
    import datetime as dt

    from roboadvisor.taller2.core.analisis import sensibilidad, sensibilidad_tau
    from roboadvisor.taller2.reportes.informe import construir_markdown

    figs = {n: tmp_path / f"{n}.png" for n in ("curva", "spreads", "dv01")}
    papeles = informe_2oct.papeles()
    md = construir_markdown(
        resultado_2oct,
        sensibilidad(papeles, informe_2oct.fecha),
        figs,
        dt.date(2026, 11, 19),
        papeles,
        sensibilidad_tau(papeles, informe_2oct.fecha),
    )
    assert "13,55 %" in md and "0 comprar · 7 vender · 22 mantener" in md
    assert "NL/365" in md and "TCO364150627" in md
    assert "Cumplimiento del enunciado" not in md and "Esteban Palacio Londoño" in md
    assert "19 de noviembre de 2026" in md and "--fecha" in md
