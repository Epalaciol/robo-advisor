"""Motor del Taller 2: flujos, Nelson-Siegel, calibración, TIR, duración, DV01 y decisión."""

import datetime as dt
import json

import numpy as np
import pytest

from roboadvisor.taller2.config import NOMINAL_DV01, ParametrosTES
from roboadvisor.taller2.core.flujos import (
    aniversario,
    cupon_corrido,
    cupon_corrido_papel,
    flujos,
    flujos_papel,
    incluye_cupon_hoy,
)
from roboadvisor.taller2.core.modelos import Betas, Flujos, Papel
from roboadvisor.taller2.core.nelson_siegel import curva, precio, spot
from roboadvisor.taller2.core.rendimientos import (
    aproximacion_precio,
    convexidad,
    duracion_macaulay,
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
        f = flujos(dt.date.fromisoformat(p["vencimiento"]), p["cupon"], fecha, conteo="Act/365")
        pe = precio(f, b, tau)
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


def test_calibracion_2oct_reproduce_excel_del_grupo(informe_2oct):
    """Libro-taller2.xlsx (B35:D35): mismos betas que el Solver del grupo (días calendario)."""
    from roboadvisor.taller2.core.analisis import analizar

    r = analizar(informe_2oct.papeles(), F, ParametrosTES(conteo_dias="Act/365"))
    np.testing.assert_allclose(
        r.calibracion.betas.como_tupla(),
        (0.13543912084533, -0.01199006426047, 0.00780016280557),
        atol=1e-7,
    )
    assert r.calibracion.rmse == pytest.approx(0.4852, abs=1e-3)
    assert r.umbral_pb == pytest.approx(23.4838, abs=1e-3)
    assert r.conteo_senales() == {"Mantener": 23, "Vender": 6}
    assert r.calibracion.convergio


def test_convencion_de_mercado_reproduce_la_tasa_sen(resultado_2oct):
    """NL/365 (sin 29-feb): la TIR del precio publicado = tasa SEN de IRC."""
    t = resultado_2oct.tabla
    sen = t[t["origen_tasa"] == "SEN"]
    assert len(sen) == 18
    assert ((sen["tir_observada"] - sen["tasa_informe"]).abs() / 1e-4).max() < 0.05
    assert t.set_index("nemotecnico").loc["TFIT34130358", "tir_observada"] == pytest.approx(
        0.135, abs=1e-6
    )


def test_dias_sin_29_de_febrero():
    from roboadvisor.taller2.core.flujos import dias_entre

    a, b = dt.date(2028, 2, 1), dt.date(2028, 3, 1)
    assert dias_entre(a, b, "Act/365") == 29 and dias_entre(a, b) == 28
    assert dias_entre(F, dt.date(2058, 3, 13)) == (dt.date(2058, 3, 13) - F).days - 8
    with pytest.raises(ValueError):
        dias_entre(a, b, "30/360")


def test_decisiones_2oct_con_umbral_1_sigma(resultado_2oct):
    assert resultado_2oct.conteo_dias == "NL/365"
    assert resultado_2oct.calibracion.betas.b0 == pytest.approx(0.135518, abs=1e-6)
    assert resultado_2oct.umbral_pb == pytest.approx(23.7203, abs=1e-3)
    assert resultado_2oct.conteo_senales() == {"Mantener": 22, "Vender": 7}
    t = resultado_2oct.tabla.set_index("nemotecnico")
    assert t.loc["TFIT08031127", "spread_pb"] == pytest.approx(-103.60, abs=0.05)
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


# --------------------------------------------------- cupón que se paga en la fecha del informe
F3NOV = dt.date(2026, 11, 3)


def _tfit_3nov(sucio=101.562):
    """Fila real de TFIT08031127 del 3-nov-2026 (cupón 5,75 pagado ese día, sucio con cupón)."""
    return Papel(
        "TFIT08031127", dt.date(2027, 11, 3), 5.75, sucio, 95.875, 1.0, 0.10247, "VAL", 22_186_857
    )


def test_cupon_en_la_fecha_entra_en_t0_si_el_precio_lo_trae():
    p = _tfit_3nov()
    assert incluye_cupon_hoy(p, F3NOV)  # sucio − limpio = 5,687 ≈ cupón (tol. absorbe 0,06)
    f = flujos_papel(p, F3NOV)
    assert f.fechas == (F3NOV, dt.date(2027, 11, 3))
    np.testing.assert_allclose(f.t, [0.0, 365 / 365])
    np.testing.assert_allclose(f.montos, [5.75, 105.75])
    assert cupon_corrido_papel(p, F3NOV) == 5.75
    y = tir(p.precio_sucio, f)
    assert 0.10 < y < 0.11 and abs(y - p.tasa_pub) * 1e4 < 30  # ≈ 10,4 %, no 4 %
    assert 0.9 < duracion_macaulay(y, f) < 1.0  # el flujo en t = 0 pesa 0 años
    assert np.isfinite(convexidad(y, f)) and dv01(y, f) > 0
    b = Betas(0.137, -0.016, 0.0)  # DF(0) = 1: el cupón de t = 0 entra completo, sin dividir por 0
    assert precio(f, b, 3.7) == pytest.approx(5.75 + 105.75 * (1 + spot(1.0, b, 3.7)) ** -1.0)


def test_cupon_en_la_fecha_ex_cupon_se_excluye_como_antes():
    p = Papel("TFIT08031127", dt.date(2027, 11, 3), 5.75, 95.9, 95.875, 1.0, 0.1025, "VAL")
    assert not incluye_cupon_hoy(p, F3NOV)
    assert flujos_papel(p, F3NOV).fechas == (dt.date(2027, 11, 3),)
    assert cupon_corrido_papel(p, F3NOV) == 0.0
    # un día sin cupón en la fecha: nada cambia
    q = _tfit_3nov()
    assert not incluye_cupon_hoy(q, dt.date(2026, 11, 4))
