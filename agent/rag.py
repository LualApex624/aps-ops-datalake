"""
rag.py — recherche sémantique dans les runbooks et post-mortems (outil search_runbooks).

Principe (RAG = Retrieval-Augmented Generation) :
  1. indexation (une fois) : chaque document est transformé en vecteur (embedding)
     par un modèle local, et les vecteurs sont enregistrés dans agent/index/runbooks.json ;
  2. recherche : la question est transformée en vecteur, puis comparée à chaque document
     par similarité cosinus ; on renvoie les k documents les plus proches.

Choix assumés :
  - 1 document = 1 morceau (chunk) : les runbooks font ~120 mots ; à plus grande échelle,
    on découperait par section (## Diagnostic, ## Résolution…).
  - Pas de base vectorielle (ChromaDB, pgvector) : 16 documents tiennent en mémoire et numpy
    suffit. Le passage à pgvector serait l'étape naturelle en production.
  - L'embedding passe par la gateway (llm_client.embed) : appel journalisé comme les autres.

Usage (depuis la racine du repo) :
    python agent/rag.py --build                       # (re)construit l'index
    python agent/rag.py "batch en échec le lundi"     # teste une recherche
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from llm_client import EMBED_MODEL, embed

ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS = ROOT / "data" / "runbooks"
INDEX = Path(__file__).parent / "index" / "runbooks.json"
MIN_SCORE = 0.35   # en dessous, on considère qu'aucun document ne correspond


def _read(path: Path) -> tuple[dict, str]:
    """Sépare l'en-tête YAML (clé: valeur) du corps Markdown."""
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        head, _, body = text[3:].partition("\n---")
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, body.strip()


def build() -> int:
    docs = []
    for path in sorted(RUNBOOKS.glob("*.md")):
        meta, body = _read(path)
        if meta.get("type") not in {"runbook", "postmortem"}:
            continue
        docs.append({"id": meta.get("id", path.stem), "title": meta.get("title", path.stem),
                     "type": meta["type"], "category": meta.get("category", ""),
                     "owner_team": meta.get("owner_team", ""), "file": path.name, "text": body})
    vectors = embed([f"{d['title']}\n{d['text']}" for d in docs], purpose="rag_index")
    for d, v in zip(docs, vectors):
        d["vector"] = v
    INDEX.parent.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps({"model": EMBED_MODEL, "docs": docs}, ensure_ascii=False), encoding="utf-8")
    return len(docs)


def search_runbooks(query: str, k: int = 3) -> dict:
    """Renvoie les k documents les plus proches de la requête. Ne lève pas d'exception."""
    out = {"query": query, "results": [], "error": None}
    try:
        if not INDEX.exists():
            raise FileNotFoundError("index absent : lancer python agent/rag.py --build")
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        if index["model"] != EMBED_MODEL:
            raise ValueError(f"index construit avec {index['model']}, modèle actuel {EMBED_MODEL} : reconstruire")
        docs = index["docs"]
        m = np.array([d["vector"] for d in docs], dtype=float)
        q = np.array(embed([query], purpose="rag_query")[0], dtype=float)
        scores = (m @ q) / (np.linalg.norm(m, axis=1) * np.linalg.norm(q))
        for i in np.argsort(-scores)[:k]:
            if scores[i] < MIN_SCORE:
                break
            d = docs[i]
            out["results"].append({"id": d["id"], "title": d["title"], "type": d["type"],
                                   "category": d["category"], "owner_team": d["owner_team"],
                                   "file": d["file"], "score": round(float(scores[i]), 3),
                                   "text": d["text"][:1200]})
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["--build"]:
        print(f"{build()} documents indexés avec {EMBED_MODEL} → {INDEX}")
    else:
        res = search_runbooks(" ".join(sys.argv[1:]) or "batch en échec le lundi matin")
        print(res["error"] or "\n".join(f"{r['score']:.3f}  {r['id']}  {r['title']}" for r in res["results"]))
