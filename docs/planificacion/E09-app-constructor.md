# E09 · App: constructor de portafolio, gráficos y guardado

**Depende de:** E02, E04, E05, E08 · **Rama:** `e09-app-constructor` · **Commit:** `feat(app): E09 constructor de portafolio con frontera, CAL y guardado`

## Objetivo
El usuario escoge de 3 a 11 activos del catálogo; la app calcula y muestra el portafolio óptimo de riesgo y el portafolio completo según su A, y lo guarda **una sola vez** ligado a su encuesta.

## Alcance
- `data/repositorio_mercado.py` (con cliente de usuario): `listar_catalogo()`, `precios(tickers, desde)` → DataFrame fecha × ticker, `rf_ultima()`, `fundamentales_ultimos(tickers)`, `ultima_fecha_precios()`.
- `pages/2_Constructor.py`
  1. Requiere sesión y encuesta; si ya hay portafolio, redirige a Mi portafolio.
  2. **Selector de activos** agrupado por clase (multiselect con búsqueda; botones de "ejemplo diversificado" opcional). Validar 3–11, mostrar el contador y bloquear al pasar de 11. Mostrar por activo: clase, moneda y, si aplica, duration. Excluir `activo=false` y el benchmark.
  3. Botón "Calcular": carga precios, `estimar` → `tangente` → `frontera` → `cal` → `y_star`/`componer` (con el A guardado, no editable). Cachear con `st.cache_data` (clave: tickers + `ultima_fecha_precios`).
  4. **Resultados** (pestañas):
     - *Resumen:* perfil y A; `y*` (% en riesgo / % libre de riesgo); retorno esperado, σ y Sharpe del portafolio de riesgo y del completo; utilidad. Si hubo recorte a 100 % (`apalancamiento_requerido`) o `advertencia`, mostrarlo en lenguaje claro.
     - *Composición:* tabla y gráfico (barras o dona) de pesos del portafolio de riesgo y del completo (incluye "Libre de riesgo").
     - *Frontera y CAL:* gráfico Plotly con frontera eficiente, activos individuales, portafolio de mínima varianza, tangente, la CAL, y el punto del portafolio completo del usuario.
     - *Betas y duration:* tabla de betas (renta variable vs ACWI) y duration de la renta fija, más beta y duration del portafolio.
     - *Supuestos:* ventana, nº de meses, rf usada, shrinkage, `w_max`, fecha de datos.
  5. **Confirmar y guardar:** checkbox "entiendo que el portafolio se guarda una sola vez" + botón. Inserta en `portafolios` con snapshots (`a_usado`, `perfil_usado`, `parametros`, `metricas`, `fecha_base` = último día con precios) y redirige a Mi portafolio.
- `data/repositorio_usuario.py`: `guardar_portafolio(...)`.
- `ui/graficos.py`: funciones Plotly reutilizables (frontera, barras de pesos, utilidad); aspecto coherente y legible en modo claro/oscuro; ejes en %.

## Fuera de alcance
Editar o recalcular un portafolio ya guardado, múltiples portafolios, pesos manuales.

## Pruebas
- Pytest: función `armar_registro_portafolio(...)` (pura) produce el dict a insertar con tipos correctos, tickers ordenados, pesos que suman 1 y `y_star ∈ [0,1]`.
- Integración opcional: insertar con usuario de prueba y verificar RLS (ya cubierto en E01).
- Manual: checklist.

## Verificación local (manual)
- [ ] Con 6 activos variados (p. ej. SPY, EFA, EMB, LQD, VNQ, GLD) y perfil Moderado: pesos suman 100 %, `y*` ∈ [0,1], frontera y CAL visibles, tangente sobre/cerca de la frontera.
- [ ] Cambiar de usuario Conservador (A=8) a Agresivo (A=1) con los mismos activos: el agresivo tiene mayor `y*`.
- [ ] Con 2 activos no deja calcular; con 12 no deja seleccionar el 12.
- [ ] Un activo con historia corta muestra mensaje claro en vez de trazas.
- [ ] Al guardar queda una fila en `portafolios` ligada a su `encuesta_id`; no se puede guardar otro.
- [ ] Las cifras mostradas coinciden con una corrida de `scripts/demo_motor.py` para los mismos datos.

## Criterios de aceptación
- [ ] Checklist completo. **Parcial**: verificado con el panel sintético de E04 (`armar_registro_portafolio` probado con pytest; `figura_frontera`/`figura_pesos` probadas end-to-end con el motor real; las cifras coinciden exactamente con `scripts/demo_motor.py`). El checklist contra datos y Supabase reales está **pendiente** (requiere E01/E02 conectados).
- [x] Todos los números vienen de `core/`; la página solo llama a `estimar/min_varianza/tangente/frontera/cal/componer/betas/duration_portafolio` y grafica — no implementa fórmulas.
- [ ] Tiempo de cálculo razonable (< 5 s con 11 activos y datos en caché). **Pendiente**: no medible sin datos reales; el cálculo con el panel sintético de 5 activos es instantáneo.
