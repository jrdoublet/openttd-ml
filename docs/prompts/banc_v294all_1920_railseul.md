# Prompts — bancs de la combinaison V294 + V295 (21/10)

Deux prompts indépendants, à coller dans une session Claude Code **sur le PC** (10 workers), à la racine d'un
checkout à jour d'`openttd-ml`. Script commun : `sweeps/run_v294all_pc.sh` (smoke 1×1 puis porte A 40×3),
testé au VPS le 20/10 avec `SMOKE_ONLY=1` (complet 1927, rail seul 1970, rail seul `ADAPT=400`).

**Bras** (même arbre de code, master `>= 6dcd532`) :
- **référence** : `OpexAI[v294_rail_continuous=0]` = défauts de master (tous les réglages V294/V295 à 0) ;
- **variante, `ADAPT=0` (défaut)** : `OpexAI[v294_rail_bridge_len=20,v294_rail_continuous=1,v294_rail_weight_pct=200,v294_rail_aaa_costs=1,v294_rail_reverse_probe=300,v294_rail_dist_decouple=200,v294_rail_slope_engine=1,v295_astar_fast=1]` ;
- **variante, `ADAPT=400`** : même chose, mais `v294_rail_continuous=0,v294_rail_weight_adapt=400` (recherche
  segmentée, poids adaptatif : départ à 400 %, repli à 200 % puis 100 % sur le segment qui cale).
- **V294c adaptatif n'agit que dans la recherche segmentée** : sous `v294_rail_continuous=1`, les trois appelants
  créent un A\* unique (`OpexCreateRailPathfinder`) et ses crochets ne sont jamais appelés. Les deux leviers
  s'excluent ; d'où les deux variantes.
- V294h (`v294_rail_defer`) est exclu : porte A −36,9 k, et inerte sous l'A\* continu.
- Par rapport au banc de combinaison du 20/10 (run GitHub 39489908683, +81,4 k, `fail_primary`) : V295 est ajouté,
  et le coût de passage à niveau de V294d est corrigé (`edd2127`) ; il était écrasé sur les diagonales.

**1920 n'est pas jouable** : dans le jeu de base tempéré, le premier véhicule (Kirby Paul Tank, wagons, camions)
apparaît en 1925, plus 0 à 511 jours de tirage. Le smoke à 1920 (VPS, 20/10) finit avec 0 véhicule des deux côtés,
AAAHogEx compris (`inactive_company`, banc invalide). **Départ retenu : 1927**, première année où tout le parc 1925
est sûrement disponible ; il n'y a pas d'avions avant 1930. Smoke 1927 au VPS : sain (Opex 15 véhicules, AAA 10).

---

## Prompt 1 — porte A 40×3, partie complète, départ 1927

```
Dépôt openttd-ml, branche master (au moins 6dcd532). Lis AGENTS.md §4/§4.1 et, dans docs/taches.md,
l'entrée V294 (combinaison v294all). Ne change aucun défaut, ne fusionne rien, ne lance aucune porte B.

Banc : porte A gain_short 40×3, partie COMPLÈTE (multimodale), départ 1927, carte 256².
(1920 est injouable : aucun véhicule avant 1925 dans le jeu de base, smoke vide au VPS le 20/10.)
Pré-enregistre d'abord dans docs/taches.md (entrée V294) : SHA exécuté, bras, graines (SEEDS du script),
règle gain_short, seuil relatif 4 %, garde de valeur 5 %, campagne v294all_complet_1927_porteA_40x3_pc_20261021.

Lance, depuis la racine du dépôt :
  git pull --ff-only && git log --oneline -1
  START_YEAR=1927 sweeps/run_v294all_pc.sh 2>&1 | tee results/v294all_complet_1927_porteA.log
Le script fait d'abord un smoke 1 graine × 1 an et s'arrête si OpexAI (compagnie 0) fait une erreur Squirrel.
Pour la variante adaptative, ajoute ADAPT=400 (campagne suffixée _adapt400) ; un banc à la fois.

À la fin, lis results/<campagne>.json et le decision.json du banc, puis rapporte : verdict brut,
Δ profit_year moyen et médian, V/D/E, Wilcoxon p, IC95 bootstrap, seuil 4 %, Δ valeur, ratio Opex/AAAHogEx
des deux bras, et les 5 pires graines. Écris le résultat dans docs/taches.md (V294), commit
« docs(taches): V294all porte A 1927 » et push. Si la porte passe, NE lance PAS la porte B :
donne la commande (GATE=B START_YEAR=1927 sweeps/run_v294all_pc.sh) et attends l'accord.
```

Alternative GitHub (permise pour une porte A si le PC est occupé ; seulement `ADAPT=0`, à adapter sinon) :
```
gh workflow run bench.yml -R jrdoublet/openttd-ml --ref master -f mode=paired -f profile=gain_short \
  -f start_year=1927 -f reference="OpexAI[v294_rail_continuous=0]" \
  -f variant="OpexAI[v294_rail_bridge_len=20,v294_rail_continuous=1,v294_rail_weight_pct=200,v294_rail_aaa_costs=1,v294_rail_reverse_probe=300,v294_rail_dist_decouple=200,v294_rail_slope_engine=1,v295_astar_fast=1]"
```
(Les graines GitHub sont les 40 canoniques, la 73 comprise : AAAHogEx y plante, voir `aaahogex_crash_graine73`.)

---

## Prompt 2 — porte A 40×3, rail seul des deux côtés (1970)

```
Dépôt openttd-ml, branche master (au moins 6dcd532). Lis AGENTS.md §4/§4.1 et, dans docs/taches.md,
l'entrée V294 (combinaison v294all) et la ligne ❌ V294c adaptatif (protocole rail seul de référence,
evidence/review/v294c_a400_20261020/README.md). Ne change aucun défaut, ne fusionne rien, ne lance aucune porte B.

Banc : porte A gain_short 40×3, RAIL SEUL des deux côtés (OpexAI mode_air=0,mode_road=0,mode_water=0 dans
les deux bras ; AAAHogEx disable_veh_aircraft/roadveh/tram/ship=1), départ 1970, carte 256².
Deux variantes, l'une après l'autre : ADAPT=0 (A* continu) puis ADAPT=400 (segmenté + poids adaptatif).
Pré-enregistre d'abord dans docs/taches.md (entrée V294) : SHA exécuté, bras, graines, règle gain_short,
seuil 4 %, garde 5 %, campagnes v294all_railseul_1970_porteA_40x3_pc_20261021 et
v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021.

Lance, depuis la racine du dépôt :
  git pull --ff-only && git log --oneline -1
  RAILSEUL=1 sweeps/run_v294all_pc.sh 2>&1 | tee results/v294all_railseul_1970_porteA.log
  RAILSEUL=1 ADAPT=400 sweeps/run_v294all_pc.sh 2>&1 | tee results/v294all_railseul_adapt400_1970_porteA.log

Pour chaque variante, rapporte comme pour un 40×3 (verdict brut, Δ moyen/médian, V/D/E, p, IC95, Δ valeur,
5 pires graines), puis, par bras, le nombre moyen de lignes rail posées et le profit rail moyen par an.
Compare au témoin rail seul de V294c (référence 1 006 835 £/an, même protocole, code e009ebf).
Écris les résultats dans docs/taches.md (V294), commit « docs(taches): V294all porte A rail seul » et push.
Si une porte passe, NE lance PAS la porte B : donne la commande (GATE=B RAILSEUL=1 [ADAPT=400]
sweeps/run_v294all_pc.sh) et attends l'accord.
```

Impossible sur GitHub : `bench.yml` n'a pas d'entrée pour les réglages d'AAAHogEx (`--aaahogex-setting`).
