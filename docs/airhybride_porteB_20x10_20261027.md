# AIRHYB — spirale hybride, porte B 20×10 du 27 octobre 2026

**Verdict : `pass` à dix ans et optimisation d'opcodes adoptable selon AGENTS.md §4 ; défaut maintenu à `air_site_funnel=0`.** La baisse mesurée du cumul `AIR_SITE_SEARCH` est de **5,11 %** sur les 20 graines, avec 11 graines en baisse et 9 en hausse. La porte B ne démontre pas un gain économique significatif, mais satisfait les critères pré-enregistrés de non-érosion. Aucun changement de défaut, de code IA ou de `master` n'est inclus dans cette qualification.

## Protocole et provenance

- Branche `air-site-funnel`, commit testé `1ffcd431ac4fa87594a4ae0430a2d8ee7b6e5c90`, état Git propre au lancement. Bundle figé commun `3462314e2e35659d34279fa89a47fa12123711dc141b205592072ef675dd1108` ; image `openttd-lab:latest`, ID `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Deux duels distincts par graine contre **AAAHogEx-115 inchangé**, carte 256×256, début 1970, simulation jusqu'à 1979, multimodal, une répétition ; référence `OpexAI[probes=258,air_site_funnel=0]`, variante `OpexAI[probes=258,air_site_funnel=1]`, identifiant `airf1`. Les 20 graines standard sont utilisées, avec `73 → 373684` pour éviter le plantage documenté d'AAAHogEx.
- Harnais `sweeps/run_c66_reference.py`, `--decision-rule non_erosion --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --required-seeds 20 --required-years 10 --years 10 --repeats 1 --probes 258 --script-debug --cpus 10 --memory 8g --max-workers 10 --mount-root ..`. Le seuil 4 % est enregistré par le lanceur mais ne conditionne pas la porte B.
- Smoke préalable `airhybride_smoke_1x1_20261027` : graine 42, 1 an, 2/2 parties complètes, verdict `diagnostic_only`, delta profit +20 227 £/an, valeur +4,92 % ; journaux `AIR_SITE_SEARCH` présents dans les deux bras.
- Porte B `airhybride_porteB_20x10_20261027` : `results/airhybride_porteB_20x10_20261027.json`, `.jsonl`, `.manifest.json`, `_bundle/`, `_engine/` et relevé local `_sites.csv` dans le worktree. Les résultats bruts volumineux demeurent dans `results/` ignoré par Git ; les chiffres essentiels sont reproduits ici.

## Résultat économique et santé

| Mesure Opex variante − Opex référence à l'année terminale | Résultat |
| --- | ---: |
| Paires complètes / attendues | **20 / 20** |
| Parties saines / attendues | **40 / 40** |
| Couverture des métriques, comparaison et échantillon d'adoption | **complètes** |
| Profit annuel, delta moyen | **+137 383,85 £/an** |
| Profit annuel, delta médian | **+185 492,50 £/an** |
| Victoires / défaites / égalités | **11 / 9 / 0** |
| Test des signes bilatéral | **p = 0,823803** |
| Wilcoxon bilatéral | **p = 0,277355** |
| IC95 bootstrap de la moyenne (20 000 rééchantillonnages, graine 0) | **[−77 620,05 ; +348 872,90] £/an** |
| IC95 Student de la moyenne | **[−98 494,93 ; +373 262,63] £/an** |
| Valeur, ratio des moyennes variante / référence | **1,019106, soit +1,910584 %** |
| Verdict brut `policy_comparison.verdict` | **`pass`** |

Tous les jeux ont `game_status=complete`, `failed_runs=0`, et aucun échec d'IA Opex attribué ou non attribué n'est relevé. Les **40 journaux moteurs** sont présents ; aucune correspondance de type `script error`, `squirrel error`, `exception`, `fatal`, `ai error` ou niveau `[E]` n'a été trouvée. `comparison_complete`, `adoption_sample_complete` et `metric_coverage_complete` valent `true`, ainsi que `ci_pass` et `value_guard_pass`.

## OpCodes et aéroports par graine

Les colonnes `AIR_SITE_SEARCH` sont le **maximum du champ cumulatif `ops=`** trouvé dans le journal de chaque bras, sur la partie entière ; le compteur est monotone (`AIR_SITE_SEARCH_OPS` n'est augmenté que d'un coût positif après chaque `OpexAirFindSite`). Le nombre d'aéroports Opex provient de `airport_slots_opex` du cliché terminal. Le « gain ops » est `(référence − variante) / référence` : positif = moins d'opcodes. `Δ profit` est variante − référence en £/an.

| Graine | AIR_SITE_SEARCH réf. | AIR_SITE_SEARCH hybride | Gain ops | Aéroports réf. / hybride | Δ profit £/an |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 2 102 600 | 2 321 098 | −10,39 % | 35 / 35 | −68 764 |
| 100 | 5 093 953 | 3 832 083 | +24,77 % | 24 / 26 | −12 135 |
| 7 | 1 825 521 | 2 046 086 | −12,08 % | 36 / 35 | +486 527 |
| 999 | 2 700 025 | 1 857 799 | +31,19 % | 33 / 37 | +486 933 |
| 2026 | 2 447 166 | 1 927 737 | +21,23 % | 34 / 33 | +532 227 |
| 1 | 2 381 138 | 2 122 657 | +10,86 % | 34 / 35 | +280 442 |
| 17 | 2 614 544 | 3 088 573 | −18,13 % | 33 / 31 | +90 543 |
| 373684 (remplace 73) | 2 804 056 | 3 607 505 | −28,65 % | 27 / 24 | −38 836 |
| 314 | 1 832 286 | 1 443 277 | +21,23 % | 38 / 39 | +1 059 721 |
| 512 | 5 373 583 | 4 947 884 | +7,92 % | 22 / 24 | +374 727 |
| 1024 | 3 309 920 | 3 366 406 | −1,71 % | 31 / 28 | −438 847 |
| 1337 | 2 013 716 | 2 073 666 | −2,98 % | 38 / 36 | −465 298 |
| 4096 | 1 384 750 | 1 157 915 | +16,38 % | 38 / 41 | +866 776 |
| 8191 | 3 148 686 | 2 079 438 | +33,96 % | 39 / 33 | +404 410 |
| 12345 | 2 740 023 | 2 294 890 | +16,25 % | 34 / 32 | −337 253 |
| 54321 | 2 596 976 | 2 331 552 | +10,22 % | 34 / 36 | +752 377 |
| 65537 | 2 615 751 | 3 208 060 | −22,64 % | 28 / 32 | −185 863 |
| 123456 | 1 841 896 | 2 345 472 | −27,34 % | 33 / 30 | −655 996 |
| 424242 | 2 645 391 | 2 423 334 | +8,39 % | 39 / 40 | +331 289 |
| 8675309 | 2 305 969 | 2 554 525 | −10,78 % | 34 / 35 | −715 303 |
| **Total 20 parties par bras** | **53 777 950** | **51 029 957** | **+5,11 %** | — | — |

Le coût cumulé du poste de recherche de sites baisse de **2 747 993 opcodes** au total. Il est toutefois supérieur avec l'hybride sur **9/20** graines. Le nombre de recherches et la trajectoire économique peuvent diverger entre les bras : ce résultat mesure la consommation réellement observée du poste, sans isoler une économie par appel à trajectoire strictement identique. Les six diagnostics antérieurs à cinq ans rapportaient des diminutions de 14 à 27 % ; la porte B complète donne la mesure pertinente à dix ans.

## Application de la règle spéciale opcodes

La règle de `AGENTS.md` §4 exige un gain mesuré sur le poste visé, un 20×10 sain, l'IC95 **Student** du delta de `profit_year` non entièrement négatif, aucune défaite significative au test des signes (`p ≥ 0,05` ou majorité de victoires) et une garde de valeur à −5 % respectée. Ces critères sont **tous satisfaits** : gain d'opcodes +5,11 %, 20/20, borne haute Student positive, `p_signes=0,823803` avec 11 victoires, valeur +1,91 %. Le verdict est donc **adoptable au titre des opcodes**, indépendamment de l'absence de gain économique statistiquement démontré. Il ne signifie pas que chaque graine progresse. **Le défaut reste 0** ; aucun changement de réglage ni fusion vers `master` n'est réalisé dans ce lot.
