# Rapport cloud n°2 (04/11/2026) : `road1y_alt_load`, une part des bus chargent à plein au bout B

Branche `cloud/road1y-altload`, créée depuis `cloud/road1y-pack2-0411` (47b758d =
`cloud/road1y-paxmin` + PROMPT2). Mission : `PROMPT2.md` ; constat : `RAPPORT_CLOUD.md` §3
(« constat secondaire ») et §4 levier 2. Aucun défaut modifié, rien poussé sur master.
Les numéros de ligne renvoient à l'arbre du commit livré.

## 1. Comment les bus d'une ligne partagent leurs ordres aujourd'hui

| Site d'achat | Code | Ordres du nouveau bus |
|---|---|---|
| Ouverture de ligne | `builder_road.nut:5464-5470` pose A (`OF_FULL_LOAD_ANY` sous `road1y_load_orders`) puis B (`OF_NONE`) sur `first` ; boucle d'achat `:5514-5540` | `CloneVehicle(depot, first, true)` : **partage** avec `first` |
| Renfort (`OpexRoad1yRefleetSaved`, `bus_districts_overrides.nut:1300`, appel `:2126` ; `_refleetRoadLines` historique, `task_road.nut:1399` ; renfort courrier fille `bus_districts.nut:519`) | tous passent par `OpexRoadRefleet` (`builder_road.nut:6444`) | modèle = 1er bus valide de `OpexLineVehicleIds` (`:6456-6466`), `CloneVehicle(..., template, true)` ; ligne sans bus : `first` reçoit des ordres propres (`:6510-6544`) puis clones partagés |
| Réallocation `road1y_weak` (défaut 15) | `OpexRoad1yWeakStep`, `bus_districts.nut:946` ; vente du dernier bus de la ligne faible `:1071`, achat `:1052` | `CloneVehicle(bestStrong.depot, sVehs[0], true)` : partage |
| Renouvellement | `main.nut:758-760` (`SetAutoRenewStatus(true)`, −6 mois) | renouvellement automatique du moteur : il conserve la liste d'ordres du véhicule remplacé (pas de code IA) |
| Fourgons courrier (`bus_districts.nut:600-624`) | `kind` courrier | hors périmètre (`kind != "pax"`) |

Toute la flotte d'une ligne PAX partage donc une seule liste d'ordres. Les remplacements par
copie d'ordres (`task_v257.nut`, `task_v284.nut`) ne concernent que le rail.

## 2. Implémentation

**Réglage** `road1y_alt_load` = N (0..50, défaut 0, `info.nut`, 4 valeurs à 0) ; globale
`ROAD1Y_ALT_LOAD` (`globals_pre.nut:94`) ; lecture, bornage 0..50 et forçage à 0 hors route seule
dans `OpexLoadSettings` (`settings.nut:162-164`) et `OpexLoadBusDistrictSettings` (`:750-752`).

**Helpers** (`bus_districts.nut:807-940`, chargé inconditionnellement par
`OpexLoadBusDistrictSettings`) :
- `OpexRoad1yAltLoadIsInverted(v)` (`:814`) : vrai si 2 ordres, ordre 0 sans plein chargement et
  ordre 1 avec `OF_FULL_LOAD_ANY`. **Le sens se lit dans les ordres réels**, jamais dans un
  compteur sauvegardé.
- `OpexRoad1yAltLoadOrient(v, inverted)` (`:823`) : sur un bus à ordres propres, retire le plein
  chargement des deux ordres (sans opérateur `~`, sans précédent dans le code) puis le remet à
  B (inversé) ou à A (normal) par `AIOrder.SetOrderFlags` ; vérifie le résultat. Les drapeaux
  non-stop sont conservés.
- `OpexRoad1yAltLoadEligible(line)` (`:842`) : N > 0, `ROAD1Y_LOAD_ORDERS` (sinon il n'y a pas de
  « sens » historique à inverser), ligne route `kind == "pax"` (exclut `mail_pax` et fret), pas
  de tour ROAD100-14 actif (4 ordres).
- `OpexRoad1yAltLoadClone(depot, template, fleet, site, lineId)` (`:856`), remplaçant de
  `CloneVehicle(depot, template, true)` : compte les bus valides de `fleet` (avant achat) et les
  inversés ; `quota = round(N % × (bus + 1))` = `(N*total + 50)/100`, **0 sous 2 bus** ; inverse si
  `inversés < quota`. Le clone **partage** les ordres d'un bus du **même sens** s'il en existe ;
  sinon **copie** (`CloneVehicle(..., false)`) puis `Orient`. Échec d'orientation : bus vendu,
  achat abandonné (jamais de bus au sens incertain). Si un bus de la flotte n'a pas 2 ordres
  (tour), repli sur le clone historique. Un bus inversé ne repartage donc jamais la liste d'un
  bus normal, ni l'inverse.

**Sites branchés** (garde `ROAD1Y_ALT_LOAD > 0 && …` puis ternaire dont la branche « sinon » est
la ligne historique inchangée) :
- ouverture `builder_road.nut:5534-5537` (`fleet = built`, `kind == "pax"`, `ROAD1Y_LOAD_ORDERS`) ;
- `OpexRoadRefleet` `builder_road.nut:6486-6499` (flotte réelle lue par `OpexLineVehicleIds`,
  complétée à chaque achat) et `:6549-6551` (ligne vide : `first` garde les ordres historiques,
  ses clones passent par le quota) ;
- `road1y_weak` `bus_districts.nut:1052-1056` (le bus reçu suit le quota de la ligne forte).

Choix : **pas de rééquilibrage** des bus existants (aucun changement d'ordres sur un bus qui
roule) ; le quota se corrige au fil des achats. `weak` peut vendre un bus inversé (dernier de la
liste) : le suivant acheté sur cette ligne le remplacera si le quota l'exige.

**À 0** : chaque site évalue `ROAD1Y_ALT_LOAD > 0` (faux) et exécute le `CloneVehicle(..., true)`
historique ; `OpexRoadRefleet` calcule en plus trois locales nulles (`altLoad=false`, `-1`,
`null`). Mêmes commandes de jeu ; l'écart d'opcodes déplace la trajectoire comme tout ajout
(identité à vérifier entre deux bras du même code).

**Mesure** (sous `DECISION_LOG`, donc `probes=258`) : `OpexDecide("ROAD1Y_ALT_LOAD", …)` à chaque
bus inversé acheté et à chaque copie/repli (`site`, `line`, `veh`, `how=shared|copy|historical|
orient_failed`, `fleet_after`, `inverted_after`, `quota`) ; recensement
`ROAD1Y_ALT_LOAD_CENSUS` en juin et novembre (`bus_districts.nut:907`, appelé
`scheduler_tasks.nut:1133`) : bus normaux/inversés par ligne, `GetProfitThisYear` des deux
groupes, inversés arrêtés au dépôt. Il ne décide rien.

## 3. Vérification « un bus inversé reste un bus de sa ligne »

- `OpexLineVehicleIds` (`lines.nut:80`) : route = `AIVehicleList_Station(A)` filtré par
  `OpexVehicleServesStation(v, B)` (`lines.nut:69`), donc par **destinations** ; l'inversion ne
  change que les drapeaux de chargement. Idem `OpexFindLineForVehicle` (`lines.nut:153`).
- `waitingA/B` (`bus_districts_overrides.nut:1673-1674`) : lus sur les StationID de la ligne,
  indépendants des bus. `isAnyWaiting` (`:1682`) compte déjà les bus en plein chargement à A ;
  un inversé qui attend à B est compté de même (la branche ROAD1Y n'exige que `movingCount > 0`).
- `road1y_spread_stops` : arrêts **joints** (même StationID) ; les ordres visent la tuile racine
  `line.stationA/B`, inchangée dans la copie.
- Sauvegarde/rechargement : rien à persister (sens = drapeaux d'ordres sauvegardés par le jeu) ;
  `_reconcileAfterLoad` (`bus_districts_overrides.nut:2163-2185`) recompte arrêts et flotte par
  les mêmes fonctions. `ROAD1Y_ALT_LOAD_CENSUS_YM` est de la mesure (non sauvegardé).
- Tour ROAD100-14 (défaut 0, exige 1 arrêt par bout donc incompatible avec `spread_stops=2`) :
  lignes à tour exclues de l'inversion ; la réparation de tour (`bus_districts_overrides.nut:1586`)
  ne retire que les ordres au-delà de 2.

## 4. Pièges rencontrés

- `OF_FULL_LOAD_ANY` vaut deux bits (`3 << 5`) : test `(f & fullAny) == fullAny` pour B,
  `== 0` pour A.
- Un clone partagé hérite du sens de son modèle : le modèle passé par l'appelant (`sVehs[0]`,
  1er bus de la liste) peut être inversé, d'où le choix d'un modèle **du sens voulu** dans la
  flotte, et la copie seulement en l'absence de modèle.
- Projection historique `ROAD1Y-B2` : les blocs `after` de
  `sweeps/fixtures/road100_bus_districts_hunks.json` ont été étendus (globals_pre, info,
  settings ×2) et les hunks de `builder_road.nut` régénérés contre le parent 481e7c08
  (reconstruction exacte vérifiée ; 31 hunks conservés, 2 fusionnés avec les nouveaux).
- Batterie complète `sweeps/test_*.py` : 148 échecs/erreurs **identiques** sur la branche de
  départ (préexistants, aucun nouveau).
- Pas de compilateur Squirrel dans la session (la compilation d'un Squirrel téléchargé a été
  refusée) : contrôle limité à l'équilibre des délimiteurs et aux motifs existants (ternaires
  multilignes, `GetOrderFlags`). **La compilation réelle reste à prouver par le smoke.**

Tests : `sweeps/test_road1y_alt_load.py` (déclaration, sites, partage par sens, mesure,
pièges Squirrel, modèle du quota : N=33 → 2 bus : 1 inversé, 5 : 2, 8 : 3, 12 : 4 ; jamais sous
2 bus ; toujours ≥ 1 bus normal pour N ≤ 50), `test_road1y_multimodal_gate.py`, fixture B2 et
commentaire de `test_v251_inventory.py` (plafond 75 inchangé, le réglage est retiré par la
projection B2). Depuis la racine : `test_road1y*` 98 tests OK, `test_road100*` 230 OK (3 sautés),
`test_v251*` 7 OK.

## 5. Smoke GitHub : **bloqué**

`gh` est installé mais son jeton (`GH_TOKEN`) est invalide, et l'outil GitHub de la session
renvoie **403 « Resource not accessible by integration »** sur
`POST /actions/workflows/bench.yml/dispatches`. Le push de la branche a fonctionné ; les
workflows de contrats déclenchés par le push (`ai-review-contracts.yml`,
`benchmark-regressions.yml`, sans partie) sont visibles en lecture. Le smoke n'a donc **pas**
tourné : aucune donnée de jeu, aucune conclusion. Commande prête (identique au PROMPT) :

```
gh workflow run bench.yml --ref cloud/road1y-altload \
  -f mode=paired -f profile=custom -f years=3 -f seeds="613553 781335 100" \
  -f reference="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,probes=258]" \
  -f variant="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,probes=258,road1y_alt_load=33]" \
  -f aaahogex_settings=road_only -f line_telemetry=true
```

À contrôler sur l'artefact :
1. 6/6 parties `complete`, `horizon_complete`, 0 ligne `[E]`/`[S]` (compilation : un échec
   de `bus_districts.nut` tuerait l'IA dans **les deux** bras, signe immédiat).
2. Mécanisme (variante seulement) : lignes `ROAD1Y_ALT_LOAD` (`inverted=1`, `how=copy` pour le
   1er inversé d'une ligne puis `shared`, aucun `orient_failed`) ; `ROAD1Y_ALT_LOAD_CENSUS` de
   novembre 1972 : `inverted ≈ round(0,33 × bus)` par ligne, `profit_inverted` non nul,
   `depot_inverted=0`.
3. Télémétrie par ligne (`line_telemetry`) : une ligne Opex à bus inversés a **deux**
   `order_list_ids` (clé = stations, pas groupe) ; `vehicle_financials` par `vehicle_id` à
   croiser avec `veh=` du journal ; au bout B (`endpoint_cargo_stats[1]`) `time_since_pickup`
   et `rating` des deux bras (attendu : temps médian 4 → ≈ 1-2, note B en hausse).
4. `profit_year` 1972 par graine des deux bras et d'AAA, sans conclusion économique.

## 6. Valeur à banquer

**`road1y_alt_load=33`** (un tiers des bus : sur une ligne de 2 à 4 bus, un inversé ; 5-7 :
deux ; 8 : trois). 50 en second bras seulement si 33 montre un mécanisme sain mais un bout B
encore peu servi. Porte A `gain_short` 40×3 puis B 20×10 à lancer par l'utilisateur **après un
smoke sain** ; aucun défaut changé.
