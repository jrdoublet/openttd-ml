# OpexAI multimodale : avion, bateau et route

Implémentation du 2026-08-28, ciblée sur **OpenTTD 15.3 / API NoAI 15**. Ces trois modes
complètent le constructeur ferroviaire sans réutiliser son modèle de coût A* : ils ont leur
propre catalogue, leur planification bornée, leur garde de trésorerie et leur transaction de
construction.

## Orchestration annuelle

`ai/OpexAI/main.nut` rafraîchit le catalogue puis tente, dans cet ordre :

1. les candidats ferroviaires classés par profit attendu / coût de recherche ;
2. la phase routière (jusqu'à 3 lignes, bus et camions, bande 5–25 tuiles) — `road_mode`, défaut 1 ;
3. au plus une liaison aérienne de passagers ;
4. au plus une liaison maritime de passagers.

Le rail choisit en premier : il vaut un ordre de grandeur de plus par ligne et dispute les mêmes
origines et la même trésorerie. Après un rechargement, OpexAI recherche les véhicules `VT_AIR` et
`VT_WATER` déjà présents avant de construire. Les liaisons aérienne et maritime réussies
rejoignent `_lines`. Les lignes routières aussi, mais `OpexOriginServed(..., includeRoad = false)`
et `_tooClose` les ignorent : un bus de 12 tuiles n'épuise pas une ville contre le rail.

**Route.** La v1 (une liaison bus, désactivée après notes −1) est **périmée**. Le mode actuel est
une phase annuelle adoptée au banc ; état, bugs, SITE/TRACEX et ce qui reste :
[`docs/opexai_route.md`](opexai_route.md). Les chiffres de coût `Pathfinder.Road` (696 794
opcodes) contre le L Manhattan (171 356) ci-dessous restent la raison pour laquelle on n'importe
pas l'A* routier.

## Liaison routière v1 (historique, 2026-08-28)

`builder_road.nut` implémente une transaction pour **un bus entre deux villes distantes de 5 à
25 tuiles** (trace concret plafonné à 32 tuiles pour la marge des arrêts). Elle choisit les paires
par population, cherche des arrêts bordant une route municipale et ayant des producteurs de
passagers dans leur vraie empreinte (`AITile.GetCargoProduction`), puis essaie seulement les deux
tracés en L. Chaque arête est prévalidée sous `AITestMode`, construite avec `AIRoad.BuildRoad`, et
contrôlée par `AIRoad.AreRoadTilesConnected` ; le dépôt et les arrêts sont ensuite vérifiés par
leur tuile frontale API (`GetRoadDepotFrontTile` / `GetRoadStationFrontTile`). Ces deux objets ne
sont pas des `IsRoadTile`, donc `AreRoadTilesConnected(objet, front)` ne convient pas à leur
interface, contrairement aux arêtes du tracé.

Le catalogue pose explicitement `ROADTYPE_ROAD`, ses coûts (tuile, arrêt, dépôt) et les bus
constructibles. Un moteur est gardé seulement s'il peut **et a de la puissance** sur cette route,
et s'il porte déjà les passagers ou peut les refitter. La capacité réellement refittée est relue
dans le dépôt avant achat.

Le rollback inverse strictement : bus, dépôt, arrêt B, arrêt A, puis les seules arêtes que la
transaction avait ajoutées. Une route municipale préexistante n'est jamais supprimée. Les ordres
`OF_NONE` sont vérifiés (exactement deux) avant le démarrage.

### Choix de pathfinding et coût mesuré

`Pathfinder.Road` est disponible (`5046524f`, version 4), mais n'est **pas importé** par OpexAI et
donc n'ajoute aucune dépendance au harnais. Sur la graine 42, la sonde de la paire la plus proche
(villes 38–22, 20 tuiles) a mesuré **696 794 opcodes** pour `RoadPathFinder` (500 itérations, chemin
de 17 nœuds). Le premier contrôle d'un L Manhattan coûtait 121 opcodes mais coupait un obstacle
depuis les centres : ce n'était pas une solution constructive. Le plan réellement validé par les
arrêts et les `AITestMode` coûte **171 356 opcodes** — 17,1 ticks d'exécution contre 69,7 — sans A*.
Il est borné et ne tente ni pont, ni tunnel, ni boucle de gares. C'est le meilleur choix mesuré
pour une seule liaison de 5–25 tuiles ; l'A* et les extensions pont/tunnel sont écartés pour leur
coût, pas supposés inutiles universellement.

### Résultat économique v1 : ne pas activer (périmé)

⚠️ **Périmé le 2026-08-29.** Le non-chargement était un bug (façade de dépôt, bit de route
perpendiculaire), pas une condamnation du mode. Le mode route est **actif**, défaut 1, voir
`docs/opexai_route.md`. Le paragraphe ci-dessous est la mesure qui a justifié
`ROAD_BUILD_ENABLED = false` pendant 24 h.

La transaction a été vérifiée en jeu sur les villes **27 (57,25)** et **33 (58,47)**, distantes de
23 tuiles (trace 24), avec un bus passagers de 35 places. Coût réellement débité : **10 092**.
Elle a bien construit deux arrêts, un dépôt et le véhicule, mais son profit réel est resté
**−588** en 1971 puis entre **−599 et −601/an** de 1972 à 1989 (coût de fonctionnement 600/an,
recettes entre −1 et 12 ; notes passagers des deux arrêts toujours −1).

La campagne active de 20 ans tombe à 12 lignes rail, `company_value` **1 749 226**, emprunt 0 et
`performance_history` 389, contre la baseline 16 lignes, **2 787 970**, 0 et 521. Le constructeur
reste donc dans le dépôt, mais `ROAD_BUILD_ENABLED = false` : la branche correspondante de
`Start()` n'appelle `_tryBuildRoad(year)` que lors d'une réactivation explicite. Le
rafraîchissement route est lui aussi sauté tant que le mode est inactif, afin de préserver le débit
de la baseline validée.

Cette décision ne réutilise pas `OpexLineEconomics` : ses paramètres (note de gare 50 %, part de
ville 22 %, fréquence cible et économie de convoi) sont calibrés pour le rail. Leur transposition
au bus n'a **pas** été vérifiée. `GetCargoProduction` ne compte que les producteurs dans le bassin,
pas le débit réellement collecté ; même après ce filtre, la recette observée ci-dessus reste nulle
en pratique. Il faut expliquer cette absence de chargement et mesurer une famille de paires avant
de proposer une réactivation.

La route ne participe volontairement ni à `OpexOriginServed` ni à `_tooClose` : un bus local peut
desservir une ville déjà reliée par rail, et ne doit pas interdire son train interurbain. (Toujours
vrai dans le mode actuel.) La v1 n'avait qu'une transaction, gardée par `_roadBuilt` ; ce garde-fou
n'existe plus, les lignes routières sont dans `_lines`.

## Liaison aérienne

Le catalogue essaie `AT_LARGE`, puis `AT_SMALL` et `AT_COMMUTER`. Un gros avion n'est jamais
retenu pour une piste courte. Parmi les moteurs constructibles et refittables en passagers, le
choix privilégie la capacité puis la vitesse.

`builder_air.nut` :

- trie les villes par population et examine les douze plus grandes ;
- cherche un emplacement dans un rayon de 35 tuiles, couvert par la ville et accepté par
  `AIAirport.BuildAirport` sous `AITestMode` ;
- plafonne la recherche à 1 200 essais de construction, partagés entre les villes ;
- exige 30 tuiles au minimum entre les villes et vérifie la portée avec
  `AIOrder.GetOrderDistance` / `AIEngine.GetMaximumOrderDistance` ;
- construit les deux aéroports, achète et refitte l'avion dans le hangar du premier, ajoute deux
  ordres `OF_NONE`, exige exactement deux ordres, puis démarre l'appareil.

La garde de capital couvre deux aéroports, l'avion, `CASH_RESERVE` et une marge de 50 000 pour le
nettoyage et les fondations. Sur tout échec après mutation, l'avion est vendu avant la suppression
des aéroports. Les blocs d'opcodes sont mesurés sous `cat_air`, `build_air_plans`,
`build_airports` et `build_aircraft`.

## Liaison maritime

La première version transporte des **passagers entre deux grandes villes côtières**. Ce choix
donne un scénario reproductible ; les sondes industrielles ne trouvaient pas de couple de docks
fiable sur les graines testées.

Le catalogue conserve tous les bateaux constructibles et refittables en passagers. Le bateau
n'est choisi qu'après construction du dépôt, grâce à
`AIVehicle.GetBuildWithRefitCapacity` : la capacité par défaut d'un moteur ne décrit pas
nécessairement sa capacité après refit, notamment avec un NewGRF multi-cargos.

`builder_water.nut` :

- examine les douze plus grandes villes et impose une distance minimale de 45 tuiles ;
- borne la recherche à 720 essais de docks ;
- prévalide chaque dock avec `AIMarine.BuildDock` sous `AITestMode` ;
- cherche la connexion par BFS à quatre voisins, avec `AIMarine.AreWaterTilesConnected` sur
  chaque arête eau-eau, une marge spatiale de 24 tuiles et un plafond de 12 000 nœuds ;
- construit les deux docks, retrouve pour chacun sa partie aquatique puis toutes ses tuiles
  d'accès navigables, et rejoue le BFS sur les structures réelles ;
- cherche ensuite le dépôt sur cette composante, avec au plus 96 essais sous `AITestMode`. Le
  dépôt est volontairement choisi **après** les docks, car un dock peut occuper une empreinte qui
  était libre pendant la planification ;
- choisit le meilleur bateau à portée selon sa capacité passagers après refit, puis sa vitesse ;
- achète le bateau, vérifie sa capacité effective, ajoute deux ordres `OF_NONE`, exige exactement
  deux ordres et le démarre.

Un dock OpenTTD occupe deux tuiles de station : l'ancre terrestre et une partie aquatique. Cette
partie aquatique n'est pas une tuile eau utilisable avec `AreWaterTilesConnected`. Le constructeur
repère donc les tuiles d'eau navigables adjacentes à la partie aquatique et démarre le BFS depuis
elles. Cette distinction a été vérifiée contre l'implémentation OpenTTD 15.3 et en partie réelle.

La transaction maritime annule dans l'ordre bateau, dépôt, dock B, dock A. Les catégories
d'opcodes sont `cat_water`, `build_water_plans`, `build_docks`, `build_water_depot` et
`build_ships`. La version 1 ne construit ni canal, ni écluse, ni bouée.

## Ordres et cargo

Les deux liaisons utilisent `OF_NONE` aux terminaux. Un ordre de transfert est réservé à une
station intermédiaire : l'utiliser à la destination finale laisserait le cargo en attente sans
paiement. Les docks sont recherchés dans le rayon de couverture de leur ville. Une future liaison
maritime industrielle devra en plus vérifier explicitement l'acceptation du cargo ou construire
une correspondance avec un autre mode.

Référence manuelle : [Waterway construction](https://wiki.openttd.org/en/Manual/Waterway%20construction#operating-ships).

## Validation reproductible

Configuration commune : OpenTTD 15.3, OpenGFX 7.1, carte 256×256, année 1970, inflation
désactivée et `Pathfinder.Rail` fourni à OpexAI.

- **Avion, graine 5, deux ans** : deux aéroports 6×6, un avion passagers de capacité 300,
  exactement deux ordres, appareil observé entre les deux stations. Panneau de commit de la
  transaction : `OA|1970|126|177535|OK`.
- **Bateau, graine 24, trois ans** : exactement deux docks, un dépôt naval et un bateau passagers
  de capacité 100. Deux ordres vérifiés ; le dernier instantané montre la station 1 visitée et la
  destination courante vers la station 0, à vitesse non nulle. Panneau de commit :
  `OM|W|1970|62|373337`.
- **Coexistence, graine 24** : les transactions avion et bateau réussissent avant la construction
  de lignes ferroviaires ; les trois types de véhicules sont actifs sans erreur Squirrel.

Dans OpenTTDLab 15.3, le chunk `ORDR` peut rester vide alors que les ordres fonctionnent. La
validation croise donc le compte d'ordres au moment de la construction, les stations/dépôts et
l'état courant du véhicule dans `VEHS`.

## Limites actuelles

- une seule liaison **avion** et une seule **maritime** ;
- la route est une phase annuelle (plusieurs lignes), `road_mode` défaut 1 — voir `docs/opexai_route.md` ;
- passagers uniquement pour l'air et l'eau ; la route fait aussi du fret camion ;
- classement encore heuristique, sans modèle de profit multimodal calibré (`ROAD_PLAN_ITERATIONS_BASE` non calé sur le rail) ;
- aucun canal, écluse ou bouée ; une paire sans composante d'eau naturelle commune est ignorée
  (le trick des pseudo-canaux — inonder du terrain sec, `docs/mecanique_jeu.md` §13 — n'est pas
  un plan : un bateau pax ne le justifie pas, coût opcode/argent non mesuré) ;
- la reconstruction après chargement est évitée par scan des véhicules, mais OpexAI ne possède
  toujours pas de schéma `Save` / `Load` persistant pour ses tables de lignes.
