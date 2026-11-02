"""Lectura paginada: PostgREST (Supabase) devuelve como máximo 1000 filas por consulta."""

TAMANO_PAGINA = 1000


def leer_todo(construir_consulta) -> list[dict]:
    """Ejecuta `construir_consulta()` (debe devolver una consulta NUEVA y con
    orden determinista) por páginas con `.range()` hasta agotar las filas."""
    filas: list[dict] = []
    inicio = 0
    while True:
        pagina = construir_consulta().range(inicio, inicio + TAMANO_PAGINA - 1).execute().data
        filas.extend(pagina)
        if len(pagina) < TAMANO_PAGINA:
            return filas
        inicio += TAMANO_PAGINA
