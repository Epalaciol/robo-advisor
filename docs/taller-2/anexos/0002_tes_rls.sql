-- Prueba de RLS de 0002 (Postgres local con stub de auth). Esperado: lecturas anon/authenticated de tes_* OK; todo lo demás "permission denied".
\set ON_ERROR_STOP 0
insert into tes_emisiones values ('TCO364201026','TCO','2026-10-20',0);
insert into tes_informes values ('2026-10-02',562515499,'csv',true,'x');
insert into tes_cotizaciones(fecha,nemotecnico,valor_nominal_mm,precio_limpio,precio_sucio) values ('2026-10-02','TCO364201026',5351599,99.43,99.43);
insert into curvas_ns values ('2026-10-02',0.135,-0.012,0.0078,3.7,1,0.49,29,'todos','ok');
insert into pipeline_runs(tipo,estado) values ('tes','ok');
select 'service: pipeline tes ok';
set role anon;
select 'anon lee tes_cotizaciones:', count(*) from tes_cotizaciones;
select 'anon lee curvas_ns:', count(*) from curvas_ns;
select count(*) from perfiles;
select count(*) from encuestas;
select count(*) from portafolios;
select count(*) from precios;
select count(*) from activos;
select count(*) from pipeline_runs;
insert into tes_informes values ('2026-10-03',1,'csv',true,'x');
delete from tes_informes;
reset role; set role authenticated;
select 'auth lee tes_senales:', count(*) from tes_senales;
insert into tes_informes values ('2026-10-03',1,'csv',true,'x');
update curvas_ns set beta0=0;
delete from tes_cotizaciones;
reset role;
select 'sin cambios:', count(*) from tes_informes;
