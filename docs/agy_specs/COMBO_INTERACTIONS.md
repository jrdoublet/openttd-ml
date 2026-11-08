# Interactions logiques entre leviers route seule (Combo)

Ce document analyse les interactions entre les leviers neutres route seule intégrés dans la branche `road1y-combo` et explicite les résolutions de conflits logiques afin de garantir que chaque levier conserve son comportement exact lorsqu'il est activé isolément, et que le défaut 0 préserve strictement le comportement de master.

## 1. Liste des leviers intégrés et paramètres banqués

| Levier | Réglage | Valeur banquée | Domaine fonctionnel |
|---|---|---|---|
| Ponts routiers A* | `road1y_bridge` | 4 | Recherche de chemin A* (eau, rail) |
| Lignes longues PAX | `road1y_far` | 64 | Distance max PAX (128+N) et budget nœuds A* |
| Admission & plafond fret | `road1y_freight` | 12 | Paliers camions fret (12) + ×2 candidats fret |
| Flotte camions AAA | `road1y_truck_fleet` | 1 | Gestion dynamique de flotte camions (route.nut) |
| Quais et renfort flotte | `road1y_berth_fleet` | 3 | Bit 1 (quais sans réserve 50k, attente 1 bus) + Bit 2 (+1 bus/mois) |
| Attente bilatérale PAX | `road1y_pax_bilat` | 1 | Refleet bus conditionné à `2 * min(waitingA, waitingB)` |
| Estimation flotte mûre | `road1y_pair_fleet` | 8 | Paires PAX ≤127 tuiles réestimées à N=8 bus pour le classement |
| Chargement alterné bout B | `road1y_alt_load` | 33 | N% des bus PAX chargent à plein au bout B (inversion ordres) |

---

## 2. Analyse zone par zone des interactions

### Zone A : Recherche de chemin A* (`road1y_astar.nut`)
- **Leviers concernés** : `road1y_bridge` et `road1y_far`.
- **Rôle de `road1y_bridge`** :
  - Dans `OpexRoad1yAStarSearch` : autorise les sauts au-dessus de l'eau et des voies ferrées de 2 à `ROAD1Y_BRIDGE + 1` tuiles lorsque `ROAD1Y_BRIDGE > 0`.
  - Dans `OpexRoad1yAStarTrace`, `OpexRoadBuildTrace` et `OpexRoadRollback` : teste, pose et annule les ponts routiers réels.
- **Rôle de `road1y_far`** :
  - Dans `OpexRoad1yAStarSearch` : ajuste la portée max `maxTiles = (ROAD1Y_ASTAR_TRACEX > 0 ? ROAD1Y_ASTAR_TRACEX : 128 + ROAD1Y_FAR + 64)` et adapte le budget de nœuds proportionnellement à la distance : `nodeBudget = (nodeBudget * dist) / 128` si `ROAD1Y_FAR > 0 && dist > 128`.
- **Analyse du conflit logique** :
  - Les modifications portent sur des variables distinctes (`nodeBudget`/`maxTiles` vs structure de voisinage dans la boucle A*).
  - En mode combo : une ligne interurbaine lointaine (>128 tuiles, permise par `road1y_far`) dispose d'un budget étendu et peut franchir des étendues d'eau ou des voies ferrées via des ponts de longueur ≤ 4 tuiles.
  - Comportement isolé : si `road1y_bridge=0`, aucun saut de pont n'est créé. Si `road1y_far=0`, `maxTiles=192` et aucun redimensionnement de budget n'a lieu.

### Zone B : Candidats et classement PAX (`bus_districts_overrides.nut`, `candidates.nut`, `economy.nut`)
- **Leviers concernés** : `road1y_far`, `road1y_pair_fleet`, `road1y_freight`.
- **Rôle de `road1y_far`** :
  - Dans `OpexRoad100SoloPaxCandidates` : autorise les paires PAX avec `dist <= 128 + ROAD1Y_FAR`.
- **Rôle de `road1y_pair_fleet`** :
  - Dans `OpexRoad100SoloPaxCandidates` : réévalue les candidats PAX avec une flotte mûre de `ROAD1Y_PAIR_FLEET` bus (au lieu de 2) via `OpexRoad1yPairFleetRank`.
  - Dans `OpexRoad1yPairFleetRank` (`road1y_pair_fleet.nut`) : la condition `if (fleet <= 0 || distance > 127) return;` est explicite.
- **Rôle de `road1y_freight`** :
  - Dans `candidates.nut` (`OpexBuildRoadCandidates`) : pour `c.kind == "freight"`, double `profitAnnual`, `revenueAnnual`, `ratio` et `roi` si `ROAD1Y_FREIGHT > 0`.
  - Dans `economy.nut` (`OpexRoadPhysicalVehicleCap`) : élève le plafond camions à `ROAD1Y_FREIGHT`.
- **Analyse du conflit logique** :
  - `road1y_freight` ne touche que les candidats fret (`c.kind == "freight"`).
  - `road1y_pair_fleet` ne touche que les candidats PAX (`c.kind == "pax"`) de distance ≤ 127 tuiles.
  - Les paires lointaines (>127 tuiles) admises par `road1y_far` ne sont pas touchées par `road1y_pair_fleet` conformément à son contrat d'origine.
  - Aucun conflit de variable ni interférence mutuelle.

### Zone C : Renforts de véhicules (`OpexRoad1yRefleetSaved` dans `bus_districts_overrides.nut`)
- **Leviers concernés** : `road1y_truck_fleet`, `road1y_pax_bilat`, `road1y_berth_fleet`, `road1y_alt_load`.
- **Détail des branchements** :
  1. *Fret* (`line.kind == "freight"`) :
     - Si `ROAD1Y_TRUCK_FLEET > 0` : appel immédiat de `OpexRoad1yTruckFleetStep(ai, line, lineVehicles, engine)` et sortie immédiate (`return`).
     - Si `ROAD1Y_TRUCK_FLEET == 0` : retombe sur le chemin historique avec `waitingA`.
  2. *Voyageurs* (`isPax`) :
     - Si `ROAD1Y_PAX_BILAT > 0` : `road1yWait = (waitingB < waitingA ? waitingB : waitingA) * 2;`.
     - Si `ROAD1Y_PAX_BILAT == 0` : `road1yWait = totalWaiting - OpexRoad1ySpreadWaiting(ai, line, engine);`.
  3. *Seuil d'attente et réserve de caisse* :
     - `road1y_berth_fleet` bit 1 :
       - Réserve caisse quai : `local reserveQuay = (ROAD1Y_BERTH_FLEET & 1) != 0 ? (nextPoolCost > 20000 ? nextPoolCost : 20000) : 50000;`.
       - Déclencheur attente : `local waitTrigger = ((ROAD1Y_BERTH_FLEET & 1) != 0 ? 1 : 2) * capacity;`.
     - `road1y_berth_fleet` bit 2 :
       - Si pas d'achat sur attente, mais `min(stops) >= 2` et `flotte < ROAD1Y_FLEET * min(stops)` et caisse disponible : achat d'1 bus.
  4. *Orientation des bus achetés* :
     - Lorsque `OpexRoadBuyFleetBus` achète un bus PAX, si `ROAD1Y_ALT_LOAD > 0`, `OpexRoad1yAltLoadOrient` est invoqué pour inverser les ordres (plein chargement en B) sur une fraction cible des bus.
- **Analyse du conflit logique** :
  - `road1y_truck_fleet` s'isole complètement sur le fret (`line.kind == "freight"`).
  - `road1y_pax_bilat` définit la métrique d'attente (`road1yWait`) pour les passagers.
  - `road1y_berth_fleet` compare cette attente (`road1yWait`) à son seuil `waitTrigger`.
  - `road1y_alt_load` intervient post-achat sur les ordres du véhicule créé.
  - L'articulation est strictement composable et conserve le comportement nominal de chaque levier pris isolément.

---

## 3. Garantie de neutralité au défaut 0

Pour chaque levier :
- Au défaut 0, la variable globale `ROAD1Y_*` vaut 0.
- Les conditions `if (ROAD1Y_* > 0)` sautent intégralement les blocs additionnels.
- Les deux chargeurs (`OpexLoadSettings` et `OpexLoadBusDistrictSettings`) appliquent `if (!road1yRoadOnly) ROAD1Y_* = 0;`.
- Le code exécuté à 0 est strictement équivalent à celui de `origin/master`.
