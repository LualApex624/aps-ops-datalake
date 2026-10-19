-- sql/roles.sql — rôle en lecture seule pour l'agent (Lot 6)
-- Exécution :
--   set -a; source docker/.env; set +a
--   docker exec -i aps-datalake-db psql -U aps -d datalake -v agent_pwd="$AGENT_DB_PASSWORD" < sql/roles.sql
-- Le mot de passe vient de docker/.env (jamais commité).

-- Création idempotente : ne crée le rôle que s'il n'existe pas
select 'create role agent_ro login'
where not exists (select 1 from pg_roles where rolname = 'agent_ro') \gexec

alter role agent_ro with login password :'agent_pwd';

-- Barrière 1 : les droits (la vraie protection)
grant connect on database datalake to agent_ro;
grant usage   on schema public     to agent_ro;
grant select  on all tables in schema public to agent_ro;
-- Les tables recréées plus tard par Dataiku (propriétaire aps) héritent du droit
alter default privileges for role aps in schema public grant select on tables to agent_ro;

-- Barrière 2 : transactions en lecture seule par défaut (contournable, d'où la barrière 1)
alter role agent_ro set default_transaction_read_only = on;

-- Barrière 3 : pas de requête de plus de 15 s
alter role agent_ro set statement_timeout = '15s';
