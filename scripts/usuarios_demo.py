"""Crea (o reinicia) usuarios de demostración fijos directamente en Supabase.

Sirven para probar la app con cada perfil sin pasar por el registro ni la encuesta:
cada usuario tiene la encuesta ya respondida (A distinto) y *sin portafolio*, listo
para armarlo en el Constructor. `prueba@local.test` queda sin encuesta (flujo completo).

Todos terminan en `@local.test` y comparten la clave `CLAVE`. El script solo toca esos
correos: jamás modifica a usuarios reales.

Uso (con `.env` apuntando al proyecto Supabase):
    python scripts/usuarios_demo.py              # crea lo que falte
    python scripts/usuarios_demo.py --reiniciar  # borra encuesta/portafolio: todos de cero
    python scripts/usuarios_demo.py --listar     # muestra los usuarios y su estado
    python scripts/usuarios_demo.py --cambiar demo.a4@local.test --a 1      # le pone A=1
    python scripts/usuarios_demo.py --cambiar demo.a4@local.test --puntaje 19  # por puntaje

Usa `service_role` (ignora RLS): solo desde tu máquina, nunca en la app.
"""

import argparse
from datetime import UTC, datetime

from crear_usuario_prueba import _buscar_usuario

from roboadvisor.core.cuestionario import IDS_PREGUNTAS, puntuar
from roboadvisor.data.cliente import cliente_servicio
from roboadvisor.data.repositorio_usuario import RepositorioUsuario

CLAVE = "Prueba1234!"  # cuentas de demostración, no es un secreto real
SUFIJO_PERMITIDO = "@local.test"

# (correo, alias, rango de edad, puntaje objetivo de la encuesta o None = sin encuesta)
USUARIOS = [
    ("prueba@local.test", "Usuario de prueba", "25-34", None),
    ("demo.a8@local.test", "Demo A=8 (conservador)", "55-64", 10),
    ("demo.a6@local.test", "Demo A=6 (cons.-moderado)", "45-54", 14),
    ("demo.a4@local.test", "Demo A=4 (moderado)", "35-44", 18),
    ("a3@local.test", "Usuario A=3", "35-44", 23),
    ("demo.a1@local.test", "Demo A=1 (agresivo)", "25-34", 26),
    ("hist.a3@local.test", "Histórico A=3 (mod.-agresivo)", "35-44", 22),
]


def respuestas_para(puntaje: int) -> dict[str, str]:
    """Respuestas a/b/c que suman exactamente `puntaje` (a=1, b=2, c=3), 9 preguntas."""
    extra = puntaje - len(IDS_PREGUNTAS)
    respuestas = {}
    for id_pregunta in IDS_PREGUNTAS:
        paso = min(2, extra)
        respuestas[id_pregunta] = "abc"[paso]
        extra -= paso
    return respuestas


def _asegurar_usuario(admin, correo: str, alias: str, edad_rango: str) -> str:
    assert correo.endswith(SUFIJO_PERMITIDO), "Solo se permiten correos @local.test"
    user_id = _buscar_usuario(admin, correo)
    if user_id is None:
        creado = admin.auth.admin.create_user(
            {"email": correo, "password": CLAVE, "email_confirm": True}
        )
        user_id = creado.user.id
        RepositorioUsuario(admin).crear_perfil(
            user_id=user_id,
            alias=alias,
            edad_rango=edad_rango,
            consentimiento_at=datetime.now(UTC).isoformat(),
        )
        print(f"  creado   {correo}")
    return user_id


def _estado(admin, user_id: str) -> str:
    enc = admin.table("encuestas").select("a").eq("user_id", user_id).execute().data
    port = admin.table("portafolios").select("user_id").eq("user_id", user_id).execute().data
    encuesta = f"A={enc[0]['a']:g}" if enc else "sin encuesta"
    return f"{encuesta}, {'con' if port else 'sin'} portafolio"


def sembrar(reiniciar: bool) -> None:
    admin = cliente_servicio()
    for correo, alias, edad_rango, puntaje in USUARIOS:
        user_id = _asegurar_usuario(admin, correo, alias, edad_rango)

        if reiniciar:
            admin.table("portafolios").delete().eq("user_id", user_id).execute()
            admin.table("encuestas").delete().eq("user_id", user_id).execute()

        tiene_encuesta = admin.table("encuestas").select("user_id").eq("user_id", user_id)
        if puntaje is not None and not tiene_encuesta.execute().data:
            respuestas = respuestas_para(puntaje)
            r = puntuar(respuestas)
            admin.table("encuestas").insert(
                {
                    "user_id": user_id,
                    "respuestas": respuestas,
                    "puntaje": r.puntaje,
                    "perfil": r.perfil,
                    "a": r.a,
                    "version_cuestionario": "v1",
                }
            ).execute()
        print(f"  {correo:<24} {_estado(admin, user_id)}")
    print(f"\nClave de todos: {CLAVE}")


# Puntaje representativo de cada perfil (A -> puntaje dentro de su rango).
PUNTAJE_POR_A = {8: 10, 6: 14, 4: 18, 3: 22, 1: 26}


def cambiar_perfil(correo: str, puntaje: int) -> None:
    """Reemplaza la encuesta del usuario por una con `puntaje` y borra su portafolio
    (un portafolio armado con otro A ya no sería coherente)."""
    assert correo.endswith(SUFIJO_PERMITIDO), "Solo se permiten correos @local.test"
    admin = cliente_servicio()
    user_id = _buscar_usuario(admin, correo)
    if user_id is None:
        raise SystemExit(f"No existe {correo}. Corre primero: python scripts/usuarios_demo.py")

    respuestas = respuestas_para(puntaje)
    r = puntuar(respuestas)  # valida el rango 9-27
    admin.table("portafolios").delete().eq("user_id", user_id).execute()
    admin.table("encuestas").delete().eq("user_id", user_id).execute()
    admin.table("encuestas").insert(
        {
            "user_id": user_id,
            "respuestas": respuestas,
            "puntaje": r.puntaje,
            "perfil": r.perfil,
            "a": r.a,
            "version_cuestionario": "v1",
        }
    ).execute()
    print(f"  {correo}: puntaje {r.puntaje} -> {r.etiqueta} (A = {r.a}), sin portafolio")


def listar() -> None:
    admin = cliente_servicio()
    for correo, _, _, _ in USUARIOS:
        user_id = _buscar_usuario(admin, correo)
        print(f"  {correo:<24} {_estado(admin, user_id) if user_id else 'no existe'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Usuarios de demostración en Supabase")
    parser.add_argument("--reiniciar", action="store_true", help="Borra encuesta y portafolio")
    parser.add_argument("--listar", action="store_true", help="Solo muestra el estado")
    parser.add_argument("--cambiar", metavar="CORREO", help="Cambia el perfil de ese usuario")
    parser.add_argument("--a", type=int, choices=sorted(PUNTAJE_POR_A), help="A deseado")
    parser.add_argument("--puntaje", type=int, help="Puntaje de la encuesta (9-27)")
    args = parser.parse_args()

    if args.cambiar:
        puntaje = args.puntaje if args.puntaje is not None else PUNTAJE_POR_A.get(args.a)
        if puntaje is None:
            parser.error("--cambiar necesita --a (8, 6, 4, 3, 1) o --puntaje (9-27)")
        cambiar_perfil(args.cambiar, puntaje)
    elif args.listar:
        listar()
    else:
        sembrar(args.reiniciar)


if __name__ == "__main__":
    main()
