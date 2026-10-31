# CLAUDE.md — Robo-advisor (Taller 1, Inversiones EAFIT)

Contexto para Claude Code. Léelo completo antes de tocar código.

## Qué es este proyecto
Proto robo-advisor para el Taller 1 de Inversiones (Maestría EAFIT, prof. Juan Carlos Botero, entrega **12 nov 2026**).
El usuario se registra, responde un cuestionario de aversión al riesgo (puntaje 9–27 → perfil → A ∈ {8,6,4,3,1}),
arma **una sola vez** un portafolio escogiendo activos de un catálogo, y la app calcula con Markowitz el portafolio
óptimo de riesgo y el portafolio completo (CAL + `y*`). Se guarda con su encuesta. En cada ingreso se muestra cómo
ha rendido con los datos nuevos y se dan recomendaciones **con reglas fijas (sin IA)**.

Un pipeline diario (GitHub Actions, 22:00 UTC = 5:00 pm Bogotá) trae precios desde Yahoo Finance y los guarda en Supabase.
El Taller 2 (Nelson-Siegel, DV01) es **incremental y posterior**: no lo implementes ahora.

## Documentos (fuente de verdad)
- `docs/00-contexto-y-requisitos.md` — requisitos del taller, trazabilidad y supuestos
- `docs/01-arquitectura.md` — componentes, flujos, seguridad
- `docs/02-modelo-datos.md` — tablas y RLS
- `docs/03-motor-financiero.md` — fórmulas y API del paquete `core`
- `docs/04-pipeline-datos.md` — pipeline y validaciones
- `docs/05-plan-entregables.md` — orden, dependencias, cronograma
- `docs/06-despliegue-y-operacion.md` — local → producción, secretos, runbook
- `docs/entregables/E00…E12` — una especificación por entregable

## Cómo trabajar (flujo por entregable)
1. Usa `/entregable E03` (ver `.claude/commands/entregable.md`) o lee a mano `docs/entregables/E03-*.md`.
2. Verifica que las dependencias del entregable estén commiteadas.
3. Implementa **solo** lo que dice el entregable (sección "Fuera de alcance" es vinculante).
4. Escribe/ejecuta las pruebas indicadas. `pytest` y `ruff check .` deben pasar.
5. Corre la verificación local del entregable y reporta el resultado real.
6. Propón el commit (mensaje convencional sugerido en el entregable). **No hagas push ni commit sin que el usuario lo confirme.**

## Stack
Python 3.11+, numpy, pandas, scipy (SLSQP), scikit-learn (LedoitWolf), plotly, streamlit, supabase-py, yfinance,
pydantic-settings, pytest, ruff. Layout `src/roboadvisor/`.

## Reglas de código
- `core/` es **puro**: sin red, sin Supabase, sin Streamlit, sin `datetime.now()` implícito. Recibe DataFrames/arrays y devuelve dataclasses. Así se prueba offline.
- Acceso a datos solo en `data/` (Supabase, Yahoo). La UI (`app/`) no calcula finanzas: llama a `core/`.
- Parámetros financieros (ventana, w_max, umbrales) viven en `config.py`, nunca "mágicos" en el código.
- Moneda base: **USD**. Sin apalancamiento (`0 ≤ y* ≤ 1`). Solo posiciones largas.
- Textos de UI y docstrings de dominio en español; nombres de código en español o inglés, pero consistentes con los docs.
- Tipado y docstrings cortas con la fórmula cuando aplique.

## Seguridad y datos personales (no negociable)
- Nunca commitear `.env`, claves ni CSV con datos de usuarios. `service_role` solo en el pipeline (secretos de GitHub) y jamás en la app.
- La app usa la clave `anon` + JWT del usuario; la seguridad la dan las políticas RLS de `supabase/migrations/`.
- Guardar solo correo (Supabase Auth), alias, rango de edad y factores de la encuesta. Sin cédula, teléfono ni nombre completo.
- Si cambias el esquema, crea una **nueva migración** (`0002_...sql`); no edites una ya aplicada.

## Comandos
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check .
python -m roboadvisor.pipeline.update_prices --dry-run   # E02
streamlit run app/Inicio.py                               # E07+
```

## Qué NO hacer
- No usar IA/LLM dentro de la app en esta fase (recomendaciones = reglas fijas).
- No implementar Nelson-Siegel/TES (Taller 2) ni datos en tiempo real/websockets.
- No inventar tickers ni duraciones: el catálogo (`supabase/seed/activos.csv`) marca lo que debe verificarse (E02).
- No dar a las recomendaciones tono de asesoría financiera real: llevan siempre el aviso "ejercicio académico".
