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
