"""
build_runbook_index.py — indexe les runbooks (en-têtes YAML) dans Postgres.

Usage (depuis la racine du repo) :
    python data/build_runbook_index.py | docker exec -i aps-datalake-db psql -U aps -d datalake

Ne garde que les fichiers `type: runbook` (les post-mortems sont exclus).
À relancer avant sql/views.sql : la table est recréée (drop … cascade).
"""
from pathlib import Path

RUNBOOKS = Path(__file__).parent / "runbooks"


def front_matter(path: Path) -> dict:
    """Lit l'en-tête YAML simple (clé: valeur) entre les deux lignes '---'."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def sql_str(value: str) -> str:
    """Littéral SQL avec échappement des apostrophes."""
    return "'" + value.replace("'", "''") + "'"


rows = []
for path in sorted(RUNBOOKS.glob("*.md")):
    meta = front_matter(path)
    if meta.get("type") != "runbook":
        continue
    rows.append("(" + ", ".join(sql_str(v) for v in (
        meta["id"], meta["category"], meta["title"], meta.get("owner_team", ""), path.name)) + ")")

print("drop table if exists runbook_index cascade;")
print("create table runbook_index (runbook_id text primary key, category text not null,"
      " title text, owner_team text, file_name text);")
print("insert into runbook_index values\n  " + ",\n  ".join(rows) + ";")
