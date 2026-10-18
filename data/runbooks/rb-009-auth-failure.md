---
id: RB-009
title: Échec d'authentification LDAP
type: runbook
category: auth_failure
applies_to: [app_server, web_server]
owner_team: infra-systems
last_reviewed: 2026-06-15
---

# Échec d'authentification LDAP

## Symptômes
« LDAP bind failure », utilisateurs incapables de se connecter.

## Diagnostic
1. Tester le bind avec le compte de service (`ldapsearch`).
2. Vérifier l'expiration du mot de passe du compte de service.

## Résolution
1. Si le compte de service est expiré : demander son renouvellement (équipe IAM) et mettre à jour le coffre de secrets.
2. Redémarrer le service applicatif pour recharger le secret.

## Escalade
Tous les utilisateurs bloqués sur une application critique : P1.
