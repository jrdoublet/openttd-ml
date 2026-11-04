# Mission cloud n°3 : `road1y_aaa_fleet` — porter la gestion de flotte bus d'AAAHogEx d'un seul bloc (route seule, 3 ans)

Dépôt `jrdoublet/openttd-ml`, branche de départ `cloud/road1y-pack2-0411`. Réponds en français. Lis d'abord `AGENTS.md` §4/§4.1, `ai/OpexAI/CLAUDE.md`, `docs/cloud/road1y_0411/PROMPT.md` (contexte, règles, données, sources AAA à décompresser) et **`RAPPORT_CLOUD.md`** (§1 « Flotte » et §3).

## Constat (RAPPORT_CLOUD.md)
- Nos lignes mûres ont 7-8 ou 11-12 bus : exactement le plafond `ROAD1Y_FLEET(4) × min(nStopsA, nStopsB)` (`OpexRoad1yRefleetSaved`, `bus_districts_overrides.nut` ~2062-2094). La flotte est bornée par ce plafond, **pas par la demande**, et ne dépend pas de la distance (8,6 bus à 64-80 tuiles comme à 112-128). Chez AAA elle croît de 4,6 (< 48 tuiles) à 13,6 (≥ 160).
- À distance égale, AAA gagne plus par ligne avec moins de bus (64-80 : 34,2 k/5,6 bus contre 29,8 k/8,6 ; 112-128 : 55,9 k/7,9 contre 43,3 k/8,6).
- AAA : ajout sur `min(attente A, B)` > 30, `buildNum = (attente − min(50, cap)) / cap` ≤ 4, rien si ≥ 2 bus arrêtés (`route.nut:2720-2724`, `:2838-2921`, `ExistsWaiting` `:3012-3026`) ; plafond `maxVehicles` qui monte de `max/12` quand la gare déborde, borné par `EstimateMaxVehicles` proportionnel au temps de trajet (`route.nut:2374-2380`, `:2799-2808`) ; retrait des bus arrêtés au-delà de 3 quand `min(attente) < min(50, cap)` (`route.nut:2553-2619`) ; bus déficitaires > 800 jours retirés en fin d'année (`:2480-2498`).

## Déjà réfuté — morceau par morceau (voir LEVIERS_TESTES.md et docs/taches.md, entrée 04/11)
`road1y_fleet` (valeur du plafond), `rich_fleet`, `berth_fleet`, `fleet_unlock`, `pax_bilat` (renfort sur min(A,B)×2), `weak` (adopté, à garder), `dest_full`. Chacun ne changeait qu'UNE règle ; la règle du projet (« évaluer les leviers ensemble ») autorise un portage cohérent de l'ensemble. **Justifie dans ton rapport en quoi ton portage diffère de chacun.**

## À faire
1. Lecture (≤ 1 h) : relire précisément la gestion de flotte routière d'AAA (fichiers ci-dessus) et la nôtre (`OpexRoad1yRefleetSaved`, `_refleetRoadLines`, `OpexRoad1yWeakStep`, la vente/retrait existants). Mesurer dans `n_spread2_gateA.jsonl.gz` (bras `spread2`) et les journaux moteurs la part des renforts « sans demande » et le nombre de bus arrêtés en charge par ligne.
2. Coder un mode `road1y_aaa_fleet` (0/1, défaut 0) pour les lignes bus PAX en route seule, qui remplace dans `OpexRoad1yRefleetSaved` le plafond fixe et la règle somme ≥ capacité par :
   - plafond = estimation du temps d'aller-retour (distance, vitesse du modèle, temps de chargement) → nombre de bus qui couvrent l'intervalle visé, comme `EstimateMaxVehicles` ; relevé progressif si la gare déborde ;
   - ajout seulement si `min(attente A, B)` dépasse un seuil et qu'il y a moins de 2 bus arrêtés en charge à la source ;
   - retrait (vente au dépôt) des bus arrêtés au-delà de 3 quand `min(attente) < capacité`, au plus 1 par mois et par ligne.
   - Garder `road1y_weak`, `spread_stops`, `load_orders` tels quels. À 0 : code exécuté strictement identique.
3. Règles du dépôt : réglage dans `info.nut` (4 valeurs à 0), globale `globals_pre.nut`, lecture + forçage à 0 hors route seule dans LES DEUX chargeurs de `settings.nut` ; pas de closure capturant une locale ; `clone`/`base` réservés ; `OpexDecide("ROAD1Y_AAA_FLEET", ...)` (ajouts, retraits, plafond calculé) sous `DECISION_LOG` ; `sweeps/test_road1y_aaa_fleet.py` ; mise à jour de `sweeps/test_road1y_multimodal_gate.py`, des fixtures `sweeps/fixtures/road100_*.json`, du plafond `sweeps/test_v251_inventory.py` ; depuis la racine, `test_road1y*`, `test_road100*`, `test_v251*` tout vert.
4. Branche `cloud/road1y-aaafleet` depuis `cloud/road1y-pack2-0411`, push de cette branche seulement. Jamais master, aucun défaut changé.
5. Smoke GitHub, comme la mission n°2 (`probes=258` aux deux bras, variante `road1y_aaa_fleet=1`, graines 613553 781335 100, 3 ans, `aaahogex_settings=road_only`, `line_telemetry=true`), suivi par `gh run view` toutes les 10 min. Vérifie : parties complètes, 0 erreur, ajouts/retraits exercés, bus par ligne en fonction de la distance (doit maintenant croître avec elle), profit par ligne. Pas de conclusion économique sur 3 graines ; pas de porte A/B.

## Livrables
`docs/cloud/road1y_0411/RAPPORT_CLOUD3.md`, branche `cloud/road1y-aaafleet` poussée, et en fin de session : branche, commit, valeur à banquer, lien du run.
