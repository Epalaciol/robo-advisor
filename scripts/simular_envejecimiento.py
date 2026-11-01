"""Mueve `fecha_base` de un portafolio hacia atrás, para probar el seguimiento
de E10 sin esperar semanas de datos reales.

Usa `service_role` (ignora RLS): **nunca** correr esto contra un proyecto de
producción con usuarios reales, solo contra tu proyecto Supabase de desarrollo
con un usuario de prueba (ver `scripts/crear_usuario_prueba.py`).

En `MOCK_DATA=true` este script **no sirve para probar la app en vivo**: el
mock vive en memoria del proceso de `streamlit run` y este script corre en un
proceso aparte, así que no comparten estado (ver docstring de
`data/cliente_mock.py`). Para esa situación, usa el expander "🧪 Solo en modo
mock" que trae la propia página "Mi portafolio" — corre en el mismo proceso.

Uso:
    python scripts/simular_envejecimiento.py --correo prueba@local.test --dias 60
"""

import argparse
from datetime import timedelta

from roboadvisor.data.cliente import cliente_servicio


def _buscar_user_id(admin, correo: str) -> str | None:
    pagina = 1
    while True:
        usuarios = admin.auth.admin.list_users(page=pagina, per_page=200)
        if not usuarios:
            return None
        for usuario in usuarios:
            if usuario.email == correo:
                return usuario.id
        pagina += 1


def envejecer(correo: str, dias: int) -> None:
    admin = cliente_servicio()

    user_id = _buscar_user_id(admin, correo)
    if not user_id:
        print(f"No se encontró ningún usuario con correo {correo}.")
        return

    filas = admin.table("portafolios").select("*").eq("user_id", user_id).execute().data
    if not filas:
        print(f"El usuario {correo} no tiene portafolio guardado.")
        return

    portafolio = filas[0]
    from datetime import date

    fecha_actual = date.fromisoformat(str(portafolio["fecha_base"])[:10])
    nueva_fecha = (fecha_actual - timedelta(days=dias)).isoformat()

    admin.table("portafolios").update({"fecha_base": nueva_fecha}).eq(
        "user_id", user_id
    ).execute()

    print(f"fecha_base de {correo}: {fecha_actual} -> {nueva_fecha}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula envejecimiento de un portafolio de prueba")
    parser.add_argument("--correo", default="prueba@local.test")
    parser.add_argument("--dias", type=int, default=60)
    args = parser.parse_args()
    envejecer(args.correo, args.dias)


if __name__ == "__main__":
    main()
