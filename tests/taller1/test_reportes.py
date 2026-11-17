"""Entregables del Taller 1 (caso, Excel y markdown del informe) con la instantánea local."""

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from roboadvisor.taller1.reportes.caso import UNIVERSO_REFERENCIA, calcular_caso
from roboadvisor.taller1.reportes.excel import generar_excel
from roboadvisor.taller1.reportes.informe import construir_markdown

DATOS = Path(__file__).resolve().parents[2] / "data_local" / "taller1"
pytestmark = pytest.mark.skipif(not (DATOS / "precios.csv").exists(), reason="sin instantánea")


@pytest.fixture(scope="module")
def caso():
    precios = (
        pd.read_csv(DATOS / "precios.csv", parse_dates=["fecha"])
        .pivot(index="fecha", columns="ticker", values="adj_close")
        .sort_index()
    )
    return calcular_caso(precios, float(pd.read_csv(DATOS / "rf.csv")["tasa_anual"].iloc[-1]))


def test_caso_tiene_11_activos_y_pesos_validos(caso):
    assert len(UNIVERSO_REFERENCIA) == 11
    assert caso.tangente.w.sum() == pytest.approx(1.0, abs=1e-6)
    assert (caso.tangente.w >= -1e-9).all() and (caso.tangente.w <= caso.params.w_max + 1e-6).all()
    assert list(caso.escenarios["a"]) == [8, 6, 4, 3, 1]
    assert (caso.escenarios["y"].between(0, 1)).all()


def test_excel_y_markdown_se_generan(caso, tmp_path):
    ruta = generar_excel(caso, tmp_path / "t1.xlsx")
    wb = load_workbook(ruta)
    assert {"Resumen", "Portafolio completo", "Betas y duration", "Voluntarios"} <= set(
        wb.sheetnames
    )
    assert wb["Resumen"]["B6"].value == pytest.approx(caso.rf)  # las fórmulas apuntan a esta celda
    assert wb["Resumen"]["B9"].value == pytest.approx(caso.tangente.sharpe)
    figs = {k: tmp_path / f"{k}.png" for k in ("frontera", "pesos", "completo")}
    md = construir_markdown(caso, figs, None, dt.date(2026, 11, 16))
    assert "Paso 5" in md and "Pendiente de completar" in md


def test_selecciones_por_perfil_a_menor_a_mas_riesgo_y_retorno(caso):
    from roboadvisor.taller1.data.semillas import leer_catalogo
    from roboadvisor.taller1.reportes.caso import selecciones_por_perfil

    sel = selecciones_por_perfil(caso.precios, leer_catalogo(), caso.rf, caso.params)
    assert [x.a for x in sel] == [8, 6, 4, 3, 1]
    assert all(len(x.tickers) == 11 for x in sel)
    assert sel[-1].vol_media > sel[0].vol_media and sel[-1].ret_medio > sel[0].ret_medio
