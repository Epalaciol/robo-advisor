# Taller 2 · Renta fija: curva cero cupón Nelson-Siegel, TIR, señales y DV01

Entrega: **jueves 19-nov-2026**. Prof. Juan Carlos Botero. Enunciado: *TALLER 2 – Análisis de Renta Fija y Renta Variable*.
Esta carpeta es la planeación del Taller 2 dentro del robo-advisor. Se ejecuta igual que el Taller 1: `/entregable E15`, etc. (el comando busca `docs/taller-2/entregables/E15-*.md`; ver §5).

| Archivo | Qué es |
|---|---|
| `07-taller2-metodologia.md` | Convenciones del Excel del profesor, fórmulas, definiciones propias, hallazgos, preguntas abiertas |
| `08-pipeline-tes.md` | Cómo llegan los informes diarios de IRC a la base de datos |
| `entregables/E13…E18` | Una especificación por entregable |
| `anexos/fixtures/` | Datos de prueba: tabla del 2-oct (validada contra el enunciado) y el ejemplo del Excel del 17-mar |
| `anexos/0002_tes.sql`, `anexos/0002_tes_rls.sql` | Migración de las tablas de TES y su prueba de RLS (se mueven a `supabase/` en E14) |

## 1. Qué pide el enunciado y dónde se cumple

| # | Requisito (texto del enunciado) | Dónde | Cómo se demuestra |
|---|---|---|---|
| T1 | "Código que permita obtener los betas **para un día determinado**" | E15 (`calibrar`) + CLI `pipeline.taller2 --csv/--fecha` (E16) y `update_tes --fecha` (E14) | Correr con `--fecha 2026-10-02` imprime β0, β1, β2, τ |
| T2 | "…basados en la información disponible en www.irc.gov.co (informe diario del mercado secundario de TES)" | E13 (parser), E14 (descarga) | El informe se baja o se carga el PDF; validaciones de `08` |
| T3 | "Con dichos betas… calcular la **curva cero cupón** usando Nelson-Siegel" | E15 (`spot`, `curva`) | Curva 1…10.950 días, gráfico en E17/E18 |
| T4 | "Tomar **cada papel que se transó** en el día y calcular su **TIR usando la cero cupón**" | E16 (`tir` del precio estimado) | Columna TIR teórica por papel |
| T5 | "Comparar la **TIR observada** contra la **TIR estimada**… oportunidad de **compra, venta o mantener**" | E16 (`senal`) | Columna spread (pb) y señal |
| T6 | "Básense en el archivo de Excel Modelo Nelson Siegel.xlsx" | E15 (prueba dorada), E18 (Excel entregable) | Reproduce el Excel a 1e-8 en 24/26 papeles; Excel propio con fórmulas y Solver |
| T7 | "Pongan el modelo a prueba con las transacciones del **2 de octubre de 2026**" con **la tabla del enunciado** | `anexos/fixtures/tes_2026-10-02.csv`, E16, E18 | Resultados del 2-oct en el reporte |
| T8 | "Calcular el **DV01 de cada papel** transado ese día **por cada $1.000 millones** de valor nominal" | E16 (`dv01`) | DV01 en COP por pb, nominal 10⁹ COP |
| T9 | Objetivo: "familiarizarse con… curvas cero cupón y **duración y convexidad**" | E16 (duración, convexidad, aproximación de precio) | Tabla ΔP real vs. aproximación con D y con D+C |
| T10 | Objetivo: "analizar el mercado accionario" | — | **Sin tarea en el enunciado**: pregunta abierta (`07` §6) |
| T11 | Entrega 19-nov, grupos de 4 | E18 | PDF + Excel + código |

**Lo que agrega la app (no lo pide el enunciado):** pipeline diario (E14) y sección pública sin login (E17). Son lo primero que se recorta si falta tiempo.

## 2. Orden y ruta crítica

```
E15 ── E16 ──────────────┬── E18   ← ruta crítica (lo que se califica)
E13 ── E14 (DB + pipeline)─┴── E17   ← extras de la app
```
- **E15 → E16 → E18 no necesitan base de datos ni IRC**: corren con el CSV del 2-oct. Pueden empezar ya, en paralelo con el cierre del Taller 1 (E11/E12).
- E13 y E14 dan el "obtener del sitio" (T2) y el pipeline; E17 la página pública.
- **Si falta tiempo, recortar en este orden:** (1) descarga automática y cron (queda la carga manual de PDF/CSV), (2) OCR, (3) histórico de β en E17, (4) E17 completo. **No se recorta:** E15, E16, E18 y el parser de PDF (E13), que es la evidencia de T2.

| Fecha | Foco |
|---|---|
| Sáb 7 – dom 8 nov | E15 y E13 (una persona; no tocan el Taller 1) |
| Lun 9 – mié 11 | E16 + preguntas al profesor (`07` §6). Resto del grupo: E11/E12 del Taller 1 |
| Jue 12 | Entrega Taller 1 |
| Vie 13 – sáb 14 | E14 (primero `probar_irc.py`) |
| Dom 15 – lun 16 | E17 |
| Mar 17 – mié 18 | E18: reporte, Excel, revisión cruzada de cifras |
| Jue 19 | Entrega |

## 3. Cambios respecto a la versión anterior de estos documentos
- **Tabla del 2-oct validada:** las 29 filas del CSV coinciden campo por campo con la tabla del enunciado (que el enunciado declara como "la tabla a utilizar"). Σ nominal = 562.515.499 y promedio de variación 9,96 ≈ 10,0, igual que la fila de totales. Ya no es un bloqueo validar contra el PDF.
- **Convención de flujos confirmada con los datos:** el cupón corrido del informe (sucio − limpio) = cupón × días desde el último aniversario / 365 en 16 de 17 bonos (error ≤ 0,004); el TFIT 2050 difiere en ~1 día de cupón (0,02).
- **Ruta crítica sin base de datos:** E16 incluye el script del 2-oct desde el CSV; la persistencia de curvas y señales pasa a E14.
- **"Un día determinado":** CLI con `--fecha` (antes solo "el último informe").
- **Calibración más robusta:** varios puntos de partida; sensibilidad con ponderación por duración (el SSE en precios casi no "ve" los TCO cortos).
- **DV01:** sin tope fijo (puede superar $1.000.000 si bajan las tasas); prueba de escala por cociente con la duración modificada; se añade DV01 de curva (desplazamiento paralelo vía β0).
- **Duración y convexidad:** tabla de aproximación de precio ±50/±100 pb (objetivo del taller).
- **Modo mock:** la página pública debe funcionar con `MOCK_DATA=true` (la app está desplegada así).
- **Excel:** un solo generador (E18), listo para correr Solver; la prueba de fórmulas usa LibreOffice si está instalado.
- **Cron sin minuto 0** (GitHub descartó una corrida programada a las :00).

## 4. Fuera de `docs/` (hacer en el repo cuando toque)
1. **E14:** mover `anexos/0002_tes.sql` a `supabase/migrations/` con el **siguiente número libre** (si ya existe un `0002_*`, renombrar a `0003_tes.sql`), y `anexos/0002_tes_rls.sql` a `supabase/tests/`.
2. **E13/E15:** copiar `anexos/fixtures/*` a `tests/fixtures/`.
3. **`CLAUDE.md`** — agregar:
   ```markdown
   ## Taller 2 (entrega 19-nov)
   - Planeación en `docs/taller-2/` (README = trazabilidad y orden). Entregables E13–E18 en `docs/taller-2/entregables/`.
   - Ruta crítica E15 → E16 → E18 sin base de datos (CSV del 2-oct). E13/E14/E17 son extras de la app.
   - `core/tes/` es puro, igual que `core/`.
   - DV01 siempre por $1.000 millones = 10⁹ COP (no 10¹²). Prueba: DV01/((P/100)·N·1e-4) = D_mod.
   - La página pública de TES es la única sin `requerir_sesion()`; solo cliente anon y tablas `tes_*`; debe funcionar con `MOCK_DATA=true`.
   ```
4. **`.claude/commands/entregable.md`:** que busque también en `docs/taller-2/entregables/` (cambiar el paso 1 a `docs/**/entregables/$ARGUMENTS-*.md` o `docs/planificacion/` + `docs/taller-2/entregables/`).
5. **`.gitignore`:** `docs/planificacion/` está ignorado. Decidir si `docs/taller-2/` se versiona (no contiene secretos ni datos personales; recomendado versionarlo).

## 5. Definition of Done
La misma del Taller 1 (`docs/05-plan-entregables.md`): pruebas y `ruff` en verde, verificación local con resultado real, sin secretos en el diff, commit convencional con el ID (`feat(tes): E15 …`).
