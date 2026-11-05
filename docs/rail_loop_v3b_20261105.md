# RAIL-LOOP v3b — diagnostic et blocage de qualification (5 novembre 2026)

## Dépendance non remplie

Le mandat v3b exige un **nouveau worktree fondé sur le master fusionné et validé**. La fusion ROAD1Y+RAIL est en **HOLD** (voir `fusion_master_20261105.md` : suite intermédiaire 3816 tests / 213 FAIL / 19 ERROR et incompatibilités de projections OFF). Aucun master fusionné qualifié n'existe encore. Par sûreté, **pas de promotion de v3b, pas de portes A/B et aucun changement de défaut**. Aucun code expérimental non committé de `.wt_rail_loop_20261104` n'a été transféré.

## Diagnostic causal établi en lecture seule

- Smoke précédent `rail_loop=3` : **99 refus `guard_required_pre` pour 44 lignes distinctes** ; par graine 17 : 17 tentatives/7 lignes, 512 : 31/13, 314 : 34/16, 8191 : 17/8.
- `OpexBuildDepot` dans `builder_rail.nut` privilégie un dépôt sur la voie primaire à l'index `k=1`. La garde `OpexRailLoopV3GuardPrecheck` (`rail_loop.nut`) exige un signal dans `[2,k-1]` pour le flux positif, impossible à `k=1` ou `k=2`. Le cas de référence seed 314 avait pu convertir avec `guard_skip k=1`, ce que v3 refuse volontairement.
- Un cas admis (seed 512, `k=3`) a échoué ensuite sur recherche A* avec `astar_ABND iters=32000` : il s'agit d'un second goulot à mesurer, distinct de l'absence de garde PBS.
- `rail_depot_signal=1` n'est **pas** une solution de contournement certifiée : le mécanisme avait présenté des pertes de rames et son constructeur à branche n'est pas compatible avec l'hypothèse de dépôt sur voie primaire de `OpexRailLoopDepotFlow`.

## Correctif v3b spécifié, mais non implémenté

1. Réserver dès la sélection des quais fret la **sortie arrière libre** et une longueur de voie avant permettant dépôt et garde PBS. Après A* voie initiale, choisir un `(k,g)` admissible avec `g>=2`, `k>=g+2`, préférer un dégagement selon la longueur réelle des trains. Faire un constructeur de dépôt v3 dédié sur voie principale, sans destruction de voies, routes, ponts, tunnels ni ouvrages préexistants ; revalider la tuile signalable et les accès en `AITestMode` avant engagement de dépenses. Persister la géométrie réservée.
2. Ne **pas** poser `SIGNALTYPE_PBS_ONEWAY` lorsque la voie initiale est encore bidirectionnelle. Réarmer uniquement après installation/revalidation de la voie retour et de toutes les protections, de façon transactionnelle et fail-closed.
3. Journaliser chaque clone (snapshot des identifiants physiques préexistants, lineId, dépôt, modèles, ordres, phase, identifiant éventuel du clone) avant `CloneVehicle`. Pendant Save/Load, réconcilier contre l'inventaire **physique** `AIVehicleList`, avec signature d'appartenance et unicité ; en cas de 0 ou plusieurs candidats ambigus : **HOLD sans nouveau clone et sans vente aveugle**. Bloquer les autres transactions de flotte tant que le journal n'est pas réconcilié. Exiger `SAVE_FULL_STATE`.
4. Contrats à prévoir : distances dépôt k1/k3/k>=4, angle/courbe/pont/tunnel, PBS impossible, lead arrière occupé, absence de démolition de pièces étrangères, Save/Load avant et après chaque phase CloneVehicle/inscription/démarrage, identifiant recyclé et candidats multiples, projections OFF exactes et état inerte `rail_loop!=3`.

## Portes d'admission futures

Smoke rail seul 4×6 graines **17, 512, 314, 8191**, comparaison v3b contre `rail_loop=1`. Exiger strictement plus de boucles sur **chacune des quatre graines**, 8/8 parties saines, **0 rame perdue** vérifiée par télémétrie physique et **reprise Save/Load injectée et observable**. Ensuite seulement : portes A 40×5 et B 20×10 rail seul sur les nouvelles graines usuelles ; toujours un seul banc `openttd-lab` à la fois et aucune modification pendant un banc.

**Statut : DIAGNOSTIC UNIQUEMENT / V3B NON TERMINÉE.** Les seuils d'admission et de publication ne sont pas atteints.
