---
id: RB-001
title: Saturation d'un système de fichiers
type: runbook
category: disk_full
applies_to: [app_server, web_server, batch_server, storage]
owner_team: infra-systems
last_reviewed: 2026-06-15
---

# Saturation d'un système de fichiers

## Symptômes
Alerte « Filesystem at NN% » ou « No space left on device ». Applications en erreur d'écriture.

## Diagnostic
1. `df -h` pour identifier le point de montage saturé.
2. `du -xh --max-depth=2 /data | sort -h | tail` pour trouver les plus gros répertoires.
3. Vérifier si des logs applicatifs ne sont plus rotés.

## Résolution
1. Compresser ou supprimer les logs de plus de 7 jours (`find /data/logs -mtime +7 -name '*.log' -delete`).
2. Vérifier la configuration logrotate.
3. Si l'espace libre reste < 15 % : demander une extension de volume (ticket infra-systems).

## Escalade
Si > 95 % et applicatif critique : escalade immédiate infra-systems, P2.
