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

## Fechas
Taller 1: **12-nov-2026** · Taller 2: 19-nov-2026 (incremental, después).
