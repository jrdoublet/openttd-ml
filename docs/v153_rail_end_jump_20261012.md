# V153 — Raccordement rail sur saut terminal (pont/tunnel)

Date : 2026-10-12
Branche : `v153-rail-endjump`
Statut : Implémenté, défaut 0 (inactif), validé par contrats statiques. Aucun commit, aucun push, aucun banc Docker.

---

## 1. Contexte et Problème

Dans `ai/OpexAI/builder_rail.nut`, la validation terminale de raccordement dans `OpexExecuteRailPlan` évaluait :
```squirrel
local connected = trackFailed == 0 &&
    AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&
    AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);
```

Or, `AIRail.AreTilesConnected(from, tile, to)` exige en précondition que `AIMap.DistanceManhattan(from, tile) == 1` et `AIMap.DistanceManhattan(to, tile) == 1`.
Lorsqu'un pont ou un tunnel termine le tracé (`DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1` côté B ou `DistanceManhattan(tiles[1], tiles[2]) > 1` côté A), la tuile `lead` (`tiles[last - 1]` ou `tiles[1]`) est une tête d'ouvrage et sa distance au segment amont dépasse 1.
L'appel `AreTilesConnected` échoue donc systématiquement, déclenchant un faux `TRKFAIL` (`cause=connect failed=0`) et un rollback complet de la ligne, alors même que l'ouvrage d'art et la voie sont physiquement continus et carrossables.

---

## 2. Résumé du Diff

1. **`ai/OpexAI/info.nut`** :
   - Ajout du réglage `rail_end_jump_connect` (type `AICONFIG_BOOLEAN`, bornes 0/1, défaut 0 pour les 4 profils `easy`, `medium`, `hard`, `custom`).
2. **`ai/OpexAI/globals_pre.nut`** :
   - Déclaration de la variable globale `RAIL_END_JUMP_CONNECT <- false;`.
3. **`ai/OpexAI/settings.nut`** :
   - Chargement dynamique : `RAIL_END_JUMP_CONNECT = AIController.GetSetting("rail_end_jump_connect") != 0;`.
4. **`ai/OpexAI/builder_rail.nut`** :
   - Implémentation de `OpexRailEndConnected(outer, lead, inner, side = null)` :
     - Si `!RAIL_END_JUMP_CONNECT` ou `AIMap.DistanceManhattan(lead, inner) <= 1` : retour strict de `AIRail.AreTilesConnected(outer, lead, inner)`.
     - Si saut (`d > 1`) :
       - Vérification que `lead` et `inner` forment un pont (`AIBridge.IsBridgeTile(lead) && AIBridge.GetOtherBridgeEnd(lead) == inner`) ou un tunnel (`AITunnel.IsTunnelTile(lead) && AITunnel.GetOtherTunnelEnd(lead) == inner`).
       - Vérification de colinéarité : `unit = (lead - inner) / d`, puis exigence `outer == lead + unit` (`outer` dans le prolongement immédiat de l'ouvrage, côté opposé à `inner`).
       - Vérification d'alignement de la voie sur `outer` : `AIMap.IsValidTile(outer + unit) && AIRail.AreTilesConnected(lead, outer, outer + unit)`, avec repli `AIRail.IsRailTile(outer)` si la tuile suivante est hors carte.
       - Trace d'exposition sous `DECISION_LOG` :
         `OpexDecide("RAIL_END_JUMP", "side=A|B ok=0|1 kind=bridge|tunnel|none lead=... inner=... outer=...")`.
   - Remplacement des vérifications dans `OpexExecuteRailPlan` :
     ```squirrel
     local connected = trackFailed == 0 &&
         OpexRailEndConnected(planA.station_exit, tiles[1], tiles[2], "A") &&
         OpexRailEndConnected(planB.station_exit, tiles[last - 1], tiles[last - 2], "B");
     ```
5. **`sweeps/test_rail_track_failure_capture.py`** :
   - Projection du nouvel appel `OpexRailEndConnected` vers la forme historique pour maintenir intact le contrat d'intégrité statique UR-15a.
6. **`sweeps/test_v153_rail_end_jump.py`** :
   - Suite de tests unitaire dédiée validant la déclaration, les réglages, les invariants mathématiques et géométriques, ainsi que l'absence de pièges Squirrel.

---

## 3. Sémantique d'`AreTilesConnected`

- **Inspection locale du source OpenTTD** : « source absent » sur l'environnement hôte (exécutable packagé / environnement conteneurisé sans arborescence `src/` locale).
- **Spécification NoAI / Doxygen (`classAIRail.html`)** :
  ```cpp
  static bool AIRail::AreTilesConnected(TileIndex from, TileIndex tile, TileIndex to);
  ```
  - **Préconditions** : `from != to`, `AIMap::DistanceManhattan(from, tile) == 1`, `AIMap::DistanceManhattan(to, tile) == 1`.
  - **Sémantique** : La fonction teste si l'infrastructure ferroviaire sur la tuile centrale `tile` établit un lien de circulation entre le bord orienté vers `from` et le bord orienté vers `to`.
  - **Absence de contrainte sur `from` / `to`** : Les tuiles extrêmes `from` et `to` ne sont utilisées que pour calculer les directions diagonales d'entrée et de sortie (`DiagdirBetweenTiles(tile, from)` et `DiagdirBetweenTiles(tile, to)`). Il n'est pas requis que `from` ou `to` soient des tuiles de rail ordinaire ; elles peuvent être des rampes de pont, des têtes de tunnel ou tout autre type de tuile adjacente.
  - **Symétrie** : La connexion ferroviaire sur une tuile étant non orientée, la fonction est rigoureusement symétrique par rapport à `from` et `to` (`AreTilesConnected(a, b, c) == AreTilesConnected(c, b, a)`).
- **Alternative en cas de divergence** : Si une révision d'OpenTTD venait à rejeter un `from` non ferroviaire, l'alternative consiste à inspecter la direction de la voie sur `outer` via `AIRail.GetRailTracks(outer)` et vérifier la présence du bit correspondant à l'axe :
  - Axe X (`GetTileX(outer) != GetTileX(lead)`) : masque `AIRail.RAILTRACK_NE_SW`.
  - Axe Y (`GetTileY(outer) != GetTileY(lead)`) : masque `AIRail.RAILTRACK_NW_SE`.

---

## 4. Risques et Interactions

1. **Interaction avec `rail_geometry_guard`** :
   - Dans `OpexRailPathGeometryIssue` (activé sous `rail_geometry_guard=1` et `rail_geometry_prefilter=1`) :
     ```squirrel
     if (AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1) {
       return { kind = "end_jump", tile = leadB };
     }
     ```
   - Le garde amont rejette explicitement tout tracé se terminant par un saut (`end_jump`) avant toute phase de dépense.
   - Par conséquent, lorsque `rail_geometry_guard=1`, le correctif `rail_end_jump_connect` est **sans objet** pour l'arrivée B car ces tracés sont préfiltrés. Le filtre amont a été conservé tel quel conformément aux instructions.
2. **Risque de virage / franchissement oblique** :
   - Dans OpenTTD, les ponts et tunnels sont strictement rectilignes et orthogonaux. La condition `outer == lead + unit` garantit que la tuile de quai se trouve exactement dans l'axe du franchissement.
3. **Comportement au défaut** :
   - Avec `rail_end_jump_connect=0`, `OpexRailEndConnected` appelle directement `AIRail.AreTilesConnected(outer, lead, inner)`. Le comportement et les résultats sont strictement identiques à la version antérieure.
