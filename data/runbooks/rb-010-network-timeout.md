---
id: RB-010
title: Pertes de paquets et timeouts réseau
type: runbook
category: network_timeout
applies_to: [network_device]
owner_team: infra-network
last_reviewed: 2026-06-15
---

# Pertes de paquets et timeouts réseau

## Symptômes
« Packet loss NN% », « Connection timeouts ».

## Diagnostic
1. Vérifier l'état des interfaces et les erreurs CRC sur l'équipement.
2. Lister les applications hébergées en aval (requête OPS-3 sur la CMDB).

## Résolution
1. Basculer sur le lien redondant si disponible.
2. Ouvrir un ticket opérateur si le lien externe est en cause.

## Escalade
Applications de criticité 1 impactées : P1, prévenir les équipes propriétaires.
