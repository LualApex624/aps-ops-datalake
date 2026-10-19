-- sql/views.sql — couche de restitution (lue par Superset et l'agent)
-- Exécution : docker exec -i aps-datalake-db psql -U aps -d datalake < sql/views.sql

-- SRE-1 · Un change par ligne : a-t-il été suivi d'un incident sur le même CI sous 48 h ?
create or replace view v_change_risk as
select
    c.change_id,
    c.planned_start,
    c.planned_start::date                      as change_date,
    c.ci_id,
    c.app_id,
    a.app_name,
    a.business_criticality,
    c.type                                     as change_type,
    c.result,
    c.is_failed,
    count(i.incident_id)                       as n_incidents_48h,
    (count(i.incident_id) > 0)::int            as has_incident_48h,
    min(i.opened_at) - c.planned_start         as time_to_first_incident
from fact_change c
left join fact_incident i
       on i.ci_id = c.ci_id
      and i.opened_at >  c.planned_start
      and i.opened_at <= c.planned_start + interval '48 hours'
left join dim_application a
       on a.app_id = c.app_id
group by c.change_id, c.planned_start, c.ci_id, c.app_id, a.app_name,
         a.business_criticality, c.type, c.result, c.is_failed;

-- SRE-1 · Taux par application (brique 0/1 agrégée, jamais un ratio stocké)
create or replace view v_change_risk_by_app as
select
    app_id,
    app_name,
    business_criticality,
    count(*)                                   as n_changes,
    sum(has_incident_48h)                      as n_changes_with_incident,
    round(avg(has_incident_48h)::numeric, 3)   as change_incident_rate,
    round(avg(is_failed)::numeric, 3)          as change_failure_rate
from v_change_risk
group by app_id, app_name, business_criticality;

-- OPS-2 · Incidents récurrents : même CI + même message normalisé, avec mesure de régularité
create or replace view v_recurring_incidents as
with base as (
    select ci_id,
           app_id_clean                          as app_id,
           description_norm,
           opened_at,
           extract(isodow from opened_at)::int   as dow,
           extract(hour   from opened_at)::int   as hour_of_day,
           resolution_minutes
    from fact_incident
    where description_norm is not null
),
agg as (
    select ci_id, app_id, description_norm,
           count(*)                                            as n_occurrences,
           count(distinct date_trunc('week', opened_at))       as n_weeks,
           min(opened_at)                                      as first_seen,
           max(opened_at)                                      as last_seen,
           mode() within group (order by hour_of_day)          as modal_hour,
           percentile_cont(0.5) within group (order by resolution_minutes)
               filter (where resolution_minutes >= 0)          as median_resolution_minutes
    from base
    group by ci_id, app_id, description_norm
    having count(*) >= 5
),
by_dow as (
    select ci_id, app_id, description_norm, dow, count(*) as n
    from base
    group by ci_id, app_id, description_norm, dow
),
top_dow as (
    select distinct on (ci_id, app_id, description_norm)
           ci_id, app_id, description_norm, dow as modal_dow, n as n_modal
    from by_dow
    order by ci_id, app_id, description_norm, n desc, dow
)
select a.ci_id,
       a.app_id,
       ap.app_name,
       a.description_norm,
       a.n_occurrences,
       a.n_weeks,
       a.first_seen,
       a.last_seen,
       t.modal_dow,
       (array['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[t.modal_dow] as modal_day_name,
       round(t.n_modal::numeric / a.n_occurrences, 3)            as modal_dow_share,
       a.modal_hour,
       round(a.median_resolution_minutes::numeric, 0)            as median_resolution_minutes,
       (a.n_weeks >= 8 and t.n_modal::numeric / a.n_occurrences >= 0.8) as is_weekly_pattern
from agg a
join top_dow t
  on t.ci_id = a.ci_id and t.app_id = a.app_id and t.description_norm = a.description_norm
left join dim_application ap
  on ap.app_id = a.app_id;

-- SRE-2 · Profil de criticité par application (médianes calculées au bon grain)
create or replace view v_app_criticality as
with inc as (
    select app_id_clean                                                as app_id,
           count(*) filter (where priority in ('P1','P2'))             as n_p1_p2,
           count(*) filter (where priority in ('P1','P2')
                              and resolution_minutes >= 0)             as n_p1_p2_resolved,
           percentile_cont(0.5) within group (order by resolution_minutes)
               filter (where priority in ('P1','P2')
                         and resolution_minutes >= 0)                  as mttr_median_p1_p2,
           percentile_cont(0.5) within group (order by resolution_minutes / sla_target_minutes)
               filter (where priority in ('P1','P2')
                         and resolution_minutes >= 0)                  as sla_ratio_median_p1_p2,
           avg(is_breach_sla) filter (where priority is not null
                                        and resolution_minutes >= 0)   as breach_rate
    from fact_incident
    group by app_id_clean
),
chg as (
    select app_id,
           count(*)       as n_changes,
           avg(is_failed) as change_failure_rate
    from fact_change
    group by app_id
)
select a.app_id,
       a.app_name,
       a.business_criticality,
       coalesce(i.n_p1_p2, 0)                                  as n_p1_p2,
       coalesce(i.n_p1_p2_resolved, 0)                         as n_p1_p2_resolved,
       round(i.mttr_median_p1_p2::numeric, 0)                  as mttr_median_p1_p2_min,
       round(i.sla_ratio_median_p1_p2::numeric, 2)             as sla_ratio_median_p1_p2,
       round(i.breach_rate::numeric, 3)                        as breach_rate,
       coalesce(c.n_changes, 0)                                as n_changes,
       round(c.change_failure_rate::numeric, 3)                as change_failure_rate,
       coalesce(i.n_p1_p2_resolved, 0) >= 10                   as is_reliable,
       coalesce(i.n_p1_p2_resolved, 0) >= 10
           and i.sla_ratio_median_p1_p2 > 1                    as is_sla_at_risk
from dim_application a
left join inc i on i.app_id = a.app_id
left join chg c on c.app_id = a.app_id;
