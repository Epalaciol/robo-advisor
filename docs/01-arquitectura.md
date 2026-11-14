# 01 · Arquitectura

## 1. Vista general

```
                 Yahoo Finance (yfinance)        ^TNX (T-note 10 años, rf) 
                          │                               │
                          ▼                               ▼
        ┌──────────────────────────────────────────────────────────┐
        │ GitHub Actions  pipeline.yml  (cron 0 22 * * 1-5 UTC)     │
        │ roboadvisor.pipeline.update_prices / update_fundamentals  │
        │ usa SUPABASE_SERVICE_ROLE_KEY (secreto de GitHub)         │
        └──────────────────────────┬───────────────────────────────┘
                                   │ upsert
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │ Supabase                                                  │
        │  Auth (email+password)                                    │
        │  Postgres + RLS                                           │
        │   catálogo/mercado: activos, precios, tasa_libre_riesgo,  │
        │                     fundamentales, pipeline_runs          │
        │   usuario:          perfiles, encuestas, portafolios      │
        └──────────────────────────┬───────────────────────────────┘
                                   │ clave anon + JWT del usuario
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │ Streamlit  (local → Streamlit Community Cloud)            │
        │  app/ (UI) ──► data/ (repositorio) ──► core/ (motor puro) │
        └──────────────────────────────────────────────────────────┘
```

## 2. Capas del código (`src/roboadvisor/`)

| Capa | Responsabilidad | Reglas |
|---|---|---|
| `core/` | Toda la matemática financiera y las reglas de recomendación | Puro: sin red, sin DB, sin UI. Entra DataFrame, sale dataclass |
| `data/` | Acceso a Supabase y Yahoo; mapeo filas ↔ dataclasses | Único lugar con I/O |
| `pipeline/` | Ingesta diaria: descarga, valida, upsert, registra corrida | Corre con `service_role`; idempotente |
| `app/` | Páginas Streamlit, autenticación, estado de sesión, gráficos | No calcula finanzas; llama a `core/` |
| `config.py` | Variables de entorno y parámetros financieros | Parámetros versionados en código |

## 3. Flujos

**Primer ingreso**
1. Registro (correo, contraseña, alias, rango de edad, consentimiento) → `perfiles`.
2. Encuesta (9 preguntas + factores personales opcionales) → `core.cuestionario.puntuar` → `encuestas` (inmutable).
3. Constructor: elige 3–11 activos → app lee `precios` → `core` calcula μ, Σ, portafolio de riesgo óptimo, frontera, CAL, `y*` → vista previa → confirmar → `portafolios` (una vez).

**Ingresos posteriores**
1. Login → si no hay encuesta, va a Encuesta; si hay encuesta pero no portafolio, va a Constructor; si hay ambos, va a **Mi portafolio**.
2. Mi portafolio: lee `portafolios` + `precios` posteriores a `fecha_base` → `core.seguimiento` (valor, retorno, vol, drawdown, contribución) → `core.recomendaciones` (reglas) → UI.

**Cada día hábil 5 pm Bogotá:** pipeline trae los días faltantes por activo, valida, hace upsert y registra la corrida (`pipeline_runs`). Funciona también como *keep-alive* del proyecto gratuito de Supabase.

## 4. Seguridad
- La app usa solo `SUPABASE_ANON_KEY` y el JWT del usuario; **RLS** restringe cada usuario a sus filas. El catálogo/mercado es de solo lectura para usuarios autenticados.
- `service_role` únicamente en GitHub Actions (y en scripts locales de administración). Nunca en Streamlit Cloud.
- `encuestas` y `portafolios` son **append-only** para el usuario (sin update/delete): garantiza que el portafolio quede ligado a la aversión con la que se construyó.
- Datos personales mínimos; consentimiento (habeas data) con fecha; alias en vez de nombre.
- El repo no contiene datos de usuarios ni claves; `.env` y `secrets.toml` están en `.gitignore`.

## 5. Entornos
| Entorno | App | Supabase | Pipeline |
|---|---|---|---|
| Local (primero) | `streamlit run app/Inicio.py` | Proyecto Supabase real (gratuito) con `.env` | Se ejecuta a mano: `python -m roboadvisor.pipeline.update_prices` |
| Producción (después) | Streamlit Community Cloud desde GitHub | **El mismo proyecto** (suficiente para un taller) | GitHub Actions programado |

Promover a producción solo cuando E00–E10 estén estables y probados con los 5 voluntarios (ver `06-despliegue-y-operacion.md`).

## 6. Costo
Streamlit Community Cloud $0 · Supabase Free $0 (500 MB; el universo de precios ocupa unos pocos MB) · GitHub Actions/repo $0 · Yahoo/FRED $0.
Riesgos del plan gratuito: pausa por 7 días sin actividad (mitigado por el cron), sin backups automáticos (exportar antes de sustentar), GitHub desactiva crons de repos sin actividad tras 60 días (hacer un commit antes si pasa tiempo).

## 7. Decisiones de diseño y alternativas descartadas
- **Pipeline en vez de Yahoo directo desde la app:** Yahoo bloquea o limita servidores compartidos; la base propia hace la app rápida y reproducible. (Si alguien insiste, `data/yahoo.py` es reutilizable, pero no se usa desde `app/`.)
- **Streamlit y no FastAPI+React:** una sola persona/lenguaje, despliegue gratuito inmediato; la lógica ya está aislada en `core/` y se podría exponer luego.
- **Optimización propia con SciPy y no PyPortfolioOpt:** el PDF debe explicar cada paso; el código propio es corto y auditable.
- **Un portafolio por usuario (`unique(user_id)`):** refleja "se hace una vez". Para permitir varios más adelante, bastaría una migración que quite la restricción.
