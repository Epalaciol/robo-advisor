"""Cuenta de administrador (migración 0004): el repositorio filtra por usuario y la página de
administración solo se abre para administradores. Corre con el cliente en memoria (MOCK_DATA)."""

from pathlib import Path

import pytest

from roboadvisor.taller1.data.repositorio_usuario import RepositorioUsuario

PAGINA = Path(__file__).resolve().parents[3] / "app" / "pages" / "5_Admin.py"


@pytest.fixture
def mock(monkeypatch):
    monkeypatch.setenv("MOCK_DATA", "true")
    import streamlit as st

    from roboadvisor.comun import cliente_mock as m

    m.ClienteMock()  # siembra usuarios de prueba
    st.cache_data.clear()  # la página cachea la lista de usuarios entre corridas
    yield m
    m._tabla("administradores").clear()


def _sesion(m, correo: str, clave: str) -> dict:
    r = m.ClienteMock().auth.sign_in_with_password({"email": correo, "password": clave})
    return {
        "user_id": r.user.id,
        "correo": correo,
        "access_token": r.session.access_token,
        "refresh_token": r.session.refresh_token,
    }


def test_repositorio_filtra_por_el_usuario_pedido(mock):
    c = mock.ClienteMock(es_servicio=True)  # ve todas las filas, como un administrador
    a3 = mock._USUARIOS[mock.CORREO_A3]["id"]
    prueba = mock._USUARIOS[mock.CORREO_PRUEBA]["id"]
    assert RepositorioUsuario(c, a3).obtener_perfil()["user_id"] == a3
    assert RepositorioUsuario(c, prueba).obtener_perfil()["user_id"] == prueba
    assert RepositorioUsuario(c, a3).obtener_encuesta()["user_id"] == a3
    assert RepositorioUsuario(c, prueba).obtener_encuesta() is None


def test_usuario_normal_no_es_admin_ni_ve_a_otros(mock):
    s = _sesion(mock, mock.CORREO_PRUEBA, mock.CLAVE_PRUEBA)
    c = mock.ClienteMock()
    c.auth.set_session(s["access_token"], s["refresh_token"])
    repo = RepositorioUsuario(c, s["user_id"])
    assert not repo.es_admin()
    assert {u["user_id"] for u in repo.listar_usuarios()} == {s["user_id"]}


def _abrir(s: dict):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(PAGINA), default_timeout=120)
    for k, v in s.items():
        at.session_state[k] = v
    return at.run()


def test_pagina_admin_niega_el_acceso_a_un_usuario_normal(mock):
    at = _abrir(_sesion(mock, mock.CORREO_PRUEBA, mock.CLAVE_PRUEBA))
    assert not at.exception
    assert any("solo para administradores" in w.value for w in at.warning)
    assert not at.dataframe


def test_pagina_admin_muestra_a_los_demas_usuarios(mock):
    s = _sesion(mock, mock.CORREO_PRUEBA, mock.CLAVE_PRUEBA)
    mock._tabla("administradores").append({"user_id": s["user_id"]})
    at = _abrir(s)
    assert not at.exception
    tabla = at.dataframe[0].value
    assert mock.ALIAS_A3 in set(tabla["Alias"])  # ve al otro usuario…
    assert mock.ALIAS_PRUEBA not in set(tabla["Alias"])  # …y no se lista a sí mismo
    assert "Esta sección es solo para administradores." not in [w.value for w in at.warning]


def test_pagina_admin_no_muestra_cuentas_de_prueba(mock):
    s = _sesion(mock, mock.CORREO_PRUEBA, mock.CLAVE_PRUEBA)
    mock._tabla("administradores").append({"user_id": s["user_id"]})
    a3 = next(p for p in mock._tabla("perfiles") if p["alias"] == mock.ALIAS_A3)
    original = dict(a3["factores"] or {})
    a3["factores"] = {**original, "_prueba": True}
    try:
        at = _abrir(s)
        assert not at.exception
        assert not at.dataframe  # el único otro usuario era de prueba
        assert any("Aún no hay usuarios" in i.value for i in at.info)
    finally:
        a3["factores"] = original
