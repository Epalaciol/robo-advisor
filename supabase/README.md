# Supabase · un proyecto, tablas separadas por taller

Mismo proyecto y mismas credenciales (`.env`) para ambos talleres. Cada taller tiene sus tablas.

| Migración | Taller | Tablas |
|---|---|---|
| `0001_init.sql` | Taller 1 | `activos`, `precios`, `tasa_libre_riesgo`, `fundamentales`, `pipeline_runs`, `perfiles`, `encuestas`, `portafolios` |
| `0002_rangos_edad.sql`, `0002_rf_tnx_y_tickers_portafolio.sql` | Taller 1 | ajustes |
| `0003_taller2_tes.sql` | **Taller 2** | `t2_informes`, `t2_cotizaciones`, `t2_curvas`, `t2_resultados`, `t2_corridas` (prefijo `t2_`) |

Aplicar en el SQL Editor, en orden, una sola vez cada una. Las tablas `t2_*` son de lectura pública
(la página del Taller 2 no pide login) y solo el `service_role` escribe en ellas.
`seed/activos.csv` es el catálogo del Taller 1.
