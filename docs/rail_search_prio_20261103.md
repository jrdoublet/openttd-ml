# RAIL-SEARCH-PRIO — arbitrage des recherches A* ferroviaires

**Mandat :** 3 novembre 2026. Worktree `/openttd-ml/.wt_sibling_20261102`,
branche `exp/rail-sibling-20261102`. **Réglage** `rail_search_prio` :
opt-in `0` par défaut, `1` politique expérimentale. Aucun commit ni
changement de défaut. Garde de valeur suspendue pour l'étude
(`--value-guard-max-loss-pct 100`), sans changement du défaut du harnais.

## Cause initiale, correction de l'hypothèse et périmètre

L'audit V190-ECO du bundle historique
`results/v190_fix_independent_4x6_20261103`
(SHA `6fef5804534fc3ff1bba4a51868a1dd60c6dc5b1139e4bd1c32aa81d9db253e1`)
montrait pour ON V190+V197, graine 841478, année 1972 :

| Événement mesuré | ON V190+V197 | OFF historique |
|---|---:|---:|
| `RAIL_SEARCH type=resumable outcome=OK` | 89 | 15 |
| `PROJECT_DISCARD reason=search_in_progress` | 36 | 0 |
| `PROJECT_CHOSEN` | 0 | 30 |
| `RAIL_BUILD` | 0 | 14 |

L'ancien soupçon d'un **stock C80 occupant le slot partagé**
était **incomplet** : `_startRailStockSearch` est déclenché
depuis la préparation C121 en mode AIR+RAIL et ne suffit pas
à expliquer, dans ce duel **rail seul**, les 89 recherches OK.
`V214_PATH` fournit **89 fois la même géométrie**
(`start=48340 end=21699 steps=73 turns=4 exits=2`) ;
les budgets sont pratiquement identiques
(80 recherches à 508 itérations, 4 à 506, 4 à 505, 1 à 503).
Il s'agit de **recalculs très similaires**, et non de
89 nouvelles lignes différentes. Les journaux historiques
n'étiquettent pas explicitement le propriétaire ; la piste
**upgrade répété** reste une inférence forte, à vérifier
avec les nouveaux logs de propriétaire.
`task_rail.nut` autorisait, sous `OpexV190Active()`,
le démarrage d'**upgrades secondaires** pendant qu'une autre
recherche A* occupait `_railSearch`. Le diagnostic doit séparer
en logs **project**, **stock**, **upgrade** et autres propriétaires,
plutôt que considérer un `RAIL_SEARCH outcome=OK`
comme une ouverture de ligne.

L'intervention `rail_search_prio=1` cherche à préserver les
recherches de **projets principaux finançables** sans interrompre
une recherche principale déjà élue ; seules des recherches
**secondaires** (stock/upgrade) peuvent céder le slot.
Leur annulation doit également libérer tout worker associé.
La construction conserve les gardes de caisse, d'abandon,
de proximité et les vérifications physiques, et les plans
stockés ne sont jamais consommés sans revalidation.
Le réglage `0` conserve les décisions et états antérieurs
sur les chemins inchangés.

## Protocole préenregistré

Le lanceur `sweeps/run_c66_reference.py` n'accepte
qu'une référence et une variante à la fois : **deux bancs 4×6**
contre la **même** référence sont nécessaires. Chaque banc utilise
quatre graines `17 512 841478 65537`, six années `1970–1975`,
carte 256², AAAHogEx-115 uniquement rail, `--probes 6`,
`--script-debug --line-telemetry --retain-savegames`,
`--cpus 9 --memory 8g --max-workers 9`,
`--mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml'`,
une seule campagne `openttd-lab` à la fois. **Aucune
édition du code pendant un banc**.

| Bras | Configuration OpexAI |
|---|---|
| Référence | `mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1` |
| PRIO | référence + `rail_search_prio=1` |
| PRIO+V190 | PRIO + `v190_rail_double_build=1,v197_guided_double=1` |

Principale métrique : `profit_year` OpexAI terminal, appariée
graine à graine à **la référence propre OpexAI**.
Indicateurs complémentaires : ouvertures ferroviaires
par graine×année, `search_in_progress` et propriétaires,
recherches et préemptions, p de Wilcoxon bilatéral, IC95
bootstrap, victoires/défaites, ratio de moyennes Opex/AAA.
Un smoke 4×6 est un **diagnostic de sélection**, pas une
qualification statistique.

**Portes conditionnelles :** chaque bras dont le profit
moyen smoke n'est pas inférieur à sa référence passe au
40 graines×5 années `gain_short`. Si son Δ moyen de
porte A est ≥0, faire séparément 20×10 rail seul
`non_erosion`, puis 20×10 multimodal
`non_erosion`, avec garde 100 %.
Les verdicts `pass/fail`, p et IC95 restent distincts
du simple signe de Δ ; ne jamais les confondre.

## Résultats de validation et de banc

Les deux campagnes ont **8/8 parties et 4/4 paires complètes** chacune,
sans échec moteur et avec le **même bundle source SHA-256**
73212e589da72b664159774dcdfdfed2ff9e5fc6d818a1ea40612fb18609d342.
La garde de valeur était neutralisée à 100 %.

| Campagne | Paires complètes | Δ moyen profit_year £/an | V/D/N | Wilcoxon p | IC95 bootstrap £/an | Opex/AAA REF→ON | Décision |
|---|---:|---:|---|---:|---|---|---|
| Smoke PRIO 4×6 | 4/4 | **−324 724,25** | 0/4/0 | 0,125 | [−509 247,50 ; −143 331,25] | 73,55 % → 44,78 % | NO-GO porte A |
| Smoke PRIO+V190 4×6 | 4/4 | **−409 490,75** | 0/4/0 | 0,125 | [−539 612 ; −279 369,50] | 74,37 % → 38,34 % | NO-GO porte A |

### Lignes ouvertes par année et propriétaire des recherches

Le bras PRIO ouvre **169 lignes contre 176** pour sa référence,
et produit 98 rejets search_in_progress contre 118 ; le bras
PRIO+V190 ouvre **141 lignes contre 176**, et produit 163
rejets contre 125. L'instrumentation PRIO+V190 confirme **32
préemptions d'upgrades**. Les deux bras restent 0 victoire / 4
malgré une exposition physique réelle.

Sur la graine 841478, PRIO construit **9 lignes en 1971 et 12 en
1972** ; PRIO+V190 en construit **10 et 7**. Le trou 0/0 de
l'ancien V190 est corrigé, mais il n'en résulte pas de profit
supérieur au témoin. Une amélioration du slot A* ne prouve donc
pas un avantage économique de l'ensemble de la compagnie.

Les ratios Opex/AAA sont descriptifs : AAA joue un match
indépendant sous chaque politique et peut diverger. La vraie
mesure causale du changement de politique est le delta
apparié de profit OpexAI. Les deux deltas moyens sont négatifs,
donc **aucune porte 40×5 ni 20×10 n'est lancée** selon les
conditions spécifiées.

Suite complète hors moteur : **3 208 tests**, un échec
préexistant de politique textuelle B6 (test_current_policy_is_observed_not_changed),
6 skipped, 2 expected failures ; nouveaux contrats, projection
OFF, V158 et V184 verts. Les 16 parties des deux smokes attestent
également que le bundle Squirrel compile et fonctionne.

## Traçabilité et restrictions

- Sources : `ai/OpexAI/{globals_pre,info,settings,task_rail,
  orchestrator,scheduler}.nut` ; tests
  `sweeps/test_rail_search_prio_20261103.py` ;
  entrée historique `docs/v190_eco_20261103.md`.
- Aucun arrêt/redémarrage Docker ou WSL. Ne jamais toucher aux
  conteneurs `fr-ordres-atelier-imperatif__*`. Aucun
  commit, push, merge, stash, reset ou nettoyage du worktree.
- Les campagnes ne doivent pas démarrer avant validation
  des contrats, de la projection OFF, de la suite complète,
  de la compilation moteur et de l'absence de banc concurrent.

## Annexes automatiques : par graine et annee

### rail_search_prio_4x6_20261103

# rail_search_prio_4x6_20261103
Source SHA: `73212e589da72b664159774dcdfdfed2ff9e5fc6d818a1ea40612fb18609d342`; years=6; seeds=[17, 512, 841478, 65537]; complete_pairs=4; verdict=fail_primary.
Delta profit Opex: mean **-324 724 £/an**, V/D/N = 0/4/0, Wilcoxon p=0.125, bootstrap IC95=[-509 248; -143 331] £/an.

| Seed | REF Opex | ON Opex | Δ profit | REF AAA | ON AAA | Opex/AAA REF→ON |
|---:|---:|---:|---:|---:|---:|---:|
| 17 | 1 540 813 | 1 218 966 | -321 847 | 1 989 234 | 2 268 080 | 77.5%→53.7% |
| 512 | 1 491 268 | 1 169 927 | -321 341 | 2 589 360 | 3 157 316 | 57.6%→37.1% |
| 841478 | 1 844 406 | 1 272 523 | -571 883 | 1 717 938 | 3 044 141 | 107.4%→41.8% |
| 65537 | 1 453 194 | 1 369 368 | -83 826 | 2 309 264 | 2 765 858 | 62.9%→49.5% |

| Seed | Final rail lines REF/ON | Trains REF/ON | Trains per line REF/ON | Max trains per line REF/ON |
|---:|---:|---:|---:|---:|
| 17 | 42/41 | 49/44 | 1.17/1.07 | 2/2 |
| 512 | 43/40 | 47/40 | 1.09/1.00 | 2/1 |
| 841478 | 48/45 | 57/48 | 1.19/1.07 | 2/2 |
| 65537 | 42/43 | 47/44 | 1.12/1.02 | 2/2 |

| Seed | Year | Lines REF/ON | Blocked REF/ON | Search slices REF/ON | Wagons built REF/ON (mean) |
|---:|---:|---:|---:|---:|---|
| 17 | 1970 | 10/10 | 0/0 | 2/2 | 3.0/3.0 |
| 17 | 1971 | 8/8 | 9/3 | 8/13 | 3.0/2.8 |
| 17 | 1972 | 10/12 | 12/6 | 11/15 | 2.9/2.4 |
| 17 | 1973 | 9/6 | 11/6 | 9/9 | 2.7/2.7 |
| 17 | 1974 | 2/5 | 0/3 | 3/10 | 3.5/3.0 |
| 17 | 1975 | 4/0 | 3/0 | 2/0 | 1.0/— |
| 512 | 1970 | 6/6 | 0/0 | 1/1 | 2.5/2.5 |
| 512 | 1971 | 11/14 | 3/0 | 10/8 | 2.6/2.4 |
| 512 | 1972 | 17/12 | 0/3 | 16/14 | 2.2/2.2 |
| 512 | 1973 | 5/6 | 4/0 | 6/8 | 3.4/2.8 |
| 512 | 1974 | 3/2 | 6/3 | 4/4 | 2.0/1.0 |
| 512 | 1975 | 1/0 | 4/3 | 1/1 | 4.0/— |
| 841478 | 1970 | 10/11 | 0/0 | 7/4 | 3.0/2.3 |
| 841478 | 1971 | 12/9 | 0/0 | 11/13 | 3.0/2.9 |
| 841478 | 1972 | 14/12 | 0/0 | 15/17 | 2.1/2.9 |
| 841478 | 1973 | 8/11 | 11/6 | 13/20 | 4.6/3.4 |
| 841478 | 1974 | 3/1 | 5/0 | 5/2 | 2.7/2.0 |
| 841478 | 1975 | 1/1 | 0/0 | 2/2 | 4.0/6.0 |
| 65537 | 1970 | 11/11 | 0/0 | 4/4 | 2.9/2.9 |
| 65537 | 1971 | 12/12 | 0/0 | 9/9 | 3.5/3.5 |
| 65537 | 1972 | 12/12 | 9/12 | 15/21 | 2.0/2.1 |
| 65537 | 1973 | 2/3 | 3/19 | 5/6 | 2.5/6.3 |
| 65537 | 1974 | 3/3 | 17/13 | 4/5 | 3.0/2.3 |
| 65537 | 1975 | 2/2 | 21/21 | 1/3 | 3.0/3.0 |

Aggregate lines REF/ON 176/169; PROJECT_DISCARD search_in_progress REF/ON 118/98.

Instrumentation ON owner events:
- blocked:project: 3440
- blocked:upgrade: 18
- end:project: 133
- end:upgrade: 79
- preempt:upgrade: 64
- start:project: 134
- start:upgrade: 85

### rail_search_prio_v190_4x6_20261103

# rail_search_prio_v190_4x6_20261103
Source SHA: `73212e589da72b664159774dcdfdfed2ff9e5fc6d818a1ea40612fb18609d342`; years=6; seeds=[17, 512, 841478, 65537]; complete_pairs=4; verdict=fail_primary.
Delta profit Opex: mean **-409 491 £/an**, V/D/N = 0/4/0, Wilcoxon p=0.125, bootstrap IC95=[-539 612; -279 370] £/an.

| Seed | REF Opex | ON Opex | Δ profit | REF AAA | ON AAA | Opex/AAA REF→ON |
|---:|---:|---:|---:|---:|---:|---:|
| 17 | 1 540 813 | 1 070 652 | -470 161 | 1 989 234 | 2 657 347 | 77.5%→40.3% |
| 512 | 1 491 268 | 1 196 371 | -294 897 | 2 589 360 | 3 399 126 | 57.6%→35.2% |
| 841478 | 1 844 406 | 1 235 343 | -609 063 | 1 717 938 | 2 558 154 | 107.4%→48.3% |
| 65537 | 1 416 764 | 1 152 922 | -263 842 | 2 165 424 | 3 528 915 | 65.4%→32.7% |

| Seed | Final rail lines REF/ON | Trains REF/ON | Trains per line REF/ON | Max trains per line REF/ON |
|---:|---:|---:|---:|---:|
| 17 | 42/29 | 49/33 | 1.17/1.14 | 2/2 |
| 512 | 43/39 | 47/49 | 1.09/1.26 | 2/2 |
| 841478 | 48/40 | 57/46 | 1.19/1.15 | 2/2 |
| 65537 | 42/33 | 47/39 | 1.12/1.18 | 2/2 |

| Seed | Year | Lines REF/ON | Blocked REF/ON | Search slices REF/ON | Wagons built REF/ON (mean) |
|---:|---:|---:|---:|---:|---|
| 17 | 1970 | 10/9 | 0/0 | 2/1 | 3.0/2.4 |
| 17 | 1971 | 8/9 | 9/3 | 8/10 | 3.0/1.2 |
| 17 | 1972 | 10/2 | 12/21 | 11/3 | 2.9/6.0 |
| 17 | 1973 | 9/3 | 11/6 | 9/6 | 2.7/4.0 |
| 17 | 1974 | 2/3 | 0/18 | 3/5 | 3.5/3.7 |
| 17 | 1975 | 4/3 | 3/6 | 2/2 | 1.0/1.3 |
| 512 | 1970 | 6/7 | 0/0 | 1/1 | 2.5/2.1 |
| 512 | 1971 | 11/12 | 3/0 | 10/6 | 2.6/1.7 |
| 512 | 1972 | 17/6 | 0/12 | 16/9 | 2.2/4.0 |
| 512 | 1973 | 5/8 | 4/3 | 6/14 | 3.4/2.9 |
| 512 | 1974 | 3/3 | 6/10 | 4/6 | 2.0/4.0 |
| 512 | 1975 | 1/3 | 4/5 | 1/3 | 4.0/2.3 |
| 841478 | 1970 | 10/9 | 0/0 | 7/7 | 3.0/2.1 |
| 841478 | 1971 | 12/10 | 0/0 | 11/15 | 3.0/2.4 |
| 841478 | 1972 | 14/7 | 0/0 | 15/13 | 2.1/3.0 |
| 841478 | 1973 | 8/7 | 11/6 | 13/17 | 4.6/3.9 |
| 841478 | 1974 | 3/5 | 5/15 | 5/5 | 2.7/4.0 |
| 841478 | 1975 | 1/2 | 0/6 | 2/6 | 4.0/4.0 |
| 65537 | 1970 | 11/7 | 0/0 | 4/3 | 2.9/2.7 |
| 65537 | 1971 | 12/11 | 0/0 | 9/14 | 3.5/2.1 |
| 65537 | 1972 | 13/6 | 6/3 | 13/13 | 2.1/3.2 |
| 65537 | 1973 | 2/3 | 18/17 | 3/3 | 4.0/4.3 |
| 65537 | 1974 | 2/3 | 12/15 | 4/7 | 9.5/5.3 |
| 65537 | 1975 | 2/3 | 21/17 | 2/3 | 2.5/5.3 |

Aggregate lines REF/ON 176/141; PROJECT_DISCARD search_in_progress REF/ON 125/163.

Instrumentation ON owner events:
- blocked:project: 3707
- end:project: 134
- end:upgrade: 71
- preempt:upgrade: 32
- start:project: 134
- start:upgrade: 73

