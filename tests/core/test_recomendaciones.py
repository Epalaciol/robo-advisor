import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.multiplos import SenalMultiplo
from roboadvisor.core.recomendaciones import AVISO_ACADEMICO, ContextoRecomendacion, generar

PARAMS = ParametrosFinancieros()


def _contexto(**overrides) -> ContextoRecomendacion:
    base = dict(
        pesos_actuales=pd.Series({"A": 0.30}),
        pesos_optimos_hoy=pd.Series({"A": 0.30}),
        retornos_12m=pd.Series({"A": 0.10}),
        rf_12m=0.03,
        vol_realizada=0.10,
        sigma_objetivo=0.10,
        senales_multiplos=[],
        tickers_portafolio=["A"],
        antiguedad_dias={"A": 1},
        params=PARAMS,
    )
    base.update(overrides)
    return ContextoRecomendacion(**base)


def test_r1_deriva_pesos_activa_con_5_1pp_no_con_4_9pp():
    ctx_no_activa = _contexto(
        pesos_actuales=pd.Series({"A": 0.349}), pesos_optimos_hoy=pd.Series({"A": 0.30})
    )
    recs = generar(ctx_no_activa)
    assert all(r.id != "R1" for r in recs)

    ctx_activa = _contexto(
        pesos_actuales=pd.Series({"A": 0.351}), pesos_optimos_hoy=pd.Series({"A": 0.30})
    )
    recs = generar(ctx_activa)
    assert any(r.id == "R1" for r in recs)


def test_r2_activo_rezagado():
    ctx_no_activa = _contexto(retornos_12m=pd.Series({"A": 0.05}), rf_12m=0.03)
    assert all(r.id != "R2" for r in generar(ctx_no_activa))

    ctx_activa = _contexto(retornos_12m=pd.Series({"A": 0.01}), rf_12m=0.03)
    assert any(r.id == "R2" for r in generar(ctx_activa))


def test_r3_fuera_de_perfil_vol_24_vs_26_sobre_objetivo():
    # sigma_objetivo=0.20, tol=0.25 -> limite=0.25
    ctx_no_activa = _contexto(vol_realizada=0.24, sigma_objetivo=0.20)
    assert all(r.id != "R3" for r in generar(ctx_no_activa))

    ctx_activa = _contexto(vol_realizada=0.26, sigma_objetivo=0.20)
    assert any(r.id == "R3" for r in generar(ctx_activa))


def test_r4_multiplos():
    señal_neutral = SenalMultiplo(
        ticker="A", pe=10.0, mediana_peers=10.0, z=0.0, senal="neutral", tilt_sugerido=0.0
    )
    ctx_no_activa = _contexto(senales_multiplos=[señal_neutral])
    assert all(r.id != "R4" for r in generar(ctx_no_activa))

    señal_cara = SenalMultiplo(
        ticker="A", pe=20.0, mediana_peers=10.0, z=2.0, senal="cara", tilt_sugerido=-0.025
    )
    ctx_activa = _contexto(senales_multiplos=[señal_cara])
    assert any(r.id == "R4" for r in generar(ctx_activa))


def test_r5_datos_viejos_5_vs_6_dias():
    ctx_no_activa = _contexto(antiguedad_dias={"A": 5})
    assert all(r.id != "R5" for r in generar(ctx_no_activa))

    ctx_activa = _contexto(antiguedad_dias={"A": 6})
    assert any(r.id == "R5" for r in generar(ctx_activa))


def test_sin_reglas_activas_solo_r0():
    ctx = _contexto()
    recs = generar(ctx)
    assert len(recs) == 1
    assert recs[0].id == "R0"


def test_orden_accion_aviso_info():
    ctx = _contexto(
        pesos_actuales=pd.Series({"A": 0.45}),
        pesos_optimos_hoy=pd.Series({"A": 0.30}),  # R1 accion (desvío 15pp)
        vol_realizada=0.26,
        sigma_objetivo=0.20,  # R3 accion
        retornos_12m=pd.Series({"A": 0.01}),
        rf_12m=0.03,  # R2 aviso
        antiguedad_dias={"A": 10},  # R5 aviso
        senales_multiplos=[
            SenalMultiplo(
                ticker="A", pe=20.0, mediana_peers=10.0, z=2.0, senal="cara", tilt_sugerido=-0.025
            )
        ],  # R4 info
    )
    recs = generar(ctx)
    severidades = [r.severidad for r in recs]
    orden_num = {"accion": 0, "aviso": 1, "info": 2}
    assert severidades == sorted(severidades, key=lambda s: orden_num[s])


def test_aviso_academico_presente_en_todas():
    ctx = _contexto()
    for r in generar(ctx):
        assert r.datos["aviso"] == AVISO_ACADEMICO
