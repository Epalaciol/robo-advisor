# 05 · Plan de entregables

Cada entregable es **probable y commiteable por sí solo**: deja el repo en verde (`pytest`, `ruff`) y se verifica en local. Se ejecutan con Claude Code: `/entregable E03`.

## Mapa y dependencias

| ID | Entregable | Depende de | Se prueba con | Estimado |
|---|---|---|---|---|
| E00 | Bootstrap del repo, tooling y CI | — | `pytest`, `ruff` | 1–2 h |
| E01 | Supabase: esquema, RLS, seed, pruebas de RLS | E00 | script SQL + pruebas de RLS | 2–3 h |
| E02 | Pipeline de datos + verificación del catálogo + workflow | E01 | `--dry-run`, carga real local, pytest con mocks | 3–4 h |
| E03 | Motor: cuestionario, puntaje, utilidad | E00 | pytest | 1–2 h |
| E04 | Motor: estimación, Markowitz, frontera, CAL, `y*` | E00 | pytest (+ datos sintéticos) | 4–5 h |
| E05 | Motor: betas, duration, métricas, seguimiento | E04 | pytest | 3 h |
| E06 | Motor: múltiplos y recomendaciones | E05 | pytest | 3 h |
| E07 | App: esqueleto, autenticación, consentimiento, estado de datos | E01, E02 | manual local | 3 h |
| E08 | App: encuesta y guardado | E03, E07 | manual local + pytest de la capa de datos | 2–3 h |
| E09 | App: constructor de portafolio, gráficos y guardado | E02, E04, E05, E08 | manual local | 4–5 h |
| E10 | App: Mi portafolio, comportamiento y recomendaciones | E06, E09 | manual local | 3–4 h |
| E11 | Despliegue: CI/CD, Streamlit Cloud, hardening, prueba de humo | E10 | checklist de `06` | 2–3 h |
| E12 | Reporte (PDF/Excel), datos de los 5 voluntarios, guion de sustentación | E10 | revisión humana | 4–6 h |

`E03`, `E04` no necesitan base de datos: se pueden hacer **en paralelo** con E01/E02 (otra persona del grupo o un worktree distinto).

## Orden real seguido (actualizado 2026-11-01)
El esquema y las migraciones de E01 ya están escritos y commiteados, pero
**no se ha creado un proyecto Supabase real todavía** — E00–E10 se
desarrollaron y probaron contra el cliente mock en memoria
(`MOCK_DATA=true`, ver `data/cliente_mock.py`), que respeta el mismo
filtrado por usuario que tendría RLS. Decisión: desplegar con datos mock
(ver `docs/06-despliegue-y-operacion.md` Fase B) para que el equipo dé
feedback de UX con una URL real, **antes** de gastar tiempo conectando un
proyecto Supabase real — conectar Supabase real es la parte más cara de
deshacer si algo del modelo de datos cambia con el feedback. Conectar
Supabase real (Fase C de `06`) y correr el pipeline en vivo pasa a ser lo
**último** antes de E12, en vez de un prerrequisito de E07.

```
E00 ─┬─ E01 ── E02 ─────────────┐
     ├─ E03 ──────────────┐     │
     └─ E04 ── E05 ── E06 ┼─────┼── E07 ─ E08 ─ E09 ─ E10 ─ E11 ─ E12
                          └─────┘
```
(E07 requiere E01+E02; E08 requiere E03; E09 requiere E04–E05; E10 requiere E06.)

## Cronograma sugerido (hoy es viernes 30-oct; entrega jueves 12-nov)

| Día | Foco | Entregables |
|---|---|---|
| Sáb 31-oct | Fundaciones y motor | E00, E01, E03, inicio E04 |
| Dom 1-nov | Datos y motor | E02 (primera carga real), E04, E05 |
| Lun 2 – mar 3 | Motor y app base | E06, E07 |
| Mié 4 – vie 6 | App completa | E08, E09 |
| Sáb 7 – dom 8 | Seguimiento y recomendaciones | E10; **voluntarios empiezan la encuesta** |
| Lun 9 – mar 10 | Despliegue | E11 (pipeline ≥ 3 días ya corriendo desde el 6-nov) |
| Mié 11 – jue 12 | Reporte y entrega | E12 |

Holgura: si algo se atrasa, **recortar en este orden**: (1) E06 múltiplos, (2) gráficos adicionales de E10, (3) despliegue en nube (entregar corriendo en local + Plan B). Lo que no se recorta: E03–E05, E08–E09 y el PDF.

Para tener ≥ 3 días de pipeline corriendo antes de E11, **activar el workflow apenas termine E02** (aunque sea en el repo privado).

## Definition of Done (aplica a todos)
- [ ] Criterios de aceptación del entregable cumplidos y marcados.
- [ ] `pytest -q` y `ruff check .` en verde.
- [ ] Verificación local ejecutada y resultado real reportado.
- [ ] Sin secretos ni datos de usuarios en el diff.
- [ ] Docs actualizados si cambió una decisión (00–04).
- [ ] Commit con mensaje convencional (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).

## Convenciones de Git
- Rama `main` protegida por CI (cuando exista) y una rama por entregable: `e03-cuestionario`. Merge por PR o squash.
- Un commit (o PR) por entregable, con el ID en el mensaje: `feat(core): E03 cuestionario y utilidad`.

## Reparto sugerido para 4 personas (opcional)
1. Datos/infra: E01, E02, E11.
2. Motor financiero: E03, E04, E05.
3. App: E07, E08, E09, E10.
4. Reglas, múltiplos, encuestas a voluntarios y reporte: E06, E12.
