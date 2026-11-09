# Revue de code : Correctifs ciblés `road1y_mail_p2p` (fix2)

**Date :** 2026-11-09  
**Branche :** `road1y-night` (base `3bde1635`)  
**Référence causale :** `$T/agy_mail8.md`

---

## 1. Vérification préalable des 4 points dans le code (`3bde1635`)

Chaque affirmation de la consigne a été vérifiée dans l'arbre `3bde1635` avant modification :

1. **Bug dépôt (`OpexRoad1yMailP2PStep`, `ai/OpexAI/bus_districts.nut` l. 1160–1175 dans `3bde1635`) — CONFIRMÉ :**
   - `OpexRoadFindDepot(trace, siteA, siteB, true)` était appelé **avant** le bloc `if (siteB.prod > siteA.prod)` qui inverse `trace` et échange `(ta, tb)` ainsi que `(siteA, siteB)`.
   - Or `OpexRoadFindDepot(..., nearA=true)` cherche prioritairement un emplacement de dépôt dans les 4 premières arêtes depuis `siteA` (`trace[0..3]`). Lorsque `siteB.prod > siteA.prod`, le dépôt restait donc attaché à l'ancien `siteA` (devenu destination `finalSiteB`), obligeant les fourgons construits/clonés au dépôt à parcourir toute la ligne à vide jusqu'à la source `finalSiteA` avant de commencer à charger.
   - **Correction (`ai/OpexAI/bus_districts.nut` l. 1179–1199) :** l'inversion `(finalTa, finalTb, finalSiteA, finalSiteB, finalTrace)` lorsque `siteB.prod > siteA.prod` est effectuée **avant** `OpexRoadFindDepot(finalTrace, finalSiteA, finalSiteB, true)`.

2. **Connexion des deux côtés de l'arrêt traversant (`ai/OpexAI/bus_districts.nut`) — CONFIRMÉ :**
   - Dans `OpexRoad1yBuildMailChild` (`ai/OpexAI/bus_districts.nut` l. 567–585), les arrêts traversants courrier vérifient `AIRoad.AreRoadTilesConnected(tile, front) && AIRoad.AreRoadTilesConnected(tile, back)`.
   - Dans `OpexRoad1yFindMailP2PSite` (`3bde1635` l. 846) et `OpexRoad1yBuildMailP2P` (`3bde1635` l. 945–960), aucune vérification `AreRoadTilesConnected(tile, front)` / `(tile, back)` n'était faite sur `siteA` et `siteB`, permettant de poser un arrêt traversant dont une extrémité est en cul-de-sac ou non raccordée.
   - **Correction (`ai/OpexAI/bus_districts.nut` l. 846–848, 947–948, 963–964, 985–992) :**
     - Filtre amont dans `OpexRoad1yFindMailP2PSite` : exige `AIRoad.AreRoadTilesConnected(tile, front) && AIRoad.AreRoadTilesConnected(tile, back)`.
     - Garde à la pose dans `OpexRoad1yBuildMailP2P` : incluse dans `validA` et `validB` après `BuildDriveThroughRoadStation`.
     - Garde post-route dans `OpexRoad1yBuildMailP2P` : juste après la boucle `BuildRoad`, vérifie que `siteA` et `siteB` sont connectés à leurs `front` et `back` respectifs, avec `OpexRoadRollback(siteA.tile, siteB.tile, null, null, builtRoad)` et journal `reason=STOP_CONN` en cas d'échec.

3. **Sous-réglages `road1y_mail_p2p_cap` (0..3, défaut 0) et `road1y_mail_p2p_maxdist` (0..192, défaut 0) — CONFIRMÉ :**
   - Dans `3bde1635`, le plafond d'ouvertures par appel/mois était codé en dur à `opened >= 3` (l. 1122) et la distance Manhattan maximale à `dist > 192` (l. 1137).
   - **Correction :** ajout du motif `AddSetting` complet pour `road1y_mail_p2p_cap` (`min=0, max=3, def=0`) et `road1y_mail_p2p_maxdist` (`min=0, max=192, def=0`) dans `ai/OpexAI/info.nut` (4 difficultés à `0`), `ai/OpexAI/globals_pre.nut`, et dans **tous** les sites de lecture de `ai/OpexAI/settings.nut` (`OpexLoadSettings` et `OpexLoadBusDistrictSettings`, forcés à `0` si `!road1yRoadOnly`). Câblage dans `OpexRoad1yMailP2PStep` via `maxOpened = (ROAD1Y_MAIL_P2P_CAP > 0) ? ROAD1Y_MAIL_P2P_CAP : 3` et `maxDist = (ROAD1Y_MAIL_P2P_MAXDIST > 0) ? ROAD1Y_MAIL_P2P_MAXDIST : 192`.

4. **Sous-réglage `road1y_mail_p2p_noload` (0..1, défaut 0) — CONFIRMÉ AVEC PRÉCISION SUR LE NOM DE LA FONCTION DE REPRISE :**
   - **Précision issue de la vérification du code (`3bde1635` / `ecd97b17`) :** le nom `OpexRoad1yEnsureMailP2PFullLoad` mentionné dans la note d'analyse n'existe pas dans `3bde1635` ; quant à `ai/OpexAI/bus_districts_overrides.nut` l. 1532, il s'agit de la reprise `ROAD100_PAX_DOUBLE` des lignes passagers. Dans `ecd97b17` (`3bde1635`), la passe de mise à niveau des ordres `mail_p2p` est logée directement dans `OpexRoad1yRefleetMailP2PLine` (`ai/OpexAI/bus_districts.nut` l. 1242–1248), qui est appelée à chaque passe de flotte et après chargement via `OpexRoad1yRefleetSaved` (`ai/OpexAI/bus_districts_overrides.nut` l. 1337).
   - **Correction :** ajout du sous-réglage `road1y_mail_p2p_noload` (0..1, défaut 0) selon le motif `AddSetting` complet, et câblage sur les **trois** sites où les drapeaux d'ordres `mail_p2p` sont posés ou réconciliés :
     1. Création initiale dans `OpexRoad1yBuildMailP2P` (`ai/OpexAI/bus_districts.nut` l. 1020–1024) : `sourceOrderFlags = ROAD1Y_MAIL_P2P_NOLOAD != 0 ? orderFlags : (orderFlags | AIOrder.OF_FULL_LOAD_ANY)`.
     2. Ajout de véhicule standard dans `OpexRoadRefleet` (`ai/OpexAI/builder_road.nut` l. 6509) : `(ROAD1Y_MAIL_P2P_NOLOAD != 0 ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag`.
     3. Synchronisation/reprise des ordres dans `OpexRoad1yRefleetMailP2PLine` (`ai/OpexAI/bus_districts.nut` l. 1244–1247) : `sourceFlags = (ROAD1Y_MAIL_P2P_NOLOAD != 0 ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | AIOrder.OF_NON_STOP_INTERMEDIATE`.

---

## 2. Vérification des invariants Squirrel et de la projection B2

- **Invariants de compilation Squirrel :** aucun mot réservé (`clone`, `base`, `static`, etc.), aucun appel `.find(`, aucune fonction anonyme `function(`, aucune constante non littérale.
- **Préservation du défaut :** `ROAD1Y_MAIL_P2P`, `ROAD1Y_MAIL_P2P_CAP`, `ROAD1Y_MAIL_P2P_MAXDIST` et `ROAD1Y_MAIL_P2P_NOLOAD` valent tous `0` par défaut aux 4 difficultés. Lorsque `road1y_mail_p2p > 0` avec les nouveaux sous-réglages à `0`, le comportement de `ecd97b17` est conservé à l'identique hormis les correctifs de bugs 1 (dépôt côté source finale) et 2 (connexion bilatérale des arrêts traversants).
- **Garde multimodale :** hors route seule (`!road1yRoadOnly`), `ROAD1Y_MAIL_P2P_CAP`, `ROAD1Y_MAIL_P2P_MAXDIST` et `ROAD1Y_MAIL_P2P_NOLOAD` sont forcés à `0` dans `OpexLoadSettings` et `OpexLoadBusDistrictSettings`.
- **Projection OFF et hunks B2 :** `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py` et `sweeps/rail_sibling_legacy.py` ont été mis à jour avec les plages exactes et les SHA256 correspondants.

---

## 3. Contrôles exécutés sur l'hôte

- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : **97 tests OK**
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : **236 tests OK** (3 ignorés `numpy`)
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : **7 tests OK**
- `git diff --check` : **0 anomalie**
