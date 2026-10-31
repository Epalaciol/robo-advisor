"""Pruebas de integración contra un proyecto Supabase real: demuestran que
las políticas RLS de `supabase/migrations/0001_init.sql` aíslan a cada usuario.

Se saltan automáticamente si no hay `.env` con `SUPABASE_SERVICE_ROLE_KEY`
(`pytest -q` debe seguir pasando igual). Los usuarios de prueba se crean y
se eliminan (con `service_role`) al terminar cada test.
"""

import uuid
from datetime import UTC, datetime

import pytest
from postgrest.exceptions import APIError

from roboadvisor.config import Settings
from roboadvisor.data.cliente import cliente_anon, cliente_servicio, cliente_usuario


def _tiene_credenciales() -> bool:
    try:
        s = Settings()
    except Exception:
        return False
    return bool(s.SUPABASE_SERVICE_ROLE_KEY)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _tiene_credenciales(),
        reason="Sin .env con SUPABASE_SERVICE_ROLE_KEY: se omiten las pruebas de integración",
    ),
]

IDS_PREGUNTAS = ["q1", "q2a", "q2b", "q2c", "q3", "q4", "q5", "q6", "q7"]


def _perfil(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "alias": "tester",
        "edad_rango": "25-34",
        "factores": {},
        "consentimiento_at": datetime.now(UTC).isoformat(),
    }


def _encuesta(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "respuestas": dict.fromkeys(IDS_PREGUNTAS, "a"),
        "puntaje": 9,
        "perfil": "conservador",
        "a": 8,
    }


def _portafolio(user_id: str, encuesta_id: str) -> dict:
    return {
        "user_id": user_id,
        "encuesta_id": encuesta_id,
        "a_usado": 8,
        "perfil_usado": "conservador",
        "tickers": ["SPY", "AGG", "GLD"],
        "pesos_riesgo": {"SPY": 0.4, "AGG": 0.4, "GLD": 0.2},
        "y_star": 0.5,
        "peso_rf": 0.5,
        "pesos_completo": {"SPY": 0.2, "AGG": 0.2, "GLD": 0.1},
        "fecha_base": datetime.now(UTC).date().isoformat(),
    }


@pytest.fixture(scope="module")
def admin():
    return cliente_servicio()


def _crear_usuario_autenticado(admin):
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    password = uuid.uuid4().hex
    creado = admin.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user_id = creado.user.id

    anon = cliente_anon()
    sesion = anon.auth.sign_in_with_password({"email": email, "password": password})
    token = sesion.session.access_token

    return user_id, cliente_usuario(token)


@pytest.fixture
def usuario_a(admin):
    user_id, cliente = _crear_usuario_autenticado(admin)
    yield user_id, cliente
    admin.auth.admin.delete_user(user_id)


@pytest.fixture
def usuario_b(admin):
    user_id, cliente = _crear_usuario_autenticado(admin)
    yield user_id, cliente
    admin.auth.admin.delete_user(user_id)


def test_anon_no_puede_leer_activos_ni_perfiles():
    anon = cliente_anon()
    with pytest.raises(APIError):
        anon.table("activos").select("*").execute()
    with pytest.raises(APIError):
        anon.table("perfiles").select("*").execute()


def test_usuario_b_no_ve_perfil_ni_encuesta_de_a(usuario_a, usuario_b):
    user_id_a, cliente_a = usuario_a
    _, cliente_b = usuario_b

    cliente_a.table("perfiles").insert(_perfil(user_id_a)).execute()
    cliente_a.table("encuestas").insert(_encuesta(user_id_a)).execute()

    perfiles_vistos_por_b = (
        cliente_b.table("perfiles").select("*").eq("user_id", user_id_a).execute()
    )
    encuestas_vistas_por_b = (
        cliente_b.table("encuestas").select("*").eq("user_id", user_id_a).execute()
    )

    assert perfiles_vistos_por_b.data == []
    assert encuestas_vistas_por_b.data == []


def test_usuario_no_puede_actualizar_ni_borrar_su_encuesta_ni_portafolio(usuario_a):
    user_id_a, cliente_a = usuario_a
    encuesta = cliente_a.table("encuestas").insert(_encuesta(user_id_a)).execute().data[0]
    portafolio = (
        cliente_a.table("portafolios")
        .insert(_portafolio(user_id_a, encuesta["id"]))
        .execute()
        .data[0]
    )

    # Sin policy de UPDATE/DELETE: RLS filtra a 0 filas, no se modifica nada.
    assert cliente_a.table("encuestas").update({"puntaje": 27}).eq(
        "id", encuesta["id"]
    ).execute().data == []
    assert cliente_a.table("encuestas").delete().eq("id", encuesta["id"]).execute().data == []
    assert cliente_a.table("portafolios").update({"y_star": 1.0}).eq(
        "id", portafolio["id"]
    ).execute().data == []
    assert (
        cliente_a.table("portafolios").delete().eq("id", portafolio["id"]).execute().data == []
    )

    encuesta_actual = (
        cliente_a.table("encuestas").select("*").eq("id", encuesta["id"]).execute().data[0]
    )
    assert encuesta_actual["puntaje"] == 9


def test_usuario_a_no_puede_usar_encuesta_de_b(usuario_a, usuario_b):
    user_id_a, cliente_a = usuario_a
    user_id_b, cliente_b = usuario_b

    encuesta_b = cliente_b.table("encuestas").insert(_encuesta(user_id_b)).execute().data[0]

    with pytest.raises(APIError):
        cliente_a.table("portafolios").insert(_portafolio(user_id_a, encuesta_b["id"])).execute()


def test_usuario_autenticado_lee_activos_pero_no_escribe(usuario_a):
    _, cliente_a = usuario_a

    assert isinstance(cliente_a.table("activos").select("*").execute().data, list)
    assert isinstance(cliente_a.table("precios").select("*").execute().data, list)

    with pytest.raises(APIError):
        cliente_a.table("activos").insert(
            {"ticker": "ZZZ_TEST_RLS", "nombre": "x", "clase": "cripto"}
        ).execute()


def test_segundo_portafolio_mismo_usuario_falla_por_unique(usuario_a):
    user_id_a, cliente_a = usuario_a
    encuesta = cliente_a.table("encuestas").insert(_encuesta(user_id_a)).execute().data[0]
    portafolio = _portafolio(user_id_a, encuesta["id"])

    cliente_a.table("portafolios").insert(portafolio).execute()
    with pytest.raises(APIError):
        cliente_a.table("portafolios").insert(portafolio).execute()
