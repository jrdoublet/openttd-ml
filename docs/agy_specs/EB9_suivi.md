# EB-9 suivi — `air_site_ranked` en multimodal

**Date :** 12 novembre 2026. **Arbre :** `grok12-nov12`, HEAD de lecture `aa6ad5f9` (base de la mesure opcodes `6e11bc31`). Lecture du code et des archives. Aucun Docker, aucun banc, aucune modification du classement ni du stop.

Le cas multimodal n'a pas de qualification causale propre. Cette note décrit où le classement s'exécute sur l'énumération initiale et sur un vrai `ET_TOWN_FOUNDED`. Elle ne réactive pas de scan cyclique après saturation.

## Défaut lu dans le source

`air_site_ranked` vaut 1 aux quatre difficultés (`info.nut:1178-1184`). `OpexLoadSettings` (`settings.nut:675-678`) charge `air_site_ranked.nut` et appelle `OpexAirRankedInstall` : `OpexAirFindSiteCatchmentListed` devient `OpexAirRankedListed` (`air_site_ranked.nut:455-461`). L'install est global. Il n'y a pas de branche « air seul » ni de branche « multimodal ».

`air_coverage_stop` vaut 0 (`settings.nut:76`, globale `AIR_COVERAGE_STOP` dans `globals_pre.nut:295`). Au défaut, `OpexAirPlans` ne prend pas le retour anticipé de `air_planning.nut:2006`. Les passages planifiés par `scheduler_tasks.nut:316` continuent avec `targetTownId = -1`.

## Énumération initiale

Les premiers plans passent par `OpexAirPlans` sans ville cible :

- construction du portefeuille, `projects.nut:351` (`airBand`) et, si le vivier pax air est vide, `projects.nut:380` (`PAX_BAND_AIR_RAIL`) ;
- tranche C78, `scheduler_tasks.nut:316`, quatrième argument de ville égal à `-1`.

`OpexAirPlansPrepare` (`air_planning.nut:424-428`) ne réordonne la liste que si `targetTownId >= 0`. À −1, l'ordre reste le tri de population, puis le rang sale C121 si l'appel est découpé. `OpexAirPlansFindSites` (`air_planning.nut:553`) parcourt le bassin jusqu'à `limit` et appelle `OpexAirFindSite` (ligne 581). Avec le défaut, cet appel est `OpexAirRankedListed` : deux bandes `[4, 14]` puis `[15, AIR_SITE_RADIUS]`, au plus 12 tests de construction natifs, puis la spirale de repli (`air_site_ranked.nut:401-440`).

En multimodal le même appel est utilisé dès que `doAir` est vrai (`projects.nut:339`). Le classement de l'énumération initiale est donc celui qualifié en air seul, appliqué tel quel aux parties qui ont aussi le rail et la route.

## Vrai `ET_TOWN_FOUNDED`

`OpexAI::_onTownFounded` (`event_handlers.nut:414`) fait deux choses distinctes.

1. `_markDirty("town_founded", …, "town", townId)` (`events.nut:40`). Si la cible est pertinente, `events.nut:140-142` enfile C77 avec `entityKind = "town"` et l'identifiant de la ville, raison `town_founded`. Le worker air (`orchestrator.nut:493-496`) appelle `OpexRegenerateAirProjectsSlice`, qui passe cet identifiant à `OpexAirPlans` (`projects_generation.nut:204-206`).
2. Si `AIR_COVERAGE_STOP` est vrai, la ville est aussi poussée dans `AIR_NEW_TOWN_QUEUE` et `AIR_COVERAGE_EXHAUSTED` repasse à faux (`event_handlers.nut:420-422`). Au défaut 0, cette file n'est pas touchée.

Sur la tranche C77, le classement s'applique ainsi :

- `OpexAirPlansPrepare` met la ville fondée en tête, puis recolle le reste du bassin (`air_planning.nut:424-428`). La recherche de sites continue sur `scanEnd` villes (`air_planning.nut:553`), chacune par `OpexAirRankedListed`.
- Les paires neuves se restreignent si le site de la ville cible est à l'index 0 : `pairOuterLimit = 1` (`air_planning.nut:761-763`). Le commentaire des lignes 746-751 dit que l'ensemble réinjecté reste celui des projets qui touchent la ville. Si le site cible n'est pas en tête, le parcours redevient complet et le filtre `air_planning.nut:820` écarte les paires qui ne touchent pas la ville.
- Les hubs ont le même filtre de ville (`air_planning.nut:1415` et `1563`).

La file `AIR_NEW_TOWN_QUEUE` ne devient pas `targetTownId`. Elle est lue seulement comme compteur : à la fin d'un scan complet, `OpexAirPlansFinalize` (`air_planning.nut:1791-1797`) la vide, ou bien arme `AIR_COVERAGE_EXHAUSTED` quand elle est vide et qu'aucun site n'a été trouvé. Un scan découpé qui rend la main avant `OpexAirPlansFinalize` ne prend pas cette décision. Au défaut, ce bloc ne s'exécute pas.

Conséquence pour un `ET_TOWN_FOUNDED` réel, au défaut multimodal : le classement natif tourne sur la ville nouvelle et sur les autres villes encore parcourues par la tranche C77. Le scan cyclique `targetTownId = -1` du scheduler n'est pas coupé. Comparer des rangs en rallumant ces scans après saturation n'est pas nécessaire pour décrire le chemin : il est déjà le chemin par défaut, et les archives ci-dessous l'ont déjà instrumenté avec `air_site_ranked=1`.

## Archives et exposition

Qualification causale, air seul, défaut ensuite passé à 1 (`docs/journaux/journal_2026-10-30_transfert_taches.md`, entrées du 27 et 28 octobre) :

| Porte | Campagne | Résultat Opex variante − référence |
|---|---|---|
| A 40×3 | `air_site_ranked_v3_gateA_40x3_20261027_night` | +156,5 k£/an, médiane +233,5 k, 25/15, Wilcoxon p = 0,0498, IC95 [+0,9 k ; +308,5 k], valeur +9,1 % |
| B 20×10 | `air_site_ranked_v3_gateB_20x10_20261027_night` | +65,9 k£/an, médiane +146,5 k, 13/7, IC95 [−151,0 k ; +258,3 k], valeur +8,2 % |

Sonde solo corrigée citée par le même journal : score admissible 0,99 de l'oracle (spirale 0,61), opcodes −1,9 % face à la spirale. Le premier smoke négatif venait de `LevelTiles` en `AITestMode`, qui réussit dès qu'un coin bouge ; le contrôle retenu est coin par coin plus tuiles voisines (`OpexAirRankedCanLevelFootprint`, installé avec le classement).

Multimodal : le même journal note un smoke graine 42 à **−183 k£/an**. Une graine ne tranche pas. Le 40×5 du 27 octobre (`docs/analyse_estim_sites_40x5_20261027.md`) joue les trois modes avec `air_site_ranked=1` et `air_site_funnel=1` déjà actifs, sondes `probes=67247874`, bundle `8d40648d…`, Git `57d5cde9` sale. Ce n'est pas un duel classement contre spirale. Profit terminal multimodal : Opex 2 738 911 £/an contre AAA 2 926 249 £/an (93,6 %, signes p = 0,154). Ouvertures AIR cumulées sur 40 parties : 340, 825, 246, 54, 33 de 1970 à 1974. La recherche de sites coûte 0,44 G d'opcodes exclusifs sur ces 40 parties. Rien dans ce dossier n'isole l'effet du classement une fois le rail et la route présents.

`ET_TOWN_FOUNDED` n'a pas de campagne dédiée dans ces archives. Le chemin est celui du code ci-dessus, présent au défaut, pas un protocole encore mesuré.

## Spécification — pas de modification

`AIR-COVERAGE-STOP` est un réglage à 0. Il n'isole pas encore la ville fondée : la file réveille un scan, et `targetTownId` vient de C77, pas de la file. Tant que ces deux mécanismes ne sont pas le même objet, changer `OpexAirPlansFindSites` ou le classement pour « ne scorer que la ville nouvelle » retire des sites partenaires dont la boucle de paires a besoin (`air_planning.nut:766`).

Spécification laissée pour un chantier ultérieur, après isolation du stop, défaut inchangé d'ici là :

- garder `OpexAirRankedListed` sur l'énumération initiale (`targetTownId = -1`) et sur la tranche C77 dont `reason = town_founded` ;
- ne pas ajouter de passe de classement déclenchée par le calendrier, la caisse ou un TTL une fois le bassin marqué épuisé ;
- ne mesurer un écart multimodal qu'en duel apparié `air_site_ranked=0` contre `=1`, mêmes autres défauts, hors de cette note.

Aucun symbole Squirrel n'est modifié par ce suivi.
