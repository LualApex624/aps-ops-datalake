---
id: RB-004
title: Relance d'une chaîne batch en erreur
type: runbook
category: batch_failure
applies_to: [batch_server]
owner_team: run-markets
last_reviewed: 2026-06-15
---

# Relance d'une chaîne batch en erreur

## Symptômes
« Batch job NN ended in error », chaîne batch arrêtée.

## Diagnostic
1. Consulter le log du job en erreur dans l'ordonnanceur.
2. Identifier l'étape en échec et ses dépendances amont.

## Résolution
1. Corriger la cause si elle est connue (fichier manquant, verrou).
2. Relancer à partir de l'étape en échec, jamais depuis le début sans accord métier.
3. Vérifier les volumes traités en fin de chaîne.

## Escalade
Batch réglementaire ou de règlement en retard sur son SLA : P2, prévenir le métier.
