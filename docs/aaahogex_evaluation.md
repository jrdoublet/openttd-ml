# AAAHogEx — évaluation comme source d'idées

**Date : 2026-08-27.** Évaluation de l'IA tierce [AAAHogEx](https://github.com/rei-artist/AAAHogEx)
(version 115, Rei Ishibashi, GPL v3) comme source d'inspiration pour `ai/TrainLineAI`.

Le code est présent en local dans `ai/AAAHogEx-115/` mais **volontairement exclu du dépôt**
(`.gitignore`) : le versionner ici rendrait `openttd-ml` dérivé de la GPL v3. Ce document est notre
analyse ; il ne reproduit pas son code.

**Conclusion en une phrase** : ne rien porter, mais deux de ses idées valent d'être réimplémentées
proprement — et l'hypothèse de départ qui avait motivé l'évaluation était fausse.

---

## 1. L'hypothèse de départ était fausse

L'idée initiale était : *« pas de pathfinding complet, juste une approximation qui construit au fur
et à mesure et utilise terraforming, tunnels et ponts quand elle rencontre un obstacle. »*

**Vérifié dans le code, c'est faux.** AAAHogEx **planifie entièrement puis construit** :

1. `RailPathBuilder.DoBuild()` appelle `FindPath(limitCount, this)` (`railbuilder.nut:2362-2377`) ;
2. le chemin complet est sérialisé dans `path1` / `path2` ;
3. `RailBuilder` ne reçoit ce chemin **qu'ensuite** et lance `Build()` (`railbuilder.nut:2382-2412`).

Il pose bien les rails tuile par tuile dans `RailBuilder.DoBuild()` (`railbuilder.nut:1090-1242`),
mais il n'y a **pas** d'alternance « chercher un peu → construire → repartir du front construit ».

**Et il subit exactement notre contrainte d'opcodes.** Sa boucle de recherche fait
`path = _FindPath(50)` (`pathfinder.nut:197-219`) — le **même découpage à 50 itérations** que le
nôtre, pour la même raison. Il n'a trouvé aucune astuce pour contourner le budget du VM, parce
qu'il n'y en a pas. Le découpage n'est pas non plus une segmentation géographique : la recherche
reprend le même A* vers son but final.

---

## 2. Les idées qui valent quelque chose

### 2.1 Ponts et tunnels comme **voisins de l'A\***, pas comme réaction à un obstacle

C'est l'idée centrale, et elle est architecturalement inverse de ce qu'on imaginait.
`_GetTunnelsBridges()` renvoie des candidats pont/tunnel qui sont **poussés dans la liste des
voisins** du nœud courant (`pathfinder.nut:1093-1137`) :

- pont proposé quand un obstacle non constructible, une différence de hauteur ou la contrainte de
  voie retour se présente ; les longueurs sont testées et le pont n'est ajouté que si l'essai est
  constructible (`pathfinder.nut:1381-1413`) ;
- tunnel proposé pour une entrée en pente valide, une sortie calculable et une longueur sous la
  limite (`pathfinder.nut:1423-1433`) ;
- **le coût A\* pénalise distinctement pont et tunnel** (`pathfinder.nut:572-604`).

Ce n'est donc pas une règle « obstacle ⇒ tunnel » : les solutions faisables sont proposées, puis
**arbitrées par la fonction de coût**. Toute la recherche se fait en `AITestMode`
(`pathfinder.nut:428-438`), donc les essais ne modifient pas la carte.

> **Note importante ajoutée après coup** : notre bibliothèque `Pathfinder.Rail` fait **déjà** cela.
> Voir §5 — le problème n'était pas l'absence de la technique.

### 2.2 Reprise en conservant le préfixe déjà construit

`RetryToBuild()` (`railbuilder.nut:1127-1153`, `1186-1211`, `1291-1329`) : en cas d'échec de pose
d'un rail, d'un pont ou d'un tunnel, il **conserve le préfixe déjà construit**, relance une
recherche depuis des points de raccordement de ce préfixe vers le but, puis remplace le tronçon
raté. C'est la vraie idée « incrémentale » du code, et elle est réactive, pas planifiée.

Notre IA n'a pas d'équivalent : un `TRKFAIL` est terminal. C'est **l'idée la plus directement
transposable**, et la moins risquée pour la barrière (elle n'intervient qu'après la première
mutation).

### 2.3 Terrassement pendant la construction

`RaiseTileIfNeeded()` (`railbuilder.nut:1105-1108`, logique en `1593-1722`, `Raise()` en
`1725-1745`) est appelé **avant chaque segment** du tracé déjà choisi. Les tunnels « underground »
nivellent aussi leurs entrées via `LevelBound()` (`railbuilder.nut:1529-1586`, `tile.nut:276-303`).
C'est une adaptation à la construction, pas une décision de recherche.

### 2.4 Instrumentation d'opcodes

`PerformanceCounter` lit `AIController.GetOpsTillSuspend()` et journalise ticks et opcodes
(`utils.nut:1039-1085`) ; la sauvegarde mesure aussi ses sous-étapes (`main.nut:4032-4089`).

**Mais aucune de ces lectures ne pilote une boucle.** Il n'y a pas de « tant qu'il reste N opcodes,
avancer ; sinon sauver l'état et reprendre au tick suivant ». Le découpage à 50 itérations est
fixe. Il mesure son coût, il ne s'y adapte pas.

### 2.5 Caches

Frontière prioritaire `AIPriorityQueue` + ensemble fermé `AIList` dans l'A* (`aystar.nut:77-108`,
déduplication en `121-140`, `171-190`) ; connectivité terrestre mémorisée dans `landConnectedCache`
(`tile.nut:506-527`) ; caches de sélection de stations, cargaisons et production
(`station.nut:15-38`, `place.nut:733-755`, `1007-1023`).

Ces caches servent surtout son IA économique multi-réseaux. Ils ne transforment pas la recherche
ferroviaire de bout en bout en construction locale bon marché.

---

## 3. Pourquoi ne rien porter

**Blocage d'API.** `info.nut:11` déclare `GetAPIVersion() = "14"` ; OpenTTD 13.4 (notre version
épinglée) n'accepte que jusqu'à `"13"`, et le refus arrive **avant** l'exécution de `main.nut`.
Le seul ajout v14 réellement utilisé est `AITileList_StationCoverage`
(`station.nut:626-649`) — et il a déjà un repli compatible pré-14 dans le code. Ce blocage
empêche donc de *l'exécuter*, pas de *le lire*.

**Licence.** GPL v3 (`license.txt`). Copier ou adapter une fonction, un bloc ou une structure
expressive identifiable créerait vraisemblablement une œuvre dérivée, avec obligation de
distribuer l'ensemble sous GPL v3 en cas de publication. S'inspirer d'une *idée* — « conserver un
front local et réagir à l'obstacle » — ne pose pas ce problème : les algorithmes ne sont pas
protégés en tant que tels. Le dépôt `openttd-ml` ne déclare aucune licence à la racine, ce qui
devrait être clarifié avant toute publication. *(Ceci n'est pas un avis juridique.)*

**Taille.** 37 531 lignes sur 16 fichiers, contre 1 166 pour `TrainLineAI`. C'est une IA
compétitive multi-modale (train, route, bateau, avion) ; la nôtre est un **instrument de mesure**
à une compagnie et une ligne. Les objectifs n'ont rien à voir.

---

## 4. Compatibilité avec notre barrière

Notre comparabilité temporelle repose sur : preflight non mutant → attente jusqu'au tick 11000 →
construction. La crainte était qu'une construction incrémentale, qui mute tôt et souvent, soit
**fondamentalement** incompatible.

**Elle ne l'est pas**, à une condition stricte : aucune mutation avant la barrière. Muter
fréquemment *après* le tick 11000 ne rompt rien. Ironiquement, comme AAAHogEx planifie puis
construit, sa forme épouse déjà la nôtre.

**Le vrai risque est ailleurs, et il est silencieux.** `first_mutation_tick` est capturé juste
avant le premier `DemolishTile` (`ai/TrainLineAI/main.nut:852-860`). Avec du terrassement ou un
pont, **la première mutation pourrait être un `RaiseTile` ou un `BuildBridge`** et échapper à
l'instrumentation, faussant `barrier_flag` sans que rien ne le signale. Toute évolution dans cette
direction impose de généraliser ce point de contrôle à une fonction unique appelée avant le premier
`DemolishTile`, `RaiseTile`, `LowerTile`, `BuildRail`, `BuildBridge` **ou** `BuildTunnel`.

Autre point : la contrainte de villes disjointes (`main.nut:575-623`) ne protège pas de tout
conflit territorial — deux lignes reliant des villes distinctes peuvent se rencontrer sur le
terrain. Un builder plus long devrait prévoir une politique explicite face à une tuile devenue
occupée.

---

## 5. Ce qu'on a appris APRÈS cette évaluation — et qui la relativise

L'évaluation supposait qu'il fallait *ajouter* ponts et tunnels. **C'est faux : notre IA en
construit déjà.**

- La bibliothèque `Pathfinder.Rail` explore nativement des candidats pont/tunnel, avec les défauts
  `_max_bridge_length = 6`, `_max_tunnel_length = 6`, `_cost_bridge_per_tile = 150`,
  `_cost_tunnel_per_tile = 120`, `_max_cost = 10000000`.
- `ai/TrainLineAI/main.nut` ne règle que `cost.max_cost` (à 200000, soit 50× moins que le défaut).
- Un pont a été mesuré sur 15 lignes construites (graine 7, rang 120, saut de 3 tuiles).

**Et relever les plafonds ne sert à rien.** Essai apparié sur 9 cas `PATHLIM` avec
`max_bridge_length = 20` : **0/9** bascule, **aucun pont de plus de 6 tuiles jamais retenu**, et
**+12,6 % de ticks** de pathfinding (18 longueurs candidates testées par nœud d'obstacle au lieu
de 4). Un cas est même passé à 11 159 ticks, au-delà de la barrière de 11 000.

La contrainte réelle est le **plafond de 30 000 itérations d'A\***, couplé à la barrière : une
itération coûte ~2 700 opcodes pour un budget de ~10 000 par tick, soit 3,7 itérations par tick,
donc 30 000 itérations ≈ 8 100 ticks — contre une barrière à 11 000. **Le pathfinding consomme
déjà ~96 % de son budget disponible.** On ne peut pas chercher plus loin sans déplacer la barrière.

---

## 5bis. Le pipeline de décision en trois étapes — et la vraie idée à emprunter

*(Ajouté après une seconde passe de lecture, motivée par une vidéo de l'auteur décrivant trois
étapes : évaluation grossière, évaluation détaillée avec le parcours, puis construction.)*

### Les trois étapes existent, avec une nuance qui compte

**Étape 1 — évaluation grossière.** `CreateRouteCandidates` (`main.nut:1578-1803`) énumère des
lieux compatibles par cargo, distance et type de véhicule, élimine les productions trop faibles
(<27), puis appelle `Route.Estimate` ; un candidat est gardé si `estimate.value > 0`. Le score
n'est **pas** `population × population / distance` comme chez nous : la variable quantitative est
la **production de cargo attendue** (`main.nut:1690-1767`). Les estimations sont mises en cache sur
des indices discrétisés de distance et de production (`route.nut:95-125`).

**Étape 2 — détaillée avec le parcours.** `TrainRouteBuilder.BuildRoute` (`trainroute.nut:2885-3045`)
choisit le train, fait chercher les gares par des factories testées sous `AITestMode`
(`station.nut:841-889`, `1322-1350`), puis lance le pathfinding. La ligne **peut être abandonnée
ici** — absence de chemin, échec du builder, pas de dépôt source — avec rollback, et le couple est
mémorisé dans `ngPathFindPairs` (`trainroute.nut:2868-2881`, `3089-3106`).

> **Nuance importante :** l'étape 2 ne recalcule **pas** la rentabilité à partir du tracé réel.
> L'estimateur prend `pathDistance = distance` (`estimator.nut:704-716`), c'est-à-dire la distance
> à vol d'oiseau, et le chemin trouvé part directement à la construction. Le rejet détaillé est un
> rejet de **faisabilité**, pas un seuil de rentabilité après tracé. Sur ce point notre
> `estimated_cost` fait exactement la même chose.

**Étape 3 — construction.** Déjà documentée §1. Une différence : **les gares sont construites
avant le pathfinding** (`BuildExec()` en `AIExecMode`, `trainroute.nut:3015-3045`,
`station.nut:2268-2283`). Nous ne pouvons pas copier ça — ce serait muter avant la barrière.

**Budget A\*.** `pathFindLimit = 80` (`main.nut:242`), triplé si l'IA est pauvre
(`trainroute.nut:3063-3064`), puis multiplié par trois dans `FindPath` en blocs de 50 itérations
(`pathfinder.nut:197-227`). Le garde-fou global est une date limite (~2 ans de jeu), pas un
compteur d'essais (`main.nut:917-926`, `1047-1050`).

**Il essaie plusieurs candidats.** `RouteCandidates` est une `SortedList` décroissante et `Pop()`
retire le meilleur restant (`main.nut:4512-4638`, `utils.nut:448-505`) ; la boucle continue après
un échec (`main.nut:927-965`). **C'est la différence décisionnelle majeure avec nous** :
`TrainLineAI` trie toutes les paires puis prend exactement `pair_rank`, sans repli — ce qui est
voulu, c'est un instrument de mesure, pas un joueur.

### `IsLandConnectedForRail` — le pré-filtre bon marché

C'est le vrai butin de cette lecture. Avant l'A\*, après le tri économique
(`main.nut:1811-1847`), AAAHogEx applique `HgTile.IsLandConnectedForRail` (`tile.nut:484-504`) :

- il suit **une seule ligne Manhattan** entre les deux points ;
- il lit `AITile.IsSeaTile` case par case ;
- il échoue si une **séquence maritime CONTIGUË dépasse 13** pour le rail (50 pour la route) ;
- il n'essaie l'autre sens que si le premier échoue (`tile.nut:496-504`) ;
- coût `O(D)` au premier appel, `O(1)` ensuite via `landConnectedCache`, table indexée par les deux
  tuiles mémorisant `[terminé, longueur_max_de_mer]` (`tile.nut:506-527`), sauvegardée avec la
  partie (`main.nut:4045`, `4141-4143`).

Pas de flood-fill, pas de régions, pas d'A\*. Quelques centaines de lectures de tuiles contre nos
30 000 itérations. Il produit des faux négatifs (un détour praticable peut être rejeté) et ignore
pentes, constructibilité, ponts et tunnels : ce n'est pas un test de joignabilité, c'est un test de
**séparation maritime**.

Seconde heuristique de relief : `GetSlopeLevel` (`tile.nut:717-741`) échantillonne les hauteurs
**tous les 8 pas** le long d'un corridor Manhattan ; `AdjustTrainScoreBySlope`
(`utils.nut:1203-1223`) s'en sert pour pénaliser le score, pas pour rejeter.

### Notre feature mesure la mauvaise grandeur

Confirmation indépendante d'une réserve qu'on avait émise sans pouvoir la trancher :

| | ce qu'on mesure | ce qu'AAAHogEx mesure |
|---|---|---|
| Grandeur | **total** de tuiles d'eau sur la droite | **plus longue séquence contiguë** de mer |
| Appel | `AITile.IsWaterTile` | `AITile.IsSeaTile` |
| Seuil | aucun (feature brute) | **13** pour le rail |

Ce n'est pas un détail : six ruisseaux d'une tuile se franchissent trivialement, une rivière de six
tuiles beaucoup moins. `corridor_water` mélange les deux, ce qui explique probablement qu'il
plafonne à **AUC 0,76** alors que l'information physique est disponible. Et leur seuil de 13 face à
notre plafond de pont de 6 est cohérent : une étendue de 7 à 13 tuiles leur est franchissable, pas
à nous.

### Les deux features à ajouter

Toutes deux calculables **avant** le pathfinding, donc disponibles sur les `PATHLIM`, pour
quelques centaines de lectures de tuiles :

1. **`corridor_max_water_run`** — la plus longue séquence d'eau contiguë sur le corridor direct.
   C'est la grandeur physiquement pertinente : « pontable ou non ».
2. **`corridor_max_uphill_step`** — équivalent de `GetSlopeLevel` : montée locale maximale
   échantillonnée toutes les 8 tuiles. Notre `corridor_dh` actuel ne donne que l'amplitude totale
   entre le point le plus bas et le plus haut du corridor, ce qui ne dit rien de la **raideur**.

C'est l'angle « emprunter une mesure, pas une technique » : aucune ligne de leur code, donc aucune
exposition GPL v3, et ça sert directement le modèle au lieu d'accélérer l'IA.

---

## 5ter. Inventaire des grandeurs qu'AAAHogEx consulte

*(Troisième passe, motivée par la question « que regarde-t-il exactement dans ses estimations de
construction ? ». Trié par calculabilité chez nous **avant** le pathfinding — c'est le seul tri qui
nous serve, puisque tout ce qui n'est connu qu'après le tracé est une fuite pour l'étage 1.)*

### Catégorie I — calculable avant le pathfinding

**Économique**
| Grandeur | API | Réf. |
|---|---|---|
| Production mensuelle source/destination | `AITile.GetCargoProduction` | `place.nut:2327-2344`, `2380-2431` |
| Acceptation réelle à destination | `AITile.GetCargoAcceptance` | `place.nut:2747-2768`, `2450-2464` |
| Cargo compatible | listes de cargo | `place.nut:1026-1079` |
| Capacité / vitesse / traction / prix du moteur | `AIEngine.*` | `estimator.nut:1296-1353`, `1454-1548` |
| Liquidités, coût théorique de voie, entretien | financier + agrégation réseau | `estimator.nut:549-562`, `route.nut:4149-4169` |
| Longueur de quai exigée par la rame | `AIGameSettings.GetValue` | `station.nut:1322-1357` |

**Autour des gares — la partie que nous n'exploitons pas du tout**
| Grandeur | API | Réf. |
|---|---|---|
| **Nombre de sites de gare réellement faisables** près de chaque ville | `AITile.IsBuildableRectangle`, `GetMaxHeight`/`GetMinHeight` (amplitude < 3) | `station.nut:1368-1389` |
| Pré-filtre d'emprise : rectangle constructible, écart de hauteur des coins ≤ 2 | `IsBuildableRectangle`, `GetMaxHeight` | `station.nut:2707-2717` |
| Faisabilité testée du vrai bâtiment, sans mutation | `AITestMode` + `AIRail.BuildRailStation` | `station.nut:841-890`, `1041-1045` |
| Score d'orientation de la gare vers l'autre extrémité | `AIMap.GetTileIndex`, `DistanceSquare` | `station.nut:939-957` |
| Distance entre sorties de quai et autre gare | `AIMap.DistanceManhattan` | `station.nut:1014-1022` |
| Production/acceptation couvertes par le rectangle de quai | `GetCargoProduction`/`Acceptance` | `station.nut:997-1026` |
| **Occupation locale des sorties** : rails voisins, propriétaire, gare ou jonction existante | `AITile.GetOwner`, `AICompany.IsMine`, `AIRail.GetRailTracks`, `AIStation.GetStationID` | `station.nut:2019-2028`, `2720-2735` |

La **jointure rail** n'est pas dans cette table : c'est un mode de placement (groupe + spread),
pas une grandeur d'étage 1. Note dédiée : `docs/aaahogex_rail_join.md`.

**Terrain sur corridor — DÉJÀ ESSAYÉ, DÉJÀ ÉCHOUÉ, ne pas y revenir**
`IsLandConnectedForRail` (séquence maritime contiguë, seuil 13) → notre `corridor_max_water_run`
fait **moins bien** que le total d'eau. `GetSlopeLevel` (pente tous les 8 pas) → notre
`corridor_max_uphill_step` fait **moins bien** que l'amplitude. Ensemble : **−0,0020 d'AUC**,
1 pli sur 5.

### Catégorie II — connu seulement pendant/après le chemin (fuite pour l'étage 1)

Longueur réelle et ratio détour/Manhattan (`route.nut:3942-3948`) ; composition du tracé — tuiles,
diagonales, virages serrés, pentes, côtes, croisements de route, ponts, tunnels
(`pathfinder.nut:504-771`) ; coût A* cumulé `g` (`aystar.nut:229-260`) ; pente réellement subie
selon le sens de circulation (`pathfinder.nut:675-693`) ; faisabilité du doublement de voie
(`pathfinder.nut:712-761`).

### Catégorie III — non transposable

Cache d'estimations discrétisées (`route.nut:91-125`) ; production ajustée par correspondances et
graphe de lignes existantes (`estimator.nut:126-208`) ; entretien réparti sur tout son réseau
(`route.nut:4149-4169`) ; gares partageables et groupes de stations (`station.nut:1761-1810`) ;
**mémoire des paires déjà impossibles** (`place.nut:758-785`, `975-1000`) — celle-ci serait de
surcroît une **fuite temporelle** si on la copiait comme feature.

### La fonction de coût de son pathfinder, pour mémoire

Tuile ordinaire / diagonale / diagonale en mer répétée ; virage ordinaire ; virage serré, virage
serré du retour, virage serré près du but, demi-tour gauche près du but ; croisement de route
(`HasTransportType`) ; côte et mer ; **pente pondérée par la traction et la puissance du moteur**
(`pathfinder.nut:165-180`, `675-693`) ; tunnel et pont avec deux seuils de surcoût chacun ; tuiles
« dangereuses » fournies par l'appelant. Trois termes sont déclarés mais **inactifs** dans cette
version : `_cost_crossing_rail`, `_cost_crossing_reverse`, `_cost_under_bridge`.

Son heuristique n'est **pas admissible** : `_Estimate` multiplie le coût octile minimal par 2 puis
ajoute un biais de guidage (`pathfinder.nut:791-820`), alors que le commentaire d'AyStar exige de
ne pas surestimer (`aystar.nut:25-31`). C'est un score de recherche pondéré, pas une borne.

---

## 5quater. La sonde de recherche tronquée — la piste retenue

Toutes les mesures du corridor direct ont échoué parce qu'elles tentent de **deviner la difficulté
du pathfinding sans faire de pathfinding**. Un cas échoue en `PATHLIM` avec une séquence d'eau
contiguë de 2 : son obstacle est sur le détour, pas sur la droite.

**L'idée** : observer l'état de l'A* à quelques instantanés précoces (500, 2 000, 5 000 itérations)
et en faire des features. La recherche **se poursuit ensuite normalement** — on n'ajoute aucune
itération, on lit ce qu'on dépensait déjà.

**Faisabilité vérifiée au source des bibliothèques** (lisibles dans le volume Docker, pas sur
l'hôte) :

- `Pathfinder.Rail` v1 : `Rail._pathfinder` référence l'objet AyStar (l. 17, 37). Squirrel n'a pas
  de visibilité privée.
- **`Graph.AyStar` v4 ne nettoie `_open`/`_closed` que sur terminaison** (`_CleanPath()`) : après
  un `FindPath()` rendant `false`, l'état est intact.
- `_open` est un `Queue.BinaryHeap` v1 → **`Peek()`** (sans retirer) et **`Count()`**.
- `_closed` est une `AIList` → `Count()`.
- Le nœud rendu expose **`GetTile()`**, **`GetCost()`** (coût cumulé `g`), `GetParent()`.

**Grandeurs mesurables** : tuiles fermées (volume exploré), taille de la frontière, coût cumulé du
meilleur nœud, distance restante de ce nœud au but, et le rapport entre coût dépensé et distance
gagnée — la difficulté du détour.

**Pourquoi elle passe le test qui a tué les autres** : toutes les features rejetées étaient
redondantes avec la distance. Deux trajets de 100 tuiles, l'un en plaine, l'autre coincé par un
lac, donnent des sondes radicalement différentes à distance identique.

**Réserve** : à 500 itérations, un trajet long peut n'avoir encore rencontré aucun obstacle
décisif. D'où les instantanés multiples — la *trajectoire* de l'exploration dit plus qu'un point
isolé. Et une recherche qui se termine avant 500 itérations est en soi le signal le plus fort qui
soit ; il faut alors une sentinelle non ambiguë, surtout pas 0.

---

## 5quinquies. `estimator.nut` : idées économiques, pas code à reprendre

Relecture clean-room du 2026-08-31. La différence la plus importante n'est pas une formule de
revenu isolée : AAAHogEx change de **fonction objectif selon la contrainte active**. Quand la
compagnie manque d'argent, il classe par revenu annuel rapporté au capital (ROI) ; riche et loin
du plafond de véhicules, par revenu rapporté à un temps de construction heuristique ; près du
plafond, par revenu rapporté au nombre de véhicules. Son rythme initial vient donc en partie d'un
arbitrage de capital, puis d'un arbitrage de débit. Son `buildingTime` reste toutefois une formule
arbitraire en distance et nombre de véhicules : pour notre objectif, les itérations A* mesurées
par OpexAI sont un meilleur dénominateur et ne doivent pas être remplacées.

L'estimateur simule aussi le couplage **production -> stock -> attente de plein chargement ->
intervalle de passage -> note de gare -> quantité captée**, inclut temps de chargement, trajet de
retour, cargaison retour/secondaire, entretien d'infrastructure, fiabilité, composition complète
de la rame et délai avant encaissement. Une partie est spécifique à son graphe de transferts ou à
son constructeur ; plusieurs coefficients portent des TODO ou sont explicitement arbitraires.

Comparaison avec OpexAI : traction, longueur de rame, nombre de trains, trajets chargés dans les
deux sens, note fonction du headway, capital, coût courant et amortissement sont déjà présents.
Le fret est calibré à `predit/reel = 1,001` à vingt ans ; ajouter toute la complexité AAAHogEx
risquerait donc surtout de consommer des opcodes. Deux écarts seulement méritent une mesure :

1. **Temps de chargement et attente du plein.** OpexAI calcule le cycle avec le trajet seul. Un
   modèle analytique dérivé des règles OpenTTD peut refermer la boucle attente/frequence/note sans
   reprendre l'algorithme AAAHogEx. Candidat prioritaire pour expliquer le pax encore optimiste de
   22,2 %, à tester séparément du fret déjà juste.
2. **Ressource financière rare.** Conserver `profit attendu / opcodes A* attendus` comme premier
   objectif. Parmi les candidats actuellement finançables -- ou dont les scores primaires sont
   indiscernables dans l'erreur du modèle -- utiliser délai de retour du capital puis
   profit/véhicule comme départages. Ne jamais bloquer la file sur un candidat non finançable : le
   banc dynamique a déjà montré que cela casse la croissance composée.

Protocole avant tout changement de décision : instrumenter hors ligne `tempsChargement`,
`attentePlein`, `notePredite`, `delaiPremierRevenu` et `profit/capital`; comparer modèle courant et
modèle enrichi sur les **mêmes lignes** par erreur absolue logarithmique prédit/réel, séparée
pax/fret et par distance. Un A/B de classement n'est justifié que si la précision hors graine
s'améliore sans dégrader le fret. Les cargaisons secondaires, doubles locomotives et transferts
restent hors périmètre tant que le constructeur OpexAI ne sait pas les réaliser.

## 6. Ce qu'il reste à retenir

| Idée | Verdict |
|---|---|
| **Attente de plein -> frequence -> note -> captation** (§5quinquies) | **PROCHAINE SONDE ECONOMIQUE** — modèle analytique clean-room, validation prédit/réel hors graine avant tout A/B |
| Objectif variable ROI / débit / véhicule (§5quinquies) | **Idée à adapter, pas à copier** — profit/opcode reste premier ; ROI seulement pour finançabilité ou départage dans l'incertitude |
| **Sonde d'A\* tronquée** (§5quater) | **LA piste retenue** — faisabilité vérifiée au source, coût nul, seule grandeur non redondante avec la distance |
| Sites de gare faisables, occupation des sorties (§5ter, cat. I) | **Inexploité chez nous** — mesures locales aux extrémités, de nature différente du corridor |
| Pré-filtre `IsLandConnectedForRail` (§5bis) | **ESSAYÉ, ÉCHOUÉ** : `corridor_max_water_run` fait moins bien que le total d'eau ; avec la raideur, −0,0020 d'AUC |
| Construction incrémentale | **Inexistante** dans AAAHogEx — l'hypothèse de départ était fausse |
| Ponts/tunnels en voisins d'A* arbitrés par le coût | **Déjà présent** chez nous via `Pathfinder.Rail` |
| `RetryToBuild` conservant le préfixe construit | **À retenir** — sans risque pour la barrière |
| Dépiler plusieurs candidats jusqu'à épuisement | Non transposable : `pair_rank` est imposé, c'est un instrument de mesure |
| Gares construites avant le pathfinding | Non transposable : muterait avant la barrière |
| Réévaluation de rentabilité après tracé | **N'existe pas** — l'estimateur garde `pathDistance = distance`, comme le nôtre |
| Terrassement pendant la pose | À retenir, mais impose de généraliser la capture de `first_mutation_tick` |
| Pilotage par budget d'opcodes | **N'existe pas** — il mesure, il ne s'adapte pas |

**Recommandation** : pas de portage, pas d'exposition GPL v3. Pour l'économie, mesurer d'abord la
boucle attente/frequence/note avec nos propres équations et nos lignes réelles ; pour le coût A\*,
la sonde tronquée reste la piste non redondante. Le changement de score d'AAAHogEx explique une
partie de son débit, mais ne remplace pas notre objectif profit/opcode. Idée secondaire à
réimplémenter en clean-room si besoin : la reprise conservant le préfixe (§2.2).

---

*Rapport d'origine produit par une session Codex, reprise possible via
`codex resume 01a0427d-aece-7ba1-8910-72fb3e773b98`. Les affirmations §1 (planifie puis construit,
découpage à 50 itérations) et §5 (défauts de la bibliothèque, résultat 0/9) ont été revérifiées
directement dans le code et par la mesure.*
