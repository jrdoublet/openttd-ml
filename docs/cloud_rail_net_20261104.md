# RAIL-NET : greffer une ligne fret sur une boucle existante (`rail_net`, défaut 0) — 4 novembre 2026

## Résumé

- **Constat.** Opex pose des lignes indépendantes point à point. AAA réutilise ses voies :
  gares partagées, embranchements, double voie à PBS à sens unique.
- **Premier pas.** Une **source fret nouvelle S** se greffe sur une **boucle RAIL-LOOP
  certifiée** (`railLoop == 2`) qui livre déjà le même cargo à la même gare B. Il n'y a plus de
  ligne S→B complète à poser : on pose un quai S et deux embranchements à sens unique.
- **Opt-in strict, fail closed.** Tout ce qui touche l'hôte est posé **en dernier** puis
  certifié. En cas d'échec, tout est retiré et la paire reste au portefeuille ordinaire (ligne
  simple).
- **Ce qui est validé, et ce qui ne l'est pas.** Code statiquement vérifié (30 contrats,
  projection OFF au bit près, suite complète inchangée), **non exécuté en moteur** : le
  smoke 4×6 du §7 est le premier banc obligatoire, avant tout autre usage.

## 1. Topologie

```
                     voie chargée de l'hôte (sens →)
   A ══════════════════════════════╦══════════════════════════════► B (quai partagé, déchargement)
   ▲                         T1 (fusion)                              │
   │                               ▲  embranchement 1 (sens unique)   │ (traversée du quai B)
   │                               │                                  ▼
   │                       [dépôt] │◄── S (quai neuf, plein chargement)
   │                                   ▲ embranchement 2 (sens unique)
   │                                   │
   ◄══════════════════════════╩════════╧══════════════════════════════╝
                     voie vide de l'hôte (sens ←)         T2 (divergence)
```

| Élément | Définition | Code |
|---|---|---|
| Voie chargée | `flow > 0` : voie 1 (`OpexDoubleGrowPrimaryRoute`) ; sinon voie 2 (`railLoopTrack2`) | `OpexRailNetTracks` |
| Voie vide | Voie 2 ; ou voie 1 parcourue à l'envers | idem |
| Embranchement 1 | Sortie **avant** du quai S → case latérale L1 → T1, sur la voie chargée | A\* `OpexCreateRailPathfinder([plan S], [{lead=L1, station_exit=T1}])` |
| Embranchement 2 | T2 sur la voie vide → case latérale L2 → sortie **arrière** du quai S | A\* `OpexCreateRailPathfinder([{lead=L2, station_exit=T2}], [plan arrière S])` |
| Rame greffée | Construite au **dépôt de l'hôte**, qui sort dans le sens de marche. Ordres : S plein, puis B (`OpexBuildTrains`) | `OpexRailNetCommit` |
| Dépôt d'entretien | Sur l'embranchement 1, ouvert dans les deux sens | `OpexBuildDepot` + courbe aval |

Les rames de S tournent S → T1 → B → T2 → S, dans le **même sens** que celles de l'hôte, sur
le tronçon partagé T1 → B → T2. Toutes les voies sont à sens unique : il n'y a **aucun
face-à-face possible**.

## 2. Pose fail closed (`OpexRailNetBuild`)

1. **Sans dépense.** Le quai S n'est desservi par personne. Les extrémités des embranchements
   sont des cases simples (pas d'ouvrage collé à un aiguillage). Aucun coude en U interdit par
   `pf.forbid_90_deg`. Pose testée sous `AITestMode` avec `AIAccounting`. Caisse ≥ coût mesuré
   + quai + dépôt + rame. Slot train libre.
2. Quai S, gare neuve.
3. Intérieurs des deux embranchements, raccordés à S mais **pas** à l'hôte : S est isolé.
4. Dépôt d'entretien sur l'embranchement 1, avec sa courbe aval.
5. PBS_ONEWAY (`OpexRailLoopSignalRun` → `OpexV190Fix2PlaceSignal`) :
   - embranchement 1 : après le dépôt ;
   - embranchement 2 : premier signal à **≥ longueur de rame + 2 cases** de T2 ;
   - au moins un signal sur chaque embranchement.
6. Continuité des deux embranchements, ouvrages compris (`OpexRailNetVerifyPath`).
7. **Seulement maintenant**, les deux pièces d'aiguillage : `BuildRail(L1, T1, T1+)` et
   `BuildRail(T2−, T2, L2)`, puis les raccords L1 et L2.
8. **Certification** :
   - l'hôte reste continu sur T1 et T2 (`AreTilesConnected(prev, T, next)`) ;
   - les deux aiguillages sont raccordés ;
   - les deux embranchements sont continus.
9. Rame : construction, ordres, inscription de la ligne, **puis** démarrage.

**Retour arrière** (`OpexRailNetRollback`) : retrait de la **seule** pièce d'aiguillage ajoutée
(`RemoveRail`, jamais `DemolishTile` sur T1/T2), des signaux, des cases d'embranchement à nous,
du dépôt et du quai S. Ensuite `railNetTried` (365 jours, par industrie) et retour au
portefeuille.

**Load en cours de route.** L'état `_railNetState` n'est pas sauvegardé. Comme l'hôte est
touché en dernier, une interruption avant l'étape 7 laisse des rails **isolés**, jamais un
aiguillage vers un embranchement inachevé. Une interruption entre l'étape 7 et l'inscription
laisse un embranchement raccordé sans rame : sans danger, car aucun ordre de l'hôte n'y mène.

## 3. Capacité par canton (étape 2)

- **Cantons.** Longueurs entre PBS_ONEWAY, relevées le long de chaque voie dans le sens de
  marche (`OpexRailNetBlocks` ; un PBS posé par `OpexV190Fix2PlaceSignal(toward=1)` regarde
  `tiles[i-1]`).
- **Débit du tronçon.** `passages/mois = 30 × (0,036 × vitesse) / (canton_max + longueur_rame)`.
  L'intervalle minimal entre deux rames est le temps de libérer le plus long canton plus la
  rame elle-même. 0,036 × vitesse donne des cases par jour, la même convention que
  `OpexLineEconomics`.
- **Demande.** Chaque rame (hôte et greffe) passe une fois par rotation :
  `rames × 30 / (2 × jours aller)`.
- **Admission.** Demande ≤ `RAIL_NET_UTIL_PCT` (70 %) du débit, **et** les plafonds
  anti-interblocage du §4.

## 4. Analyse d'interblocage

| Risque | Mécanisme | Règle codée | Où |
|---|---|---|---|
| Face-à-face | Impossible : toutes les voies et les deux embranchements sont à sens unique (PBS_ONEWAY) | Sens unique certifié | `OpexRailLoopSignalRun(..., toward=1, ...)` |
| Anneau saturé (gridlock) | Un anneau de N cantons à sens unique se bloque s'il porte N rames : aucune ne trouve de canton libre devant elle | **Rames de l'hôte + de la greffe ≤ N − 2**, avec N = `railLoopBlocks` (cantons des deux voies + 2 quais), la règle déjà employée par `OpexRailLoopCommit`. Les rames greffées sont comptées entières sur l'anneau de l'hôte (prudent : elles n'y passent qu'une partie du temps) | `OpexRailNetCycleCap`, `OpexRailNetCapacity`, `OpexRailNetHostMayGrow`, `OpexRailNetGrow` |
| File de chargement complet qui remonte jusqu'à un aiguillage | Les rames attendent derrière celle qui charge. Si la file atteint T2, les rames de l'autre ligne sont bloquées derrière une attente de **production**, sans limite si la source s'arrête | **Greffe** : rames ≤ cantons de l'embranchement 2 + 1. **Hôte** : rames ≤ cantons entre T2 et son quai + 1, avec T2 choisi pour la file de l'hôte actuelle puis `railNetQueueCap` vérifié à chaque croissance de l'hôte | `OpexRailNetQueueFits`, `OpexRailNetDivergeSite`, `OpexRailNetGrow`, `OpexRailNetHostMayGrow` |
| Rame arrêtée qui engage l'aiguillage | Une rame arrêtée au premier signal après une divergence, avec sa queue sur T2, bloquerait la voie vide | Premier PBS de l'embranchement 2 à ≥ longueur de rame + 2 cases de T2. Aiguillages à ≥ longueur de rame + 2 cases des deux extrémités de chaque voie de l'hôte | `OpexRailNetBuild` (`host.platformLength + 2`), `OpexRailNetPlan` (`margin`) |
| Fusion | Une rame de l'embranchement 1 attend à son dernier PBS, la tête **avant** T1, sans engager l'hôte. Le PBS réserve le passage de T1 jusqu'au signal suivant de la voie chargée | Pas de signal sur T1 (TracksOverlap). PBS sur l'embranchement 1 avant L1 | `OpexRailNetJunctionTile`, `OpexRailNetBuild` |
| Coude à 90° interdit | `pf.forbid_90_deg=1` : une ligne avec un U n'est pas roulable | Case interdite à l'A\* devant L1 et derrière L2, contrôle des quatre cases autour de chaque aiguillage, contrôle des deux embranchements entiers | `OpexRailNetBegin`, `OpexRailNetHasNinety` |
| Quai B partagé | Déchargement court (B sans plein). La file avant B est sur la voie chargée, comptée dans l'anneau | Plafond de l'anneau | idem |
| Entretien | Les rames greffées vont au dépôt de l'embranchement 1 (sur leur parcours). Les rames de l'hôte gardent leur dépôt | Dépôt ouvert dans les deux sens | `OpexRailNetBuild` |

**Limites connues, classées (c), à vérifier en moteur.**
- Avec `railLoopFlow < 0`, le dépôt de l'hôte est sur la voie vide : la première rame greffée
  traverse le quai de chargement de l'hôte avant de rejoindre S. Elle peut y attendre une rame
  en plein chargement.
- Une rame de l'hôte pourrait choisir le dépôt de la greffe pour son entretien (YAPF, dépôt le
  plus proche) et traverser le quai S.
- Une seule greffe par hôte dans cette étape (`railNetFeeder`). Le tracé de l'hôte n'est plus
  relu après greffe : la capacité de la greffe s'appuie sur `railLoopBlocks`, `railNetPbs2` et
  `railNetQueueCap`.

## 5. Planificateur (étape 3)

Pour chaque hôte admissible, au plus 4 hôtes par passe :
1. **Sources.** Industries qui produisent le cargo de l'hôte, sans aucune gare autour
   (`GetAmountOfStationsAround == 0`), à ≥ 24 cases de B, proches du tronc, hors mémoire
   `railNetTried`.
2. **Sites.** Quai S à partir de `OpexStationPlans` (même longueur que les quais de l'hôte), avec
   un arrière libre et plat. T1 au plus près de la sortie avant de S, T2 au plus près de son
   arrière, tous deux dans un rayon de `RAIL_NET_MAX_SPUR` = 40 cases.
3. **Devis.**
   - Greffe : (embranchements à vol d'oiseau × 1,4) × voie × `RAIL_TERRAIN_FACTOR`, plus quai,
     dépôt et rame.
   - Ligne simple : `OpexLineEconomics(S→B)`, le modèle du portefeuille.
4. **Choix** : greffe seulement si `devis greffe ≤ 80 % × devis ligne simple` **et** capacité
   admise. Sinon `RNET phase=plan choice=plain_cheaper|capacity|no_junction|spur_far|no_site` :
   RAIL-NET ne fait rien et le portefeuille garde la ligne simple.

## 6. Câblage, projection OFF, contrats

- **Réglage** `rail_net` (booléen, défaut 0), une seule lecture. Global `RAIL_NET`.
- **Module** `ai/OpexAI/rail_net.nut`, chargé par `main.nut`. Champ transitoire `_railNetState`.
- **Points d'entrée** :
  - `task_rail.nut::_expandRailLines` appelle `OpexRailNetSelect` après RAIL-LOOP ;
  - `scheduler.nut` appelle `OpexRailNetStep`, une tranche A\* de 200 itérations par passe,
    6 000 par embranchement.
- **Exclusions.** Les lignes greffées échappent à RAIL-LOOP (`OpexRailLoopEligible`), aux
  Cas 1/2 et à V284. RAIL-LOOP ne fait plus grandir un hôte saturé (`OpexRailNetHostMayGrow`).
  Sans greffe, aucune ligne ne porte `railNetHost` : seuls les opcodes changent quand
  `rail_net=0`.
- **Projection OFF** : `sweeps/rail_net_off.py`, en tête de chaîne de
  `invest_stall_diagnostic_off.off_source`. Elle restaure au bit près les 8 fichiers touchés
  par rapport à `8268b653` (empreintes dans le test) et refuse un hunk partiel ou dupliqué.
- **Contrats** : `sweeps/test_rail_net_20261104.py`, 30 tests :
  - câblage et gardes ;
  - ordre de pose fail closed et certification ;
  - retour arrière qui ne touche jamais une case de l'hôte ;
  - règles d'interblocage, avec les formules portées en Python ;
  - planificateur ;
  - sûreté Squirrel (closures, mots réservés, `const`) ;
  - arité et existence de toutes les fonctions `Opex*` appelées ;
  - projection.
- **Compteurs de réglages** : 96 → 97 dans six tests, motif « RAIL-NET opt-in ».
- **Suite complète** : 3 437 tests, mêmes 4 échecs et 12 erreurs préexistants
  (`test_b6_portfolio_causality`, deux `test_rail_long_v3_multi`, `test_v166_aaahogex_settings`).

## 7. Plan de banc pour le PC

RAIL-NET n'agit que sur des boucles **certifiées** : il faut donc `rail_loop=1` (défaut) et des
parties assez longues pour qu'une boucle existe. D'où un smoke de 6 ans, avec `decision_log`
pour `RNET` et la sonde des véhicules perdus : `probes=65542` = 65536 (véhicules perdus) + 6
(bits habituels du smoke). Une valeur explicite dans le bras prime sur `--probes`.

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,decision_log=1,probes=65542]'
$net = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,decision_log=1,probes=65542,rail_net=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')

# 1. Compilation 1x1 (le module n'est actif qu'avec rail_net=1)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[rail_net=1,decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/rail_net_smoke_1x1_20261104.json

# 2. Smoke 4x6 rail seul
python -X utf8 sweeps/run_c66_reference.py --campaign rail_net_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id rail_net --reference $ref --variant $net `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/rail_net_smoke_4x6_20261104.json @aaa

# 3. Lecture
Get-ChildItem results\rail_net_smoke_4x6_20261104_engine\*rail_net*.log | ForEach-Object {
  $f = $_
  $plan   = (Select-String $f 'RNET phase=plan').Count
  $conn   = (Select-String $f 'RNET phase=plan .*choice=connect').Count
  $begin  = (Select-String $f 'RNET phase=begin').Count
  $commit = (Select-String $f 'RNET phase=commit').Count
  $fail   = Select-String $f 'RNET phase=fail .*reason=(\w+)' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Group-Object | ForEach-Object { "$($_.Name):$($_.Count)" }
  $feeders = Select-String $f 'RNET phase=commit .*feeder=(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }
  $hosts   = Select-String $f 'RNET phase=commit host=(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }
  $lost  = @(Select-String $f 'C41_VEHICLE_LOST .* line=(\d+)' | Where-Object { ($feeders + $hosts) -contains $_.Matches[0].Groups[1].Value }).Count
  $crash = @(Select-String $f 'RNET phase=watch .*(feeder_crashed=[1-9]|host_crashed=[1-9])').Count
  $stuck = @(Select-String $f 'RNET phase=watch .*feeder_stopped=(\d+) .*host_stopped=(\d+)').Count
  "$($f.Name) plan=$plan connect=$conn begin=$begin commit=$commit fails=[$($fail -join ',')] lost=$lost crash=$crash watch=$stuck" }
```

**Critères du smoke** (tous obligatoires pour passer à la suite) :

| Critère | Seuil |
|---|---|
| Santé | 8/8 parties complètes, 0 erreur NoAI ou Squirrel, année de fin 1976 |
| Exposition | ≥ 2 `RNET phase=commit` sur les 4 graines ; sinon RAIL-NET est inerte et il faut relire les motifs `plan` (`no_junction`, `plain_cheaper`…) avant tout banc économique |
| **Trains perdus** | **0** `C41_VEHICLE_LOST` sur une ligne greffée ou sur son hôte |
| **Accidents** | **0** relevé `watch` avec `feeder_crashed` ou `host_crashed` > 0 |
| **Trains bloqués** | Aucune ligne dont `feeder_stopped + host_stopped` = **toutes** ses rames sur **deux relevés consécutifs** (30 jours d'écart). Un arrêt isolé à un signal est normal |
| Débit | Profit annuel de la greffe > 0 à sa deuxième année. Profit de l'hôte non dégradé de plus de 10 % par rapport à l'année avant la greffe (`--line-telemetry`) |
| Fail closed | Pour chaque `RNET phase=fail` après `begin` : pas de rails orphelins raccordés à l'hôte (sauvegarde : T1/T2 n'ont qu'une pièce de voie) |
| Économie | Smoke seulement. Ensuite porte A 40×5 `gain_short`, puis porte B 20×10 `non_erosion`, garde de valeur 5 % ; `rail_net` reste à 0 jusqu'à la décision de l'utilisateur |

Si un critère « perdus », « accidents » ou « bloqués » échoue : ne pas lancer la porte A.
Relire alors le motif dans le journal (sens des PBS, position de T2 par rapport à la file de
l'hôte, dépôt choisi pour l'entretien), corriger, puis relancer le smoke.

## 8. Étapes suivantes (non codées)

1. Plusieurs greffes par hôte : les cantons de l'hôte sont relus en tenant compte des
   aiguillages déjà posés.
2. Greffe sur une double voie V190 / Cas 2 indépendante, pas seulement sur RAIL-LOOP.
3. Gares partagées à plusieurs quais quand B sature (débit du quai : 30 / temps de séjour par
   rame).
4. Planificateur intégré au portefeuille. Aujourd'hui RAIL-NET compare lui-même greffe et ligne
   simple puis s'efface : il ne retire pas le candidat ligne simple du vivier.
