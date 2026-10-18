# V265 — Prolongement d'une ligne ferroviaire par embranchement de voie

**Date** : 18 octobre 2026  
**Chantier** : V265 (`v265_branch_extension`) — Branche `v265`, issue de `master` (`2c4efe8`)  
**Modèle de référence** : AAAHogEx `TrainRouteExtendBuilder` (`ai/AAAHogEx-115/trainroute.nut:3161`), `CombineByFork` (`railbuilder.nut:930`), et anti-blocage (`trainroute.nut:2385`).

---

## 1. Contexte et Objectif

La construction de lignes ferroviaires point-à-point indépendantes est le mode exclusif d'OpexAI dans sa version courante. Chaque ligne finance deux gares complètes, l'intégralité du tracé physique de voie (terrassement, ponts, tunnels, rails), un dépôt dédié et une rame.

À l'inverse, **AAAHogEx** structure son réseau en toile d'araignée via deux briques fondamentales :
1. **L'extension et bifurcation de voie (`TrainRouteExtendBuilder` & `CombineByFork`)** : plutôt que de poser une nouvelle voie en doublon le long d'un corridor déjà équipé, une ligne existante bifurque via un aiguillage sur sa voie existante vers une nouvelle destination réceptrice.
2. **L'anti-blocage en gare partagée/terminus (`trainroute.nut:2385`)** : lorsqu'un quai ou une gare partagée est saturée par des trains à l'arrêt, un train est immédiatement envoyé au dépôt pour libérer le quai et éviter le blocage face-à-face à la bifurcation ou en gorge de gare.

### Problématique de rentabilité globale (Mémoire V149 / V207 / V212 / V214)
Dans les campagnes historiques, les changements ferroviaires passaient souvent en test « rail seul » mais s'effondraient en partie complète (ex. V207+V212+V214 : −904 k£/an à 10 ans). La cause racine a été identifiée (V149) : **le rail consomme le capital d'amorçage au détriment de l'aérien** en 1970–1972, alors que l'aérien offre un ROI de 70 à 120 %/an et monopolise les bassins aéroportuaires face à AAAHogEx.  
Toute intervention ferroviaire doit obligatoirement sanctuariser la trésorerie de l'aérien.

---

## 2. Revue critique et remplacement des seuils non sourcés du diagnostic V226

Le diagnostic V226 (`docs/v226_reseau_araignee_20261018.md` §4.2) proposait plusieurs règles et seuils heuristiques. Conformément aux exigences V265, chaque seuil non sourcé est ici analysé, confronté aux sources du moteur OpenTTD 15.3 (`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src`) et remplacé par une valeur dérivée d'un mécanisme physique prouvé, ou supprimé.

### 2.1 Le seuil de « 80 tuiles » (V226 §4.2)
- **Proposition initiale non sourcée** : « Lorsqu'une ligne existante est courte (< 80 tuiles) et qu'une seconde opportunité existe à 40–80 tuiles... »
- **Critique** : Ce seuil de 80 tuiles est arbitraire. Dans AAAHogEx (`main.nut:3187`), l'extension est conditionnée par `TrainRoute.GetIdealDistance(cargo) - route.pathDistance >= 100`, où `GetIdealDistance` est calculé par échantillonnage de la courbe de paiement NoAI.
- **Mécanisme OpenTTD 15.3 (`src/economy.cpp:965-1010`)** :  
  La fonction `GetTransportedGoodsIncome(num_pieces, dist, transit_periods, cargo_type)` applique une formule où le revenu par pièce transportée dépend de la distance Manhattan $d$ et du temps de parcours $t$ :
  $$\text{Income} \propto d \cdot \max\left(31, 255 - \frac{t - \text{periods}_1}{\dots}\right)$$
  Sur courte distance, le coût fixe de la gare et du matériel immobilisé ne s'amortit pas.  
- **Remplacement dans OpexAI** :  
  Dans `candidates.nut:348-433`, OpexAI calcule dynamiquement pour chaque époque et matériel :
  - `catalog.bounds.railMin` : distance minimale où le profit ferroviaire surclasse le transport routier (typiquement 20 à 35 tuiles selon la locomotive et le cargo).
  - `catalog.bounds.railMax` : portée maximale d'A* soutenable (`OpexRailDistanceForIterations`, typiquement 110 à 150 tuiles).
  - *Règle physique de l'embranchement* :
    1. Distance du nouveau tronçon de bifurcation $d(F, C) \ge \text{bounds.roadMin}$ (environ 11 à 15 tuiles), seuil physique nécessaire pour implanter la nouvelle gare (longueur $L \approx 3\text{--}4$ tuiles), la gorge de raccordement ($\ge 2$ tuiles) et les cantons de signalisation PBS ($\ge 2\text{--}4$ tuiles).
    2. Distance totale cumulée depuis l'origine $d(A, C) \le \text{bounds.railMax}$.

### 2.2 Le seuil de caisse « 150 000 £ » (V226 §4.2)
- **Proposition initiale non sourcée** : « Conditionner le raccordement convergent à une réserve de caisse disponible $\ge 150\ 000$ £ ou à une activation à partir de 1972 ».
- **Critique** : 150 000 £ est un montant fixe arbitraire qui dépend du climat économique, de l'inflation et des NewGRF.
- **Remplacement par un modèle économique dynamique fondé sur le jeu** :
  1. *Verrou temporel d'amorçage* : Aucune extension autorisée avant l'an 3 (`AIDate.GetYear(now) >= OPEX_START_YEAR + 2`, soit 1972). En 1970 et 1971, tout le capital disponible est réservé à l'expansion aéroportuaire.
  2. *Condition de désendettement* : `AICompany.GetLoanAmount() == 0`. Aucune extension n'est financée sur découvert ou emprunt bancaire.
  3. *Solvabilité et réserve dynamique* :
     $$\text{BankBalance} \ge \text{DevisExtension} + \text{OpexCashReserve}()$$
  4. *Garde anti-cannibalisation AIR* :
     $$\text{BankBalance} - \text{DevisExtension} \ge \text{PrixAvionLePlusCher}$$
     (dérivé du catalogue, typiquement ~35 k£ à ~55 k£ en vanilla 1970 pour un avion type BAC 1-11 ou Viscount). Cela garantit mathématiquement qu'une opportunité d'achat d'avion n'est jamais bloquée par l'embranchement ferroviaire.

### 2.3 L'estimation « ~60 % d'opcodes d'A* » (V226 §5)
- **Proposition initiale non sourcée** : Affirmation d'un « gain net de ~60 % d'opcodes d'A* » sans dérivation.
- **Critique** : Le gain dépend de la géométrie du réseau et du point d'embranchement.
- **Dérivation mathématique et mécanique (`candidates.nut:81-106`)** :  
  L'algorithme A* bidimensionnel non contraint explore une surface proportionnelle au carré de la distance :
  $$\text{Iterations}(d) \propto d^2$$
  Si une nouvelle ligne directe $A \to C$ parcourt une distance $d_{AC}$, tandis qu'une extension depuis un point de bifurcation $F$ ne parcourt que $d_{FC} = (1 - \alpha) d_{AC}$ (où $\alpha$ est la fraction du tronc commun existant $A \to F$) :
  $$\frac{\text{Iterations}(d_{FC})}{\text{Iterations}(d_{AC})} \approx \left(\frac{d_{FC}}{d_{AC}}\right)^2 = (1 - \alpha)^2$$
  - Si l'embranchement se situe à 60 % du trajet ($\alpha = 0{,}6$), la recherche ne consomme que $(0{,}4)^2 = 16\ \%$ des itérations d'une ligne neuve complète, soit **84 % d'économie réelle**, et non un 60 % forfaitaire.
  - Le coût en opcodes d'une itération dans le pathfinder d'OpexAI (`pathfinder_v90/v129.nut`) est mesuré empiriquement entre 80 et 120 opcodes. La réduction d'opcodes est donc strictement le produit du différentiel d'itérations calculé par le coût unitaire mesuré.

---

## 3. Données disponibles dans le code courant

| Donnée | Emplacement / Source | Utilisation dans V265 |
|---|---|---|
| Lignes existantes | `this._lines` (`lines.nut`, `task_rail.nut`) | Identification des lignes actives, cargo, rentabilité (`lastProfit`), matériel (`loco`, `wagons`). |
| Géométrie de quai | `line.platformA`, `line.platformB` | Position des ancres (`anchor`), directions, longueurs, sorties (`station_exit`) et tuiles de raccordement (`lead`). |
| Voies et aiguillages | `AIRail.BuildRail(prev, cur, next)` | Construction du switch de bifurcation sur voie vive (`OpexV181TryBuildSwitchSegment` dans `builder_rail.nut:4570`). |
| Signalisation PBS | `AIRail.BuildSignal(tile, front, SIGNALTYPE_PBS)` | Pose des signaux de protection de bifurcation et d'approche de gare (`OpexTryBuildSignal` dans `builder_rail.nut:2755`). |
| États des trains | `AIVehicle.GetState(v)`, `AIVehicle.VS_AT_STATION` | Détection de l'occupation des quais en gare commune (`task_report.nut`, `builder_rail.nut:128`). |
| Dépôt ferroviaire | `line.depot`, `AIRail.GetRailDepotFrontTile` | Destination pour le renvoi d'anti-blocage (`AIVehicle.SendVehicleToDepot`). |
| Trésorerie & Emprunt | `AICompany.GetBankBalance()`, `AICompany.GetLoanAmount()`, `OpexCashReserve()` | Filtrage strict de la solvabilité sans crédit. |

---

## 4. Point d'insertion exact dans le code courant

1. **Déclaration du réglage** (`ai/OpexAI/info.nut:16`) :
   - Déclaration via `AddSetting` : `name = "v265_branch_extension"`, bornes 0–1, booléen, défaut 0 à tous les niveaux (`easy_value = 0`, `medium_value = 0`, `hard_value = 0`, `custom_value = 0`).
2. **Globales et constantes** (`ai/OpexAI/globals_pre.nut`) :
   - `V265_BRANCH_EXTENSION <- false;`
   - Constantes physiques et économiques sourcées en commentaire.
3. **Chargement unique** (`ai/OpexAI/settings.nut:57`, `OpexLoadSettings`) :
   - Lecture via `AIController.GetSetting("v265_branch_extension")` vers `V265_BRANCH_EXTENSION`.
4. **Module métier dédié** (`ai/OpexAI/task_v265.nut`) :
   - Implémentation des fonctions `_dispatchV265BranchExtension(task, year)` et `_v265AntiBlockStep()`.
   - Requis dans `ai/OpexAI/main.nut:666` après la déclaration de la classe `OpexAI`.
5. **Ordonnancement et boucle de jeu** :
   - Dans `main.nut:Start()` : enregistrement dans `this._taskQueue` avec `enabled = V265_BRANCH_EXTENSION`.
   - Dans `scheduler.nut:7` (`_runNextTaskWithSlackLedger`) : appel de la surveillance anti-blocage `if (V265_BRANCH_EXTENSION) this._v265AntiBlockStep();`.
   - Dans `scheduler_tasks.nut` : méthode de dispatch `_dispatchV265BranchExtension(task, year)`.

---

## 5. Mécanisme détaillé : Signalisation et Anti-blocage

### 5.1 Signalisation PBS au point d'embranchement (`CombineByFork`)
La tuile de bifurcation $F$ connecte trois branches :
- Branche $A$ (vers la gare d'origine partagée),
- Branche $B$ (vers l'ancien terminus),
- Branche $C$ (vers le nouveau terminus prolongé).

*Contrainte moteur OpenTTD 15.3 (`src/rail_cmd.cpp`, `TracksOverlap`)* :  
Le moteur refuse la pose de tout signal sur une tuile comportant plusieurs voies sécantes ou d'aiguillage.  
*Solution* :
Des signaux bidirectionnels à réservation de chemin (PBS, `AIRail.SIGNALTYPE_PBS`) sont posés sur chacune des trois branches, à 1 ou 2 tuiles en amont de la tuile de bifurcation $F$, orientés vers l'aiguillage.  
Grâce au PBS, aucun train n'entre dans la zone d'aiguillage tant qu'il n'a pas réservé un chemin entièrement libre jusqu'à son canton de destination (quai libre ou signal de sortie).

### 5.2 Anti-blocage en gare d'origine commune (`trainroute.nut:2385`)
Lorsqu'une ligne existante dessert à la fois $B$ et $C$ (soit par alternance d'ordres, soit par convois distincts partageant le quai d'origine $A$) :
- Si tous les quais de la gare $A$ sont occupés par des rames en chargement (`AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION`), tout train revenant de $B$ ou $C$ s'arrête devant le signal d'entrée de $A$.
- Si le train entrant s'arrête sur le canton de bifurcation ou la gorge de gare, il bloque la sortie des trains qui viennent de charger. **C'est le deadlock terminal.**
- **Application du modèle AAAHogEx (`trainroute.nut:2385`)** :
  ```squirrel
  if (srcStationStops.len() >= platformNum && srcStationStops.len() > 0) {
    local veh = srcStationStops[0];
    if (!AIOrder.IsGotoDepotOrder(veh, AIOrder.ORDER_CURRENT)) {
      AIVehicle.SendVehicleToDepot(veh);
    }
  }
  ```
  Le premier train en cours de chargement est envoyé au dépôt le plus proche. Le quai est libéré immédiatement ; le train arrivant peut entrer et décharger ; le train envoyé au dépôt est ensuite relancé (`AIVehicle.StartStopVehicle`) dès qu'un quai se libère.

---

## 6. Analyse des risques et parades

| Risque | Impact | Parade mise en œuvre |
|---|---|---|
| **Siphonnement de la caisse AIR** | Baisse massive du profit à 10 ans en partie complète (V149). | Verrouillage temporel strict ($\ge 1972$), emprunt nul requis, et réserve dynamique garantissant la solvabilité pour le prochain avion le plus cher. |
| **Deadlock en gare commune** | Arrêt complet de circulation des rames. | Détection de saturation des quais et renvoi de décongestion au dépôt (`_v265AntiBlockStep`), calqué sur AAAHogEx `trainroute.nut:2385`. |
| **Collision ou blocage à la bifurcation** | Trains arrêtés face-à-face. | Protection par signaux PBS bidirectionnels sur les 3 branches en amont de la tuile de bifurcation. |
| **Perturbation d'opcodes au défaut 0** | Dérive de trajectoire de simulation. | Court-circuit absolu `if (!V265_BRANCH_EXTENSION) return;` avant toute lecture d'état, garantissant un coût d'opcode rigoureusement nul au défaut. |

---

## 7. Plan de mesure et qualification proposé

1. **Exposition (Diagnostic ciblé)** :
   - Campagne 5 graines × 5 ans en duel face à AAAHogEx avec `--script-debug` et `decision_log=1`.
   - Vérifier la présence des lignes `V265_CANDIDATE`, `V265_BUILD`, `V265_FORK` et `V265_ANTIBLOCK`.
   - Contrôler l'absence totale d'erreurs `ERR_TRAIN_LOST` ou de blocages de trains.
2. **Porte A (Gain à court terme V102)** :
   - Protocole V102 : 40 graines × 3 ans, duel face à AAAHogEx, `gain_short`, seuil relatif 4 %, garde de valeur 5 %.
   - Valider que l'extension de ligne par embranchement apporte un incrément net de profit sans pénaliser la croissance de la flotte aérienne.
