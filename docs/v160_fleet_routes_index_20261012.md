# V160 — fleet.resize : compter les routes par aéroport une fois par passe (optimisation d'opcodes stricte)

**Date :** 12 octobre 2026\
**Branche :** `v160-fleet-routes-index`\
**Contexte & Objectif :** Réduire le coût quadratique en opcodes de `OpexAI::_resizeAirFleets` (`task_air.nut`, span `fleet.resize`), mesuré à ~1 k/appel en 1970 et atteignant 110–155 k/appel en 1974 (10–16 M opcodes/an).\

---

## 1. Mesure et instrumentation (`PROBE_SPAN_TRACE`)

Des sous-spans `OpexSpanAgg` ont été placés autour des étapes clés de `_resizeAirFleets` sous `PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null`, garantissant un coût d'allocation et de mesure strictement nul lorsque la sonde est inactive :
- `fleet.sort` : tri des lignes air par ROI (`OpexAirFleetPriorityCompare` / `OpexAirFleetSortSelect`).
- `fleet.cadence_cap` : calcul du plafond physique de cadence (`OpexAirCadenceCap` / `OpexAirCadenceCapIndexed`).
- `fleet.refusal` : refus pré-cadence et gardes diverses (`OpexAirFleetRefusal`).
- `fleet.marginal` : calcul du modèle marginal existant (`OpexAirExistingLineMarginalEconomics`).
- `fleet.first_live` : garde 1→2 C121 basée sur `OpexC121FirstLiveBalanced90`.
- `fleet.add_plane` : tentative d'ajout physique ou rééquipement via `OpexAirAddPlane`.

---

## 2. Implémentation du réglage `air_fleet_routes_index`

### Réglage et globale
- **Réglage :** `air_fleet_routes_index` dans [info.nut](../ai/OpexAI/info.nut#L1487-L1495) (min 0, max 2, défaut 0 sur les 4 profils `easy_value`, `medium_value`, `hard_value`, `custom_value`).
- **Globale :** `AIR_FLEET_ROUTES_INDEX <- 0;` dans [globals_pre.nut](../ai/OpexAI/globals_pre.nut#L759-L761).
- **Chargement :** [settings.nut](../ai/OpexAI/settings.nut#L166-L168).

### Modes
- **0 (Défaut / Historique) :** Appel direct historique `OpexAirCadenceCap(line, catalog, lines)` recalculant `OpexAirLiveRoutesAtAirport` pour chaque ligne examinée (O(N²)).
- **1 (Indexé) :** Construction paresseuse (lazy build) au premier appel de `AIR_CADENCE_CAP` via `OpexAirBuildRoutesIndex(this._lines)`. L'index est une table Squirrel `StationID -> count` des lignes air vivantes. Chaque consultation se fait en O(1) dans `OpexAirCadenceCapIndexed`.
- **2 (Comparateur / Diagnostic) :** Calcul conjoint des deux méthodes (directe historique et indexée). En cas de divergence, émission de `OpexDecide("FLEET_ROUTES_MISMATCH", "line=" + line.lineId + " direct=" + capDirect + " indexed=" + capIndexed)` sous `DECISION_LOG`. En fin de passe, rapport global `OpexDecide("FLEET_ROUTES_INDEX", "year=" + year + " lines=" + airLines.len() + " mismatches=" + routesMismatchCount)`. Utilisation du résultat direct pour ne pas dériver.

### Prédicat exact et déduplication
Dans [air_trip.nut](../ai/OpexAI/air_trip.nut#L121-L153), `OpexAirBuildRoutesIndex` reproduit fidèlement le prédicat de `OpexAirLiveRoutesAtAirport` :
- `line.mode == "air"`
- Ligne vivante : au moins un véhicule valide dans `vehicles` ou `vehicle` valide
- Résolution en `StationID` via `OpexAirLineStationId(other, 0)` et `OpexAirLineStationId(other, 1)`
- Une ligne reliant la même station aux deux bouts (`otherA == otherB`) n'incrémente le compteur de cette station qu'une seule fois.

### Politique d'invalidation
L'index local `routesIndex` est invalidé (`routesIndex = null`) à chaque événement au sein de la passe susceptible de modifier la vivacité ou la flotte :
1. Reprise/remplacement V92 via `OpexAirAddPlane`.
2. Reconstitution de crash via `OpexAirRefleetCrashedPlane`.
3. Achat d'un avion supplémentaire dans la boucle `while (have < maxPlanesForAirport && addedThisPass < maxAddedPerPass)` via `OpexAirAddPlane`.

---

## 3. Analyse de `task_report.nut`

Dans [task_report.nut](../ai/OpexAI/task_report.nut#L568-L569), `OpexAirLiveRoutesAtAirport` est appelé uniquement sous le bloc :
```squirrel
if (C98_AIR_REALIZED_PROBE && lMode == "air") {
    ...
    local liveRoutesA = OpexAirLiveRoutesAtAirport(line.stationA, this._lines);
    local liveRoutesB = OpexAirLiveRoutesAtAirport(line.stationB, this._lines);
    ...
}
```
Ce bloc est sous la sonde `C98_AIR_REALIZED_PROBE` (défaut 0 / OFF). En runtime standard de jeu ou de banc, cette branche n'est jamais exécutée. Elle n'impacte pas le budget d'opcodes normal. `OpexAirBuildRoutesIndex` y est directement réutilisable si cette sonde venait à être activée pour un diagnostic lourd.

---

## 4. Recensement des autres coûts O(lignes) dans `_resizeAirFleets` et appelés

1. **`OpexAirFleetYield` & Comparateur de tri (`task_air.nut:1043`, `1055`) :**
   - Parcourt `line.vehicles.len()`, mais n'itère pas sur l'ensemble de `_lines`. Coût O(1) par ligne, O(N log N) pour le tri complet.
2. **`OpexC121RefreshVisibleFleet` (`air_fleet.nut:316`) :**
   - Appelé pour chaque ligne acceptant les premières gardes.
   - Construit `others` en parcourant `_lines` (`task_air.nut:1176`, `air_fleet.nut:352`).
   - Il retourne immédiatement quand `C121_AIR_VISIBLE_COMPETITION == 0`. **Correction (Claude) :** ce n'est pas le défaut courant : `settings.nut` pose `C121_AIR_VISIBLE_COMPETITION = C121_AIR_ECONOMICS`, à 1 par défaut depuis `36fa8c7`.
   - Sous C121 actif, il dispose d'un cache mensuel (`C121_VISIBLE_FLEET_CACHE`) ; V155 a montré que le garder derrière les gardes « O » ne gagne rien.
3. **`OpexAirAddPlane` (`air_fleet.nut:397`) & `OpexAirConsiderReplace` (`air_fleet.nut:205`) :**
   - Dans `OpexAirConsiderReplace`, appel à `OpexAirCadenceCap(line, catalog, null)` avec `lines = null`. Comme `lines == null`, `OpexAirLiveRoutesAtAirport` retourne immédiatement 0 en O(1).
4. **`OpexAirExistingLineMarginalEconomics` (`air_route_economics.nut:171`) :**
   - Ne parcourt pas `lines`, inspecte uniquement le véhicule template de la ligne en cours et effectue un calcul analytique de recette/coût.

Le goulot O(N²) dominant au défaut dans `_resizeAirFleets` était donc bien `OpexAirCadenceCap` avec `lines = this._lines`.

---

## 4 bis. Revue (Claude)

`OpexAirCadenceCapIndexed` dupliquait tout le corps de `OpexAirCadenceCap`. Il est ramené à un
appel de `OpexAirCadenceCap(line, catalog, lines, routesIndex)`, où seul le comptage des routes
change (`OpexAirRoutesIndexAt`) : une seule formule de cadence à maintenir.

Limite d'équivalence : un avion qui s'écrase pendant la passe (le script peut être suspendu
entre deux lignes) n'invalide pas l'index. Le mode 2 le dira.

## 5. Tests et validation

Le fichier de tests unitaires [sweeps/test_v160_fleet_routes_index.py](../sweeps/test_v160_fleet_routes_index.py) a été créé et exécuté avec succès :
- **Contrats statiques :**
  - Présence et défauts à 0 de `air_fleet_routes_index` et `AIR_FLEET_ROUTES_INDEX`.
  - Présence et protection des sous-spans `fleet.*`.
  - Signature et présence de `OpexAirBuildRoutesIndex` et `OpexAirCadenceCapIndexed`.
  - Points d'invalidation de l'index dans `_resizeAirFleets`.
  - Détection et logging des mismatches en mode 2.
- **Équivalence fonctionnelle :**
  - Vérification sur listes vides, lignes uniques, stations partagées.
  - Vérification de la déduplication quand une ligne a la même station aux deux extrémités.
  - Ignorance des lignes mortes et des modes non-air.
  - Vérification sur 50 configurations aléatoires de réseaux avec combinaisons mixtes de véhicules vivants/morts.

Résultat : **11/11 tests passés avec succès** (0 régression sur la suite existante).
