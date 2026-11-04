# T4 — Revue du pathfinder et de la recherche segmentée (4 novembre 2026)

## Résumé

1. **Trou certain dans l'interdiction des virages à 90°.** La bibliothèque les refuse grâce au
   grand-parent du nœud. Chaque nouveau segment repart de `[front, previous]` sans
   grand-parent, si bien que le premier pas d'un segment peut faire un coude à 90°, et même sans
   coût de virage. Sous `pf.forbid_90_deg=1` (défaut de nos duels), une telle ligne n'est pas
   roulable (T4-01).
2. **Mesure livrée, sans effet au défaut** : sous `decision_log`, `V214_PATH` porte `ninety=` et
   `segments=`. **Le correctif reste à qualifier** (opt-in) : la bibliothèque accepte déjà un 3e
   élément de source quand `V233_LONG_GOOD=1`, ce qui est le défaut.
3. **Q1, les `structures` vides n'ont pas d'effet au défaut.** Le repli
   `GetOtherTunnelEnd(cur) == next` des constructeurs reproduit la classification de la
   bibliothèque. Seul DOUBLE-GROW (opt-in) refuse les ouvrages sans type, et donc tout ouvrage
   choisi par l'A\*, en mode continu **comme en mode segmenté** (T4-05).
4. **Q2, pentes** : une pente coûte une tuile. Le poids A\* (200 %, puis 400 % par V294c) écrase
   encore ce coût, et V294j ne le relève que pour une locomotive faible, sans tenir compte du
   poids de la rame (T4-02, à mesurer).
5. **Q3, la limite est `HARD_ITERATION_CAP = 5 000`.** Un `ABND` occupe environ 50 à 75 jours de
   slot. Les `ABND` font 40 % des `RAIL_BUILD_FAIL` du pack et `NOPA` 4,4 %. Les leviers de
   budget, de report et de sens inverse sont déjà réfutés (T4-03).

## Périmètre et provenance

- **Référence** : `ccr-6d627d08-tlnphk` au commit **`8268b653`**. Les numéros de ligne
  désignent ce commit.
- **Livraison** : branche `cloud/revue-rail-T4-20261104`, partie de `8268b653`, indépendante
  de T2 et de T3.
- **Lecture complète** : `builder_rail.nut:2027-3095`.
- **Lecture ciblée** :
  - `pathfinder_v90/v129.nut` : `InitializePath` `:325-410`, `_Cost` `:483-600`,
    `_Neighbours` `:630-720` ;
  - `pathfinder_v90/rail.nut:60-200` (coûts par défaut) ;
  - consommateurs des `structures` : `builder_rail.nut:4086-4100`, `:4244-4252`,
    `:4312-4322`, `:5136-5150`, `:5195-5206`, `rail_loop.nut:296-310`,
    `double_grow_geometry.nut:612-624`, `double_grow_v2_build.nut:146-155` ;
  - `task_rail.nut:1040-1130` et `:1250-1270` ;
  - `v233_long_good.nut:488-540`.
- **Historique** : `docs/taches.md`, entrées RAIL-ECH (20/10), V294 et V294h (20/10), V307
  (21-26/10) et V261/V262 (`forbid_90_deg`, 18/10).
- **Pack** : `docs/cloud_pack_20261104/logs_*.csv`, en comptes agrégés. Il ne contient pas les
  champs `V214_PATH` ni `RAIL_SEARCH ... iters=` par ligne.

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T4-01 | (a) code, (c) fréquence ; **bloquant** par ligne touchée | `builder_rail.nut:2807` (`[[front, previous]]`), `:2778` (alternatives), `:2656` ; `v129.nut:401-405`, `:653-662` | À chaque jonction de segments (coupure à 2 000 itérations, retour arrière), le segment suivant démarre de `Path(null, previous) → front`. Au premier développement de `front`, `gp == null` : le filtre « Disallow 90 degree turns » (`offset == blocked`), le coût de virage et `_TunnelsBridgesInto` sont sautés. Un coude en U (E, N, O) devient possible, et même moins cher qu'un virage normal | Opt-in à qualifier : source `[front, previous, prefix[len-3]]`, que `v129.nut:394-400` accepte déjà sous `V233_LONG_GOOD > 0` (défaut 1). Raccorder la queue à partir de l'indice 3 au lieu de 2 (le 1er nœud devient le grand-parent), et faire de même pour les alternatives. **Mesure livrée** : `ninety=` | Une ligne à coude interdit n'est pas roulable (capital perdu, `NOTRAIN`/train perdu, slot). Fréquence inconnue : à lire dans `ninety=` |
| T4-02 | (b) ; perte de profit | `rail.nut:72` (`slope=100`) ; `builder_rail.nut:2040-2058` ; `globals_pre.nut:193` (poids 200), `:155` (V294c 400) | Une tuile en pente coûte 100, autant qu'une tuile plate de plus. Le poids A\* (×2 à ×4 sur l'heuristique) rend la montée encore moins chère relativement. V294j ne passe la pente à 1 500 que si la force de traction est sous `pente × 50` kN, ou si la puissance est sous `pente × 600` sur une carte montagneuse. **La masse de la rame est ignorée**, alors que RAIL-LOOP et RAIL-FILL allongent et remplissent les trains | Mesurer d'abord : tuiles en pente par ligne et vitesse moyenne chargée. Puis, en opt-in, un coût de pente dérivé du rapport force de traction / masse prévue (locomotive + wagons pleins) | Inconnu ; perte de vitesse en charge sur les lignes vallonnées, sensible pour les rames longues |
| T4-03 | (a) mesuré ; opcodes et slot | `globals_pre.nut:675` ; `builder_rail.nut:82-120` (`OpexIterationBudget`) ; `task_rail.nut:1796` (ban `ABND`) | Plafond de 5 000 itérations. Un `ABND` occupe environ 50 jours de slot (RAIL-ECH) ou 75 jours de médiane (V307, 42 % du temps des tentatives rail), à environ 1 500 opcodes par itération. Pack : **3 847 `ABND` sur 9 682 `RAIL_BUILD_FAIL` (40 %)**, 426 `NOPA` (4,4 %). Chaque `ABND` bannit la paire 365 × n jours (T3-02) | Aucune proposition nouvelle de budget. **Déjà réfutés** : relever le plafond (V97), reprendre en fond (V294h, porte A −36,9 k), chercher en sens inverse (V307 mode 6, neutre). Restent le coût par itération (règle opcodes) et T4-01 | Indirect |
| T4-04 | (a) ; style | `builder_rail.nut:2595`, `:2401`, `:2423` | `state.bridgeLen` n'est jamais lu. `OpexLocalStructureChoices` borne ponts et tunnels par la constante `SEGMENTED_BRIDGE_MAX_LEN` (20), alors que l'A\* d'un segment suit `V294_RAIL_BRIDGE_LEN` | Lire `state.bridgeLen` (repli sur la constante) | Nul au défaut (20 = 20) ; cohérence si le réglage change |
| T4-05 | (a) ; robustesse, opt-in seulement | `builder_rail.nut:2199-2205` ; `double_grow_geometry.nut:618-620` ; `double_grow_v2_build.nut:150-152` | Q1 : en mode continu (`v294_rail_continuous`, défaut 0), `structures = []`. **En mode segmenté (défaut) aussi**, seuls les ouvrages de `OpexLocalStructureChoices` sont enregistrés, pas ceux que l'A\* choisit à l'intérieur d'un segment. Au défaut, sans effet : tous les constructeurs replient sur `GetOtherTunnelEnd(cur) == next`, le même critère que `_Cost` (`v129.nut:506`). DOUBLE-GROW refuse en revanche tout `kind == null` (`clear_structure`, `missing_bridge_or_tunnel`) | Pour DOUBLE-GROW : accepter `null` quand le repli est vérifiable sous `AITestMode` (tunnel ou pont de la longueur voulue) | Nul au défaut ; débloque les ouvrages de DOUBLE-GROW s'il revient |
| T4-06 | (c) ; robustesse, V190 seulement | `builder_rail.nut:505-519` | `OpexV190MergeIgnoredTiles` ferme les bandes parallèles de **tous** les plans A et B, sans exclure les `lead`/`station_exit` des autres plans : un quai candidat peut devenir inatteignable. Au défaut, seul V233L s'en sert, et il protège ses interfaces primaires (`v233_long_good.nut:496-510`, plans `[0]`) | Retirer de l'ensemble les leads et sorties de tous les plans | Nul au défaut |

### T4-01 — Coude à 90° à la jonction des segments

**Bibliothèque** (`v129.nut:653-662`) :

```squirrel
local gp = par._prev;
local blocked = (gp != null) ? (gp._tile - par_tile) : 0;
...
if (gp != null && offset == blocked) continue;   // Disallow 90 degree turns
```

**Recherche segmentée** (`builder_rail.nut:2807`, `:2778`, `:2799`) :

```squirrel
state.activeSources = [[front, previous]];
```

`InitializePath` (`v129.nut:401-405`) construit `Path(null, previous)`, puis `Path(p0, front)`.
Au premier `_Neighbours(front)`, `par = previous` et `gp = null`, donc le voisin
`front + (prefix[len-3] - previous)` n'est plus filtré. Dans `_Cost`, la condition de virage
`gp != null && DistanceManhattan(new, gp) == 3` est fausse elle aussi : le coude interdit ne
paie aucun virage.

Après un ouvrage local (`[[to, front]]`), la branche « saut » (`v129.nut:639-645`) impose la
continuation dans l'axe : pas de trou de ce côté-là.

**Pourquoi « bloquant » si cela arrive.**

- La note du 18/10 (`taches.md`, T28 annulé) et `v190_fix_directional.nut:79` établissent que
  `pf.forbid_90_deg` est actif sur nos bancs et que « l'A\* refuse déjà les 90° ». La décision
  utilisateur (5) du 18/10 de ne pas consulter ce réglage repose sur cet invariant.
- `AIRail.BuildRail` et `AreTilesConnected` ne voient pas le coude : la pose réussit. Les trains
  ne trouvent ensuite pas de route.

**Mesure livrée.** Sous `decision_log`, `task_rail.nut` (branche T4 `:1262-1276`) ajoute
`ninety=` et `segments=` à `V214_PATH`. Un U est compté sur quatre tuiles consécutives à pas
unitaires dont la première et la dernière sont voisines. C'est exactement le motif filtré par la
bibliothèque (test de portage dans `test_revue_rail_T4_20261104.py`).

**Correction proposée (non codée).**

1. Sources `[front, previous, prefix[len-3]]` aux trois endroits.
2. Queue raccordée à partir de l'indice 3 (`OpexCanAppendSegment` également).
3. Mêmes changements pour les alternatives empilées.

Chaque recherche segmentée change de trajectoire : opt-in, puis portes A et B.

### Réponses aux questions du prompt

**1. Qui suppose encore des `structures` planifiées ?**

| Consommateur | Comportement si `kind == null` | Au défaut |
|---|---|---|
| `OpexBuildTrack` (`builder_rail.nut:4091`, `:4315`) | Repli tunnel si `GetOtherTunnelEnd(cur) == next`, sinon pont | Correct |
| Devis et sonde de pose (`:4247`, `:5140`, `:5198`) | Même repli | Correct |
| RAIL-LOOP (`rail_loop.nut:303`) | Même repli | Correct |
| V259, ponts mémorisés (`task_rail.nut:1610`, `:1624`, `:1908`) | `kind != "tunnel"` et test `GetOtherTunnelEnd` | Correct |
| DOUBLE-GROW (`double_grow_geometry.nut:619`, `double_grow_v2_build.nut:151`) | **Refus** (`clear_structure`) | Opt-in ; refuse tout ouvrage de l'A\* |

Le repli équivaut à la règle de la bibliothèque (`_Cost`, `v129.nut:506` :
`GetOtherTunnelEnd(new_tile) == prev_tile` ⇒ tunnel, sinon pont), la relation de tunnel étant
symétrique. Le piège historique (`builder_rail.nut:2251-2253`) concernait les choix locaux
segmentés, qui sont enregistrés.

**2. Les poids produisent-ils des tracés que les rames lourdes montent mal ?** C'est probable
(T4-02).

- Coûts au défaut :

  | Élément | Coût |
  |---|---|
  | Tuile | 100 |
  | Pente | 100 |
  | Virage | 50 (V214 : 300 en sortie de diagonale) |
  | Coude serré | 1 500 |
  | Diagonale (V294d) | 67 |
  | Tunnel par tuile | 0 |

- Poids : 200 % au départ, 400 % au premier segment sous V294c.
- `OpexTrainSlopeSteepness` lit bien le réglage moteur (3 % par défaut). V294j ne s'en sert
  qu'en comparant la force de traction du moteur seul.
- Le coût de pente d'AAA n'est pas vérifiable ici : sa source est absente du clone (GPL, non
  récupérée). Le commentaire de `OpexV294ApplyRailCosts` ne cite que diagonale, ponts, tunnels
  et passages à niveau.

**3. Limite d'itérations, coût d'un échec, taux `NOPATH`.**

- Limite : `HARD_ITERATION_CAP = 5 000`, plancher 2 000 et facteur 4 dans
  `OpexIterationBudget`. Les segments font 2 000 itérations (10 000 après un retour arrière,
  toujours bornés par le budget) ; `timeSafe = min(50 000, budget)`.
- Coût d'un échec : environ 50 jours (RAIL-ECH), médiane 75 jours en production (V307) ; une
  itération coûte environ 1 500 opcodes.
- Taux dans le pack : `ABND` 40 % des `RAIL_BUILD_FAIL`, `NOPA` 4,4 %. `RAIL_SEARCH` n'y est pas
  ventilé par issue : à relire sur les journaux bruts (plan, étape 0).

**4. `forbid_90_deg` et tuiles ignorées : un quai constructible inatteignable ?**

- **Oui, pour 90°, dans l'autre sens** : l'A\* *peut* produire un coude interdit à une jonction
  (T4-01), et rendre ainsi inutilisable un trajet dont la variante sans coude existait.
- Tuiles ignorées au défaut :
  - le préfixe moins ses deux dernières cases (correct) ;
  - les réserves V233L, qui protègent les interfaces primaires.
- Toute tuile déjà en rail est une impasse (`_HasRail`) ; seuls les ponts la franchissent.
- Le risque de fermer un quai candidat existe sous V190 (T4-06, opt-in).

## Changement livré (branche `cloud/revue-rail-T4-20261104`)

- **Mesure** : `task_rail.nut`, dans le bloc `if (DECISION_LOG)` de `_continueRailSearch`, après
  le calcul de géométrie. Champs `ninety=` et `segments=` de `V214_PATH`. **Aucun effet au
  défaut** (`decision_log=0`) : ni décision, ni opcode.
- **Projection OFF** : `sweeps/revue_rail_t4_off.py`, nouvelle tête de chaîne de
  `invest_stall_diagnostic_off.off_source`, avant RAIL-KEEP. Elle restaure les octets de
  `8268b653`, est idempotente et refuse un hunk partiel ou dupliqué. Les tests de projection de
  RAIL-LOOP, RAIL-FILL et RAIL-KEEP retirent d'abord cette couche.
- **Tests** : `sweeps/test_revue_rail_T4_20261104.py`, 13 tests.
  - Sémantique du compteur, portée en Python : U compté ; droite, escalier diagonal et coude
    V214 non comptés ; équivalence avec le filtre `blocked` de la bibliothèque.
  - Constat T4-01 documenté : sources à deux tuiles, 3e élément réservé à V233L.
  - Mesure placée dans le bloc `DECISION_LOG`.
  - Projection.
- **Suite complète** :
  - avant : 3 407 tests ;
  - après : 3 420 tests, **mêmes 4 échecs et 12 erreurs préexistants**
    (`test_b6_portfolio_causality`, deux `test_rail_long_v3_multi`,
    `test_v166_aaahogex_settings`) ;
  - `test_v214_rail_turn_costs` reste vert.
- **Squirrel relu deux fois** :
  - `slice` est la table locale de `_continueRailSearch` ;
  - le test `"segments" in slice` couvre le résultat de l'A\* continu (sans ce champ) ;
  - pas de closure, de `const` ni de mot réservé.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$log = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,decision_log=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')

# 0. Sur des journaux EXISTANTS sous decision_log : issues de RAIL_SEARCH et coudes en U
#    (le champ ninety= n'existe qu'à partir de cette branche ; étape 2 pour le compter)
Get-ChildItem .wt_rail_loop_20261104\results\rail_loop_non_erosion_rail_20x10_20261104_engine\*.log |
  ForEach-Object { $o = Select-String $_ 'RAIL_SEARCH type=resumable outcome=(\w+)' |
                   ForEach-Object { $_.Matches[0].Groups[1].Value } | Group-Object |
                   ForEach-Object { "$($_.Name):$($_.Count)" }; "$($_.Name) $($o -join ',')" }

# 1. Compilation 1x1
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t4_smoke_1x1_20261104.json

# 2. Smoke 4x6 rail seul, decision_log=1 contre référence (la mesure n'agit pas sur le jeu)
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t4_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t4_log --reference $ref --variant $log `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t4_smoke_4x6_20261104.json @aaa
# Lecture : coudes interdits et segments par tracé trouvé
Get-ChildItem results\revue_t4_smoke_4x6_20261104_engine\*revue_t4_log*.log | ForEach-Object {
  $p = Select-String $_ 'V214_PATH .* ninety=(\d+) segments=(\d+)'
  $bad = @($p | Where-Object { [int]$_.Matches[0].Groups[1].Value -gt 0 }).Count
  "$($_.Name) paths=$($p.Count) with_ninety=$bad" }
```

**Critères de lecture.**

| Critère | Lecture |
|---|---|
| Santé | 8/8, 0 erreur NoAI, année de fin 1976 |
| `with_ninety` = 0 sur toutes les graines | T4-01 reste un trou logique sans fréquence observée ; garder l'opt-in en réserve |
| `with_ninety` > 0 | Croiser `start=`/`end=` avec la ligne construite : profit nul, `NOTRAIN`, train « perdu ». Si au moins une ligne morte par graine, coder l'opt-in T4-01, puis porte A 40×3 et porte B 20×10 |
| `segments` des tracés avec coude | Doit être ≥ 2 (sinon le U viendrait d'ailleurs : relire le contrôle `gp` de la bibliothèque) |
| Profit et valeur, référence contre `decision_log` | Seul le journal diffère ; un écart s'explique par le décalage d'opcodes (chaos), pas par une décision |
| T4-02 (pentes) | Hors de ce smoke. Instrumenter d'abord le nombre de tuiles en pente par tracé (même endroit que `ninety=`) avant tout opt-in |
