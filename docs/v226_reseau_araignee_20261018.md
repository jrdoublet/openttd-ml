# V226 — Diagnostic et conception : réseau ferré « en araignée » (modèle AAAHogEx)

Date : **18 octobre 2026**  
Branche : `v226` (issue de `master`)  
Auteur : Agent Antigravity (d'après analyse du code d'AAAHogEx-115, mesures de bancs existants et historique d'OpexAI)

---

## Introduction

Dans OpexAI, l'infrastructure ferroviaire est historiquement conçue comme un ensemble de **lignes point-à-point isolées** : chaque ligne relie une origine $A$ à une destination $B$ avec ses propres quais, sa propre voie unique (ou double) dédiée, son propre dépôt et ses propres rames en navette fermée. Toute interconnexion physique ou logique entre lignes est rigoureusement bloquée à la génération par la règle `origin_served` (`candidates.nut:1021`, `candidates.nut:1102`), ainsi qu'à la pose par le filtre de proximité `_tooClose` (`task_rail.nut:271`).

À l'inverse, l'adversaire de référence **AAAHogEx-115** déploie un réseau ferré articulé « en araignée » (*hub-and-spoke*) caractérisé par :
1. La convergence de plusieurs branches de collecte vers des gares ou nœuds déjà desservis ;
2. L'enchaînement de villes ou de débouchés sur un même axe ferroviaire ;
3. L'usage massif d'ordres de **transfert** (`OF_TRANSFER`), tant en rabattement multimodal (bus/train vers aéroport ou gare principale) qu'en consolidation de fret ;
4. Des mécanismes explicites de gestion de la saturation des gares et de partage de capacité.

Deux prototypes antérieurs (`v193_chain_towns` et `v194_short_to_served_dst`) ont tenté d'amorcer ces comportements avant d'être retirés le 17/10 en V227 après des résultats négatifs en bancs 3 ans rail seul.

Ce document établit :
- L'analyse détaillée de l'architecture ferroviaire d'AAAHogEx avec preuves `fichier:ligne` ;
- Une mesure empirique sur les journaux de parties réelles de notre banc ;
- L'analyse des causes d'échec de V193 et V194 ;
- Trois propositions de conception concrètes, modulaires et chiffrées, adaptées au code courant d'OpexAI.

---

## 1. Structure du réseau ferré d'AAAHogEx (preuves dans `ai/AAAHogEx-115`)

L'implémentation d'AAAHogEx repose sur une modélisation hiérarchique très différente du simple couple `(tileA, tileB)` d'OpexAI.

### 1.1 La brique fondamentale : `StationGroup` vs `HgStation`
- **Définition et rôle** (`ai/AAAHogEx-115/station.nut:2-150`) :  
  Une gare logique dans AAAHogEx est un `StationGroup` (classe `StationGroup`). Ce groupe agrège une ou plusieurs implantations physiques (`hgStations`, tableau d'`HgStation`).
- **Création et nommage** (`station.nut:1894-1905`, `station.nut:2406-2432`) :  
  Chaque `HgStation` créée est enregistrée dans un `StationGroup` (`stationGroup.AddHgStation(this)`). Le nom public OpenTTD de la gare reçoit comme préfixe l'identifiant formaté sur 4 chiffres du groupe (`s = "0000".slice(0, max(0, 4 - s.len())) + s;`, ligne 2415), visible dans les logs (ex. `0001Danville`, `0027Sinfingfield`).
- **Suivi des lignes** (`station.nut:84-121`, `station.nut:136-142`) :  
  Le `StationGroup` maintient les listes des lignes qui l'utilisent : `usingRoutesAsDest` et `usingRoutesAsSource`. Plusieurs lignes peuvent ainsi partager le même pôle multimodal.

### 1.2 Choix de la destination : gare existante vs nouvelle gare
AAAHogEx distingue deux mécanismes majeurs de sélection :

1. **Génération de lignes indépendantes** (`ai/AAAHogEx-115/main.nut:879`, `GetRouteCandidatesGen`) :  
   Évalue des paires directes origine-destination entre industries primaires et transformateurs/villes.
2. **Génération de lignes de transfert vers gare existante** (`ai/AAAHogEx-115/main.nut:895`, `GetTransferCandidates`) :  
   - Appelée à chaque cycle de planification dans `ScanPlaces()` (`main.nut:895`).
   - Parcourt les lignes déjà existantes (`Route.GetAllRoutes()`, `main.nut:1925-1939`).
   - Pour chaque ligne, appelle `CreateTransferPlans(route, isDest, vehicleType)` (`main.nut:1986-1989`, `main.nut:2163-2340`).
   - Recherche des sources productrices dans un rayon de 0 à 500 tuiles pour le rail (`main.nut:2180-2182`) et fixe la destination du plan sur le `StationGroup` de la gare existante :
     ```squirrel
     t.dest <- hgStation.stationGroup;  // main.nut:2277
     ```
   - Lors de la construction dans `BuildRoute` (`ai/AAAHogEx-115/trainroute.nut:2887`) :
     ```squirrel
     local isTransfer = options.rawin("transfer") ? options.transfer : (dest instanceof StationGroup);
     ```
     Dès que `dest` est un `StationGroup`, la ligne est automatiquement typée comme ligne de transfert.
   - Implantation physique : `CreateBestOnStationGroup` (`station.nut:893-916`) utilise `GetStationCandidatesInSpread` (`station.nut:184-213`) pour trouver un emplacement de quai contigu ou proche dans la limite de `maxStationSpread` (jusqu'à 12 tuiles, `station.nut:193-195`) et utilise `AIStation.STATION_JOIN_ADJACENT` (`station.nut:2060`) pour fusionner la nouvelle structure au `StationGroup` existant.

### 1.3 Embranchements sur voie existante vs nouvelle voie
AAAHogEx évite de reposer des voies parallèles redondantes grâce à deux constructeurs spécialisés :

1. **Extension de ligne (`TrainRouteExtendBuilder`)** (`ai/AAAHogEx-115/main.nut:3149-3387`, `trainroute.nut:3161-3288`) :  
   - Déclenchement : dans `SearchAndBuildAdditionalDest` (`main.nut:3149`), si la ligne existante est plus courte que sa distance idéale (`TrainRoute.GetIdealDistance(route.cargo) - route.pathDistance >= 100`, `main.nut:3187-3190`), AAA cherche une destination supplémentaire plus lointaine via `Place.SearchAdditionalAcceptingPlaces` (`main.nut:3300-3360`).
   - Construction : `TrainRouteExtendBuilder` pose une nouvelle gare terminus à la destination additionnelle (`trainroute.nut:3197-3215`).
   - Raccordement par embranchement : `TwoWayPathToStationRailBuilder` (`railbuilder.nut:2487-2580`) trouve le tracé entre la voie existante et la nouvelle gare. Puis `CombineByFork` raccorde physiquement les voies (`trainroute.nut:3267-3268`) :
     ```squirrel
     local removeRemain1 = route.pathSrcToDest.CombineByFork(railBuilder.buildedPath1, false);
     local removeRemain2 = route.pathDestToSrc.CombineByFork(railBuilder.buildedPath2, true);
     ```
   - Algorithme `CombineByFork` (`ai/AAAHogEx-115/railbuilder.nut:930-967`) : identifie la tuile d'embranchement (`pointTile = forkPath.tile`, ligne 948), tronque la voie existante à ce point (`SubPathEnd(pointTile)`, ligne 950) et fusionne avec le nouveau chemin (`remainPath.Combine(forkPath)`, ligne 954).
   - Préservation de l'ancien terminus : l'ancien tronçon vers l'ancienne gare est enregistré dans `branchLines` (`trainroute.nut:3278`) :
     ```squirrel
     route.AddBranchLine(lastStation, BuildedPath(removePath1, route), BuildedPath(removePath2, route));
     ```
     Si la nouvelle industrie cesse d'accepter le cargo (fréquent en ECS ou climat économique), AAAHogEx réactive l'ancien terminus grâce à `ChangeDestination` (`trainroute.nut:1449-1520`, `2577`).
2. **Lignes de retour et transfert médian (`TrainReturnRouteBuilder`)** (`ai/AAAHogEx-115/main.nut:3389-3413`, `trainroute.nut:3291-3479`) :  
   - Sur les lignes longues ($\ge 800$ tuiles, `main.nut:3395`), AAA recherche des flux retour le long de la voie (`SearchReturnPlacePairs`, `main.nut:3398`).
   - Il implante une gare de transfert médiane au bord de la voie retour existante (`GetBuildableStationByPath`, `trainroute.nut:3372-3377`), raccorde les voies par embranchement (`trainroute.nut:3400-3453`) et crée une ligne de retour `TrainReturnRoute` (`trainroute.nut:3456-3477`).

### 1.4 Gares partagées entre routes
- Dans AAAHogEx, une gare (physique ou `StationGroup`) accueille couramment plusieurs lignes :
  - Soit par ajout de quais rattachés (`AIStation.STATION_JOIN_ADJACENT`, `station.nut:2060`) ;
  - Soit par utilisation conjointe des quais pour des cargaisons compatibles ;
  - Soit en interface intermodale : un `StationGroup` urbain reçoit simultanément des trains de passagers, des bus urbains de rabattement, et une ligne aérienne vers un autre pôle.

### 1.5 Transferts et ordres de mission (unload, transfer, full load)
La gestion des ordres dans `ai/AAAHogEx-115/trainroute.nut` met en œuvre des mécanismes NoAI avancés :

- **Ordres de base d'un train** (`trainroute.nut:1328-1342`, `BuildOrder`) :
  - Origine : chargement complet non-stop :
    ```squirrel
    AIOrder.AppendOrder(engineVehicle, srcHgStation.platformTile, AIOrder.OF_FULL_LOAD_ANY + AIOrder.OF_NON_STOP_INTERMEDIATE); // l. 1330
    ```
  - Dépôt : passage conditionnel pour entretien :
    ```squirrel
    AIOrder.AppendOrder(engineVehicle, srcDepot, AIOrder.OF_SERVICE_IF_NEEDED); // l. 1332
    ```
  - Destination :
    - Si transfert (`IsTransfer()`) : ordre de **transfert sans rechargement** :
      ```squirrel
      AIOrder.AppendOrder(engineVehicle, destHgStation.platformTile, AIOrder.OF_NON_STOP_INTERMEDIATE + AIOrder.OF_TRANSFER + AIOrder.OF_NO_LOAD); // l. 1334
      ```
    - Si bidirectionnel : `OF_NON_STOP_INTERMEDIATE` (l. 1336).
    - Sinon (terminus normal) : déchargement complet sans rechargement :
      ```squirrel
      AIOrder.AppendOrder(engineVehicle, destHgStation.platformTile, AIOrder.OF_NON_STOP_INTERMEDIATE + AIOrder.OF_UNLOAD + AIOrder.OF_NO_LOAD); // l. 1338
      ```
- **Ordres conditionnels sur boucle de retour** (`trainroute.nut:1350-1366`, `AddReturnTransferOrder`) :
  - Arrêt à la gare de transfert : `OF_NON_STOP_INTERMEDIATE` (l. 1355).
  - Saut conditionnel si le train est vide :
    ```squirrel
    local conditionOrderPosition = AIOrder.GetOrderCount(vehicle);
    AIOrder.AppendConditionalOrder(vehicle, 0); // l. 1359
    AIOrder.SetOrderCompareValue(vehicle, conditionOrderPosition, 0); // l. 1360
    AIOrder.SetOrderCompareFunction(vehicle, conditionOrderPosition, AIOrder.CF_EQUALS); // l. 1361
    AIOrder.SetOrderCondition(vehicle, conditionOrderPosition, AIOrder.OC_LOAD_PERCENTAGE); // l. 1362
    ```
    Si le pourcentage de charge est de 0 % (pas de fret retour disponible au transfert), le train saute directement l'ordre de la gare de destination retour pour éviter un voyage à vide inutile !
  - Destination retour : déchargement sans rechargement (`OF_UNLOAD + OF_NO_LOAD`, l. 1364).
- **Modification d'ordres en ligne** (`trainroute.nut:1497-1520`, `ChangeDestination`) :  
  Lors d'une extension de ligne, AAA modifie dynamiquement la feuille de route du train en service via `AIOrder.InsertOrder` (l. 1502) et `AIOrder.RemoveOrder` (l. 1517), sans renvoyer le train au dépôt.

### 1.6 Nombre de routes par gare et prévention de la saturation
Partager des gares pose un risque immédiat d'engorgement (*deadlock* / saturation). AAAHogEx met en place quatre garde-fous stricts :

1. **Dimensionnement des quais dès la construction** :
   - `SrcRailStation.platformNum = 2` (`station.nut:4617`) pour les gares amont.
   - `TerminalStation.platformNum = 3` (`station.nut:4886`) pour les terminus.
   - En cas d'extension, `stationFactory.platformNum = 3` (`trainroute.nut:3201`) pour absorber l'afflux.
2. **Dimensionnement selon la longueur des rames** (`trainroute.nut:2905-2911`) :  
   Lorsqu'un quai est rattaché à un `StationGroup`, la longueur minimale est calée sur le maximum des longueurs de rames exploitant déjà ce pôle (`maxPlatformLength`).
3. **Éviction active au dépôt en cas d'engorgement (*anti-gridlock*)** (`trainroute.nut:2385-2387`) :
   ```squirrel
   if ((IsBiDirectional() || returnRoute != null) && srcStationStops.len() == srcHgStation.platformNum) {
       SendVehicleToDepot(srcStationStops[0]);
   }
   ```
   Si le nombre de trains arrêtés dans la gare atteint le nombre de quais disponibles (`platformNum`), AAA envoie immédiatement le premier train au dépôt pour libérer les aiguillages d'approche !
4. **Modèle de capacité résiduelle du tronc** (`ai/AAAHogEx-115/route.nut:632-677`, `GetLeftCapacity`) :  
   Avant d'autoriser un transfert vers une ligne de tronc, AAA vérifie la capacité résiduelle. Pour éviter de saturer le tronc, il plafonne la capacité admissible au tiers de la capacité maximale :
   ```squirrel
   maxCapacity = GetMaxRouteCapacity(cargo, callRoutes);
   maxCapacity = maxCapacity / 3; // route.nut:665
   local production = station.stationGroup.GetCurrentExpectedProduction(cargo, GetVehicleType(), true, callRoutes);
   local result = max(0, maxCapacity - production); // route.nut:673
   ```
   Un transfert n'est créé que si `GetLeftCapacity >= 1`.
5. **Plafond de desserte par industrie de destination** (`main.nut:3165-3177`) :  
   Au plus une ligne de livraison vers une industrie donnée (`GetRoutesUsingDest().len() == 0`).

---

## 2. Mesure sur nos journaux existants (lecture seule)

Une inspection des résultats de bancs multi-graines conservés dans les différents worktrees a été réalisée.

### 2.1 Périmètre des données analysées
Les journaux bruts du moteur OpenTTD (`--script-debug`, niveau `script=4`), qui capturent à la fois les traces `[0] [I]` (OpexAI) et `[1] [I]` (AAAHogEx), ont été analysés dans :
- `/home/deploy/projects/wt-v257rev/results/v257rev_expo3_3x4_20261018_engine/` (6 parties, 3 graines × 4 ans, duel complet) ;
- `/home/deploy/projects/wt-v259/results/v259_expo_6x10_20261018_engine/` (12 parties, 6 graines × 10 ans, duel complet) ;
- `/home/deploy/projects/wt-v233b/results/v233chain_expo_10x10_20261018_engine/` (20 parties, 10 graines × 10 ans, duel complet) ;
- `/home/deploy/projects/wt-v257tele/results/v257tele_railseul_3x3_20261018_engine/` (3 parties, 3 graines × 3 ans, rail seul).

*(Note technique : dans les répertoires de qualification Porte A stricte comme `wt-v252/results/v252m2_porteA_40x6_20261018_engine/`, les fichiers `.log` sont de taille 0 octet car `--script-debug` est désactivé par protocole de performance V102 pour ne pas fausser les temps de tick).*

### 2.2 Nombre de gares desservies par route ferroviaire

| IA | Campagne / Horizon | Nombre total de routes rail | Gares par route (à la pose) | Lignes prolongées (`Extend succeeded`) | Gares par route (après prolongement) |
|---|---|---|---|---|---|
| **OpexAI** | `v257rev` (4 ans) | 68 lignes | **2,00** (100 %) | 0 | 2,00 |
| **OpexAI** | `v259` (10 ans) | 199 lignes | **2,00** (100 %) | 0 | 2,00 |
| **OpexAI** | `v233chain` (10 ans) | 352 lignes | **2,00** (100 %) | 0 | 2,00 |
| **AAAHogEx** | `v257rev` (4 ans) | 81 routes | **2,00** (100 %) | 0 | 2,00 |
| **AAAHogEx** | `v259` (10 ans) | 366 routes | **2,00** (initial) | **11** (~0,92 / partie) | **3,00** (sur les routes prolongées) |
| **AAAHogEx** | `v233chain` (10 ans) | 650 routes | **2,00** (initial) | **15** (~0,75 / partie) | **3,00** (sur les routes prolongées) |

*Constat :* OpexAI reste figée à 2 gares par ligne tout au long des 10 ans. AAAHogEx démarre en point-à-point à 2 gares, puis étend dynamiquement environ 1 ligne par partie en créant une 3ᵉ gare raccordée par embranchement.

### 2.3 Partage des gares entre routes ferroviaires

La distribution du nombre de routes ferroviaires convergeant sur une même gare (ou `StationGroup` chez AAA) s'établit comme suit :

| Campagne | IA | Gares à 1 route | Gares à 2 routes | Gares à 3 routes | Gares à 4 routes | Part des gares partagées ($\ge 2$ routes) |
|---|---|---|---|---|---|---|
| **v257rev** (4 ans) | OpexAI | 136 (100 %) | 0 (0 %) | 0 | 0 | **0,0 %** |
| | AAAHogEx | 144 (94,1 %) | 9 (5,9 %) | 0 | 0 | **5,9 %** |
| **v259** (10 ans) | OpexAI | 396 (99,7 %) | 1 (0,3 %) | 0 | 0 | **0,3 %** *(artefact de tuile urbaine)* |
| | AAAHogEx | 503 (79,2 %) | 87 (13,7 %) | 17 (2,7 %) | 1 (0,2 %) | **16,6 % (105 gares)** |
| **v233chain** (10 ans) | OpexAI | 698 (99,6 %) | 3 (0,4 %) | 0 | 0 | **0,4 %** |
| | AAAHogEx | 923 (84,7 %) | 130 (11,9 %) | 31 (2,8 %) | 6 (0,6 %) | **15,3 % (167 gares)** |

*Constat majeur :* Chez AAAHogEx, à 10 ans, **plus de 15 % des gares ferroviaires sont partagées entre plusieurs routes**, avec jusqu'à 4 lignes convergeant sur un même pôle. Chez OpexAI, le partage est virtuellement inexistant (0,3 % à 0,4 % d'artefacts).

### 2.4 Synthèse multimodale et limites de la télémétrie
En recoupant les lignes routières et aériennes (visible sur la graine 42 de `v257rev`), on observe des hubs majeurs d'AAAHogEx tels que `Danville` (`StationGroup:0001` et `0024`) qui agrègent :
- 1 ligne aérienne passagers (`0001Danville <-> 0004Little Frundingbury [Passengers] Air`) ;
- 1 ligne aérienne courrier (`0024Danville <-> 0027Little Frundingbury [Mail] Air`) ;
- 1 ligne ferroviaire passagers en transfert (`T:0001Danville <- 0190Wunfingford [Passengers] Rail`) ;
- 1 ligne ferroviaire courrier en transfert (`T:0024Danville <- 0146Linnwell [Mail] Rail`) ;
- 2 lignes de rabattement routier courrier (`T:0024Danville <- 0166Danville #M1 [Mail] Road`, `#M2`).

*Limites de télémétrie relevées :*
- Les fichiers `.sav` OpenTTD complets ne sont pas archivés lors des campagnes headless (seuls les fichiers `.log` et `.json` sont produits).
- La géométrie fine interne des voies d'AAAHogEx (aiguillages doubles, voies de garage, longueurs exactes de chaque quai physique au sein du `StationGroup`) n'est pas consignée dans les logs textuels de haut niveau.

---

## 3. Pourquoi V193 et V194 ont échoué

Les deux tentatives précédentes ont été éliminées le 17/10 lors du chantier V227 (`5663617`). Leur analyse permet d'éviter de répéter les mêmes erreurs de conception.

### 3.1 V193 (`v193_chain_towns`, commit `9253535`)
- **Principe du prototype** :  
  V193 s'inscrivait dans le cadre du projet V88 (chaînes de biens). Face à l'explosion combinatoire de V88 (qui générait jusqu'à 11 423 candidats `CHAIN_GEN` sur une seule graine), V193 limitait la recherche aux $N$ villes les plus peuplées par couple source->usine (`V193_CHAIN_TOWNS`, 1..10, défaut 0) et n'insérait que la meilleure chaîne.
- **Résultat mesuré** (`docs/taches.md:1434`, banc rail seul 10×3 `v193_railseul_10x3_20261014`) :  
  `profit_year` variante − référence = **−31,7 k£/an** (médiane −88,4 k, 4/5, $p = 0,50$), valeur d'entreprise **−7,8 %**.
- **Analyse des causes d'échec** :
  1. *Héritage des défauts structurels de V88* : V88 planifiait conjointement deux étapes physiques (étape 1 : matières premières amont vers usine ; étape 2 : usine vers ville) mais monopolisait le créneau unique de recherche A* (`_activeGoodsChain`) et surévaluait le score du portefeuille en divisant le profit cumulé des deux étapes par le seul capital de la première étape.
  2. *Inadéquation de l'horizon de banc à 3 ans* : Une chaîne industrielle complète exige que les matières premières soient livrées pour que l'usine commence à produire des biens (délai médian mesuré de 1,85 an entre décision et étape 2, puis 217 jours jusqu'à la première livraison). Sur un banc à 3 ans, la rentabilité de l'étape 2 est nulle car la production réelle démarre à peine ; les dépenses d'infrastructure pénalisent lourdement la valeur et le profit.
  3. *Ce n'était pas un réseau convergent* : V193 générait deux lignes point-à-point consécutives, sans réutiliser les voies ni créer de tronc commun.

### 3.2 V194 (`v194_short_to_served_dst`, commit `ca4b97c`)
- **Principe du prototype** :  
  V182 (`V182_RAIL_FREIGHT_MIN_DIST = 100`) filtrait les lignes de fret de moins de 100 tuiles car le fret ferroviaire court est intrinsèquement peu rentable (30 k£/an contre 47 k£/an pour les lignes longues). V194 exemptait de ce filtre les candidats courts dont la destination était située à moins de `MIN_SEPARATION` d'une de nos gares rail existantes (`OpexV194NearOwnRailStation(dstTile)`), dans l'idée de créer des lignes d'apport vers un pôle déjà desservi.
- **Résultat mesuré** (`docs/taches.md:1436`, banc rail seul 10×3 `v194b_railseul_10x3_20261014`) :  
  `profit_year` = **−17,0 k£/an**, 2/6, $p = 0,25$ (nul/négatif).
- **Analyse des causes d'échec** :
  1. *Contradiction géométrique immédiate* : En autorisant à la génération une destination située à moins de `MIN_SEPARATION` (environ 14 tuiles) d'une gare existante, le candidat était retenu dans le vivier mais se heurtait frontalement au précheck de construction dans `task_rail.nut` :
     ```squirrel
     local close = this._tooClose(candidate); // task_rail.nut:271
     ```
     Comme aucun mécanisme de raccordement automatique de quai n'était associé à V194, le projet était rejeté avec l'erreur `too_close_no_join` dans 100 % des cas où un quai parallèle strict ne pouvait être posé.
  2. *Modèle économique déficitaire sans transfert* : Une ligne de fret courte autonome de 30 ou 50 tuiles paie le coût complet d'une locomotive, de wagons, d'un dépôt et d'un quai neuf. En l'absence de consolidation de flux ou d'ordres de transfert vers un train lourd, elle dégage un revenu dérisoire par rapport au capital engagé.

---

## 4. Propositions concrètes adaptées au code courant d'OpexAI

Pour reproduire les gains d'AAAHogEx sans reproduire les écueils de V193/V194 ni pénaliser la partie complète (où l'aérien reste le moteur de profit primaire), voici 3 propositions modulaires, chacune isolée derrière un réglage paramétrable.

### 4.1 Proposition 1 : Convergence de fret amont vers une usine commune (`v226_convergent_freight`)

#### Concept
Permettre à plusieurs sources de matières premières compatibles (ex. deux fermes céréales/bétail ou une ferme et une aciérie) de livrer la **même usine de transformation**, en raccordant physiquement les nouveaux quais à la gare existante.

#### Points d'ancrage dans le code
1. **Génération (`candidates.nut`)** :
   - Dans `OpexFreightCandidates` (`candidates.nut:1101-1105`), lorsque la destination `industries[di]` est un transformateur (`isTransformer == true`) et que nous y possédons déjà une gare rail (`sd != null`), lever l'exclusion `stats.pairsOriginServed++` si la source `source` est vierge (`ss == null`).
   - Marquer le candidat : `candidate.convergent_dest <- true; candidate.targetStationId <- sd.stationId;`.
2. **Construction des quais (`builder_rail.nut`)** :
   - Assouplir `OpexJoinPlatformPlans` (`builder_rail.nut:399-440`) : actuellement, le placement exige un parallélisme strict, une longueur identique et un terrain parfaitement plat.
   - Étendre la recherche en autorisant des quais perpendiculaires en T ou adjacents dans le rayon de `maxStationSpread` (comme `GetStationCandidatesInSpread` d'AAA), avec `AIStation.STATION_JOIN_ADJACENT`.
3. **Contrôle de proximité (`task_rail.nut`)** :
   - Dans `_tooClose` (`task_rail.nut:271`), désactiver l'interdiction `too_close_no_join` spécifiquement pour la gare de destination si `candidate.convergent_dest == true` et qu'un plan de quai joint valide a été trouvé.

#### Données nécessaires
- `stationId` de la gare destinatrice existante (déjà accessible dans `line.stationB`).
- Capacité d'acceptation de l'usine (vérification via `AICargoList_StationAccepting`).

#### Coût en opcodes
- Génération : quasi nul ($O(1)$ par industrie destinatrice).
- Construction : test de 4 à 8 positions de quais adjacents sous `AITestMode` (~1 500 à 2 000 opcodes par candidat sélectionné, strictement compensé par l'évitement de l'A* de recherche de site urbain).

#### Réglage
- `v226_convergent_freight` (booléen, 0/1, défaut 0).

#### Protocole de validation et garde « partie complète »
- **Étape 1 (Rail seul)** : 40×3 (Porte A) puis 20×10 (Porte B). Valider que le taux de rejet `SITEAB` diminue et que le profit fret amont augmente sans congestion de quai.
- **Étape 2 (Partie complète)** : 40×6 (Porte A) puis 20×10 (Porte B).  
  *Garde de cannibalisation AIR (mémoire `rail_defauts_negatifs_partie_complete`) :*  
  En 1970–1972, l'aérien offre un rendement marginal supérieur à 70 %/an. La pose d'une seconde ligne convergente ne doit pas consommer le capital d'un avion. **Conditionner le raccordement convergent à une réserve de caisse disponible $\ge 150\ 000$ £ ou à une activation à partir de 1972 (an 3)**, comme V217 (`v217_rail_refill`).

---

### 4.2 Proposition 2 : Prolongement de ligne par embranchement de voie (`v226_track_branch_extension`)

#### Concept
Transposer directement le mécanisme `TrainRouteExtendBuilder` d'AAAHogEx (`trainroute.nut:3161`). Lorsqu'une ligne de fret ou de passagers existante est courte ($< 80$ tuiles) et qu'une seconde opportunité d'acceptation existe dans le même prolongement géographique (à 40–80 tuiles de l'ancien terminus), prolonger la voie par un embranchement aiguillé plutôt que de tirer une ligne indépendante depuis l'origine.

#### Points d'ancrage dans le code
1. **Génération (`candidates.nut` / `task_rail.nut`)** :
   - Créer une micro-tâche annuelle de scan d'extension : pour chaque ligne rail active dont la longueur physique est $< 80$ tuiles, rechercher les industries ou villes acceptatrices situées à moins de 80 tuiles de l'extrémité $B$.
   - Créer un projet d'extension : `project.isExtension = true; project.baseLine = line;`.
2. **Construction de la voie (`builder_rail.nut`)** :
   - Implanter une nouvelle gare terminus à la nouvelle destination $C$.
   - Lancer l'A* segmenté (`_startRailSearch`) non pas depuis $A$, mais **depuis la tuile d'approche (`lead`) de la gare $B$** vers la nouvelle gare $C$.
   - Poser un signal PBS à l'aiguillage de bifurcation.
3. **Mise à jour des ordres (`lines.nut`)** :
   - Modifier les ordres de la rame via `AIOrder.InsertOrder` pour insérer le terminus $C$, soit en remplacement de $B$ (si $B$ était saturé ou secondaire), soit en terminus alternatif.

#### Données nécessaires
- Tracé de voie de la ligne existante (`platformB.lead`, orientation de sortie).
- Liste des véhicules affectés à la ligne existante.

#### Coût en opcodes
- **Gain net très significatif** : un pathfinding A* sur 40 à 60 tuiles consomme entre 300 et 800 itérations, contre 2 500 à 5 000 itérations pour une ligne directe de 140 tuiles depuis l'origine.

#### Réglage
- `v226_track_branch_extension` (booléen, 0/1, défaut 0).

#### Protocole de validation
- **Étape 1 (Rail seul)** : Diagnostic 10×6 pour valider la fluidité de circulation aux aiguillages PBS et vérifier l'absence totale de blocage de train.
- **Étape 2 (Partie complète)** : Porte A 40×6 puis Porte B 20×10. Vérifier que le prolongement apporte un incrément net de profit supérieur au coût de l'extension.

---

### 4.3 Proposition 3 : Rabattement ferroviaire passagers en transfert vers aéroport (`v226_rail_pax_feeder`)

#### Concept
Résoudre la cannibalisation destructive démontrée lors des essais V207/V216 (où les lignes rail passagers posées entre villes ont fait chuter le profit global de **−187 k£/an** en partie complète en siphonnant la clientèle des aéroports).  
Copier exactement la doctrine d'AAAHogEx (`T:0001Danville<-0190Wunfingford[Passengers]Rail`) : **le train de passagers ne concurrence pas l'avion, il l'alimente**. Une courte navette ferroviaire relie une ville satellite dépourvue d'aéroport à notre gare rattachée à l'aéroport principal, avec ordre de **transfert pur** (`OF_TRANSFER | OF_NO_LOAD`).

#### Points d'ancrage dans le code
1. **Génération (`candidates.nut`)** :
   - Identifier nos aéroports possédant une gare rail conjointe (ou éligibles à un quai joint).
   - Rechercher les villes situées à 30–60 tuiles de l'aéroport qui n'ont pas d'aéroport OpexAI.
   - Générer un candidat feeder : `src = ville_satellite`, `dst = gare_aeroport`, `orderMode = "transfer"`.
2. **Ordres du train (`task_rail.nut` / `lines.nut`)** :
   - À la gare de la ville satellite : `AIOrder.OF_FULL_LOAD_ANY + AIOrder.OF_NON_STOP_INTERMEDIATE`.
   - À la gare de l'aéroport : `AIOrder.OF_NON_STOP_INTERMEDIATE + AIOrder.OF_TRANSFER + AIOrder.OF_NO_LOAD`.
3. **Évaluation économique (`projects.nut`)** :
   - Ne pas utiliser le prix brut du billet train (qui est faible sur courte distance).
   - Scorer le projet sur :  
     $$\text{Score} = \text{Revenu transfert} + (\text{Passagers apportés} \times \text{Marge nette avion sur places vacantes})$$
   - Bloquer la construction si les avions au départ de l'aéroport sont déjà pleins (taux de remplissage $\ge 90$ %).

#### Données nécessaires
- Suivi du taux de remplissage moyen des avions sur le hub aéroportuaire considéré (donnée déjà présente dans les sondes C121).

#### Coût en opcodes
- Très faible : le vivier de feeder ne scanne que 1 à 3 villes satellites autour de chacun de nos 3 ou 4 aéroports existants.

#### Réglage
- `v226_rail_pax_feeder` (booléen, 0/1, défaut 0).

#### Protocole de validation
- **Uniquement en partie complète** (le banc en rail seul n'a aucun sens pour ce mécanisme puisqu'il n'y a aucun avion à alimenter en aval).
- Qualification directement sur **Porte A 40×6 ans**, suivie de **Porte B 20×10 ans**.
- Critères spécifiques d'observation : vérifier que le nombre de passagers embarqués dans les avions augmente et que la note de la station aéroportuaire reste élevée.

---

## 5. Synthèse comparative des propositions

| Axe | Proposition 1 : Convergence fret | Proposition 2 : Extension de tronc | Proposition 3 : Feeder rail $\to$ air |
|---|---|---|---|
| **Cible** | Fret matières premières (usines) | Fret et passagers interurbains | Passagers et courrier urbains |
| **Mécanisme clé** | Quais joints assouplis (`STATION_JOIN_ADJACENT`) | Bifurcation sur voie existante (`CombineByFork`) | Ordres de transfert pur (`OF_TRANSFER`) |
| **Goulot adressé** | Rejet `SITEAB` et paires `origin_served` | Coût d'A* et lignes trop courtes | Cannibalisation rail/air de V216 |
| **Coût opcodes** | Quasi neutre | **Gain net de ~60 % d'opcodes d'A*** | Très faible ($< 5\ 000$ opcodes/an) |
| **Risque principal** | Encombrement de l'approche de l'usine | Gestion des signaux PBS à la bifurcation | Saturer les aéroports sans avions suffisants |
| **Banc recommandé** | Rail seul 40×3 / 20×10, puis complet 40×6 | Rail seul 10×6, puis complet 40×6 | **Partie complète 40×6 / 20×10 directement** |

---

## Conclusion et recommandation de phasage

L'analyse démontre qu'AAAHogEx ne gagne pas par un tracé de chemin supérieur, mais par une **topologie de réseau unifiée** où les lignes se renforcent mutuellement par transfert et convergence, au lieu de se concurrencer.

Pour OpexAI, le déploiement doit être strictement étanche pour éviter toute régression :
1. **Phase 1 (Recommandée en premier)** : Proposition 1 (`v226_convergent_freight`), car l'outillage de quai joint existe déjà partiellement (`OpexJoinPlatformPlans`, V178) et ne nécessite pas de refonte du pathfinder de voie.
2. **Phase 2** : Proposition 3 (`v226_rail_pax_feeder`), qui traite directement la pathologie économique centrale d'OpexAI en partie complète (la guerre interne entre le rail passagers et l'aérien).
3. **Phase 3** : Proposition 2 (`v226_track_branch_extension`), qui demande un travail plus délicat de signalisation et de raccordement d'aiguillage sur voie vive.
