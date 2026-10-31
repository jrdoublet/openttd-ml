# PCAL-03 — Inventaire chiffré des gros postes d'opcodes précalculables

**Date :** 21 octobre 2026  
**Branche git :** `pcal03` (`/home/deploy/projects/wt-pcal03`)  
**Cadre :** Règle des optimisations d'opcodes ([AGENTS.md](../../AGENTS.md) §4). Document seul, aucune modification dans `ai/OpexAI/`.

---

## 1. Comment OpexAI mesure ses opcodes (sondes, étiquettes et réglages)

Le budget d'opcodes dans OpenTTD NoAI n'est pas un stock mais un **débit par tick** (10 000 opcodes par tick dans OpenTTD 15.3, non reportables).
OpexAI dispose de plusieurs niveaux d'instrumentation passive :

| Sonde / Mécanisme | Réglage NoAI (`info.nut` / `settings.nut`) | Étiquette de journal exacte | Format et grandeurs relevées | Fichier source |
|---|---|---|---|---|
| **Chronométrage de bloc** | N/A (fonction helper universelle) | N/A (utilisé en mémoire) | `OpexOpsMeasureBegin()` / `OpexOpsMeasureEnd(mark)` : calcule `elapsedTicks * 10000 + delta_opcodes` | [`ai/OpexAI/budget.nut:19-31`](../ai/OpexAI/budget.nut#L19-L31) |
| **Comptabilité budgétaire** | `probes & 2 != 0` (panneaux `DEBUG_SIGNS`) | Panneaux `OC\|`, `OP\|`, `OS\|`, `OW\|`, `BT\|`, `BC\|` | Cumul par catégorie (`cat_*`, `cand_*`, `build_*`) dans `OpexBudget` ; `BC\|<cat>\|<ops>k\|...` | [`ai/OpexAI/budget.nut:33-97`](../ai/OpexAI/budget.nut#L33-L97), [`ai/OpexAI/task_report.nut:904-946`](../ai/OpexAI/task_report.nut#L904-L946) |
| **Trace hiérarchique de spans** | `probes & 4096 != 0` | `OPEX <date> SPAN` et `OPEX <date> SPAN_AGG` | `SPAN id=<id> par=<par> dep=<dep> n=<name> t0=<tick> tk=<ticks> op=<opcodes>`<br>`SPAN_AGG par=<id> n=<name> cnt=<n> op=<opcodes>` | [`ai/OpexAI/probes.nut:2631-2740`](../ai/OpexAI/probes.nut#L2631-L2740) |
| **Profil boucle principale** | `probes & 2048 != 0` (détourne vers `_mainLoopProfiled`) | `LOOP_OPS` | `LOOP_OPS y=<year> post=<name> n=<n> ops=<ops> tk=<ticks> max=<max>` | [`ai/OpexAI/probes.nut:2485-2588`](../ai/OpexAI/probes.nut#L2485-L2588) |
| **Phases de construction rail** | `probes & 256 != 0` (`DECISION_LOG`) | `RAIL_ATTEMPT` | `... iters=<iters> ops=<ops> search_ops=<sops> phases=<plans>/<search>/<stations>/<track>/<trains>` | [`ai/OpexAI/task_rail.nut:1171-1201`](../ai/OpexAI/task_rail.nut#L1171-L1201) |
| **Régénérations de catalogue** | `probes & 32768 != 0` | `C76_REGEN` | `OPEX <date> C76_REGEN phase=regen kind=<kind> reason=<reason> year=<y> ops=<ops>` | [`ai/OpexAI/probes.nut:2321-2327`](../ai/OpexAI/probes.nut#L2321-L2327), [`ai/OpexAI/task_report.nut:1342-1372`](../ai/OpexAI/task_report.nut#L1342-L1372) |
| **Coût détaillé catalogue** | `catalog_cost_probe=1` *(retiré en V239)* | `CATALOG_COST` | `OPEX <date> CATALOG_COST reason=<r> total_ops=<total> mode_regen_ops=... air_ops=...` | [`ai/OpexAI/probes.nut:767-815`](../ai/OpexAI/probes.nut#L767-L815) *(inactif au master)* |
| **Révisions moteurs rail V257** | `probes & 256 != 0` (`DECISION_LOG`) | `V257_OPS` | `OPEX <date> V257_OPS ops=<ops> cursor=<cur>` | [`ai/OpexAI/task_v257.nut:183`](../ai/OpexAI/task_v257.nut#L183) |

> [!NOTE]
> La compagnie `[0]` dans les journaux NoAI est toujours OpexAI ; la compagnie `[1]` est l'adversaire (AAAHogEx).

### Protocole et commande pour une campagne profilée

Pour mesurer ces postes sur une nouvelle campagne profilée sans modifier le code :
- **Réglage OpexAI :** `probes=39170` (panneaux 2 + `DECISION_LOG` 256 + boucle 2048 + spans 4096 + catalogue 32768). Les réglages individuels ont été retirés ; `probes=13` activerait notamment le bit 1 de **toutes** les sondes. Ce profil influe sur le rythme d'exécution : il sert au diagnostic, pas à une comparaison économique avec une partie non profilée.
- **Commande hôte (profil PC local 10 CPU / 10 workers) :**
  ```bash
  python3 sweeps/run_c66_reference.py --campaign pcal03_profil_3x3 \
    --reference "OpexAI[probes=39170]" --script-debug \
    --years 3 --seeds 42 7 100 --cpus 10 --memory 8g --max-workers 10
  ```
- **Extraction automatique des chiffres :**
  ```bash
  python3 sweeps/pcal03_inventaire.py results/pcal03_profil_3x3_engine
  ```

---

## 2. Tableau de synthèse par poste (PCAL-03)

Les chiffres ci-dessous proviennent de l'extraction sur les campagnes disponibles les plus récentes contenant les étiquettes correspondantes :
- **Profil SPAN 256² (1 an, 1970, graine 42)** : `results/v277v279_profil_42x1_20261020_engine/reference_seed42_r0.log` (étiquette `SPAN` / `SPAN_AGG`, compagnie `[0]`).
- **Profil SPAN 1024² (1 an, 1970, graine 42)** : `results/m1024_span_42x1_20261019_engine/reference_seed42_r0.log` (étiquette `SPAN` / `SPAN_AGG`, compagnie `[0]`).
- **Campagne rail phases (3 ans, 3 graines 42/7/100, rail seul, référence master)** : `results/v296c_mech_railseul_3x3_20261021_engine/reference_*.log` (étiquette `RAIL_ATTEMPT phases=`, compagnie `[0]`).
- **Audit des régénérations complètes (5 graines × 5 ans)** : `docs/reconstructions_completes_audit_20261012.md` (`results/regen_cost_5x5_20261012*`, étiquette `C76_REGEN`).
- **Profil C121 historique (5 graines × 6 ans duel, 256²)** : `docs/opcode_profile_c121_20261002.md`.

| Poste | Opcodes/an mesurés | Fréquence | Entrées dont dépend le résultat | Invalidation (ce qui détruit la validité) | Cache existant | Gain net plausible |
|---|---|---|---|---|---|---|
| **1. AIR plans, hubs & demande** | **13,95 M/an** (`air.plans`, 256²)<br>dont :<br>- `air.new_pairs` : 6,85 M/an<br>- `air.hub_site` : 2,69 M/an<br>- `air.sites` : 2,01 M (256²) → **9,65 M** (1024²)<br>- `air.prepare` : 0,80 M (256²) → 2,20 M (1024²)<br>- `air.hub_discover` : 0,47 M/an<br>- `OpexAirStationCatchmentProduction` : **non mesuré** isolément (inclus dans `air.c121.demand` 3,17 M/an) | 786 appels/an (256²)<br>354 appels/an (1024²)<br>~1 appel/jour de scan | Populations des villes, coordonnées des centres, relief/pentes locales, rayons de catchment, révisions des aéroports/avions (`AIEngine`), concurrents présents. | Croissance de ville (`revA != townA`), déblocage avion (`airportRev`), station rivale proche, expiration TTL 365j dans C121, obstacle bâti. | - `C121_CATALOG_CACHE` mémoïse choix d'avion, demande et économie par clé de plan.<br>- `AIR_SITE_CACHE` garde le meilleur site par ville.<br>- Mais la combinaison des paires et les scans de hubs sont **rejoués en boucle**. | **5 à 15 M ops/an**<br>(Surtout à 1024² via PCAL-02 précalcul sites top-K, et mémoïsation inter-scans des paires géométriquement sous le seuil). |
| **2. Régénérations, filtrage & sélection** | **~35 à 45 M/an** (sélection cumulée 256²)<br>dont :<br>- `select.reselect` : 12,04 M/an<br>- `catalog.rebuild` : 10,81 M/an<br>- `pub.filter` : 6,25 M/an<br>- `select.full` : 5,86 M/an<br>- `pub.select.score` : 5,66 M/an<br>- `pub.select.filter` : 4,55 M/an<br>- `projects.post_regen.incremental` : 2,46 M/an<br>- `_c76DoFullRegen("reactive")` : **5 à 12 M ops/événement** (concentré en 1972-1973) | Resélection : ~195/an (~1 tous les 2 jours).<br>Rebuild catalogue : ~300/an.<br>Rebuild réactif : 1 à 3/an en moyenne, pics à 12 M ops en un bloc. | Trésorerie disponible (`budgetNow`), liste des lignes et paires abandonnées, révisions de couches C76 (`towns`, `industries`, `lines`, `engines.*`). | Mouvement de caisse significatif (doublement +50 k£), construction de ligne, événement NoAI sur couche non filtrable par C80. | - `_projects` garde le vivier trié.<br>- V277 et V279 (filtre rapide et mémo de sélection) sont **inactifs à 256²** (défaut 0, actifs auto à 1024² seulement).<br>- `_c76DoFullRegen` **aucun cache**. | **10 à 25 M ops/an**<br>(Gisement n°1 absolu : PO-01 décomposition des rebuilds réactifs, PO-02 / V288 coalescence et non-recalcul des viviers stables). |
| **3. Constructibilité rail avant A\*** | **527 783 ops/an** (référence 3 graines × 3 ans)<br>(2,38 M sur graine 42 seule = 793 k/an)<br>Contexte rail :<br>- A* `search` : 18,42 M ops/an<br>- Pose `track` : 6,70 M ops/an<br>- Matériel `trains` : 0,63 M ops/an<br>- `railprep.after_pass` : 5,74 M ops/an | 6,9 tentatives/an en moyenne (20-21 tentatives sur 3 ans).<br>Moyenne de 76,6 k ops par tentative rail. | Coordonnées `src`/`dst`, longueur de quai, relief, pente, rayon de recherche (30 tuiles), orientation, gares existantes de la compagnie. | Construction rivale ou municipale sur l'emprise, nivellement, démolition. | **Aucun cache persistant** entre tentatives. Le balayage du carré est recalculé de zéro à chaque tentative.<br>V296c a tenté un ensemble natif, réfuté car ×10 plus cher que le scan paresseux. | **0,3 à 0,6 M ops/an** direct sur les sites de gares.<br>Gain indirect élevé si filtrage précoce évitant un A* coûteux (1,5 à 4 M ops) pour un site impossible. |
| **4. Route et flotte** | **Route : 0 op/an (consommateur inactif)**<br>`town_growth` : **0 op/an** (désactivé en V234)<br>`OpexRoadPlanFor` : **0 op/an** (0 ligne construite)<br>Flotte AIR : **5,59 M/an**<br>- `task.air_fleet` : 2,82 M/an<br>- `fleet.inject` : 2,14 M/an<br>- `fleet.resize` : 0,62 M/an<br>Flotte RAIL V257 : **0,42 M/an** | Flotte air : 204 appels/an (~tous les 2 jours).<br>Flotte rail V257 : 2 003 appels/an (fond).<br>Route : 0 appel. | Flotte : lignes actives, attente de cargo aux gares/aéroports, capacité des véhicules, notes de station, date. | Changement d'attente aux stations, mise en service/retrait d'un véhicule, expiration. | Déjà très fortement mis en cache et optimisé par V159/V160 (`air_fleet`), V252 (moteurs air), V257 (moteurs rail). | **< 1 M ops/an**<br>(Poste route sans consommateur métier ; poste flotte déjà optimisé, gains marginaux). |
| **5. Cartographie / eau C67** | **0 op/an (inactif au défaut)**<br>`catalog.refresh.water` : 340 ops/an (initialisation unique)<br>`loop.c67` : 0 op/an<br>`task.water` / BFS : 0 op/an | 0 appel en partie courante. | Raster de la carte (relief, eau, pente, composantes connexes). | Toute terraformation, construction de pont, écluse ou canal. | `terrain_map.nut` et `water_graph.nut` existent en modules autonomes mais sans consommateur métier au défaut. | **0 op/an (gain net négatif)**<br>Recensement V290 du 20/10 : **0 plate-forme pétrolière sur 40 graines**, 0 paire côtière maritime. Tout précalcul serait un gaspillage pur. |

---

## 3. Analyse détaillée par poste (lecture statique du code)

### Poste 1 : AIR plans, hubs et demande
- **Fonctions vérifiées :**
  - [`OpexAirPlans`](../ai/OpexAI/air_planning.nut#L1813) : coordination du scan du catalogue aérien (span `air.plans` [L1858](../ai/OpexAI/air_planning.nut#L1858)).
  - [`OpexAirPlansNewPairs`](../ai/OpexAI/air_planning.nut#L534) : génération des paires directes ville–ville (span `air.new_pairs` [L1708](../ai/OpexAI/air_planning.nut#L1708)).
  - [`OpexAirPlansHubToSite`](../ai/OpexAI/air_planning.nut#L1235) : paires étoile depuis un aéroport existant vers une ville (span `air.hub_site` [L1891](../ai/OpexAI/air_planning.nut#L1891)).
  - [`OpexAirPlansDiscoverHubs`](../ai/OpexAI/air_planning.nut#L1050) : identification des aéroports carrefours (span `air.hub_discover` [L1787](../ai/OpexAI/air_planning.nut#L1787)).
  - [`OpexAirPlansHubToHub`](../ai/OpexAI/air_planning.nut#L1393) : paires inter-hubs (span `air.hub_hub` [L1902](../ai/OpexAI/air_planning.nut#L1902)).
  - [`OpexAirPlansFindSites`](../ai/OpexAI/air_planning.nut#L297) : balayage des sites d'aéroports par ville (span `air.sites` [L1693](../ai/OpexAI/air_planning.nut#L1693)).
  - [`OpexAirStationCatchmentProduction`](../ai/OpexAI/air_coverage.nut#L212) : sommation tuile par tuile du cargo capté ([`opcode_exact.nut:541`](../ai/OpexAI/opcode_exact.nut#L541)).
  - [`OpexC121CatalogChoice`](../ai/OpexAI/air_catalog_c121.nut#L109) : évaluation économique C121 et sélection d'avion.
- **Entrées et dépendances :**
  Positions des villes, populations, constructibilité du terrain dans le rayon municipal, liste des avions disponibles, dates d'introduction, aéroports déjà construits.
- **Invalidation :**
  Variation de population d'une ville (révision de couche `town`), nouvel avion débloqué (`engines.air`), nouvel aéroport posé (`stationRev`), expiration TTL (365 jours dans C121).
- **Caches existants :**
  - `C121_CATALOG_CACHE` mémoïse l'évaluation du plan et le choix de l'avion ;
  - `AIR_SITE_CACHE` conserve le site trouvé par ville et type d'aéroport ;
  - `town_batch` précalcule la production par ville une fois par jour.
  - **Défaut du système actuel :** bien que les évaluations élémentaires soient mémoïsées, l'ordonnanceur relance le balayage complet des paires (`air.plans`) à chaque tick libre de tranche C78/V147. À 1024², la recherche de sites (`air.sites`) explose à **9,65 M ops/an** (27,2 k ops par appel contre 2,5 k à 256²).
- **Consommateur réel :**
  `task_projects.nut` (sélection du portefeuille) et `air_construction.nut`.

---

### Poste 2 : Régénérations, filtrage et sélection
- **Fonctions vérifiées :**
  - [`_c76DoFullRegen`](../ai/OpexAI/orchestrator.nut#L1228) : reconstruction complète réactive synchrone (déclenchée à [orchestrator.nut:612](../ai/OpexAI/orchestrator.nut#L612)).
  - [`_dispatchCatalog`](../ai/OpexAI/scheduler_tasks.nut#L313) : dispatch de catalogue en file (span `catalog.rebuild` [L459](../ai/OpexAI/scheduler_tasks.nut#L459)).
  - [`OpexReselectProjects`](../ai/OpexAI/projects_selection.nut#L1360) : re-sélection du vivier existant (span `select.reselect` [L1363](../ai/OpexAI/projects_selection.nut#L1363)).
  - Filtrage de sélection : span `pub.select.filter` ([projects_selection.nut:1383](../ai/OpexAI/projects_selection.nut#L1383)).
  - Filtrage de publication incrémentale : span `pub.filter` ([projects_update.nut:485](../ai/OpexAI/projects_update.nut#L485)).
  - Mise à jour incrémentale post-construction : [`OpexIncrementalUpdateProjects`](../ai/OpexAI/projects_update.nut#L469) (span `select.incremental` [L472](../ai/OpexAI/projects_update.nut#L472)).
- **Entrées et dépendances :**
  Trésorerie disponible, catalogue complet de tous les modes, lignes construites, révisions de couches C76.
- **Invalidation :**
  Changement de tranche de capital (seuil de financement), modification des lignes, révisions de couches NoAI non couvertes par C80 mode regen (`towns`, `lines`, `engines.air`), filet annuel `c76PeriodicDue`.
- **Caches existants :**
  - `_projects` conserve l'état trié.
  - V277 (publication sans reparcours complet du vivier) et V279 (mémoïsation du filtre de re-sélection) ont été créés pour ce poste, mais sont **désactivés par défaut à 256²** (`v277_air_pub_fast=3`, `v279_reselect_memo=3` actif auto à partir de 1024² seulement).
  - La reconstruction réactive complète `_c76DoFullRegen("reactive")` ne dispose d'aucun cache ni découpage : elle recalcule tous les modes de façon bloquante d'un seul bloc (5 à 12 M opcodes).
- **Consommateur réel :**
  `task_projects.nut` (cœur décisionnel d'OpexAI).

---

### Poste 3 : Constructibilité rail avant A*
- **Fonctions vérifiées :**
  - [`OpexRailPlatformPlans`](../ai/OpexAI/builder_rail.nut#L690) : sélection des plans de plateformes pour une paire rail candidate.
  - [`OpexStationPlans`](../ai/OpexAI/builder_rail.nut#L283) : recherche des emplacements de quais autour d'un centre (ville/industrie).
  - [`OpexJoinPlatformPlans`](../ai/OpexAI/builder_rail.nut#L386) : recherche de quai parallèle sur une gare existante de la compagnie.
  - [`OpexV131BuildTownClearance`](../ai/OpexAI/builder_rail.nut#L3486) et pipeline de réparation V131 ([`task_rail.nut:1719+`](../ai/OpexAI/task_rail.nut#L1719)).
  - Mesure des phases de pose : [`task_rail.nut:1171-1201`](../ai/OpexAI/task_rail.nut#L1171-L1201) (`phases=plans/search/stations/track/trains`).
- **Entrées et dépendances :**
  Extrémités `src`/`dst`, cargo, longueur de rame `platformLength`, pente du terrain, eau, rayon de recherche de gare (30 tuiles), orientation et dégagement d'approche.
- **Invalidation :**
  Toute modification des tuiles de la plateforme (bâtiment municipal, route, nivellement, voies posées par l'adversaire).
- **Caches existants :**
  - **Aucun cache persistant** entre tentatives successives.
  - Tentative V296c : précalcul d'un ensemble de tuiles plates et constructibles (`AITileList` natif) au lieu de boucles Squirrel. **Résultat : ÉCHEC** — le coût est passé de 48,7 k à 488,5 k opcodes par appel (×10), car la boucle Squirrel historique sort dès `limit` quais trouvés, alors que le précalcul parcourait l'ensemble du rectangle (cf. [ancien registre archivé](journaux/journal_2026-10-30_transfert_taches.md)).
- **Consommateur réel :**
  `task_rail.nut` (`_advanceRailSearchThroughput` et `_tryBuildRailProject`).

---

### Poste 4 : Route et flotte
- **Fonctions vérifiées :**
  - Sites routiers : [`OpexRoadSites`](../ai/OpexAI/builder_road.nut#L150), [`OpexRoadPlanFor`](../ai/OpexAI/builder_road.nut#L542), [`_tryBuildRoadProject`](../ai/OpexAI/task_road.nut#L3).
  - Tâche `town_growth` : [`main.nut:495`](../ai/OpexAI/main.nut#L495) (`enabled = false`, `dueCycle = 2147483647`).
  - Gestion flotte air : [`_resizeAirFleets`](../ai/OpexAI/task_air.nut#L716) (span `fleet.resize` [L718](../ai/OpexAI/task_air.nut#L718)), [`_c121InjectAirFleetPlans`](../ai/OpexAI/scheduler_tasks.nut#L104) (span `fleet.inject` [L106](../ai/OpexAI/scheduler_tasks.nut#L106)).
  - Révisions moteurs : V257 rail ([`task_v257.nut:142`](../ai/OpexAI/task_v257.nut#L142)), V252 air ([`task_v252.nut:28`](../ai/OpexAI/task_v252.nut#L28)).
- **Analyse du consommateur actif :**
  - **La route n'a aucun consommateur actif.** La tâche `town_growth` a été désactivée en V234 ; les projets routiers ne franchissent quasiment jamais le knapsack v2 face au rail et à l'air. Consommation réelle mesurée : **0 opcode/an**.
  - **La flotte est déjà fortement optimisée.** V159/V160 ont optimisé `air_fleet`, V252 et V257 ont découpé les révisions moteurs en micro-tâches de fond (quelques dizaines d'opcodes par passage).

---

### Poste 5 : Cartographie et eau C67
- **Fonctions vérifiées :**
  - [`_c67SlackHook`](../ai/OpexAI/main.nut#L869), [`OpexTerrainMap`](../ai/OpexAI/terrain_map.nut#L14), [`OpexWaterGraph`](../ai/OpexAI/water_graph.nut#L23), [`_dispatchTerrain`](../ai/OpexAI/task_terrain.nut#L42).
- **Analyse du consommateur actif :**
  - Tous les réglages C67 sont à **0 par défaut** (`c67_terrain_map=0`, `c67_water_exposure_probe=0`, `C67_SLACK_HOOK=false`).
  - Le recensement V290 du 20/10/2026 sur 40 graines × 3 ans a établi qu'il y a **zéro plate-forme pétrolière** et **zéro liaison maritime de vrac** sur les cartes de banc.
  - Consommation actuelle mesurée : **0 opcode/an** (hors 340 opcodes d'initialisation unique). Tout précalcul ici serait un gaspillage net de budget d'opcodes.

---

## 4. Classement argumenté des 3 postes les plus prometteurs

### 🥇 1er : Poste 2 — Régénérations, filtrage et sélection (Gisement : 10 à 25 M opcodes/an)
**Pourquoi c'est le n°1 :**
1. **Poids budgétaire dominant :** La sélection et les régénérations consomment plus de la moitié du budget global annuel de l'IA (~35 à 45 M opcodes sur 67,5 M).
2. **Inutilité des recalculs récurrents :** La re-sélection (`select.reselect` : 12,0 M ops/an) et la reconstruction de vivier (`catalog.rebuild` : 10,8 M ops/an) rejouent les mêmes tris et calculs économiques sur des viviers quasi identiques à plus de 95 %.
3. **Le fléau des reconstructions réactives synchrones :** `_c76DoFullRegen("reactive")` consomme 5 à 12 M opcodes en un seul bloc dès qu'un événement NoAI non filtrable par C80 arrive.
4. **Feuille de route déjà balisée :** Ce chantier correspond exactement à **PO-01** (découpage des reconstructions réactives), **PO-02** (expiration indépendante par mode) et **V288** (coalescence selon la fraîcheur). L'adoption de V277+V279 à 256² libérerait immédiatement ~11,8 M ops/an sans perte.

### 🥈 2e : Poste 1 — AIR plans, hubs et recherche de sites (Gisement : 5 à 15 M opcodes/an)
**Pourquoi c'est le n°2 :**
1. **Poids massif sur toutes les échelles de carte :** 13,95 M ops/an à 256² pour `air.plans`, avec une inflation dramatique de la recherche de sites (`air.sites`) à 1024² (**9,65 M ops/an** pour ce seul sous-poste).
2. **Précalculable et réutilisable :** Les emplacements d'aéroports dans une ville changent très peu tant que la ville ne bâtit pas sur les tuiles clés. Précalculer et mémoïser un top-K de sites par ville/époque (projet **PCAL-02**) pendant les temps morts évite de rescanner le rectangle urbain à chaque passage de catalogue.
3. **Élagage géométrique amont :** Les scans `air.new_pairs` (6,85 M ops/an) et `air.hub_site` (2,69 M ops/an) évaluent des centaines de combinaisons géométriquement ou économiquement non viables qui pourraient être éliminées par un index statique de distance/connectivité.

### 🥉 3e : Poste 3 — Constructibilité rail avant A* (Gisement : 0,5 à 2 M opcodes/an direct + filtre A*)
**Pourquoi c'est le n°3 :**
1. **Coût unitaire non négligeable :** La phase `plans` de `RAIL_ATTEMPT` consomme 527 k ops/an au défaut (jusqu'à 2,38 M ops sur graine 42), avec une moyenne de 76,6 k ops par tentative rail.
2. **Effet multiplicateur d'évitement :** Déterminer la constructibilité des quais *avant* de lancer la recherche A* permet d'échouer rapidement (`SITEA`/`SITEB` en < 10 k ops) plutôt que de dépenser 2,7 M opcodes dans un A* voué à l'abandon ou au rejet de quai.
3. **Mise en garde obligatoire (leçon V296c) :** Ne jamais tenter un précalcul exhaustif non borné (la version V296c en `AITileList` natif a multiplié le coût par 10 car l'implémentation Squirrel historique sort dès `limit` quais trouvés). Le précalcul doit être ciblé exclusivement sur le top 5 des projets finançables du portefeuille.

### Pourquoi les Postes 4 et 5 sont disqualifiés
- **Poste 4 (Route) :** Tâche `town_growth` désactivée (0 op/an) et 0 ligne routière financée en jeu normal. Flotte déjà optimisée. Gisement réel quasi nul.
- **Poste 5 (Cartographie / Eau C67) :** Aucun consommateur en partie courante (0 plate-forme pétrolière). Tout précalcul consommerait des opcodes pour un mode inerte.
