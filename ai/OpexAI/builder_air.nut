/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * Apres echec : avions vendus avant retrait des aeroports neufs ; si une commande
 * echoue ou qu'un avion est parti, le nettoyage se poursuit de facon persistante.
 */

require("air_recovery.nut");

AIR_HUB_NEW_SITE_POOL <- 12;
AIR_SITE_RADIUS <- 25;
AIR_TOWN_MIN_DISTANCE <- 32;
AIR_MAX_SITE_PROBES <- 1500;
/* C78.4 : une tranche AIR grande carte peut traverser plusieurs suspensions
 * automatiques NoAI, mais reste bornee a environ un jour de jeu. Les mesures
 * C39/C76 utilisent ~186k opcodes/jour ; 180k garde une petite marge. */
AIR_PLAN_SLICE_OPS <- 180000;
AIR_MAX_PLANES_PER_ROUTE <- 16;
AIR_PLAN_DIAG_SEQ <- 0;
/* Plafond de distance aerienne (0 = illimite, docs/taches.md C6 supprime) */
AIR_MAX_DISTANCE <- 0;
/* Ordre de chargement passagers aerien (0 = aucun, 1 = deux extremites, 2 = premiere extremite seulement, comme AAAHogEx) */
AIR_FULL_LOAD <- 0;
/* Cache de sites d'aeroport par ville et type d'aeroport (C33.1) */
AIR_SITE_CACHE_ENABLED <- true;
AIR_SITE_CACHE <- {};
/* C118/C120 : cache exact de la liste des villes presentes dans le catchment
 * d'une emprise neuve. Contrairement au cache historique attache a l'objet
 * `site`, cette cle survit aux objets site recrees pour chaque combo moteur ET
 * aux regenerations suivantes. C'est coherent avec AIR_SITE_CACHE : tant que
 * ville/type pointe vers la meme ancre, rescanner son rectangle a chaque build
 * ne change pas la geometrie mais peut suspendre l'IA pendant des semaines.
 * Le cache est invalide avec le cache de site ; un site reel construit passe
 * ensuite par AITileList_StationCoverage, donc n'utilise plus cette prediction. */
AIR_TERRITORIAL_COVERAGE_CACHE <- {};
AIR_TERRITORIAL_COVERAGE_HITS <- 0;
AIR_TERRITORIAL_COVERAGE_MISSES <- 0;
/* Cache court pour les hubs existants : exact pendant une generation AIR,
 * invalide avant la generation suivante car une construction jointe peut
 * agrandir le catchment de station. */
AIR_STATION_COVERAGE_TOWN_CACHE <- {};
AIR_STATION_COVERAGE_HITS <- 0;
AIR_STATION_COVERAGE_MISSES <- 0;
/* C121 : topologie exacte station -> catchment. Elle est independante du cargo
 * et de la ville : la construire une seule fois par station permet aux quatre
 * evaluations endpoint x PASS/MAIL de reutiliser exactement le meme ensemble
 * AITileList_StationCoverage. Les ratings ne sont volontairement pas caches. */
AIR_C121_STATION_COVERAGE_CACHE <- {};
/* C36.3 : Filtre d'emprise sans AITestMode avant la sonde (defaut 1, banc 20x10). */
AIR_CHEAP_SITE <- true;
/* C33.2 : Arrets de bus joints au chantier aeroport */
AIR_JOINED_STOPS <- false;

require("air_coverage.nut");

require("air_towns.nut");

require("air_trip.nut");

require("air_sites.nut");
require("air_c83_repair.nut");

require("air_economics_c121.nut");

require("air_catalog_c121.nut");

require("air_route_economics.nut");

require("air_fleet.nut");

require("air_engine_choice.nut");

require("air_planning.nut");

require("air_construction.nut");

require("air_town_demand.nut");
