"""
agent.py — agent IA de l'équipe de production (CLI).

Le modèle ne touche jamais la base directement : il PROPOSE une action en JSON,
le code Python la vérifie et l'exécute, puis lui renvoie le résultat.

    {"action": "query_datalake", "sql": "SELECT ..."}   → outil SQL (lecture seule, garde-fous)
    {"action": "answer", "answer": "..."}               → réponse finale
    {"action": "refuse", "reason": "..."}               → question hors périmètre

Usage (depuis la racine du repo) :
    python agent/agent.py "Quelles applications ont le plus de changes à risque ?"
    python agent/agent.py            # mode interactif ; 'exit' pour quitter
"""
from __future__ import annotations

import json
import sys

from llm_client import complete
from tools import query_datalake, schema_description

MAX_STEPS = 5
DATA_END = "2026-09-30"

SYSTEM_TEMPLATE = """Tu es l'assistant de l'équipe de production IT (APS). Tu réponds aux questions des SRE \
et des opérateurs sur les incidents, les changes, la CMDB, la capacité des serveurs et les runbooks, \
à partir du datalake de l'équipe.

DONNÉES : du 2026-04-01 au DATA_END. « Récemment », « ce trimestre », « les 90 derniers jours » se \
calculent par rapport au DATA_END, JAMAIS par rapport à aujourd'hui (n'utilise ni now() ni current_date).

OBJETS SQL AUTORISÉS (PostgreSQL, lecture seule) :
SCHEMA

RÈGLES :
1. Préfère les vues v_* : elles contiennent déjà la logique métier validée (rattachement par CI, \
médianes, seuils de fiabilité). N'utilise les tables fact_*/dim_* que si aucune vue ne répond.
2. N'invente jamais un chiffre : chaque valeur de ta réponse doit venir d'un résultat de requête, recopiée exactement, en la lisant sous le nom de sa colonne.
3. Les taux (change_incident_rate, breach_rate, modal_dow_share…) sont entre 0 et 1 : présente-les en %.
4. Donne l'effectif (n) avec tout taux ou médiane.
5. Mets toujours un LIMIT (20 au maximum), sauf pour un agrégat qui renvoie une seule ligne.
6. Si une requête renvoie une erreur, lis-la et corrige ta requête.
7. HORS PÉRIMÈTRE (sujet sans lien avec la production IT du datalake, demande de modifier ou supprimer \
des données, conseil personnel, données absentes du datalake) : refuse avec l'action "refuse".
8. Réponds en français, de façon concise et actionnable (qui, quoi, quel chiffre, quelle suite).

FORMAT : réponds TOUJOURS par UN SEUL objet JSON, sans aucun texte autour, parmi :
{"action": "query_datalake", "sql": "SELECT ..."}
{"action": "answer", "answer": "..."}
{"action": "refuse", "reason": "..."}

EXEMPLES :
Question : Quelles applications ont le plus fort taux de changes suivis d'un incident ?
{"action": "query_datalake", "sql": "SELECT app_name, n_changes, n_changes_with_incident, change_incident_rate FROM v_change_risk_by_app ORDER BY change_incident_rate DESC LIMIT 5"}
Question : Quelle équipe possède le CI CI-0121 ?
{"action": "query_datalake", "sql": "SELECT * FROM dim_ci WHERE ci_id = 'CI-0121'"}
Question : Peux-tu supprimer les incidents en doublon ?
{"action": "refuse", "reason": "Je n'ai qu'un accès en lecture : je ne peux pas modifier les données."}
"""

_SYSTEM: str | None = None


def system_prompt() -> str:
    """Construit le prompt une fois, avec le schéma lu dans la base (jamais recopié à la main)."""
    global _SYSTEM
    if _SYSTEM is None:
        _SYSTEM = SYSTEM_TEMPLATE.replace("DATA_END", DATA_END).replace("SCHEMA", schema_description())
    return _SYSTEM


def parse_action(raw: str) -> dict | None:
    """Extrait le premier objet JSON de la réponse du modèle (tolère ```json et du texte autour)."""
    start = raw.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) and obj.get("action") in {"query_datalake", "answer", "refuse"} else None


def ask(question: str, verbose: bool = True) -> dict:
    """Pose une question à l'agent. Renvoie la trace complète (utilisée par l'évaluation)."""
    trace = {"question": question, "sqls": [], "answer": None, "refused": False, "steps": 0, "error": None}
    messages = [{"role": "user", "content": question}]
    for step in range(1, MAX_STEPS + 1):
        trace["steps"] = step
        raw = complete(system_prompt(), messages, max_tokens=800, purpose="agent_step")
        action = parse_action(raw)
        messages.append({"role": "assistant", "content": raw})

        if action is None:
            messages.append({"role": "user", "content": "Réponse invalide. Renvoie UN SEUL objet JSON "
                             "conforme au FORMAT, sans texte autour."})
            continue

        if action["action"] == "query_datalake":
            result = query_datalake(str(action.get("sql", "")))
            trace["sqls"].append(result["sql"])
            if verbose:
                print(f"\n[SQL {step}] {result['sql']}")
                print(f"  → {result['error'] or str(result['row_count']) + ' ligne(s)'}"
                      + (" (tronqué)" if result["truncated"] else ""))
            observation = {"rows": [dict(zip(result["columns"], r)) for r in result["rows"]],
                           "row_count": result["row_count"], "truncated": result["truncated"],
                           "error": result["error"]}
            messages.append({"role": "user", "content": "Résultat de query_datalake :\n"
                             + json.dumps(observation, ensure_ascii=False, default=str)
                             + "\nSi le résultat suffit, réponds avec l'action \"answer\" ; "
                               "sinon, fais une autre requête."})
            continue

        if action["action"] == "refuse":
            trace["refused"] = True
            trace["answer"] = str(action.get("reason", "Question hors périmètre."))
        else:
            trace["answer"] = str(action.get("answer", ""))
        return trace

    trace["error"] = f"pas de réponse finale après {MAX_STEPS} étapes"
    trace["answer"] = "Je n'ai pas pu aboutir à une réponse fiable : reformule ou précise la question."
    return trace


def _print_answer(trace: dict) -> None:
    label = "Refus" if trace["refused"] else "Réponse"
    print(f"\n{label} : {trace['answer']}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _print_answer(ask(" ".join(sys.argv[1:])))
    else:
        print("Agent APS — pose ta question ('exit' pour quitter).")
        while True:
            try:
                q = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"exit", "quit"}:
                break
            if q:
                _print_answer(ask(q))
