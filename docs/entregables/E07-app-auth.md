# E07 · App: esqueleto, autenticación, consentimiento y estado de datos

**Depende de:** E01, E02 · **Rama:** `e07-app-auth` · **Commit:** `feat(app): E07 esqueleto Streamlit, registro y login`

## Objetivo
Una app Streamlit multipágina que permite registrarse, iniciar sesión, cerrar sesión y que enruta al usuario según su avance (sin encuesta → Encuesta; con encuesta sin portafolio → Constructor; con ambos → Mi portafolio).

## Alcance
- Estructura:
  ```
  app/
    Inicio.py                 # login/registro + enrutamiento por estado
    pages/1_Encuesta.py       # placeholder "próximamente" (E08)
    pages/2_Constructor.py    # placeholder (E09)
    pages/3_Mi_portafolio.py  # placeholder (E10)
    ui/auth.py, ui/estado.py, ui/estilos.py
  ```
- `ui/auth.py`:
  - Registro: correo, contraseña (≥ 8), **alias**, **rango de edad** (25-34 … 65-74, "otro"), **checkbox de consentimiento** (texto breve de tratamiento de datos para fines académicos, habeas data) → `supabase.auth.sign_up` + insert en `perfiles` con `consentimiento_at = now()`.
  - Login/logout con `sign_in_with_password`; guardar `access_token`/`refresh_token` y `user` en `st.session_state`.
  - `requerir_sesion()` para usar al inicio de cada página: si no hay sesión, redirige a Inicio. Refrescar token si expiró; si falla, cerrar sesión con mensaje.
  - Los clientes de datos se construyen **con el JWT del usuario** (`cliente_usuario`) para que RLS aplique.
- `data/repositorio_usuario.py`: `obtener_perfil()`, `obtener_encuesta()`, `obtener_portafolio()` (cada uno devuelve `None` si no existe) usando el cliente del usuario.
- `ui/estado.py`: función `estado_usuario() -> 'sin_encuesta' | 'sin_portafolio' | 'completo'` y barra lateral con alias, estado y **Estado de datos** (última corrida de `pipeline_runs`, fecha del último precio).
- Aviso permanente en el pie: "Ejercicio académico; no constituye asesoría financiera."
- Mensajes de error amigables (no mostrar trazas ni claves).
- Si falta `.env`/secretos, la app muestra instrucciones de configuración en vez de fallar.

## Fuera de alcance
Contenido de las páginas 1–3 (solo placeholders), gráficos, motor.

## Pruebas
- Unitarias de lo no visual: `estado_usuario` con repositorios falsos; validación de formulario de registro (correo, contraseña corta, alias vacío, sin consentimiento).
- Manual (checklist abajo).

## Verificación local (checklist manual)
```bash
streamlit run app/Inicio.py
```
- [ ] Registro con consentimiento crea `auth.users` y fila en `perfiles` (verificar en Supabase).
- [ ] Registro sin consentimiento se bloquea.
- [ ] Login/logout funcionan; recargar la página pide login de nuevo (aceptable).
- [ ] Usuario nuevo es enviado a Encuesta; las páginas protegidas no abren sin sesión.
- [ ] Sidebar muestra el estado de datos (última corrida del pipeline).
- [ ] Revisar en el navegador/red que no viaja `service_role`.

## Criterios de aceptación
- [ ] Todo lo anterior marcado.
- [ ] `grep -ri service_role app/ src/roboadvisor/data/repositorio_usuario.py` vacío.
- [ ] `pytest` y `ruff` verdes.
