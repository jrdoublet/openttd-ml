# OpexAI multimodale : avion et bateau

Implémentation du 2026-08-28, ciblée sur **OpenTTD 15.3 / API NoAI 15**. Ces deux modes
complètent le constructeur ferroviaire sans réutiliser son modèle de coût A* : ils ont leur
propre catalogue, leur planification bornée, leur garde de trésorerie et leur transaction de
construction.

## Orchestration annuelle

`ai/OpexAI/main.nut` rafraîchit le catalogue puis tente, dans cet ordre :

1. au plus une liaison aérienne de passagers ;
2. au plus une liaison maritime de passagers ;
3. les candidats ferroviaires classés par profit attendu / coût de recherche.

Après un rechargement, OpexAI recherche les véhicules `VT_AIR` et `VT_WATER` déjà présents
avant de construire. Cela empêche les doublons même si l'état en mémoire de l'IA a été perdu.
Les liaisons réussies rejoignent `_lines`, ce qui permet de réutiliser le reporting des stations,
du profit des véhicules et la protection contre la cannibalisation des lignes ferroviaires.

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

- une seule liaison de chaque mode ;
- passagers uniquement pour l'air et l'eau ;
- classement encore heuristique, sans modèle de profit multimodal calibré ;
- aucun canal, écluse ou bouée ; une paire sans composante d'eau naturelle commune est ignorée ;
- la reconstruction après chargement est évitée par scan des véhicules, mais OpexAI ne possède
  toujours pas de schéma `Save` / `Load` persistant pour ses tables de lignes.
