---
id: RB-011
title: Échec de la sauvegarde nocturne
type: runbook
category: backup_failure
applies_to: [db_server, storage]
owner_team: infra-systems
last_reviewed: 2026-06-15
---

# Échec de la sauvegarde nocturne

## Symptômes
« Nightly backup failed », « Backup job exceeded window ».

## Diagnostic
1. Lire le code d'erreur de l'outil de sauvegarde.
2. Vérifier l'espace disponible sur la cible de sauvegarde.

## Résolution
1. Relancer la sauvegarde hors des heures de batch.
2. Deux échecs consécutifs : prévenir le DBA, car la purge des archivelogs (RB-002) devient impossible.

## Escalade
Pas de sauvegarde valide depuis 48 h sur une base critique : P2.
