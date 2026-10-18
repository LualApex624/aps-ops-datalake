# Vérité terrain (générée automatiquement — ne pas éditer)

Seed : `42` · période : 2026-04-01 → 2026-09-30

Volumes : 4080 incidents (doublons inclus), 1161 changes,
250 CI, 41175 relevés de capacité.

## Patterns injectés

| # | Pattern | Où | Détecté par |
|---|---|---|---|
| 1 | 60 % des changes suivis d'un incident sur le même CI sous 2–30 h (43 incidents) | Payments Gateway (APP-01), Trade Capture (APP-10), Customer Portal (APP-21) | `v_change_risk`, dashboard « Change risk », SRE-1 |
| 2 | Même incident chaque lundi ~07:30 (26 occurrences), catégorie `batch_failure` | Settlement Batch, `CI-0121` | `v_recurring_incidents`, OPS-2 |
| 3 | Disque qui se remplit linéairement de 58 % à ~87.6 % | General Ledger, `CI-0048` | OPS-1, panneau capacité |
| 4 | Durée de résolution P1/P2 × 4.5 | Core Banking (APP-05) | `v_app_criticality`, SRE-2 |

## Défauts de qualité injectés (lignes distinctes, hors lignes de pattern)

| Défaut | Lignes |
|---|---|
| Priorité manquante | 80 |
| `resolved_at` antérieur à `opened_at` | 25 |
| CI absent de la CMDB (`CI-9xxx`) | 40 |
| `app_id` incohérent avec la CMDB | 50 |
| Incidents dupliqués (même `incident_id`) | 60 |

## Hypothèses

- Cibles SLA (`priority.csv`) : P1 4 h, P2 8 h, P3 2 j, P4 5 j — choisies, non issues d'un référentiel réel.
- Priorités : P1 3 %, P2 12 %, P3 45 %, P4 40 % ; sur les applications de criticité 1 : 8 / 27 / 40 / 25 %.
- Durées de résolution log-normales (médianes P1 90 min, P2 4 h, P3 20 h, P4 50 h).
- Arrivées d'incidents : loi de Poisson (25/jour ouvré, 11/jour de week-end).
