# INVEST-STALL — investissements ferroviaires après 1973

Date : 3 novembre 2026. Worktree : `/openttd-ml/.wt_sibling_20261102`.
Étude expérimentale opt-in, **aucun défaut modifié** ; garde de valeur
explicitement ignorée (`--value-guard-max-loss-pct 100`).

## Question et définition

Pourquoi OpexAI, en rail seul, laisse-t-il des millions de livres non investis
alors que son profit stagne en 1975–1979, et quels investissements sûrs sur les
**origines déjà desservies** permettent de reprendre la croissance ?

Le gain ne se démontre pas par le seul nombre de projets considérés ou de
recharges de vivier. Pour l'adopter il faut identifier des constructions
physiques et utiles, la baisse de caisse oisive **à performance non dégradée**,
puis franchir les portes économiques appariées. Les cas `ABND`, `NOPA`,
`SITE`, `search_in_progress`, les remplacements `V257_REPLACE` et les
ajouts effectifs de rame doivent être distingués.

## Autopsie du bras de référence RAIL-LONG r2 (1973–1975)

Sources : `results/rail_long_smoke_4x6_r2_20261103.json` et
`results/rail_long_smoke_4x6_r2_20261103_engine/reference_seed*_r0.log`.
Script reproductible :
`python -X utf8 sweeps/analyse_invest_stall.py --input results --out results/invest_stall_baseline_20261103`.
Table mensuelle `results/invest_stall_baseline_20261103.csv`,
agrégat annuel `results/invest_stall_baseline_20261103.json`.

| Somme des 4 graines, référence | 1973 | 1974 | 1975 |
|---|---:|---:|---:|
| Paires examinées (événements, non uniques) | 12 159 | 14 405 | 14 112 |
| Rejets `origin_served` | 11 169 | 13 420 | 13 115 |
| Candidats générés et conservés | 553 | 520 | 597 |
| Projets rail choisis | 33 | 14 | 9 |
| Lignes construites | 24 | 11 | 3 |
| Refus `too_close_no_join` | 71 | 63 | 66 |
| Refus `search_in_progress` | 33 | 31 | 32 |
| Refus pour argent insuffisant | 2 | 0 | 0 |

Les rejets `origin_served` constituent environ 92,9 % des paires
générées en 1975 ; ce sont des observations répétées, **pas 13 115 sources
distinctes**. Le verrou principal est en amont : les producteurs déjà
desservis ne peuvent plus ouvrir de capacité ordinaire. `candidates.nut`
vers les lignes 1535–1623 et 1693–1698, ainsi que le parcours PO01C
`po01c_generators.nut` vers 190–249, retirent ces paires. Les exceptions
sibling/open restent très strictes (`candidates.nut:1397-1436`).
Une fois candidat, les contrôles de proximité (`lines.nut:317-370`,
`task_rail.nut:391-408`) et l'A* reprenable (`task_rail.nut:283-325`)
freinent encore la construction. Les abandons A* ont un cooldown fini
(`lines.nut:277-311`) ; les considérer permanents serait faux.

Le plateau à **47 trains** n'est pas un plafond global :
la graine 841478 est à 57 trains, tandis que le plafond NoAI réel
`vehicle.max_trains` est testé par `builder_rail.nut:5064-5075`.
L'histoire ordinaire permet deux trains par ligne seulement dans certaines
topologies (`task_rail.nut:639-644`). Trois graines ont atteint 47 à des
dates différentes : 17 en juin 1974, 512 vers novembre 1975, 65537 vers
octobre 1975.

## Première intervention : recharge multicargo (R1, écartée)

Réglage `invest_stall=1`, caisse ≥750 k£, au plus quatre balayages
additionnels, `OpexN75BudgetEligibleProject` avant publication ; garde
géométrique et économique conservée. Source conservée avant la nouvelle
intervention dans le bundle de `results/invest_stall_smoke_4x10_20261103_r1`.

Source figée : bundle `2a297b009a498566e413995a5090c67224a3cf18eef534d99888adfbad76743e`.
Quatre graines 17, 512, 841478, 65537 en 1v1 rail seul ; huit parties
complètes, 10 ans, sondes 6, script-debug, télémétrie mensuelle, saves.
Variant−référence en 1979 : **−79 690,25 £/an** en moyenne,
1 victoire / 3 défaites, Wilcoxon p=0,25, IC95
[−182 747,75 ; +3 927,50] £/an ; valeur des sociétés
+1,05 % en ratio des moyennes.

La trace montre peu de sorties physiques : en 1979, **157 scans
`INVEST_STALL` supplémentaires**, zéro publication admissible.
En 1975, 109 scans, seulement 3 publications. Somme annuelle des quatre
graines de `RAIL_BUILD` : références 20/13/6 en 1973/74/75,
variante 15/15/5. Ces événements répétés ne prouvent **aucun effet net**
sur les origines saturées. Le balayage multicargo ne traite donc pas
`origin_served`. Il peut en outre évincer du vivier voyageurs lors du
rechargement rail ; la variante R1 ne doit pas être adoptée.

Exploitation :
`python -X utf8 sweeps/analyse_invest_stall.py --input results --log-glob 'invest_stall_smoke_4x10_20261103_r1_engine/*_seed*_r0.log' --start-year 1973 --end-year 1979 --out results/invest_stall_smoke_4x10_20261103_r1_monthly`.

## Nouvelle orientation (mandat de l'orchestrateur)

L'option INVEST-STALL doit désormais chercher du **fret non transporté sur
des sources déjà desservies**, par production, % transporté et note de gare,
quand la trésorerie dépasse un seuil logué. Ordre : capacité sécurisée sur
ligne existante (wagons jusqu'au quai, extension du quai si possible,
deuxième rame seulement sur double voie/évitement PBS certifié) ; sinon
deuxième **gare physiquement distincte** sur la même origine vers une autre
destination, sous contrôles de couverture et anti-collision ; enfin
relaxation progressive et bornée de distance pour fret.

La présence de plusieurs trains ou le score d'une ligne ne constitue
pas une attestation de signaux : exclure les voies uniques, les voies doubles
isolées sans PBS et les dépôts/ordres invalides. Journaliser les refus et les
succès physiques sous `INVEST_STALL`; aucune modification OFF.

## Protocole de validation et décisions

État historique R1 : **3 236 tests**, un échec historique B6, six
`skipped` et deux `expected failures`. La projection OFF initiale des
six fichiers de configuration était exacte. L'évaluation finale v2-r2
et ses contrôles complémentaires figurent plus bas.

Le protocole pré-enregistré prévoyait un smoke 4×10 distinct du R1, avec référence exactement
appariée, paramètres `--cpus 9 --memory 8g --max-workers 9`,
`--mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml'`,
`--probes 6 --script-debug --line-telemetry --retain-savegames`,
désactivation des quatre familles AAA non rail et garde de valeur
neutralisée (`--value-guard-max-loss-pct 100`).
Après le smoke : porte B rail seul 20×10 `non_erosion`, puis porte A rail
seul 40×5 `gain_short` (gain ≥4 %, Wilcoxon p<0,05, borne basse IC95>0,
40 paires couvertes). Le multimodal 20×10 n'était autorisé **que si la
porte A passait**. Cette condition n'est pas satisfaite : **multimodal
non exécuté**, conformément au protocole, et non en raison d'une panne.

## Implémentation v2 (opt-in, code intégré)

### Détection commune et sûreté

`invest_stall.nut` active la sélection seulement avec `invest_stall=1`,
rail activé, année ≥1974 (relative à l'année de départ) et capital disponible
≥750 000 £. La source doit être fret, industrie valide, production mensuelle
supérieure à la capacité **mensuelle réellement estimée de toutes les rames
Opex de cette industrie et de ce cargo**, et `% transporté <75` ou
`note de gare <75 %`. **Correction v3 :** `AIStation.GetCargoRating()`
retourne déjà un **pourcentage 0..100** sous NoAI 15.3 ; le diviser de
nouveau par 255, comme le faisait v2, sous-estimait l'offre captée d'un
facteur 2,55. La capacité utilise
les véhicules réels, leur chargement, vitesse effective et temps de cycle.
Un relevé mensuel `INVEST_STALL event=gate/screen/summary` explicite l'offre,
la capacité, la note, le transporté, la trésorerie et les motifs d'exclusion.

### (a) Agrandir une rame sans dégrader sa sécurité

`invest_stall_fleet.nut` sélectionne au plus une fois par mois une ligne
fret existante, à **une seule rame**, dont le quai accepte un wagon de plus.
L'équipement doit garder la vitesse effective ; marge incrémentale positive
après coût entier de la nouvelle rame, frais et amortissement ; nouvelle
vérification au dépôt avant achat. Le moteur transactionnel V284 conserve la
rame initiale jusqu'à la validation de la remplaçante, avec logs
`screen/pick/done/skip`, annulation et état persisté. Un `Save/Load` avec
opt-in ensuite désactivé doit reprendre la transaction pour rollback.

**Limites volontaires** : aucun allongement physique de quai ajouté ; aucun
deuxième train neuf autorisé par ce chemin tant que deux voies, PBS, dépôts
et ordres ne sont pas certifiés. Les évitements ponctuels V284 sur voie
unique ne sont pas une certification. La garde historique au dépôt
`waitingNow >= wagon.capacity` reste applicable et peut limiter
l'exposition malgré une production insuffisamment transportée.

### (b) Deuxième gare physique sur une source servie

Les générateurs classiques et PO01C n'excluent plus automatiquement une
source desservie **sous ce seul opt-in** et **uniquement** pour une autre
destination non desservie, même industrie et même cargo. Depuis **v2-r2**,
la priorité à (a) bloque la nouvelle gare pour place résiduelle dans le
quai ou double voie **seulement si l'offre réellement captée par la gare
mère dépasse déjà sa capacité**. La place physique ne suffit pas à
prouver que la mère pourra charger plus de fret. `_tooClose`
n'exempte que la paire *nouvelle source A / extrémité A de la ligne mère* ;
les autres lignes, le bout B et toutes les destinations restent protégés.

Le constructeur exige une gare source **NEW** avec StationID distinct,
sans contact avec une gare dans son voisinage 3×3, site A testé en
`AITestMode`, nouveau quai de destination, tracé indépendant des voies,
gares et dépôts existants, puis recontrôle juste avant travaux et des
StationID réels après construction ; rollback si ces garanties échouent.
Un train dédié à cette ligne évite de partager une voie unique avec la
ligne mère. Les événements `origin_screen/candidate/skip`,
`site_ok/reject`, `station_built` et `build_ok` permettent de vérifier
l'exposition physique, pas seulement l'éligibilité du projet.

### (c) Élargissement des distances fret

Bonus local au maximum fret : **+20 tuiles dès 1974, +40 en 1975,
+60 en 1976 et après**, avec caisse disponible ≥750 k£ et uniquement sous
`invest_stall=1`. Ni `catalog.bounds` ni les bornes AIR/ROAD/voyageurs
ne changent. La grille V276 demeure hors de cette détente faute d'avoir
étendu son catalogue : fail-closed. Les candidatures au-delà de l'ancienne
borne loguent `INVEST_STALL event=distance_keep`.

### Contrats et projection OFF

La projection fige les sources pré-v2 du **bundle R1 réellement exécuté**
dans `sweeps/fixtures/invest_stall_v2_off_20261103.json` (hunks ancrés,
SHA avant/après). La couche de raffinement v2-r2 est figée séparément dans
`sweeps/fixtures/invest_stall_v2_r2_off_20261103.json`.
`sweeps/invest_stall_source_off.py` retire successivement v2-r2,
v2-r1 puis les changements de configuration v1, sans modifier les
empreintes historiques. Les projecteurs `invest_stall_v2_off.py`
et `invest_stall_v2_r2_off.py` vérifient les hunks et empreintes attendus,
en refusant les sources inconnues. Au total, **13 fichiers** restituent
exactement leurs SHA pré-INVEST-STALL ; la double projection OFF est
idempotente après correction de la reconnaissance des états intermédiaires.
Les modules de flotte/gate supplémentaires sont chargés mais inertes en OFF.

Contrats ciblés finaux : **34 tests INVEST-STALL** et **12 tests V284**
verts. Suite globale : **3 264 tests**, six sautés, deux échecs attendus,
**un seul échec B6 préexistant** :
`test_b6_portfolio_causality.TestB6PortfolioCausality.test_current_policy_is_observed_not_changed`.
Il compare un ancien motif textuel sans la garde `v161NetMarginalModeled`,
déjà présente avant INVEST-STALL. Cette étude ne modifie pas B6 et ne
présente pas la suite comme intégralement verte.

La continuation des transactions V284 à travers Save/Load, même si
`invest_stall` est désactivé après sauvegarde, est couverte par des
**contrats de source**. Aucun smoke dédié de rechargement au milieu d'une
transaction INVEST-STALL n'a été exécuté : cette sûreté n'est pas
dynamiquement démontrée.

## Raffinement v2-r2 : offre réellement captée par la gare mère

Le smoke **v2-r1** révélait un blocage résiduel : `fleet_headroom`
refusait une seconde gare dès qu'un wagon pouvait encore tenir dans le
quai, sans vérifier si la gare mère captait assez de fret pour remplir
la rame existante. La distinction est causale : **capacité physique
disponible ≠ capacité utile économiquement alimentée**.

Dans `ai/OpexAI/candidates.nut`,
`OpexInvestStallSecondSourceParent` évalue d'abord
`OpexInvestStallSourceGap`, puis l'offre captée estimée :

```squirrel
local ratedOffer = gap.production.tofloat() * gap.rating / 100.0;
local canLoadMoreAtMother = ratedOffer > gap.capacity;
```

La voie flotte reste prioritaire **uniquement lorsque**
`canLoadMoreAtMother` est vrai et que le quai ou une double voie présente
une marge physique. Sinon, la nouvelle gare peut être **candidate**,
mais demeure soumise à tous les contrôles de site, proximité, rails,
construction réelle et rollback. L'événement
`INVEST_STALL event=origin_fleet_blocked reason=rating_supply` rend ce
nouvel arbitrage observable. La projection OFF est inchangée.
Cette décision v2 utilisait néanmoins la **note divisée à tort par 2,55** :
elle ne doit donc pas être interprétée comme un arbitrage fondé sur une
mesure réelle correcte avant la révision v3.

## Smoke v2-r1 — rail seul, 4 graines × 10 ans

Campagne : `invest_stall_smoke_4x10_20261103_v2_r1` ;
graines **17, 512, 841478, 65537**, 8/8 parties complètes.

- Bundle : `9b7293f42eacdfa95d7ff488eec5b3b02e2e1511577e169fa965d51b0c650005`.
- Manifeste SHA : `2c106b328a763782f0e884b47658067e438524109d46e27b69592982bc39240c`.
- Résultat : `results/invest_stall_smoke_4x10_20261103_v2_r1.json` ;
  manifeste `.manifest.json`, journaux `_engine/`, sources `_bundle/`
  et sauvegardes `_saves/` avec le même préfixe dans `results/`.

Variation ON − référence en 1979 : **+74 422,75 £/an** en moyenne,
2 victoires / 2 défaites ; médiane non retenue ; Wilcoxon **p=0,625** ;
IC95 bootstrap **[−21 446,50 ; +202 203,75] £/an** ;
valeur de compagnie (ratio des moyennes) **+2,685789 %**.
Verdict runner : `diagnostic_only`, **pas une qualification**.

| Graine | Δ profit/an | Trains REF → ON |
|---|---:|---:|
| 17 | −39 254 £ | 50 → 44 |
| 512 | −3 639 £ | 52 → 49 |
| 841478 | +270 818 £ | 56 → 53 |
| 65537 | +69 766 £ | 54 → 53 |

Comptage des logs ON entre 1974 et 1979 : **2 152** refus
`origin_skip reason=fleet_headroom` ; **2 956** `fleet skip` pour
`nonpositive_margin_or_traction` ; seulement **12**
`origin_candidate`, **1** `site_ok`, **1** `station_built`,
**1** `build_ok` ; **20** `fleet pick` et **9** `fleet done`.
Il s'agit de comptes d'événements, pas d'industries distinctes.
L'exposition insuffisante justifiait le raffinement r2.

Analyse conservée :
`results/invest_stall_smoke_4x10_20261103_v2_r1_events.csv`
et `.json` (même préfixe, script
`sweeps/analyse_invest_stall_v2.py`).

## Smoke v2-r2 — rail seul, 4 graines × 10 ans

Campagne : `invest_stall_smoke_4x10_20261103_v2_r2`,
**8/8 parties complètes**.

- Bundle : `cdae36892e7408d20663a361f4f0530a6fb64255c69c59d3e09ce5f3611d7243`.
- Manifeste SHA : `17afa34b4fe85311e4eff45e3180195ff6801f99ef202863e9ba0a0ec30f471d`.
- Artefacts :
  `results/invest_stall_smoke_4x10_20261103_v2_r2.json`,
  `.manifest.json`, `_engine/`, `_bundle/`, `_saves/`
  (préfixe identique dans `results/`).

Variation ON − REF en 1979 : **+115 247 £/an** en moyenne,
médiane **+122 101 £/an**, **3 V / 1 D**, Wilcoxon **p=0,25**,
IC95 bootstrap **[+193 ; +223 447] £/an** ; valeur
**+3,512607 %** en ratio des moyennes ; `diagnostic_only`.
Quatre graines ne suffisent pas à établir un gain significatif.

| Graine | Profit REF/an | Profit ON/an | Δ profit/an | Trains REF → ON |
|---|---:|---:|---:|---:|
| 17 | 1 331 339 £ | 1 276 440 £ | −54 899 £ | 50 → 44 |
| 512 | 1 580 328 £ | 1 659 061 £ | +78 733 £ | 52 → 51 |
| 841478 | 1 771 375 £ | 2 043 060 £ | +271 685 £ | 54 → 55 |
| 65537 | 1 627 519 £ | 1 792 988 £ | +165 469 £ | 50 → 52 |

### Exposition : tentatives et constructions effectives

| Compteur ON (logs 1974–1979) | v2-r1 | v2-r2 |
|---|---:|---:|
| `origin_candidate` | 12 | 163 |
| `site_ok` | 1 | 13 |
| `station_built` | 1 | 4 |
| `build_ok` | 1 | 4 |
| `fleet pick` | 20 | 20 |
| `fleet done` | 9 | 8 |

En v2-r2, on relève en outre **1 685**
`origin_fleet_blocked reason=rating_supply`, **57**
`origin_skip reason=fleet_headroom` et **6** `site_reject`.
Les quatre `build_ok`, corroborés par `station_built`,
documentent une exposition **physique**, non de simples candidatures.
Ces événements ne permettent pas de déduire quatre industries uniques.
Le bénéfice économique n'est pas établi par le seul accroissement des
candidats (12 → 163) ou des constructions (1 → 4).

| Caisse fin 1979 | REF | ON |
|---|---:|---:|
| Graine 17 | 5 237 226 £ | 3 924 304 £ |
| Graine 512 | 6 875 910 £ | 7 259 263 £ |
| Graine 841478 | 7 435 009 £ | 8 232 004 £ |
| Graine 65537 | 6 678 467 £ | 7 940 209 £ |

La variante ne dépense davantage de caisse que sur **une des quatre
graines** à cet horizon ; elle conserve encore plusieurs millions
de livres inutilisés. Le signal de profit du smoke justifiait l'essai
de non-érosion, **pas l'adoption**.

## Porte B — `non_erosion`, rail seul 20×10 : PASS

Campagne : `invest_stall_non_erosion_20x10_20261103_v2_r2`,
**20/20 paires, 40 parties**, référence et variante sous le bundle
v2-r2 `cdae36892e7408d20663a361f4f0530a6fb64255c69c59d3e09ce5f3611d7243`.
Manifeste SHA :
`dcf76c75f71f48a0c9fc1b98342b8b016adc014fc4923f7e7fb269c1c817bf11`.
Sources : `results/invest_stall_non_erosion_20x10_20261103_v2_r2.json`,
`.manifest.json`, `_engine/`, `_bundle/` (préfixe identique).

| Statistique ON − REF en 1979 | Résultat |
|---|---:|
| Δ moyen `profit_year` | +35 903,1 £/an |
| Médiane | +79 722,5 £/an |
| Victoires / défaites / égalités | 14 / 6 / 0 |
| Wilcoxon p | 0,38837623596191406 |
| IC95 bootstrap | [−80 732,8 ; +143 618,2] £/an |
| Ratio des moyennes de valeur de compagnie | −2,114766 % |
| Verdict officiel | **`pass`** |

La porte `non_erosion` est unilatérale : elle échoue si la **borne
supérieure** de l'IC95 est négative, ce qui n'est pas le cas. Le seuil
de +4 % n'est pas une condition de la porte B. La garde de valeur
est bien neutralisée à **100 %** pour cette étude. Ce PASS **ne
constitue pas une preuve de gain positif significatif**.

| Moyennes des 20 graines, fin 1979 | REF | ON |
|---|---:|---:|
| Profit/an | 1 754 380 £ | 1 790 283 £ |
| Trésorerie | 6 625 525 £ | 6 435 411 £ |
| Véhicules | 55,95 | 54,80 |
| Gares | 82,85 | 84,45 |

Avec **−190 k£** de caisse, **+1,6 gare** et **−1,15 véhicule**
en moyenne, la politique ne débloque pas le plateau du parc ferroviaire.
La trésorerie résiduelle reste très abondante (≈**6,4 M£**).

## Porte A — `gain_short`, rail seul 40×5 : FAIL PRIMARY

Campagne finale : `invest_stall_gain_short_40x5_20261103_v2_r2`,
**40/40 paires, 80/80 parties**, même bundle v2-r2.
Manifeste SHA :
`4ae80f02f3b6e2ac779de8425ca6d1cc868b4795b9c271afc00815e9888ff251`.
Artefacts : `results/invest_stall_gain_short_40x5_20261103_v2_r2.json`,
`.manifest.json`, `_engine/`, `_bundle/` (préfixe identique).

| Critère | Mesure officielle | Règle | Résultat |
|---|---:|---|---|
| Δ moyen `profit_year` | +5 533,725 £/an | ≥+63 384,16 £/an (+4 %) | Échec |
| Médiane Δ | +4 230,5 £/an | Informatif | — |
| Victoires / défaites / égalités | 20 / 20 / 0 | Informatif | — |
| Wilcoxon p | 0,6655508074145473 | <0,05 | Échec |
| IC95 bootstrap | [−72 823,425 ; +78 315,05] £/an | Borne basse >0 | Échec |
| Couverture | 40/40 paires | 40/40 | OK |
| Valeur compagnie | −2,19547 % | Garde ignorée (`100`) | Non bloquante |

**Verdict officiel du runner : `fail_primary`.**
Les 80 simulations ont été exécutées et les 40 paires sont couvertes,
mais la rubrique `summary` distingue, **dans chaque politique**,
**30 `status=complete`** et **10 `status=stagnation_suspect`**.
Ces statuts de santé sont à signaler et n'ont pas empêché le verdict ;
il serait inexact de prétendre que les 40 parties de chaque bras
portent toutes le statut `complete`.

| Moyennes des 40 graines, fin 1974 | REF | ON |
|---|---:|---:|
| Profit/an | 1 584 604 £ | 1 590 138 £ |
| Trésorerie | 400 643 £ | 357 941 £ |
| Véhicules | 50,90 | 49,55 |
| Gares | 76,67 | 75,80 |

Malgré **−42,7 k£** de trésorerie, la variante possède **−1,35
véhicule** et **−0,87 gare** en moyenne. L'effet annuel de
**+5,5 k£**, non significatif, reste très inférieur à l'objectif
pré-enregistré de **+63,4 k£**. **La porte A est fermée.**

## Limites physiques, économiques et attribution

- L'allongement **dans les quais existants** est implémenté via V284 ;
  l'allongement **physique des quais** ne l'est pas.
- Aucune **deuxième rame** nouvelle sans voie double / évitement / PBS
  et circulation certifiés : les anciennes boucles de voie unique
  ne valent pas certification. Cette exclusion est volontaire.
- La seconde gare impose une station et un corridor physiquement
  indépendants ; le générateur V276 et les destinations déjà servies
  ne sont pas ouverts par cette étude.
- Les transactions Save/Load sont couvertes par des contrats, **pas
  par un smoke de rechargement en pleine transaction**.
- Les volumes de candidatures sont des **événements répétables**.
  Seuls les `station_built` / `build_ok` attestent ici une construction ;
  cela ne garantit ni profit futur ni résolution durable de saturation.
- Les gares progressent à dix ans, mais les véhicules reculent en
  moyenne aux deux portes. Le **plateau d'investissement ferroviaire**
  n'est donc pas résolu économiquement ni structurellement.

## Reproductibilité et provenance

Plateforme : **Windows / PowerShell 5.1**, OpenTTD **15.3**, NoAI
**15**, OpenGFX **7.1** ; Docker `openttd-lab:latest`,
digest `sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`.
Worktree `/openttd-ml/.wt_sibling_20261102`,
branche `exp/rail-sibling-20261102`, HEAD
`99f29d9c858f390de6193978a4f12d3fbdb48127` ;
le worktree était volontairement dirty, sans commit de l'étude.
Les bundles et manifests ci-dessus figent les sources réelles des
campagnes ; le seul SHA Git ne représente pas cet arbre expérimental.

Commandes **historiques, déjà exécutées**. Ne pas relancer sous ces
identifiants ni écraser les résultats ; pour une nouvelle expérience,
utiliser un nouveau nom de campagne et un nouvel `--out`.

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,invest_stall=1]'
$aaa = @(
  '--aaahogex-setting','disable_veh_roadveh=1',
  '--aaahogex-setting','disable_veh_tram=1',
  '--aaahogex-setting','disable_veh_ship=1',
  '--aaahogex-setting','disable_veh_aircraft=1'
)
$common = @(
  '--mount-root','C:\Users\jr\vscode\openttd-ml\openttd-ml',
  '--cpus','9','--memory','8g','--max-workers','9',
  '--value-guard-max-loss-pct','100',
  '--start-year','1970','--map-size','8','--repeats','1',
  '--primary-metric','profit_year'
)

# Smoke v2-r2 — 4 graines × 10 ans
python -X utf8 sweeps/run_c66_reference.py `
  --campaign invest_stall_smoke_4x10_20261103_v2_r2 `
  --policy-id reference --variant-policy-id invest_stall_v2_r2 `
  --reference $ref --variant $on --decision-rule non_erosion `
  --min-useful-primary-delta-pct 4 --required-seeds 4 `
  --required-years 10 --years 10 --seeds 17 512 841478 65537 `
  --probes 6 --script-debug --line-telemetry --line-telemetry-monthly `
  --retain-savegames results/invest_stall_smoke_4x10_20261103_v2_r2_saves `
  --out results/invest_stall_smoke_4x10_20261103_v2_r2.json `
  @common @aaa

# Porte B — 20 graines canoniques × 10 ans
python -X utf8 sweeps/run_c66_reference.py `
  --campaign invest_stall_non_erosion_20x10_20261103_v2_r2 `
  --policy-id reference --variant-policy-id invest_stall_v2_r2 `
  --reference $ref --variant $on --decision-rule non_erosion `
  --min-useful-primary-delta-pct 4 --required-seeds 20 `
  --required-years 10 --years 10 --probes 6 --script-debug `
  --line-telemetry `
  --out results/invest_stall_non_erosion_20x10_20261103_v2_r2.json `
  @common @aaa

# Porte A — 40 graines canoniques × 5 ans
python -X utf8 sweeps/run_c66_reference.py `
  --campaign invest_stall_gain_short_40x5_20261103_v2_r2 `
  --policy-id reference --variant-policy-id invest_stall_v2_r2 `
  --reference $ref --variant $on --decision-rule gain_short `
  --min-useful-primary-delta-pct 4 --required-seeds 40 `
  --required-years 5 --years 5 --probes 6 --script-debug `
  --line-telemetry `
  --out results/invest_stall_gain_short_40x5_20261103_v2_r2.json `
  @common @aaa
```

La v2-r1 possède son propre bundle figé, différent de v2-r2 ;
les sources courantes ne doivent pas être prétendues identiques à ce
premier smoke. Les journaux, sauvegardes, manifests, JSON et bundles
existants sont conservés sans modification.

Contrôles de source et de tests réalisés :

```powershell
python -X utf8 sweeps/invest_stall_source_off.py
python -X utf8 -m unittest discover -s sweeps -p 'test_invest_stall*.py' -q
python -X utf8 -m unittest discover -s sweeps -p 'test_v284_rail_growth.py' -q
python -X utf8 -m unittest discover -s sweeps -p 'test_*.py' -q
git diff --check
```

Résultats v2-r2 : **13 SHA OFF exacts**, **34/34** contrats INVEST-STALL,
**12/12** V284 ; suite globale **3 264 tests**, seul B6 historique
en échec. Les vérifications non destructives finales sont consignées
à la clôture, sans nouvelle exécution des benchmarks moteur.

## INVEST-STALL v3 — note de gare corrigée, smoke r2, clôture

La v3 corrige l'unité de `AIStation.GetCargoRating()` dans
`ai/OpexAI/invest_stall.nut` : la valeur **0..100 est conservée telle
quelle**, avec rejet des mesures hors plage. En v2, l'expression
`rawRating * 100 / 255` transformait par exemple **75 % en 29 %**.
Cela faussait à la fois le filtrage `pct >= 75 && rating >= 75`,
l'offre de la gare mère (`ratedOffer`) et la rentabilité marginale des
wagons. Les chiffres de v2-r2 restent ceux de son bundle figé ; les
résultats de v3 ne les remplacent pas rétrospectivement.

Le smoke **v3 r2**, `results/invest_stall_v3_smoke_4x10_20261103_r2.json`,
comporte **4/4 paires complètes, 8/8 parties saines**, sur dix ans
(1970–1979 ; graines 17, 512, 841478, 65537), avec la même référence
rail seule au sein de son bundle. Source figée SHA-256 :
`2d54f780181da9bfc1d6d68389c6f1df7ec21d8f9a47af0a0eed308acb1fb9a9` ;
manifeste SHA-256 :
`0051c66234a873b5141521b2c0aa641297b1d6a47ea6a15bbcd2d26fcbef7a0c`.
Journaux dans `results/invest_stall_v3_smoke_4x10_20261103_r2_engine/`,
sauvegardes dans le répertoire correspondant `_saves/`.

| Profit propre Opex en 1979 | REF | v3 ON | Delta |
|---|---:|---:|---:|
| Moyenne sur 4 graines | 1 649 970,25 £/an | 1 671 650,75 £/an | **+21 680,50 £/an** |
| Graine 17 | 1 440 687 | 1 295 444 | −145 243 |
| Graine 512 | 1 580 328 | 1 606 743 | +26 415 |
| Graine 841478 | 1 957 732 | 2 030 268 | +72 536 |
| Graine 65537 | 1 621 134 | 1 754 148 | +133 014 |

Le JSON figé relève **3 victoires / 1 défaite** (et non 2/2),
Wilcoxon **p=0,875**, IC95 bootstrap de la moyenne
**[−90 798,25 ; +106 364,25] £/an**. Verdict du runner :
**`fail_primary`**. Le gain moyen d'environ **+1,31 %** de la
référence est inférieur au seuil +4 %, et l'intervalle inclut zéro.

| Indicateur fin 1979, moyenne des quatre graines | REF | v3 ON | ON − REF |
|---|---:|---:|---:|
| Caisse | 6 559 565 £ | 6 812 940 £ | +253 375 £ |
| Véhicules | 53,50 | 50,75 | −2,75 |
| Gares | 79,25 | 78,00 | −1,25 |

Dans les journaux ON de v3 r2 entre 1974 et 1979,
**34 `origin_candidate`**, **9 `site_ok`**, **6 `station_built`**,
**5 `build_ok`**, **97 `fleet pick`** et **59 `fleet done`** sont
observés. Ce sont des événements : des `station_built` peuvent être
suivis d'un échec avant ligne productive, et un renouvellement de rame
ne constitue pas nécessairement un véhicule supplémentaire en service.
Le parc final de la variante est plus petit et **6,81 M£ restent
disponibles**. La variante v3 r2 demeure **économiquement neutre à
l'échelle de ce smoke** et n'apporte aucune preuve de déblocage de
l'investissement ferroviaire. Les portes supplémentaires sont fermées ;
aucune qualification ni adoption par défaut.

## Verdict final — NO-GO d'adoption

**INVEST-STALL v1 multicargo : NO-GO** (−79,7 k£/an au smoke).
**v2-r1 : exposition physique insuffisante** (une construction).
**v2-r2 : mécanisme effectivement exposé** (quatre `build_ok` dans le
smoke), avec signal moyen **+115,2 k£/an** sur quatre graines, mais
sans confirmation statistique.

**Porte B 20×10 : PASS de non-érosion** (+35,9 k£/an, IC95 incluant
zéro). **Porte A 40×5 : `fail_primary`** (+5,5 k£/an,
p=0,66555, IC95 incluant zéro). La politique **n'est pas
économiquement qualifiée pour l'adoption** : ne pas changer le
réglage par défaut, qui reste **`invest_stall=0`** aux quatre
difficultés. Le code expérimental demeure disponible sous opt-in.

**v3 : correction réelle de l'échelle des notes de gare, mais smoke
r2 neutre** (+21,7 k£/an, 3 V/1 D, p=0,875) ; aucune porte nouvelle.

**Le multimodal 20×10 n'a pas été exécuté**, exclusivement parce que
le résultat de la porte A ne satisfait pas la condition d'ouverture.
Les limitations physiques et le risque résiduel de transactions
Save/Load non vérifiées en smoke dédié restent explicitement connus.
Aucune autre politique (RDS, V190, SEARCH-PRIO, RAIL-LONG) n'est
relancée ni modifiée à cette clôture.

INVEST-STALL TERMINÉ
