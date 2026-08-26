# Phase-2 hurdle dataset schema

`data/phase2_hurdle_v1.csv` is one row per isolated single-company attempt. CSV is used rather
than Parquet because 1,000 rows are small, the result is directly inspectable/versionable, and no
column needs nested types. `docs/phase2_hurdle_campaign_v1.json` is the raw run record.

## Identifiers and split

- `attempt_id`, `line_index`: stable join keys into the raw JSON/signs.
- `seed`: world identifier. Split train/validation/test **by seed**, never by row.
- `stagger_slot`: always zero in this dataset; recorded as a reproducibility check, not a model
  input.

## Legitimate pre-construction inputs

`pair_rank`, `engine_rank`, `num_trains`, `wagons_per_train`, `town_a_population`,
`town_b_population`, and `distance_straight` are knowable after choosing the candidate pair but
before pathfinding/construction. `town_a`/`town_b` are raw map-local identifiers for traceability,
not recommended generalization features. Population comes from `AITown.GetPopulation` emitted in
the preflight `TRLN|...|P...|D...` sign because OpenTTD 13.4's CITY chunk has no population field.

## Outcomes and data quality — never model inputs

- Stage 1: `built`, `stage`, `failure_reason`.
- Timing quality: `barrier_flag`, `first_mutation_tick` (filter regression data to `M`).
- Post-hoc capital: `construction_cost`, `vehicle_cost`, `infra_cost`.
- Stage-2 components/target: `n_lead_vehicles`, `sum_profit_last_year`,
  `avg_max_age_years`, `vehicle_amortization_annual`, `infra_amortization_annual`,
  `amortization_annual`, `profit_ligne`.

`path_length` is deliberately absent: it is a pathfinder result and therefore leakage. Realized
cost and every profit/amortization field are outcomes, not features. Missing selected-pair features
mean the attempt failed before a candidate pair existed; downstream code must handle that missing
state explicitly rather than impute it using an outcome.

## Artefacts de configuration à exclure de l'entraînement (v1 uniquement)

**10 lignes de `data/phase2_hurdle_v1.csv` échouent pour une raison de configuration, pas de
terrain.** Elles doivent être écartées du jeu d'entraînement de l'étage 1 : laissées en place,
elles apprendraient au classifieur une règle fausse et non généralisable (« `engine_rank=7` ⇒
échec »), alors que le paramètre était simplement hors plage sur ces cartes.

Règle de filtrage :

```python
df = df[~df.failure_reason.isin(("ENGOOR", "PAIROOR"))]
```

| Raison | n | Cause |
|---|---:|---|
| `ENGOOR` | 9 | `engine_rank=7` demandé, mais < 8 moteurs constructibles sur 6 des 50 graines |
| `PAIROOR` | 1 | `pair_rank=200` demandé, mais < 200 paires éligibles sur la graine 1020 |

Ne pas exclure *toutes* les lignes à `engine_rank=7` : 116 des 125 ont abouti normalement (les
graines qui disposent bien de 8 moteurs). Seules les 9 lignes réellement en `ENGOOR` sont
artefactuelles.

**Corrigé à la source pour les campagnes suivantes** (2026-08-26) : `engine_rank` borné à `[0,6]`
dans `info.nut` et la variation de campagne ramenée à `%7`; les rangs de paire s'arrêtent à 180 au
lieu de 200. Ces bornes sont mesurées sur les 50 graines de cette campagne — un échantillon
nettement plus solide que la sonde à 8 graines qui avait servi à fixer les bornes précédentes
(elle annonçait 8-9 moteurs et un plafond de paires ≥ 255, tous deux optimistes). Une v2 ne devrait
donc plus produire ni `ENGOOR` ni `PAIROOR`.

## Résultats de la campagne v1

1000 lignes, 50 graines, 20 rangs de paire. 772 construites (77,2 %) / 228 échecs (22,8 %) —
équilibre de classes exploitable pour l'étage 1. Barrière : **811 `M`, 0 `O`** (les 189 vides sont
des échecs survenus avant toute mutation de la carte). `profit_ligne` sur les lignes construites :
−1 949 404 à +14 828 175, médiane 1 889 390.

Gradient de constructibilité par rang de paire, décroissant et régulier — c'est lui qui fabrique la
classe négative :

| rang | 0 | 5 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 |
|---|---|---|---|---|---|---|---|---|---|---|
| construites | 94 % | 92 % | 98 % | 94 % | 84 % | 78 % | 72 % | 86 % | 76 % | 78 % |

| rang | 90 | 100 | 110 | 120 | 130 | 140 | 150 | 160 | 180 | 200 |
|---|---|---|---|---|---|---|---|---|---|---|
| construites | 62 % | 84 % | 78 % | 64 % | 74 % | 72 % | 60 % | 74 % | 70 % | 54 % |

Répartition des échecs : `PATHLIM` 188, `TRKFAIL` 30, `ENGOOR` 9, `PAIROOR` 1. La domination des
`PATHLIM` (82 % des échecs) confirme que la constructibilité est d'abord un problème
**topographique** — voir l'argument pour le CNN dans `docs/phase3_ml.md`, section 3.6.

**Note de coût** : 3 h 48 de wallclock pour 1000 parties, très au-dessus de l'estimation de ~71 min
tirée du débit de calibration Phase 0 (12,8 s/partie avec trAIns). L'écart vient du preflight de
`TrainLineAI` : aux rangs élevés, le pathfinder consomme une grande partie de son budget avant
d'échouer en `PATHLIM`. À reprendre dans tout dimensionnement de campagne future.

**`data/` est dans `.gitignore`** : le CSV n'est pas versionné, seul `docs/phase2_hurdle_campaign_v1.json`
l'est. Le CSV se régénère depuis le JSON brut — mais la campagne elle-même ne se régénère
fidèlement qu'à version de `main.nut` et configuration OpenTTD constantes (voir la nuance en
section 3.8 de `docs/phase3_ml.md`).
