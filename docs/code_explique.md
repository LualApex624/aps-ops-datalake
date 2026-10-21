# Le code expliqué

Pour chaque fichier : son rôle en une phrase, ses blocs clés, et les questions qu'on peut poser en entretien, avec une réponse courte.

Niveaux de maîtrise visés :
- **SQL des vues** : savoir le réécrire seul.
- **Python** : savoir expliquer chaque bloc et pourquoi il est là.
- **Docker, YAML, plomberie** : savoir ce que ça fait, et retrouver la syntaxe au besoin.

---

## `data/generate_data.py` — les données simulées

**Rôle** : produire 6 mois de données réalistes, avec 4 patterns et 5 défauts **connus à l'avance**.

**Blocs clés**
1. `SEED = 42` et `rng = np.random.default_rng(SEED)` : même graine, mêmes tirages, mêmes fichiers à l'octet près.
2. L'ordre de construction : **CMDB d'abord** (les dimensions), puis changes, incidents normaux, patterns, défauts. Un incident référence un CI qui doit déjà exister.
3. Les lois de probabilité : **Poisson** pour le nombre d'incidents par jour, **log-normale** pour les durées (toujours positives, queue longue à droite), **gamma** pour rendre certains CI plus « bruyants ».
4. Les fonctions `inject_*` ajoutent les patterns ; `inject_defects` abîme des lignes **distinctes**, hors lignes de pattern, pour que les comptages attendus soient exacts.

**Questions**
- *Pourquoi versionner le script plutôt que les CSV ?* La seed les régénère à l'identique, et c'est prouvé par comparaison d'empreintes. Le code est la source de vérité.
- *Pourquoi une log-normale pour les durées ?* La plupart des incidents se règlent vite, et quelques-uns traînent. C'est aussi pour ça qu'on utilise une **médiane** plutôt qu'une moyenne.

## `data/check_ground_truth.py` — le corrigé automatique

**Rôle** : vérifier que les données contiennent bien les patterns et les défauts annoncés (9 contrôles).

**Question** — *Pourquoi `MIN_N = 10` ?* Une médiane calculée sur moins de 10 incidents n'est pas exploitable : un seul cas extrême la fait basculer.

## Dataiku : la recette Python de normalisation

**Rôle** : rendre comparables des messages qui ne diffèrent que par des nombres ou un nom de serveur.

```python
t = text.lower()
t = re.sub(r"ci-\d{4}", "<ci>", t)   # nom du serveur → <ci>
t = re.sub(r"\d+", "<n>", t)         # tous les nombres → <n>
t = re.sub(r"\s+", " ", t).strip()   # espaces multiples
```

**Question** — *Pourquoi remplacer `ci-xxxx` AVANT les nombres ?* Sinon, `ci-0121` deviendrait `ci-<n>`, et on perdrait le jeton `<ci>`. L'ordre des remplacements compte. Résultat : 2 315 messages distincts → 26.

## `sql/views.sql` — les vues métier (à savoir réécrire)

### `v_change_risk` et `v_change_risk_by_app`

```sql
select c.change_id, c.app_id,
       count(i.incident_id)            as n_incidents_48h,
       (count(i.incident_id) > 0)::int as has_incident_48h
from fact_change c
left join fact_incident i
       on i.ci_id = c.ci_id
      and i.opened_at >  c.planned_start
      and i.opened_at <= c.planned_start + interval '48 hours'
group by c.change_id, c.app_id;
```

**Questions**
- *Pourquoi `left join` ?* Pour garder les changes **sans** incident : sans eux, le taux serait de 100 %.
- *Pourquoi `count(i.incident_id)` et pas `count(*)` ?* Un left join sans correspondance produit **une ligne remplie de NULL**. `count(*)` la compterait (1), alors que `count(colonne)` ignore les NULL (0).
- *Pourquoi le même CI et pas la même application ?* Une application a plusieurs CI, donc un incident tombe presque toujours dans la fenêtre : le taux de base dépasserait 60 % et le signal disparaîtrait. Par CI, il est d'environ 15 %.
- *Pourquoi `>` et pas `>=` sur `planned_start` ?* Un incident ouvert avant ou au moment exact du change ne peut pas en être la conséquence.
- Taux par application : `avg(has_incident_48h)`. Une moyenne de 0 et de 1, c'est une proportion.

### `v_recurring_incidents`

**Idée** : regrouper par CI et message normalisé, puis mesurer la **régularité** (`modal_dow_share` = part des occurrences tombant le jour le plus fréquent). Les CTE `by_dow` et `top_dow` trouvent ce jour avec `distinct on (...) order by n desc`.

**Question** — *Pourquoi ne pas trier simplement par fréquence ?* Un CI bruyant peut avoir 19 alertes réparties au hasard. Une récurrence se reconnaît à sa régularité : environ 14 % le même jour si c'est le hasard, 100 % pour CI-0121.

### `v_app_criticality`

```sql
percentile_cont(0.5) within group (order by resolution_minutes / sla_target_minutes)
    filter (where priority in ('P1','P2') and resolution_minutes >= 0)
```

**Questions**
- *Pourquoi un ratio au SLA plutôt que des minutes ?* 600 minutes, c'est grave pour un P1 (cible 240) et très bien pour un P3 (cible 2 880). Le ratio rend les priorités comparables.
- *Pourquoi calculer la médiane dans la vue et pas dans Superset ?* Une médiane n'est **pas ré-agrégeable** : la médiane des médianes n'est pas la médiane globale. On la calcule une fois, au bon grain.
- *Pourquoi `resolution_minutes >= 0` ?* Pour exclure les 25 durées négatives (défaut marqué `dq_negative_duration`).

### `v_runbook_coverage`

**Question** — *Pourquoi « dernier trimestre = celui de la date maximale » et pas `now()` ?* Les données s'arrêtent au 30 septembre. Avec `now()`, le trimestre courant serait vide. On ancre la période sur les données.

## `sql/roles.sql` — le rôle en lecture seule

**Rôle** : donner à Superset et à l'agent un accès qui ne peut rien modifier.

**Les 3 barrières** : `GRANT SELECT` seulement (la vraie protection), `default_transaction_read_only` (contournable, démontré au test), `statement_timeout = 15s`.
`alter default privileges` : les tables recréées plus tard par Dataiku héritent automatiquement du droit de lecture.

**Question** — *Pourquoi ne pas se contenter du mode lecture seule ?* Une session peut le désactiver (`SET default_transaction_read_only = off`). Seuls les droits ne se contournent pas : c'est la défense en profondeur.

## `superset/Dockerfile` et `docker/compose.yml`

- L'image officielle de Superset n'embarque **aucun pilote** : le Dockerfile ajoute `psycopg2-binary`, puis repasse en utilisateur non-root.
- Superset joint la base par `datalake-db:5432`, le nom du service sur le réseau Docker interne. `localhost` désignerait le conteneur lui-même, et le port 5433 n'existe que côté Mac.
- Les secrets sont dans `docker/.env`, jamais commité ; `.env.example` en montre le format.

## `agent/llm_client.py` — la gateway LLM

**Rôle** : point d'accès **unique** au modèle. Changer de fournisseur (Ollama, Mistral, Claude) revient à changer une variable.

**Blocs clés** : `complete()` et `embed()`, chacune dans un `try/finally` qui **journalise chaque appel**, même en erreur : date, modèle, latence, tokens, statut et **empreinte SHA-256** du prompt, mais **pas le contenu**.

**Questions**
- *Pourquoi ne pas journaliser les prompts ?* Ils contiennent des données d'incidents. Un journal technique ne doit pas devenir une copie non maîtrisée de données sensibles ; l'empreinte suffit à rapprocher deux appels.
- *Pourquoi `num_ctx = 8192` pour Ollama ?* Par défaut, le contexte est petit, et le prompt (règles et schéma) serait **tronqué sans avertissement**.

## `agent/tools.py` — l'outil SQL

**Rôle** : exécuter le SQL proposé par le modèle, seulement s'il passe les garde-fous.

**Blocs clés**
1. `check_sql` : une instruction, `SELECT`/`WITH` uniquement, mots-clés d'écriture interdits (en ignorant le contenu des chaînes).
2. `EXPLAIN (format json, verbose)` : le moteur révèle les tables **réellement lues**, sans exécuter la requête ; toute table hors liste blanche est refusée.
3. `fetchmany(51)` : 50 lignes au maximum, et un drapeau `truncated`.
4. `schema_description()` : le schéma est lu dans `information_schema`, jamais recopié à la main.

**Questions**
- *Pourquoi EXPLAIN plutôt qu'une expression régulière sur FROM/JOIN ?* Le texte SQL se contourne facilement (jointure par virgule, sous-requête, alias), alors que le plan du moteur dit la vérité. Les vues apparaissent avec leurs tables sous-jacentes, d'où la liste `INTERNAL`.
- *Que se passe-t-il si le modèle écrit `DROP TABLE` ?* Il est refusé par `check_sql`. Et même sans ce contrôle, `agent_ro` n'a aucun droit d'écriture.

## `agent/rag.py` — la recherche dans les runbooks

**Rôle** : retrouver la bonne procédure à partir d'une description en langage naturel.

**Blocs clés** : indexation (chaque document → un vecteur `bge-m3`, stocké en JSON) ; recherche (question → vecteur, **similarité cosinus** `m @ q / (‖m‖·‖q‖)`, top 3 au-dessus de `MIN_SCORE`).

**Questions**
- *Pourquoi pas ChromaDB ?* 16 documents tiennent en mémoire, et numpy suffit. En production, on passerait à `pgvector`, dans Postgres.
- *Le seuil suffit-il ?* Non : un bon et un mauvais runbook atteignaient tous deux environ 0,56. D'où la vérification par le modèle (catégorie, titre) et la piste d'une recherche hybride.

## `agent/agent.py` — la boucle de l'agent

**Rôle** : faire dialoguer le modèle et les outils jusqu'à une réponse.

**Boucle** (5 étapes au maximum) : le modèle renvoie un JSON (`query_datalake`, `search_runbooks`, `answer`, `refuse`) ; `parse_action` l'extrait ; le code exécute l'outil et renvoie le résultat **sous forme `{colonne: valeur}`** ; on recommence.

**Questions**
- *Pourquoi des dictionnaires plutôt que colonnes + lignes ?* Avec deux listes séparées, le modèle 7B alignait mal les positions : il avait répondu « 19 h » au lieu de 7 h. Chaque valeur collée à son nom a corrigé l'erreur.
- *Pourquoi le modèle ne se connecte-t-il pas directement à la base ?* Pour que **chaque action passe par le code**, qui la vérifie, la journalise et l'affiche.

## `agent/eval/` — l'évaluation

**Rôle** : mesurer l'agent sur 12 questions dont les réponses attendues sont fixées à l'avance.

**Questions**
- *10/12, c'est fiable ?* Sur 12 questions, l'intervalle de confiance à 95 % va d'environ 55 % à 95 %. Pour conclure, il faudrait une centaine de questions.
- *Pourquoi relire à la main ?* Le contrôle par mots-clés a validé Q10, qui recommandait pourtant un runbook hors sujet.
