"""Crea (o actualiza) la cuenta de administrador compartida y la marca en `public.administradores`.

Requiere haber aplicado `supabase/migrations/0004_administradores.sql`. Usa `service_role`: correr
solo desde la máquina del administrador, nunca desde la app. La clave no se guarda en el
repositorio: se pasa por argumento o se genera una al azar y se imprime una sola vez.

    python scripts/taller1/crear_admin.py --correo admin@mft-investments.app
    python scripts/taller1/crear_admin.py --correo admin@mft-investments.app --clave "..."
    python scripts/taller1/crear_admin.py --correo admin@mft-investments.app --quitar
"""

import argparse
import secrets
import string
from datetime import UTC, datetime

from roboadvisor.comun.cliente import cliente_servicio


def _buscar(c, correo: str):
    pagina = 1
    while True:
        usuarios = c.auth.admin.list_users(page=pagina, per_page=200)
        for u in usuarios:
            if (u.email or "").lower() == correo.lower():
                return u
        if len(usuarios) < 200:
            return None
        pagina += 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--correo", required=True)
    ap.add_argument("--clave", help="si se omite, se genera una al azar")
    ap.add_argument("--alias", default="Administrador")
    ap.add_argument("--quitar", action="store_true", help="quita el rol (no borra la cuenta)")
    a = ap.parse_args()

    c = cliente_servicio()
    u = _buscar(c, a.correo)
    if a.quitar:
        if u:
            c.table("administradores").delete().eq("user_id", u.id).execute()
        print("Rol de administrador quitado." if u else "No existe esa cuenta.")
        return

    alfabeto = string.ascii_letters + string.digits
    clave = a.clave or "".join(secrets.choice(alfabeto) for _ in range(14)) + "!7"
    if u is None:
        u = c.auth.admin.create_user(
            {"email": a.correo, "password": clave, "email_confirm": True}
        ).user
        creada = True
    else:
        c.auth.admin.update_user_by_id(u.id, {"password": clave})
        creada = False
    # Perfil mínimo (sin encuesta): así la app lo reconoce y no aparece entre los voluntarios
    if not c.table("perfiles").select("user_id").eq("user_id", u.id).execute().data:
        c.table("perfiles").insert(
            {
                "user_id": u.id,
                "alias": a.alias,
                "edad_rango": "otro",
                "factores": {},
                "consentimiento_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
    c.table("administradores").upsert({"user_id": u.id}).execute()
    print(f"Cuenta {'creada' if creada else 'actualizada'}: {a.correo}")
    print(f"Clave: {clave}")


if __name__ == "__main__":
    main()
