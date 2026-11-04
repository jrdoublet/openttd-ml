# T2 — Revue de l'ordonnanceur rail I : slot de recherche et extension (4 novembre 2026)

## Résumé

1. **Le slot `_railSearch` ne fuit pas au défaut** : chaque chemin de prise a un chemin de
   libération. Le compteur `search_in_progress` mesure mal la pression sur le slot, pour deux
   raisons de code (T2-07).
2. **Boucle certaine dans le Cas 2** (seconde voie et second train) :
   - l'admission estime la voie 2 sur la distance de Manhattan ;
   - l'exécution la recalcule sur le tracé réel, plus long ;
   - entre les deux, l'A\* tourne puis échoue sur `CASH` sans mémoire, et recommence au cycle
     suivant en occupant le slot.

   Corrigé derrière l'opt-in `rail_upgrade_cash_memory` (F2, défaut 0).
3. **Bug V190 confirmé** : `_startRailUpgradeSearch` écrasait un slot occupé. Corrigé sans
   condition (F1), **sans effet au défaut** puisque son unique appelant passe après la garde de
   retour anticipé.
4. **Le gain le plus probable** est ailleurs : avec RAIL-LOOP désormais par défaut, le Cas 2
   atteint son seuil d'attente avant celui de RAIL-LOOP. Il double alors **de façon
   indépendante, à une rame**, des lignes qui auraient pu devenir des boucles à 8 rames (T2-03,
   classé (b), à mesurer).
5. **Opcodes** : la préparation des gares avant l'A\* est synchrone (7 à 11 M d'opcodes mesurés).
   Une ligne au tracé introuvable est retracée à chaque cycle par RAIL-LOOP (constat T1, en
   bordure de périmètre).

## Périmètre et provenance

- **Référence** : `ccr-6d627d08-tlnphk` au commit **`8268b653`**, qui contient `rail_loop=1` par
  défaut, puis RAIL-FILL et RAIL-KEEP (opt-in, défaut 0). Les numéros de ligne désignent ce
  commit, sauf mention « branche T2 ».
- Par rapport à `fbc0f100`, la référence du prompt, les lignes de `_expandRailLines` sont
  décalées d'une à trois : `:643` → `:644`, `:706-728` → `:710-732`, `:1830` → `:1834`.
- **Livraison** : branche `cloud/revue-rail-T2-20261104`.
- **Lecture** :
  - complète : `task_rail.nut:1-1414` ;
  - ciblée : `task_projects.nut:899-980` et `1069-1230` (consommation en début de passe),
    `scheduler.nut:255-480` (tranches A\*), `persist.nut:1030-1048` (Load),
    `builder_rail.nut:6519-6640` (upgrade), `lines.nut:317-470` (`_tooClose`, V178),
    `rail_loop.nut:540-630` (sélecteur appelé en tête de `_expandRailLines`).
- **Pas de journaux moteur** dans cette session. Le pack ne contient pas les étiquettes
  `RAIL_EXPAND` ni `C41_RAIL_CASH_RELEASE` : les fréquences sont donc à mesurer sur le PC (§4).

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T2-03 | (b), perte de profit | `task_rail.nut:631`, `:651`, `:675`, `:710-732` ; `rail_loop.nut:604` | Le Cas 2 (seuil : 2 wagons en attente) prend des lignes avant RAIL-LOOP (seuil : une rame pleine). Elles deviennent `doubleTrack=1` et sortent définitivement de RAIL-LOOP, avec 2 rames au plus | Sous RAIL-LOOP, réserver aux boucles les lignes encore admissibles ; le Cas 2 seulement après un refus géométrique de RAIL-LOOP. Opt-in, non codé | Élevé si fréquent : RAIL-LOOP vaut environ +29 k£/an par rame ajoutée, jusqu'à 8 rames, contre 1 rame pour le Cas 2 |
| T2-01 | (a) logique, (c) fréquence ; perte de profit et opcodes | `task_rail.nut:718-722` ; `builder_rail.nut:6614-6619` ; `task_rail.nut:1867-1879` | Le devis d'admission (`line.distance`) est plus faible que le devis d'exécution (`tiles2.len()`). Sur `CASH`, le slot est libéré sans mémoire et l'A\* complet est relancé au cycle suivant, tant que la caisse reste entre les deux | **F2 codé (opt-in)** : mémoriser `totalNeeded` dans `line.upgradeCashNeed` et l'utiliser à l'admission | Moins de recherches d'upgrade identiques ; slot libéré pour les projets |
| T2-02 | (a), bloquant sous V190 | `task_rail.nut:644` → `:732` → `:1834` | Avec V190 actif, `_expandRailLines` continue quand le slot est occupé, et `_startRailUpgradeSearch` **écrase** `_railSearch`, y compris un A\* de projet ou un plan prêt | **F1 codé (sans condition)** : retour immédiat si le slot est occupé. Sans effet au défaut | Rend V190 et FIX2 mesurables sans destruction du portefeuille |
| T2-04 | (b) mesuré, opcodes | `task_rail.nut:1045` → `OpexPrepareRailRoute` | Les plans de gare sont calculés d'un bloc avant la première tranche A\*. Deux `SITEB` ont coûté **7 à 11 M d'opcodes chacun** (`docs/point_9h_20261103.md`) | Découper la préparation en phase reprenable du slot (`phase="plans"`) ou la borner par opcodes, avec repli `SITEB` | Pas de gel ; moins de retard des autres tâches. Économie indirecte |
| T2-05 | (a) répétition, (c) coût ; opcodes | `rail_loop.nut:604-608` (périmètre T1) | Ligne admissible à l'attente mais `OpexDoubleGrowPrimaryRoute == null` : `continue` sans marquage, donc retracée (jusqu'à 2 000 pas) à **chaque** cycle d'expansion | Poser `railLoop=-1` et `railLoopRetry=now+365`, avec `reason=primary_route` | Opcodes ; aucun effet de décision |
| T2-06 | (b), opcodes | `task_rail.nut:395` ; `lines.nut:317-387` | `_tooClose` parcourt toutes les lignes pour chaque candidat de rang, à chaque passe. Les mêmes identités bloquées sont réexaminées sans fin (3 347 rejets pour 162 identités, `point_9h`) | Mémoïsation pure par candidat et version de `_lines`, sous la règle opcodes. Ne pas filtrer avant le TOP_K (déjà réfuté) | Opcodes uniquement |
| T2-07 | (a), mesure | `task_rail.nut:312-326` vs `:369-415` ; `:449-452` | (1) `search_in_progress` est compté **avant** les refus abandon / proximité / caisse : un candidat trop proche est compté « slot ». (2) Les `PROJECT_DISCARD` ne sont publiés que dans une passe qui choisit un projet | Journaliser les deux motifs (slot et vrai motif) et publier les rejets mensuellement, sous `DECISION_LOG` | Diagnostics justes ; aucun effet de jeu |
| T2-08 | (a), robustesse | `persist.nut:1038-1045` | Après Load, un A\* en cours (ou fini, en phase `build`) est abandonné et le portefeuille entier reconstruit | Acceptable (le slot est transitoire par conception). Option : persister `candidate.railPlan` des plans finis | Faible : les bancs ne rechargent pas |
| T2-09 | (a), style | `task_rail.nut:841-1037` | `_continueRailExpansion` ne sert qu'aux sauvegardes anciennes : plus aucun code ne crée `_railExpansion` (seulement `persist.nut:851`) | Relève de T9 (inventaire) | Nul |

### T2-03 — Le Cas 2 double avant RAIL-LOOP

Ordre dans `_expandRailLines` :
1. `OpexRailLoopSelect` (`:631`), qui renvoie `false` après avoir lancé une recherche ;
2. puis, si le slot est libre (`:644`), la boucle historique sur **toutes** les lignes
   (`:651`, qui saute seulement `railLoop > 0`).

| | Cas 2 | RAIL-LOOP |
|---|---|---|
| Seuil d'attente fret | `2 × wagon.capacity`, lu sur `lastWaitingA` (`:675`) | `waiting ≥ capacité de la rame` (`rail_loop.nut:604`) |
| Effet sur la ligne | `doubleTrack=1`, 2 rames | 8 rames au plus |

Avec 3 wagons ou plus par rame, le seuil du Cas 2 est le plus bas. Une ligne en croissance
franchit donc d'abord celui du Cas 2. Une ligne mise de côté par RAIL-LOOP pour caisse
(`railLoop=-1`, nouvel essai à 60 jours) est aussi exposée au Cas 2 pendant ce délai.

Une fois doublée, la ligne est exclue à vie de RAIL-LOOP (`OpexRailLoopEligible` exige
`doubleTrack==0`) et plafonne à 2 rames (`:658`, `trains >= 2`).

**Preuve à produire** sur les journaux du 20×10 RAIL-LOOP, par graine : le nombre de
`RAIL_EXPAND action=double_track ok=1` comparé aux `RLOOP phase=commit`, et la date de chaque
doublement par rapport à la première admission RAIL-LOOP de la même ligne.

**Correction proposée** (opt-in, non codée car (b)) : sous `RAIL_LOOP`, le Cas 2 saute une ligne
tant que :
- `railLoop` vaut 0 ;
- ou que son dernier refus RAIL-LOOP est un report de caisse.

Cela suppose de stocker le motif de refus dans `rail_loop.nut`.

### T2-01 — Recherche d'upgrade relancée en boucle après `CASH`

| Moment | Formule | Source |
|---|---|---|
| Admission | `line.distance × costTrackPerTile + 2 × platformLength × costStation + dépôt + rame` | `task_rail.nut:718-722` |
| Exécution | `tiles2.len() × costTrackPerTile + (quai A2 + quai B2) × costStation + dépôt + rame` | `builder_rail.nut:6614-6619` |

Le tracé réel est en général 1,2 à 1,5 fois la distance de Manhattan.

Si `estimation ≤ caisse < devis réel`, voici l'enchaînement :
1. l'A\* complet tourne ;
2. `_consumeRailUpgrade` reçoit `CASH`, libère le slot et ne garde aucune trace (`:1867-1879`) ;
3. au cycle d'expansion suivant, le même `need` repasse et la même recherche recommence.

La mémoire d'abandon (`OpexRailUpgradeRejectKey`) ne s'applique qu'aux échecs autres que la
caisse (`:1927`).

**Indices.**
- Sous RAIL-SEARCH-PRIO : 85 recherches d'upgrade démarrées pour environ 24 seconds trains en
  référence (`docs/rail_search_prio_20261103.md`).
- 89 recherches « OK » de géométrie identique sur la graine 841478 en 1972
  (`docs/v190_eco_20261103.md` §5), sous V190, où T2-02 s'ajoute.

**F2 (branche T2, opt-in `rail_upgrade_cash_memory`)** :
- `builder_rail.nut` renvoie `result.cost = totalNeeded` sur `CASH` ;
- `_consumeRailUpgrade` l'écrit dans `line.upgradeCashNeed`, champ persistant de la ligne ;
- l'admission du Cas 2 prend `max(estimation, upgradeCashNeed)`.

Au défaut (0), aucune de ces trois lignes n'agit.

### T2-02 — Écrasement du slot sous V190

`task_rail.nut:644` ne rend la main que si `RAIL_SEARCH_PRIO || !OpexV190Active()`. Sous V190,
la boucle continue, et le Cas 2 appelle `_startRailUpgradeSearch` (`:732`), qui affecte
`this._railSearch = {kind="upgrade"…}` sans test (`:1834`).

**F1 (branche T2, sans condition)** : `if (this._railSearch != null) return;` en tête de
`_startRailUpgradeSearch`.

**Sans effet au défaut**, ce qu'un contrat vérifie :
- l'unique appelant de toute l'IA est `task_rail.nut:732` ;
- il est placé après la garde `:644`, qui rend la main quand le slot est occupé et que V190 est
  inactif ;
- rien ne prend le slot entre les deux.

Sous V190, la boucle consomme encore son tour d'expansion à préparer des quais
(`OpexPrepareUpgradeSearch`) tant que le slot est occupé. C'est un gaspillage d'opcodes, plus
une destruction.

## Réponses aux questions du prompt

**1. Cycle de vie de `_railSearch`.**

| Preneur | Emplacement |
|---|---|
| Projet | `_startRailSearch`, `:1101` (`kind=primary`) |
| Upgrade | `_startRailUpgradeSearch`, `:1834` |
| Stock C80 et préparation C121 | `:2006` (T3) |
| Réparation V131 | `:3046` (T3) |
| Worker | `orchestrator.nut` |

| Chemin de libération | Emplacement |
|---|---|
| Plan trouvé dès la première tranche | `:1141` |
| Retour à des quais courts (RAIL-LONG) | `:1315` |
| Caisse insuffisante en consommation | `:1374`, `:1389` |
| Consommation en début de passe | `task_projects.nut:973` |
| Upgrade terminé ou refusé pour caisse | `:1877`, `:1929` |
| Load | `persist.nut:1042` |
| Annulations stock et worker | T3 |

Un plan primaire terminé (`phase=build`) **attend la passe projects suivante**, au plus une passe
de plus si un AIR défensif est en tête (`c77DefensiveDeferred`). **Aucune fuite trouvée au
défaut.**

Les `search_in_progress` (environ 236 par 4×6) surestiment la pression sur le slot (T2-07). Les
mesures historiques indiquent par ailleurs que le slot n'est pas la contrainte (« créneau rail
pas la contrainte », V184, PRIO).

**2. Projets finançables après 1973.** Dans ce périmètre, aucun filtre ne bloque à tort un projet
finançable déjà classé :
- abandon avec délai ;
- proximité `_tooClose` ;
- `vehicle.max_trains` ;
- caisse, avec A\* lancé même sous la caisse et plan conservé.

La seconde source et le prolongement relèvent de la génération (`candidates.nut`, hors
périmètre) et sont déjà mesurés neutres (`docs/cloud_portefeuille_20261104.md`).

Le gisement réel est la **capacité des lignes existantes**, et le défaut T2-03 en gaspille une
partie.

**3. Opcodes.** Points coûteux identifiés :
- T2-04 : préparation synchrone, mesurée à 7-11 M ;
- T2-06 : `_tooClose` à chaque passe ;
- T2-05 : retraçage de RAIL-LOOP.

Les boucles sur `_lines` restent linéaires, avec une seule action d'expansion par appel. Pas de
balayage de carte non borné dans `task_rail.nut:1-1414`.

**4. Reprise après chargement.** Non : le pathfinder n'est pas sérialisable. `persist.nut:1038-1045`
abandonne la recherche et reconstruit le portefeuille ; le projet repartira de zéro (T2-08).

## Corrections livrées (branche `cloud/revue-rail-T2-20261104`)

| Fichier | Changement |
|---|---|
| `task_rail.nut` | F1 : garde en tête de `_startRailUpgradeSearch`. F2 : lecture de `upgradeCashNeed` à l'admission du Cas 2, écriture sur `CASH` dans `_consumeRailUpgrade` |
| `builder_rail.nut` | F2 : `result.cost = totalNeeded` sur `CASH`, sous le réglage |
| `info.nut`, `globals_pre.nut`, `settings.nut` | Réglage `rail_upgrade_cash_memory` (défaut 0, lecture unique) |
| `sweeps/revue_rail_t2_off.py` | Projection OFF stricte, appelée en tête de chaîne (`invest_stall_diagnostic_off.py`) |
| `sweeps/test_revue_rail_T2_20261104.py` | 8 contrats : garde, appelant unique après `:644`, devis divergents, ordre écriture/lecture de la mémoire, projection composée égale aux SHA d'avant intervention, refus d'un hunk altéré, arités |
| Tests des couches RAIL-LOOP/FILL/KEEP et six tests d'inventaire | Composent la nouvelle couche ; plafond d'`AddSetting` passé de 96 à 97 |

**Suite** : 3 415 tests avant comme après, mêmes 16 échecs/erreurs préexistants dans cette
session (B6, deux `rail_long_v3_multi`, `test_v166_*` sans source AAAHogEx), **aucun nouveau**.
`git diff --check` est propre.

**Non compilé** : il n'y a pas de compilateur Squirrel ici. Chaque modification a été relue :
pas de closure, pas de `const`, pas de mot réservé, et `upgrade.cost` existe dans la table de
résultat.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_upgrade_cash_memory=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')

# 0. Fréquence de la boucle T2-01 au défaut, sur des journaux EXISTANTS (aucune partie)
Get-ChildItem .wt_rail_loop_20261104\results\rail_loop_non_erosion_rail_20x10_20261104_engine\*.log |
  ForEach-Object { $n = (Select-String -Path $_ -Pattern 'C41_RAIL_CASH_RELEASE reason=upgrade_cash').Count; "$($_.Name) $n" }
# T2-03 : doublements Cas 2 contre boucles, par graine
Get-ChildItem .wt_rail_loop_20261104\results\rail_loop_non_erosion_rail_20x10_20261104_engine\rail_loop_*.log |
  ForEach-Object { $d = (Select-String $_ 'RAIL_EXPAND action=double_track line=\d+ reason=OK ok=1').Count;
                   $c = (Select-String $_ 'RLOOP phase=commit').Count; "$($_.Name) cas2=$d loops=$c" }

# 1. Compilation 1x1 (F1 est toujours actif)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[rail_upgrade_cash_memory=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t2_smoke_1x1_20261104.json

# 2. Smoke 4x6 rail seul, F2 ON contre OFF
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t2_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t2 --reference $ref --variant $on `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t2_smoke_4x6_20261104.json @aaa
```

**Critères de lecture du smoke.**

| Critère | Attendu |
|---|---|
| `C41_RAIL_CASH_RELEASE reason=upgrade_cash` par ligne | ON : au plus 1 par ligne et par niveau de caisse ; OFF : répétitions |
| `RAIL_SEARCH` | ON ≤ OFF |
| `search_in_progress` | ON ≤ OFF |
| `RAIL_BUILD`, `RAIL_EXPAND double_track ok=1` | ON ≥ OFF |
| Santé | 8/8, 0 erreur NoAI |

Si l'étape 0 montre moins d'une répétition par graine, F2 n'a pas d'objet. Si elle en montre
plusieurs, F2 relève de la règle opcodes : l'adoption se fait si le 20×10 est neutre ou mieux.

**Pour T2-03**, il faut d'abord la preuve de l'étape 0. Ensuite seulement : coder l'opt-in
« la boucle d'abord », puis smoke 4×10 et porte B 20×10. Le gain de RAIL-LOOP n'apparaît qu'à
10 ans.

T2 TERMINÉ
