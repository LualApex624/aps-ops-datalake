"""
run_eval.py — évalue l'agent sur agent/eval/questions.yaml.

Pour chaque question : on pose la question à l'agent, on vérifie automatiquement la réponse
(expressions attendues, refus, outil utilisé), et on enregistre la trace complète.

Usage (depuis la racine du repo) :
    python agent/eval/run_eval.py              # les 12 questions
    python agent/eval/run_eval.py Q06 Q10      # seulement certaines

Sorties :
    agent/eval/results/run_<date>.json   trace complète (SQL, recherches, réponses)
    agent/eval/results/latest.md         tableau de résultats, à compléter par l'analyse des échecs
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # pour importer agent.py, tools.py, ...

from agent import ask                      # noqa: E402
from llm_client import MODEL, PROVIDER     # noqa: E402

RESULTS = HERE / "results"


def check(case: dict, trace: dict) -> list[str]:
    """Renvoie la liste des contrôles échoués (vide = réponse correcte)."""
    failures = []
    answer = (trace.get("answer") or "").lower()
    if case.get("expect_refusal", False) != trace["refused"]:
        failures.append("refus attendu" if case.get("expect_refusal") else "refus inattendu")
    for pattern in case.get("must_contain", []):
        if not re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"absent : {pattern}")
    for pattern in case.get("must_not_contain", []):
        if re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"présent à tort : {pattern}")
    tool = case.get("expected_tool")
    if tool == "query_datalake" and not trace["sqls"]:
        failures.append("aucune requête SQL")
    if tool == "search_runbooks" and not trace["searches"]:
        failures.append("aucune recherche de runbook")
    if tool == "none" and (trace["sqls"] or trace["searches"]):
        failures.append("outil utilisé alors qu'il fallait refuser directement")
    if trace.get("error"):
        failures.append(trace["error"])
    return failures


def main(selected: list[str]) -> None:
    cases = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
    if selected:
        cases = [c for c in cases if c["id"] in selected]
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            trace = ask(case["question"], verbose=False)
        except Exception as exc:  # une panne (base, Ollama) compte comme un échec, sans arrêter l'évaluation
            trace = {"question": case["question"], "sqls": [], "searches": [], "answer": None,
                     "refused": False, "steps": 0, "error": f"{type(exc).__name__}: {exc}"[:200]}
        trace["latency_s"] = round(time.perf_counter() - start, 1)
        failures = check(case, trace)
        rows.append({**case, "trace": trace, "passed": not failures, "failures": failures})
        print(f"{case['id']}  {'OK   ' if not failures else 'ÉCHEC'}  {trace['latency_s']:>5} s  "
              f"{'; '.join(failures)}")

    score = sum(r["passed"] for r in rows)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    meta = {"date": stamp, "provider": PROVIDER, "model": MODEL, "score": score, "total": len(rows)}
    (RESULTS / f"run_{stamp}.json").write_text(
        json.dumps({"meta": meta, "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Évaluation de l'agent — {score}/{len(rows)}", "",
             f"Modèle : `{PROVIDER}` · `{MODEL}` · exécution du {stamp} · trace : `run_{stamp}.json`", "",
             "| Id | Cas d'usage | Résultat | Contrôles échoués | Outils | Durée |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        t = r["trace"]
        tools = f"{len(t['sqls'])} SQL, {len(t['searches'])} recherche(s)"
        lines.append(f"| {r['id']} | {r['use_case']} | {'OK' if r['passed'] else 'NO'} | "
                     f"{'; '.join(r['failures']) or '—'} | {tools} | {t['latency_s']} s |")
    lines += ["", "## Réponses", ""]
    for r in rows:
        answer = (r["trace"]["answer"] or "").replace("\n", " ")
        lines += [f"**{r['id']} — {r['question']}**", "",
                  f"- Attendu : {r['expected']}", f"- Obtenu : {answer}", ""]
    lines += ["## Analyse des échecs", "", "_À compléter : pour chaque échec, cause et piste de correction._", ""]
    (RESULTS / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nScore : {score}/{len(rows)} → {RESULTS / 'latest.md'}")


if __name__ == "__main__":
    main(sys.argv[1:])
