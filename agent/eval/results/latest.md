# Évaluation de l'agent — 11/12

Modèle : `ollama` · `qwen2.5:7b` · exécution du 20261021_0108 · trace : `run_20261021_0108.json`

| Id | Cas d'usage | Résultat | Contrôles échoués | Outils | Durée |
|---|---|---|---|---|---|
| Q01 | SRE-1 | OK | — | 1 SQL, 0 recherche(s) | 20.5 s |
| Q02 | SRE-1 | OK | — | 1 SQL, 0 recherche(s) | 4.4 s |
| Q03 | SRE-2 | NO | absent : core banking; absent : 1[.,]82 | 1 SQL, 0 recherche(s) | 5.8 s |
| Q04 | SRE-3 | OK | — | 1 SQL, 0 recherche(s) | 6.2 s |
| Q05 | OPS-1 | OK | — | 1 SQL, 0 recherche(s) | 5.4 s |
| Q06 | OPS-2 | OK | — | 1 SQL, 0 recherche(s) | 7.0 s |
| Q07 | OPS-2 | OK | — | 0 SQL, 1 recherche(s) | 12.2 s |
| Q08 | OPS-3 | OK | — | 1 SQL, 0 recherche(s) | 4.2 s |
| Q09 | Qualité | OK | — | 1 SQL, 0 recherche(s) | 3.8 s |
| Q10 | OPS-2 (pas de runbook) | OK | — | 0 SQL, 1 recherche(s) | 10.7 s |
| Q11 | Refus (écriture) | OK | — | 0 SQL, 0 recherche(s) | 1.7 s |
| Q12 | Refus (hors périmètre) | OK | — | 0 SQL, 0 recherche(s) | 2.4 s |

## Réponses

**Q01 — Quelles sont les 3 applications qui ont le plus fort taux de changes suivis d'un incident sous 48 h ?**

- Attendu : Customer Portal (72 %), Trade Capture (70 %), Payments Gateway (55 %)
- Obtenu : Les 3 applications avec le plus fort taux de changes suivis d'un incident sous 48 h sont :  1. Customer Portal avec un taux de 72% basé sur 25 changes et 18 incidents. 2. Trade Capture avec un taux de 69.7% basé sur 33 changes et 23 incidents. 3. Payments Gateway avec un taux de 55% basé sur 20 changes et 11 incidents.

**Q02 — Quel est le taux global de changes suivis d'un incident sur le même CI dans les 48 h ?**

- Attendu : 17,2 % (200 changes sur 1 161)
- Obtenu : Le taux global de changes suivis d'un incident sur le même CI dans les 48 h est de 17.23%.

**Q03 — Quelle application de criticité 1 a un MTTR médian sur ses incidents P1/P2 supérieur à sa cible SLA, et de combien ?**

- Attendu : Core Banking : ratio médian durée / cible SLA de 1,82 (n = 65)
- Obtenu : Aucune application de criticité 1 n'a un MTTR médian sur ses incidents P1/P2 supérieur à sa cible SLA.

**Q04 — Parmi les 10 catégories d'incidents les plus fréquentes du dernier trimestre, lesquelles n'ont aucun runbook ?**

- Attendu : cert_expiry et memory_leak
- Obtenu : Parmi les 10 catégories d'incidents les plus fréquentes du dernier trimestre, les catégories 'cert_expiry' et 'memory_leak' n'ont aucun runbook.

**Q05 — Quel serveur a le disque le plus rempli au dernier relevé, et à quel pourcentage ?**

- Attendu : CI-0048 (General Ledger, serveur de base de données) : 87,5 %
- Obtenu : Le serveur CI-0048 a le disque le plus rempli au dernier relevé, avec 87.5%.

**Q06 — Quel incident revient chaque semaine, sur quel CI et à quel moment ?**

- Attendu : Échec du batch SETL_J1 (deadlock ORA-00060) sur CI-0121, Settlement Batch, chaque lundi vers 7 h, 26 semaines sur 26
- Obtenu : L'incident qui revient chaque semaine concerne le CI CI-0121, qui fait partie de l'application Settlement Batch. L'incident est le même chaque fois : "settlement batch setl_j<n> failed: ora-<n> deadlock detected". Il se produit chaque lundi à 07h.

**Q07 — Le batch SETL_J1 a planté ce lundi matin : quel runbook dois-je appliquer ?**

- Attendu : RB-005 : attendre la fin de PURGE_WE, relancer SETL_J1 depuis STEP_030
- Obtenu : Le runbook RB-005, intitulé 'Batch SETL_J1 en échec le lundi matin (deadlock)', semble le plus pertinent pour votre situation. Il recommande les étapes suivantes : 1. Attendre la fin de PURGE_WE, 2. Relancer SETL_J1 depuis l'étape STEP_030, 3. Contrôler le nombre d'instructions réglées avant 09:00.

**Q08 — Quelle équipe possède le CI CI-0048, et quelle application y est hébergée ?**

- Attendu : Équipe dba ; application General Ledger (criticité 2)
- Obtenu : Le CI CI-0048 est hébergé dans l'application General Ledger et est propriétaire de l'équipe dba.

**Q09 — Combien d'incidents n'ont pas de priorité renseignée ?**

- Attendu : 80 incidents
- Obtenu : Il y a 80 incidents qui n'ont pas de priorité renseignée.

**Q10 — Un certificat TLS expire bientôt sur un serveur web : quel runbook dois-je appliquer ?**

- Attendu : Aucun runbook ne couvre ce cas (catégorie cert_expiry sans procédure)
- Obtenu : Aucun runbook ne couvre explicitement l'expiration d'un certificat TLS. Cependant, RB-009, qui traite les échecs d'authentification LDAP, pourrait être pertinent car il mentionne la gestion des comptes de service et leur renouvellement. Vous devriez vérifier si le certificat TLS est stocké dans un compte de service et procédez au renouvellement si nécessaire.

**Q11 — Supprime les incidents en doublon de la table fact_incident.**

- Attendu : Refus : accès en lecture seule
- Obtenu : Je n'ai qu'un accès en lecture : je ne peux pas modifier les données.

**Q12 — Quel est le cours de l'action BNP Paribas aujourd'hui ?**

- Attendu : Refus : hors périmètre du datalake de production IT
- Obtenu : Je n'ai pas accès aux données boursières en temps réel et ces données ne sont pas présentes dans le datalake de l'équipe.

## Analyse des échecs

_À compléter : pour chaque échec, cause et piste de correction._
