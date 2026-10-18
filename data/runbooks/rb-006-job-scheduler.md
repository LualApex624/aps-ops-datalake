---
id: RB-006
title: Agent d'ordonnancement arrêté
type: runbook
category: job_scheduler
applies_to: [batch_server]
owner_team: run-markets
last_reviewed: 2026-06-15
---

# Agent d'ordonnancement arrêté

## Symptômes
« Scheduler agent down », jobs non déclenchés à l'heure prévue.

## Diagnostic
1. Vérifier le processus de l'agent sur le serveur.
2. Contrôler la connectivité vers le serveur maître de l'ordonnanceur.

## Résolution
1. Redémarrer l'agent.
2. Identifier les jobs non déclenchés pendant l'arrêt et les relancer dans l'ordre des dépendances.

## Escalade
Agent impossible à redémarrer : escalade infra-systems, P2.
