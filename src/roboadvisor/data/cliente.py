"""Clientes de Supabase.

`service_role` ignora RLS: solo lo usa el pipeline y los scripts de
administración, **nunca** la app. La app usa `anon` + el JWT del usuario
(`cliente_usuario`); la seguridad la dan las políticas RLS de
`supabase/migrations/`.

Modo mock: con `MOCK_DATA=true` en el entorno, estas funciones devuelven un
cliente falso en memoria (`cliente_mock.py`) en vez de conectarse a Supabase.
Pensado solo para correr la app en local sin un proyecto real.
"""

import os

from roboadvisor.config import Settings
from supabase import Client, create_client


def modo_mock_activo() -> bool:
    return os.environ.get("MOCK_DATA", "").strip().lower() == "true"


def cliente_anon(settings: Settings | None = None) -> Client:
    """Cliente con la clave pública `anon` (sin JWT de usuario; RLS deniega todo)."""
    if modo_mock_activo():
        from roboadvisor.data.cliente_mock import crear_cliente_mock

        return crear_cliente_mock()
    s = settings or Settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_ANON_KEY)


def cliente_servicio(settings: Settings | None = None) -> Client:
    """Cliente con `service_role` (ignora RLS). Falla si no está configurada."""
    if modo_mock_activo():
        from roboadvisor.data.cliente_mock import crear_cliente_mock

        return crear_cliente_mock(es_servicio=True)
    s = settings or Settings()
    if not s.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "Falta SUPABASE_SERVICE_ROLE_KEY: este cliente es solo para el pipeline "
            "y scripts de administración, nunca para la app."
        )
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)


def cliente_usuario(access_token: str, settings: Settings | None = None) -> Client:
    """Cliente `anon` con el JWT del usuario puesto, para que las políticas RLS apliquen."""
    if modo_mock_activo():
        from roboadvisor.data.cliente_mock import crear_cliente_mock

        cliente = crear_cliente_mock()
        cliente.postgrest.auth(access_token)
        return cliente
    s = settings or Settings()
    client = create_client(s.SUPABASE_URL, s.SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client
