# 02 · Modelo de datos y RLS

Fuente ejecutable: `supabase/migrations/0001_init.sql`. Catálogo inicial: `supabase/seed/activos.csv`.

## Tablas

### Mercado (escribe solo el pipeline con `service_role`; leen los usuarios autenticados)
| Tabla | Clave | Columnas relevantes |
|---|---|---|
| `activos` | `ticker` | `nombre`, `clase`, `region`, `moneda`, `es_renta_fija`, `duration` (obligatoria si es renta fija), `rol` (`invertible`/`benchmark`), `activo`, `notas` |
| `precios` | `(ticker, fecha)` | `close`, `adj_close` (>0), `volumen` |
| `tasa_libre_riesgo` | `fecha` | `tasa_anual` (decimal, p. ej. 0.0425), `fuente` |
| `fundamentales` | `(ticker, fecha)` | `pe`, `pb`, `ev_ebitda`, `div_yield`, `fuente` |
| `pipeline_runs` | `id` | `tipo`, `iniciado_at`, `terminado_at`, `estado`, `filas_precios`, `detalle` (jsonb) |

### Usuario (cada fila pertenece a `auth.users`)
| Tabla | Cardinalidad | Contenido |
|---|---|---|
| `perfiles` | 1 por usuario | `alias`, `edad_rango`, `factores` (jsonb: ocupación, ingresos en rango, dependientes, experiencia…), `consentimiento_at` |
| `encuestas` | 1 por usuario (`unique(user_id)`) | `respuestas` (jsonb `{q1:"a", q2a:"b", …}`), `puntaje` 9–27, `perfil`, `a` ∈ {8,6,4,3,1}, `version_cuestionario` |
| `portafolios` | 1 por usuario (`unique(user_id)`) | `encuesta_id`, `a_usado`, `perfil_usado`, `tickers[]` (3–11), `pesos_riesgo`, `y_star`, `peso_rf`, `pesos_completo`, `metricas`, `parametros` (ventana, rf del T-note a 10 años, w_min, w_max, universo elegido), `fecha_base` |

Los snapshots `a_usado`/`perfil_usado`/`parametros` hacen que el portafolio sea reproducible aunque cambien configuración o catálogo.

## Mapeo del puntaje al perfil
| Puntaje | Perfil | A |
|---|---|---|
| 9–12 | Conservador | 8 |
| 13–16 | Conservador a moderado | 6 |
| 17–20 | Moderado | 4 |
| 21–24 | Moderado a agresivo | 3 |
| 25–27 | Agresivo | 1 |

Cada respuesta vale: a=1, b=2, c=3. Los 9 ítems son: Q1, Q2A, Q2B, Q2C, Q3, Q4, Q5, Q6, Q7.

## Políticas RLS (resumen)
| Tabla | Lectura | Escritura |
|---|---|---|
| `activos`, `precios`, `tasa_libre_riesgo`, `fundamentales`, `pipeline_runs` | `authenticated` | ninguna (solo `service_role`, que ignora RLS) |
| `perfiles` | solo el dueño | el dueño: insert y update |
| `encuestas` | solo el dueño | el dueño: **solo insert** |
| `portafolios` | solo el dueño | el dueño: **solo insert**, y la `encuesta_id` debe ser suya |

`anon` no tiene acceso a ninguna tabla.

## Consultas que usará la app (para dimensionar índices)
- Precios de N tickers desde una fecha: índice `(ticker, fecha)` (PK) y `fecha`.
- Último dato por ticker (para detectar datos viejos): `max(fecha)` por ticker.
- Perfil/encuesta/portafolio por `user_id`: índices por `unique(user_id)`.

## Tamaño estimado
≈25 activos × ~1.300 días hábiles (5 años) ≈ 33.000 filas de precios (<10 MB). Crece unas 25 filas por día hábil. Holgado frente a los 500 MB del plan gratuito.

## Evolución
Cambios de esquema = nueva migración numerada. Para aplicar: SQL Editor de Supabase o `psql "$SUPABASE_DB_URL" -f supabase/migrations/000X_*.sql`.
