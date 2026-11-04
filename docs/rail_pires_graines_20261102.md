# Graines ferroviaires défavorables — dépouillement rétrospectif du 2 novembre 2026

**Portée.** Analyse hors ligne des résultats existants, sans partie supplémentaire. Les comparaisons portent sur des duels de deux compagnies, OpexAI et AAAHogEx-115, sur une carte commune de 256². La campagne ferroviaire `rail_sibling_railseul_40x5_20261102` était encore en cours de production (JSONL non finalisé) au moment du dépouillement ; les résultats définitifs de cette campagne **ne figurent pas** ici. Les quatre graines du smoke `r2` forment un diagnostic, pas une qualification de rendement.

## Calcul et sources

Pour chaque `(graine, politique)` possédant deux compagnies `game_ok=true`, quatre trimestres valides au dernier checkpoint et un profit AAA strictement positif, calculer `100 × profit_year(OpexAI) / profit_year(AAAHogEx)`. Pour une campagne avec bras de référence et variante, prendre ensuite la **médiane des deux ratios de la graine** (deux mondes appariés, mais résultats distincts pour AAA). Classer les graines par cette médiane croissante ; les rangs 1 correspondent aux plus faibles ratios. La médiane globale indiquée est la médiane *entre graines* de ces valeurs, **pas** le ratio des moyennes des profits. Aucun regroupement brut des ratios n'est effectué entre horizons ou configurations différents.

| Campagne et configuration | Horizon | Graines et duels exploitables | Médiane des ratios médians par graine | Trois plus faibles ratios médians |
| --- | --- | ---: | ---: | --- |
| RAIL seul, V275, référence / variante | 1972 (3 ans) | 40 ; 80 | **50,076 %** | 999533 **28,283 %** ; 1337 **34,864 %** ; 100 **36,273 %** |
| MULTI, N75-MC porte A, OFF / ON | 1974 (5 ans) | 40 ; 80 | **99,284 %** | 512 **26,214 %** ; 65537 **61,353 %** ; 781335 **64,291 %** |
| MULTI, N75-MC 20×10, OFF / ON | 1979 (10 ans) | 20 ; 40 | **60,052 %** | 512 **27,613 %** ; 65537 **42,493 %** ; 100 **49,885 %** |
| MULTI, référence 83e436cc, politique unique | 1979 (10 ans) | 20 ; 20 | **58,911 %** | 512 **20,887 %** ; 1337 **41,391 %** ; 2026 **45,824 %** |
| RAIL seul, sibling smoke **r2**, OFF / ON | 1974 (5 ans) | 4 ; 8 | **85,268 %** | 42 **56,642 %** ; 999 **68,155 %** ; 7 **102,380 %** |

**Provenance :**

- RAIL V275 : [`evidence/review/results/v275_railseul_porteA_40x3_pc_20261019.json.gz`](../evidence/review/results/v275_railseul_porteA_40x3_pc_20261019.json.gz), bundle `ebf9cc3589ae` ; protocole détaillé dans [`v275_railseul_porteA_20261019.md`](v275_railseul_porteA_20261019.md). Le bras ON est un *paquet* V207+V275, pas un effet isolé de V275.
- MULTI cinq ans : [`results/nuit75_multicargo_porteA_40x5_20261025.json`](../results/nuit75_multicargo_porteA_40x5_20261025.json), bundle `ae6b948c9b14` ; N75-MC n'a pas franchi la porte A (cf. [`nuit75_multi_cargo_20261025.md`](nuit75_multi_cargo_20261025.md)).
- MULTI dix ans : [`results/nuit75_multicargo_default_20x10_seedsfix_20261025.json`](../results/nuit75_multicargo_default_20x10_seedsfix_20261025.json), bundle `0bde1bde0de7` ; [`results/nuit75_master83e_baseline20x10_20261024.json`](../results/nuit75_master83e_baseline20x10_20261024.json), bundle `ba2012554b09`. Les deux campagnes ont des arbres et des dates de mesure distincts ; les ratios ne sont pas des deltas causaux appariés entre campagnes.
- Smoke RAIL cinq ans `r2` : [`results/rail_sibling_railseul_smoke_4x5_r2_20261102.json`](../results/rail_sibling_railseul_smoke_4x5_r2_20261102.json), bundle complet `9526d128d28e17b103123cb8ff8530347428d7942f6cace12bb86b2a26ca7ed5`, manifeste `461179095c167b42442dcfe17c3bd492b7252d8c4da3e080e8f963368904688f` ; 8/8 parties et 4/4 paires saines, zéro `failed_runs`. Le premier smoke `rail_sibling_railseul_smoke_4x5_20261102` a échoué avec l'erreur Squirrel `expected 'IDENTIFIER'` et n'entre dans aucun classement.

## Graines 512 et 1337, rangs selon le scénario

| Graine | RAIL V275, 1972 | MULTI 40×5, 1974 | MULTI 20×10, 1979 | MULTI baseline 20×10, 1979 |
| --- | ---: | ---: | ---: | ---: |
| **512** | 12/40 ; 44,513 % | **1/40 ; 26,214 %** | **1/20 ; 27,613 %** | **1/20 ; 20,887 %** |
| **1337** | **2/40 ; 34,864 %** | 14/40 ; 85,965 % | 8/20 ; 54,385 % | **2/20 ; 41,391 %** |

En classant les mêmes 40 graines par **moyenne de leurs deux rangs** RAIL V275 et MULTI 40×5, les cinq plus faibles sont : 232037 (rangs 8 et 4, moyenne 6), 512 (12 et 1, moyenne 6,5), 100 (3 et 11, moyenne 7), 841478 (7 et 7, moyenne 7), 1337 (2 et 14, moyenne 8). Cette moyenne de rangs est une *priorisation descriptive* ; l'horizon RAIL (1972) diffère de l'horizon MULTI (1974), et les configurations ne sont pas identiques.

**Lecture économique.** La graine 512 est le cas le plus régulièrement en difficulté en multimodal, tandis que 1337 est surtout critique dans le RAIL V275 et la référence multimodale dix ans. Les ratios seuls ne suffisent pas à attribuer le déficit à la croissance du rail : ils peuvent augmenter lorsque AAA régresse.

## Autopsie des trois plus faibles graines du smoke RAIL sibling `r2`

Les logs `ref_seed{graine}_r0.log` et `rail_sibling_l1_seed{graine}_r0.log`, sous [`results/rail_sibling_railseul_smoke_4x5_r2_20261102_engine/`](../results/rail_sibling_railseul_smoke_4x5_r2_20261102_engine/), conservent `RAIL_BUILD`, `RAIL_SIBLING_KEEP` et `LINE_REVENUE` (avec `probes=6`, incluant la journalisation des décisions). Le JSON de la campagne a `line_telemetry=null`, mais ces journaux fournissent une télémétrie **par ligne** indépendante.

Pour rapprocher les lignes entre deux bras, les identifiants locaux `line=` sont remplacés par la clé exacte `(cargo,src,dst)` du `RAIL_BUILD`. Les additions portent uniquement sur les événements `LINE_REVENUE mode=rail year=1974`. Ces événements sont écrits en **janvier–février 1974**, et le code [`task_report.nut`](../ai/OpexAI/task_report.nut) précise que `real_rev` et `real_prof` portent sur **l'année écoulée**, donc **1973**. Ce ne sont ni les profits 1974 de lignes, ni une ventilation comptable complète du profit annuel de la compagnie. Les lignes démarrées en 1974 n'ont pas encore cet historique annuel.

| Graine | `profit_year` Opex 1974 OFF → ON | `profit_year` AAA 1974 OFF → ON | Ratio Opex/AAA OFF → ON | Lignes RAIL avec relevé 1973 OFF → ON | Somme `real_prof` RAIL 1973 OFF → ON |
| --- | ---: | ---: | ---: | ---: | ---: |
| **42** | 1 174 166 → 1 123 713 £ (**−50 453**) | 1 894 464 → 2 190 231 £ (**+295 767**) | 61,979 → 51,306 % | 40 → 39 | 1 074 296 → 1 083 996 £ (**+9 700**) |
| **999** | 1 850 688 → 1 808 651 £ (**−42 037**) | 2 759 572 → 2 611 899 £ (**−147 673**) | 67,064 → 69,247 % | 45 → 45 | 1 680 022 → 1 684 832 £ (**+4 810**) |
| **7** | 2 060 375 → 2 095 564 £ (**+35 189**) | 2 743 800 → 1 616 096 £ (**−1 127 704**) | 75,092 → 129,668 % | 47 → 45 | 1 999 335 → 1 733 282 £ (**−266 053**) |

Les deux premières graines ont un profit propre OpexAI en recul à fin 1974 malgré un total `real_prof` des lignes légèrement supérieur en 1973. Sur 7, le ratio final semble s'envoler mais l'essentiel de sa hausse provient de la chute du profit AAA ; les profits des lignes Opex observés pour 1973 ont baissé fortement. Il est donc essentiel de séparer l'évolution des services et celle de la compagnie.

### 42 — une ligne sibling réellement posée, mais une dégradation globale

Le journal ON contient **22** événements `RAIL_SIBLING_KEEP` (13 clés distinctes). Une de ces clés correspond exactement à une construction ultérieure : **COAL, 19055 → 13978**, candidat retenu le **23/01/1973** et `RAIL_BUILD` le **28/01/1973**, avec `reuse=1`, `join_end=A`. La ligne est absente des relevés OFF comparables ; `LINE_REVENUE year=1974` indique **+17 313 £** de `real_prof` réalisé en 1973. C'est une **exposition physique positive** du mécanisme sibling, sans preuve que l'effet net sur l'empire est favorable. Aucune autre clé KEEP ne correspond à un `RAIL_BUILD` postérieur dans cette graine.

Le relevé 1973 compte 34 marchés RAIL communs, 6 propres à OFF et 5 propres à ON. Sur trois marchés communs, les plus fortes pertes ON−OFF de `real_prof` sont : **LVST 17494 → 44972**, 28 947 → 18 492 £ (**−10 455**) ; **PASS 44107 → 33442**, 105 900 → 96 552 £ (**−9 348**) ; **PASS 6457 → 22642**, 40 435 → 35 104 £ (**−5 331**). Les profits agrégés RAIL ne rendent pas compte du recul du `profit_year` compagnie au checkpoint suivant.

### 999 — candidats sibling conservés, aucune pose directement reliée

Le journal ON donne **25** `RAIL_SIBLING_KEEP` (11 clés distinctes), mais **aucun** rapprochement exact candidat → `RAIL_BUILD` postérieur. Les journaux prouvent l'examen des candidats ; ils ne prouvent aucune construction sibling sur cette graine. Les relevés 1973 ont 43 marchés RAIL communs, 2 propres à OFF et 2 propres à ON. Parmi les marchés communs : **COAL 35547 → 43953**, 26 218 → 9 097 £ (**−17 121**) ; **OIL_ 49852 → 60212**, 20 210 → 15 489 £ (**−4 721**) ; **WOOD 55024 → 30434**, 7 257 → 3 575 £ (**−3 682**). Les lignes sur les autres marchés compensent la perte dans le total ferroviaire, mais le profit propre annuel de 1974 recule de 42 037 £.

### 7 — forte recomposition des marchés, ratio amplifié par AAA

Le journal ON donne **11** `RAIL_SIBLING_KEEP` (11 clés distinctes), **aucune** pose associée par clé exacte. Seuls **26 marchés RAIL** sont communs aux relevés 1973 ; 21 figurent uniquement OFF et 19 uniquement ON. Les trois plus fortes pertes ON−OFF de `real_prof` parmi les marchés communs sont : **GOOD 16754 → 32783**, 96 967 → −2 531 £ (**−99 498**) ; **OIL_ 19603 → 46570**, 56 950 → 11 104 £ (**−45 846**) ; **PASS 40296 → 11608**, 163 509 → 121 635 £ (**−41 874**). Ici, malgré un Opex en progression de 35 189 £ en 1974, le ratio ON 129,668 % résulte surtout du recul d'AAA de 1,128 M£. Le fort renouvellement des OD empêche d'attribuer les pertes de lignes au seul sibling.

## Limites et implications de mesure

Les archives RAIL V275 et N75-MC fournissent des résultats complets par graine, mais leurs champs `line_telemetry` sont **nuls**, et les logs correspondants ne sont pas conservés dans ce worktree pour reconstruire des lignes historiques sur 512 ou 1337. La télémétrie approfondie ci-dessus provient donc du **smoke sibling r2** et n'est pas extrapolable aux cohortes 40/20 graines. Le code `task_report.nut` récupère le profit/revenu annuel de chaque ligne, mais le journal ne ventile pas PASS et MAIL à l'intérieur d'un service combiné. Les coûts d'infrastructure, l'amortissement et les autres postes comptables ne sont pas reconstitués par la somme `real_prof`.

Dans les quatre graines `r2`, le rapprochement exact des clés `RAIL_SIBLING_KEEP` avec les nouvelles `RAIL_BUILD` donne **1 pose documentée / 66 événements KEEP** (42 : 1/22 ; 999 : 0/25 ; 7 : 0/11 ; 100 : 0/8), sur un nombre plus faible de clés distinctes. Ce nombre n'est ni un taux de succès causal ni une preuve de non-constructibilité des autres candidats : des candidats peuvent être écartés au classement, à la revalidation ou par des contraintes de financement.

La qualification nocturne 40×5 devra exploiter son **JSON final**, ses contrôles de santé et ses logs de construction avant toute conclusion sur `rail_sibling`. Les ratios doivent rester descriptifs ; le gain économique se mesure sur `profit_year` d'OpexAI et sur des lignes effectivement rémunérées.
