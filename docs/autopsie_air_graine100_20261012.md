> **Note de relecture (Claude, 12/10)** — rapport d'agy archivé tel quel. Le « correctif minimal » du §6
> (marquer `seenStations` avant le test de saturation) correspond au **marquage anticipé déjà testé dans
> AC04-A v2** (+307 k opcodes en 1970–1971, rejeté) : ce n'est pas une piste neuve, et AC04-A reste au
> chantier catalogue de l'utilisateur. L'apport neuf de cette autopsie est **l'exposition en partie** (3/5
> graines, jusqu'à 30 passes bloquées, ~1,2–1,5 M£ de caisse dormante) et la **cause aval distincte** :
> `batch_plan_dead` ne retire pas le plan du portefeuille (`task_projects.nut`, `continue` sans purge), si bien
> que la resélection le remet en tête. Ce volet aval est traité séparément, hors catalogue.

# Autopsie : Projet AIR bloqué 3 mois, graine 100

**Document :** Autopsie causale du projet AIR bloqué 17 passes consécutives en 1974–1975 (`docs/taches.md §3`).  
**Code examiné :** Commit `9144dc5` (lecture stricte via `git show 9144dc5:<chemin>`).  
**Journal analysé :** `results/astar_pending_expo_5x6_20261011_engine/reference_seed100_r0.log` (5 210 247 octets, 28 050 lignes).

---

## Synthèse exécutive

L'anomalie « projet AIR bloqué 3 mois, graine 100 » est une **manifestation directe en jeu de l'anomalie AC04-A** (hub saturé reclassé à tort comme orphelin à `routes=0`).

Sur les 17 passes incriminées (`in_cap` entre 1,15 M£ et 1,48 M£, bien supérieur aux 40 964 £ requis), l'IA ne bloque pas sur une marge de caisse ni sur un devis, mais tente à chaque passe de construire une liaison **Hub-to-Hub entre deux aéroports ayant déjà atteint leur plafond de saturation** (3 routes par aéroport sous `air_hub_max_routes=3`).
À chaque passe, la garde vivante `OpexAirBatchPlanStillLive` détecte la saturation réelle et rejette le plan (`batch_plan_dead`). Cependant, ce rejet **n'invalide pas le portefeuille** et **n'écarte pas le projet du catalogue** : le projet reste en tête (`rank=0`), empêchant le portefeuille de progresser tant qu'aucun autre chantier (ex: rail) ne se termine.

---

## 1. Identité exacte du projet AIR (et ses 3 incarnations)

Le capital `best_nonrail_cap=40964` correspond très exactement à la formule de financement d'une liaison **Hub-to-Hub** sans construction d'aéroport (`newAirports = 0`) :
$$\text{capital} = \text{prix de l'avion (38 964 £)} + \text{marge de sécurité Hub-Hub (2 000 £)} = 40 964\text{ £}$$
- **Avion :** Moteur 223 (*Bakewell Luckett LB-10*), 1 appareil.
- **Type :** `arm = "hubhub"`, deux extrémités réutilisées (`reuseA = true`, `reuseB = true`), coût d'infrastructure nul.
- **Rang :** Rang 0 du portefeuille (ou meilleur non-rail).

Les 17 passes bloquées se décomposent en **3 périodes successives**, portant sur **3 paires Hub-to-Hub distinctes** mais de signature identique :

| Période | Passes | Dates | Paire (Tuiles / Villes) | Profit annuel prédit | ROI / Score | Motif de fin de blocage |
|---|---|---|---|---|---|---|
| **1** | 487 à 493 (7 passes) | 26/10/1974 au 22/11/1974 | 24247 (Town 31, *Chufingley Market*) $\leftrightarrow$ 22803 (Town 6, pop 1037) | 8 655 £/an | ROI 222 / Score 61.6 | Pose rail 20909-31179 le 06/12/1974 (passe 494) |
| **2** | 495 à 501 (7 passes) | 07/12/1974 au 31/12/1974 | 61075 (Town 27, *Ruttown*) $\leftrightarrow$ 26430 (Town 35, pop 303) | 9 841 £/an | ROI 252 / Score 63.1 | Régénération annuelle du catalogue (02/01/1975) |
| **3** | 518 à 520 (3 passes) | 16/05/1975 au 27/05/1975 | 61075 (Town 27, *Ruttown*) $\leftrightarrow$ 59176 (Town 0, *Sendington*) | 6 330 £/an | ROI 162 / Score 50.7 | Pose rail 15063-31179 le 27/05/1975 (passe 520) |

---

## 2. Cheminement dans le code et motif de rejet à chaque passe

Pour chacune des 17 passes, l'ordonnanceur appelle `_tryBuildProjects` dans `task_projects.nut` :

1. **Parcours du portefeuille (`task_projects.nut:1601-1725`) :**
   - Le projet `rank=0` est sélectionné : `mode == "air"`.
   - Ligne 1711 : `if (project.mode == "air" && !OpexAirBatchPlanStillLive(project.payload, this._lines))`.
2. **Évaluation de vivacité (`task_air.nut:571-604`) :**
   - Lignes 596-597 :
     ```squirrel
     if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;
     if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;
     ```
3. **Contrôle de capacité du Hub (`task_air.nut:551-568`) :**
   - La fonction compte le nombre réel de lignes actives dans `lines` connectées à la station de l'ancre (`routes`).
   - Ligne 566 : `local maxRoutes = OpexAirAirportMaxRoutes(airportType);` (dans `air_trip.nut:174-181`, vaut `min(AIR_HUB_MAX_ROUTES, 4) = 3` pour les aéroports communaux/petits).
   - Ligne 567 : `return routes < maxRoutes;`.
   - **Preuve matérielle :** Les deux extrémités ont déjà 3 lignes actives chacune :
     - Town 31 (24247) possède les lignes 15, 31, 39 ($routes = 3$).
     - Town 6 (22803) possède les lignes 1, 14, 18 ($routes = 3$).
     - Town 27 (61075) possède les lignes 14, 17, 29 ($routes = 3$).
     - Town 35 (26430) possède les lignes 12, 24, 27 ($routes = 3$).
     - Town 0 (59176) possède les lignes 3, 15, 19 ($routes = 3$).
   - `routes < maxRoutes` est faux ($3 < 3$ faux). `OpexAirBatchPlanStillLive` retourne `false`.
4. **Rejet silencieux en cours de passe (`task_projects.nut:1721-1724`) :**
   - Le plan est écarté avec le motif `reason = "batch_plan_dead"` inséré dans `passDiscards`.
   - Ligne 1724 : `continue;` saute au candidat suivant **sans retirer le plan de `this._projects.best`**.
5. **Sortie de passe :**
   - Le candidat suivant (rail fret ou pax) a un pathfinding A* en vol : rejeté par `search_in_progress`.
   - Aucun candidat n'est construit $\rightarrow$ `P2_PASS` et `P5_RAIL_PASS` enregistrent `stop=no_candidate_built`.
   - **Événements du journal :** `DECISION_LOG` étant limité à la première passe du mois civil (`_lastProjectScanMonth != ym`, `task_projects.nut:1593-1597`), `PROJECT_DISCARD ... reason=batch_plan_dead` n'est émis que les jours de bascule mensuelle :
     - Ligne 24200 (1974-11-04) : `PROJECT_DISCARD rank=0 mode=air src=24247 dst=22803 reason=batch_plan_dead`
     - Ligne 24477 (1974-12-06) : `PROJECT_DISCARD rank=0 mode=air src=61075 dst=26430 reason=batch_plan_dead`
     - Ligne 26077 (1975-05-26) : `PROJECT_DISCARD rank=0 mode=air src=61075 dst=59176 reason=batch_plan_dead`

---

## 3. Pourquoi il RESTE en tête : Lien direct avec le bug AC04-A

Le maintien en tête du projet provient de la conjonction de deux défaillances architecturales :

### A. La cause amont : Bug de découverte de hub (AC04-A)
Dans `ai/OpexAI/air_planning.nut:1328-1364` (commit `9144dc5`) :
```squirrel
// Boucle 1 : parcours des lignes existantes
local maxRoutes = OpexAirAirportMaxRoutes(existingType);
if (routeCount >= maxRoutes) continue; // <-- SAUT AVANT seenStations.rawset !
...
seenStations.rawset(station, true);
hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });

// Boucle 2 : aéroports orphelins (censés être des aéroports sans aucune ligne, ex. BFAIL)
local orphanList = AIStationList(AIStation.STATION_AIRPORT);
for (local st = orphanList.Begin(); !orphanList.IsEnd(); st = orphanList.Next()) {
  if (st in seenStations) continue; // <-- La station saturée n'y est pas !
  ...
  seenStations.rawset(st, true);
  hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 }); // <-- Reclassée à 0 route !
}
```
**Mécanisme exact :**
1. Une station active saturée ($routeCount \ge 3$) est rejetée par la boucle 1 avec un `continue` **avant** d'être marquée dans `seenStations`.
2. La boucle des orphelins parcourt toutes les stations de la carte. Trouvant la station saturée absente de `seenStations`, elle la classe comme un aéroport « orphelin » avec **`routes = 0`**.
3. Le générateur de paires Hub-to-Hub (`air_planning.nut:1805-1925`) reçoit donc ces deux hubs saturés marqués comme ayant 0 route. Il génère la liaison, prédit un excellent profit pour un coût de 40 964 £, et la catalogue.

### B. La cause aval : Absence de mémoire d'abandon ou d'invalidation
1. **Pas de purge dans `task_projects.nut` :** Lorsqu'un plan subit `batch_plan_dead`, l'ordonnanceur fait simplement `continue;`. Le tableau `this._projects.best` n'est pas modifié.
2. **Resélection aveugle :** Entre deux passes, `OpexReselectProjects` (`projects.nut`) prend les candidats existants dans le cache et les reclasse selon la trésorerie disponible. Il ne revalide pas la saturation des hubs. Le projet conserve son score élevé et réapparaît en `rank=0`.
3. **Le plan A* rail en vol bloque le reste :** Tant que la recherche A* du projet ferroviaire au rang 1 est active (`search_in_progress`), le rail ne peut pas être construit pour purger ou forcer un renouvellement du portefeuille.

---

## 4. Dénouement et coût d'opportunité

### Dénouement
- **Période 1 (26/10 au 22/11/1974) :** Débloquée le 06/12/1974 (passe 494) par l'achèvement du pathfinder rail `20909 <-> 31179` (`PROJECT_CHOSEN rank=2 cost=40895 profit=3258`), provoquant une reconstruction incrémentale du portefeuille.
- **Période 2 (07/12 au 31/12/1974) :** Débloquée le 02/01/1975 par l'horloge annuelle (`C39_PASS_CLOCK phase=annual year=1975 key=worker|regen_candidates`), qui vide et reconstruit tout le vivier.
- **Période 3 (16/05 au 27/05/1975) :** Débloquée le 27/05/1975 (passe 520) par l'achèvement du tracé rail céréales `15063 <-> 31179` (`PROJECT_CHOSEN rank=1 cost=47398 profit=28005 roi=590`).
- **Devenir du projet :** Le projet AIR en lui-même n'a **JAMAIS été construit**, car physiquement interdit par la limite des slots.

### Coût d'opportunité
Pendant ces 17 passes (durée cumulée de blocage : **~75 jours**), les projets finançables en file d'attente étaient :
1. **Lignes ferroviaires prêtes :**
   - En Période 1 : Ligne rail passagers `12595 <-> 22803` (coût 41 119 £, profit 4 506 £/an, bloquée ensuite pour `too_close_no_join`).
   - En Période 2 : Ligne rail `20909 <-> 31179` prête à construire dès le 03/12/1974 mais retardée de plusieurs ticks/jours.
2. **Capitaux dormants :** Plus de **1,15 à 1,48 M£ de trésorerie disponible** immobilisée sans investissement actif alors que le vivier contenait des projets alternatifs viables.

---

## 5. Présence sur les 4 autres graines du même 5×6

L'analyse des 5 fichiers journaux sous `results/astar_pending_expo_5x6_20261011_engine/` démontre que le phénomène n'est pas isolé à la graine 100 :

| Graine | Événements `batch_plan_dead` | Passes `stop=no_candidate_built` avec AIR finançable | Séries $\ge 5$ passes consécutives bloquées sur le MÊME projet AIR fantôme |
|---|---|---|---|
| **100** | **43** | **121** | **7 séries** (11 p. en 1972, 6 p. en 1973, 10 p. en 1973, 26 p. en 1974, 18 p. en 1974, **10 p. fin 1974**, **7 p. déc. 1974**) |
| **5678** | **12** | **92** | **4 séries** (5 p. en 1971, 18 p. en 1971, 9 p. en 1972, **30 passes consécutives en nov-déc 1972** sur `src=36956 dst=61399`) |
| **42** | **9** | **7** | **1 série** (5 passes du 17/10/1971 au 20/10/1971, `cap=40964`, `score=1602.87`) |
| **999** | **76** | **2** | 0 série $\ge 5$ (le catalogue régénère plus souvent ou les échecs dispersent les scores) |
| **1234** | **3** | **1** | 0 série $\ge 5$ |

Le phénomène est donc **structurel et reproductible** sur au moins **3 graines sur 5** (100, 5678 et 42), avec des blocages atteignant jusqu'à 30 passes consécutives (graine 5678 en 1972).

---

## 6. Hypothèse causale et correctif MINIMAL envisageable

### Hypothèse causale
Une station d'aéroport saturée est exclue de `seenStations` par un saut prématuré dans la boucle des lignes actives de `DiscoverHubs`. Elle est ensuite réinjectée par la boucle des orphelins avec `routes = 0`. Le plan Hub-Hub fantôme ainsi produit est sélectionné au sommet du portefeuille en raison de son faible capital et de son score artificiel, puis systématiquement rejeté par la garde vivante à chaque passe, sans jamais être purgé du portefeuille ni mémorisé comme invalide.

### Correctif MINIMAL envisageable (2 lignes)

Au lieu de la solution complexe testée sous `ac04_hub_route_fix` (qui recomptait dynamiquement les routes de tous les orphelins et consommait +213 000 opcodes VM), le correctif minimaliste consiste à **enregistrer la station dans `seenStations` AVANT le test de saturation** :

Dans `ai/OpexAI/air_planning.nut` (autour de la ligne 1329) :
```diff
         local existingType = AIAirport.GetAirportType(end.anchor);
         if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
         local station = AIStation.GetStationID(end.anchor);
         if (!AIStation.IsValidStation(station)) continue;
+        seenStations.rawset(station, true);
         local routeCount = 0;
         ...
         local maxRoutes = OpexAirAirportMaxRoutes(existingType);
         if (routeCount >= maxRoutes) continue;
-        seenStations.rawset(station, true);
         hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });
```

**Pourquoi ce correctif est optimal :**
1. **Coût en opcodes :** Rigoureusement nul ($\Delta \text{opcodes} = 0$, déplacement d'une instruction `rawset` existante). Aucun balayage supplémentaire de lignes.
2. **Efficacité :** Une station saturée ayant déjà des lignes ne sera **jamais** traitée par la seconde boucle des orphelins (`if (st in seenStations) continue;`). Elle ne sera donc jamais déclarée orpheline à `routes = 0`.
3. **Pureté fonctionnelle :** Les vrais aéroports orphelins (ex: issus d'un `BFAIL` où un seul aéroport a été posé sans aucune ligne) conservent leur traitement intact.

### Mesure de validation requise
1. **Contrat unitaire :** Test statique dans `sweeps/test_ac04_air_hub_site_resume.py` vérifiant qu'une station ayant $\ge 3$ routes est présente dans `seenStations` et absente de `hubs`.
2. **Validation sur logs :** Rejeu du diagnostic 5×6 avec comptage des événements `PROJECT_DISCARD mode=air reason=batch_plan_dead` : la métrique cible est la **disparition totale des rejets `batch_plan_dead` pour cause de hub saturé** sur les 5 graines.
3. **Règle d'adoption :** Validation de neutralité opcodes et économique selon le protocole V102 (A40×3 puis B20×10).
