# P0 RAIL ready→dépense — diagnostic apparié 40 graines × 5 ans (10/10/2026)

## Objet et protocole

Prolongement **diagnostique** de la porte A 40×3 (rejetée, voir
`rail_ready_readmission_gateA_20261009.md`), afin de sélectionner des
graines défavorables à autopsier **sans chercher une variante opportuniste**.

- Référence `OpexAI[rail_ready_readmission=0]` ; variante
  `OpexAI[rail_ready_readmission=1]`. Aucun autre réglage différenciant.
- 40 graines canoniques, une réalisation/grain, 1970–1974,
  deux politiques, carte partagée avec AAAHogEx : **80/80 parties
  terminées et saines** ; 40/40 comparaisons complètes.
- Source : worktree isolé
  `.scratch_rail_ready_readmission_A2`, code congelé SHA256
  `250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8`,
  **strictement identique au 40×3 A2**. Docker `openttd-lab:latest`,
  10 CPU, 10 workers maximum, une seule campagne.
- Identifiant :
  `rail_ready_readmission_diag_40x5_20261010_r1`.
  `--script-debug` pour traces NoAI et `--line-telemetry` pour
  reconstitution annuelle des lignes à partir des sauvegardes ;
  cette dernière est du post-traitement et n'influence pas les décisions.
- V102 `gain_short`, 40 paires et cinq ans : comparaison rétrospective
  à la même règle de gain +4 % / p de Wilcoxon bilatéral < 0,05 /
  IC95 bootstrap de la moyenne entièrement positif / valeur de compagnie
  ≥95 % de la référence. **Cet horizon n'annule pas le rejet 40×3**.

## Verdict global à cinq ans

| Mesure variante − référence | Résultat |
| --- | ---: |
| Profit annuel terminal (1974), moyenne | **+29 385,63 £/an** |
| Médiane | +51 873,50 £/an |
| Victoires / défaites / égalités | **28 / 10 / 2** |
| IC95 bootstrap (20 000 tirages, seed0) | **[−33 434,45 ; +88 655,10] £/an** |
| Test des signes | p = 0,005098 |
| Wilcoxon bilatéral (critère obligatoire V102) | **p = 0,053049** |
| Gain minimal +4 % de la référence (1 930 303 £/an) | **+77 212,12 £/an** |
| Valeur de compagnie : ratio des moyennes | **1,011586** (+1,1586 %) |
| Verdict harnais | **`fail_primary`** |

Le nombre de victoires est élevé, mais les pertes sur certaines graines
sont importantes. Le **test des signes seul ne suffit pas** : Wilcoxon,
borne inférieure bootstrap et seuil de gain utile ne satisfont pas
le contrat. La garde de valeur de compagnie est satisfaite.

| Année | Delta de profit annuel moyen (£/an) | V/D/E |
| --- | ---: | --- |
| 1970 | −626,90 | 3/3/34 |
| 1971 | −72,95 | 10/13/17 |
| 1972 | −2 498,20 | 17/15/8 |
| 1973 | +39 718,57 | 19/15/6 |
| 1974 | +29 385,63 | 28/10/2 |

## Graines à analyser en priorité : pire profit annuel 1974

Classement par **delta de profit annuel OpexAI (ON − OFF)**, non par
profit OpexAI − AAAHogEx.

| Graine | Δ profit 1974 (£/an) | Δ valeur 1974 (£) | Évolution du delta 1972 → 1973 → 1974 (£/an) |
| --- | ---: | ---: | --- |
| **746035** | **−525 183** | −799 163 | −131 370 → −239 585 → −525 183 |
| **424242** | **−481 430** | −1 170 286 | −310 572 → −265 500 → −481 430 |
| **8191** | **−372 964** | −692 943 | −272 379 → −117 034 → −372 964 |
| 73 | −234 443 | −634 440 | −178 044 → −68 953 → −234 443 |
| 999 | −227 729 | −1 060 706 | −273 799 → −285 291 → −227 729 |
| 515222 | −210 145 | −147 597 | +166 915 → −84 872 → −210 145 |
| 12345 | −151 691 | −406 694 | +12 829 → −249 180 → −151 691 |

Point d'attention, **les raisons peuvent être différentes selon la
graine**. À fin 1974, la télémétrie brute permet de compter :

- Seed **746035** : 4 lignes RAIL OFF contre **6 ON** ;
  57 lignes AIR dans les deux bras, 1 ligne ROAD OFF contre 2 ON.
  Une perte malgré *plus* de lignes RAIL ne s'explique donc pas par
  une simple absence d'expansion ferroviaire.
- Seed **424242** : 7 lignes RAIL OFF contre **5 ON**,
  55 AIR OFF contre **51 ON**.
- Seed **8191** : 2 RAIL dans les deux bras ;
  53 AIR OFF contre **42 ON**.

Ces décomptes sont **des observations finales**, pas une preuve
du premier mécanisme causal. Une ligne différente peut résulter d'une
divergence économique antérieure. Les comptages n'ont pas vocation à
être additionnés aux profits de compagnie.

## Autopsie rétrospective des trois pires graines (sans nouveau banc)

Exploitation de `line_telemetry.snapshots` du JSON 40×5, uniquement
`arm=OpexAI` pour les chiffres qui suivent. Une ligne est un service
reconstitué depuis les ordres des véhicules, regroupé par mode ; les
`market_key` AIR comparent les mêmes **paires de villes** entre bras.
La somme des `profit_this_year_gbp` est un **profit observé des véhicules
au 1er décembre**, pas le `profit_year` de la compagnie au terme de
l'exercice. Elle n'inclut pas tous les postes comptables ; les recettes
et frais d'exploitation distincts sont indisponibles dans ce schéma.

| Graine, fin 1974 | Profit véhicules AIR OFF → ON (£) | Δ AIR (£) | Profit véhicules RAIL OFF → ON (£) | Δ RAIL (£) | Flotte AIR OFF → ON |
| --- | ---: | ---: | ---: | ---: | ---: |
| **746035** | 2 365 640 → 1 918 007 | **−447 633** | 33 124 → 14 768 | −18 356 | 124 → 128 |
| **424242** | 2 407 892 → 1 933 614 | **−474 278** | 108 854 → 43 709 | −65 145 | 109 → 96 |
| **8191** | 1 889 229 → 1 578 398 | **−310 831** | 62 419 → 49 769 | −12 650 | 101 → 72 |

### Marchés AIR conservés ou remplacés, fin 1974

| Graine | Marchés communs | Uniquement OFF | Uniquement ON | Δ profit sur les communs (£) | Profit OFF des marchés perdus (£) | Profit ON des nouveaux marchés (£) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **746035** | 43 | 14 | 14 | **−327 714** | 381 768 | 261 849 |
| **424242** | 24 | 31 | 27 | **−343 222** | 868 366 | 737 311 |
| **8191** | 18 | 35 | 24 | **+37 279** | 784 280 | 436 170 |

Les arrondis des profits par marché peuvent différer d'une unité de
ceux des sommes avant arrondi. La décomposition est **descriptive** :

- **746035** : même nombre de lignes AIR (57/57), mais seulement
  **43 marchés communs** ; 14 marchés remplacés par 14 autres.
  La perte AIR vient surtout des marchés conservés (−327 714 £),
  et non d'une baisse de capacité globale : 124 → 128 appareils,
  capacité PASS 27 280 → 28 160, MAIL 4 960 → 5 120.
  Cela ne démontre ni une surcapacité causale, ni une baisse de ratings :
  il manque les revenus par ligne et les décisions de redéploiement.
- **424242** : 24 marchés AIR seulement sont communs, avec −343 222 £
  de profit sur ceux-ci et un remplacement de marchés défavorable ;
  la flotte AIR passe de 109 à 96 appareils. Les 3 marchés RAIL de 1971
  sont toutefois **identiques, gares aux mêmes tuiles**, malgré le
  remaniement AIR massif dès cette année-là.
- **8191** : seulement 18 marchés AIR communs fin 1974, **sur lesquels
  ON fait +37 279 £**. Le différentiel négatif vient surtout du
  portefeuille de marchés (OFF 35 marchés absents d'ON, contre
  24 marchés propres à ON) et des appareils AIR 101 → 72.
  Le total des lignes RAIL reste 2/2, mais cela ne prouve pas que les
  décisions ferroviaires aient été identiques.

### Première divergence observable et limite causale

Les captures ont lieu seulement **le 1er décembre de chaque année** :

- **746035** : décembre 1970 identique sur les 8 marchés AIR et leur
  profit véhicule ; décembre 1971 : 38/38 marchés AIR, **33 communs**,
  5 remplacés de chaque côté, pendant que les 2 marchés RAIL et leurs
  tuiles de gares restent identiques ; en 1972 la chute du profit des
  véhicules AIR ON−OFF atteint environ −237 k£.
- **424242** : décembre 1970 identique sur les 8 marchés AIR ;
  décembre 1971 : **38 AIR OFF contre 34 ON, dont 19 communs**, perte
  AIR ON−OFF de l'ordre de −309 k£, mais les 3 marchés RAIL et leurs
  gares sont encore identiques.
- **8191** : **décembre 1970** comporte déjà un marché AIR différent
  dans chaque bras (7 marchés communs sur 8), sans ligne RAIL à cette
  date ; la différence de profit véhicules AIR est alors +21 k£.
  En 1971 les 2 marchés RAIL sont encore communs, mais seuls
  15 marchés AIR sur 36 OFF / 34 ON le sont.

Ces observations **ne donnent pas le premier jour ni la décision causale**.
Les 6 journaux moteur des trois graines ne contiennent aucun événement
`RAIL_READY_READMISSION` ni `RAIL_READY_ADMISSION` : dans le code gelé,
le premier n'est écrit que sous `DECISION_LOG` et le second sous
`rail_ready_admission_shadow`, tous deux à **0 par défaut**. Absence
de journal **ne signifie pas absence de report**. `retained_savegames`
est `null` et les captures annuelles ne permettent pas la reconstruction
intra-annuelle. Les champs `observed_opcodes_total` et
`selection_kopcodes_samples` sont `null` dans les résultats de ces
graines : **coût en opcodes non mesuré**.

L'inspection du chemin de code gelé (`task_projects.nut`, vers
1562–1596 et 1790–1889) confirme que la variante prend
`_projects.best[0]`, vérifie `profitAnnual > 0` et le devis finançable,
puis diffère un A* primaire prêt hors préparation C121 si son rang est
différent de zéro. Elle ne vérifie **ni la constructibilité réelle du
projet concurrent**, ni une comparaison fraîche et directe de son
profit avec le RAIL prêt. `readyReadmissionHeadKey` interdit un second
report pour **la même** tête, mais une autre tête permet un nouveau
report. La passe de portefeuille suit ensuite la garde de consommation.
Ce sont des **risques dans le code**, pas des causes prouvées sur ces
trois graines.

**Prochaine preuve manquante :** instrumenter *uniquement* le point
`A* prêt → report ou consommation`, la clé et le rang de la tête,
la clé du RAIL, les devis/caisse, puis le **résultat réel** du premier
projet essayé pendant la passe (`built` / rejet / cash / pending), le
devenir de la recherche RAIL et le coût en opcodes. Activer cette
instrumentation séparément, OFF au défaut, sur **quelques graines
ciblées OFF/ON de même source gelée**, avant toute autre campagne large.
Ne pas inférer cette chaîne à partir des seules statistiques 1974.

## Preuves conservées, autopsie suivante

Les données brutes ont été déplacées lors du nettoyage dans
`results/rail_ready_readmission_A2/` (archive locale ignorée par Git).
Le [classement des graines](archives/rail_ready_readmission_A2_20261010_seed_ranking.csv)
et le [manifest de la campagne](archives/rail_ready_readmission_A2_20261010.manifest.json)
sont aussi conservés dans la documentation versionnable. L'archive locale contient :

- `rail_ready_readmission_diag_40x5_20261010_r1.json` :
  80 parties, séries annuelles, comparaison statistique,
  **800/800** captures annuelles de télémétrie `line_telemetry.snapshots`
  sans erreur.
- `rail_ready_readmission_diag_40x5_20261010_r1_seed_ranking.csv` :
  classement des **40 graines**, cinq deltas annuels, capital,
  emplacements aéroportuaires et nombres de lignes par mode fin 1974.
- `rail_ready_readmission_diag_40x5_20261010_r1.manifest.json`,
  `_bundle/`, `_engine/` et `.jsonl` : empreintes, code exécutable,
  logs moteur et checkpoints originaux.

**Autopsie initiale terminée :** les marchés AIR et la chronologie
annuelle distinguent trois mécanismes observables ; la cause de chaque
report RAIL initial reste à démontrer par des événements de décision.
Si une reproduction ciblée est autorisée, garder des sources OFF/ON
appariées, activer une instrumentation de diagnostic OFF par défaut et
mesurer également son coût en opcodes.

**Décision :** aucun retour sur le rejet V102 initial, aucun nouveau
réglage adopté, aucune porte B, aucun commit/push.
