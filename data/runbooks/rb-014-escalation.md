---
id: RB-014
title: Matrice d'escalade
type: runbook
category: escalation
applies_to: [*]
owner_team: run-markets
last_reviewed: 2026-06-15
---

# Matrice d'escalade

## Symptômes
Besoin de savoir quelle équipe contacter.

## Diagnostic
Utiliser `owner_team` de la CMDB pour le CI concerné (la CMDB fait foi, pas le champ du ticket).

## Résolution
| Équipe | Périmètre |
|---|---|
| run-payments | Paiements, cartes, canaux clients |
| run-markets | Marchés, règlement, batchs |
| run-lending | Crédit, Core Banking, comptabilité |
| dba | Bases de données |
| infra-systems | Serveurs, stockage, sauvegarde |
| infra-network | Réseau, API Gateway |

## Escalade
Hors heures ouvrées : astreinte de l'équipe propriétaire.
