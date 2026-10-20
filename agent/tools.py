"""
tools.py — outils de l'agent.

query_datalake(sql) : exécute une requête SELECT sur la couche gold, en lecture seule.
Garde-fous (défense en profondeur) :
  1. côté application : une seule instruction, SELECT/WITH uniquement, mots-clés
     d'écriture refusés ; puis on demande au moteur (EXPLAIN, sans exécuter)
     quelles tables seront lues, et on refuse tout ce qui sort de la liste blanche ;
  2. côté base : rôle agent_ro (GRANT SELECT seulement, transactions en lecture
     seule, statement_timeout de 15 s) ;
  3. côté résultat : au plus MAX_ROWS lignes renvoyées au modèle.
Le SQL exécuté est toujours renvoyé, pour être affiché à l'utilisateur.

Test rapide : python agent/tools.py
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_ROWS = 50

# Tables lues en interne par les vues (autorisées dans le plan d'exécution, pas citées au modèle)
INTERNAL = {"runbook_index"}

# Liste blanche : couche gold uniquement, avec ce que chaque objet permet de répondre.
ALLOWED = {
    "v_change_risk":         "1 ligne par change : a-t-il été suivi d'un incident sur le MÊME CI dans les 48 h ? (SRE-1)",
    "v_change_risk_by_app":  "1 ligne par application : taux de changes suivis d'un incident sous 48 h (SRE-1)",
    "v_recurring_incidents": "1 ligne par (CI, message normalisé) vu au moins 5 fois : fréquence et régularité (OPS-2)",
    "v_app_criticality":     "1 ligne par application : MTTR médian P1/P2, ratio médian durée/cible SLA, fiabilité n>=10 (SRE-2)",
    "v_runbook_coverage":    "1 ligne par catégorie d'incident du dernier trimestre : fréquence et runbooks existants (SRE-3)",
    "fact_incident":         "1 ligne par incident unique (dédoublonné). Utiliser app_id_clean et cmdb__app_name / cmdb__owner_team (la CMDB fait foi)",
    "fact_change":           "1 ligne par change",
    "fact_capacity":         "1 ligne par CI et par jour : cpu_pct, disk_pct (OPS-1)",
    "dim_ci":                "1 ligne par CI (serveur) : type, application, équipe propriétaire (OPS-3)",
    "dim_application":       "1 ligne par application : nom, criticité métier (1 = la plus critique)",
    "dim_team":              "1 ligne par équipe",
    "dim_priority":          "P1 à P4 et cible SLA en minutes",
    "dim_date":              "calendrier : jour de semaine (1 = lundi), week-end, mois, trimestre",
}

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|copy|call|"
    r"execute|vacuum|analyze|refresh|set|reset|lock|comment|pg_sleep|pg_read_file|dblink)\b",
    re.IGNORECASE)


def _load_env(path: Path) -> None:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env(ROOT / "agent" / ".env")
_load_env(ROOT / "docker" / ".env")   # AGENT_DB_PASSWORD


def _connect():
    import psycopg  # pip install "psycopg[binary]"
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5433")),
        dbname=os.environ.get("DB_NAME", "datalake"),
        user=os.environ.get("DB_USER", "agent_ro"),
        password=os.environ["AGENT_DB_PASSWORD"],
        connect_timeout=5,
    )


def check_sql(sql: str) -> str | None:
    """Renvoie un message d'erreur si la requête est refusée, None sinon."""
    s = sql.strip().rstrip(";").strip()
    if not s:
        return "requête vide"
    no_strings = re.sub(r"'(?:[^']|'')*'", "''", s)      # ignore le contenu des chaînes
    if ";" in no_strings:
        return "une seule instruction SQL est autorisée"
    if not re.match(r"^(select|with)\b", s, re.IGNORECASE):
        return "seules les requêtes SELECT (ou WITH … SELECT) sont autorisées"
    m = FORBIDDEN.search(no_strings)
    if m:
        return f"mot-clé interdit : {m.group(0).upper()}"
    return None


def _relations(plan) -> set[tuple[str, str]]:
    """Parcourt le plan JSON d'EXPLAIN et renvoie les (schéma, table) lus."""
    found = set()
    if isinstance(plan, dict):
        if "Relation Name" in plan:
            found.add((plan.get("Schema", "?"), plan["Relation Name"]))
        for v in plan.values():
            found |= _relations(v)
    elif isinstance(plan, list):
        for v in plan:
            found |= _relations(v)
    return found


def _jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, timedelta):
        return str(v)
    return v


def query_datalake(sql: str) -> dict:
    """Exécute la requête si elle passe les garde-fous. Ne lève jamais d'exception :
    renvoie {"sql", "columns", "rows", "row_count", "truncated", "error"}."""
    sql = sql.strip().rstrip(";").strip()
    out = {"sql": sql, "columns": [], "rows": [], "row_count": 0, "truncated": False, "error": None}
    refusal = check_sql(sql)
    if refusal:
        out["error"] = f"Requête refusée par le garde-fou : {refusal}"
        return out
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("explain (format json, verbose) " + sql)          # plan seulement, rien n'est exécuté
            read = _relations(cur.fetchone()[0])
            bad = sorted(f"{sch}.{t}" for sch, t in read
                         if sch != "public" or (t not in ALLOWED and t not in INTERNAL))
            if bad:
                out["error"] = f"Requête refusée par le garde-fou : lecture hors couche gold ({', '.join(bad)})"
                return out
            cur.execute(sql)
            rows = cur.fetchmany(MAX_ROWS + 1)
            out["columns"] = [d.name for d in cur.description]
            out["truncated"] = len(rows) > MAX_ROWS
            out["rows"] = [[_jsonable(v) for v in r] for r in rows[:MAX_ROWS]]
            out["row_count"] = len(out["rows"])
    except Exception as exc:  # erreur SQL renvoyée au modèle pour qu'il se corrige
        out["error"] = f"{type(exc).__name__}: {str(exc).strip()[:300]}"
    return out


def schema_description() -> str:
    """Décrit les objets autorisés (colonnes et types lus dans la base) pour le prompt."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""select table_name, column_name, data_type
                       from information_schema.columns
                       where table_schema = 'public' and table_name = any(%s)
                       order by table_name, ordinal_position""", (list(ALLOWED),))
        cols: dict[str, list[str]] = {}
        for t, c, typ in cur.fetchall():
            cols.setdefault(t, []).append(f"{c} {typ}")
    lines = []
    for name, purpose in ALLOWED.items():
        if name in cols:
            lines.append(f"- {name} — {purpose}\n    colonnes : {', '.join(cols[name])}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(schema_description()[:1500], "...\n")
    r = query_datalake("select app_name, change_incident_rate from v_change_risk_by_app "
                       "order by change_incident_rate desc limit 3")
    print(r["columns"], r["rows"], r["error"])
    print(query_datalake("delete from fact_incident")["error"])
    print(query_datalake("select * from pg_shadow")["error"])
