# 06 · Despliegue y operación

Estrategia (actualizada 2026-11-01, ver `docs/05-plan-entregables.md` §"Orden
real seguido"): **primero desplegar con datos mock para que el equipo dé
feedback**, y solo al final —cuando la app ya esté validada— conectar el
proyecto Supabase real. Antes seguíamos el orden inverso (Supabase real desde
E01); se invirtió porque conectar la base de datos real es la parte más lenta
de deshacer si algo cambia, mientras que el modo mock (`MOCK_DATA=true`, ver
`data/cliente_mock.py`) ya se comporta igual que producción para cualquier
flujo de usuario (incluye su propio filtrado por `user_id`).

## Fase A — Local con datos mock (E00–E10)
Sin Supabase: `MOCK_DATA=true streamlit run app/Inicio.py` (ver quickstart del
`README.md`). Mismo flujo de usuario, mismas pruebas manuales; los datos viven
en memoria del proceso y se pierden al reiniciar — adecuado para iterar rápido
y para que el equipo pruebe sin necesitar credenciales de nadie.

## Fase B — Despliegue de feedback con datos mock (E11, primera mitad)
Objetivo: una URL que el equipo pueda abrir para dar feedback, **sin** depender
de un proyecto Supabase real todavía.
1. Repo en GitHub (puede ser público: no hay secretos ni datos de usuarios reales en modo mock).
2. share.streamlit.io → New app → repo, rama `master`, archivo `app/Inicio.py`.
3. Secret de la app (Advanced settings → Secrets): `MOCK_DATA = "true"`. No se necesita ninguna credencial de Supabase en esta fase.
4. Compartir la URL con el equipo; recoger feedback antes de pasar a la Fase C.

Limitación conocida: los datos (usuarios, encuestas, portafolios) se reinician
cada vez que Streamlit Community Cloud duerme/reinicia la app — aceptable para
feedback de UX, no para los 5 voluntarios reales (eso espera a la Fase C).

## Fase C — Conectar Supabase real (al final, antes de E12)
1. **Supabase:** crear proyecto gratuito. En Authentication → Providers: email habilitado; para desarrollo desactivar "Confirm email" (o usar correos reales). Anotar URL, `anon` key y `service_role` key.
2. **Esquema:** pegar `supabase/migrations/0001_init.sql` en el SQL Editor y ejecutar; luego importar `supabase/seed/activos.csv` en la tabla `activos` (Table Editor → Import) o ejecutar el script de E01.
3. **`.env`:** copiar `.env.example` → `.env` y completar. El `service_role` solo se usa al correr el pipeline en tu máquina.
4. **Datos:** `python -m roboadvisor.pipeline.update_prices` (primera carga histórica).
5. **App:** `streamlit run app/Inicio.py`. Registrar usuarios de prueba (no los 5 voluntarios aún).
6. **Pruebas:** `pytest -q` (sin red) y recorrido manual de los 3 flujos (primer ingreso, reingreso, datos viejos).

## Fase D — Promoción a producción con datos reales (E11, segunda mitad / E12)
Criterios para promover (todos):
- [ ] `pytest` y `ruff` verdes en CI.
- [ ] Pipeline corrió ≥ 3 días hábiles seguidos desde GitHub Actions sin error.
- [ ] RLS verificada (usuario A no ve nada de usuario B; `anon` no lee nada).
- [ ] Flujo completo probado local con al menos 2 usuarios de prueba.
- [ ] `README` con instrucciones y aviso de ejercicio académico.

Pasos:
1. Repo en GitHub (preferible **privado**; si Streamlit Community Cloud exigiera público, confirmar que no hay datos ni secretos en el historial: `git log -p | grep -i service_role` debe salir vacío).
2. Secretos del repo (GitHub → Settings → Secrets → Actions): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`. Activar `pipeline.yml`.
3. share.streamlit.io → New app → repo, rama `main`, archivo `app/Inicio.py`. `requirements.txt` en la raíz con `-e .` o la lista de dependencias.
4. Secrets de la app (Advanced settings → Secrets, formato TOML):
   ```toml
   SUPABASE_URL = "https://..."
   SUPABASE_ANON_KEY = "eyJ..."
   ```
   **No** poner `service_role` aquí.
5. En Supabase → Authentication → URL Configuration: agregar la URL de la app como *Site URL*/redirect.
6. Prueba de humo en producción: registro, encuesta, portafolio, reingreso.

## Operación
| Tarea | Cuándo | Cómo |
|---|---|---|
| Revisar corrida del pipeline | Diario (1 min) | Pestaña Actions o "Estado de datos" en la app |
| Despertar la app | 10 min antes de presentar | Abrir la URL (Streamlit duerme tras ~12 h sin tráfico) |
| Respaldo de datos de usuarios | Antes de sustentar y tras encuestar a los voluntarios | Table Editor → Export CSV de `perfiles`, `encuestas`, `portafolios`; guardar **fuera** del repo |
| Evitar pausa de Supabase | Automático con el cron | Si hay vacaciones > 7 días sin ejecuciones, abrir el proyecto en el dashboard |
| Rotar claves | Si se filtra alguna | Supabase → Settings → API → regenerar; actualizar secretos |

## Runbook de fallos
- **Pipeline falla:** abrir el log; casos típicos: Yahoo limitó (reintentar con `workflow_dispatch`), ticker deslistado (marcar `activo=false`), clave vencida. La app sigue funcionando con los últimos datos y la regla R5 avisa.
- **App muestra "datos desactualizados":** correr el pipeline a mano.
- **Proyecto Supabase pausado:** restaurar desde el dashboard (no se pierden datos), correr el pipeline.
- **Usuario no puede registrarse:** revisar "Confirm email", límites de correos del proveedor SMTP por defecto de Supabase (bajos) y URL de redirección.

## Plan B para la sustentación
Tener la app corriendo en local con el mismo `.env` y un `exports/` con capturas/CSV del resultado de los 5 voluntarios, por si falla internet o el hosting.

## Costos
$0. Único gasto opcional: Supabase Pro ($25/mes) para backups, no necesario para la entrega.
