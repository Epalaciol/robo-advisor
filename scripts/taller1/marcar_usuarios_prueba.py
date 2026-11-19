"""Marca las cuentas de prueba (`@local.test`) para que la página de administración no las muestre.

La vista de administrador no ve correos, así que la marca va en el perfil: `factores._prueba = true`
(no cambia el esquema ni se muestra como factor). Idempotente. Usa `service_role`: correr solo desde
la máquina del administrador.

    python scripts/taller1/marcar_usuarios_prueba.py
"""

from roboadvisor.comun.cliente import cliente_servicio

SUFIJO_PRUEBA = "@local.test"


def main() -> None:
    c = cliente_servicio()
    correos = {u.id: (u.email or "") for u in c.auth.admin.list_users(per_page=1000)}
    perfiles = c.table("perfiles").select("user_id, alias, factores").execute().data
    marcados = 0
    for p in perfiles:
        if not correos.get(p["user_id"], "").endswith(SUFIJO_PRUEBA):
            continue
        factores = {**(p["factores"] or {}), "_prueba": True}
        c.table("perfiles").update({"factores": factores}).eq("user_id", p["user_id"]).execute()
        marcados += 1
        print(f"  - {p['alias']}")
    print(f"{marcados} cuentas de prueba marcadas.")


if __name__ == "__main__":
    main()
