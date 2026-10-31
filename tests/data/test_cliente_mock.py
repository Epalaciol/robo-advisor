"""Pruebas del cliente Supabase falso en memoria (modo mock, sin red)."""

import pytest
from postgrest.exceptions import APIError

import roboadvisor.data.cliente_mock as cliente_mock_modulo
from roboadvisor.data.cliente_mock import CLAVE_PRUEBA, CORREO_PRUEBA, crear_cliente_mock


@pytest.fixture(autouse=True)
def _estado_mock_limpio():
    """Aísla cada prueba: el mock vive en dicts a nivel de módulo (persisten
    entre pruebas si no se limpian), y puede haber datos reales sembrados
    desde `data_local/` si ese directorio existe en este checkout.
    """
    cliente_mock_modulo._TABLAS.clear()
    cliente_mock_modulo._USUARIOS.clear()
    cliente_mock_modulo._SESIONES.clear()
    yield


def test_usuario_de_prueba_sembrado_y_puede_iniciar_sesion():
    cliente = crear_cliente_mock()
    sesion = cliente.auth.sign_in_with_password(
        {"email": CORREO_PRUEBA, "password": CLAVE_PRUEBA}
    )
    assert sesion.user.id
    assert sesion.session.access_token


def test_login_con_clave_incorrecta_falla():
    cliente = crear_cliente_mock()
    with pytest.raises(ValueError):
        cliente.auth.sign_in_with_password({"email": CORREO_PRUEBA, "password": "mala"})


def test_registro_y_login_de_usuario_nuevo():
    cliente = crear_cliente_mock()
    registro = cliente.auth.sign_up({"email": "nuevo@local.test", "password": "clave1234"})
    assert registro.session.access_token

    otro_cliente = crear_cliente_mock()
    sesion = otro_cliente.auth.sign_in_with_password(
        {"email": "nuevo@local.test", "password": "clave1234"}
    )
    assert sesion.user.id == registro.user.id


def test_registro_con_correo_duplicado_falla():
    cliente = crear_cliente_mock()
    cliente.auth.sign_up({"email": "dup@local.test", "password": "clave1234"})
    with pytest.raises(ValueError):
        cliente.auth.sign_up({"email": "dup@local.test", "password": "otra1234"})


def test_select_filtra_por_usuario_autenticado():
    admin = crear_cliente_mock()
    sesion_a = admin.auth.sign_up({"email": "a@local.test", "password": "clave1234"})
    sesion_b = admin.auth.sign_up({"email": "b@local.test", "password": "clave1234"})

    cliente_a = crear_cliente_mock()
    cliente_a.postgrest.auth(sesion_a.session.access_token)
    cliente_a.table("perfiles").insert(
        {"user_id": sesion_a.user.id, "alias": "A", "edad_rango": "25-34", "consentimiento_at": "x"}
    ).execute()

    cliente_b = crear_cliente_mock()
    cliente_b.postgrest.auth(sesion_b.session.access_token)
    vistos_por_b = cliente_b.table("perfiles").select("*").execute().data

    assert vistos_por_b == []
    vistos_por_a = cliente_a.table("perfiles").select("*").execute().data
    assert len(vistos_por_a) == 1
    assert vistos_por_a[0]["alias"] == "A"


def test_insert_duplicado_en_tabla_unica_lanza_apierror():
    admin = crear_cliente_mock()
    sesion = admin.auth.sign_up({"email": "c@local.test", "password": "clave1234"})
    cliente = crear_cliente_mock()
    cliente.postgrest.auth(sesion.session.access_token)

    fila = {
        "user_id": sesion.user.id,
        "puntaje": 18,
        "perfil": "moderado",
        "a": 4,
        "respuestas": {},
    }
    cliente.table("encuestas").insert(fila).execute()
    with pytest.raises(APIError):
        cliente.table("encuestas").insert(fila).execute()


def test_servicio_ve_todas_las_filas_sin_filtrar_por_usuario():
    admin = crear_cliente_mock()
    sesion_a = admin.auth.sign_up({"email": "d@local.test", "password": "clave1234"})
    sesion_b = admin.auth.sign_up({"email": "e@local.test", "password": "clave1234"})

    cliente_a = crear_cliente_mock()
    cliente_a.postgrest.auth(sesion_a.session.access_token)
    cliente_a.table("perfiles").insert(
        {"user_id": sesion_a.user.id, "alias": "D", "edad_rango": "25-34", "consentimiento_at": "x"}
    ).execute()

    cliente_b = crear_cliente_mock()
    cliente_b.postgrest.auth(sesion_b.session.access_token)
    cliente_b.table("perfiles").insert(
        {"user_id": sesion_b.user.id, "alias": "E", "edad_rango": "25-34", "consentimiento_at": "x"}
    ).execute()

    servicio = crear_cliente_mock(es_servicio=True)
    todos = servicio.table("perfiles").select("*").execute().data
    aliases = {f["alias"] for f in todos}
    assert {"D", "E"}.issubset(aliases)


def test_eq_in_order_limit():
    cliente = crear_cliente_mock(es_servicio=True)
    cliente.table("precios").insert(
        [
            {"ticker": "X", "fecha": "2024-01-01", "adj_close": 10},
            {"ticker": "X", "fecha": "2024-01-02", "adj_close": 11},
            {"ticker": "Y", "fecha": "2024-01-01", "adj_close": 20},
        ]
    ).execute()

    ultimo_x = (
        cliente.table("precios")
        .select("*")
        .eq("ticker", "X")
        .order("fecha", desc=True)
        .limit(1)
        .execute()
        .data
    )
    assert len(ultimo_x) == 1
    assert ultimo_x[0]["fecha"] == "2024-01-02"

    filtrados = cliente.table("precios").select("*").in_("ticker", ["X"]).execute().data
    assert all(f["ticker"] == "X" for f in filtrados)

    desde = cliente.table("precios").select("*").gte("fecha", "2024-01-02").execute().data
    assert all(f["fecha"] >= "2024-01-02" for f in desde)


def test_update_y_delete():
    cliente = crear_cliente_mock(es_servicio=True)
    cliente.table("precios").insert(
        {"ticker": "Z", "fecha": "2024-01-01", "adj_close": 1}
    ).execute()

    cliente.table("precios").update({"adj_close": 2}).eq("ticker", "Z").execute()
    actualizado = cliente.table("precios").select("*").eq("ticker", "Z").execute().data[0]
    assert actualizado["adj_close"] == 2

    cliente.table("precios").delete().eq("ticker", "Z").execute()
    assert cliente.table("precios").select("*").eq("ticker", "Z").execute().data == []


def test_upsert_actualiza_filas_existentes():
    cliente = crear_cliente_mock(es_servicio=True)
    cliente.table("activos").upsert(
        {"ticker": "ABC", "nombre": "Original"}, on_conflict="ticker"
    ).execute()
    cliente.table("activos").upsert(
        {"ticker": "ABC", "nombre": "Actualizado"}, on_conflict="ticker"
    ).execute()

    filas = cliente.table("activos").select("*").eq("ticker", "ABC").execute().data
    assert len(filas) == 1
    assert filas[0]["nombre"] == "Actualizado"
