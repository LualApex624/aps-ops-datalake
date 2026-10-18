---
id: RB-005
title: Batch SETL_J1 en échec le lundi matin (deadlock)
type: runbook
category: batch_failure
applies_to: [batch_server]
owner_team: run-markets
last_reviewed: 2026-06-15
---

# Batch SETL_J1 en échec le lundi matin (deadlock)

## Symptômes
Chaque lundi vers 07:30 : « Settlement batch SETL_J1 failed: ORA-00060 deadlock detected » sur le serveur batch de Settlement Batch.

## Diagnostic
1. Confirmer que le job de purge du week-end (`PURGE_WE`) s'est terminé après 07:00 : c'est la cause connue du verrou.
2. Vérifier qu'aucune autre session ne tient de verrou sur `SETTLEMENT_QUEUE`.

## Résolution
1. Attendre la fin de `PURGE_WE`.
2. Relancer SETL_J1 depuis l'étape STEP_030.
3. Contrôler le nombre d'instructions réglées avant 09:00 (ouverture des marchés).

## Escalade
Correctif définitif à automatiser : décaler `PURGE_WE` ou ajouter une dépendance dans l'ordonnanceur (problème ouvert côté SRE).
