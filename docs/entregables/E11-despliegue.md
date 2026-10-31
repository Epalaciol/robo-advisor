# E11 · Despliegue, CI/CD y endurecimiento

**Depende de:** E10 y pipeline corriendo ≥ 3 días hábiles · **Rama:** `e11-despliegue` · **Commit:** `chore: E11 despliegue en Streamlit Cloud y endurecimiento`

## Objetivo
Promover a producción lo que ya está estable en local, siguiendo `docs/06-despliegue-y-operacion.md` (Fase B).

## Alcance
- **CI:** `ci.yml` ya corre `ruff` + `pytest`; agregar un job opcional manual para las pruebas de integración (`workflow_dispatch`, con secretos de un proyecto de pruebas).
- **Auditoría de seguridad** (script `scripts/auditar_repo.sh` o checklist en el PR): sin claves en el historial (`git log -p | grep -iE "service_role|eyJ"` vacío), `.env` ignorado, políticas RLS aplicadas y verificadas otra vez con `pytest -m integration`.
- **Streamlit Cloud:** crear la app apuntando a `app/Inicio.py`, rama `main`; cargar secretos `SUPABASE_URL` y `SUPABASE_ANON_KEY` (sin `service_role`); verificar que arranca con `requirements.txt`.
- **Supabase:** URL de la app en *URL Configuration*; reactivar "Confirm email" si se desea (probar el flujo) o dejarlo documentado como decisión.
- **Pipeline:** confirmar que el cron corrió ≥ 3 días hábiles seguidos; registrar en `docs/06` la fecha.
- **Prueba de humo en producción** con 2 usuarios nuevos: registro, encuesta, portafolio, reingreso.
- **README final** con URL de la app, instrucciones locales, arquitectura resumida y aviso académico.
- **Exportar respaldo** de `perfiles`, `encuestas`, `portafolios` a `exports/` (ignorado por git) como ensayo del respaldo.
- Página "Acerca de / metodología" dentro de la app con enlaces a las fórmulas (resumen de `docs/03`).

## Fuera de alcance
Dominio propio, monitoreo avanzado, pagos, nuevos features.

## Verificación
- [ ] La URL pública funciona desde otro dispositivo/red.
- [ ] Un usuario de producción no ve datos de otro (probar con dos cuentas).
- [ ] Tras dormir la app, abrirla la despierta correctamente.
- [ ] `git log -p | grep -iE "service_role|eyJ"` no devuelve claves reales.
- [ ] El workflow programado se ve en la pestaña Actions con ≥ 3 corridas exitosas.

## Criterios de aceptación
- [ ] Criterios de promoción de `docs/06` §Fase B marcados.
- [ ] Plan B local documentado y probado (app en local con el mismo `.env`).
- [ ] Respaldo exportado y guardado fuera del repo.
