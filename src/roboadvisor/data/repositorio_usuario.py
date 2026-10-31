"""Acceso a los datos propios del usuario (vía su cliente, con JWT: RLS aplica).

Solo usa la clave pública `anon` con el token del usuario; cada método confía
en las políticas RLS de `supabase/migrations/` para devolver solo las filas
del usuario autenticado.
"""

from postgrest.exceptions import APIError

from supabase import Client


class RepositorioUsuario:
    """Perfil, encuesta y portafolio del usuario autenticado (o `None` si no existen)."""

    def __init__(self, cliente: Client):
        self._cliente = cliente

    def crear_perfil(
        self,
        user_id: str,
        alias: str,
        edad_rango: str,
        consentimiento_at: str,
        factores: dict | None = None,
    ) -> dict:
        fila = {
            "user_id": user_id,
            "alias": alias,
            "edad_rango": edad_rango,
            "factores": factores or {},
            "consentimiento_at": consentimiento_at,
        }
        return self._cliente.table("perfiles").insert(fila).execute().data[0]

    def obtener_perfil(self) -> dict | None:
        datos = self._cliente.table("perfiles").select("*").execute().data
        return datos[0] if datos else None

    def obtener_encuesta(self) -> dict | None:
        datos = self._cliente.table("encuestas").select("*").execute().data
        return datos[0] if datos else None

    def obtener_portafolio(self) -> dict | None:
        datos = self._cliente.table("portafolios").select("*").execute().data
        return datos[0] if datos else None

    def guardar_encuesta(self, payload: dict) -> dict:
        """Inserta la encuesta (inmutable: `unique(user_id)`). Mensaje claro si ya existía."""
        try:
            return self._cliente.table("encuestas").insert(payload).execute().data[0]
        except APIError as error:
            raise ValueError("Ya existe una encuesta guardada para tu usuario.") from error

    def actualizar_factores(self, user_id: str, factores: dict) -> None:
        self._cliente.table("perfiles").update({"factores": factores}).eq(
            "user_id", user_id
        ).execute()

    def obtener_estado_pipeline(self) -> dict | None:
        """Última corrida del pipeline y fecha del precio más reciente (lectura
        autenticada de tablas de mercado; no filtra por usuario)."""
        corridas = (
            self._cliente.table("pipeline_runs")
            .select("*")
            .order("terminado_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not corridas:
            return None

        precios = (
            self._cliente.table("precios")
            .select("fecha")
            .order("fecha", desc=True)
            .limit(1)
            .execute()
            .data
        )
        ultima_fecha_precio = precios[0]["fecha"] if precios else None

        return {"estado": corridas[0]["estado"], "ultima_fecha_precio": ultima_fecha_precio}
