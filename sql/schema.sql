-- sql/schema.sql — objets gérés en SQL, hors du Flow Dataiku
-- Exécution : docker exec -i aps-datalake-db psql -U aps -d datalake < sql/schema.sql

drop table if exists dim_date cascade;

create table dim_date as
select
    d::date                         as date_key,
    extract(year    from d)::int    as year,
    extract(quarter from d)::int    as quarter,
    extract(month   from d)::int    as month,
    to_char(d, 'FMMonth')           as month_name,
    extract(week    from d)::int    as iso_week,
    extract(isodow  from d)::int    as day_of_week,   -- 1 = lundi … 7 = dimanche
    to_char(d, 'FMDay')             as day_name,
    extract(isodow  from d) >= 6    as is_weekend
from generate_series('2026-01-01'::date, '2026-12-31'::date, interval '1 day') as d;

alter table dim_date add primary key (date_key);
