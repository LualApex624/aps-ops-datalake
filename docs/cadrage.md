## Persona : SRE
- Qui : ingénieur fiabilité dans l'équipe production. Il rend compte au responsable de la production IT.
- Quand il ouvre l'outil : chaque semaine en revue de fiabilité, et après tout incident majeur (P1).
- Sa question n°1 : Quelles applications ou quels CI concentrent les incidents récurrents ou post-change, et lesquels sont critiques pour le métier ?
- Ce qu'il décide ensuite : automatiser la correction d'un incident récurrent, ouvrir une analyse de cause racine, renforcer la validation des changes d'une application.
- Utilité de l'outil : éviter de croiser à la main des exports ITSM et CMDB dans Excel, ce qui fait que l'analyse n'est jamais faite.
- Où il regarde : les dashboards en priorité, et l'agent pour les questions ad hoc en SQL.

## Persona : OPS
- Qui : opérateur run ou d'astreinte. Il rend compte au team lead du run.
- Quand il ouvre l'outil : à l'arrivée d'un ticket, plusieurs fois par jour.
- Sa question n°1 : Cet incident est-il déjà arrivé sur ce CI ? Comment a-t-il été résolu, et quel runbook s'applique ?
- Ce qu'il décide ensuite : appliquer le runbook, ou escalader vers l'équipe propriétaire du CI.
- Utilité de l'outil : éviter de chercher dans le wiki, de ne pas savoir qui possède le CI, et d'escalader des incidents déjà connus.
- Où il regarde : l'agent en priorité, qui interroge l'historique et les runbooks.

## Use cases

### SRE-1 : Quelles applications critiques ont le plus fort taux de changes suivis d'un incident dans les 48 h, sur les 90 derniers jours ?
- Définition : taux = nb de changes suivis d'≥ 1 incident **sur le même CI (ci_id)**, ouvert dans l'intervalle ]planned_start ; planned_start + 48 h], ÷ nb total de changes de l'application
- Pourquoi le CI et pas l'application : une application a plusieurs CI, donc un incident tombe presque toujours dans la fenêtre ; rattaché par app_id, le taux de base dépasse 60 % et le signal disparaît. Par CI, le taux de base est ≈ 15 % et les applications à risque ressortent à 55–72 %.
- Garde-fous : afficher n_changes à côté du taux ; n'alerter que si écart net à la médiane ET volume suffisant (40 applications comparées → risque de faux positifs).
- Décision : passer ces applications en revue de change renforcée et imposer des tests de non-régression
- Données : changes, incidents, cmdb
- Implémentation : vues v_change_risk (1 ligne par change) et v_change_risk_by_app (taux par application)
- Où : dashboard « Change risk »
- Pattern couvert : 1

### SRE-2 : Quelles applications de criticité 1 ont un MTTR médian des incidents P1/P2 supérieur à la cible SLA ?
- Définition : MTTR médian = médiane de (resolved_at − opened_at), durées ≥ 0 uniquement ; comparé à la cible SLA via le ratio médian durée / cible (lue dans priority, hypothèse documentée) ; n affiché, médiane jugée fiable si n ≥ 10
- Période : 6 mois (avril → septembre 2026) dans v_app_criticality ; le contrôle de vérité terrain porte sur le T3
- Décision : financer un chantier de fiabilisation ou revoir le processus d'escalade de ces applications
- Données : incidents, cmdb, priority
- Implémentation : vue v_app_criticality (médianes calculées au grain application, non ré-agrégeables)
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
- Définition : même ci_id + même description normalisée ; régularité mesurée par la part des occurrences tombant le jour de semaine le plus fréquent (hasard ≈ 14 %) ; motif hebdomadaire si ≥ 8 semaines distinctes et ≥ 80 % le même jour
- Décision : appliquer le runbook ; si récurrent, signaler au SRE pour automatisation
- Données : incidents, runbooks
- Implémentation : vue v_recurring_incidents
- Où : agent
- Pattern couvert : 2

### OPS-3 : Quelles applications sont hébergées sur ce CI, quelle est leur criticité et quelle équipe prévenir ?
- Décision : notifier les équipes propriétaires ; escalader en P1 si une application de criticité 1 est touchée
- Données : incidents, cmdb
- Où : agent
- Limite : pas de graphe de dépendances entre CI → impact « en aval » non couvert

## Modèle de données

### fact_incident
- Grain : 1 ligne = 1 incident unique (après dédoublonnage en silver)
- Clés étrangères : opened_at::date → dim_date, ci_id → dim_ci, app_id_clean → dim_application, cmdb__owner_team → dim_team, priority → dim_priority
- Mesures :
  - resolution_minutes (additive en théorie, mais on l'agrège par MÉDIANE → non additive en pratique)
  - is_breach_sla (0/1 entier, additive : somme = nb d'incidents hors SLA)
- Attributs propres (dimension dégénérée) : incident_id, category, status, description_norm
- Drapeaux qualité : dq_missing_priority, dq_negative_duration, dq_orphan_ci, dq_app_mismatch

### fact_change
- Grain : 1 ligne = 1 change unique
- Clés étrangères : planned_start::date → dim_date, ci_id → dim_ci, app_id → dim_application
- Mesures stockées :
  - duration_minutes = actual_end − planned_start (agrégée par médiane)
  - is_failed (0/1, depuis result ∈ {failed, rolled_back}, additive)
- Mesures calculées dans v_change_risk (non stockées, car elles dépendent de fact_incident) :
  - has_incident_48h (0/1, additive : somme = nb de changes suivis d'un incident)
  - n_incidents_48h (additive)
- Attributs propres : change_id, type (standard / normal / emergency), result
- Le taux de SRE-1 n'est PAS stocké : il est calculé dans v_change_risk_by_app

### fact_capacity
- Grain : 1 ligne = 1 CI × 1 jour (clé unique : date + ci_id)
- Clés étrangères : date → dim_date, ci_id → dim_ci
- Mesures :
  - cpu_pct (non additive → MAX / AVG)
  - disk_pct (non additive → dernière valeur pour OPS-1, MAX/AVG pour les tendances)

### Dimensions
- dim_date (créée en SQL, sql/schema.sql) : date_key (date), year, quarter, month, month_name, iso_week, day_of_week (1 = lundi), day_name, is_weekend
  → day_of_week sert à détecter l'incident du lundi (pattern 2) ; partir de dim_date fait apparaître les jours sans incident
- dim_application : app_id, app_name, business_criticality (1–4)
  → Group sur la CMDB par app_id (40 lignes)
- dim_ci : ci_id, ci_type, app_id, owner_team
- dim_team : owner_team (6 équipes)
  → Group sur cmdb.owner_team ; la CMDB fait foi
- dim_priority : priority (P1–P4), label, sla_target_minutes (entier)
  → les cibles SLA sont des hypothèses, documentées

## Règles de qualité
- Source de vérité CI → application : la CMDB. Les incohérences avec incidents.app_id sont comptées et publiées (dq_app_mismatch) ; les analyses utilisent app_id_clean.
- Corriger quand la vérité est connue, sinon marquer (dq_*) ; toujours compter.
- Un ratio ou un pourcentage n'est jamais stocké au grain : il se calcule à l'agrégation.
- Une médiane n'est pas ré-agrégeable : elle est calculée au grain d'analyse, dans la vue.
- Les durées négatives (dq_negative_duration) sont exclues des médianes.
- Un indicateur n'est affiché qu'avec son effectif n ; seuil de fiabilité n ≥ 10.
- Les types sont corrigés à la source (ex. sla_target_minutes passé de text à int dans Dataiku), pas par des conversions dans chaque requête.
