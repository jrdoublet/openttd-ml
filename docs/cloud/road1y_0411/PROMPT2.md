# Mission cloud n°2 : `road1y_alt_load` — une part des bus chargent à plein au bout B (route seule, 3 ans)

Dépôt `jrdoublet/openttd-ml`, branche de départ `cloud/road1y-pack2-0411` (= `cloud/road1y-paxmin` : master 558f5bd8 + données + levier `road1y_pax_min` à défaut 0). Réponds en français. Lis d'abord `AGENTS.md` §4/§4.1, `ai/OpexAI/CLAUDE.md`, puis `docs/cloud/road1y_0411/PROMPT.md` (mission n°1 : contexte, règles, données) et **`RAPPORT_CLOUD.md`** (ton propre rapport précédent : §3 « constat secondaire » et §4 levier 2).

## Constat (RAPPORT_CLOUD.md)
Avec `road1y_load_orders=1` (défaut), nos bus PAX chargent à plein (`OF_FULL_LOAD_ANY`) au bout A seulement (`ai/OpexAI/builder_road.nut` ~5463 à la construction, ~6498 à la reconstruction des ordres). Au bout B, temps depuis le dernier chargement médian 4 (p90 16) contre 1 (p90 8) chez AAA ; note de gare B 153 contre 168. `road1y_dest_full=1` (plein aux DEUX bouts pour tous les bus) a été réfuté au smoke (−29 k£/an) : chaque bus attendait deux fois. Ne le refais pas.

## Levier à coder : `road1y_alt_load` (0..50, défaut 0 = pourcentage de bus « inversés »)
- Pour les lignes bus PAX (`kind == "pax"`, mode route) en route seule : environ `N %` des bus de la ligne reçoivent la liste d'ordres inverse — chargement complet au bout B, aucun à A — les autres gardent l'ordre actuel. Ainsi chaque bout a souvent un bus en charge, sans qu'aucun bus attende deux fois.
- Points à traiter (lis le code avant de choisir ; cite fichier:ligne dans ton rapport) :
  1. Comment les bus d'une ligne partagent leurs ordres aujourd'hui (`AIOrder.ShareOrders` ? `CloneVehicle` ? ordres propres ?) aux trois endroits où l'on achète des bus : ouverture de ligne (`builder_road.nut`), renfort (`OpexRoad1yRefleetSaved` dans `bus_districts_overrides.nut` et `_refleetRoadLines`), réallocation `road1y_weak` (`OpexRoad1yWeakStep`, vente + clone) et le remplacement / renouvellement s'il existe. Un bus inversé ne doit jamais repartager les ordres d'un bus normal, et inversement.
  2. Choisir quels bus sont inversés : simplest = au moment d'un achat, inverser si `inversés < round(N % × (bus de la ligne après achat))`. Compter les inversés en lisant les ordres réels (flags de l'ordre 0), pas via un compteur sauvegardé fragile.
  3. Les fonctions qui identifient « les bus d'une ligne » (ex. `OpexLineVehicleIds`) ou qui lisent la station du 1er ordre, le calcul de `waitingA/B`, `road1y_spread_stops` (arrêts joints : mêmes StationID), la sauvegarde/rechargement (`_reconcileAfterLoad`) : vérifier qu'un bus inversé reste reconnu comme bus de sa ligne.
  4. À 0 : code exécuté strictement identique à l'actuel.
- Règles du dépôt (identiques à la mission n°1) : réglage dans `info.nut` (4 valeurs égales à 0), globale dans `globals_pre.nut`, lecture + bornage + forçage à 0 hors route seule dans LES DEUX chargeurs de `settings.nut` ; pas de closure capturant une locale ; `clone`/`base` réservés ; `OpexDecide("ROAD1Y_ALT_LOAD", ...)` si `DECISION_LOG` (bus inversés achetés, lignes concernées) ; test `sweeps/test_road1y_alt_load.py`, ajout dans `sweeps/test_road1y_multimodal_gate.py`, fixtures `sweeps/fixtures/road100_*.json` et plafond `sweeps/test_v251_inventory.py` à jour ; depuis la racine `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'`, `-p 'test_road100*.py'`, `-p 'test_v251*.py'` tout vert.
- Branche `cloud/road1y-altload` depuis `cloud/road1y-pack2-0411`, push de cette branche seulement. Jamais master, aucun défaut changé.

## Smoke GitHub (comme la mission n°1, avec probes=258 aux deux bras)
```
gh workflow run bench.yml --ref cloud/road1y-altload \
  -f mode=paired -f profile=custom -f years=3 -f seeds="613553 781335 100" \
  -f reference="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,probes=258]" \
  -f variant="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,probes=258,road1y_alt_load=33]" \
  -f aaahogex_settings=road_only -f line_telemetry=true
```
Suivi par `gh run view` toutes les 10 min. Vérifie : 6/6 parties complètes, 0 erreur de script, le mécanisme exercé (nombre de bus inversés par ligne, et que ces bus roulent : profit non nul, pas bloqués en dépôt), le temps depuis le dernier chargement et la note au bout B dans la télémétrie des deux bras, et profit_year par graine. Pas de conclusion économique sur 3 graines ; pas de porte A/B (je les lance sur le VPS).

## Livrables
`docs/cloud/road1y_0411/RAPPORT_CLOUD2.md` (choix d'implémentation avec fichier:ligne, pièges rencontrés, smoke), branche `cloud/road1y-altload` poussée, et en fin de session : branche, commit, valeur à banquer, lien du run.
