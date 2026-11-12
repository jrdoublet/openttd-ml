# Revue — mesure OPCODES / AIList du 12 novembre 2026

Revue de la lecture qui produit [OPCODES_AILIST_mesure.md](OPCODES_AILIST_mesure.md). Aucun diff Squirrel. HEAD lu : `6e11bc31`, branche `grok12-nov12`.

## Sites relus

| Site | Constat |
|---|---|
| `air_coverage.nut:413-447` | L1 courant : `AIStationList` puis `HasCargoRating` par identifiant. Pas de `Valuate` sur ce filtre. |
| `candidates.nut:1226-1234` | L2 courant : boucle d'indices et `GetCargoAcceptance`. Pas de `AITileList`. |
| `projects_selection.nut:1141-1144` | `select.full` est le plus gros poste consommé du tableau multimodal du 27/10. |
| `probes.nut:3003-3028` | `stable_unfunded` est séparé de `useless`. Le commentaire 3020-3022 interdit de traiter un snapshot non financé comme une boucle inutile au sens de la sonde. |
| `air_planning.nut:511`, `:581`, `:2006` | La recherche de sites tourne au défaut. Le sommeil du bassin est derrière `AIR_COVERAGE_STOP`. |
| `settings.nut:675-678` | `air_site_ranked=1` remplace `OpexAirFindSiteCatchmentListed` au chargement. |
| `task_air.nut:515-600` | `fleet.resize` refuse la cadence avant le plafond et le marginal. `OpexC121RefreshVisibleFleet` est absent du dépôt. |
| `main.nut:478` | `town_growth` est dans la file avec `enabled = false`. |
| `probes.nut:2317` | Le registre C75 bypass a déjà son réglage à 0. Son coût VM n'est pas dans les journaux. |

## Décision

Pas de correctif. L1 et L2 natifs sont des régressions mesurées (+144 et +606 opcodes sur les appels exposés). Les trois gisements hors rail sont soit décisionnels (resélection, flotte), soit déjà derrière `air_coverage_stop` à défaut 0 (sites AIR). Ajouter un `AddSetting` pour rejouer `Valuate` contredirait la mesure. Le plafond `test_v251_inventory.py` (68 réglages après projection) n'a pas à bouger.

## Hors périmètre respecté

Rail non modifié. Défauts non modifiés. `idle1_slack_worker=1` laissé en place : il écrit des populations et n'est pas un levier d'opcodes pur. Variantes vides, benchmarks historiques et pistes exclues du lot (V260, V300, flotte bus, courrier point à point, et la liste du prompt) non rouvertes.

## Limite

Les JSON de sonde du 23 octobre ne sont pas dans `results/`. Les comptes L1/L2 viennent du journal, pas d'un recalcul moteur. Les milliards du 27/10 sont des sommes de spans exclusifs sous sondes ; ils décrivent un ordre de grandeur de poste, pas une part inutile isolée, sauf pour le smoke V309 du 25 octobre (35,43 M dont 0,591 M financés).
