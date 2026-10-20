# Analyse de l'évaluation de l'agent

Exécution : `results/run_20261021_0108.json` · modèle `ollama` / `qwen2.5:7b` (local, température 0)

**Score : 11/12 au contrôle automatique, 10/12 après relecture manuelle** (Q10 requalifiée en échec).
Critère du projet (≥ 10/12, chaque échec expliqué) : atteint.

## Échecs

### Q03 — mauvaise colonne, puis conclusion tirée d'un résultat vide
- SQL généré : `SELECT … FROM v_app_criticality WHERE business_criticality = 1 AND breach_rate > 1 …`
- Cause 1 : confusion entre `breach_rate` (part des incidents hors SLA, entre 0 et 1, toutes priorités)
  et `sla_ratio_median_p1_p2` (durée médiane / cible SLA ; > 1 = SLA dépassé). `breach_rate > 1` est
  impossible : la requête renvoie 0 ligne.
- Cause 2 : le modèle interprète ce résultat vide comme une réponse (« aucune application »)
  au lieu de remettre en cause sa requête → réponse fausse donnée avec assurance.
- Origine : le schéma transmis au modèle ne contient que les noms et types des colonnes, pas leur sens.
- Pistes : documenter chaque colonne dans la base (`COMMENT ON COLUMN`) et injecter ce dictionnaire
  de données dans le prompt ; règle « un résultat vide impose de vérifier la condition avant de
  conclure ». Requête correcte : `… WHERE business_criticality = 1 AND is_sla_at_risk`.

### Q10 — conseil hors sujet (faux positif du contrôle automatique)
- La réponse reconnaît qu'aucun runbook ne couvre l'expiration de certificat, puis recommande RB-009
  (authentification LDAP) avec une justification inventée.
- Cause : la recherche sémantique renvoie des documents de thème voisin, avec des scores (0,42–0,44)
  indiscernables de ceux d'un bon résultat ; le modèle 7B cherche à rendre utile ce qu'on lui fournit.
- Pistes : recherche hybride (mots-clés + sens) et filtre sur la catégorie de l'incident ; ne transmettre
  au modèle que les documents de la bonne catégorie ; modèle plus grand ; renforcer le contrôle
  automatique (`must_not_contain` sur les runbooks hors sujet).

## Réserves (réponses justes, formulation imprécise)
- Q01 : « 18 incidents » au lieu de « 18 changes suivis d'un incident ».
- Q08 : relation CI ↔ application inversée dans la phrase.

## Limites de l'évaluation
- Contamination : Q06, Q07 et Q10 ressemblent à des questions utilisées pendant la mise au point ;
  leur score est probablement optimiste.
- Petit échantillon : 10/12 = 83 %, intervalle de confiance à 95 % (Wilson) ≈ 55 %–95 %.
- Contrôle par expressions régulières : il mesure la présence de mots, pas la justesse du conseil ;
  la relecture manuelle reste indispensable (cf. Q10).
- Un seul modèle et une seule exécution ; les sorties d'un LLM peuvent varier d'une exécution à l'autre.
