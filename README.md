# Robo-advisor — Taller 1 de Inversiones (EAFIT, 2026-II)

Proto robo-advisor: registro, cuestionario de aversión al riesgo, portafolio óptimo (Markowitz) con CAL, seguimiento y recomendaciones por reglas fijas.
Datos de Yahoo Finance cargados por un pipeline diario en Supabase; app en Streamlit. **Ejercicio académico; no constituye asesoría financiera.**

## Cómo arrancar con Claude Code
1. Abre `claude` en la carpeta. Lee primero `CLAUDE.md` y `docs/05-plan-entregables.md`.
2. Ejecuta los entregables en orden: `/entregable E00`, luego `/entregable E01`, etc. Cada uno se prueba y se commitea por separado.
3. Mientras se hacen E01/E02, E03 y E04 pueden avanzar en paralelo (no necesitan base de datos).

## Estado
- [x] **E00** — bootstrap del repo, tooling (`pyproject.toml`, `ruff`), CI mínimo y `config.py`.
- [ ] E01…E12 — ver `docs/05-plan-entregables.md`.

## Qué hay en este paquete
| Ruta | Contenido |
|---|---|
| `CLAUDE.md` | Contexto y reglas para Claude Code |
| `.claude/commands/entregable.md` | Comando `/entregable E0X` |
| `docs/00…06` | Requisitos, arquitectura, datos, motor, pipeline, plan, despliegue |
| `docs/entregables/E00…E12` | Especificación de cada entregable (alcance, pruebas, verificación, aceptación) |
| `supabase/migrations/0001_init.sql` | Esquema + RLS |
| `supabase/seed/activos.csv` | Catálogo inicial (24 filas; los tickers se verifican en E02) |
| `.env.example`, `.gitignore` | Variables y exclusiones |

## Antes de empezar (acciones humanas)
- Crear el proyecto Supabase gratuito y guardar las claves en `.env` (nunca en git).
- Crear el repo en GitHub (preferible privado).
- Enviar al profesor las preguntas de `docs/00-contexto-y-requisitos.md` §5.

## Aplicar el esquema (E01)
1. Copia `.env.example` a `.env` y completa `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
2. En el SQL Editor del proyecto Supabase, pega y ejecuta `supabase/migrations/0001_init.sql` (una sola vez).
3. Carga el catálogo: `python scripts/cargar_catalogo.py` (idempotente, usa `service_role`).
4. Verifica la seguridad: `pytest -m integration -q` (crea y borra usuarios de prueba).
5. (Opcional) Usuario fijo para probar la app en local sin pasar por el registro cada vez:
   `python scripts/crear_usuario_prueba.py` (correo `prueba@local.test`, clave `Prueba1234!`;
   `--borrar` para eliminarlo). Solo para desarrollo local.

## Modo mock (correr la app sin Supabase)
Para probar la app completa en local sin crear un proyecto Supabase:
```bash
MOCK_DATA=true streamlit run app/Inicio.py
```
Usa un cliente Supabase falso en memoria (`roboadvisor/data/cliente_mock.py`): se siembra solo
con el catálogo (`supabase/seed/activos.csv`) y, si existen, los precios reales de
`data_local/` (`python scripts/descargar_precios_prueba.py`, 10 años de los ETF del catálogo
— excluye `CIB`/`EC`, que son acciones ADR individuales, y la cripto `BTC-USD`/`ETH-USD`,
no ETF; `GXG` aparece deslistado en Yahoo, confirma el `VERIFICAR en E02` que ya tenía
anotado el catálogo). Entra con el usuario ya creado
`prueba@local.test` / `Prueba1234!`. Los datos viven solo en la memoria del proceso del
servidor y se pierden al reiniciarlo; los scripts sueltos (`cargar_catalogo.py`,
`crear_usuario_prueba.py`) no los ven porque corren en otro proceso. **No reemplaza** las
pruebas de RLS de `tests/db/test_rls.py`, que siguen corriendo solo contra un Supabase real.

## Fechas
Taller 1: **12-nov-2026** · Taller 2: 19-nov-2026 (incremental, después).
