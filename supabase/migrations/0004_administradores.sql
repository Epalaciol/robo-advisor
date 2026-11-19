-- 0004: cuentas de administrador (solo lectura de todos los usuarios).
-- Aplicar una vez en el SQL Editor de Supabase. La app sigue usando la clave anon + JWT:
-- un administrador puede LEER perfiles, encuestas y portafolios de cualquier usuario, pero no
-- modificarlos (no se crean políticas de insert/update/delete para administradores).
-- Las cuentas se marcan con service_role desde la máquina del administrador
-- (scripts/taller1/crear_admin.py); la app no puede insertar en esta tabla.

create table if not exists public.administradores (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.administradores enable row level security;
revoke all on public.administradores from anon;
grant select on public.administradores to authenticated;

-- Cada usuario solo puede ver si él mismo es administrador
create policy administradores_select_propio on public.administradores for select to authenticated
  using (user_id = (select auth.uid()));

-- security definer: consulta la tabla sin depender de su propia RLS (evita recursión)
create or replace function public.es_admin() returns boolean
  language sql stable security definer set search_path = public
as $$
  select exists (select 1 from public.administradores where user_id = auth.uid());
$$;
revoke all on function public.es_admin() from public, anon;
grant execute on function public.es_admin() to authenticated;

-- Lectura adicional para administradores (las políticas de select se combinan con OR)
create policy perfiles_select_admin on public.perfiles for select to authenticated
  using ((select public.es_admin()));
create policy encuestas_select_admin on public.encuestas for select to authenticated
  using ((select public.es_admin()));
create policy portafolios_select_admin on public.portafolios for select to authenticated
  using ((select public.es_admin()));
