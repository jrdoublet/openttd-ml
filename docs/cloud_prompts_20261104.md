# Prompts pour sessions cloud (Opus / Fable) — revue des échecs rail du 02-04/11/2026

Branche à pousser avant de lancer : `exp/rail-sibling-20261102` (code expérimental + rapports + `docs/cloud_pack_20261104/`).
Chaque prompt est autonome : une session par prompt, en parallèle si vous voulez. Les sessions cloud
**n'ont pas Docker/OpenTTD** : elles lisent, raisonnent, codent derrière un réglage opt-in, écrivent
des tests de contrat Python, et rendent les commandes de banc à exécuter ensuite sur le PC.

---

## Préambule commun (à coller en tête de chaque prompt)

```
Tu travailles sur le dépôt openttd-ml, branche exp/rail-sibling-20261102. OpexAI est une IA NoAI
(Squirrel) pour OpenTTD 15.3, dans ai/OpexAI/. Elle affronte AAAHogEx-115 (GPL, référence de force ;
idées seulement, ne jamais recopier son code dans OpexAI). Lis d'abord AGENTS.md (§2 architecture,
§2 « Invariants Squirrel », §4 validation), CLAUDE.md, ai/OpexAI/CLAUDE.md, puis
docs/point_9h_20261103.md (bilan des 02-03/11).

Objectif produit : en rail seul, atteindre 100 % du profit annuel d'AAAHogEx à 5 ans (aujourd'hui
~83 %) et ne pas s'effondrer à 10 ans (~45 %) ; en multimodal, 80 % à 10 ans (aujourd'hui ~61-64 %).

Constat transversal mesuré : Opex plafonne à ~50-55 véhicules et ~1,2 train par ligne, son profit est
presque identique d'une carte à l'autre (1,1-1,9 M£/an) ; AAA fait 30-60 k£/véhicule/an contre ~30 k£
pour Opex, avec des rames de 10-13 wagons (souvent 2-3 locomotives), des quais de 7 tuiles, 4 à 12
rames par bonne ligne, une double voie avec des centaines de PBS à sens unique, et une flotte qui grandit
avec le trafic. Après 1973 presque tous les candidats Opex sont rejetés `origin_served` et la caisse dort
(1-2 M£ à 5 ans, 5-8 M£ à 10 ans).

Données : docs/cloud_pack_20261104/campaigns.csv (89 campagnes : réglages, Δ profit, V/D, p, IC95),
per_seed.csv (profit, véhicules, gares, caisse par graine et par bras), logs_<campagne>.csv (comptes
d'événements DECISION_LOG par tag/raison). Les journaux et sauvegardes complets ne sont pas dans le
dépôt : si une question exige une donnée absente, écris exactement la mesure et la commande à lancer.

Hypothèse de travail imposée : un échec mesuré ne prouve PAS que l'idée est mauvaise. Pour chaque
expérience de ton périmètre, distingue (a) idée réfutée, (b) implémentation défaillante (bug, garde
trop stricte, mauvais ordre des opérations, exposition nulle), (c) mesure non concluante. Appuie chaque
conclusion sur fichier:ligne et sur les chiffres du pack.

Contraintes : aucun changement de valeur par défaut ; tout nouveau comportement derrière un réglage
opt-in défaut 0 déclaré dans info.nut/settings.nut, projection OFF octet-pour-octet identique (voir les
projecteurs sweeps/*_off.py existants) ; tests de contrat dans sweeps/test_*.py
(`python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` ; échec préexistant connu :
test_b6_portfolio_causality.test_current_policy_is_observed_not_changed) ; respecter les invariants
Squirrel (pas de `getroottable`, budget d'opcodes, Save/Load). Commits sur une nouvelle branche
cloud/<sujet>-20261104 à partir de exp/rail-sibling-20261102, jamais sur master, pas de merge.

Livrable : docs/cloud_<sujet>_20261104.md avec (1) diagnostic par expérience (a/b/c) avec preuves,
(2) les 1-3 corrections les plus prometteuses, classées par gain attendu / risque, (3) le code de la
meilleure correction derrière son réglage + tests verts, (4) le plan de bancs exact pour le PC :
smoke 4×6 rail seul `python -X utf8 sweeps/run_c66_reference.py` avec graines `17 512 314 8191`,
`--probes 6 --script-debug --line-telemetry --retain-savegames`, critères d'exposition physique
(ce qui doit apparaître dans les journaux), puis portes A 40×5 gain_short et B 20×10 non_erosion.
```

---

## Prompt 1 — Double voie et signalisation (V190, DOUBLE-GROW, RAIL-DEPOT-SIGNAL, RAIL-PAIR)

```
[préambule commun]

Sujet : « double-voie ». Pourquoi n'arrivons-nous pas à faire circuler plus de 2 trains par ligne,
alors que c'est le premier écart avec AAAHogEx ?

Expériences à autopsier (rapports dans docs/) :
- V190-FIX indépendant (v190_rail_double_build=1,v197_guided_double=1) : docs/v190_fix_20261103.md,
  docs/v190_eco_20261103.md. 16 doubles construites, 29/32 trains rentables, MAIS −318 k£/an : la seconde
  recherche A* monopolise le slot `_railSearch` (task_rail.nut ~162-198) et les ouvertures de lignes
  s'effondrent (seed 841478 : 0 ligne en 1971-72 contre 12-14). Jamais plus de 2 trains par double.
- V190 directionnel (v190_fix_directional) : 0 double construite (15 TRK2FAIL, 17 NOPLATFORM, 13 NOPATH2,
  9 DIRECTIONAL_NO_SAFE_SWITCH_PAIR).
- DOUBLE-GROW v1 (double_grow=1, ai/OpexAI/double_grow*.nut) : 9 diagnostics, 0 double, NO_PARALLEL_BAND.
  DOUBLE-GROW v2 (double_grow=2) : 0 double ; refus de caisse 1971-74 (OpexAvailableCapital<250000 alors
  que la caisse finit à 1-2 M£), puis quote=-1, 7 A* sans construction, NO_NATIVE_STATION_SITES
  (docs/double_grow_20261103.md).
- RAIL-DEPOT-SIGNAL (rail_depot_signal) : 26/124 trains perdus avec PBS ; version fail-closed neutre
  (docs/rail_depot_signal_20261103.md). RAIL-PAIR (rail_pair, second quai + PBS sur voie unique) :
  −120 k (docs/rail_pair_20261103.md).
Lis AAAHogEx-115 (railbuilder.nut, station.nut, trainroute.nut ; lecture seule) pour sa géométrie :
double voie dès la construction ou après, PBS à sens unique ~toutes les 7 tuiles, gares 2-3 quais × 7,
dépôts, et comment il évite que la construction monopolise sa recherche.

Questions : quelle est la façon la plus simple et robuste, dans l'architecture OpexAI, de poser une
ligne fret à deux voies à sens unique (construction initiale doublée, ou doublement différé) sans bloquer
le portefeuille, et de faire grandir la flotte à 4-8 rames ? Quelles gardes/ordres d'opérations de nos
implémentations sont faux ? Propose et code la version minimale qui construit au moins une double par
graine avec >2 rames et sans train perdu.
```

## Prompt 2 — Capacité par rame et réinvestissement (RAIL-LONG v1-v3, RAIL-CONSIST, INVEST-STALL)

```
[préambule commun]

Sujet : « capacite-rame ». Pourquoi nos rames restent courtes et notre caisse dort, alors qu'AAA
transporte 240 unités/rame contre 90 ?

Expériences à autopsier :
- RAIL-CONSIST 200 % (rail_consist_pct) : −61 k (rames longues sur quais courts ?).
- RAIL-LONG v1 (rail_long=1) : exposition faible, devis long rejeté → repli court ; v2 (rail_long=2) :
  smoke −31 k ; avec invest_stall=1 : smoke +174 k (4/4) puis 20×10 +18 k et multimodal −120 k (neutres).
  v3 (rail_long=3, modernisation transactionnelle, docs/rail_long_v3_upgrade_20261104.md,
  docs/rail_long_v3_gates_post_r6_20261104.md) : A rail 40×3 −7 k, A multimodal −64 k (fail), B rail
  20×10 +47 k, B multimodal +100 k (pass non-érosion). docs/rail_long_20261103.md pour v1/v2.
- INVEST-STALL v1-v3 (invest_stall, ai/OpexAI/invest_stall*.nut) : docs/invest_stall_20261103.md,
  docs/invest_stall_obstacles_20261104.md, docs/invest_stall_diagnostic_p0_20261104.md,
  docs/invest_stall_platform_qualification_20261104.md. Constat clé : 37 renforcements de flotte choisis,
  0 terminé (`invest_stall_recheck`, `approach_timeout`, 254 `nonpositive_margin_or_traction`) ; la
  revalidation task_v284.nut ~515-615 réexige des conditions que l'achat ne peut pas satisfaire ?
Lis AAAHogEx-115 (trainroute.nut ~970-1008, ~2957-2988 ; estimator.nut) pour sa composition de rames
(nombre de locos, wagons, choix moteur selon puissance/effort/vitesse) et sa croissance de flotte.

Questions : nos rames longues sont-elles effectivement construites (exposition) ? La marge/traction est-
elle mal calculée (unités, années, coût de remplacement) ? Le pipeline d'achat via dépôt (V284) est-il
trop fragile ? Propose et code la voie la plus directe pour obtenir, sur les lignes fret à fort trafic,
des rames ≥ 8 wagons (multi-traction si nécessaire) et une flotte qui grandit quand la cargaison attend.
```

## Prompt 3 — Portefeuille, recherche et arrêt d'investissement (SEARCH-PRIO, origines épuisées, RAIL-OPEN/SIBLING)

```
[préambule commun]

Sujet : « portefeuille ». Pourquoi Opex cesse d'ouvrir des lignes après 1973 avec des millions en
caisse, alors qu'AAA continue de croître ?

Expériences à autopsier :
- RAIL-SEARCH-PRIO (rail_search_prio) : −325 k ; avec V190 −410 k ; lignes 141 contre 176,
  `search_in_progress` 163 contre 125, 3 707 `blocked:project` : la préemption aggrave le goulot
  (docs/rail_search_prio_20261103.md). Les recherches secondaires (upgrades, stock C80,
  task_rail.nut ~1580-1831) partagent le slot `_railSearch`.
- Diagnostic d'épuisement : invest_stall_baseline (dans docs/invest_stall_20261103.md) : seed 17 en
  1973, 3 547 rejets `generation_reject_origin_served` sur 3 717 candidats ; 1975 : 1 778/1 965,
  120 `rail_open_reject_both_ends_served`.
- RAIL-SIBLING (rail_sibling) et RAIL-OPEN (rail_open) : +22 à +61 k, neutres ou faibles
  (docs/rail_sibling_lot1_40x5_analysis_20261102.md, docs/rail_open_20261102.md).
- Graines systématiquement perdantes : docs/rail_pires_graines_20261102.md et per_seed.csv (314, 8191,
  512, 746035, 232037, 100, 1024, 1337 : ratio 34-76 %, AAA y monte à 50-70 véhicules).
Lis AAAHogEx-115 (main.nut, estimator.nut ~1767-1811) : comment choisit-il ses routes, réutilise-t-il
une source déjà desservie (autre destination, plus de trains, autre cargaison), comment son budget ROI
évolue avec la caisse.

Questions : la règle `origin_served` est-elle trop stricte (une industrie qui produit plus que ce qu'on
transporte devrait rester candidate) ? L'ordonnanceur de recherches est-il structurellement sous-
dimensionné (un seul slot) ? Propose et code la correction qui fait remonter le nombre de projets
choisis/construits après 1973 sans dégrader 1970-72.
```

## Prompt 4 — Revue croisée « pourquoi 30 k£ par véhicule au lieu de 60 » (synthèse, sans code obligatoire)

```
[préambule commun]

Sujet : « synthese ». Avant tout nouveau correctif, compare de bout en bout une ligne fret type d'OpexAI
et d'AAAHogEx-115, du choix de la route à la livraison : cargaison et distance choisies, gare (quais,
longueur, orientation, jointure), voie (simple/double, signaux), dépôt, moteur et wagons (puissance,
vitesse, capacité), ordres (chargement complet, partage), cadence, note de gare, profit par rame et par
an. Utilise docs/point_9h_20261103.md, docs/v190_eco_20261103.md §6 (photographies déc. 1975 des deux
IA), per_seed.csv et le code des deux IA. Classe les écarts par contribution estimée au déficit de
profit par véhicule, et pour les 3 premiers dis lequel de nos chantiers l'attaquait, pourquoi il a échoué
(idée / implémentation / mesure) et quelle serait la bonne implémentation dans OpexAI. Livrable :
docs/cloud_synthese_20261104.md, avec une feuille de route ordonnée (pas de code obligatoire).
```
