"""Crea (o borra) un usuario de prueba fijo para desarrollo local.

No hay rol "admin" en el esquema: cada usuario ve solo sus propios datos
(RLS). Esto solo da una cuenta con credenciales fijas para no pasar por el
formulario de registro cada vez que pruebas la app en local.

Usa `service_role` (ignora RLS): nunca correr esto contra un proyecto de
producción real, solo contra tu proyecto Supabase de desarrollo.

Uso:
    python scripts/crear_usuario_prueba.py
    python scripts/crear_usuario_prueba.py --correo otra@local.test --clave Otra1234!
    python scripts/crear_usuario_prueba.py --borrar
"""

import argparse
from datetime import UTC, datetime

from roboadvisor.data.cliente import cliente_servicio
from roboadvisor.data.repositorio_usuario import RepositorioUsuario

CORREO_POR_DEFECTO = "prueba@local.test"
CLAVE_POR_DEFECTO = "Prueba1234!"  # cuenta de desarrollo local, no es un secreto real
ALIAS_POR_DEFECTO = "Usuario de prueba"
EDAD_RANGO_POR_DEFECTO = "25-34"


def _buscar_usuario(admin, correo: str) -> str | None:
    """Busca un usuario existente por correo (la API admin no filtra por email,
    así que se pagina sobre `list_users`)."""
    pagina = 1
    while True:
        usuarios = admin.auth.admin.list_users(page=pagina, per_page=200)
        if not usuarios:
            return None
        for usuario in usuarios:
            if usuario.email == correo:
                return usuario.id
        pagina += 1


def crear(correo: str, clave: str, alias: str, edad_rango: str) -> None:
    admin = cliente_servicio()

    existente = _buscar_usuario(admin, correo)
    if existente:
        print(f"Ya existe un usuario con correo {correo} (id={existente}). No se creó de nuevo.")
        print(f"Correo: {correo}")
        print(f"Clave:  {clave} (si la cambiaste manualmente, esta puede no ser la vigente)")
        return

    creado = admin.auth.admin.create_user(
        {"email": correo, "password": clave, "email_confirm": True}
    )
    user_id = creado.user.id

    RepositorioUsuario(admin).crear_perfil(
        user_id=user_id,
        alias=alias,
        edad_rango=edad_rango,
        consentimiento_at=datetime.now(UTC).isoformat(),
    )

    print("Usuario de prueba creado.")
    print(f"Correo: {correo}")
    print(f"Clave:  {clave}")
    print("Solo para desarrollo local; no lo uses en producción.")


def borrar(correo: str) -> None:
    admin = cliente_servicio()
    user_id = _buscar_usuario(admin, correo)
    if not user_id:
        print(f"No se encontró ningún usuario con correo {correo}.")
        return
    admin.auth.admin.delete_user(user_id)
    print(f"Usuario {correo} (id={user_id}) eliminado (perfil/encuesta/portafolio en cascada).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Usuario de prueba fijo para desarrollo local")
    parser.add_argument("--correo", default=CORREO_POR_DEFECTO)
    parser.add_argument("--clave", default=CLAVE_POR_DEFECTO)
    parser.add_argument("--alias", default=ALIAS_POR_DEFECTO)
    parser.add_argument("--edad-rango", default=EDAD_RANGO_POR_DEFECTO, dest="edad_rango")
    parser.add_argument(
        "--borrar", action="store_true", help="Elimina el usuario en vez de crearlo"
    )
    args = parser.parse_args()

    if args.borrar:
        borrar(args.correo)
    else:
        crear(args.correo, args.clave, args.alias, args.edad_rango)


if __name__ == "__main__":
    main()
