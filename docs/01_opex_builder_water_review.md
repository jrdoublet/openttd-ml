Voici les faiblesses majeures et les axes d'amélioration pour ton `builder_water.nut`, classés par impact.

---

### 1. Les anomalies bloquantes et économiques

* **Le rayon de recherche du dock (`town.tile`) :**
Dans `OpexWaterFindSite`, tu limites la recherche à `r <= coverage` (souvent 5 cases pour un quai) autour de `town.tile`. Or, le centre de la ville (`town.tile`) est rarement sur le rivage. Dans la majorité des cartes, une ville côtière a son centre à 10 ou 20 cases de la mer. **Conséquence :** le script ne trouve presque aucun dock et élimine 90 % des villes valables. Il faut chercher les tuiles côtières dans un rayon plus large (ex. 15 à 30 cases) et vérifier si le quai couvre au moins quelques maisons ou génère des passagers via `AITile.GetCargoProduction(dock, catalog.paxCargo, 1, 1, coverage)`.
* **Le calcul des revenus dans `OpexWaterEconomics` :**
Tu calcules le revenu avec `waterDistance` :
```squirrel
local income = AICargo.GetCargoIncome(catalog.paxCargo, distance, oneWayDays);

```


OpenTTD calcule **toujours** le paiement sur la **distance de Manhattan à vol d'oiseau entre les stations**, jamais sur la distance réelle parcourue sur l'eau. Si un navire met 80 jours pour faire un détour maritime de 120 cases entre deux quais distants de 45 cases en Manhattan, OpenTTD te paiera sur la base de 45 cases avec la pénalité de temps de 80 jours. Ton calcul surestime massivement la rentabilité des routes sinueuses. Il faut passer `AIMap.DistanceManhattan(siteA.dock, siteB.dock)` pour la distance du revenu, tout en gardant `waterDistance` pour le temps de parcours.
* **Division entière sur `tripsPerMonth` :**
`local tripsPerMonth = 30 / oneWayDays;`
En Squirrel, c'est une division entière. Si un aller simple prend 35 jours, `30 / 35` donne `0`, puis tu forces `tripsPerMonth = 1`. Forcer 1 voyage par mois pour un trajet qui en prend deux triple artificiellement la capacité transportée et les bénéfices. Utilise des flottants ou calcule directement sur l'année :
```squirrel
local tripsPerYear = 365.0 / (2.0 * oneWayDays);
local carriedAnnual = offeredAnnual < (ship.capacity * tripsPerYear) ? offeredAnnual : (ship.capacity * tripsPerYear);

```


* **Trésorerie non vérifiée :**
`WATER_CAPITAL_MARGIN` est déclaré en haut du fichier mais n'est **jamais utilisé**. Dans `OpexBuildWaterRoute`, tu ne vérifies ni le solde en banque (`AICompany.GetBankBalance`) ni la capacité d'emprunt restante avant de poser le premier quai.

---

### 2. Le BFS maritime et la boîte englobante

* **L'écueil du `WATER_BFS_MARGIN = 24` :**
Une boîte englobante avec une marge de 24 cases casse complètement la navigation maritime. Si une péninsule, un isthme ou une baie oblige le bateau à descendre de 30 cases pour contourner la terre, ton BFS échoue (`-1`) alors qu'il existe un passage direct en eau libre. Pour les voies maritimes, soit tu élargis considérablement la zone, soit tu évites le BFS systématique.
* **Explosion d'opcodes ($N \times (N-1) / 2$) :**
Dans `OpexWaterPlans`, tu exécutes `OpexWaterFindConnection` pour **chaque paire** admissible. Si tu as 8 sites, cela fait 28 BFS explorant jusqu'à 12 000 cases chacun dans l'eau libre (sans heuristique A* pour guider la recherche vers la cible). C'est un gouffre à opcodes.
* **Optimisation `OpexWaterContains` :**
Dans la boucle intérieure du BFS :
```squirrel
if (OpexWaterContains(siteB.waterTiles, current)) return distance;

```


Appeler une fonction qui itère sur un tableau à chaque nœud exploré ralentit le parcours. Utilise une table de hachage pour une vérification en $O(1)$ :
```squirrel
local targetSet = {};
foreach (w in siteB.waterTiles) targetSet.rawset(w, true);
// Dans le BFS :
if (current in targetSet) return distance;

```



---

### 3. Gestion des quais et dépôts

* **Anticipation de la pente du quai :**
Dans `OpexWaterFindSite`, tu testes des tuiles d'eau adjacentes arbitraires avec `OpexWaterAdjacentTiles`. Or, un quai requiert une pente côtière orientée vers l'eau (`SLOPE_SW`, `SLOPE_NW`, etc.). L'eau sur laquelle s'étend le dock n'est pas aléatoire : elle est déterminée par `AITile.GetSlope(dock)`. Tester la pente en amont évite des appels inutiles à `AITestMode()` et garantit que la tuile d'eau sélectionnée sera bien la tuile frontale du quai.
* **Abus de `AITestMode()` dans `OpexWaterFindDepot` :**
Tu fais jusqu'à 96 probes en instanciant `AITestMode()` à chaque passage dans la boucle :
```squirrel
local depotOk = false;
{ local probe = AITestMode(); depotOk = AIMarine.BuildWaterDepot(current, next); }

```


Le coût d'instanciation de `AITestMode` à répétition est élevé. Filtre d'abord les deux tuiles avec de simples vérifications natives sans coût :
```squirrel
if (AITile.GetSlope(current) != AITile.SLOPE_FLAT || AITile.GetSlope(next) != AITile.SLOPE_FLAT) continue;
if (!AITile.IsWaterTile(current) || !AITile.IsWaterTile(next)) continue;

```


De plus, un dépôt d'eau n'a pas besoin d'être cherché à 20 cases au large : le placer sur l'une des cases d'eau immédiatement adjacentes au front du quai A suffit largement.

---

### 4. Sélection des villes

* **Biais du tri par population :**
`OpexWaterSortedTowns` sélectionne les 12 plus grandes villes de la carte sans vérifier si elles touchent l'eau. Sur une carte continentale, les 12 plus grosses villes peuvent être à l'intérieur des terres : ton script s'épuise alors à chercher des quais pour des villes terrestres et s'arrête sans rien bâtir.
**Correctif :** filtre les villes qui possèdent au moins une tuile d'eau navigable à portée avant de les insérer dans le pool de sélection.

---

### Synthèse des modifications prioritaires

1. **Économie :** passe la distance Manhattan à `AICargo.GetCargoIncome` et fluidifie le calcul des rotations annuelles.
2. **Candidats :** élargis la recherche de côte autour des villes (15-25 cases) en vérifiant l'acceptation passagers, et ne garde dans `WATER_TOWN_POOL` que les villes côtières.
3. **Connectivité :** remplace la recherche par `targetSet[current]` et élargis ou supprime la bounding box étriquée sur l'eau libre (ou passe sur un A* avec distance Manhattan comme heuristique).
4. **Trésorerie :** ajoute le garde-fou financier avant `OpexBuildWaterRoute` :
```squirrel
local costEst = (2 * catalog.costDock) + catalog.costWaterDepot + plan.economics.ship.price;
if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < costEst + WATER_CAPITAL_MARGIN) return result;

```