---
id: RB-002
title: Purge des archivelogs sur un serveur Oracle
type: runbook
category: disk_full
applies_to: [db_server]
owner_team: dba
last_reviewed: 2026-06-15
---

# Purge des archivelogs sur un serveur Oracle

## Symptômes
Disque /u02 ou /data au-delà de 85 % sur un serveur de base de données ; croissance régulière.

## Diagnostic
1. Vérifier l'état de la dernière sauvegarde RMAN.
2. Mesurer la tendance de remplissage sur 14 jours (dashboard capacité).

## Résolution
1. Ne purger les archivelogs qu'**après** une sauvegarde RMAN réussie : `DELETE ARCHIVELOG ALL BACKED UP 1 TIMES TO DISK;`.
2. Si la croissance est structurelle (tendance linéaire), demander une extension de stockage avant 90 %.

## Escalade
Remplissage projeté > 90 % sous 7 jours : ticket DBA + infra-systems, P2.
