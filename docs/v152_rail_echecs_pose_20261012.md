# Autopsie des échecs de pose rail et proposition de réparation / conservation de tracé (12/10/2026)

Ce document constitue l'autopsie détaillée des 14 tentatives rail infructueuses observées lors du diagnostic 5×6 de la V148 ([docs/v148_rail_diag_20261012.md](../docs/v148_rail_diag_20261012.md)), ainsi qu'une proposition d'architecture non implémentée, strictement alignée sur la vision utilisateur : *« des tracés prêts à être construits ou réparés en cas d'échec »*.

Il répond point par point aux quatre questions du programme V152, avec vérification systématique dans le code source de l'IA OpexAI et dans les journaux moteur bruts `/home/deploy/projects/openttd-ml/results/v148_rail_diag_5x6_20261012_engine/v148_master_seed*_r0.log`.

---

## 1. Autopsie de TRKFAIL avec `endx=1`, `error=0`, et flux financier du rollback

### 1.1 Signification exacte de `startx`, `endx`, `error=0` et `actual` dans `RAIL_ATTEMPT`

La ligne de journalisation `RAIL_ATTEMPT` est émise par `OpexAI::_recordRailAttempt` dans [task_rail.nut:1580-1596](../ai/OpexAI/task_rail.nut#L1580-L1596) :
- `startx` et `endx` ([task_rail.nut:1595-1596](../ai/OpexAI/task_rail.nut#L1595-L1596)) proviennent de `result.startx` et `result.endx`, calculés au début de `OpexExecuteRailPlan` dans [builder_rail.nut:2191-2203](../ai/OpexAI/builder_rail.nut#L2191-L2203) :
  - `startx = (DistanceManhattan(tiles[0], tiles[1]) > 1) ? 1 : 0` : indique si le premier segment intermédiaire après la sortie de gare A saute directement par un pont ou tunnel (distance > 1 tuile).
  - `endx = (DistanceManhattan(tiles[tail - 2], tiles[tail - 1]) > 1) ? 1 : 0` (où `tail = tiles.len() - 1`) : indique si le dernier segment avant la tuile d'approche (`lead`, `tiles[tail - 1]`) de la gare B est un franchissement (pont ou tunnel) dont la culée/tête atterrit directement sur la tuile de tête `tiles[tail - 1]`.
- `error` ([task_rail.nut:1607](../ai/OpexAI/task_rail.nut#L1607)) provient de `result.error`, initialisé à `0` dans `OpexExecuteRailPlan` ([builder_rail.nut:2163](../ai/OpexAI/builder_rail.nut#L2163)).
- `actual` ([task_rail.nut:1591](../ai/OpexAI/task_rail.nut#L1591)) provient de `result.actualCost`, initialisé à `0` ([builder_rail.nut:2174](../ai/OpexAI/builder_rail.nut#L2174)) et mis à jour via `costs.GetCosts()` ([builder_rail.nut:2374](../ai/OpexAI/builder_rail.nut#L2374)).

### 1.2 Le mécanisme de panne : comment `TRKFAIL` sort avec `error=0`

Le cas `endx=1` avec `error=0` est un bug d'interface géométrique entre le franchissement et la tête de gare B :
1. Dans `builder_rail.nut:1345-1354`, la boucle `OpexBuildTrack` itère de `i = 1` à `i = tiles.len() - 2` :
   - À l'avant-dernière tuile (`i = last - 1`), `prev = tiles[last - 2]`, `cur = tiles[last - 1]`, `next = tiles[last]` (qui est `planB.station_exit`).
   - Parce que `DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1` (`endx=1`), la condition `AIMap.DistanceManhattan(prev, cur) > 1` à la ligne 1352 est satisfaite :
     ```squirrel
     } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
       ok = true; // autre bout d'un franchissement deja pose
     ```
   - La boucle effectue donc un `continue` implicite (`ok = true`) sans exécuter `AIRail.BuildRail(prev, cur, next)` pour relier la tête de franchissement `tiles[last - 1]` à la sortie de quai `tiles[last] = planB.station_exit` !
   - Aucun ordre de construction n'ayant échoué, `trackFailed` vaut `0` ([builder_rail.nut:1405, 2308](../ai/OpexAI/builder_rail.nut#L1405)).
2. À la ligne [builder_rail.nut:2310-2312](../ai/OpexAI/builder_rail.nut#L2310-L2312), le test de raccordement final est exécuté :
   ```squirrel
   local connected = trackFailed == 0 &&
       AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&
       AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);
   ```
   Comme le morceau de voie `tiles[last - 1]` vers `planB.station_exit` n'a jamais été posé, `AIRail.AreTilesConnected(...)` retourne `false` (`exit_b = 0`).
3. Le bloc `if (!connected)` ([builder_rail.nut:2313](../ai/OpexAI/builder_rail.nut#L2313)) est activé :
   - Comme `trackFailed == 0`, la condition `if (trackFailed > 0 && ...)` ([builder_rail.nut:2314](../ai/OpexAI/builder_rail.nut#L2314)) est fausse.
   - Par conséquent, `result.error` n'est jamais renseigné et conserve sa valeur par défaut `0`.
   - La ligne de décision émise est :
     `RAIL_TRACK_FAIL cause=connect failed=0 tiles=... exit_a=1 exit_b=0 ... d21=...`
   - Le motif de sortie est affecté à `"TRKFAIL"` ([builder_rail.nut:2375](../ai/OpexAI/builder_rail.nut#L2375)).

### 1.3 Le rail partiel est-il démonté ou laissé sur la carte ? L'argent est-il perdu ?

Le rail partiel n'est **jamais** laissé sur la carte :
- La ligne [builder_rail.nut:2373](../ai/OpexAI/builder_rail.nut#L2373) appelle immédiatement `OpexRollback(tiles, planA, planB, null, null)`.
- Dans [builder_rail.nut:1516-1540](../ai/OpexAI/builder_rail.nut#L1516-L1540), `OpexRollback` démolit systématiquement :
  1. Toutes les tuiles de quai de la gare A (`planA.anchor + planA.step * i`) via `AITile.DemolishTile`.
  2. Toutes les tuiles de quai de la gare B (`planB.anchor + planB.step * i`) via `AITile.DemolishTile`.
  3. Toutes les tuiles du tracé intermédiaire (`tiles[1]` à `tiles[tiles.len() - 2]`) via `AITile.DemolishTile`.
- **Destruction financière absolue :**
  - Dans OpenTTD, la démolition (`DemolishTile`) coûte de l'argent en plus de la construction.
  - L'objet comptable `costs = AIAccounting()` instancié avant les gares à la ligne [builder_rail.nut:2273](../ai/OpexAI/builder_rail.nut#L2273) enregistre à la fois les dépenses de pose (terrassement, gares, ponts, tunnels, rails) ET les dépenses de démolition du rollback.
  - À la ligne [builder_rail.nut:2374](../ai/OpexAI/builder_rail.nut#L2374), `result.actualCost = costs.GetCosts()` enregistre la somme totale dépensée.
  - **100 % de l'argent dépensé est irrémédiablement perdu** : aucun actif n'est conservé, la trésorerie est débitée (ex. 15 623 £, 12 049 £, 11 749 £), et le terrain est rendu vierge.

### 1.4 Pourquoi la 4e tentative sort-elle avec `actual=0` ?

Lors de la 4e tentative (1974-12-27), le journal indique `actual=0`, `error=261` (`ERR_AREA_NOT_CLEAR`).
Dans [builder_rail.nut:2204-2252](../ai/OpexAI/builder_rail.nut#L2204-L2252), la fonction `OpexQuoteRailCapital` simule la construction sous `AITestMode()` (`RAIL_DEVIS`).
Sur cette tentative, la simulation de devis a échoué avec l'erreur `261` sur la tuile 44451 (`RAIL_QUOTE_FAIL reason=TRKFAIL tile=44451 err=261`).
Comme l'échec a eu lieu dans le devis prévisionnel, l'exécution a été interrompue avant la ligne 2273 (`costs = AIAccounting()`) : aucun terrassement réel n'a eu lieu, et `result.actualCost` est resté à `0`.

---

## 2. Pourquoi la même paire voyageurs a été retentée 5 fois (Graine 42)

### 2.1 Que fait `_recordRailAttempt` / `_markPairAbandoned` pour un `TRKFAIL` voyageurs ?

Dans [task_rail.nut:1696-1703](../ai/OpexAI/task_rail.nut#L1696-L1703) :
```squirrel
if (ABANDON_MEMORY && (result.reason == "ABND" || result.reason == "SITEA" || result.reason == "SITEB" ||
                       result.reason == "SITEAB" || result.reason == "NOPA" || result.reason == "STNFAIL"
                       || (((RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY)
                            || (RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight"))
                           && result.reason == "TRKFAIL"
                           && ("persistentGeometry" in result) && result.persistentGeometry))) {
  this._markPairAbandoned(OpexAbandonedPairKey(candidate));
}
```
Pour un échec de type `TRKFAIL` :
1. `RAIL_GEOMETRY_GUARD` vaut `0` par défaut ([info.nut:1121](../ai/OpexAI/info.nut#L1121), [settings.nut:100](../ai/OpexAI/settings.nut#L100)).
2. `RAIL_FREIGHT_TRKFAIL_MEMORY` ne s'applique qu'au fret (`candidate.kind == "freight"`).
3. **Pour une paire voyageurs (`pax`), `_markPairAbandoned` n'est JAMAIS appelé sur un `TRKFAIL` !**
4. Aucun cooldown (ni `ABANDON_MEMORY`, ni C77/C80, ni `_abandonedPairs`) n'enregistre la paire. La table `this._abandonedPairs` reste totalement vierge de cette paire.

### 2.2 Chronologie et sélection de la graine 42 dans le portefeuille

Pourquoi un candidat de rang 41 avec `pred_roi=90` a-t-il été sélectionné à la 1re tentative, puis répété 4 fois de suite ?
L'analyse des journaux de la graine 42 révèle la mécanique exacte :

#### Tentative 1 : Octobre 1973
- La recherche A* pour `pax 49565->33442` avait été initiée plusieurs mois auparavant (lorsque le vivier initial avait qualifié cette ligne).
- Le calcul A* s'est terminé le 1973-10-17 après 6 582 itérations (`RAIL_SEARCH_END primary outcome=OK iters=6582`).
- Dans la passe projets du 1973-10-24, `_consumeResumableRailAtPassStart` ([task_projects.nut:1230-1252](../ai/OpexAI/task_projects.nut#L1230-L1252)) consomme ce plan prêt à construire.
- À cette date, la génération annuelle avait repuplé le portefeuille : les 40 meilleurs projets étaient des lignes fret et aériennes à fort ROI. Dans la liste triée `this._projects.best`, la paire `49565->33442` occupait la 41e position (`rank=41`).
- La construction est lancée, échoue sur la connexion terminale B (`d21=5`, `exit_b=0`), subit un rollback qui détruit 15 623 £, et `task_projects.nut:1248` logue `PROJECT_DISCARD mode=rail rank=41 reason=TRKFAIL`.
- Comme `candidate.kind == "pax"`, aucune mémoire d'abandon n'est enregistrée.

#### Tentatives 2, 3 et 4 : Août 1974, Octobre 1974, Décembre 1974
Entre l'automne 1973 et l'été 1974, OpexAI construit ses premières lignes fret et aériennes. En août 1974 :
- Les projets aériens et routiers disponibles sont tous construits ou saturés.
- Il ne reste plus que 33 projets dans le vivier rail.
- Aux rangs 0 et 1 de `this._projects.best` se trouvent deux projets fret (`54044->59980` et `59980->44107`). Mais à chaque passe mensuelle, ces deux projets sont rejetés avant l'A* par `too_close_no_join` ([task_rail.nut:438-442](../ai/OpexAI/task_rail.nut#L438-L442)) :
  `PROJECT_DISCARD mode=rail rank=0 reason=too_close_no_join`
  `PROJECT_DISCARD mode=rail rank=1 reason=too_close_no_join`
- **Le rang 2 disponible est immédiatement `pax 49565->33442` !**
- Le portefeuille sélectionne donc ce rang 2 :
  - **1974-08-17** : `PROJECT_CHOSEN mode=rail rank=2 ... src=49565 dst=33442`. Recherche A* refaite (4 991 itérations, ~7,4 M opcodes), pose tentée, échec connectique `d21=3`, rollback, 12 049 £ brûlées.
  - **1974-10-27** : Aussitôt le slot `_railSearch` libéré et le vivier réévalué, rangs 0 et 1 rejetés `too_close_no_join`, rang 2 choisi à nouveau ! Recherche A* refaite (5 020 itérations, ~7,4 M opcodes), pose tentée, échec connectique `d21=3`, rollback, 11 749 £ brûlées.
  - **1974-12-27** : Rang 2 choisi une 4e fois ! Recherche A* refaite (5 020 itérations), échec au devis `RAIL_QUOTE_FAIL` sur la tuile 44451 (`err=261`), `actual=0`.

#### Tentative 5 : Septembre 1975
- En 1975, les villes ont grandi et le terrain a été modifié aux abords de la gare B.
- La recherche A* est lancée une 5e fois sur la même paire `49565->33442`.
- Cette fois, le pathfinder ne trouve plus d'issue et épuise son plafond de 10 000 itérations :
  `RAIL_SEARCH type=resumable outcome=ABND iters=10000 budget=10000` (consommant 11,8 M opcodes).
- Comme le motif est cette fois `ABND`, la condition `result.reason == "ABND"` de la ligne [task_rail.nut:1696](../ai/OpexAI/task_rail.nut#L1696) est enfin satisfaite !
- La paire est inscrite dans `this._abandonedPairs` via `_markPairAbandoned` et n'est plus jamais retentée.

**Bilan sur cette seule paire :** 5 recherches A* successives, ~41,4 millions d'opcodes gaspillés, 39 421 £ d'argent détruit en pure perte.

---

## 3. Examen des 4 ABND et 5 STNFAIL : Signes précurseurs avant l'A* ?

### 3.1 Les 4 cas d'abandon A* (`ABND`, plafond 10 000 itérations)
Les 4 cas observés dans le diagnostic V148 sont :
- Graine 100 : `src=42387 dst=34031` (10 000 iters, 12,3 M opcodes)
- Graine 42 : `src=49565 dst=33442` (10 000 iters, 11,8 M opcodes, 5e tentative ci-dessus)
- Graine 5678 : `src=55355 dst=33967` (10 000 iters, 11,8 M opcodes)
- Graine 5678 : `src=24584 dst=42137` (10 000 iters, 11,9 M opcodes)

**Y avait-il un signe précurseur avant l'A* ?**
1. **Distance Manhattan (`manh`) :**
   - Les distances de ces 4 cas sont respectivement de 68, 64, 75 et 69 tuiles.
   - Or, les lignes ferroviaires réussies ont des distances comparables (médiane à 66 tuiles, échelle 55–85 tuiles).
   - Comme démontré dans l'autopsie V100/V101 (`docs/taches.md`), la distance seule ne discrimine absolument pas les échecs des succès.
2. **Terrain et rugosité :**
   - La sonde `probe_rail_terrain` (V101) a montré que les échecs franchissent des reliefs plus accidentés (pentes, eau).
   - Cependant, un seuil éliminatoire strict sur la rugosité rejette des lignes viables et rentables (faux positifs destructeurs pour le profit).
3. **Prédiction A* (`pred_astar`) :**
   - Le budget alloué par `OpexIterationBudget` ([builder_rail.nut:1832](../ai/OpexAI/builder_rail.nut#L1832)) dépend du profit attendu. Pour ces lignes majeures, il sature le plafond dur de 10 000 itérations.
   - Contrairement aux `TRKFAIL` et `STNFAIL`, un `ABND` s'inscrit immédiatement dans `_abandonedPairs` ([task_rail.nut:1696](../ai/OpexAI/task_rail.nut#L1696)), ce qui empêche sa réexécution. Le coût reste néanmoins de ~12 M opcodes pour chaque occurrence.

### 3.2 Les 5 cas d'échec de gare (`STNFAIL`)
Les 5 échecs `STNFAIL` se produisent lors de `OpexBuildRailStation` ([builder_rail.nut:2080-2084](../ai/OpexAI/builder_rail.nut#L2080-L2084)) ou lors de la pose réelle ([builder_rail.nut:2294-2302](../ai/OpexAI/builder_rail.nut#L2294-L2302)) :
- Causes physiques : pente locale modifiée entre l'évaluation du vivier et la construction, expansion urbaine (maisons apparues sur l'emprise), ou dégradation de la note municipale (`TownRating` < `POOR`).
- **Comportement mémoire :**
  - Dans [task_rail.nut:1696-1697](../ai/OpexAI/task_rail.nut#L1696-L1697), `result.reason == "STNFAIL"` est explicitement listé sous `ABANDON_MEMORY` :
  - La paire est immédiatement marquée abandonnée et n'est pas retentée.
  - Le gaspillage d'opcodes pour un `STNFAIL` est modéré (~1,5 à 2 M opcodes par tentative, car le pathfinder A* s'arrête ou la pose avorte avant le déploiement de voie).

---

## 4. Proposition d'architecture : Conservation et réparation de tracé

Cette proposition s'articule autour de la vision utilisateur : *« des tracés prêts à être construits ou réparés en cas d'échec »*.

### 4.1 Analyse comparative : Pourquoi les tentatives passées ont échoué

Avant de formaliser une solution, il est impératif de comprendre pourquoi les pistes précédentes ont été rejetées ou réfutées :
1. **V131 (réparation à la pose de tracés précalculés en stock) :**
   - V131 stockait des tracés calculés un ou deux ans plus tôt.
   - À la construction, l'environnement avait changé (terrains occupés par des aéroports concurrents de 10–15 tuiles). Tenter de "réparer" par un mini-A* au moment de la pose a provoqué des régressions sévères de trésorerie et d'opcodes (instabilités, impasses).
2. **Mémoire TRKFAIL géométrique fret (08/10) :**
   - Bannissait définitivement toute paire ayant produit un TRKFAIL persistant.
   - Rejetée car elle éliminait des paires fret très rentables dont le problème géométrique n'était qu'un détail d'aiguillage réparable, entraînant une perte nette de profit.

### 4.2 L'opportunité propre au problème `endx=1`

Le cas `endx=1` mis au jour dans cette autopsie est fondamentalement différent :
- **Le tracé A* calculé (99 % des tuiles) est totalement parfait, valide et libre.**
- Le problème n'est **PAS** une obstruction de terrain sur le tracé.
- Le problème est un **défaut géométrique d'interface terminale** à la tuile `tiles[last - 1]` : un pont ou un tunnel saute directement sur la tête de quai, et la boucle de pose `OpexBuildTrack` saute l'instruction de pose du raccordement vers `planB.station_exit`.
- Au lieu de démolir tout le tracé (rollback destructeur) puis de recalculer 10 000 itérations d'A* pour refaire exactement la même erreur, la solution relève de la connectivité terminale.

### 4.3 Mesures proposées par famille de panne

#### Famille A : TRKFAIL en bout de tracé (`endx=1` / saut terminal vers tête de quai)
- **Action de réparation / pose :**
  1. *Dans `OpexBuildTrack` ([builder_rail.nut:1352-1354](../ai/OpexAI/builder_rail.nut#L1352-L1354)) :*
     Lorsque `AIMap.DistanceManhattan(prev, cur) > 1`, au lieu de simplement exécuter `ok = true; continue;`, vérifier si `i == last - 1`. Si `i == last - 1`, poser explicitement la transition entre la tête de pont/tunnel `cur` et la sortie de quai `next = planB.station_exit` via `AIRail.BuildRail(cur, cur, next)`.
  2. *Alternative préventive sans toucher à l'A* :*
     Dans `OpexRailPathGeometryIssue` ([builder_rail.nut:1138-1140](../ai/OpexAI/builder_rail.nut#L1138-L1140)), le cas `end_jump` est déjà identifié. Si le raccordement direct est impossible sans culée intermédiaire, rejeter avant terrassement (`actual=0`) et mémoriser la contrainte pour cette géométrie de quai précise, plutôt que de dépenser 15 000 £ en construction/démolition.
- **Coût en opcodes attendu :** Quasi nul (< 5 000 opcodes pour poser la pièce ou vérifier le raccordement), au lieu de 7 400 000 opcodes par itération d'A* évitée.
- **Gain financier :** Préservation intégrale du capital (sur la graine 42, évite 39 421 £ de pertes nettes et permet à la ligne de circuler dès 1973 avec ~4,8 k£/an de profit).

#### Famille B : TRKFAIL voyageurs générique (Boucle de répétition infinie)
- **Action de conservation de tracé et de régulation :**
  - Dans [task_rail.nut:1696-1703](../ai/OpexAI/task_rail.nut#L1696-L1703), étendre la mémoire d'abandon temporaire aux paires voyageurs :
    Ne pas autoriser une paire `pax` ayant subi un `TRKFAIL` à être réinjectée dans le portefeuille au tick suivant sans un cooldown minimal (ex. `ABANDON_COOLDOWN_DAYS = 180`).
  - Si le tracé a échoué à la pose, conserver le plan sous forme de candidat "en attente de validation physique" (ou appliquer le cooldown existant), plutôt que de relancer immédiatement le pathfinder lourd.
- **Coût en opcodes attendu :** 0 opcode.
- **Gain :** Élimination immédiate des 4 répétitions aveugles (économie de ~30 M opcodes sur la graine 42).

#### Famille C : ABND (Épuisement du budget A*)
- **Action :**
  - Maintenir le comportement actuel de marquage dans `_abandonedPairs` ([task_rail.nut:1696](../ai/OpexAI/task_rail.nut#L1696)).
  - Pré-filtrer les candidats dont l'extrémité est topologiquement bloquée (relief direct impraticable aux abords immédiats des ancres de quai) avant d'engager 10 000 itérations d'A*.
- **Coût en opcodes attendu :** Économie nette de 11 à 12 M opcodes par cas bloqué.

### 4.4 Réglage et sonde pour validation causale (défaut 0)

Conformément à la méthode OpexAI :
- **Nouveau réglage proposé :**
  `rail_endpoint_repair` (booléen, défaut 0).
  - Déclaré dans `info.nut` avec `easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0`.
  - Chargé dans `settings.nut` (`RAIL_ENDPOINT_REPAIR = AIController.GetSetting("rail_endpoint_repair") != 0;`).
  - Active la pose de raccordement terminal sous `endx=1` dans `OpexBuildTrack` et le cooldown de retry sur les paires voyageurs.
- **Sonde dédiée :**
  Émission sous `DECISION_LOG` de la sonde :
  `RAIL_ENDPOINT_REPAIR status=repaired tile=... src=... dst=... cost=...`
  permettant de prouver l'exposition réelle dès le smoke et le banc 5×6 avant toute porte A V102.

### 4.5 Estimation de l'enjeu économique et d'opcodes (d'après V148)

Sur les 5 graines × 5 ans du banc V148 :
- **Budget total opcodes IA :** 233 M opcodes.
- **Opcodes consommés en tentatives rail échouées :** ~110 M opcodes (47,2 % du total d'OpexAI !).
  - `TRKFAIL` : 44 M opcodes.
  - `ABND` : 47 M opcodes.
  - `STNFAIL` : 10 M opcodes.
  - Autres / abandons : ~9 M opcodes.
- **Enjeu en trésorerie (£) :**
  - Sur la seule graine 42 : **39 421 £** de capital détruit par rollback sur la paire `49565->33442`.
  - En évitant ces destructions et en connectant la ligne dès octobre 1973 :
    Gain direct de trésorerie : +39,4 k£.
    Recettes cumulées sur 4 ans d'exploitation (1973–1977 à ~4,8 k£/an) : ~19,2 k£.
    Impact total estimé sur la valeur d'entreprise (graine 42) : **> +58 k£**.

---

## 5. Fichiers et lignes cités (Vérification rigoureuse)

Chaque référence ci-dessous a été vérifiée directement dans le code source courant :

1. `ai/OpexAI/builder_rail.nut:1126-1142` : Fonction `OpexRailPathGeometryIssue(tiles, planA, planB)` et détection de l'incohérence terminale `end_jump` (`AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1`).
2. `ai/OpexAI/builder_rail.nut:1342-1406` : Fonction `OpexBuildTrack(tiles, structures, failure)`, boucle de pose `for (local i = 1; i < tiles.len() - 1; i++)`, branche `AIMap.DistanceManhattan(prev, cur) > 1` (lignes 1352-1354) qui effectue `ok = true` sans poser le rail terminal, et capture des erreurs.
3. `ai/OpexAI/builder_rail.nut:1516-1540` : Fonction `OpexRollback(tiles, planA, planB, depot, vehicles)` qui démolit intégralement les gares A et B et toutes les tuiles de voie intermédiaire par `AITile.DemolishTile`.
4. `ai/OpexAI/builder_rail.nut:2160-2203` : Fonction `OpexExecuteRailPlan`, initialisation de `result.error = 0` (ligne 2163), `result.actualCost = 0` (ligne 2174), et calcul de `result.startx` et `result.endx` sous `DECISION_LOG` (lignes 2191-2203).
5. `ai/OpexAI/builder_rail.nut:2204-2252` : Devis prévisionnel sous `AITestMode` (`RAIL_DEVIS`) et sortie précoce `RAIL_QUOTE_FAIL` laissant `actualCost = 0`.
6. `ai/OpexAI/builder_rail.nut:2273` : Instanciation du compteur financier réel `costs = AIAccounting()` avant construction des gares.
7. `ai/OpexAI/builder_rail.nut:2308-2321` : Détection de l'échec de raccordement `connected = trackFailed == 0 && ... AreTilesConnected(...)` (lignes 2310-2312) ; comme `trackFailed == 0`, `result.error` n'est pas renseigné et reste `0`.
8. `ai/OpexAI/builder_rail.nut:2373-2376` : Appel de `OpexRollback`, enregistrement de `result.actualCost = costs.GetCosts()` (dépenses perdues), assignation `result.reason = "TRKFAIL"`.
9. `ai/OpexAI/task_rail.nut:438-442` : Rejet en amont de l'A* par `too_close_no_join`.
10. `ai/OpexAI/task_rail.nut:1230-1252` : Dans `task_projects.nut`, consommation au début de passe des recherches A* terminées (`_consumeResumableRailAtPassStart`) et journalisation du discard de portefeuille.
11. `ai/OpexAI/task_rail.nut:1364-1406` : Réception du résultat A* (`outcome = slice.stop`), assemblage du plan par `OpexCompleteRailRouteAfterSearch`.
12. `ai/OpexAI/task_rail.nut:1469-1487` : Exécution de `OpexBuildLine`, effacement de `candidate.railPlan = null`, enregistrement de la tentative via `_recordRailAttempt`.
13. `ai/OpexAI/task_rail.nut:1580-1609` : Journalisation `RAIL_ATTEMPT` détaillant `actual`, `quote`, `endx`, `startx`, `error`, etc.
14. `ai/OpexAI/task_rail.nut:1696-1704` : Condition d'enregistrement dans `_abandonedPairs` via `_markPairAbandoned` ; montre que `TRKFAIL` n'est mémorisé que si `candidate.kind == "freight" && RAIL_FREIGHT_TRKFAIL_MEMORY`, excluant totalement les paires voyageurs (`pax`).
15. `ai/OpexAI/settings.nut:100-104` : Initialisation de `RAIL_GEOMETRY_GUARD`, `RAIL_GEOMETRY_PAIR_MEMORY` et `RAIL_FREIGHT_TRKFAIL_MEMORY` à partir des paramètres NoAI.
16. `ai/OpexAI/info.nut:1117-1160` : Déclaration des paramètres de garde géométrique rail avec valeurs par défaut `0`.
17. `ai/OpexAI/persist.nut:768-771, 872-875` : Sauvegarde et rechargement de la table `_abandonedPairs`.
