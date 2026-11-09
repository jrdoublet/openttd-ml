# Revue de code — Réconciliation des contrats et projections suite au commit `ecd97b17` (`road1y_mail_p2p`)

**Date :** 9 novembre 2026  
**Branche :** `road1y-night`  
**Base :** `ecd97b17` (`fix(road1y): unblock autonomous mail pairs and demand-driven fleets`)  
**Auteur :** Antigravity  

---

## 1. Contexte et périmètre

Le commit `ecd97b17` a fait évoluer l'implémentation Squirrel de `road1y_mail_p2p*` (`ai/OpexAI/bus_districts.nut`, `builder_road.nut`, `settings.nut`, `globals_pre.nut`, `info.nut`) sans mettre à jour les tests de contrat ni les tables d'empreintes et hunks de projection.

Cette intervention porte **exclusivement sur les tests et fixtures Python/JSON** (aucun fichier `.nut` modifié) :
1. Audit complet du diff Squirrel de `ecd97b17` (vérification de l'absence de bug de syntaxe ou d'identifiant non déclaré).
2. Mise à jour exigeante des contrats dans `sweeps/test_road1y_mail_p2p.py` et `sweeps/test_road1y_multimodal_gate.py`.
3. Synchronisation des hunks `ROAD1Y-B2` dans `sweeps/fixtures/road100_bus_districts_hunks.json` et des tables de projection SHA256 dans `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py` et `sweeps/rail_sibling_legacy.py`.

---

## 2. Audit du code Squirrel (`ecd97b17`)

| Critère | Statut | Vérification |
|:---|:---:|:---|
| **Syntaxe et identifiants Squirrel** | **CONFORME** | Toutes les fonctions appelées (`OpexRoadBfsPath`, `OpexRoadTraceMulti`, `OpexRoadOnDtAxis`, `OpexRoadTraceBuildable`, `OpexRoad1yAStarSearch`, `OpexRoadRollback`, `OpexRoadFindDepot`, `OpexRoad100CatchmentOverlaps`) existent avec les signatures exactes attendues. |
| **Mots réservés / `.find(` / lambdas** | **CONFORME** | Aucun mot réservé (`clone`, `base`, `parent`, `static`, `delegate`, `resume`, `vargc`, `vargv`), aucun `.find(`, aucune fonction anonyme `function(` dans les 7 fonctions `OpexRoad1y*MailP2P*`. |
| **Comportement à 0 inchangé** | **CONFORME** | `ROAD1Y_MAIL_P2P == 0` coupe `OpexRoad1yMailP2PStep`, `OpexRoad1yRefleetMailP2PLine`, la branche `mail_p2p` de `OpexRoadRefleet` et le hook `OpexRoad1yRefleetSaved`. |
| **Double chargement dans `settings.nut`** | **CONFORME** | Lecture de `road1y_mail_p2p*` dans `OpexLoadBusDistrictSettings` avant `require("bus_districts_overrides.nut")` (pour installer le hook `_refleetRoadLines <- OpexRoad1yRefleetSaved` au chargement du fichier avant `Start` même si `road1y_mail_on_pax=0`) et dans `OpexLoadSettings`, avec garde `!road1yRoadOnly` dans les deux chargeurs. |

---

## 3. Analyse des modifications de tests et fixtures

### 3.1. Contrats `sweeps/test_road1y_mail_p2p.py`
Les tests vérifient désormais tous les nouveaux invariants de `ecd97b17` sans affaiblissement :
- **Sites multiples (`OpexRoad1yFindMailP2PSite`) :** retour d'un tableau `[]` (jusqu'à 8 candidats triés par score décroissant), rayon `rad = 10`, espacement minimal `AIMap.DistanceManhattan(tile, other) <= 2`, pénalité `score /= 2` sur `OpexRoad100CatchmentOverlaps` au lieu d'un veto.
- **Paires actives (`OpexRoad1yMailP2PActivePairs`) :** filtrage par `line.cargo != ai._catalog.mailCargo` pour n'exclure que les paires ayant déjà un service courrier.
- **Budget de chemins (`OpexRoad1yMailP2PTrace`) :** décompte `budget.paths` (`paths = 48, nodes = 6000`), priorité au réseau existant (`OpexRoadBfsPath` à 4096 nœuds), puis `OpexRoadTraceMulti` (4 variantes) et `OpexRoad1yAStarSearch` borné par `budget`, sous garde `missing <= maxMissing && OpexRoadTraceBuildable(trace)`.
- **Curseur de paires et gardes (`OpexRoad1yMailP2PStep`) :** curseur `ROAD1Y_MAIL_P2P_CURSOR` sur `pairCount = nTowns * nTowns` avec rotation source/destination, garde population `>= 400`, distance Manhattan `16..192`, plafonds `attempts >= 24 || budget.paths <= 0 || siteSearches >= 32 || opened >= 3`, et inversion `siteB.prod > siteA.prod` pour placer le plus gros gisement en source.
- **Chargement complet à la source uniquement et rollback (`OpexRoad1yBuildMailP2P`, `OpexRoadRefleet`, `OpexRoad1yRefleetMailP2PLine`) :** `AIOrder.OF_FULL_LOAD_ANY` sur l'arrêt source A uniquement, `OF_NONE` (avec `OF_NON_STOP_INTERMEDIATE`) sur la destination B, et nettoyage complet via `OpexRoadRollback(siteA.tile, siteB.tile, newDepot, ..., builtRoad)` sur chaque branche d'échec.
- **Renfort basé sur la capacité engagée (`OpexRoad1yRefleetMailP2PLine`) :** calcul de `committedCapacity` (capacité libre des fourgons au dépôt ou à `<= 2` tuiles des gares A/B), `backlog = totalWaiting - committedCapacity`, garde `if (have > 0 && backlog < capacity) return;`, `want = have == 0 ? 2 : backlog / capacity`, et plancher `if (mailCap < 2) mailCap = 2;`.

### 3.2. Inventaire des deux chargeurs (`sweeps/test_road1y_multimodal_gate.py`)
- Ajout documenté de `road1y_mail_p2p`, `road1y_mail_p2p_missing`, `road1y_mail_p2p_cash` et `road1y_mail_p2p_start` dans `BUS_DISTRICT_KEYS`.
- Vérification dans `test_getsetting_sites_are_only_the_two_loaders` que chaque clé présente dans `LOAD_SETTINGS_KEYS & BUS_DISTRICT_KEYS` est lue exactement 2 fois dans `settings.nut` (et 1 seule fois sinon), et jamais hors de `settings.nut`.
- Vérification de la garde `!road1yRoadOnly` dans les deux chargeurs avant `require("bus_districts_overrides.nut")`.

### 3.3. Projections et hunks (`sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/road100_off_projection.py`, `sweeps/rail_*_legacy.py`)
- Mise à jour du hunk 32 de `builder_road.nut` et du hunk 3 de `settings.nut` dans `road100_bus_districts_hunks.json` pour refléter l'état courant de la couche `ROAD1Y-B2`.
- Prise en compte dans `_subtract_exact` (`road100_off_projection.py`) des deux témoins historiques figés par SHA256 exact (`44d9313eab` et `origin/master`) antérieurs à l'ajout des lignes `ROAD1Y_MAIL_P2P` dans ces deux hunks.
- Mise à jour des tables SHA256 `ROAD1Y_B2_RAIL_MERGE`, `ROAD1Y_B2_RAIL_MERGE_STAGES` et `_MERGE_SHA` pour `globals_pre.nut`, `info.nut` et `settings.nut`.
- Le nombre d'`AddSetting` dans `info.nut` (75) n'ayant pas changé dans `ecd97b17`, le plafond de `test_v251_inventory.py` (77) est conservé tel quel.

---

## 4. Résultats des tests hôte

- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : **97 tests réussis** (0 échec).
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : **236 tests réussis** (0 échec, 3 ignorés).
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : **7 tests réussis** (0 échec).
- `git diff --check` : **0 anomalie**.
