# 04 · Pipeline de datos

## Objetivo
Mantener `precios`, `tasa_libre_riesgo` y `fundamentales` al día sin tiempo real: una corrida diaria tras el cierre. La app solo lee la base.

## Programación
`.github/workflows/pipeline.yml`
- `cron: "0 22 * * 1-5"` → 22:00 UTC = **5:00 pm Bogotá** (UTC−5, sin horario de verano), lunes a viernes. Cae después del cierre de EE.UU. en cualquier época del año.
- `workflow_dispatch` para correrlo a mano.
- Fundamentales: workflow separado `pipeline-fundamentales.yml` con `cron: "30 22 * * 5"` (viernes 5:30 pm Bogotá).
- Secretos del repo: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- Nota: GitHub pausa los workflows programados de un repo sin actividad por 60 días; hacer un commit o reactivarlo.

## Módulos
```
pipeline/
  update_prices.py        CLI: --dry-run, --desde YYYY-MM-DD, --tickers A,B
  update_fundamentals.py  CLI idéntica
  validators.py           reglas de calidad
data/
  yahoo.py                descargar_precios(tickers, desde), descargar_rf(), descargar_fundamentales(ticker)
  repositorio.py          upsert_precios, ultima_fecha_por_ticker, registrar_corrida, ...
```

## Algoritmo `update_prices`
1. Leer del catálogo los tickers `activo = true` (invertibles + benchmark).
2. Para cada ticker, `ultima_fecha` en `precios`; pedir a Yahoo desde `ultima_fecha − 5 días` (solapamiento para corregir ajustes) o, si no hay datos, `historico_anios` (6) atrás.
3. Validar (abajo). Los tickers inválidos **no** se cargan y quedan en el reporte; los demás sí (estado `parcial`).
4. `upsert` por lotes (p. ej. 500 filas) con `on_conflict=(ticker,fecha)`.
5. Descargar `^IRX` → `tasa_libre_riesgo` (`tasa_anual = cierre/100`).
6. Insertar fila en `pipeline_runs` con estado, conteos y detalle por ticker.
7. Código de salida ≠ 0 si el estado es `error` (que el workflow falle y avise por correo de GitHub). `parcial` sale 0 pero deja el detalle visible.

**Idempotente:** correrlo dos veces el mismo día no duplica ni cambia resultados.

## Validaciones (`validators.py`)
- Sin `adj_close` ≤ 0 ni nulos.
- Sin fechas futuras ni duplicadas.
- Salto diario |retorno| > 40 % en renta fija o > 60 % en renta variable/cripto → advertencia (se carga pero se reporta) salvo splits conocidos.
- Frescura: el último dato por ticker no debe tener más de `dias_stale` días hábiles de atraso respecto a la fecha de la corrida; si no, advertencia.
- Cripto: se descarta cualquier fecha sin ruedas de acciones al construir retornos (el motor alinea por cierre de mes; el pipeline guarda todo).

## Fundamentales
`yfinance.Ticker(t).info` → `trailingPE`, `priceToBook`, `enterpriseToEbitda`, `dividendYield`. Muchos ETF no traen P/E: guardar `NULL`, no ceros. Registrar `fuente = "yahoo"`. Es información informativa, no se usa para optimizar.

## Verificación inicial del catálogo (E02)
Antes de cargar historia, un script `verificar_catalogo` descarga 1 mes de cada ticker y reporta cuáles fallan, cuáles tienen historia < 60 meses y cuáles no traen precio. Esos se marcan `activo = false` en el seed hasta resolverlos. **No se asume que todos los tickers del seed son válidos.**

## Monitoreo
- Página/Sección "Estado de datos" en la app (sidebar): última corrida, estado, fecha del último precio. Alimenta la regla R5.
- El workflow fallido manda correo al dueño del repo (configuración por defecto de GitHub).

## Alternativa descartada
Consultar Yahoo directo desde la app (sin base): más simple en el papel, pero frágil (límites de Yahoo en servidores compartidos), lento en cada ingreso y no reproducible. Si se quisiera "casi tiempo real", se podría llamar `yahoo.py` desde un botón de refresco **con caché** y manejo de errores, sin websockets.
