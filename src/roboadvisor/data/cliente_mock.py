"""Cliente Supabase falso en memoria, para correr la app completa en local
**sin** un proyecto Supabase real. Se activa con `MOCK_DATA=true` (ver
`data/cliente.py`).

Implementa solo el subconjunto de la API de `supabase-py` que la app
realmente usa: `table().select/insert/update/upsert/delete().eq/in_/gte()
.order().limit().execute()` y un `auth` mínimo (`sign_up`,
`sign_in_with_password`, `set_session`, `sign_out`, `admin.*`).

**No reemplaza las pruebas de RLS** de `tests/db/test_rls.py` (esas corren
contra un proyecto Supabase real); aquí solo se filtran `perfiles`,
`encuestas` y `portafolios` por el usuario autenticado del cliente, para que
la app se comporte como en producción en un flujo normal — no es una prueba
de seguridad.

Los datos viven en memoria de **este proceso** mientras corre: se pierden al
reiniciar el servidor de Streamlit y no los ve ningún script lanzado aparte
(`scripts/cargar_catalogo.py`, `scripts/crear_usuario_prueba.py`, ...), que
corren en su propio proceso. El catálogo y los precios se siembran
automáticamente la primera vez que se usa el mock, desde
`supabase/seed/activos.csv` y `data_local/precios.csv`/`rf.csv` (si existen:
ver `scripts/descargar_precios_prueba.py`). También se crea un usuario de
prueba fijo: correo `prueba@local.test`, clave `Prueba1234!`; y otro con encuesta
hecha (A = 3) y sin portafolio: `a3@local.test`, misma clave.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from postgrest.exceptions import APIError

from roboadvisor.data.semillas import leer_catalogo

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
TABLAS_DEL_USUARIO = {"perfiles", "encuestas", "portafolios"}
TABLAS_CON_USER_ID_UNICO = {"encuestas", "portafolios"}

CORREO_PRUEBA = "prueba@local.test"
CLAVE_PRUEBA = "Prueba1234!"
ALIAS_PRUEBA = "Usuario de prueba"

# Segundo usuario: encuesta ya respondida (puntaje 23 → "moderado_agresivo", A = 3), sin portafolio.
CORREO_A3 = "a3@local.test"
CLAVE_A3 = "Prueba1234!"
ALIAS_A3 = "Usuario A=3"
RESPUESTAS_A3 = {
    "q1": "c",
    "q2a": "b",
    "q2b": "c",
    "q2c": "c",
    "q3": "b",
    "q4": "c",
    "q5": "b",
    "q6": "c",
    "q7": "b",
}  # 5·c + 4·b = 15 + 8 = 23

# Estado global del proceso (persiste mientras corre el servidor; no se comparte entre procesos).
_TABLAS: dict[str, list[dict]] = {}
_USUARIOS: dict[str, dict] = {}  # correo -> {id, correo, clave}
_SESIONES: dict[str, str] = {}  # access_token -> user_id


def _tabla(nombre: str) -> list[dict]:
    return _TABLAS.setdefault(nombre, [])


def _sembrar_catalogo() -> None:
    if _tabla("activos"):
        return
    try:
        _TABLAS["activos"] = leer_catalogo()
    except FileNotFoundError:
        pass


def _sembrar_precios_y_rf() -> None:
    ruta_precios = RAIZ_PROYECTO / "data_local" / "precios.csv"
    if not _tabla("precios") and ruta_precios.exists():
        df = pd.read_csv(ruta_precios, parse_dates=["fecha"])
        df["fecha"] = df["fecha"].dt.date.astype(str)
        _TABLAS["precios"] = df.to_dict(orient="records")

    ruta_rf = RAIZ_PROYECTO / "data_local" / "rf.csv"
    if not _tabla("tasa_libre_riesgo") and ruta_rf.exists():
        df = pd.read_csv(ruta_rf, parse_dates=["fecha"])
        df["fecha"] = df["fecha"].dt.date.astype(str)
        _TABLAS["tasa_libre_riesgo"] = df.to_dict(orient="records")


def _sembrar_usuario_prueba() -> None:
    if CORREO_PRUEBA in _USUARIOS:
        return
    user_id = str(uuid.uuid4())
    _USUARIOS[CORREO_PRUEBA] = {"id": user_id, "correo": CORREO_PRUEBA, "clave": CLAVE_PRUEBA}
    _tabla("perfiles").append(
        {
            "user_id": user_id,
            "alias": ALIAS_PRUEBA,
            "edad_rango": "25-34",
            "factores": {},
            "consentimiento_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


def _sembrar_usuario_a3() -> None:
    if CORREO_A3 in _USUARIOS:
        return
    user_id = str(uuid.uuid4())
    ahora = datetime.now(UTC).isoformat()
    _USUARIOS[CORREO_A3] = {"id": user_id, "correo": CORREO_A3, "clave": CLAVE_A3}
    _tabla("perfiles").append(
        {
            "user_id": user_id,
            "alias": ALIAS_A3,
            "edad_rango": "35-44",
            "factores": {},
            "consentimiento_at": ahora,
            "created_at": ahora,
        }
    )
    _tabla("encuestas").append(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "respuestas": RESPUESTAS_A3,
            "puntaje": 23,
            "perfil": "moderado_agresivo",
            "a": 3,
            "version_cuestionario": "v1",
            "created_at": ahora,
        }
    )


def _sembrar_todo() -> None:
    _sembrar_catalogo()
    _sembrar_precios_y_rf()
    _sembrar_usuario_prueba()
    _sembrar_usuario_a3()


class _RespuestaFalsa:
    def __init__(self, data: list[dict]):
        self.data = data


class _ConsultaFalsa:
    """Imita el *query builder* encadenable de `postgrest-py`."""

    def __init__(self, tabla: str, usuario_actual_ref: list[str | None], es_servicio: bool):
        self._tabla = tabla
        self._usuario_actual_ref = usuario_actual_ref
        self._es_servicio = es_servicio
        self._filtros: list[tuple[str, str, object]] = []
        self._orden: tuple[str, bool] | None = None
        self._limite: int | None = None
        self._modo: str | None = None
        self._payload: list[dict] | None = None
        self._on_conflict: str | None = None

    # -- construcción de la consulta ---------------------------------
    def select(self, _columnas: str = "*") -> "_ConsultaFalsa":
        self._modo = "select"
        return self

    def insert(self, payload: dict | list[dict]) -> "_ConsultaFalsa":
        self._modo = "insert"
        self._payload = payload if isinstance(payload, list) else [payload]
        return self

    def update(self, payload: dict) -> "_ConsultaFalsa":
        self._modo = "update"
        self._payload = payload
        return self

    def upsert(
        self, payload: dict | list[dict], on_conflict: str | None = None
    ) -> "_ConsultaFalsa":
        self._modo = "upsert"
        self._payload = payload if isinstance(payload, list) else [payload]
        self._on_conflict = on_conflict
        return self

    def delete(self) -> "_ConsultaFalsa":
        self._modo = "delete"
        return self

    def eq(self, columna: str, valor: object) -> "_ConsultaFalsa":
        self._filtros.append((columna, "eq", valor))
        return self

    def in_(self, columna: str, valores: list) -> "_ConsultaFalsa":
        self._filtros.append((columna, "in", valores))
        return self

    def gte(self, columna: str, valor: object) -> "_ConsultaFalsa":
        self._filtros.append((columna, "gte", valor))
        return self

    def order(self, columna: str, desc: bool = False) -> "_ConsultaFalsa":
        self._orden = (columna, desc)
        return self

    def limit(self, n: int) -> "_ConsultaFalsa":
        self._limite = n
        return self

    # -- ejecución -----------------------------------------------------
    def _filas_crudas(self) -> list[dict]:
        return _tabla(self._tabla)

    def _con_alcance_de_usuario(self, filas: list[dict]) -> list[dict]:
        if self._es_servicio or self._tabla not in TABLAS_DEL_USUARIO:
            return filas
        usuario_actual = self._usuario_actual_ref[0]
        return [f for f in filas if f.get("user_id") == usuario_actual]

    def _con_filtros(self, filas: list[dict]) -> list[dict]:
        for columna, operador, valor in self._filtros:
            if operador == "eq":
                filas = [f for f in filas if f.get(columna) == valor]
            elif operador == "in":
                filas = [f for f in filas if f.get(columna) in valor]
            elif operador == "gte":
                filas = [
                    f for f in filas if f.get(columna) is not None and str(f[columna]) >= str(valor)
                ]
        return filas

    def _seleccionar(self) -> list[dict]:
        filas = self._con_alcance_de_usuario(list(self._filas_crudas()))
        filas = self._con_filtros(filas)
        if self._orden:
            columna, desc = self._orden
            filas = sorted(filas, key=lambda f: f.get(columna) or "", reverse=desc)
        if self._limite is not None:
            filas = filas[: self._limite]
        return filas

    def _insertar(self) -> list[dict]:
        tabla = self._filas_crudas()
        insertadas = []
        for fila in self._payload or []:
            nueva = dict(fila)
            nueva.setdefault("id", str(uuid.uuid4()))
            nueva.setdefault("created_at", datetime.now(UTC).isoformat())
            if self._tabla in TABLAS_CON_USER_ID_UNICO and any(
                f.get("user_id") == nueva.get("user_id") for f in tabla
            ):
                raise APIError(
                    {
                        "message": f"duplicate key value violates unique constraint "
                        f"({self._tabla}.user_id)",
                        "code": "23505",
                    }
                )
            tabla.append(nueva)
            insertadas.append(nueva)
        return insertadas

    def _upsertar(self) -> list[dict]:
        tabla = self._filas_crudas()
        claves = (self._on_conflict or "id").split(",")
        resultado = []
        for fila in self._payload or []:
            existente = next(
                (f for f in tabla if all(f.get(c) == fila.get(c) for c in claves)), None
            )
            if existente:
                existente.update(fila)
                resultado.append(existente)
            else:
                nueva = dict(fila)
                tabla.append(nueva)
                resultado.append(nueva)
        return resultado

    def _actualizar(self) -> list[dict]:
        filas = self._con_filtros(self._con_alcance_de_usuario(self._filas_crudas()))
        for fila in filas:
            fila.update(self._payload or {})
        return filas

    def _borrar(self) -> list[dict]:
        tabla = self._filas_crudas()
        filas = self._con_filtros(self._con_alcance_de_usuario(list(tabla)))
        for fila in filas:
            tabla.remove(fila)
        return filas

    def execute(self) -> _RespuestaFalsa:
        _sembrar_todo()
        if self._modo == "select":
            return _RespuestaFalsa(self._seleccionar())
        if self._modo == "insert":
            return _RespuestaFalsa(self._insertar())
        if self._modo == "upsert":
            return _RespuestaFalsa(self._upsertar())
        if self._modo == "update":
            return _RespuestaFalsa(self._actualizar())
        if self._modo == "delete":
            return _RespuestaFalsa(self._borrar())
        raise RuntimeError(f"Operación no soportada por el mock: {self._modo}")


class _AuthFalso:
    def __init__(self, usuario_actual_ref: list[str | None]):
        self._usuario_actual_ref = usuario_actual_ref
        self.admin = SimpleNamespace(
            create_user=self._admin_crear_usuario,
            delete_user=self._admin_borrar_usuario,
            list_users=self._admin_listar_usuarios,
        )

    def _crear_sesion(self, user_id: str) -> tuple[str, str]:
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        _SESIONES[access_token] = user_id
        self._usuario_actual_ref[0] = user_id
        return access_token, refresh_token

    def sign_up(self, credenciales: dict) -> SimpleNamespace:
        correo, clave = credenciales["email"], credenciales["password"]
        if correo in _USUARIOS:
            raise ValueError("El correo ya está registrado")
        user_id = str(uuid.uuid4())
        _USUARIOS[correo] = {"id": user_id, "correo": correo, "clave": clave}
        access_token, refresh_token = self._crear_sesion(user_id)
        return SimpleNamespace(
            user=SimpleNamespace(id=user_id, email=correo),
            session=SimpleNamespace(access_token=access_token, refresh_token=refresh_token),
        )

    def sign_in_with_password(self, credenciales: dict) -> SimpleNamespace:
        correo, clave = credenciales["email"], credenciales["password"]
        usuario = _USUARIOS.get(correo)
        if not usuario or usuario["clave"] != clave:
            raise ValueError("Credenciales inválidas")
        access_token, refresh_token = self._crear_sesion(usuario["id"])
        return SimpleNamespace(
            user=SimpleNamespace(id=usuario["id"], email=correo),
            session=SimpleNamespace(access_token=access_token, refresh_token=refresh_token),
        )

    def set_session(self, access_token: str, _refresh_token: str) -> SimpleNamespace:
        user_id = _SESIONES.get(access_token)
        if user_id is None:
            raise ValueError("Sesión inválida o expirada")
        self._usuario_actual_ref[0] = user_id
        return SimpleNamespace(user=SimpleNamespace(id=user_id))

    def sign_out(self, _options: object = None) -> None:
        self._usuario_actual_ref[0] = None

    def _admin_crear_usuario(self, atributos: dict) -> SimpleNamespace:
        correo, clave = atributos["email"], atributos["password"]
        if correo in _USUARIOS:
            raise ValueError("El correo ya está registrado")
        user_id = str(uuid.uuid4())
        _USUARIOS[correo] = {"id": user_id, "correo": correo, "clave": clave}
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=correo))

    def _admin_borrar_usuario(self, user_id: str, should_soft_delete: bool = False) -> None:
        for correo, datos in list(_USUARIOS.items()):
            if datos["id"] == user_id:
                del _USUARIOS[correo]
        for nombre_tabla in TABLAS_DEL_USUARIO:
            _TABLAS[nombre_tabla] = [f for f in _tabla(nombre_tabla) if f.get("user_id") != user_id]

    def _admin_listar_usuarios(self, page: int = 1, per_page: int = 200) -> list[SimpleNamespace]:
        if page > 1:
            return []
        return [SimpleNamespace(id=d["id"], email=c) for c, d in _USUARIOS.items()]


class ClienteMock:
    """Reemplazo en memoria de `supabase.Client` para desarrollo local."""

    def __init__(self, es_servicio: bool = False):
        _sembrar_todo()
        self._es_servicio = es_servicio
        self._usuario_actual_ref: list[str | None] = [None]
        self.auth = _AuthFalso(self._usuario_actual_ref)
        self.postgrest = SimpleNamespace(auth=self._postgrest_auth)

    def _postgrest_auth(self, access_token: str) -> None:
        self._usuario_actual_ref[0] = _SESIONES.get(access_token)

    def table(self, nombre: str) -> _ConsultaFalsa:
        return _ConsultaFalsa(nombre, self._usuario_actual_ref, self._es_servicio)


def crear_cliente_mock(es_servicio: bool = False) -> ClienteMock:
    return ClienteMock(es_servicio=es_servicio)
