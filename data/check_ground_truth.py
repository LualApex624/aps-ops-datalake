"""
check_ground_truth.py — Vérifie que les données générées contiennent bien
les 4 patterns et les défauts annoncés dans ground_truth.json.

Usage (depuis la racine du repo) :
    python data/check_ground_truth.py
Code de sortie 0 si tout passe, 1 sinon.
"""
from pathlib import Path
import json
import sys

import pandas as pd

D = Path(__file__).parent
truth = json.loads((D / "ground_truth.json").read_text())
inc = pd.read_csv(D / "incidents.csv", parse_dates=["opened_at", "resolved_at"])
chg = pd.read_csv(D / "changes.csv", parse_dates=["planned_start", "actual_end"])
cmdb = pd.read_csv(D / "cmdb.csv")
cap = pd.read_csv(D / "capacity.csv", parse_dates=["date"])
prio = pd.read_csv(D / "priority.csv")

results = []


def check(name, ok, detail):
    results.append(ok)
    print(f"[{'OK ' if ok else 'KO '}] {name} — {detail}")


# Version « propre » minimale pour tester les patterns
clean = inc.drop_duplicates("incident_id")
clean = clean[clean.ci_id.isin(cmdb.ci_id)]

# --- Pattern 1 : taux de changes suivis d'un incident sur le même CI sous 48 h
m = chg.merge(clean[["ci_id", "opened_at"]], on="ci_id", how="left")
m["hit"] = (m.opened_at > m.planned_start) & (m.opened_at <= m.planned_start + pd.Timedelta(hours=48))
per_change = m.groupby("change_id").agg(app_id=("app_id", "first"), hit=("hit", "any"))
rate = per_change.groupby("app_id").hit.mean().sort_values(ascending=False)
expected = set(truth["patterns"]["P1_change_risk"]["apps"])
top3 = set(rate.index[:3])
others = rate.drop(list(expected)).median()
check("Pattern 1 (change risk)", top3 == expected and rate[list(expected)].min() > 2 * others,
      f"top 3 = {sorted(top3)} ; taux cibles = {rate[list(expected)].round(2).tolist()} ; médiane autres = {others:.2f}")

# --- Pattern 2 : incident du lundi ~07:30 sur le même CI
ci2 = truth["patterns"]["P2_monday"]["ci_id"]
mon = clean[(clean.ci_id == ci2) & (clean.category == "batch_failure")
            & (clean.opened_at.dt.dayofweek == 0) & (clean.opened_at.dt.hour == 7)]
n_mondays = pd.date_range(*truth["period"], freq="W-MON").size
check("Pattern 2 (lundi 07:xx)", len(mon) >= n_mondays - 1 and mon.short_description.nunique() == 1,
      f"{len(mon)} occurrences pour {n_mondays} lundis ; {mon.short_description.nunique()} message(s) distinct(s)")

# --- Pattern 3 : disque qui se remplit
ci3 = truth["patterns"]["P3_disk"]["ci_id"]
last = cap[cap.date == cap.date.max()].set_index("ci_id").disk_pct
others_max = cap[cap.ci_id != ci3].disk_pct.max()
check("Pattern 3 (disque)", last[ci3] > 85 and others_max < 85,
      f"{ci3} au dernier relevé = {last[ci3]} % ; max des autres CI sur la période = {others_max} %")

# --- Pattern 4 : MTTR des P1/P2 sur l'application critique (ratio durée / cible SLA)
q3 = clean[(clean.opened_at >= "2026-07-01") & clean.priority.isin(["P1", "P2"]) & clean.resolved_at.notna()]
q3 = q3[q3.resolved_at > q3.opened_at].merge(prio, on="priority")
q3 = q3.merge(cmdb[["app_id", "business_criticality"]].drop_duplicates(), on="app_id")
q3 = q3[q3.business_criticality == 1]
q3["ratio"] = (q3.resolved_at - q3.opened_at).dt.total_seconds() / 60 / q3.sla_target_minutes
MIN_N = 10  # une médiane sur moins de 10 incidents n'est pas exploitable
med = q3.groupby("app_id").ratio.agg(["median", "size"])
med = med[med["size"] >= MIN_N].sort_values("median", ascending=False)
app4 = truth["patterns"]["P4_mttr"]["app_id"]
ok4 = app4 in med.index and med.index[0] == app4 and med.loc[app4, "median"] > 1 and (med["median"] > 1).sum() == 1
check("Pattern 4 (MTTR)", ok4,
      f"{app4} : médiane durée/SLA = {med.loc[app4, 'median']:.2f} (n={int(med.loc[app4, 'size'])}) ; "
      f"suivant (n≥{MIN_N}) = {med.index[1]} à {med['median'].iloc[1]:.2f}" if app4 in med.index
      else f"{app4} a moins de {MIN_N} incidents P1/P2 au trimestre")

# --- Défauts de qualité : les comptages doivent être exacts
d = truth["defects"]
dups = inc.duplicated(keep="first").sum()
check("Doublons", dups == d["duplicates"], f"{dups} trouvés / {d['duplicates']} attendus")
miss = inc.drop_duplicates().priority.isna().sum()
check("Priorités manquantes", miss == d["missing_priority"], f"{miss} / {d['missing_priority']}")
u = inc.drop_duplicates()
inv = (u.resolved_at < u.opened_at).sum()
check("resolved_at < opened_at", inv == d["resolved_before_opened"], f"{inv} / {d['resolved_before_opened']}")
orph = (~u.ci_id.isin(cmdb.ci_id)).sum()
check("CI orphelins", orph == d["orphan_ci"], f"{orph} / {d['orphan_ci']}")
mm = u.merge(cmdb[["ci_id", "app_id"]], on="ci_id", suffixes=("", "_cmdb"))
mis = (mm.app_id != mm.app_id_cmdb).sum()
check("app_id incohérent avec la CMDB", mis == d["app_mismatch"], f"{mis} / {d['app_mismatch']}")

print(f"\n{sum(results)}/{len(results)} vérifications passées")
sys.exit(0 if all(results) else 1)
