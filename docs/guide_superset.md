# Guide d'utilisation des dashboards

Deux dashboards Superset, pensés pour le persona **SRE** (revue de fiabilité hebdomadaire). Accès : http://localhost:8089.
Chaque graphique répond à une question précise et débouche sur une décision.

Règle de lecture commune : **un taux ou une médiane ne se lit jamais sans son effectif (n)**. Sur 40 applications, quelques écarts apparaissent par pur hasard ; on n'agit que sur un écart net **et** un volume suffisant.

---

## Dashboard « Change risk » (SRE-1)

**Question** : quels changes, et sur quelles applications, sont suivis d'un incident ?
**Définition** : un change est « à risque » si un incident est ouvert **sur le même CI** dans les 48 h qui suivent son début (`v_change_risk`).

| Graphique | Ce qu'il montre | Comment le lire | Décision |
|---|---|---|---|
| **Taux global de changes à risque** (Big Number) | 17,2 % des changes (200 sur 1 161) | C'est la **référence** : un taux d'application ne se juge que par rapport à elle | — |
| **Taux par application** (barres, top 15) | Part des changes de chaque application suivis d'un incident | Chercher les barres **nettement détachées** de la référence. Ici : Customer Portal (72 %), Trade Capture (70 %), Payments Gateway (55 %), puis une chute à 29 % | Mettre ces applications en **revue de change renforcée** et exiger des tests de non-régression |
| **Changes suivis d'un incident** (table) | Le détail : date, change, application, CI, type, résultat, nombre d'incidents, délai avant le 1ᵉʳ incident | Partir des applications repérées sur les barres, puis examiner leurs changes un par un | Contacter l'implémenteur, ouvrir une analyse de cause racine |

**Pièges**
- Le taux par application est calculé comme `somme des changes touchés / somme des changes`, **jamais** comme une moyenne des taux. Sinon, une application de 12 changes pèserait autant qu'une de 33.
- Un change avec 2 ou 3 incidents ne compte qu'**une fois** dans le taux (`has_incident_48h` vaut 0 ou 1) ; `n_incidents_48h` mesure la gravité.
- Une corrélation dans le temps n'est pas une preuve : la table désigne des **candidats** à examiner.

---

## Dashboard « Incident analytics » (SRE-2, SRE-3, OPS-2)

| Graphique | Question | Comment le lire | Décision |
|---|---|---|---|
| **Volume hebdomadaire par priorité** (barres empilées) | La charge évolue-t-elle, et sur quelles priorités ? | Environ 150 incidents par semaine, surtout P3 et P4. La couche `<NULL>` correspond aux **80 incidents sans priorité** : elle est laissée visible volontairement | Suivre la tendance ; relancer la qualité de saisie si la part `<NULL>` augmente |
| **Applications vs cible SLA (P1/P2)** (table) | Quelles applications résolvent leurs incidents graves trop lentement ? | `sla_ratio_median_p1_p2` = durée médiane / cible SLA. **Au-dessus de 1, le SLA n'est pas tenu** (case colorée). Seules les applications avec au moins 10 incidents P1/P2 résolus sont affichées. Ici : **Core Banking à 1,82** (n = 65), la suivante à 0,71 | Financer un chantier de fiabilisation ou revoir l'escalade de Core Banking |
| **Top 10 catégories du trimestre et runbooks** (table) | Quels incidents fréquents n'ont aucune procédure ? | Lignes avec `n_runbooks = 0` (colorées) : **cert_expiry** et **memory_leak** | Créer des tickets de rédaction de runbook, puis d'automatisation |
| **Incidents récurrents (top 20)** (table) | Quel incident revient, au même endroit, au même moment ? | `modal_dow_share` = part des occurrences tombant le jour le plus fréquent (environ 14 % si c'est le hasard). **CI-0121 : 26 semaines sur 26, 100 % le lundi, vers 7 h**. CI-0182 a presque autant d'occurrences, mais réparties au hasard | Signaler au SRE pour un correctif définitif (ici, décaler le job `PURGE_WE`) |

**Pièges**
- **Fréquence ≠ régularité** : la table se lit d'abord par `is_weekly_pattern`, puis par le nombre d'occurrences.
- **Semaines incomplètes** : la première et la dernière barre du volume hebdomadaire couvrent moins de 7 jours. Leur hauteur plus faible ne signale pas une baisse d'activité.
- Les médianes et le ratio au SLA couvrent **toute la période** (avril → septembre 2026) : elles ne réagissent pas à un filtre de période.

---

## Ce que les dashboards ne couvrent pas (et où le trouver)

| Besoin | Où |
|---|---|
| Le disque bientôt plein (OPS-1) | Agent : « Quel serveur a le disque le plus rempli au dernier relevé ? » |
| Quel runbook appliquer (OPS-2) | Agent : recherche sémantique dans les runbooks |
| Quelle équipe prévenir pour un CI (OPS-3) | Agent : requête sur `dim_ci` |
