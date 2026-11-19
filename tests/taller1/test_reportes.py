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
    assert {"Resumen", "Portafolio completo", "Composición completa", "Encuestas"} <= set(
        wb.sheetnames
    )
    assert wb["Resumen"]["B6"].value == pytest.approx(caso.rf)  # las fórmulas apuntan a esta celda
    assert wb["Resumen"]["B9"].value == pytest.approx(caso.tangente.sharpe)
    claves = ("frontera", "pesos", "completo", "correlaciones", "desempeno", "indiferencia")
    figs = {k: tmp_path / f"{k}.png" for k in (*claves, "composicion")}
    md = construir_markdown(caso, figs, None, dt.date(2026, 11, 16))
    assert "Resumen ejecutivo" in md and "Pendiente de completar" in md
    assert "Cumplimiento del enunciado" not in md and "§" not in md
    assert "Sebastian Duarte Uran" in md
    assert "Acceso de administrador" in md and "admin@mft-investments.app" in md
    assert "se envía en el correo" in md  # la clave nunca va en el PDF
    assert "valor real de y*" in md  # sección del tope de 100 %


def test_seccion_voluntarios_con_datos_avisa_rangos_faltantes(caso):
    from roboadvisor.taller1.reportes.informe import seccion_voluntarios

    v = pd.DataFrame(
        [
            {"alias": "V1", "rango_edad": "25-34", "q1": "b", "q2a": "b", "q2b": "c", "q2c": "c",
             "q3": "c", "q4": "c", "q5": "a", "q6": "c", "q7": "c", "ocupacion": "Empleado/a",
             "activos_elegidos": "SPY, EFA", "y_guardado": "1.0"},
            {"alias": "V2", "rango_edad": "35-44", "q1": "a", "q2a": "b", "q2b": "b", "q2c": "a",
             "q3": "a", "q4": "c", "q5": "c", "q6": "a", "q7": "b", "ocupacion": "",
             "activos_elegidos": "", "y_guardado": ""},
        ]
    )  # fmt: skip
    md = seccion_voluntarios(caso, v)
    assert "V1" in md and "V2" in md and "Ocupación" in md and "Puntaje" in md
    assert "45-54, 55-64, 65-74" in md  # el enunciado pide uno por rango
    assert "Pendiente de completar" in seccion_voluntarios(caso, None)


def test_escenarios_sin_tope_y_optimo_sin_apalancamiento(caso):
    from roboadvisor.taller1.reportes.caso import escenarios_extendidos, optimo_sin_apalancamiento

    e = escenarios_extendidos(caso)
    t = caso.tangente
    # sin tope: y* fórmula, préstamo = y* − 1 y U* = rf + Sharpe²/(2A)
    assert (e["prestamo_sin_tope"] == (e["y_sin_recorte"] - 1).clip(lower=0)).all()
    assert e["utilidad_sin_tope"].tolist() == pytest.approx(
        (caso.rf + t.sharpe**2 / (2 * e["a"])).tolist()
    )
    assert (e["utilidad_sin_tope"] >= e["utilidad"] - 1e-12).all()  # el tope nunca sube U
    s = optimo_sin_apalancamiento(caso)
    assert (s["utilidad"] >= e["utilidad"] - 1e-12).all()  # la frontera solo puede mejorar


def test_composicion_completa_suma_100(caso):
    from roboadvisor.taller1.reportes.caso import composicion_completa

    comp = composicion_completa(caso)
    assert comp.sum().tolist() == pytest.approx([1.0] * 5, abs=1e-4)


def test_multiplos_frente_a_acwi(caso):
    from roboadvisor.taller1.reportes.caso import multiplos_referencia

    f = pd.DataFrame(
        {"ticker": ["ACWI", "QQQ", "SMH", "COLO", "EFA", "EWZ", "ILF"],
         "fecha": "2026-11-13", "pe": [20.0, 28.0, 27.0, None, 17.5, 14.0, 11.0],
         "div_yield": [1.4, 0.5, 0.2, None, 3.3, 1.8, 3.7]}
    )  # fmt: skip
    m = multiplos_referencia(caso, f)
    senal = dict(zip(m["tabla"]["ticker"], m["tabla"]["senal"], strict=True))
    assert senal == {"QQQ": "cara", "SMH": "cara", "COLO": "sin_dato", "ILF": "barata",
                     "EWZ": "barata", "EFA": "neutral"}  # fmt: skip
    assert m["ajustado"].sum() == pytest.approx(1.0)


def test_eda_con_encuestas_sinteticas(tmp_path):
    from roboadvisor.taller1.reportes import eda

    filas = []
    for i, (edad, letra) in enumerate(
        [
            ("25-34", "c"),
            ("35-44", "b"),
            ("45-54", "b"),
            ("55-64", "c"),
            ("65-74", "a"),
            ("18-24", "b"),
        ]
    ):
        filas.append(
            {"alias": f"V{i + 1}", "rango_edad": edad, "fecha_encuesta": "2026-11-18",
             **{q: letra for q in ["q1", "q2a", "q2b", "q2c", "q3", "q4", "q5", "q6", "q7"]},
             "ocupacion": "Jubilado/a" if letra == "a" else "Empleado/a",
             "rango_ingresos": "Menos de $2.000.000", "dependientes_economicos": "0",
             "nivel_educativo": "Pregrado", "experiencia_invirtiendo_anios": "Sin experiencia",
             "horizonte_principal_inversion": "3 a 5 años",
             "colchon_emergencia": "Sí" if i % 2 else "No",
             "activos_elegidos": "SPY, GLD", "y_guardado": "1.0", "origen_portafolio": "asignado"}
        )  # fmt: skip
    r = eda.analizar(pd.DataFrame(filas), tmp_path, {a: 1.0 for a in (8, 6, 4, 3, 1)},
                     {a: 1.0 for a in (8, 6, 4, 3, 1)})  # fmt: skip
    assert r.puntaje["n"] == 6 and r.puntaje["min"] == 9 and r.puntaje["max"] == 27
    assert r.perfiles["Personas"].sum() == 6
    assert r.alfa == pytest.approx(1.0)  # todas las respuestas de cada persona son iguales
    assert r.horizonte["monotonas"] == 6
    assert set(r.asociaciones["Factor"]) >= {"Edad", "Ocupación"}
    assert all(p.exists() for p in r.figuras.values())


def test_universo_de_referencia_es_el_de_mayor_sharpe(caso):
    from roboadvisor.taller1.data.semillas import leer_catalogo
    from roboadvisor.taller1.reportes.caso import GRUPOS_ENUNCIADO, buscar_universo

    mejor, sharpe = buscar_universo(caso, leer_catalogo())
    assert sorted(mejor) == sorted(UNIVERSO_REFERENCIA)  # si cambian los datos, revisar config
    assert sharpe == pytest.approx(caso.tangente.sharpe, abs=1e-6)
    assert "SPY" not in mejor and all(set(mejor) & g for g in GRUPOS_ENUNCIADO.values())
