# E01 · Supabase: esquema, RLS, seed y pruebas de seguridad

**Depende de:** E00 · **Rama:** `e01-supabase` · **Commit:** `feat(db): E01 esquema, RLS y catálogo inicial`

## Objetivo
Tener el proyecto Supabase real con el esquema aplicado, el catálogo cargado y la seguridad **demostrada** con pruebas.

## Acciones manuales (las hace una persona, Claude Code solo guía)
1. Crear proyecto Supabase gratuito; habilitar email; desactivar "Confirm email" en desarrollo.
2. Copiar URL, `anon` key y `service_role` key a `.env` (no commitear).

## Alcance (lo que implementa Claude Code)
- Revisar `supabase/migrations/0001_init.sql` (ya provisto) y aplicarlo. Si algo falla en Supabase, **corregir en una migración nueva o en el 0001 si aún no se aplicó en ninguna base**, y avisar.
- `scripts/aplicar_migraciones.py` (opcional, usa `SUPABASE_DB_URL` con `psycopg`) o instrucciones claras para el SQL Editor.
- `scripts/cargar_catalogo.py`: lee `supabase/seed/activos.csv` y hace upsert en `activos` con `service_role`. Tipos: `es_renta_fija` y `activo` booleanos, `duration` vacío → `NULL`.
- `src/roboadvisor/data/cliente.py`:
  - `cliente_anon()` y `cliente_servicio()` (el segundo falla si no hay `service_role`).
  - `cliente_usuario(access_token)` que devuelve un cliente con el JWT puesto (para que RLS aplique).
- Pruebas de integración `tests/db/test_rls.py` marcadas `@pytest.mark.integration` (se saltan si no hay `.env`):
  1. `anon` no puede leer `activos` ni `perfiles`.
  2. Usuario A inserta su perfil/encuesta; usuario B no los ve.
  3. Usuario A no puede actualizar ni borrar su `encuesta` ni su `portafolio`.
  4. Usuario A no puede insertar un portafolio con la `encuesta_id` de B.
  5. Usuario autenticado puede leer `activos`/`precios` pero no escribir.
  6. Segundo portafolio del mismo usuario falla por `unique(user_id)`.
  Los usuarios de prueba se crean y se **eliminan** al terminar (con `service_role`).
- Registrar `markers = integration` en `pyproject.toml`.

## Fuera de alcance
Pipeline, motor, UI.

## Pruebas
`pytest -q` (sin `.env`) debe seguir pasando saltando las de integración; `pytest -m integration -q` con `.env` debe pasar todo.

## Verificación local
```bash
python scripts/cargar_catalogo.py
pytest -m integration -q
```
Revisar en el Table Editor que `activos` tiene 24 filas (22 invertibles activos, `ACWI` como benchmark y `TES_COP` con `activo=false`).

## Criterios de aceptación
- [ ] Esquema aplicado sin errores; RLS habilitada en las 8 tablas. **Pendiente**: requiere que crees el proyecto Supabase real y ejecutes la migración (acción humana, ver README §"Aplicar el esquema").
- [ ] Catálogo cargado (rerun idempotente). **Código listo y probado offline** (`tests/test_cargar_catalogo.py`); falta correrlo contra un proyecto real.
- [ ] Las 6 pruebas de RLS pasan contra el proyecto real. **Pendiente**: las 6 pruebas están escritas y se saltan automáticamente sin `.env`; no se han ejecutado contra una base real.
- [x] `service_role` no aparece en ningún archivo versionado.
