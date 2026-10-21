# Calibration par cargo et quartile de distance — 21 octobre 2026

Source : 40 parties solo et 40 parties duel, de 1970 à 1980, produits par
`sweeps/run_calibration_pc.sh` (bundle du commit `4eb307d0`).
Recalcul hors ligne avec `sweeps/analyse_calibration_quartiles.py`.

Sorties exhaustives (348 combinaisons avant consolidation, 347 lignes présentes) :

- `results/calibration_pc_20261021/results/calibration_cout_profit_quartiles_20261021.csv`
- `results/calibration_pc_20261021/results/calibration_cout_profit_quartiles_20261021.json`
- `results/calibration_pc_20261021/results/calibration_cout_profit_quartiles_20261021.md`

## Définition des mesures

- Quartiles de distance **par mode**, calculés sur toutes les constructions
  (chaque ligne compte une fois) des deux campagnes, seuils communs aux bras :
  **AIR** 169 / 189 / 213, **RAIL** 90 / 127 / 172,
  **ROAD** 25,25 / 33 / 40,75 (unités `dist` des journaux moteur).
  La borne supérieure appartient au quartile inférieur.
- **Coût de construction** : `RAIL_BUILD` / `ROAD_BUILD` apparié au
  `PROJECT_CHOSEN` de mêmes mode, origine et destination ;
  on compare coût journalisé / coût prédit, seulement si les deux sont > 0.
  Les coûts négatifs de ROAD sont donc exclus, pas convertis artificiellement
  en dépenses positives. AIR et WATER ne publient pas de coût physique : leur
  `*_BUILD cost` est un **devis**, impropre à cet exercice.
- **Profit annuel** : `LINE_REVENUE`, âge ≥ 2, observation
  `real_prof * vehicules_initiaux / vehs` / `pred_prof` brut avant C70.
  Le prédicteur doit être > 0 ; les profits réels négatifs sont gardés.
  Un ratio de 0,25 = seulement un quart du profit promis.
- Les coûts sont pondérés par construction, les profits par ligne-année.
  La sortie CSV comporte également `lines` (lignes indépendantes
  identifiables) et `equal_line_median_ratio`, où chaque ligne pèse une fois.
  **n est un effectif de constructions ou de lignes-années, pas un nombre
  d'expériences indépendantes.** Les cellules à moins de 20 observations
  (et particulièrement moins de 5) restent fragiles.

## 1. Coûts — séparation stricte des profits

Médiane coût réel / prédit, en **duel** ; format `ratio (n constructions)`.

| RAIL cargo | Q1 ≤90 | Q2 91–127 | Q3 128–172 | Q4 ≥173 |
|---|---:|---:|---:|---:|
| COAL | 1,18 (41) | 1,35 (51) | 1,50 (41) | 1,61 (57) |
| GRAI | 1,31 (36) | 1,50 (50) | 1,61 (49) | 1,78 (44) |
| IORE | 1,17 (22) | 1,41 (54) | 1,54 (56) | 1,70 (38) |
| OIL_ | 1,23 (25) | 1,46 (33) | 1,62 (39) | 1,77 (32) |
| WOOD | 1,12 (20) | 1,38 (38) | 1,53 (42) | 1,62 (47) |
| LVST | 1,35 (11) | 1,55 (17) | 1,82 (11) | 1,78 (22) |
| PASS | 1,15 (88) | 1,60 (3) | — | — |
| GOOD | 0,99 (5) | 1,60 (3) | 1,47 (14) | 1,32 (17) |
| **TOUS** | **1,22 (248)** | **1,43 (254)** | **1,56 (254)** | **1,69 (258)** |

En solo, les ratios RAIL tous cargos Q1–Q4 sont respectivement
**1,19 / 1,37 / 1,51 / 1,59** (985 constructions exploitables).
Les 1 014 constructions exploitables du duel montrent un déficit croissant
du devis de construction avec la distance ; 24 291 £ d'erreur absolue
médiane par construction au global.

Pour ROAD, il n'existe que 49 coûts exploitables en duel,
avec les médianes Q1–Q4 **1,04 (14) / 1,33 (10) / 1,17 (17) / 1,11 (8)**.
Le détail cargo × quartile est présent dans le CSV, mais la majorité des
cellules ne comptent que 1 à 8 constructions : aucune calibration
par cellule ROAD des coûts ne serait défendable sur ces seuls cas.

## 2. Profit annuel — indépendamment des coûts

Médiane profit réel / prédit brut, en **duel** ; format
`ratio (n lignes-années)`.

| Cargo / mode | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| **AIR PASS** | **0,25 (2 833)** | **0,26 (3 017)** | **0,24 (3 116)** | **0,23 (3 306)** |
| RAIL COAL | 0,66 (458) | 0,81 (318) | 1,12 (211) | 1,14 (266) |
| RAIL GRAI | 0,86 (223) | 0,82 (267) | 1,07 (259) | 1,10 (205) |
| RAIL IORE | 0,88 (181) | 1,07 (311) | 1,25 (313) | 1,28 (181) |
| RAIL OIL_ | 0,76 (124) | 0,95 (160) | 1,13 (182) | 1,34 (151) |
| RAIL WOOD | 0,80 (261) | 1,14 (220) | 1,22 (233) | 1,21 (237) |
| RAIL LVST | 0,75 (64) | 0,86 (82) | 1,10 (44) | 1,10 (77) |
| RAIL PASS | 1,28 (289) | — | — | — |
| RAIL GOOD | 0,25 (29) | 0,98 (16) | 0,58 (58) | 0,58 (59) |
| **RAIL TOUS** | **0,76 (1 629)** | **0,96 (1 385)** | **1,14 (1 309)** | **1,16 (1 179)** |
| ROAD PASS | 0,09 (45) | 0,20 (34) | 0,10 (53) | 0,38 (7) |
| ROAD MAIL | 0,05 (14) | — | 0,18 (7) | 1,06 (14) |
| ROAD COAL | 1,06 (7) | 1,35 (7) | 1,71 (10) | — |
| ROAD GRAI | — | 1,13 (19) | 1,82 (6) | 2,05 (11) |
| ROAD IORE | 0,46 (12) | — | 1,43 (14) | 1,47 (27) |
| ROAD WOOD | 0,96 (14) | 1,71 (14) | 1,60 (20) | 2,16 (14) |
| **ROAD TOUS** | **0,21 (92)** | **0,88 (81)** | **0,87 (121)** | **1,54 (78)** |

Les cellules rares RAIL STEL/VALU, ainsi que ROAD OIL_ et toutes les
combinaisons sans observation, figurent dans le CSV exhaustif.

### Comparaison solo / duel et amplitude absolue

| Mesure globale | Solo : médiane et n | Duel : médiane et n | Erreur absolue médiane duel |
|---|---:|---:|---:|
| Coût RAIL | 1,438 (985) | 1,473 (1 014) | 24 291 £/construction |
| Coût ROAD, positives seules | 1,251 (32) | 1,168 (49) | 5 440 £/construction |
| Profit AIR PASS | 0,313 (15 608) | 0,242 (12 272) | 71 274 £/ligne-année |
| Profit RAIL | 1,166 (5 857) | 0,990 (5 502) | 8 581 £/ligne-année |
| Profit ROAD | 0,404 (350) | 0,868 (372) | 2 712 £/ligne-année |

La comparaison solo / duel ne mesure pas un traitement causal isolé :
l'IA concurrente modifie la demande, la sélection des lignes et leur âge.
Les ratios sont des diagnostics du modèle **brut**, pas d'une table C70
appliquée au moment du classement des projets.

## Qualité et couverture des données

- 40 parties par bras.
- Constructions `RAIL_BUILD` : 1 070 solo / 1 088 duel ;
  coûts appariés valides : 985 / 1 014.
- Constructions `ROAD_BUILD` : 59 / 59 ;
  coûts positifs : 32 / 49 ; 27 / 10 observations à coût réel non positif.
- AIR_BUILD : 2 492 / 1 932, sans coût physique vérifiable
  dans ces journaux.
- Observations profit non appariables faute de `vehs` valide : 123 / 232.
  Profits prédits non positifs et non exploitables dans le ratio : 60 / 57.

## Implications techniques

1. **Ne pas corriger tous les coûts RAIL d'un même multiplicateur.**
   Le biais suit nettement la distance ; une correction prudente
   par quartile, puis par cargo si échantillon suffisant, serait plus logique.
2. **Ne pas apprendre le profit AIR avec un simple facteur issu d'une
   économie sans concurrence** : le solo vaut environ 0,30–0,33 selon
   le quartile ; le duel vaut 0,23–0,26. Tester la calibration
   solo → duel sans réinterpréter cela comme un effet purement causal.
3. **Séparer coûts et profits dans la décision.** Les lignes de fret
   RAIL longues peuvent avoir un profit réel > prédit tout en coûtant
   sensiblement plus cher à construire ; un ratio de profit favorable
   ne garantit donc pas le ROI du capital.
4. Avant toute mise en production, valider hors échantillon par
   **graines disjointes**, avec erreur par ligne puis impact économique
   dans un banc contrôlé. Aucune modification de politique n'est faite ici.
