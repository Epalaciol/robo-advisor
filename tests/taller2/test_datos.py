"""Lectura del informe, validaciones, descarga de IRC (sin red) y repositorio con el mock."""

import dataclasses
import datetime as dt

import httpx
import pytest

from roboadvisor.taller2.datos import irc
from roboadvisor.taller2.datos.informe import (
    a_fecha,
    a_numero,
    errores,
    fecha_en_texto,
    parsear_texto,
    validar,
    vencimiento_de_nemotecnico,
)

TEXTO = """INFORME DIARIO DE DEUDA PÚBLICA
viernes, 2 de octubre de 2026
Tasa Fija en Pesos
Fecha Vencimiento Nemotécnico Valor Nominal* Cupón Precio Limpio Precio Sucio Duración Var.Pb
20-oct-26 TCO364201026 5.351.599 0,00 99,430 99,430 0,05 11,607 VAL 11,629 VAL -2,2
TFIT31261050 19.913.239 7,25 57,940 64,693 7,94 13,030 VAL 13,000 SEN 3,0
13-mar-58 TFIT34130358 17.058.750 12,00 88,908 95,582 7,76 13,500 SEN 13,327 SEN 17,3
oct-50 Total Tasa Fija en Pesos 42.323.588 Promedio 6,0
Tasa Fija en UVR
15-abr-27 TUVT20150427 10.000.000 3,30 100,000 101,000 0,50 4,000 SEN 4,100 SEN -10,0
"""


def test_utilidades():
    assert a_numero("5.351.599") == 5351599
    assert a_numero("99,430") == 99.43
    assert a_numero("-2,2") == -2.2
    with pytest.raises(ValueError):
        a_numero("")
    assert a_fecha("9-feb-33") == dt.date(2033, 2, 9)
    assert a_fecha("20-DIC-26") == dt.date(2026, 12, 20)
    assert fecha_en_texto("viernes, 6 de noviembre de 2026") == dt.date(2026, 11, 6)
    assert vencimiento_de_nemotecnico("TCO364201026") == dt.date(2026, 10, 20)
    assert vencimiento_de_nemotecnico("TFIT08031127") == dt.date(2027, 11, 3)


def test_parser_anclado_en_nemotecnico_tolera_fecha_partida_e_ignora_uvr():
    inf = parsear_texto(TEXTO)
    assert inf.fecha == dt.date(2026, 10, 2)
    assert [f.nemotecnico for f in inf.filas] == ["TCO364201026", "TFIT31261050", "TFIT34130358"]
    f50 = inf.filas[1]
    assert f50.vencimiento == dt.date(2050, 10, 26) and f50.vencimiento_impreso is None
    assert f50.tasa_pub == pytest.approx(0.1303) and f50.origen_prev == "SEN"
    assert inf.total_nominal_mm == 42_323_588 and inf.promedio_var_pb == 6.0


def test_csv_del_enunciado_valida_sin_errores(informe_2oct):
    assert len(informe_2oct.filas) == 29
    assert informe_2oct.total_nominal_mm == 562_515_499
    h = validar(informe_2oct)
    assert not errores(h)
    assert [x.nemotecnico for x in h if x.codigo == "V5"] == ["TFIT31261050"]


@pytest.mark.parametrize(
    "cambio,codigo",
    [
        ({"total_nominal_mm": 1}, "V1"),
        ({"promedio_var_pb": 99.0}, "V4"),
    ],
)
def test_validaciones_de_totales(informe_2oct, cambio, codigo):
    inf = dataclasses.replace(informe_2oct, **cambio)
    assert codigo in {x.codigo for x in errores(validar(inf))}


def test_validaciones_por_fila(informe_2oct):
    filas = list(informe_2oct.filas)
    filas[0] = dataclasses.replace(filas[0], cupon=5.0, precio_sucio=filas[0].precio_limpio + 1)
    filas[1] = dataclasses.replace(filas[1], vencimiento_impreso=dt.date(2030, 1, 1))
    filas[2] = dataclasses.replace(filas[2], precio_sucio=filas[2].precio_limpio - 1)
    inf = dataclasses.replace(informe_2oct, filas=filas, total_nominal_mm=None)
    codigos = {(x.codigo, x.nemotecnico) for x in errores(validar(inf))}
    assert ("V2", filas[0].nemotecnico) in codigos
    assert ("V3", filas[1].nemotecnico) in codigos
    assert ("V2", filas[2].nemotecnico) in codigos


def test_total_descuadrado_por_redondeo_es_advertencia_y_una_fila_perdida_es_error(informe_2oct):
    suma = sum(f.valor_nominal_mm for f in informe_2oct.filas)
    leve = dataclasses.replace(informe_2oct, total_nominal_mm=suma + 3)  # caso 21→25-sep
    h = validar(leve)
    assert not errores(h)
    assert any(x.codigo == "V1" and x.nivel == "advertencia" for x in h)
    perdida = dataclasses.replace(informe_2oct, total_nominal_mm=suma + 1_884_373)
    assert "V1" in {x.codigo for x in errores(validar(perdida))}


TEXTO_22_SEP = """martes, 22 de septiembre de 2026
52 22-sep-26 TCO364220926 1.884.373 0,00 99,971 99,971 0,00 11,167 VAL 11,274 VAL -10,7
53 20-oct-26 TCO364201026 5.351.599 0,00 99,037 99,037 0,08 11,670 VAL 11,720 VAL -5,0
Total Tasa Fija en Pesos 7.235.972 Promedio -8,0
"""


def test_papel_que_vence_el_dia_del_informe_es_advertencia_y_no_entra_a_la_curva():
    inf = parsear_texto(TEXTO_22_SEP)
    assert inf.fecha == dt.date(2026, 9, 22)
    assert inf.filas[0].vencimiento == dt.date(2026, 9, 22)
    h = validar(inf)
    assert not [x for x in errores(h) if x.nemotecnico == "TCO364220926"]
    assert any(x.nemotecnico == "TCO364220926" and x.nivel == "advertencia" for x in h)
    assert [p.nemotecnico for p in inf.papeles()] == ["TCO364201026"]


def test_fila_no_leida_queda_en_avisos():
    texto = TEXTO_22_SEP + "99 20-oct-26 TFIT99999999 raro sin datos\n"
    inf = parsear_texto(texto)
    assert any(a.startswith("fila no leída:") and "TFIT99999999" in a for a in inf.avisos_lectura)


FILA_TCO_CUPON = (
    "65 5-oct-27 TCO364051027 900.000 1,00 88,780 88,780 0,99 12,749 VAL 12,851 VAL -10,2"
)


def test_tco_con_cupon_erroneo_se_corrige_a_cero_con_advertencia(informe_2oct):
    texto = "viernes, 9 de octubre de 2026\n" + FILA_TCO_CUPON + "\n"
    f = parsear_texto(texto).filas[0]
    assert f.cupon == 0 and f.cupon_original == 1.0
    inf = dataclasses.replace(informe_2oct, filas=[*informe_2oct.filas, f], total_nominal_mm=None)
    h = validar(inf)
    assert [x.nivel for x in h if x.codigo == "V2c"] == ["advertencia"]
    assert not [x for x in errores(h) if x.nemotecnico == f.nemotecnico]
    assert f.nemotecnico in {p.nemotecnico for p in inf.papeles()}


def test_dia_sin_texto_da_aviso_en_c1_y_no_falla():
    from roboadvisor.taller2.datos.informe import SinTexto
    from roboadvisor.taller2.pipeline.procesar import DiaTES
    from roboadvisor.taller2.pipeline.validacion import chequeo_cobertura

    assert issubclass(SinTexto, ValueError)
    ok = DiaTES(dt.date(2026, 10, 20), "ok")
    sin = DiaTES(dt.date(2026, 10, 21), "sin_texto", mensaje="PDF sin texto extraíble")
    assert chequeo_cobertura([ok, sin]).estado == "AVISO"
    err = DiaTES(dt.date(2026, 10, 22), "error_lectura", mensaje="corrupto")
    assert chequeo_cobertura([ok, sin, err]).estado == "FALLA"


# ----------------------------------------------------------------------------------- IRC
LISTADO = """
<table><tr><td><a href="/440/-/document_library/njyl/view_file/3672492?_x=1&amp;y=2">
<span>Informe Diario TES 6 de Noviembre de 2026</span></a></td></tr>
<tr><td><a href="/440/-/document_library/njyl/view_file/3661305">
Informe Diario TES 30 de Octubre de 2026</a></td></tr>
</table><a href="/440/-/document_library/njyl/view/3002336?_curEntry=2">Página siguiente</a>
"""
LISTADO_2 = """<a href="https://www.irc.gov.co/440/-/document_library/njyl/view_file/111">
Informe Diario TES 2 de Octubre de 2026</a>"""
VISTA = '<a href="/documents/d/guest/informe-diario-tes-2-oct?download=true">Descargar</a>'


def test_url_directa_y_listado():
    assert irc.url_directa(dt.date(2026, 11, 6)).endswith(
        "/documents/d/guest/informe-diario-6-de-noviembre-de-2026?download=true"
    )
    idx = irc.informes_en_listado(LISTADO)
    assert idx[dt.date(2026, 11, 6)].endswith("view_file/3672492?_x=1&y=2")
    assert dt.date(2026, 10, 30) in idx
    assert irc.pagina_siguiente(LISTADO).endswith("_curEntry=2")
    assert irc.enlace_descarga(VISTA).endswith("informe-diario-tes-2-oct?download=true")


def test_descarga_directa_y_respaldo_por_listado():
    pdf = b"%PDF-1.4 falso"

    def manejar(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "informe-diario-6-de-noviembre" in url:
            return httpx.Response(200, content=pdf)
        if "informe-diario-tes-2-oct" in url:
            return httpx.Response(200, content=pdf)
        if url.endswith("/440"):
            return httpx.Response(200, text=LISTADO)
        if "_curEntry=2" in url:
            return httpx.Response(200, text=LISTADO_2)
        if url.endswith("view_file/111"):
            return httpx.Response(200, text=VISTA)
        return httpx.Response(404, text="no")

    cli = irc.ClienteIRC(httpx.Client(transport=httpx.MockTransport(manejar)), pausa_s=0)
    datos, url = cli.descargar(dt.date(2026, 11, 6))
    assert datos == pdf and "6-de-noviembre" in url
    datos, url = cli.descargar(dt.date(2026, 10, 2))
    assert datos == pdf and "informe-diario-tes-2-oct" in url
    with pytest.raises(irc.NoPublicado):
        cli.descargar(dt.date(2026, 10, 12))  # festivo: ni URL directa ni en el listado


def test_bloqueo_del_sitio_da_mensaje_claro():
    cli = irc.ClienteIRC(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403))), pausa_s=0
    )
    with pytest.raises(PermissionError, match="sin-descarga"):
        cli.descargar(dt.date(2026, 11, 6))


# -------------------------------------------------------------------- repositorio (mock)
def test_repositorio_guarda_y_lee_con_el_mock(informe_2oct, resultado_2oct, monkeypatch):
    from roboadvisor.comun import cliente_mock
    from roboadvisor.taller2.config import ParametrosTES
    from roboadvisor.taller2.datos.repositorio import RepositorioTES

    monkeypatch.setattr(cliente_mock, "_TALLER2_SEMBRADO", [True])  # tablas vacías
    for t in ("t2_informes", "t2_cotizaciones", "t2_curvas", "t2_resultados"):
        cliente_mock._TABLAS.pop(t, None)
    repo = RepositorioTES(cliente_mock.crear_cliente_mock(es_servicio=True))
    repo.guardar_informe(informe_2oct, validar(informe_2oct))
    repo.guardar_resultado(resultado_2oct, ParametrosTES())
    repo.guardar_resultado(resultado_2oct, ParametrosTES())  # idempotente
    anon = RepositorioTES(cliente_mock.crear_cliente_mock())
    assert anon.fechas() == [dt.date(2026, 10, 2)]
    tabla = anon.tabla_dia(dt.date(2026, 10, 2))
    assert len(tabla) == 29 and set(tabla["senal"]) == {"Vender", "Mantener"}
    b, tau = anon.betas(dt.date(2026, 10, 2))
    assert b.b0 == pytest.approx(resultado_2oct.calibracion.betas.b0) and tau == 3.7
