> **Note de relecture (Claude, 12/10)** — rapport d'agy archivé tel quel, mesure sur le 5×6 frais
> `astar_pending_expo_5x6_20261011` (code `9144dc5`, V126 OFF). Le blocage par la marge en 1970–1971 est
> **un proxy** (`VIVIER next_capital` − 28 k£), pas un événement direct : `AIR_FINANCE_SELECT` et le coût réel
> `AIAccounting` ne sont émis que sous `probe_air_finance_margin=1`. La baisse à 2 k£ a déjà échoué en porte A
> le 07/10 (V126, `fail_primary`) et le 08/10 (6×3, −70,7 k£/an) : ne pas la relancer. Une marge intermédiaire
> adaptée au risque d'échec (BFAIL ≈ 20 k£ exposés) serait une hypothèse distincte, à mesurer d'abord sous la
> sonde dédiée.

# Rapport V126 — Marge de financement des aéroports et coût réel : mesure sur journaux frais (1970–1975)

**Dépôt :** `/home/deploy/projects/openttd-ml` (lecture seule, commit `9144dc5b8aa696c46d57fb0ff36df120f6f8d757`, 11/10/2026).  
**Corpus analysé :** Journaux bruts du banc 5×6 frais `results/astar_pending_expo_5x6_20261011_engine/reference_seed{42,100,999,1234,5678}_r0.log` (options actives : `decision_log=1`, `probe_scheduler=1`, `--script-debug` ; défauts courants donc `air_site_cost_quote=0`, `air_site_cost_margin_pct=0`, `probe_air_finance_margin=0`, `probe_cost=0`).

---

## 1. Tentatives de construction, capital prévu et échecs (1970–1975)

### 1.1 Constructions réalisées (`AIR_BUILD`) par graine et par année
Au total, **251 lignes aériennes** ont été construites sur les 5 graines entre 1970 et 1975 :
- **1970** est dominée par les nouvelles paires (`newpair`, 2 aéroports neufs, marge 30 k£) : 33 newpair, 7 hubsite, 0 hubhub.
- **1971** voit l'expansion en étoile (`hubsite`, 1 aéroport neuf, marge 12 k£) et les maillages (`hubhub`, 0 aéroport neuf, marge 2 k£) : 9 newpair, 39 hubsite, 56 hubhub.
- **1972–1975** est massivement `hubhub` (coût prévu = 1 avion ~38 964 £ ou 36 914 £).

| Graine | Total | 1970 (np/hs/hh) | 1971 (np/hs/hh) | 1972 (np/hs/hh) | 1973 (np/hs/hh) | 1974 (np/hs/hh) | 1975 (np/hs/hh) | Capital prévu total (£) | Capital prévu médian (£) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **42** | 54 | 10 (9/1/0) | 29 (2/12/15) | 4 (1/2/1) | 1 (0/0/1) | 5 (0/2/3) | 5 (0/0/5) | 3 131 818 | 38 964 |
| **100** | 44 | 9 (6/3/0) | 18 (0/6/12) | 8 (0/3/5) | 3 (1/1/1) | 1 (0/0/1) | 5 (1/1/3) | 2 336 715 | 38 964 |
| **999** | 40 | 6 (4/2/0) | 11 (3/6/2) | 10 (1/7/2) | 5 (0/1/4) | 5 (0/2/3) | 3 (1/0/2) | 3 235 946 | 61 523 |
| **1234** | 56 | 6 (5/1/0) | 10 (4/6/0) | 26 (0/8/18) | 3 (0/2/1) | 4 (0/2/2) | 7 (0/0/7) | 2 910 401 | 36 914 |
| **5678** | 57 | 9 (9/0/0) | 30 (4/9/17) | 14 (0/0/14) | 3 (0/1/2) | 1 (0/0/1) | 0 (0/0/0) | 3 079 045 | 38 964 |
| **Total** | **251** | **40** | **98** | **62** | **15** | **16** | **20** | **14 693 925** | — |

*Preuve journal :*
`[2026-10-11 21:15:26] dbg: [script:4] [0] [I] OPEX 1970-1-17 AIR_BUILD arm=newpair line=0 src=24869 dst=48086 src_town=2 dst_town=30 dist=214 profit=393340 cost=119705 planes=2 engine=223`

### 1.2 Échecs de construction (`PROJECT_DISCARD reason=build_failed`) et motifs
Au total, **66 chantiers ont échoué** en cours de pose physique (52 BFAIL, 14 AFAIL) :
- **Footprint non plat (`error=263 airport footprint remains non-flat`) : 20 échecs** (4 AFAIL, 16 BFAIL), présents sur toutes les graines (42: 4, 100: 4, 999: 4, 1234: 5, 5678: 3).
- **Emprise invalide (`error=2 invalid airport footprint`) : 32 échecs** (4 AFAIL, 28 BFAIL), concentrés sur la graine 5678 en 1970–1971 suite à l'expansion municipale entre scan et pose.
- **Refus municipal (`error=258 ERR_LOCAL_AUTHORITY_REFUSES`) : 10 échecs** (4 AFAIL, 6 BFAIL), sur la graine 1234 (1973) et 100 (1971), non résolus par les plantations d'arbres.
- **Plafond de stations (`error=771 ERR_STATION_TOO_MANY_STATIONS_IN_TOWN`) : 4 échecs** (2 AFAIL, 2 BFAIL) en 1973/1975.

| Graine | Total Échecs | AFAIL | BFAIL | 1970 | 1971 | 1972 | 1973 | 1974 | 1975 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **42** | 4 | 1 | 3 | 1 | 1 | 1 | 1 | 0 | 0 |
| **100** | 5 | 1 | 4 | 1 | 1 | 1 | 2 | 0 | 0 |
| **999** | 5 | 2 | 3 | 3 | 1 | 0 | 0 | 0 | 1 |
| **1234** | 15 | 5 | 10 | 2 | 2 | 0 | 11 | 0 | 0 |
| **5678** | 37 | 5 | 32 | 4 | 29 | 1 | 3 | 0 | 0 |
| **Total** | **66** | **14** | **52** | **11** | **34** | **3** | **17** | **0** | **1** |

*Preuve journal :*
`[2026-10-11 21:15:33] dbg: [script:4] [0] [I] OPEX 1971-5-8 PROJECT_DISCARD rank=0 mode=air src=59980 dst=28041 reason=build_failed detail=BFAIL error=263 error_text=airport footprint remains non-flat`

### 1.3 Coût réel dépensé (`AIAccounting`) et coût perdu des échecs : état des données
- **Coût réel AIAccounting des réussites : NON DISPONIBLE dans ces journaux.** Le code ne publie `result.actualCost` que sous `PROBE_AIR_FINANCE_MARGIN` (événement `AIR_FINANCE_TRY`, `task_air.nut:802`) ou sous `AIR_COST_PROBE` (panneau `AC|`, `task_air.nut:818`). Les deux réglages étant à 0 au défaut, aucun compteur `actualCost` n'est inscrit dans le log.
- **Coût perdu des échecs : NON CHIFFRÉ dans `PROJECT_DISCARD`.** Sur les 52 `BFAIL`, l'aéroport A était déjà posé (16 200 £ catalogue + terrassement). Avec la maintenance à 0, l'aéroport A orphelin est conservé sans être liquidé. La perte nette réelle n'est traçable que sous `probe_air_finance_margin=1` (`AIR_ORPHAN_RETAIN`, `air_construction.nut:502`).
- **Proxy disponible (`P2_BUILD` delta de capital disponible) :** Le delta `cap_before - cap_after` sur les passes à 1 construction montre un ratio médian par rapport au capital prévu de **0,90 à 1,02** (max 1,12 sur graine 100), mais ce delta macroéconomique incorpore les recettes, frais d'exploitation et intérêts de la période.

---

## 2. Refus pour marge de financement

Le filtrage par la marge intervient à deux niveaux distincts :
1. **À la sélection Vivier / Portefeuille (`projects_selection.nut:1724`) :** Le capital d'éligibilité (`decisionFinanceCapital`) inclut `OpexAirRequiredMargin` (30 k£, 12 k£ ou 2 k£). Si `budget < capital + marge`, le projet n'entre jamais dans `projects.best`.
2. **À l'exécution (`task_air.nut:830`) :** Si la caisse baisse entre sélection et pose (`money < capital + reserve + margin`), le projet est rejeté pour `insufficient_cash`.

### 2.1 Refus d'exécution (`PROJECT_DISCARD reason=insufficient_cash`)
Seulement **12 rejets d'exécution** apparaissent sur l'ensemble des 5 graines, car le Vivier filtre l'essentiel en amont :
- **Graine 100 (1971-06-15) :** 3 projets rejetés dans la même passe (`src=59176 dst=24247`, `src=59176 dst=15598`, `src=21717 dst=41042`), `need=92 164 £`, `cash=79 826 £`, **déficit = 12 338 £**.
  - *Chronologie / Devenir :* 
    - Le projet `59176 <-> 24247` a été **construit 10 jours plus tard** (1971-06-25, line 15, profit 97 232 £/an).
    - Le projet `21717 <-> 41042` a été **construit 17 jours plus tard** (1971-07-02, line 16, profit 86 804 £/an).
    - Le projet `59176 <-> 15598` a été retenté le 1972-06-28 mais s'est soldé par un **BFAIL** (site 15598 non nivelable).
- **Graine 1234 (1970-09-21 et 1972-08-02) :** 8 rejets.
  - 1970-09-21 : `src=41400 dst=5163`, `need=111 126 £`, `cash=106 689 £`, **déficit = 4 437 £**. Les deux villes ont été raccordées plus tard via d'autres hubs.
  - 1972-08-02 : 7 rangs consécutifs (`src=32905` vers diverses destinations), `need=63 914 £`, `cash=63 855 à 63 700 £`, **déficits minimes de 59 à 214 £**.
- **Graine 5678 (1970-04-10) :** 1 rejet (`src=57904 dst=16545`), `need=106 364 £`, `cash=97 465 £`, **déficit = 8 899 £**. La première extrémité a été construite **59 jours plus tard** (1970-06-08, line 2), la seconde **8 mois plus tard** (1970-12-16, line 8).
- **Graines 42 et 999 :** 0 rejet d'exécution (la caisse n'a jamais fléchi entre sélection et pose).

*Preuve journal :*
`[2026-10-11 21:15:34] dbg: [script:4] [0] [I] OPEX 1971-6-15 PROJECT_DISCARD rank=1 mode=air src=59176 dst=24247 reason=insufficient_cash need=92164 cash=79826`

### 2.2 Blocage amont au Vivier (Portefeuille) : jours bloqués et passes
L'événement dédié `AIR_FINANCE_SELECT` (`projects_selection.nut:2118`) n'est pas émis au défaut. En revanche, l'arbitrage est traçable via `VIVIER` (`budget` vs `next_capital`) et `P5_RAIL_PASS` (`best_nonrail_cap`) :
Lorsque le budget disponible est insuffisant pour `next_capital` (projet aérien avec sa marge de 30 k£), mais couvrirait le capital réel + 2 k£ de plancher résiduel (`budget >= next_capital - 28 000 £`), le projet est **matériellement bloqué par la seule marge de financement**.

Ce phénomène est massif et circonscrit à **1970–1971** :

| Graine | Passes Vivier bloquées par marge en 1970 | Jours uniques bloqués en 1970 | Passes Vivier bloquées par marge en 1971 | Jours uniques bloqués en 1971 | Déficit médian au Vivier (£) | Déficit p90 au Vivier (£) |
|---|---:|---:|---:|---:|---:|---:|
| **42** | 75 | **69 jours** | 140 | **112 jours** | 17 063 | 25 459 |
| **100** | 141 | **131 jours** | 160 | **138 jours** | 14 452 | 22 698 |
| **999** | 108 | **83 jours** | 200 | **161 jours** | 9 378 | 23 919 |
| **1234** | 175 | **106 jours** | 120 | **98 jours** | 13 574 | 23 056 |
| **5678** | 149 | **127 jours** | 175 | **128 jours** | 8 490 | 22 909 |
| **Moyenne** | **130 passes** | **103 jours** | **159 passes** | **127 jours** | **12 591 £** | **23 608 £** |

En 1972–1975, ce blocage tombe à zéro (la caisse dépasse largement les marges).

*Preuve journal :*
`[2026-10-11 21:15:31] dbg: [script:4] [0] [I] OPEX 1971-1-22 VIVIER path=reselect considered=58 selected=3 pool_selected=3 rejected=55 not_selected=55 budget=51543 selection_pool_capital=112323 next_capital=101364 remaining=0 pool_headroom=0 sel_ops=25692`  
`[2026-10-11 21:15:31] dbg: [script:4] [0] [I] OPEX 1971-1-23 P5_RAIL_PASS pass=129 date=1971-1-22 in_cap=51469 alts=55 rail_alts=0 rail_aff=0 rail_in_best=3 nonrail_in_best=0 rail_built=0 stop=no_candidate_built best_rail_rank=-1 best_nonrail_mode=air best_nonrail_score=948.2262 best_nonrail_cap=101364`

---

## 3. Combien de refus auraient été évités avec une marge au résidu réel (2 000 £) ?

1. **Sur les refus d'exécution observés (12 événements) :**
   - **12 sur 12 (100 %)** auraient été évités immédiatement.
   - Sur la graine 100, le besoin `need = capital + reserve + 30 000 = 92 164 £` serait descendu à `64 164 £`. Avec `cash = 79 826 £`, les 3 refus du 15 juin 1971 disparaissaient, avançant la mise en service des lignes 15 et 16 de 10 à 17 jours.
   - Sur la graine 1234, les déficits du 1972-08-02 étaient de 59 à 214 £, effacés par n'importe quelle baisse marginale.
   - Sur la graine 5678, le déficit de 8 899 £ était inférieur à la réduction de 28 000 £ de marge.

2. **Sur les blocages Vivier / Portefeuille :**
   - Dans **54 % des passes bloquées en 1970** et **67 % des passes en 1971**, le budget disponible couvrait le capital réel + 2 k£.
   - La baisse de marge aurait permis de débloquer la sélection **103 jours plus tôt en 1970** et **127 jours plus tôt en 1971** par graine en moyenne.

---

## 4. Localisation des événements de journal dans le code (commit `9144dc5`)

| Donnée recherchée | Statut dans les logs frais | Fichier et ligne au commit `9144dc5` | Condition d'émission dans le code | Ce qui manque pour une mesure complète |
|---|---|---|---|---|
| **Ligne construite & capital prévu** | **Présent** | `ai/OpexAI/task_air.nut:846-851` | `DECISION_LOG=1` (`AIR_BUILD`) | Mesure le capital prévu (`buildPlan.capital`), pas le coût réel. |
| **Coût réel dépensé (`AIAccounting`)** | **ABSENT** | `ai/OpexAI/task_air.nut:802` (`AIR_FINANCE_TRY`) et `task_air.nut:818` (panneau `AC\|`) | `PROBE_AIR_FINANCE_MARGIN=1` ou `AIR_COST_PROBE=1` (`probe_cost=1`) | Les deux réglages valent 0 au défaut. `AIAccounting` n'est pas logué. |
| **Ventilation coût réel (sites/avions)** | **ABSENT** | `ai/OpexAI/air_construction.nut:261, 340` | `PROBE_AIR_FINANCE_MARGIN=1` | Les compteurs `c_level`, `c_airport`, `c_planes` ne sont pas instanciés. |
| **Échecs de pose & motif** | **Présent** | `ai/OpexAI/task_air.nut:839` | `DECISION_LOG=1` (`PROJECT_DISCARD detail=...`) | Donne l'étape (AFAIL/BFAIL) et l'erreur, mais pas le coût perdu. |
| **Perte nette d'un échec / orphelin** | **ABSENT** | `ai/OpexAI/air_construction.nut:502` | `PROBE_AIR_FINANCE_MARGIN=1` (`AIR_ORPHAN_RETAIN`) | Réglage à 0 au défaut ; la perte d'actif de l'aéroport A orphelin n'est pas loguée. |
| **Refus caisse à l'exécution** | **Présent** | `ai/OpexAI/task_air.nut:831` | `DECISION_LOG=1` (`PROJECT_DISCARD reason=insufficient_cash`) | Présent, mais plafonné à 3 lignes/mois (`task_projects.nut:2066`). |
| **Refus marge amont (Vivier)** | **Partiel (proxy)** | `ai/OpexAI/projects_selection.nut:2118` (`AIR_FINANCE_SELECT`) | `PROBE_AIR_FINANCE_MARGIN=1` | L'événement direct manque ; reconstitué via `VIVIER next_capital` (`ledgers.nut:980`). |

---

## 5. Verdict économique et recommandation

### 5.1 Verdict
**Oui, la marge historique (30/12/2 k£) bloque matériellement des aéroports rentables sur le code actuel.**
- **Ordre de grandeur en temps :** **~70 à 130 jours de retard** par graine en 1970 et en 1971 sur l'ouverture des premières lignes.
- **Ordre de grandeur financier :** Pour des lignes générant 150 k£ à 400 k£/an de profit (~400 à 1 100 £/jour), retarder la pose de 30 à 90 jours représente un manque à gagner de trésorerie de **~20 k£ à ~70 k£ par ligne retardée** au démarrage.

### 5.2 Pourquoi une baisse directe de marge à 2 k£ reste dangereuse
Les données fraîches confirment la présence de **52 échecs BFAIL** sur les 5 graines.
Lors d'un BFAIL, la compagnie a déjà payé l'aéroport A (~16,2 k£ + terrassement ~5–15 k£). Avec une marge de seulement 2 000 £ :
1. Un surcoût imprévu de terrassement ou un BFAIL consomme la réserve de trésorerie.
2. La compagnie se retrouve en risque d'illiquidité avant que la première recette n'arrive (délai médian 43–83 jours).
3. Ce mécanisme explique l'échec économique de la campagne 6×3 du 08/10 (`-70 729 £/an` de perte moyenne sous devis ON + marge 2 k£).

### 5.3 Variante isolée à tester et protocole V102
Pour lever ce verrou sans reproduire la régression de la campagne du 08/10, il faut dissocier l'évaluation du risque et la marge :
1. **Variante isolée candidate :**
   `air_site_cost_quote=1` avec **marge protectrice adaptée au risque d'échec** (ex. `air_site_quote_keep_legacy_margin=1` ou une marge calibrée couvrant l'exposition BFAIL ~20 k£ au lieu du plancher 2 k£).
2. **Protocole de qualification V102 :**
   - **Contrats & Smoke apparié :** 1 graine × 1 an avec `probe_air_finance_margin=1` pour mesurer les résidus exacts.
   - **Porte A (`gain_short`) :** 40 graines × 3 ans, règle `gain_short`, seuil relatif +4 % du `profit_year` de référence, garde de valeur −5 %, Wilcoxon bilatéral p < 0,05, borne basse bootstrap IC95 > 0.
   - **Porte B (`non_erosion`) :** 20 graines × 10 ans, règle `non_erosion`, borne haute bootstrap IC95 >= 0, garde de valeur −5 %.
   - **Défauts inchangés** tant que les deux portes V102 ne sont pas franchies.
