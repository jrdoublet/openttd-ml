# Le mode route d'OpexAI

État au **2026-08-29**. Ce document décrit ce que le mode route fait, ce qui a été mesuré, et ce
qui reste ouvert. Il remplace la note historique sur la « liaison bus v1 », qui décrivait une
transaction unique et désactivée.

---

## 1. Ce que le mode fait

Une **phase annuelle** (`OpexAI::_tryBuildRoads`, `main.nut`) qui bâtit jusqu'à
`ROAD_MAX_NEW_LINES_PER_YEAR = 3` petites lignes routières, dans la bande **5 à 25 tuiles** — celle
que le rail refuse structurellement (`MIN_DISTANCE = 25` dans `candidates.nut`, une mesure : sous
25 tuiles le profit médian d'une ligne **rail** est négatif).

Trois familles de candidats (`OpexBuildRoadCandidates`, `candidates.nut`) :

| famille | véhicule | arrêt | sens |
|---|---|---|---|
| ville ↔ ville, passagers | bus | arrêt de bus | bidirectionnel |
| industrie → industrie | camion | aire de chargement | **une seule direction** |
| industrie → ville | camion | aire de chargement | **une seule direction** |

Le type d'arrêt est **imposé par le cargo**, jamais choisi : un bus ne chargera jamais sur une aire
de chargement camion (`docs/mecanique_jeu.md` §11). `OpexRoadStopKind` est le seul endroit qui en
décide.

Réglage de partie **`road_mode`** (défaut 1). À 0, la baseline rail retrouve *exactement* son
chemin d'opcodes antérieur : le catalogue routier n'est même pas rafraîchi.

## 2. Les trois décisions d'allocation

1. **Le rail choisit en premier.** `_tryBuildRoads` tourne **après** `_tryBuild`. Les deux modes ne
   se disputent jamais la même *paire* (bandes de distance disjointes) mais bien les mêmes
   *origines* et la même trésorerie ; le rail vaut un ordre de grandeur de plus par ligne, donc il
   sert d'abord et la route prend ce qui reste.
2. **Une ligne routière ne verrouille rien pour le rail.** Elle vit dans `_lines` (pour être
   rapportée et mise au rebut par le même code) mais `OpexOriginServed(..., includeRoad = false)` et
   `_tooClose` l'ignorent. Une desserte de bus de 12 tuiles n'épuise pas une ville, et un arrêt de
   rayon 3 ne cannibalise pas le bassin d'une gare rail.
3. **Deux plafonds annuels**, tous deux arbitraires : 3 lignes neuves, 6 tentatives. Le second
   existe parce qu'un plan qui échoue coûte quand même ses sondes de site.

## 3. Le modèle économique (`OpexRoadLineEconomics`, `economy.nut`)

Repris du rail, avec trois écarts, chacun justifié :

- **`MAX_ROAD_VEHICLES = 2`.** Un arrêt n'accueille que deux véhicules à la fois ; au-delà ils font
  la queue sur la route et se bloquent (`docs/mecanique_jeu.md` §11). Ce n'est pas une précaution,
  c'est la règle du jeu. Le levier de volume est le **multistop**, non implémenté.
- **`ROAD_SPEED_EFFICIENCY_PCT = 60`** contre 70 au rail. Hypothèse, non calibrée.
- **La durée de trajet suit le tracé**, et ici tracé et distance Manhattan coïncident (le tracé est
  un L de Manhattan), ce qui autorise la même formule sans facteur de détour.

Les ordres appliquent la leçon du fret rail du 2026-08-28 : une ligne de fret est à sens unique,
donc `OF_FULL_LOAD_ANY` à la source et **`OF_NONE` au puits**. Le pax fait l'inverse du rail et ne
charge jamais à plein : sur une ligne courte, la note de gare dépend à 51 % du délai depuis le
dernier ramassage — un bus qui attend d'être plein détruit ce que la ligne a de bon.

## 4. 🔴 Les quatre bugs que la mise en service a révélés

Tous mesurés sur la campagne graine 42 (`docs/opex_road_20y_42.json`), tous corrigés.

1. **`clone` est un mot réservé de Squirrel.** `local clone = ...` fait échouer la compilation du
   fichier entier. L'échec est presque muet : une ligne dans la sortie OpenTTD, aucun panneau, une
   compagnie qui existe sans rien construire. Symptôme au dépouillement : `company_value = 1`.
2. **`ERR_LAND_SLOPED_WRONG` sur la pose du tracé** (≈ la moitié de 21 échecs sur 21 tentatives).
   `AITestMode` valide chaque arête **isolément**, sur la carte d'avant la pose. Or une tuile qui
   reçoit des bits de route sur **deux axes** — le coin du L, la façade d'un arrêt, la façade du
   dépôt — n'est constructible en deux axes que si elle est **plate**. Chaque arête passait son test
   isolé et la pose réelle échouait dès que la deuxième direction arrivait. Correctif :
   `OpexRoadIsFlat` sur ces seules tuiles de jonction (une longue portion droite en pente reste
   acceptée, elle ne porte qu'un axe).
3. **`ERR_AREA_NOT_CLEAR` sur le dépôt** (l'autre moitié). Même dissymétrie plan/pose : les quatre
   voisins d'une façade sont testés avant la pose du tracé, et les deux qui sont dans l'axe **sont**
   le tracé. Vides au test, ils portent une route au moment de bâtir le dépôt. Correctif : le tracé
   est indexé et ses tuiles sont exclues des sites de dépôt.
4. **La liste de véhicules figée à la construction est fausse dès qu'un véhicule est remplacé.** Le
   renouvellement détruit l'ancien identifiant et OpenTTD **recycle** les identifiants libérés — une
   liste figée finit par ne plus rien désigner, ou par désigner le véhicule d'une autre ligne.
   Symptôme : trois lignes sur quatre finissant à `vehCount = 0` avec une note de gare de 48 à 60,
   et l'une repassant de 0 à 1 véhicule d'une année sur l'autre. Correctif : une ligne routière
   interroge sa gare (`AIVehicleList_Station`), ce qui est exact ici parce qu'un arrêt routier est
   toujours posé en `STATION_NEW` et n'est jamais joint.

## 5. Deux correctifs qui ne sont PAS du mode route

Découverts en mesurant la route, mais valables pour toute la compagnie. **Ne pas les attribuer au
mode route au banc.**

- **Renouvellement automatique** (`SetAutoRenewStatus(true)`, `-6` mois, plancher `CASH_RESERVE`).
  Un camion vit ~12 ans quand une locomotive en vit 20 à 30 : le mode d'échec ne se voyait pas tant
  que l'IA ne roulait qu'en rail sur 20 ans.
- **Détection de ligne morte** : la condition exigeait `ratingA <= 0`, et cette clause était fausse
  — **une gare conserve sa dernière note quand plus rien n'y passe**. La ligne OIL_ a roulé **onze
  ans à −842 par an** sans être mise au rebut, note figée à 67. Le revenu implicite suffit et ne
  ment pas. La prudence reste assurée par l'industrie source en souffrance et par
  `DEAD_STREAK_THRESHOLD` années consécutives.

## 6. Ce que la mesure donne (graine 42, 20 ans, `docs/opex_road_20y_42.json`)

**4 lignes routières, dont 3 de fret**, toutes vivantes à la dernière année avec leurs 2 véhicules :

| ligne | dist. | profit prédit | profit réel (dernier exercice) |
|---|---|---|---|
| COAL, industrie → industrie | 22 | 4 974 | 4 779 |
| OIL_, industrie → industrie | 24 | 4 238 | 917 (production source tombée à 18) |
| WOOD, industrie → industrie | 16 | 2 773 | 3 298 |
| PASS, ville ↔ ville | 23 | 1 031 | 10 715 |

> ⚠️ **Mesure antérieure au correctif « trajets chargés » du 2026-08-29**
> (`docs/mecanique_jeu.md` §1 ter). Depuis, la même graine donne **6 lignes routières (4 fret,
> 2 pax)** au lieu de 4 : le modèle passagers ne demande plus deux fois trop de véhicules, donc des
> candidats bus qui tombaient sous `ROAD_MIN_PROFIT_ANNUAL` passent désormais. Les chiffres du
> tableau ci-dessus restent valables comme illustration du comportement d'une ligne, pas comme
> décompte.

**Le modèle de fret est bien calibré** (rapport prédit/réel de 0,84 à 1,20 sur les années à
production stable) : `STATION_RATING_PCT = 50`, calibré sur le rail, tient aussi pour le camion.
**Le modèle pax sous-estime d'un facteur ~10** — et c'est la piste la plus prometteuse ouverte, voir
§7.

Coût : ~15 000 opcodes par plan, ~300 000 par construction, ~60 000 par an pour la génération de
candidats. Négligeable devant les ~270 M d'opcodes annuels.

## 6 bis. 🔴 Le verdict du banc apparié (`docs/bench_v2_road.json`)

20 graines × 20 ans, `OpexAI` contre `OpexAI[road_mode=0]`. Les deux bras portent le
renouvellement automatique et le correctif de ligne morte : le banc isole donc **le mode route
seul**.

| métrique | écart apparié | t | graines gagnées | test des signes |
|---|---|---|---|---|
| `performance_history` | **+36,6 pts (+9,3 %)** | **2,03** | **16 / 20** | **p = 0,012** |
| `company_value` | +232 433 (+9,6 %) | 1,50 | 13 / 20 | p = 0,26 |

**Adopté**, sur `performance_history` — la métrique que le projet a désignée comme la bonne entre
variantes d'OpexAI, parce qu'elle est moins bruitée que `company_value` chez nous (CV 31 % contre
45 % sur ce banc). Le test des signes est ici la lecture la plus solide : 16 sur 20 ne s'obtient par
hasard qu'une fois sur cent.

`company_value` va dans le même sens (+9,6 %) mais ne tranche pas, et pour une raison identifiable
plutôt que par bruit diffus :

> 🔴 **Une graine sur vingt paie très cher.** La graine 8675309 tombe de 1 460 136 à **1** —
> l'insolvabilité — quand la route est active. Sa trajectoire diverge dès 1974 : la valeur s'érode
> de 165 793 à 55 691 en cinq ans pendant que le bras sans route grimpe régulièrement, la trésorerie
> finit collée au plancher `CASH_RESERVE` (35 000 à 48 000 les six dernières années), et l'emprunt
> n'est jamais remboursé — **sur les deux bras** : cette graine appartient déjà au régime d'échec
> d'emprunt connu du backlog. À elle seule elle retire 73 000 à l'écart moyen ; sans elle, la route
> gagne +13 % sur 13 graines de 19.
>
> **Mécanisme non établi.** L'hypothèse à tester est que la phase routière consomme la trésorerie
> marginale qui aurait financé la ligne rail suivante, et qu'une compagnie pauvre n'amorce alors
> jamais sa composition. Le garde-fou naturel serait un plancher de trésorerie propre à la route,
> plus haut que `CASH_RESERVE`, ou une route interdite tant que l'emprunt n'est pas remboursé.
> **À mesurer, pas à supposer.**

## 7. Ce qui reste ouvert, par impact estimé

1. **Le plancher `ROAD_MIN_PROFIT_ANNUAL = 1000` coupe des lignes pax qui rapportent 10 000.** La
   seule ligne pax bâtie était prédite à 1 031 et a rendu 7 000 à 11 700 par an. La cause probable
   est `TOWN_CATCHMENT_SHARE_PCT = 22`, calibré sur des **gares rail**. Un facteur propre à la route
   se mesure exactement comme le premier l'a été (`sweeps/opex_predict_vs_actual.py`). C'est n = 1 :
   à mesurer, pas à recalibrer d'après ce seul cas.
2. **`SITEA` / `SITEB` dominent les échecs de plan** (36 sur 40 tentatives échouées) : aucun site
   d'arrêt valide autour de l'extrémité. Le rayon n'est pas le levier — au-delà du rayon de
   couverture (3), `GetCargoProduction` rend zéro de toute façon. Les suspects sont l'exigence de
   platitude de la façade et `ROAD_MAX_SITE_PROBES = 48`.
3. **Le classement routier et le classement rail ne sont pas comparables.**
   `ROAD_PLAN_ITERATIONS_BASE` est non calibré et ne sert qu'à ordonner les candidats routiers entre
   eux. Le panneau `RB` mesure désormais le coût réel de chaque tentative, ce qui rend cette
   calibration possible — et donc, à terme, **un seul classement pour tous les modes**, ce que la
   philosophie du projet demande.
4. **Le multistop** (`AIStation.STATION_JOIN_ADJACENT`) est le seul levier de volume par ligne, le
   plafond de deux véhicules par arrêt étant une règle du jeu.
5. **Rebâtir la flotte d'une ligne tombée à zéro véhicule.** Vu une fois : une ligne bus perd ses
   deux véhicules en deux ans et ne se reconstitue jamais, notes de gare de 54 à −1, alors qu'elle
   rendait 9 000/an et que ses arrêts, sa route et son dépôt sont payés. Cause non établie (n = 1) ;
   le suspect est le **passage à niveau** avec nos propres voies — un train est le seul objet qui
   détruise un véhicule routier (`docs/mecanique_jeu.md` §11).

## 8. Les pistes déjà écartées par la mesure — ne pas les reproposer

- `Pathfinder.Road` : 696 794 opcodes contre 171 356 pour le tracé Manhattan borné.
- Arrêts traversants (`BuildDriveThroughRoadStation`) : 912 232 opcodes, aucun gain. C'est cette
  disposition en cul-de-sac qui impose d'écarter les **véhicules articulés** au catalogue.
- Distance du dépôt aux arrêts, testée de 1 à 4 tuiles : la variable pertinente était la
  **connexité**, pas la distance.
- `GetRoadDepotFrontTile` / `GetRoadStationFrontTile` ne prouvent **jamais** un raccordement : ils
  rendent la géométrie déclarée. Le seul prédicat est `AIRoad.AreRoadTilesConnected`.
