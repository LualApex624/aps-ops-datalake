---
id: RB-008
title: Dégradation des temps de réponse
type: runbook
category: latency
applies_to: [app_server, web_server, db_server, network_device, storage]
owner_team: infra-systems
last_reviewed: 2026-06-15
---

# Dégradation des temps de réponse

## Symptômes
« Response time above threshold », lenteurs signalées par les utilisateurs.

## Diagnostic
1. Situer la couche lente : web, application, base, réseau (tableau de bord APM).
2. Corréler avec la charge CPU du jour (capacity).

## Résolution
1. Si la base est en cause : appliquer RB-003.
2. Si CPU > 90 % : identifier le processus et envisager un ajout de ressources.
3. Sinon, ouvrir un ticket à l'équipe de la couche identifiée.

## Escalade
Dégradation sur application de criticité 1 pendant plus de 30 min : P2.
