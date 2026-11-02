# Robo-advisor — Taller 1 de Inversiones (EAFIT, 2026-II)

Proto robo-advisor: registro, cuestionario de aversión al riesgo, portafolio óptimo (Markowitz) con CAL, seguimiento y recomendaciones por reglas fijas.
Datos de Yahoo Finance cargados por un pipeline diario en Supabase; app en Streamlit. **Ejercicio académico; no constituye asesoría financiera.**

## Quickstart (jugar con la app en 5 minutos, sin Supabase)

Requiere Python ≥ 3.11.

```bash
git clone <url-del-repo>
cd robo-advisor
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python scripts/descargar_precios_prueba.py   # ~1 min, descarga 10 años de ETF reales de Yahoo
MOCK_DATA=true streamlit run app/Inicio.py
```

Abre `http://localhost:8501`. Inicia sesión con el usuario ya creado por el modo mock:
**correo `prueba@local.test`, clave `Prueba1234!`**. Todo corre en memoria (nada de Supabase,
nada de claves) — ver [Modo mock](#modo-mock-correr-la-app-sin-supabase) más abajo.

## Estado del proyecto
Motor financiero y app completos (E00–E09); falta Mi portafolio/seguimiento (E10), despliegue
(E11) y reporte (E12). Ver `docs/05-plan-entregables.md` para el detalle de cada entregable y
`docs/entregables/E0X-*.md` para sus criterios de aceptación marcados.

## Qué hay en este paquete
| Ruta | Contenido |
|---|---|
| `CLAUDE.md` | Contexto y reglas para Claude Code |
| `docs/00…06` | Requisitos, arquitectura, datos, motor, pipeline, plan, despliegue |
| `docs/entregables/E00…E12` | Especificación de cada entregable (alcance, pruebas, verificación, aceptación) |
| `src/roboadvisor/core/` | Motor financiero puro (cuestionario, Markowitz, riesgo, recomendaciones) |
| `src/roboadvisor/data/` | Supabase, Yahoo Finance y el cliente mock |
| `src/roboadvisor/pipeline/` | Carga diaria de precios/fundamentales |
| `app/` | App Streamlit (multipágina) |
| `tests/` | `pytest -q` (unitarias) y `pytest -m integration -q` (requieren Supabase real) |
| `supabase/migrations/0001_init.sql` | Esquema + RLS |
| `supabase/seed/activos.csv` | Catálogo inicial (23 filas, sin GXG; los tickers se verifican en E02) |
| `.env.example`, `.gitignore` | Variables y exclusiones (nunca se commitea `.env`) |

## Correr las pruebas
```bash
pytest -q && ruff check .
```
100+ pruebas unitarias, sin red ni Supabase. Las de integración (`-m integration`, RLS real)
se saltan automáticamente si no hay `.env`.

## Modo mock (correr la app sin Supabase)
Para desarrollo/demo sin un proyecto Supabase real:
```bash
MOCK_DATA=true streamlit run app/Inicio.py
```
Usa un cliente Supabase falso en memoria (`roboadvisor/data/cliente_mock.py`): se siembra con
el catálogo (`supabase/seed/activos.csv`) y, si existen, los precios reales de `data_local/`
(corre primero `python scripts/descargar_precios_prueba.py` — 10 años de los ETF del catálogo;
excluye `CIB`/`EC`, acciones ADR individuales, y la cripto `BTC-USD`/`ETH-USD`, que no son ETF;
`GXG` suele aparecer deslistado en Yahoo, consistente con el `VERIFICAR en E02` que ya tenía
anotado el catálogo). Entra con `prueba@local.test` / `Prueba1234!`, o con `a3@local.test` / `Prueba1234!` (encuesta ya hecha, A = 3, sin portafolio: listo para armarlo).

Los datos viven solo en la memoria del proceso del servidor y **se pierden al reiniciarlo**;
`data_local/` está en `.gitignore`, cada quien la descarga localmente. Los scripts sueltos
(`cargar_catalogo.py`, `crear_usuario_prueba.py`) no ven los datos del mock porque corren en
otro proceso — son para el flujo con Supabase real. **El modo mock no reemplaza** las pruebas
de RLS de `tests/db/test_rls.py`, que siguen corriendo solo contra un Supabase real.

## Conectar un Supabase real (para el entregable final)
1. Crear el proyecto Supabase gratuito (acción humana).
2. Copiar `.env.example` a `.env` y completar `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY` (nunca se commitea).
3. En el SQL Editor del proyecto, pegar y ejecutar `supabase/migrations/0001_init.sql` (una sola vez).
4. Cargar el catálogo: `python scripts/cargar_catalogo.py` (idempotente, usa `service_role`).
5. Verificar la seguridad: `pytest -m integration -q` (crea y borra usuarios de prueba).
6. (Opcional) Usuario fijo para no pasar por el registro cada vez:
   `python scripts/crear_usuario_prueba.py` (mismo correo/clave que el modo mock;
   `--borrar` para eliminarlo). Solo para desarrollo local.
7. Cargar precios reales: `python -m roboadvisor.pipeline.update_prices` (ver `docs/04`).

## Cómo arrancar con Claude Code
1. Abre `claude` en la carpeta. Lee primero `CLAUDE.md` y `docs/05-plan-entregables.md`.
2. Ejecuta los entregables en orden: `/entregable E00`, luego `/entregable E01`, etc. Cada uno se prueba y se commitea por separado.

## Fechas
Taller 1: **12-nov-2026** · Taller 2: 19-nov-2026 (incremental, después).
