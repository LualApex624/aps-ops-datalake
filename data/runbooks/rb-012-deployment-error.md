---
id: RB-012
title: Rollback d'une mise en production
type: runbook
category: deployment_error
applies_to: [app_server, web_server]
owner_team: run-payments
last_reviewed: 2026-06-15
---

# Rollback d'une mise en production

## Symptômes
« Errors after deployment », « Release failed health check » dans les heures qui suivent un change.

## Diagnostic
1. Identifier le change concerné (même CI, moins de 48 h).
2. Comparer le taux d'erreur avant et après le change.

## Résolution
1. Appliquer le plan de retour arrière décrit dans le change.
2. Passer le change en résultat `rolled_back`.
3. Rattacher l'incident au change pour le suivi SRE.

## Escalade
Rollback impossible ou application de criticité 1 indisponible : P1.
