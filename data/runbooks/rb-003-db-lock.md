---
id: RB-003
title: Sessions bloquantes et deadlocks
type: runbook
category: db_lock
applies_to: [db_server]
owner_team: dba
last_reviewed: 2026-06-15
---

# Sessions bloquantes et deadlocks

## Symptômes
« Blocking sessions detected », « ORA-00060 deadlock ». Transactions applicatives en timeout.

## Diagnostic
1. Identifier la session bloquante (`v$session` où `blocking_session` non nul).
2. Récupérer le SQL et le module applicatif de la session.

## Résolution
1. Si la session bloquante est un batch ou une session inactive : la tuer après accord du responsable applicatif.
2. Si deadlock récurrent : ouvrir un problème (analyse de cause racine) auprès de l'équipe applicative.

## Escalade
Plus de 3 occurrences sur le même objet en 30 jours : problème à ouvrir, propriétaire = équipe applicative.
