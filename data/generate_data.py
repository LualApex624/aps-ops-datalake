"""
generate_data.py — 6 mois de données de production IT simulées (avril → septembre 2026).

Usage (depuis la racine du repo) :
    python data/generate_data.py

Produit dans data/ :
    cmdb.csv, priority.csv, incidents.csv, changes.csv, capacity.csv,
    ground_truth.json, ground_truth.md

Reproductible : même SEED → mêmes fichiers, octet pour octet.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------
SEED = 42
START = pd.Timestamp("2026-04-01")
END = pd.Timestamp("2026-09-30 23:59:59")
INCIDENTS_PER_WEEKDAY = 25        # moyenne de la loi de Poisson
INCIDENTS_PER_WEEKEND_DAY = 11
CHANGES_PER_WEEKDAY = 8.5
CHANGES_PER_WEEKEND_DAY = 1.0
N_CIS = 250
OUT = Path(__file__).parent
TS_FMT = "%Y-%m-%d %H:%M:%S"

rng = np.random.default_rng(SEED)
DAYS = pd.date_range(START.normalize(), END.normalize(), freq="D")

# ---------------------------------------------------------------------------
# Référentiels
# ---------------------------------------------------------------------------
# (nom, criticité métier 1–4, équipe propriétaire)
APPS = [
    ("Payments Gateway", 1, "run-payments"), ("SEPA Hub", 1, "run-payments"),
    ("SWIFT Connector", 1, "run-payments"), ("Card Authorization", 1, "run-payments"),
    ("Core Banking", 1, "run-lending"), ("Loan Origination", 2, "run-lending"),
    ("Mortgage Engine", 2, "run-lending"), ("Credit Scoring", 2, "run-lending"),
    ("Collateral Mgmt", 3, "run-lending"), ("Trade Capture", 1, "run-markets"),
    ("Market Data Feed", 2, "run-markets"), ("Risk Engine", 1, "run-markets"),
    ("Pricing Library", 2, "run-markets"), ("Settlement Batch", 1, "run-markets"),
    ("Reconciliation", 2, "run-markets"), ("General Ledger", 2, "run-lending"),
    ("Regulatory Reporting", 2, "run-markets"), ("AML Screening", 2, "run-payments"),
    ("KYC Portal", 3, "run-payments"), ("Fraud Detection", 2, "run-payments"),
    ("Customer Portal", 2, "run-payments"), ("Mobile Banking API", 2, "run-payments"),
    ("Online Banking", 2, "run-payments"), ("CRM", 3, "run-lending"),
    ("Document Mgmt", 3, "infra-systems"), ("Data Warehouse", 3, "infra-systems"),
    ("HR Portal", 4, "infra-systems"), ("Treasury Mgmt", 2, "run-markets"),
    ("FX Platform", 2, "run-markets"), ("Securities Custody", 3, "run-markets"),
    ("Fund Accounting", 3, "run-markets"), ("Liquidity Monitor", 3, "run-markets"),
    ("Identity Provider", 2, "infra-systems"), ("API Gateway", 2, "infra-network"),
    ("Notification Service", 3, "infra-systems"), ("Monitoring Platform", 3, "infra-systems"),
    ("Backup Service", 3, "infra-systems"), ("Email Gateway", 4, "infra-network"),
    ("Contract Archive", 4, "infra-systems"), ("Intranet", 4, "infra-systems"),
]
assert len(APPS) == 40

PRIORITY = pd.DataFrame({
    "priority": ["P1", "P2", "P3", "P4"],
    "label": ["Critique", "Haute", "Moyenne", "Basse"],
    "sla_target_minutes": [240, 480, 2880, 7200],  # hypothèses documentées
})
PRIO_PROBS = [0.03, 0.12, 0.45, 0.40]
PRIO_PROBS_CRITICAL = [0.08, 0.27, 0.40, 0.25]  # applications de criticité 1
MEDIAN_RESOLUTION_MIN = {"P1": 90, "P2": 240, "P3": 1200, "P4": 3000}
RESOLUTION_SIGMA = 0.9  # log-normale : queue longue à droite

CATEGORIES_BY_CI_TYPE = {
    "app_server": {"app_crash": .30, "memory_leak": .15, "deployment_error": .10,
                   "latency": .20, "auth_failure": .10, "cert_expiry": .05, "disk_full": .10},
    "web_server": {"latency": .35, "cert_expiry": .15, "app_crash": .20,
                   "auth_failure": .20, "disk_full": .10},
    "db_server": {"db_lock": .35, "disk_full": .25, "latency": .20, "backup_failure": .20},
    "batch_server": {"batch_failure": .50, "job_scheduler": .30, "disk_full": .20},
    "storage": {"disk_full": .40, "backup_failure": .40, "latency": .20},
    "network_device": {"network_timeout": .70, "latency": .30},
}
CI_TYPE_ORDER = list(CATEGORIES_BY_CI_TYPE)  # ordre fixe → reproductibilité

DESCRIPTIONS = {
    "app_crash": ["Application process crashed on {ci}", "Service unavailable: JVM terminated on {ci}",
                  "HTTP 503 returned by {ci}"],
    "memory_leak": ["Heap usage at {n}% and growing on {ci}", "OutOfMemoryError on {ci}"],
    "deployment_error": ["Errors after deployment on {ci}", "Release failed health check on {ci}"],
    "latency": ["Response time {n}0 ms above threshold on {ci}", "Slow transactions reported on {ci}"],
    "auth_failure": ["LDAP bind failure on {ci}", "Users unable to log in via {ci}"],
    "cert_expiry": ["TLS certificate expires in {n} days on {ci}", "SSL handshake errors on {ci}"],
    "disk_full": ["Filesystem /data at {n}% on {ci}", "No space left on device on {ci}"],
    "db_lock": ["Blocking sessions detected on {ci}", "Deadlock ORA-00060 on {ci}"],
    "backup_failure": ["Nightly backup failed on {ci}", "Backup job exceeded window on {ci}"],
    "batch_failure": ["Batch job {n} ended in error on {ci}", "Batch chain stopped on {ci}"],
    "job_scheduler": ["Scheduler agent down on {ci}", "Job {n} not triggered on {ci}"],
    "network_timeout": ["Packet loss {n}% on {ci}", "Connection timeouts through {ci}"],
}
HOUR_WEIGHTS = np.array([1, 1, 1, 1, 1, 2, 3, 6, 9, 10, 10, 9,
                         8, 9, 10, 10, 9, 7, 5, 3, 2, 2, 1, 1], dtype=float)
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

# Applications et CI choisis pour la vérité terrain
P1_CHANGE_RISK_APPS = ["Payments Gateway", "Trade Capture", "Customer Portal"]
P2_MONDAY_APP = "Settlement Batch"
P3_DISK_APP = "General Ledger"
P4_MTTR_APP = "Core Banking"


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def describe(categories: np.ndarray, ci_ids: np.ndarray) -> list[str]:
    """Texte libre de l'incident, avec des valeurs variables (à normaliser au Lot 3)."""
    out = []
    for cat, ci in zip(categories, ci_ids):
        template = DESCRIPTIONS[cat][rng.integers(len(DESCRIPTIONS[cat]))]
        out.append(template.format(ci=ci, n=int(rng.integers(10, 99))))
    return out


def resolution_minutes(priorities: np.ndarray) -> np.ndarray:
    medians = np.array([MEDIAN_RESOLUTION_MIN[p] for p in priorities], dtype=float)
    return medians * np.exp(rng.normal(0, RESOLUTION_SIGMA, len(priorities)))


def make_incidents(opened, ci_ids, categories, priorities, minutes, cmdb, pattern=""):
    """Assemble un DataFrame d'incidents ; app_id et team viennent de la CMDB."""
    ref = cmdb.set_index("ci_id").loc[ci_ids]
    df = pd.DataFrame({
        "opened_at": pd.to_datetime(opened),
        "ci_id": ci_ids,
        "app_id": ref["app_id"].to_numpy(),
        "team": ref["owner_team"].to_numpy(),
        "priority": priorities,
        "category": categories,
        "short_description": describe(np.asarray(categories), np.asarray(ci_ids)),
        "_pattern": pattern,
    })
    df["resolved_at"] = df["opened_at"] + pd.to_timedelta(np.round(minutes), unit="m")
    return df


# ---------------------------------------------------------------------------
# 1. CMDB
# ---------------------------------------------------------------------------
def gen_cmdb() -> tuple[pd.DataFrame, pd.DataFrame]:
    apps = pd.DataFrame(APPS, columns=["app_name", "business_criticality", "app_team"])
    apps.insert(0, "app_id", [f"APP-{i:02d}" for i in range(1, len(apps) + 1)])

    rows = []
    for _, a in apps.iterrows():  # chaque application a au moins 3 CI
        for t in ["app_server", "web_server", "db_server"]:
            rows.append((a.app_id, t))
    rows.append((apps.loc[apps.app_name == P2_MONDAY_APP, "app_id"].item(), "batch_server"))
    core = apps.loc[apps.app_name == P4_MTTR_APP, "app_id"].item()  # un core banking est un gros périmètre
    rows += [(core, t) for t in ["app_server"] * 4 + ["db_server"] * 2 + ["web_server"] * 2]
    extra_types = ["app_server", "web_server", "db_server", "batch_server", "storage", "network_device"]
    for _ in range(N_CIS - len(rows)):
        rows.append((apps.app_id.iloc[rng.integers(len(apps))],
                     extra_types[rng.choice(6, p=[.25, .15, .15, .1, .15, .2])]))

    cmdb = pd.DataFrame(rows, columns=["app_id", "ci_type"])
    cmdb = cmdb.merge(apps, on="app_id", how="left")
    team_by_type = {"db_server": "dba", "storage": "infra-systems", "network_device": "infra-network"}
    cmdb["owner_team"] = [team_by_type.get(t, at) for t, at in zip(cmdb.ci_type, cmdb.app_team)]
    cmdb.insert(0, "ci_id", [f"CI-{i:04d}" for i in range(1, len(cmdb) + 1)])
    cmdb = cmdb[["ci_id", "ci_type", "app_id", "app_name", "business_criticality", "owner_team"]]
    return cmdb, apps


def app_id(apps, name):
    return apps.loc[apps.app_name == name, "app_id"].item()


def first_ci(cmdb, app, ci_type):
    return cmdb[(cmdb.app_id == app) & (cmdb.ci_type == ci_type)].ci_id.iloc[0]


# ---------------------------------------------------------------------------
# 2. Changes
# ---------------------------------------------------------------------------
def gen_changes(cmdb) -> pd.DataFrame:
    lam = np.where(DAYS.dayofweek < 5, CHANGES_PER_WEEKDAY, CHANGES_PER_WEEKEND_DAY)
    day_idx = np.repeat(np.arange(len(DAYS)), rng.poisson(lam))
    n = len(day_idx)
    hours = rng.choice([10, 14, 18, 19, 20, 21, 22], size=n, p=[.08, .07, .2, .25, .2, .15, .05])
    start = DAYS[day_idx] + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(rng.integers(0, 60, n), unit="m")
    eligible = cmdb[cmdb.ci_type.isin(["app_server", "web_server", "db_server", "batch_server"])]
    ci = eligible.ci_id.to_numpy()[rng.integers(len(eligible), size=n)]
    duration = 60 * np.exp(rng.normal(0, 0.6, n))
    changes = pd.DataFrame({
        "planned_start": start,
        "actual_end": start + pd.to_timedelta(np.round(duration), unit="m"),
        "ci_id": ci,
        "app_id": cmdb.set_index("ci_id").loc[ci, "app_id"].to_numpy(),
        "type": rng.choice(["standard", "normal", "emergency"], size=n, p=[.6, .35, .05]),
        "result": rng.choice(["success", "failed", "rolled_back"], size=n, p=[.92, .05, .03]),
    }).sort_values("planned_start", kind="stable").reset_index(drop=True)
    changes.insert(0, "change_id", [f"CHG-{i:05d}" for i in range(1, len(changes) + 1)])
    return changes


# ---------------------------------------------------------------------------
# 3. Incidents « normaux »
# ---------------------------------------------------------------------------
def gen_baseline_incidents(cmdb, apps) -> pd.DataFrame:
    lam = np.where(DAYS.dayofweek < 5, INCIDENTS_PER_WEEKDAY, INCIDENTS_PER_WEEKEND_DAY)
    day_idx = np.repeat(np.arange(len(DAYS)), rng.poisson(lam))
    n = len(day_idx)
    opened = (DAYS[day_idx]
              + pd.to_timedelta(rng.choice(24, size=n, p=HOUR_WEIGHTS), unit="h")
              + pd.to_timedelta(rng.integers(0, 3600, n), unit="s"))

    ci_weights = rng.gamma(2.0, 1.0, len(cmdb))  # certains CI sont plus « bruyants »
    ci_idx = rng.choice(len(cmdb), size=n, p=ci_weights / ci_weights.sum())
    ci_ids = cmdb.ci_id.to_numpy()[ci_idx]
    ci_types = cmdb.ci_type.to_numpy()[ci_idx]

    categories = np.empty(n, dtype=object)
    for t in CI_TYPE_ORDER:
        mask = ci_types == t
        cats = list(CATEGORIES_BY_CI_TYPE[t])
        probs = list(CATEGORIES_BY_CI_TYPE[t].values())
        categories[mask] = rng.choice(cats, size=mask.sum(), p=probs)

    # La priorité dépend de la criticité métier : une panne sur une appli critique pèse plus
    criticality = cmdb.business_criticality.to_numpy()[ci_idx]
    priorities = np.where(
        criticality == 1,
        rng.choice(["P1", "P2", "P3", "P4"], size=n, p=PRIO_PROBS_CRITICAL),
        rng.choice(["P1", "P2", "P3", "P4"], size=n, p=PRIO_PROBS),
    )
    minutes = resolution_minutes(priorities)

    # Pattern 4 : application critique au MTTR anormalement élevé sur P1/P2
    core = app_id(apps, P4_MTTR_APP)
    slow = (cmdb.app_id.to_numpy()[ci_idx] == core) & np.isin(priorities, ["P1", "P2"])
    minutes[slow] *= 4.5

    df = make_incidents(opened, ci_ids, categories, priorities, minutes, cmdb)
    df.loc[slow, "_pattern"] = "P4_mttr"
    return df


# ---------------------------------------------------------------------------
# 4. Patterns de la vérité terrain
# ---------------------------------------------------------------------------
def inject_change_risk(changes, cmdb, apps) -> pd.DataFrame:
    """Pattern 1 : sur 3 applications, 60 % des changes provoquent un incident
    sur le même CI entre 2 h et 30 h après le début du change."""
    targets = [app_id(apps, a) for a in P1_CHANGE_RISK_APPS]
    ch = changes[changes.app_id.isin(targets)]
    ch = ch[rng.random(len(ch)) < 0.60]
    n = len(ch)
    opened = ch.planned_start.to_numpy() + pd.to_timedelta(rng.uniform(2, 30, n), unit="h").to_numpy()
    categories = rng.choice(["deployment_error", "app_crash"], size=n, p=[.6, .4])
    priorities = rng.choice(["P2", "P3"], size=n, p=[.4, .6])
    return make_incidents(opened, ch.ci_id.to_numpy(), categories, priorities,
                          resolution_minutes(priorities), cmdb, pattern="P1_change_risk")


def inject_monday_batch(cmdb, apps) -> pd.DataFrame:
    """Pattern 2 : le même incident, chaque lundi vers 7 h 30, sur le même CI.

    Spécification :
      - CI : le batch_server de l'application P2_MONDAY_APP (utilise first_ci)
      - un incident par lundi de la période (DAYS), à 07:30 ± quelques minutes
      - category = "batch_failure", priority = "P3"
      - short_description identique chaque semaine (même message d'erreur)
      - durée de résolution : médiane ~ 50 min
      - pattern = "P2_monday"
    Retourne un DataFrame construit avec make_incidents().
    """
    # 1. CHOISIR : le serveur batch de l'application Settlement Batch
    ci = first_ci(cmdb, app_id(apps, P2_MONDAY_APP), "batch_server")

    # 2. CALCULER : tous les lundis de la période, à 7h30 ± quelques minutes
    mondays = DAYS[DAYS.dayofweek == 0]
    n = len(mondays)
    opened = mondays + pd.Timedelta(hours=7, minutes=30) + pd.to_timedelta(rng.normal(0, 6, n), unit="m")

    # 3. TIRER : même catégorie, même priorité, durée ~50 min
    categories = np.array(["batch_failure"] * n)
    priorities = np.array(["P3"] * n)
    minutes = 50 * np.exp(rng.normal(0, 0.3, n))

    # 4. ASSEMBLER
    df = make_incidents(opened, np.array([ci] * n), categories, priorities, minutes, cmdb,
                        pattern="P2_monday")
    df["short_description"] = "Settlement batch SETL_J1 failed: ORA-00060 deadlock detected"
    return df


def gen_capacity(cmdb, apps) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Relevé quotidien par CI. Pattern 3 : un serveur DB dont le disque se remplit."""
    cis = cmdb[cmdb.ci_type != "network_device"].reset_index(drop=True)
    n_ci, n_days = len(cis), len(DAYS)
    t = np.arange(n_days)
    weekday = (DAYS.dayofweek < 5).astype(float)

    disk = (rng.uniform(30, 68, (n_ci, 1)) + rng.uniform(-0.005, 0.02, (n_ci, 1)) * t
            + rng.normal(0, 0.6, (n_ci, n_days)))
    cpu = rng.uniform(10, 45, (n_ci, 1)) + 8 * weekday + rng.normal(0, 4, (n_ci, n_days))

    target = first_ci(cmdb, app_id(apps, P3_DISK_APP), "db_server")
    row = cis.index[cis.ci_id == target][0]
    disk[row] = 58 + (87.6 - 58) * t / (n_days - 1) + rng.normal(0, 0.3, n_days)

    capacity = pd.DataFrame({
        "date": np.tile(DAYS.strftime("%Y-%m-%d"), n_ci),
        "ci_id": np.repeat(cis.ci_id.to_numpy(), n_days),
        "cpu_pct": np.clip(cpu, 1, 99).ravel().round(1),
        "disk_pct": np.clip(disk, 5, 99).ravel().round(1),
    }).sort_values(["date", "ci_id"], kind="stable").reset_index(drop=True)

    # Quelques alertes disque en septembre sur ce serveur
    sept = DAYS[DAYS >= "2026-09-10"]
    days = sept[rng.choice(len(sept), size=3, replace=False)].sort_values()
    opened = days + pd.Timedelta(hours=9) + pd.to_timedelta(rng.integers(0, 480, 3), unit="m")
    alerts = make_incidents(opened, np.array([target] * 3), np.array(["disk_full"] * 3),
                            np.array(["P3"] * 3), resolution_minutes(np.array(["P3"] * 3)),
                            cmdb, pattern="P3_disk")
    return capacity, alerts


# ---------------------------------------------------------------------------
# 5. Défauts de qualité volontaires
# ---------------------------------------------------------------------------
DEFECTS = {"missing_priority": 80, "resolved_before_opened": 25,
           "orphan_ci": 40, "app_mismatch": 50, "duplicates": 60}


def inject_defects(inc, cmdb, apps) -> pd.DataFrame:
    """Chaque défaut touche des lignes distinctes, hors lignes de pattern,
    pour que les comptages attendus soient exacts."""
    clean = inc.index[(inc._pattern == "") & inc.resolved_at.notna()].to_numpy()
    picked = rng.choice(clean, size=sum(DEFECTS.values()), replace=False)
    groups, start = {}, 0
    for name, k in DEFECTS.items():
        groups[name] = np.sort(picked[start:start + k])
        start += k

    inc.loc[groups["missing_priority"], "priority"] = np.nan
    g = groups["resolved_before_opened"]
    inc.loc[g, "resolved_at"] = inc.loc[g, "opened_at"] - pd.to_timedelta(rng.integers(10, 600, len(g)), unit="m")
    g = groups["orphan_ci"]
    inc.loc[g, "ci_id"] = [f"CI-9{int(x):03d}" for x in rng.integers(0, 1000, len(g))]
    g = groups["app_mismatch"]
    wrong = []
    for current in inc.loc[g, "app_id"]:
        choices = apps.app_id[apps.app_id != current].to_numpy()
        wrong.append(choices[rng.integers(len(choices))])
    inc.loc[g, "app_id"] = wrong

    dups = inc.loc[groups["duplicates"]]
    inc = pd.concat([inc, dups]).sort_values(["opened_at", "incident_id"], kind="stable")
    return inc.reset_index(drop=True), {k: v.tolist() for k, v in groups.items()}


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------
def main():
    cmdb, apps = gen_cmdb()
    changes = gen_changes(cmdb)
    baseline = gen_baseline_incidents(cmdb, apps)
    p1 = inject_change_risk(changes, cmdb, apps)
    p2 = inject_monday_batch(cmdb, apps)
    capacity, p3 = gen_capacity(cmdb, apps)

    inc = pd.concat([baseline, p1, p2, p3], ignore_index=True)
    inc = inc.sort_values("opened_at", kind="stable").reset_index(drop=True)
    inc.insert(0, "incident_id", [f"INC-{i:06d}" for i in range(1, len(inc) + 1)])
    inc["status"] = np.where(inc.resolved_at > END, "In Progress", "Resolved")
    inc.loc[inc.resolved_at > END, "resolved_at"] = pd.NaT

    patterns = inc[inc._pattern != ""]
    inc, defect_rows = inject_defects(inc, cmdb, apps)

    cols = ["incident_id", "opened_at", "resolved_at", "priority", "ci_id", "app_id",
            "team", "category", "short_description", "status"]
    inc[cols].to_csv(OUT / "incidents.csv", index=False, date_format=TS_FMT)
    changes.to_csv(OUT / "changes.csv", index=False, date_format=TS_FMT)
    cmdb.to_csv(OUT / "cmdb.csv", index=False)
    PRIORITY.to_csv(OUT / "priority.csv", index=False)
    capacity.to_csv(OUT / "capacity.csv", index=False, float_format="%.1f")

    truth = {
        "seed": SEED,
        "period": [str(START.date()), str(END.date())],
        "rows": {"incidents": len(inc), "changes": len(changes), "cmdb": len(cmdb),
                 "capacity": len(capacity)},
        "patterns": {
            "P1_change_risk": {"apps": [app_id(apps, a) for a in P1_CHANGE_RISK_APPS],
                               "app_names": P1_CHANGE_RISK_APPS,
                               "injected_incidents": int((patterns._pattern == "P1_change_risk").sum())},
            "P2_monday": {"ci_id": first_ci(cmdb, app_id(apps, P2_MONDAY_APP), "batch_server"),
                          "app_name": P2_MONDAY_APP,
                          "injected_incidents": int((patterns._pattern == "P2_monday").sum())},
            "P3_disk": {"ci_id": first_ci(cmdb, app_id(apps, P3_DISK_APP), "db_server"),
                        "app_name": P3_DISK_APP, "last_disk_pct_target": 87.6},
            "P4_mttr": {"app_id": app_id(apps, P4_MTTR_APP), "app_name": P4_MTTR_APP,
                        "p1_p2_resolution_multiplier": 4.5},
        },
        "defects": {k: len(v) for k, v in defect_rows.items()},
    }
    (OUT / "ground_truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False) + "\n")
    write_ground_truth_md(truth)
    print(json.dumps(truth["rows"]), "| défauts :", json.dumps(truth["defects"]))


def write_ground_truth_md(t):
    p = t["patterns"]
    d = t["defects"]
    md = f"""# Vérité terrain (générée automatiquement — ne pas éditer)

Seed : `{t['seed']}` · période : {t['period'][0]} → {t['period'][1]}

Volumes : {t['rows']['incidents']} incidents (doublons inclus), {t['rows']['changes']} changes,
{t['rows']['cmdb']} CI, {t['rows']['capacity']} relevés de capacité.

## Patterns injectés

| # | Pattern | Où | Détecté par |
|---|---|---|---|
| 1 | 60 % des changes suivis d'un incident sur le même CI sous 2–30 h ({p['P1_change_risk']['injected_incidents']} incidents) | {', '.join(f"{n} ({i})" for n, i in zip(p['P1_change_risk']['app_names'], p['P1_change_risk']['apps']))} | `v_change_risk`, dashboard « Change risk », SRE-1 |
| 2 | Même incident chaque lundi ~07:30 ({p['P2_monday']['injected_incidents']} occurrences), catégorie `batch_failure` | {p['P2_monday']['app_name']}, `{p['P2_monday']['ci_id']}` | `v_recurring_incidents`, OPS-2 |
| 3 | Disque qui se remplit linéairement de 58 % à ~{p['P3_disk']['last_disk_pct_target']} % | {p['P3_disk']['app_name']}, `{p['P3_disk']['ci_id']}` | OPS-1, panneau capacité |
| 4 | Durée de résolution P1/P2 × {p['P4_mttr']['p1_p2_resolution_multiplier']} | {p['P4_mttr']['app_name']} ({p['P4_mttr']['app_id']}) | `v_app_criticality`, SRE-2 |

## Défauts de qualité injectés (lignes distinctes, hors lignes de pattern)

| Défaut | Lignes |
|---|---|
| Priorité manquante | {d['missing_priority']} |
| `resolved_at` antérieur à `opened_at` | {d['resolved_before_opened']} |
| CI absent de la CMDB (`CI-9xxx`) | {d['orphan_ci']} |
| `app_id` incohérent avec la CMDB | {d['app_mismatch']} |
| Incidents dupliqués (même `incident_id`) | {d['duplicates']} |

## Hypothèses

- Cibles SLA (`priority.csv`) : P1 4 h, P2 8 h, P3 2 j, P4 5 j — choisies, non issues d'un référentiel réel.
- Priorités : P1 3 %, P2 12 %, P3 45 %, P4 40 % ; sur les applications de criticité 1 : 8 / 27 / 40 / 25 %.
- Durées de résolution log-normales (médianes P1 90 min, P2 4 h, P3 20 h, P4 50 h).
- Arrivées d'incidents : loi de Poisson ({INCIDENTS_PER_WEEKDAY}/jour ouvré, {INCIDENTS_PER_WEEKEND_DAY}/jour de week-end).
"""
    (OUT / "ground_truth.md").write_text(md)


if __name__ == "__main__":
    main()
