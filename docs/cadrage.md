## Persona : SRE
- Qui : ingénieur fiabilité dans l’équipe production. Il rend compte au responsable de la production IT.
- Quand il ouvre l'outil : chaque semaine en revue de fiabilité, et après tout incident majeur (P1).
- Sa question n°1 : Quelles applications ou quels CI concentrent les incidents récurrents ou post-change, et lesquels sont critiques pour le métier ?
- Ce qu'il décide ensuite : automatiser la correction d’un incident récurrent, ouvrir une analyse de cause racine, renforcer la validation des changes d’une application.
- Utilité de l'outil : Eviter de croiser à la main des exports ITSM et CMDB dans Excel, donc l’analyse n’est jamais faite.
- Où il regarde : les dashboards en priorité, et l’agent pour les questions ad hoc en SQL.

## Persona : OPs
- Qui : opérateur run ou d’astreinte. Il rend compte au team lead du run.
- Quand il ouvre l'outil : à l’arrivée d’un ticket, plusieurs fois par jour.
- Sa question n°1 : Cet incident est-il déjà arrivé sur ce CI ? Comment a-t-il été résolu, et quel runbook s’applique ?
- Ce qu'il décide ensuite : appliquer le runbook, ou escalader vers l’équipe propriétaire du CI.
- Utilité de l'outil : Eviter de , chercher dans le wiki, ne pas savoir qui possède le CI, escalader des incidents déjà connus.
- Où il regarde : l’agent en priorité, qui interroge l’historique et les runbooks.


## Use cases

### SRE-1 : Quelles applications critiques ont le plus fort taux de changes suivis d'un incident dans les 48 h, sur les 90 derniers jours ?
- Définition : taux = nb de changes suivis d'≥ 1 incident sous 48 h sur le même app_id ÷ nb total de changes de l'app
- Décision : passer ces applications en revue de change renforcée et imposer des tests de non-régression
- Données : changes, incidents, cmdb
- Où : dashboard « Change risk »
- Pattern couvert : 1

### SRE-2 : Quelles applications de criticité 1 ont un MTTR médian des incidents P1/P2 supérieur à la cible SLA, sur le dernier trimestre ?
- Définition : MTTR médian = médiane de (resolved_at − opened_at) ; cible SLA lue dans la table priority (hypothèse documentée) ; n affiché
- Décision : financer un chantier de fiabilisation ou revoir le processus d'escalade de ces applications
- Données : incidents, cmdb, priority
- Où : dashboard « Incident analytics »
- Pattern couvert : 4

### SRE-3 : Parmi les 10 catégories d'incidents les plus fréquentes ce trimestre, lesquelles n'ont aucun runbook ?
- Définition : jointure incidents.category ↔ catégorie déclarée dans l'en-tête des runbooks
- Décision : créer des tickets de rédaction de runbook, puis d'automatisation, pour réduire le toil
- Données : incidents, runbooks
- Où : dashboard « Incident analytics »

### OPS-1 : Au dernier relevé, quels serveurs de base de données dépassent 85 % de disque, et à quelle date atteindront-ils 90 % au rythme actuel ?
- Définition : projection linéaire sur les 14 derniers jours (pas un modèle prédictif)
- Décision : purger les logs ou demander une extension de stockage avant le seuil
- Données : capacity, cmdb
- Où : agent (+ panneau capacité en bonus)
- Pattern couvert : 3

### OPS-2 : L'incident que je viens de recevoir sur le CI X s'est-il déjà produit ? À quelle fréquence, et quel runbook appliquer ?
- Décision : appliquer le runbook ; si récurrent, signaler au SRE pour automatisation
- Données : incidents, runbooks
- Où : agent
- Pattern couvert : 2

### OPS-3 : Quelles applications sont hébergées sur ce CI, quelle est leur criticité et quelle équipe prévenir ?
- Décision : notifier les équipes propriétaires ; escalader en P1 si une application de criticité 1 est touchée
- Données : incidents, cmdb
- Où : agent
- Limite : pas de graphe de dépendances entre CI → impact « en aval » non couvertincidents, cmdb, runbooks
- Où : agent


## Modèle de données

### fact_incident
- Grain : 1 ligne = 1 incident unique (après dédoublonnage en silver)
- Clés étrangères : date_opened_key → dim_date, ci_id → dim_ci, app_id → dim_application,
  team_id → dim_team, priority → dim_priority
- Mesures :
  - resolution_minutes (additive en théorie, mais on l'agrège par MÉDIANE → non additive en pratique)
  - is_breach_sla (0/1, additive : somme = nb d'incidents hors SLA)
- Attributs propres (dimension dégénérée) : incident_id, category, status


### fact_change
- Grain : 1 ligne = 1 change unique
- Clés étrangères : date_start_key → dim_date, ci_id → dim_ci, app_id → dim_application
- Mesures :
  - has_incident_48h (0/1, additive : somme = nb de changes suivis d'un incident)
  - incidents_48h_count (additive)
  - duration_minutes = actual_end − planned_start (agrégée par médiane)
  - is_failed (0/1, depuis result, additive)
- Attributs propres : change_id, change_type (standard / normal / emergency), result
- Le taux de SRE-1 n'est PAS stocké : il est calculé dans v_change_risk

### fact_capacity
- Grain : 1 ligne = 1 CI × 1 jour (clé unique : date_key + ci_id)
- Clés étrangères : date_key → dim_date, ci_id → dim_ci
- Mesures :
  - cpu_pct (non additive → MAX / AVG)
  - disk_pct (non additive → dernière valeur pour OPS-1, MAX/AVG pour les tendances)

### Dimensions
- dim_date : date_key (AAAAMMJJ), date, day_of_week, is_weekend, week, month, quarter
  → day_of_week sert à détecter l'incident du lundi (pattern 2)

- dim_application : app_id, app_name, business_criticality (1–4)
  → construite à partir des app_id distincts de la CMDB

- dim_ci : ci_id, ci_type, app_id, owner_team

- dim_team : team_id, team_name
  → construite à partir de cmdb.owner_team ∪ incidents.team

- dim_priority : priority (P1–P4), label, sla_target_minutes
  → les cibles SLA sont des hypothèses, documentées

## Règles de qualité
- Source de vérité CI → application : la CMDB. Les incohérences avec incidents.app_id sont comptées et publiées.
- Un ratio ou un pourcentage n'est jamais stocké au grain : il se calcule à l'agrégation.
