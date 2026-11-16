"""Motor del Taller 2: flujos, Nelson-Siegel, calibración, TIR, duración, DV01 y decisión."""

import datetime as dt
import json

import numpy as np
import pytest

from roboadvisor.taller2.config import NOMINAL_DV01, ParametrosTES
from roboadvisor.taller2.core.flujos import aniversario, cupon_corrido, flujos
from roboadvisor.taller2.core.modelos import Betas, Flujos
from roboadvisor.taller2.core.nelson_siegel import curva, precio, spot
from roboadvisor.taller2.core.rendimientos import (
    aproximacion_precio,
    convexidad,
    duracion_modificada,
    dv01,
    dv01_analitico,
    tir,
)
from roboadvisor.taller2.core.senales import senal, umbral_pb

from .conftest import FIXTURES

F = dt.date(2026, 10, 2)


def test_flujos_bono_con_cupon():
    f = flujos(dt.date(2027, 11, 3), 5.75, F)
    assert f.fechas == (dt.date(2026, 11, 3), dt.date(2027, 11, 3))
    np.testing.assert_allclose(f.t, [32 / 365, 397 / 365])
    np.testing.assert_allclose(f.montos, [5.75, 105.75])


def test_flujos_tco_y_aniversario_en_la_fecha_y_29_febrero():
    assert len(flujos(dt.date(2027, 9, 7), 0.0, F).t) == 1
    # aniversario exactamente en la fecha de valoración: no cuenta
    assert flujos(dt.date(2028, 10, 2), 10.0, F).fechas[0] == dt.date(2027, 10, 2)
    assert aniversario(dt.date(2028, 2, 29), 1) == dt.date(2027, 2, 28)
    with pytest.raises(ValueError):
        flujos(F, 5.0, F)


def test_cupon_corrido_coincide_con_el_informe(informe_2oct):
    for f in informe_2oct.filas:
        if f.nemotecnico == "TFIT31261050":
            continue  # el informe difiere ~1 día de cupón (0,02); queda como advertencia V5
        dif = f.precio_limpio + cupon_corrido(f.vencimiento, f.cupon, F) - f.precio_sucio
        assert abs(dif) < 0.005, f.nemotecnico


def test_spot_limites_y_vectorizado():
    b = Betas(0.13, -0.02, 0.01)
    assert spot(0.0, b, 3.7) == pytest.approx(0.11)
    assert spot(1e6, b, 3.7) == pytest.approx(0.13, abs=1e-6)
    t = np.array([0.5, 1.0, 10.0])
    np.testing.assert_allclose(spot(t, b, 3.7), [spot(float(x), b, 3.7) for x in t])
    c = curva(b, 3.7)
    assert len(c) == 10_950 and c["factor_descuento"].is_monotonic_decreasing


def test_prueba_dorada_excel_del_profesor():
    datos = json.loads((FIXTURES / "modelo_excel_2026-03-17.json").read_text())
    b, tau = Betas(*datos["betas"]), datos["tau"]
    fecha = dt.date.fromisoformat(datos["fecha_calculo"])
    for p in datos["papeles"]:
        pe = precio(flujos(dt.date.fromisoformat(p["vencimiento"]), p["cupon"], fecha), b, tau)
        esperado = p["precio_estimado_correcto"] if p["excel_roto"] else p["precio_estimado_excel"]
        assert pe == pytest.approx(esperado, abs=1e-8), p["vencimiento"]


def test_tir_bono_par_y_tco():
    f = Flujos(fechas=(), t=np.array([1.0, 2.0, 3.0]), montos=np.array([8.0, 8.0, 108.0]))
    assert tir(100.0, f) == pytest.approx(0.08, abs=1e-12)
    tco = Flujos(fechas=(), t=np.array([1.0]), montos=np.array([100.0]))
    assert tir(90.0, tco) == pytest.approx(1 / 0.9 - 1, abs=1e-12)
    y = 0.11
    assert duracion_modificada(y, tco) == pytest.approx(1 / 1.11)
    assert convexidad(y, tco) == pytest.approx(2 / 1.11**2)


def test_calibracion_2oct_reproduce_excel_del_grupo(resultado_2oct):
    """Libro-taller2.xlsx (B35:D35): mismos betas que el Solver del grupo."""
    b = resultado_2oct.calibracion.betas
    np.testing.assert_allclose(
        b.como_tupla(), (0.13543912084533, -0.01199006426047, 0.00780016280557), atol=1e-7
    )
    assert resultado_2oct.calibracion.rmse == pytest.approx(0.4852, abs=1e-3)
    assert resultado_2oct.calibracion.convergio


def test_decisiones_2oct_con_umbral_1_sigma(resultado_2oct):
    assert resultado_2oct.umbral_pb == pytest.approx(23.4838, abs=1e-3)
    assert resultado_2oct.conteo_senales() == {"Mantener": 23, "Vender": 6}
    t = resultado_2oct.tabla.set_index("nemotecnico")
    assert t.loc["TFIT08031127", "spread_pb"] == pytest.approx(-102.82, abs=0.05)
    assert t.loc["TFIT08031127", "senal"] == "Vender"


def test_dv01_escala_10_a_la_9(resultado_2oct):
    """DV01 / ((P/100)·N·1 pb) = D*: con N = 10**12 esta prueba falla (×1.000)."""
    assert NOMINAL_DV01 == 1_000_000_000
    t = resultado_2oct.tabla
    cociente = t["dv01_cop"] / (t["precio_sucio"] / 100 * NOMINAL_DV01 * 1e-4)
    np.testing.assert_allclose(cociente, t["duracion_modificada"], rtol=1e-4)
    d = t.set_index("nemotecnico")["dv01_cop"]
    assert d["TCO364201026"] == pytest.approx(4366.73, rel=1e-3)
    assert d["TFIT34130358"] == pytest.approx(653823.95, rel=1e-3)
    # variante del Excel del grupo (duración del informe) = columna Q
    q = t.set_index("nemotecnico")["dv01_excel_cop"]
    assert q["TCO364201026"] == pytest.approx(4427.378305979735, rel=1e-6)


def test_dv01_numerico_igual_al_analitico(informe_2oct):
    for p in informe_2oct.papeles():
        f = flujos(p.vencimiento, p.cupon, F)
        y = tir(p.precio_sucio, f)
        assert dv01(y, f) == pytest.approx(dv01_analitico(y, f, p.precio_sucio), rel=1e-6)


def test_duracion_coincide_con_el_informe(resultado_2oct):
    t = resultado_2oct.tabla
    assert (t["duracion_macaulay"] - t["duracion_informe"]).abs().max() <= 0.02


def test_aproximacion_duracion_convexidad_tfit_2058(informe_2oct):
    p = next(x for x in informe_2oct.papeles() if x.nemotecnico == "TFIT34130358")
    f = flujos(p.vencimiento, p.cupon, F)
    for fila in aproximacion_precio(tir(p.precio_sucio, f), f):
        error_dc = abs(fila["duracion_convexidad"] - fila["exacto"])
        assert error_dc < abs(fila["duracion"] - fila["exacto"])
        assert error_dc < 0.0005


def test_senal_y_umbrales():
    assert senal(10.0, 10.0) == "Mantener"
    assert senal(10.01, 10.0) == "Comprar"
    assert senal(-10.01, 10.0) == "Vender"
    x = [1, 2, 3, 4, -100]
    assert umbral_pb(x, "sigma") == pytest.approx(np.std(x, ddof=1))
    assert umbral_pb(x, "sigma_robusta") < umbral_pb(x, "sigma")
    assert umbral_pb(x, 7) == 7


def test_variantes_de_calibracion(informe_2oct):
    from dataclasses import replace

    from roboadvisor.taller2.core.analisis import analizar

    p = ParametrosTES()
    sen = analizar(informe_2oct.papeles(), F, replace(p, usar_origen="SEN", umbral=10.0))
    assert sen.calibracion.n == 18
    pond = analizar(informe_2oct.papeles(), F, replace(p, ponderacion="duracion", umbral=10.0))
    assert pond.conteo_senales() == {"Mantener": 15, "Comprar": 10, "Vender": 4}
