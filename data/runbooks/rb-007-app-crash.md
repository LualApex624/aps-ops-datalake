---
id: RB-007
title: Redémarrage d'un service applicatif (JVM)
type: runbook
category: app_crash
applies_to: [app_server, web_server]
owner_team: run-payments
last_reviewed: 2026-06-15
---

# Redémarrage d'un service applicatif (JVM)

## Symptômes
« Service unavailable », « HTTP 503 », processus JVM arrêté.

## Diagnostic
1. Récupérer les dernières lignes du log applicatif et le fichier hs_err si présent.
2. Vérifier si un change a eu lieu sur ce CI dans les 48 h (vue `v_change_risk`).

## Résolution
1. Redémarrer le service via le script de l'équipe (`svc restart <app>`).
2. Vérifier le health check.
3. Si un change récent existe : contacter son implémenteur avant tout autre redémarrage.

## Escalade
Deuxième crash en 24 h ou application de criticité 1 : P1/P2 selon l'impact, prévenir le responsable applicatif.
