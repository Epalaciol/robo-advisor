-- 0001_init.sql — Esquema inicial del robo-advisor (Taller 1)
-- Ejecutar en el SQL Editor de Supabase o con psql. Ver docs/02-modelo-datos.md

-- =========================================================
-- 1. Mercado (lo escribe el pipeline con service_role)
-- =========================================================

create table public.activos (
  ticker          text primary key,
  nombre          text not null,
  clase           text not null check (clase in (
                    'acciones_colombia_latam', 'acciones_eeuu', 'acciones_eafe',
                    'acciones_emergentes', 'renta_fija_colombia', 'renta_fija_ig',
                    'renta_fija_hy', 'renta_fija_global', 'renta_fija_emergente',
                    'reit', 'cripto', 'materias_primas', 'benchmark')),
  region          text,
  moneda          text not null default 'USD',
  es_renta_fija   boolean not null default false,
  duration        numeric(5,2),
  rol             text not null default 'invertible' check (rol in ('invertible', 'benchmark')),
  activo          boolean not null default true,
  notas           text,
  created_at      timestamptz not null default now(),
  constraint duration_si_renta_fija check (not es_renta_fija or duration is not null)
);

create table public.precios (
  ticker      text not null references public.activos (ticker) on delete cascade,
  fecha       date not null,
  close       numeric(18,6),
  adj_close   numeric(18,6) not null check (adj_close > 0),
  volumen     bigint,
  primary key (ticker, fecha)
);
create index precios_fecha_idx on public.precios (fecha);

create table public.tasa_libre_riesgo (
  fecha        date primary key,
  tasa_anual   numeric(8,6) not null check (tasa_anual >= 0 and tasa_anual < 1),
  fuente       text not null default 'yahoo:^IRX'
);

create table public.fundamentales (
  ticker      text not null references public.activos (ticker) on delete cascade,
  fecha       date not null,
  pe          numeric(12,4),
  pb          numeric(12,4),
  ev_ebitda   numeric(12,4),
  div_yield   numeric(8,6),
  fuente      text not null default 'yahoo',
  primary key (ticker, fecha)
);

create table public.pipeline_runs (
  id              bigint generated always as identity primary key,
  tipo            text not null check (tipo in ('precios', 'fundamentales')),
  iniciado_at     timestamptz not null default now(),
  terminado_at    timestamptz,
  estado          text not null check (estado in ('ok', 'parcial', 'error')),
  filas_precios   integer not null default 0,
  detalle         jsonb not null default '{}'::jsonb
);

-- =========================================================
-- 2. Usuario (cada fila pertenece a auth.users)
-- =========================================================

create table public.perfiles (
  user_id           uuid primary key references auth.users (id) on delete cascade,
  alias             text not null check (char_length(alias) between 2 and 40),
  edad_rango        text not null check (edad_rango in ('25-34', '35-44', '45-54', '55-64', '65-74', 'otro')),
  factores          jsonb not null default '{}'::jsonb,
  consentimiento_at timestamptz not null,
  created_at        timestamptz not null default now()
);

create table public.encuestas (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null unique references auth.users (id) on delete cascade,
  respuestas            jsonb not null,
  puntaje               smallint not null check (puntaje between 9 and 27),
  perfil                text not null check (perfil in (
                          'conservador', 'conservador_moderado', 'moderado',
                          'moderado_agresivo', 'agresivo')),
  a                     numeric(3,1) not null check (a in (8, 6, 4, 3, 1)),
  version_cuestionario  text not null default 'v1',
  created_at            timestamptz not null default now()
);

create table public.portafolios (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null unique references auth.users (id) on delete cascade,
  encuesta_id     uuid not null references public.encuestas (id),
  a_usado         numeric(3,1) not null check (a_usado in (8, 6, 4, 3, 1)),
  perfil_usado    text not null,
  tickers         text[] not null check (cardinality(tickers) between 3 and 11),
  pesos_riesgo    jsonb not null,
  y_star          numeric(7,6) not null check (y_star between 0 and 1),
  peso_rf         numeric(7,6) not null check (peso_rf between 0 and 1),
  pesos_completo  jsonb not null,
  metricas        jsonb not null default '{}'::jsonb,
  parametros      jsonb not null default '{}'::jsonb,
  fecha_base      date not null,
  created_at      timestamptz not null default now()
);

-- =========================================================
-- 3. Row Level Security
-- =========================================================

alter table public.activos            enable row level security;
alter table public.precios            enable row level security;
alter table public.tasa_libre_riesgo  enable row level security;
alter table public.fundamentales      enable row level security;
alter table public.pipeline_runs      enable row level security;
alter table public.perfiles           enable row level security;
alter table public.encuestas          enable row level security;
alter table public.portafolios        enable row level security;

-- anon no accede a nada
revoke all on all tables in schema public from anon;

-- Mercado: lectura para usuarios autenticados; escritura solo service_role (que ignora RLS)
create policy activos_lectura           on public.activos           for select to authenticated using (true);
create policy precios_lectura           on public.precios           for select to authenticated using (true);
create policy tasa_lectura              on public.tasa_libre_riesgo for select to authenticated using (true);
create policy fundamentales_lectura     on public.fundamentales     for select to authenticated using (true);
create policy pipeline_runs_lectura     on public.pipeline_runs     for select to authenticated using (true);

-- Perfiles: el dueño lee, inserta y actualiza
create policy perfiles_select on public.perfiles for select to authenticated
  using (user_id = (select auth.uid()));
create policy perfiles_insert on public.perfiles for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy perfiles_update on public.perfiles for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Encuestas: el dueño lee e inserta (inmutable)
create policy encuestas_select on public.encuestas for select to authenticated
  using (user_id = (select auth.uid()));
create policy encuestas_insert on public.encuestas for insert to authenticated
  with check (user_id = (select auth.uid()));

-- Portafolios: el dueño lee e inserta (inmutable); la encuesta debe ser suya
create policy portafolios_select on public.portafolios for select to authenticated
  using (user_id = (select auth.uid()));
create policy portafolios_insert on public.portafolios for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.encuestas e
      where e.id = encuesta_id and e.user_id = (select auth.uid())
    )
  );
