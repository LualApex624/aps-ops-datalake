## Persona : SRE
- Qui : ingénieur fiabilité dans l’équipe production. Il rend compte au responsable de la production IT.
- Quand il ouvre l'outil : chaque semaine en revue de fiabilité, et après tout incident majeur (P1).
- Sa question n°1 : Quelles applications ou quels CI concentrent les incidents récurrents ou post-change, et lesquels sont critiques pour le métier ?
- Ce qu'il décide ensuite : automatiser la correction d’un incident récurrent, ouvrir une analyse de cause racine, renforcer la validation des changes d’une application.
- Utilité de l'outil : Eviter de croiser à la main des exports ITSM et CMDB dans Excel, donc l’analyse n’est jamais faite.
- Où il regarde : les dashboards en priorité, et l’agent pour les questions ad hoc en SQL.

- ## Persona : OPs
- Qui : opérateur run ou d’astreinte. Il rend compte au team lead du run.
- Quand il ouvre l'outil : à l’arrivée d’un ticket, plusieurs fois par jour.
- Sa question n°1 : Cet incident est-il déjà arrivé sur ce CI ? Comment a-t-il été résolu, et quel runbook s’applique ?
- Ce qu'il décide ensuite : appliquer le runbook, ou escalader vers l’équipe propriétaire du CI.
- Utilité de l'outil : Eviter de , chercher dans le wiki, ne pas savoir qui possède le CI, escalader des incidents déjà connus.
- Où il regarde : l’agent en priorité, qui interroge l’historique et les runbooks.
