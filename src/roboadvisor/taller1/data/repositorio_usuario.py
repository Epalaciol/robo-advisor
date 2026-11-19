"""Acceso a los datos propios del usuario (vía su cliente, con JWT: RLS aplica).

Solo usa la clave pública `anon` con el token del usuario; la seguridad la dan las
políticas RLS de `supabase/migrations/`. Como un administrador (migración 0004) puede
leer las filas de todos, cada lectura filtra además por `user_id`: el del usuario en
sesión o, en la página de administración, el del usuario que se está revisando.
"""

from postgrest.exceptions import APIError

from supabase import Client


class RepositorioUsuario:
    """Perfil, encuesta y portafolio de un usuario (o `None` si no existen).

    `user_id`: de quién leer. Sin él se confía solo en RLS (válido para un usuario normal,
    que solo ve sus filas); la app siempre lo pasa.
    """

    def __init__(self, cliente: Client, user_id: str | None = None):
        self._cliente = cliente
        self._user_id = user_id

    def _leer(self, tabla: str) -> dict | None:
        consulta = self._cliente.table(tabla).select("*")
        if self._user_id:
            consulta = consulta.eq("user_id", self._user_id)
        datos = consulta.execute().data
        return datos[0] if datos else None

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
        return self._leer("perfiles")

    def obtener_encuesta(self) -> dict | None:
        return self._leer("encuestas")

    def obtener_portafolio(self) -> dict | None:
        return self._leer("portafolios")

    def es_admin(self) -> bool:
        """¿El usuario en sesión es administrador? (False si la migración 0004 no está aplicada)."""
        if not self._user_id:
            return False
        try:
            datos = (
                self._cliente.table("administradores")
                .select("user_id")
                .eq("user_id", self._user_id)
                .execute()
                .data
            )
        except Exception:
            return False
        return bool(datos)

    def listar_usuarios(self) -> list[dict]:
        """Para administradores: perfil, encuesta y portafolio de todos los usuarios visibles
        (RLS decide qué se ve: un usuario normal solo obtiene su propia fila)."""
        perfiles = (
            self._cliente.table("perfiles")
            .select("user_id, alias, edad_rango, factores, created_at")
            .execute()
            .data
        )
        encuestas = {
            e["user_id"]: e
            for e in self._cliente.table("encuestas")
            .select("user_id, puntaje, perfil, a, respuestas, created_at")
            .execute()
            .data
        }
        portafolios = {
            p["user_id"]: p
            for p in self._cliente.table("portafolios")
            .select(
                "user_id, tickers, pesos_riesgo, pesos_completo, y_star, peso_rf, fecha_base, "
                "parametros, metricas"
            )
            .execute()
            .data
        }
        return [
            {
                **p,
                "encuesta": encuestas.get(p["user_id"]),
                "portafolio": portafolios.get(p["user_id"]),
            }
            for p in perfiles
        ]

    def guardar_encuesta(self, payload: dict) -> dict:
        """Inserta la encuesta (inmutable: `unique(user_id)`). Mensaje claro si ya existía."""
        try:
            return self._cliente.table("encuestas").insert(payload).execute().data[0]
        except APIError as error:
            raise ValueError("Ya existe una encuesta guardada para tu usuario.") from error

    def guardar_portafolio(self, payload: dict) -> dict:
        """Inserta el portafolio (inmutable: `unique(user_id)`). Mensaje claro si ya existía."""
        try:
            return self._cliente.table("portafolios").insert(payload).execute().data[0]
        except APIError as error:
            raise ValueError("Ya existe un portafolio guardado para tu usuario.") from error

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
