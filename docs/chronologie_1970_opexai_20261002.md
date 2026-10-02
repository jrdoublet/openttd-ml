# Chronologie de la première année d'OpexAI (1970), en micro-tâches

*2 octobre 2026. Diagnostic, pas un banc d'adoption.*

**Source.**
- Données : `results/chrono_1970_default_5x1_20261002.json` et son dossier `.artifacts/` (journaux `-d script=4` et points mensuels).
- Partie : duel contre AAAHogEx-115 sous OpenTTD 15.3, 5 graines (42, 100, 999, 1234, 5678), un an.
- Réglages : défaut courant (C115, `town_growth=0`, C121 inactif).
- Deux bras :
  - `reference` : défaut plus `probe_scheduler=1,catalog_cost_probe=1`, ce qui donne un journal daté tâche par tâche ;
  - `light` : défaut sans sonde, servant de témoin.
- Écart entre les deux bras : dans le bruit du duel (aéroports d'OpexAI au 1er décembre : 7,8 contre 8,6).
- Lanceur : `sweeps/diag_first_year_chrono.py`.
- Inventaire du code : rapport de grok du même jour, repris et corrigé au §4.

**Unités.** L'IA reçoit environ 18,5 ticks par jour de jeu, soit à peu près 6 750 ticks par an (environ 10 000 opcodes par tick). « j24 » désigne le 24e jour de 1970.

**Piège de lecture.** `P2_BUILD` est daté de la **fin** de la passe `projects`. Au second semestre, la pose a lieu au début de la passe, 17 à 27 jours plus tôt. Les dates de pose ci-dessous sont recalées sur le début de passe. Pour les comptes, seuls les points mensuels font foi : une construction faite par une intention réactive n'émet pas `P2_BUILD`.

## 1. Résumé

1. **Janvier-février : OpexAI part plus tôt qu'AAAHogEx, mais n'engage pas son argent.**
   - Première ligne posée entre j15 et j43 (médiane j24).
   - AAA n'a encore aucun aéroport au 1er février.
   - La première passe ne pose qu'une ou deux lignes (`K_pass` = 0, puis un seul contournement C75), puis laisse 110 à 212 k£ en caisse pendant trois à cinq semaines.
   - Au 1er février, AAA a déjà engagé 380 k£ (caisse 19 k£), alors qu'OpexAI garde 187 k£.
2. **Mars-juin : les deux IA sont à sec et font jeu égal.**
   - Au 1er mai, chacune a 6,0 aéroports.
   - OpexAI enchaîne des passes `projects` vides (capital disponible 7 à 17 k£) et ajoute des avions aux lignes existantes.
3. **Juillet-décembre : l'écart se creuse alors qu'OpexAI a de l'argent.**
   - AAA passe de 6,2 à 14,6 aéroports en dépensant tout ce qui rentre (caisse autour de 30 k£).
   - OpexAI passe de 6,0 à 7,8 aéroports et accumule 36 puis 150 k£.
   - Cause mesurée : une décision de construction toutes les cinq à six semaines, une ou deux lignes par décision, et chaque pose suivie d'un recalcul aérien synchrone de 16 à 27 jours.
4. **Ce qui ne relève pas de l'aérien passagers pèse peu en 1970.**
   - Environ 10 % du temps d'IA, au plus : industries, candidats rail et eau, part non aérienne de la sélection.
   - Une ou deux lignes routières de 15 à 25 k£, dans trois graines sur cinq.
   - Aucun rail posé et aucun A* rail lancé, dans aucune graine.
   - Supprimer tout cela rendrait au plus un mois de temps d'IA par an.
5. **Le temps part dans la machinerie aérienne elle-même.**
   - Planificateur `OpexAirPlans` : environ 46 % du temps d'IA, soit environ 165 jours de jeu.
   - Sélection et resélection du portefeuille : environ 25 % (environ 93 jours). Cela inclut la tâche `air_fleet`, qui n'achète rien en 1970 mais resélectionne tout le portefeuille à chaque tour de file.

## 2. Tableau mensuel

Bras `light`, moyenne des 5 graines, relevé le 1er du mois. Caisse = argent en banque, emprunt compris. Les deux IA sont à l'emprunt maximal (300 k£) toute l'année.

| 1er du mois | Opex aéroports | Opex avions | Opex caisse | AAA aéroports | AAA avions | AAA caisse |
|---|---|---|---|---|---|---|
| janv. | 0 | 0 | 100 k | 0 | 0 | 100 k |
| févr. | 2,8 | 1,4 | **187 k** | 0 | 0 | 19 k |
| mars | 5,2 | 2,6 | 88 k | 4,6 | 3,8 | 26 k |
| avr. | 5,8 | 3,0 | 53 k | 5,4 | 4,0 | 31 k |
| mai | 6,0 | 3,2 | 35 k | 6,0 | 4,0 | 38 k |
| juin | 6,0 | 3,8 | 30 k | 6,2 | 5,8 | 27 k |
| juil. | 6,0 | 4,6 | 36 k | 7,2 | 6,4 | 29 k |
| août | 6,0 | 5,8 | 62 k | 8,0 | 7,4 | 34 k |
| sept. | 6,4 | 6,8 | 65 k | 9,4 | 8,8 | 36 k |
| oct. | 7,0 | 7,8 | 89 k | 11,4 | 10,4 | 36 k |
| nov. | 7,4 | 8,8 | 110 k | 12,6 | 12,2 | 29 k |
| déc. | 7,8 | 9,6 | **150 k** | 14,6 | 13,8 | 44 k |
| janv. 71 | 8,8 | 11,2 | 130 k | 15,4 | 15,4 | 53 k |

AAA met environ un avion par aéroport dès l'ouverture. OpexAI pose un avion par ligne de deux aéroports, puis renforce plus tard.

## 3. Chronologie, phase par phase

### Phase 0 : `Start()`, j0

Aucun travail sur la carte. Les étapes, dans l'ordre :
1. lecture des réglages ;
2. amorçage par étapes laissé à l'étape 0 ;
3. initialisation C69/C75 ;
4. vidage du cache de sites aériens ;
5. renouvellement automatique ;
6. emprunt maximal ;
7. auto-tests C80 et C76 (`main.nut:610-700`).

Aucun catalogue, aucun A* et aucun parcours des villes n'ont lieu ici.

### Phase 1 : premier `catalog`, de j0 à j13-35

Un seul appel synchrone : aucune autre tâche ne tourne tant qu'il n'est pas revenu.

| Micro-tâche | Coût mesuré (5 graines) | Mode |
|---|---|---|
| Rafraîchissement global : 42 à 46 villes, 47 à 54 industries, moteurs | 0,27 M opcodes, environ 1,5 j | partagé |
| `OpexAirPlans`, étape 0 (`prepare`, `sites`, `new_pairs`, hubs vides) | 163 à 508 ticks, **9 à 28 j** | aérien passagers |
| Candidats de fret rail pour un cargo (étape 0) | 0,01 à 0,04 M opcodes, moins de 0,2 j | rail |
| Sélection : `OpexProjectSelectAffordable` sur 187 à 321 alternatives | 0,4 à 1,0 M opcodes, 2 à 5 j | tous modes |

- Fin du premier catalogue : j13, j22, j22, j30, j35.
- Graine 5678 : une offre de subvention (intention réactive `c77_subsidy`) ajoute 6 jours.
- Avant le premier `projects`, la file passe encore par `report` (bilan annuel, une seule fois), `scrap`, `air` (qui se désactive) et `air_fleet` (rien à faire).

### Phase 2 : première passe `projects`, pose entre j15 et j43

- Pose d'une ou deux lignes aériennes en un à deux jours.
- Au premier passage, `K_pass` vaut 0 (`probes.nut` vers 1940). Après la première pose, seul le contournement `c75_kpass_bypass` laisse passer une seconde ligne neuve. La suivante arrête la passe (`task_projects.nut:1721-1779`).
- Lignes posées : 1, 2, 2, 1 et 2 (graines 100, 1234, 42, 5678, 999).
- Capital disponible restant : 212, 110, 139, 173 et 140 k£.
- Graine 5678 : la seconde ligne autorisée n'aboutit pas (cause non lue). La passe suivante, le 17 mars, examine 64 projets avec 172 k£ et ne pose rien (`projects_examined_no_effect`).
- La même tâche lance ensuite la régénération `staged_full` de l'étape suivante de l'amorçage (rail passagers), soit un à trois jours.

### Phase 3 : février-mars, amorçage et deuxième vague

- Deuxième `catalog` complet (changement de mois), 11 à 15 j. C'est l'étape rail passagers : 100 à 140 candidats rail pour 0,3 à 0,4 M opcodes.
- Deuxième pose : j29, j47 et j49 (graines 100, 42, 1234) ; seulement vers j99 et j122 pour 5678 et 999. Une ligne à chaque fois, arrêt `cash`.
- Troisième `catalog` complet (entre fin février et mi-mai), jusqu'à 35 j.
  - Il contient un `OpexAirPlans` complet de 20 à 27 j (3,7 à 5,1 M opcodes).
  - Il ajoute les candidats route et eau (étape 3).
  - L'amorçage atteint ensuite l'étape 4 (`COMPLETE`).

### Phase 4 : avril-juillet, à sec

- Capital disponible de 7 à 17 k£, aucun projet finançable (`in_best=0`).
- Passes `projects` vides (`empty_pool`) tous les deux jours environ. Chacune est précédée d'une resélection `air_fleet` de 27 ticks (1,5 j).
- Les dépenses partent en avions ajoutés aux lignes existantes (projets `fleet`).
- Dans les graines 42, 999 et 1234, une ou deux lignes routières (15 à 25 k£) sont posées quand aucun aérien n'est finançable (`cause=all_unaffordable`).
- À l'étape 4, le catalogue mensuel n'est plus qu'une resélection : 0,45 à 1,1 M opcodes, 2 à 6 j.

### Phase 5 : août-décembre, cycle de décision lent

Cycle observé dans la graine 42 (les autres graines sont à ± 5 j près) :

| Étape du cycle | Durée |
|---|---|
| `catalog` : resélection mensuelle, ou une fois un recalcul complet sur déclencheur `capital` (28 j) | 3 à 6 j |
| `air_fleet` : aucun achat, mais resélection du portefeuille (0,8 à 0,9 M opcodes) | 2 à 5 j |
| `projects` : pose d'une ou deux lignes | 1 à 2 j |
| … puis, dans la même tâche, recalcul complet de `OpexAirPlans` (régénération `incremental`) | **16 à 27 j** |
| … puis sélection incrémentale | 2 à 4 j |
| `expand`, `refleet`, `repay`, `report`, `scrap` | moins de 1 j |

**Bilan : une décision de construction tous les 35 à 45 jours, deux lignes au plus.**

Arrêts des passes qui ont posé quelque chose au second semestre (5 graines) :
- 12 `cash` : le projet suivant dépasse le capital disponible, réserve déduite ;
- 11 `k_pass` ;
- 2 fins de liste.

Le capital disponible après passe va de 14 à 250 k£ (médiane environ 110 k£).

## 4. Où va le temps d'IA en 1970

Moyenne par graine, bras `reference`. Ventilation tirée des sondes `AIR_LIGHT` (entrée et sortie de `OpexAirPlans`), `SELECTION_LIGHT`, `CATALOG_COST` et `PROJECTS_COST`. Les postes peuvent se recouvrir de quelques pour cent.

| Poste | Ticks par an | Part | Jours de jeu | Mode |
|---|---|---|---|---|
| `OpexAirPlans`, tous contextes : catalogue, régénération après pose, réactif | ~3 085 | ~46 % | ~165 | aérien passagers |
| Sélection et resélection du portefeuille (31 à 121 appels) | ~1 715 | ~25 % | ~93 | tous modes : environ 340 alternatives, dont 50 à 140 rail |
| Pose (2,1 à 4,9 M opcodes) | ~320 | ~5 % | ~17 | aérien surtout, route |
| Rafraîchissement global du catalogue (10 à 14 fois) | ~280 | ~4 % | ~15 | partagé : villes utiles à l'aérien, industries inutiles |
| Candidats rail : fret à l'étape 0, passagers aux étapes 1-2, recalculs `capital` | ~110 | ~1,6 % | ~6 | rail |
| Plans eau et assemblage | ~60 | ~1 % | ~3 | eau, tous modes |
| Autres tâches de la file | ~100 | ~1,5 % | ~5 | entretien, finance |
| Hors file : événements, `Sleep(1)`, orchestrateur, C77 | ~1 100 | ~16 % | — | — |

Part non aérienne, estimée à environ 10 % au plus :
- candidats rail et eau : 2,6 % ;
- moitié industries du rafraîchissement : environ 2 % ;
- part rail et route de la sélection : environ 30 % des alternatives, soit environ 7 % du temps. Ce dernier chiffre est une estimation proportionnelle, non mesurée.

## 5. Inventaire des micro-tâches et de ce qui les coupe

Classement selon la demande : supprimer ou décaler ce qui ne sert pas l'aérien passagers.

### A. Sans rapport avec l'aérien passagers : candidats à la suppression ou au report

| Micro-tâche | Fichier:ligne | Coût 1970 mesuré | Réglage existant au défaut C115 | Si on la coupe en 1970 |
|---|---|---|---|---|
| Candidats fret rail, étape 0 | `projects.nut:130`, `candidates.nut:1459` | < 0,5 % | **aucun** (voir note) | Plus de paire de fret rail dans le premier vivier |
| Candidats rail passagers, étapes 1-2 et complète | `projects.nut:131`, `candidates.nut:1450` | ~1 % | **aucun** | Plus de paire rail ; le planificateur ne lance pas d'A* en 1970 de toute façon |
| Étapes 1 à 3 de l'amorçage (`AIR_RAIL`, `RAIL_ONLY`, `ROUTE_ONLY`) | `projects.nut:129-134`, `task_projects.nut:2061-2063` | régénérations `staged_full`, 1 à 3 j chacune | `policy_portfolio=0` génère tout d'un coup, ce qui est l'inverse du but | Elles n'existent que pour étager les modes non aériens |
| Catalogue route, candidats route fret, pose route, `refleet` route | `catalog.nut:1100`, `projects.nut:292`, `task_road.nut:3,306` | ~0 % du temps, mais 1 à 2 lignes à 15-25 k£ dans 3 graines sur 5 | `policy_road=0` (`ROAD_BUILD_ENABLED=false`) coupe proprement, mais pour **toute** la partie | Plus de camions ; l'argent reste pour l'aérien suivant |
| Plans eau, catalogue des navires | `projects.nut:134`, `builder_water.nut:330`, `catalog.nut:767` | ~0,5 % | aucun | Plus de navires |
| Industries et acceptation urbaine hors passagers dans le rafraîchissement | `catalog.nut:908-916`, `985-1022` | ~2 % | aucun | Fret aveugle |
| Réactif industrie (`regen`, `c77_entity`) et subvention non passagers (`c77_subsidy`, `c77_build`) | `orchestrator.nut:1099`, `event_handlers.nut:342` | 6 j dans la graine 5678, sinon rare | aucun : le socle C80 est forcé | Les offres de fret n'entrent plus dans le vivier |
| `expand`, A* rail, tranches V89 | `task_rail.nut:586`, `scheduler.nut:423` | ~0,2 % (inerte : aucune ligne rail) | `rail_expand=0` déjà | Rien en 1970 |

**Note.** `policy_rail=0` ne coupe **pas** la génération des candidats rail. Il éteint seulement `RAIL_DEVIS`, l'A* reprenable, la micro-échéance, la recherche segmentée, `RAIL_REFLEET`, le plafond dynamique du pathfinder, `PAX_FULL_LOAD` et `ORIGIN_SITABLE` (`settings.nut:32-40`). Les modes générés ne dépendent que de l'étape d'amorçage (`projects.nut:130-134`). Le rapport de grok disait le contraire : c'est faux.

**Seul interrupteur « aérien seul la première année » existant.** `c121_catalog_air_first_year` (`projects.nut:135-141`, `scheduler_tasks.nut:190`). Il exige `c121_catalog_incremental`, qui exige `c121_air_economics` (`settings.nut:306-309`), donc **il est inutilisable sous C115**.

### B. Partagé, à garder

- Rafraîchissement des villes et des moteurs aériens.
- Emprunt et `repay` (plancher `loan_repay_floor_k=300`).
- `scrap`.
- Événements : ville fondée, moteur disponible.
- `report`.
- Renouvellement automatique.

### C. Aérien passagers : là où le temps passe réellement

| Micro-tâche | Fichier:ligne | Coût 1970 mesuré | Remarque |
|---|---|---|---|
| `OpexAirPlans` après chaque pose, dans la même tâche `projects` (étape < 4 : `staged_full` ; ensuite : `incremental`, qui refait quand même tout le plan) | `task_projects.nut:2061-2077` | 16 à 27 j par pose, 5 à 7 fois par an | Bloque toute décision suivante |
| `OpexAirPlans` dans le `catalog` mensuel complet ou sur déclencheur `capital` | `scheduler_tasks.nut:305-345` | 9 à 28 j, 3 à 4 fois par an | Premier appel en janvier : il fixe la date de la première ligne |
| Resélection du portefeuille à chaque `air_fleet` sans travail et à chaque `catalog` mensuel | `scheduler_tasks.nut:828-854` | 1,5 à 5 j par appel, ~25 % du temps | Sous `FLEET_PORTFOLIO`, `air_fleet` n'achète rien |
| Arrêt de passe `K_pass` + un seul contournement C75 | `task_projects.nut:1721-1779` | 1 à 2 lignes par passe ; 110 à 212 k£ immobiles en janvier-février, médiane environ 110 k£ au second semestre | `c121FirstYearAirBatch` lève cet arrêt pour l'aérien, mais seulement sous C121 |

Chemin jusqu'à la commande de construction :
1. `_runOrchestratorTick` ;
2. `_runNextTask` ;
3. `_dispatchProjects` ;
4. `_tryBuildProjects` ;
5. `OpexPromoteLiveDefensiveAir` ;
6. `_tryBuildAirProject` (`task_air.nut:305`) ;
7. `OpexBuildAirRoute` (`air_construction.nut:195`) ;
8. `AIAirport.BuildAirport` ;
9. `AIVehicle.BuildVehicleWithRefit` ;
10. `OpexAirBuildJoinedStops`.

## 6. Antécédent à connaître avant de couper

L'essai le plus proche a déjà été mesuré sous C121 (`docs/catalogue_decoupe_phase2_20260929.md`, VPS, 29-30/09).

Il combinait trois mécanismes :
- aérien seul la première année (`c121_catalog_air_first_year=1`) ;
- chaînage aérien au-delà de `K_pass` ;
- replanification différée, c'est-à-dire sans `OpexAirPlans` synchrone après chaque pose.

Résultats :
- 11, 11 et 12 aéroports ouverts en 1970 contre 10, 7 et 7 au défaut C115 (solo, 3 graines) ;
- 56 k£ de caisse fin 1970 au lieu de 254 k£ (graine 42).

En duel 5×3, C121 a ensuite décroché en 1972 pour une raison de flotte, sans rapport avec ces trois mécanismes.

Le 30/09, l'utilisateur a refusé de greffer ces accélérations C121 (cache catalogue, replanification différée) sur la référence C115. Le plus gros poste mesuré ici, le recalcul aérien après chaque pose, est précisément la replanification différée.
