# Guía técnica — MFT Investments · Robo-advisor (Taller 1, Inversiones EAFIT)

> Para la guía de uso orientada al profesor, ver el [README principal](README.md).
> Este documento explica cómo levantar el proyecto, su estructura y las tecnologías.

Proto robo-advisor: registro, cuestionario de aversión al riesgo, portafolio óptimo (Markowitz) con CAL, seguimiento y recomendaciones por reglas fijas.
Datos de Yahoo Finance cargados por un pipeline diario en Supabase; app en Streamlit. **Ejercicio académico; no constituye asesoría de inversión.**

## Tecnologías
| Capa | Herramientas |
|---|---|
| Motor financiero | Python 3.11+, numpy, pandas, scipy (SLSQP), covarianza muestral |
| App | Streamlit (multipágina), plotly |
| Datos | Supabase (Postgres + Auth + RLS), `supabase-py`, `yfinance` |
| Automatización | GitHub Actions (cron 22:23 UTC ≈ 5:23 pm Bogotá, con respaldo) |
| Calidad | pytest, ruff, CI en GitHub Actions |

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
Motor financiero y app completos, con Supabase real conectado, datos de Yahoo cargados y el
pipeline diario activo en GitHub Actions. Pendiente: verificación de tickers con el profesor,
pruebas finales en producción y reporte. Ver `docs/05-plan-entregables.md`.

## Qué hay en este paquete
| Ruta | Contenido |
|---|---|
| `docs/00…06` | Requisitos, arquitectura, datos, motor, pipeline, plan, despliegue |
| `src/roboadvisor/core/` | Motor financiero puro (cuestionario, Markowitz, riesgo, recomendaciones) |
| `src/roboadvisor/data/` | Supabase, Yahoo Finance y el cliente mock |
| `src/roboadvisor/pipeline/` | Carga diaria de precios/fundamentales |
| `app/` | App Streamlit (multipágina): `Inicio.py`, `pages/`, `ui/` (componentes), `static/` (logo) |
| `.streamlit/config.toml` | Tema de la app (colores de la marca) |
| `tests/` | `pytest -q` (unitarias) y `pytest -m integration -q` (requieren Supabase real) |
| `supabase/migrations/` | `0001_init.sql` (esquema + RLS) y `0002_rangos_edad.sql` |
| `supabase/seed/activos.csv` | Catálogo inicial (23 filas, sin GXG; los tickers los valida el profesor) |
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
el catálogo es solo ETF;
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
3. En el SQL Editor del proyecto, ejecutar en orden `supabase/migrations/0001_init.sql` y `0002_rangos_edad.sql` (una sola vez cada una).
4. Cargar el catálogo: `python scripts/cargar_catalogo.py` (idempotente, usa `service_role`).
5. Verificar la seguridad: `pytest -m integration -q` (crea y borra usuarios de prueba).
6. (Opcional) Usuario fijo para no pasar por el registro cada vez:
   `python scripts/crear_usuario_prueba.py` (mismo correo/clave que el modo mock;
   `--borrar` para eliminarlo). Solo para desarrollo local.
   Para probar cada perfil: `python scripts/usuarios_demo.py` crea en la base 6 usuarios fijos
   `@local.test` (clave `Prueba1234!`): `prueba@` (sin encuesta), `demo.a8@`, `demo.a6@`,
   `demo.a4@`, `a3@` y `demo.a1@` (encuesta hecha, sin portafolio). `--reiniciar` los deja de
   cero (borra encuesta y portafolio) para volver a jugar; `--listar` muestra su estado;
   `--cambiar CORREO --a 1` (o `--puntaje 19`) le cambia el perfil de riesgo a un usuario.
7. Cargar precios reales: `python -m roboadvisor.pipeline.update_prices` (ver `docs/04`).

## Desplegar en Streamlit Community Cloud
1. share.streamlit.io → New app → repo, rama `master`, archivo `app/Inicio.py`.
2. Secrets (Settings → Secrets), solo la clave pública:
   ```toml
   SUPABASE_URL = "https://<proyecto>.supabase.co"
   SUPABASE_ANON_KEY = "sb_publishable_..."
   ```
   Para una demo sin base de datos usar solo `MOCK_DATA = "true"`. **Nunca** poner la clave `service_role`.
3. Tras cambios en módulos de `app/ui/` o `src/`, usar **Manage app → Reboot app** (Streamlit conserva módulos viejos en memoria).
4. Pipeline: en GitHub → Settings → Secrets → Actions crear `SUPABASE_URL`, `SUPABASE_ANON_KEY` y `SUPABASE_SERVICE_ROLE_KEY`; el workflow `pipeline.yml` corre de lunes a viernes.

## Fechas
Taller 1: **12-nov-2026** · Taller 2: 19-nov-2026 (incremental, después).
