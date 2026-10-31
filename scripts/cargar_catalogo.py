"""Carga (upsert, idempotente) `supabase/seed/activos.csv` en la tabla `activos`.

Usa `service_role` (ignora RLS): solo correr desde la máquina del
administrador o el pipeline, nunca desde la app. Requiere `SUPABASE_URL` y
`SUPABASE_SERVICE_ROLE_KEY` en `.env`.
"""

from roboadvisor.data.cliente import cliente_servicio
from roboadvisor.data.semillas import leer_catalogo as cargar_filas


def main() -> None:
    filas = cargar_filas()
    cliente = cliente_servicio()
    resultado = cliente.table("activos").upsert(filas, on_conflict="ticker").execute()
    print(f"Catálogo cargado: {len(resultado.data)} filas (upsert sobre 'ticker').")


if __name__ == "__main__":
    main()
