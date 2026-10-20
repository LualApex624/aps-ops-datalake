"""
llm_client.py — point d'accès unique au modèle de langage (LLM gateway).

Tout appel au LLM passe par complete(). Le reste du code ne connaît ni le
fournisseur ni son API : changer de modèle = changer une variable d'environnement.

Configuration : agent/.env (jamais commité), voir agent/.env.example
    LLM_PROVIDER=mistral | claude | ollama
    LLM_MODEL=mistral-large-latest | claude-sonnet-5-5 | qwen2.5:7b ...
    MISTRAL_API_KEY / ANTHROPIC_API_KEY

Journal : agent/logs/llm_calls.jsonl — une ligne par appel (date, fournisseur,
modèle, latence, tokens, statut, empreinte du prompt). Le contenu n'est PAS
journalisé : les prompts contiennent des données d'incidents.

Test rapide : python agent/llm_client.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
LOG_FILE = HERE / "logs" / "llm_calls.jsonl"
DEFAULT_MODELS = {"mistral": "mistral-large-latest", "claude": "claude-sonnet-5-5", "ollama": "qwen2.5:7b"}


def _load_env(path: Path = HERE / ".env") -> None:
    """Charge agent/.env (clé=valeur) sans dépendance externe."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env()
PROVIDER = os.environ.get("LLM_PROVIDER", "mistral")
MODEL = os.environ.get("LLM_MODEL", DEFAULT_MODELS.get(PROVIDER, ""))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def _fingerprint(system: str, messages: list[dict]) -> str:
    raw = json.dumps({"system": system, "messages": messages}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _log(record: dict) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _call_mistral(system, messages, max_tokens, temperature):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY absente de agent/.env")
    payload = {"model": MODEL, "max_tokens": max_tokens, "temperature": temperature,
               "messages": [{"role": "system", "content": system}] + messages}
    for attempt in range(4):  # plan gratuit : ~1 requête/s → réessai sur 429
        try:
            data = _post_json("https://api.mistral.ai/v1/chat/completions", payload,
                              {"Authorization": f"Bearer {key}"})
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {exc.code} : {exc.read().decode('utf-8', 'replace')[:200]}") from None
    usage = data.get("usage", {})
    return data["choices"][0]["message"]["content"], usage.get("prompt_tokens"), usage.get("completion_tokens")


def _call_claude(system, messages, max_tokens, temperature):
    import anthropic  # pip install anthropic (uniquement si LLM_PROVIDER=claude)
    resp = anthropic.Anthropic().messages.create(model=MODEL, system=system, messages=messages,
                                                 max_tokens=max_tokens, temperature=temperature)
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_ollama(system, messages, max_tokens, temperature):
    data = _post_json(f"{OLLAMA_URL}/api/chat",
                      {"model": MODEL, "stream": False,
                       "messages": [{"role": "system", "content": system}] + messages,
                       "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 8192}}, {}, timeout=180)
    return data["message"]["content"], data.get("prompt_eval_count"), data.get("eval_count")


PROVIDERS = {"mistral": _call_mistral, "claude": _call_claude, "ollama": _call_ollama}


def complete(system: str, messages: list[dict], max_tokens: int = 1024,
             temperature: float = 0.0, purpose: str = "") -> str:
    """Envoie une conversation au modèle configuré et renvoie le texte de la réponse.

    messages : [{"role": "user" | "assistant", "content": "..."}]
    purpose  : étiquette libre pour le journal (ex. "plan", "sql", "answer")
    """
    start = time.perf_counter()
    status, error, tokens_in, tokens_out = "ok", None, None, None
    try:
        if PROVIDER not in PROVIDERS:
            raise ValueError(f"LLM_PROVIDER inconnu : {PROVIDER}")
        text, tokens_in, tokens_out = PROVIDERS[PROVIDER](system, messages, max_tokens, temperature)
        return text
    except Exception as exc:
        status, error = "error", f"{type(exc).__name__}: {exc}"[:300]
        raise
    finally:
        _log({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "provider": PROVIDER, "model": MODEL, "purpose": purpose,
            "latency_ms": round((time.perf_counter() - start) * 1000),
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "status": status, "error": error,
            "prompt_sha256": _fingerprint(system, messages),
        })


if __name__ == "__main__":
    print(f"Fournisseur : {PROVIDER} · modèle : {MODEL}")
    print(complete("Réponds en un seul mot.",
                   [{"role": "user", "content": "Quelle est la capitale du Luxembourg ?"}],
                   max_tokens=20, purpose="smoke_test"))
