# E17 · Sección pública de TES (sin login)

**Depende de:** E14 (o solo su parte de `cliente_mock`), E16, E07 · **Rama:** `e17-pagina-tes` · **Commit:** `feat(app): E17 sección pública de curva TES y señales`
**Cubre:** extra de la app (no lo pide el enunciado). Sirve para la demo y para las capturas del reporte.

## Objetivo
Una página de la misma app, abierta sin iniciar sesión, con la curva cero cupón, la tabla de señales y el DV01 del día. Debe funcionar en producción (Supabase) y en modo mock (`MOCK_DATA=true`).

## Alcance
- Página `app/pages/9_Curva_TES.py` (numeración alta para que quede al final del menú; seguir el patrón de las páginas existentes):
  - **No llama a `requerir_sesion()`** y no lee `st.session_state` del usuario.
  - Usa solo el cliente `anon` (o `cliente_mock`). Lee `tes_informes`, `tes_cotizaciones`, `tes_emisiones`, `curvas_ns`, `tes_senales`. Lecturas con `st.cache_data(ttl=3600)`.
  - Si `Inicio.py` redirige a quien no tiene sesión, verificar que no afecte a esta página. Agregar en `Inicio.py`, sin sesión, un enlace "Curva TES (pública)".
- Contenido:
  1. Encabezado con la fecha del informe y un selector de fechas cargadas (por defecto la última). Aviso si la última tiene más de 5 días hábiles.
  2. Gráfico Plotly: curva spot (plazo en años vs. tasa %), calculada con `core/tes.curva` desde β y τ, y puntos de TIR observada por papel, coloreados por señal.
  3. Métricas: β0, β1, β2, τ, RMSE, número de papeles, conteo de COMPRAR / VENDER / MANTENER.
  4. Tabla: nemotécnico, vencimiento, cupón, precio sucio, precio estimado, TIR observada, TIR teórica, spread (pb), señal, D*, convexidad, DV01 por $1.000 millones (formato `$653.824`).
  5. Expansor "Cómo leer esto": qué es la curva, qué significa el spread y su signo, que el DV01 es por $1.000.000.000 de nominal, y la advertencia de sensibilidad de `07` §5.
  6. Si hay ≥ 5 fechas: evolución de β0 (nivel) y de −β1 (pendiente).
  7. Aviso fijo: "Ejercicio académico. Las señales son salidas de un modelo, no recomendaciones de inversión."
- Lógica de presentación en `app/ui/tes.py` (funciones puras que arman figura y tabla), para poder probarla.

## Fuera de alcance
Botón de descarga de Excel (lo agrega E18 cuando exista el generador), alertas, comentarios.

## Pruebas
1. `streamlit.testing.v1.AppTest` con `MOCK_DATA=true`: la página abre sin sesión, sin excepciones, y muestra 29 filas y la fecha 2026-10-02.
2. Para **cada** otra página de `app/pages/`, AppTest sin sesión → redirige o muestra el login (la protección no se rompió).
3. `app/ui/tes.py`: la tabla formateada tiene las columnas esperadas; el DV01 del TFIT 2058 se muestra como `$653.824`.
4. Revisión estática: `grep -n "cliente_servicio\|service_role" app/` vacío.
5. Integración (Supabase real): con la clave `anon` sin JWT, la página carga datos.

## Verificación local
```bash
MOCK_DATA=true streamlit run app/Inicio.py   # abrir "Curva TES" en ventana privada, sin iniciar sesión
streamlit run app/Inicio.py                  # contra Supabase, con el 2-oct cargado (E14)
```

## Criterios de aceptación
- [ ] Accesible sin login en local y en el despliegue; el resto de páginas sigue protegido.
- [ ] Cifras iguales a las de E16 para el 2-oct.
- [ ] Aviso académico visible; ninguna clave sensible en la app.
