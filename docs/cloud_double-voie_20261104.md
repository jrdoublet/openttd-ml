# Double voie et signalisation — revue cloud du 4 novembre 2026 (Prompt 1)

Sujet : « double-voie ». Pourquoi OpexAI ne fait-il pas circuler plus de deux trains par ligne,
alors que c'est le premier écart avec AAAHogEx ?

Session cloud **sans Docker ni OpenTTD** : rien n'a été joué en moteur. Les chiffres viennent de
`docs/cloud_pack_20261104/` (campagnes, graines, journaux agrégés) et des rapports du 3 novembre.
Les références `fichier:ligne` portent sur `ai/OpexAI/` au commit `47395b4`. **Aucun défaut
n'est modifié** : le nouveau réglage `rail_loop` vaut 0. Sa projection OFF redonne, octet pour
octet, les six fichiers câblés.

Source AAAHogEx‑115 : elle n'est pas versionnée (`.gitignore`, licence GPL) et n'a pas pu être
téléchargée ici (serveur de contenu BaNaNaS en TCP 3978 bloqué par le proxy). La comparaison
reprend donc les lectures déjà faites avec leurs références : `docs/v190_eco_20261103.md` §6,
`docs/rail_depot_signal_20261103.md` §2 et `docs/v190_fix_20261103.md` §G.

## 0. Résumé

1. **Aucune des cinq expériences ne réfute l'idée « double voie + plusieurs rames ».** Toutes ont
   échoué sur la mise en œuvre (catégorie b) :
   - V190-FIX a construit **deux voies isolées, une rame par voie**. Par construction, une telle
     ligne ne peut pas dépasser deux trains (`task_rail.nut:755`).
   - V190 et V190-FIX2 ont aussi détruit le portefeuille. Sous V190, l'extension de lignes ne
     s'arrête plus quand une recherche occupe le slot (`task_rail.nut:643`).
     `_startRailUpgradeSearch` (`task_rail.nut:728` → `:1830`) **écrase alors `_railSearch`**,
     y compris un A* de projet en cours ou un plan prêt à construire.
   - FIX2, DOUBLE-GROW et RDS ont buté sur la **géométrie des gorges** : aiguillages près des
     quais, virages à 90°, quai parallèle, embranchement de dépôt.
   - DOUBLE-GROW v2 avait en plus **deux bugs bloquants**, détaillés au §1.
2. **Correction retenue et codée : RAIL-LOOP** (`rail_loop=1`, défaut 0). Un quai OpenTTD est
   traversant. La voie 2 relie donc **l'arrière du quai aval à l'arrière du quai amont**, et la
   ligne devient une boucle à sens unique traversant ses deux gares :
   - aucun aiguillage de gorge, aucun quai neuf, aucun dépôt neuf ;
   - des PBS à sens unique sur les deux voies ;
   - des clones à ordres partagés, jusqu'à 8 rames ;
   - une recherche A* hors du slot `_railSearch`, en tranches bornées.
3. **Banc à lancer sur le PC** (§6) :
   - smoke 1×1 de compilation ;
   - smoke 4×6 rail seul, graines `17 512 314 8191`, avec critères d'exposition physique ;
   - puis portes A 40×5 `gain_short` et B 20×10 `non_erosion`.

## 1. Diagnostic par expérience

Catégories : (a) idée réfutée ; (b) implémentation défaillante ; (c) mesure non concluante.
Points de comparaison du pack, mêmes quatre graines × 6 ans, bras ON :

| Campagne | `RAIL_SEARCH` | `RAIL_BUILD` | `search_in_progress` |
|---|---:|---:|---:|
| `rds_failclosed_smoke_4x6` (≈ référence, RDS non exposé) | 377 | 351 | 236 |
| `rail_pair_smoke_4x6_r4` | 373 | 350 | 251 |

### 1.1 V190-FIX indépendant (`v190_rail_double_build=1,v197_guided_double=1`)

**Verdict : (b), et (c) pour l'idée.**

**Plafond de deux trains par construction.**
- Chaque double se compose de deux voies **isolées et bidirectionnelles**, avec une rame chacune
  (`docs/v190_fix_20261103.md` §C).
- L'extension par clonage les exclut explicitement (`task_rail.nut:755`, `v190Independent`).
- `V190_RAIL_MAX_TRAINS <- 4` (`globals_pre.nut:141`) ne sert qu'aux boucles V181.
- « Jamais plus de deux trains par double » est donc le comportement codé, pas une limite
  découverte au banc.

**Effondrement du portefeuille.** Pack `logs_v190_fix_independent_4x6`, comparé à la référence :

| Mesure | V190-FIX | Référence |
|---|---:|---:|
| `RAIL_SEARCH` | 524 | ≈ 377 |
| `RAIL_BUILD` | 301 | ≈ 351 |
| `search_in_progress` | 400 | ≈ 236 |

Deux mécanismes de code expliquent l'écart.

- **Écrasement du slot de recherche.**
  - Avec V190 actif, `_expandRailLines` ne rend plus la main quand `_railSearch != null`
    (`task_rail.nut:643`, « OFF: conserver EXACTEMENT l'exception V190 »).
  - Les lignes simples issues des replis V190 passent alors par le « Cas 2 »
    (`task_rail.nut:706-728`) : 96 événements `fallback_single` sont journalisés dans ce 4×6.
  - Ce cas appelle `_startRailUpgradeSearch`, qui **affecte `this._railSearch = {kind="upgrade"}`
    sans test** (`task_rail.nut:1830-1841`).
  - Un A* de projet en cours, ou un plan déjà en phase `build`, est alors perdu. Le slot reste
    occupé par une recherche de doublement d'une ancienne ligne.
  - C'est cohérent avec la graine 841478 en 1972 : 89 `RAIL_SEARCH OK`, 0 `PROJECT_CHOSEN`,
    0 ouverture, alors que la caisse monte de 376 à 548 k£ (`docs/v190_eco_20261103.md` §5).
- **Seconde A\* synchrone.**
  - La seconde voie est planifiée **dans** la complétion du plan primaire
    (`builder_rail.nut:4917-4950`), avec tout le budget restant (`remain`) et une échéance de
    `RAIL_SEARCH_SAFETY_TICKS` (`builder_rail.nut:4927-4932`).
  - L'IA est bloquée pendant ce temps, et le plan primaire prend le retard correspondant.

**Le capital n'est pas la contrainte.** En fin de partie, la caisse des bras ON va de 0,35 à
1,39 M£ (`per_seed.csv`). Les doubles coûtent en moyenne 1,98 fois le simple apparié, mais
`docs/v190_eco_20261103.md` §5 établit que la chronologie n'est pas celle d'une caisse épuisée.

**Ce que l'expérience ne dit pas.** Les 32 rames des doubles ont produit 29 profits positifs.
La double voie elle-même fonctionnait ; c'est son intégration qui a coûté −318 k£/an. Rien ne
mesure une double **à plus de deux rames** : l'idée n'est pas testée (c).

### 1.2 V190 directionnel (`v190_fix_directional=1`)

**Verdict : (b), géométrie de gorge et même écrasement de slot.**

Le pack `logs_v190_fix2_directional_orchestrated_4x6` compte :
- `build_double OK` = 6 événements, soit 3 doubles (chaque double est journalisée deux fois) ;
- 24 `TRK2FAIL`, 20 `NOPATH2`, 10 `LOOPFAIL`, 20 `NOPLATFORM_*`, 4 `pair_reject` ;
- `search_in_progress` = 569, pour **273** `RAIL_BUILD`.

Sur `v190_fix2_safe90_wp_diag_3x6`, les graines 512 et 841478 ON finissent avec **23 et 18
véhicules** contre 50 et 57, et 40 et 28 gares contre 71 et 82, malgré 0,9 à 1,6 M£ en caisse.

Pourquoi la géométrie échoue :
- Les deux aiguillages A et B doivent tomber entre `clear+2` et `clear+26` cases des quais
  (`v190_fix_directional.nut:357-359`).
- C'est précisément la zone encombrée : quais parallèles, dépôt, leads.
- `pf.forbid_90_deg=1` y interdit les transitions trouvées (§J.2 du rapport V190-FIX).

Les six rames de trois doubles sûres étaient toutes bénéficiaires. Le mécanisme directionnel
marche donc **quand** la gorge est constructible ; il n'est pas réfuté.

### 1.3 DOUBLE-GROW v1 (`double_grow=1`)

**Verdict : (b), stratégie géométrique inadaptée et garde de caisse.**

- **Bande parallèle stricte inconstructible.** La bande décalée d'une case est occupée près des
  gares par le quai, le dépôt historique, la sortie et des voies rivales (`finaldiag` :
  `clear_forbidden=primary_depot`, `site_occupied` 8/8). D'où 9 diagnostics et
  0 double (`NO_PARALLEL_BAND`).
- **Garde de caisse de 750 k£** (`double_grow.nut:31`). Elle s'applique avant tout examen,
  alors que la caisse ne dépasse 250 k£ qu'en 1973-1974 (rapport DOUBLE-GROW).

Le doublement différé n'est pas réfuté : c'est le tracé « collé à la voie 1 » qui ne passe pas.

### 1.4 DOUBLE-GROW v2 (`double_grow=2`)

**Verdict : (b), deux bugs bloquants identifiés.**

**Bug 1 — le refus de caisse arrête tout le balayage.**
- Le sélecteur fait `return false` au premier refus (`double_grow_v2.nut:115-124`), **sans
  avancer le curseur**.
- La même ligne chère est donc ré-examinée à chaque passe ; les autres ne le sont jamais.
- Pack `idle_slot` : **356 `skip cash` sur 365 admissions**. Pack `quote_sites` : 176/176.
- Le devis d'admission ajoute en plus la voie entière, deux quais, un dépôt, une rame et une
  réserve de 50 k£ (`double_grow_v2.nut:19-39`).

**Bug 2 — tous les ponts et tunnels sont refusés.**
- Avec `V294_RAIL_CONTINUOUS`, `OpexAdvanceRailPathfinder` rend `structures = []`
  (`builder_rail.nut:2204`).
- `OpexDoubleGrowClear` rejette tout saut sans ouvrage planifié (`double_grow_geometry.nut:616-620`).
- Toute trace passant par un pont ou un tunnel est donc refusée : 4 des 5 `GEOMETRY_FAILED` du
  pack `idle_slot` sont des `clear_structure`.
- `OpexTestRailTrack` (`builder_rail.nut:4318-4321`) traite pourtant correctement l'absence de
  structure planifiée, en déduisant pont ou tunnel du terrain.

**Autres freins.**
- `NO_NATIVE_STATION_SITES` : il faut un quai parallèle libre à chaque bout, la même contrainte
  de gorge qu'en 1.2.
- L'A\* n'avance que si aucun « travail principal » n'est en cours : 8 `pause principal_busy`.

### 1.5 RAIL-DEPOT-SIGNAL (`rail_depot_signal=1`)

**Verdict : (b) pour la version exposée, (c) pour la version fail-closed.**

- 26 des 124 rames ON étaient perdues, toutes sur les embranchements PBS.
- Les ablations montrent que les trois PBS autour de l'embranchement empêchent la récupération
  YAPF (`docs/rail_depot_signal_20261103.md` §9.1).
- La version fail-closed n'expose **aucun** embranchement :
  `OpexRailDepotSignalSpurRoutingCertified()` renvoie `false` (`rail_depot_signal.nut:15-18`).
- Le 40×5 à −12 k£ (p = 0,47) ne mesure donc rien du levier.

Leçon pour la double voie : **ne pas créer d'embranchement de dépôt neuf**. RAIL-LOOP garde le
dépôt primaire tel quel et lui ajoute au plus la courbe de sortie aval.

### 1.6 RAIL-PAIR (`rail_pair=1`)

**Verdict : (a) pour « plus de rames sur voie unique », avec une exposition faible (c).**

- 3 tandems sur 4 graines, −120 k£/an (1V/3D).
- Résultat cohérent avec V271b (−70 k£ à 10 ans) et V202k (35 évitements, −27 k£).
- Deux rames sur une voie unique se gênent : la capacité de la voie, pas le nombre de quais,
  limite le débit.
- Cela confirme qu'il faut **deux voies orientées**, ce que vise RAIL-LOOP.

## 2. Ce que fait AAAHogEx (lectures documentées, sans copie de code)

- **Double voie orientée avec PBS à sens unique** environ toutes les 7 cases : 391 à 807
  `PBS_ONEWAY` par graine en décembre 1975 (`docs/v190_eco_20261103.md` §6).
  - Points d'entrée signalés : `railbuilder.nut:1103-1105`, `1214-1227` et `1513-1525`.
  - Deux trajets distincts `pathSrcToDest` / `pathDestToSrc` (`trainroute.nut`).
- **Gares de 2 à 3 quais × 7 cases** (`station.nut:1518-1558`, `1601-1642`).
- **Dépôt hors tracé**, accès vérifiés (`BuildDepotForRail`, `tile.nut`).
- **Croissance de flotte avec le trafic.** Service `rail|22,34` (graine 512) : 2 rames en octobre
  1974, **9 en décembre 1975** ; un train construit puis cloné à ordres partagés
  (`trainroute.nut:970-1008`).
- **Choix simple ou double** par comparaison de deux offres (`estimator.nut:1767-1811`).

**Comment AAA évite le goulot de recherche.** Les rapports existants n'attestent rien de
directement lisible ici. Un écart structurel est en revanche certain : AAA n'utilise jamais
d'aiguillage de gorge « inventé » après coup. Ses points de raccordement sont posés avec la
gare.

## 3. Corrections proposées, classées par gain attendu / risque

| Rang | Correction | Gain attendu | Risque | État |
|---:|---|---|---|---|
| 1 | **RAIL-LOOP** : voie 2 de l'arrière du quai aval vers l'arrière du quai amont, boucle à sens unique traversant les deux gares, PBS_ONEWAY, flotte de 2 à 8 rames | Élevé : attaque directement le plafond d'environ 1,2 train par ligne, sur des lignes déjà rentables, avec la caisse qui dort après 1973 | Moyen : comportements moteur non vérifiés ici (§5) ; exposition dépendante d'arrières de quai libres | **Codé**, `rail_loop=1`, défaut 0 |
| 2 | **Garde du slot sous V190** : ne jamais appeler `_startRailUpgradeSearch` si `_railSearch != null` (`task_rail.nut:706-728`), et sortir la seconde A\* V190 de la complétion synchrone | Moyen : rend V190 et FIX2 enfin mesurables sans destruction du portefeuille | Faible | Non codé : V190 n'est plus la voie recommandée. Correctif : ajouter `if (this._railSearch != null) continue;` juste avant `OpexPrepareUpgradeSearch` |
| 3 | **DOUBLE-GROW v2 réparé** : avancer le curseur au refus de caisse, et dans `OpexDoubleGrowClear` accepter un saut sans structure planifiée quand `OpexTestRailTrack` l'a construit | Faible à moyen : reste limité par `NO_NATIVE_STATION_SITES` | Faible | Non codé ; deux lignes chacun |

La correction 1 évite chacune des causes d'échec du §1 :

| Cause d'échec | Réponse de RAIL-LOOP |
|---|---|
| Gorge (1.2, 1.3, 1.4) | Aucun aiguillage : la voie 2 entre et sort par les extrémités **déjà droites** des quais existants |
| Quai parallèle (`NOPLATFORM`, `NO_NATIVE_STATION_SITES`) | Aucun quai neuf |
| Embranchement de dépôt (1.5) | Dépôt primaire inchangé, plus au besoin une courbe de sortie aval ; un PBS de garde entre la gare amont et le dépôt interdit la sortie à contre-sens |
| Slot `_railSearch` (1.1, 1.2) | État propre `_railLoopState` ; tranche de 200 itérations par passe d'ordonnanceur, budget de 8 000 ; ne lit ni n'écrit jamais `_railSearch` (contrat testé) |
| Caisse (1.3, 1.4) | Devis ≈ 1,5 × longueur de voie 1 + une rame ; un refus reporte la ligne de 60 jours et **le balayage continue** (contrat testé) |
| Voie unique (1.6) | Deux voies, sens unique, autant de cantons que de signaux |

## 4. Code livré (réglage `rail_loop`, défaut 0)

### Fichiers

| Fichier | Contenu |
|---|---|
| `ai/OpexAI/rail_loop.nut` | Module neuf |
| `info.nut`, `globals_pre.nut`, `settings.nut`, `main.nut`, `task_rail.nut`, `scheduler.nut` | Câblage, chaque appel gardé par `RAIL_LOOP &&` |
| `sweeps/rail_loop_off.py` | Projection OFF stricte, appelée en tête de `invest_stall_diagnostic_off.py`, donc retirée en premier par toutes les chaînes historiques |
| `sweeps/test_rail_loop_20261104.py` | 20 contrats |
| Six tests d'inventaire | Plafond d'`AddSetting` passé de 93 à 94, avec justification |

### Machine d'état

**Sélection mensuelle** (`OpexRailLoopSelect`, en tête de `_expandRailLines`) :
1. D'abord la **croissance** des boucles certifiées : une rame si la cargaison en attente à la
   source atteint la capacité d'une rame, si la ligne est rentable et si au plus `cap` rames
   circulent. `cap = cantons − 2`, plafonné à 8, au plus une rame tous les 45 jours.
2. Sinon, **admission** d'une ligne fret :
   - une seule rame, simple voie, âgée d'au moins 180 jours, rentable ;
   - une rame pleine de cargaison en attente ;
   - devis finançable.

**Démarrage** (`OpexRailLoopBegin`) : contrôles fail-closed avant toute dépense, chacun avec son
motif journalisé.
- La voie 1 doit se retracer exactement (`OpexDoubleGrowPrimaryRoute`, puis
  `OpexDoubleGrowVerifyRoute`).
- Quais non partagés avec une autre ligne.
- **Sens imposé par le dépôt** : la courbe existante doit être amont.
- Front de dépôt droit ; courbe de sortie aval posable (test en `AITestMode`, sous bouclier
  `AIAccounting`) ; case signalable pour le PBS de garde.
- Aucun `PBS_ONEWAY` déjà posé à contre-sens.
- Case arrière de chaque quai libre et plate.
- Le pathfinder part de l'arrière du quai aval et vise l'arrière du quai amont. Il ignore la
  voie 1, les quais, les leads et le dépôt.

**Étapes** (`OpexRailLoopStep`, à chaque passe de `_runNextTask`) :
1. **Recherche** : une tranche A\* de 200 itérations.
2. **Pose de la voie 2** (`OpexRailLoopBuildTrack2`), dans cet ordre :
   - certification : extrémités exactes, cases d'extrémité simples, trace dédiée, aucune case
     protégée, aucun virage à 90°, test natif `OpexTestRailTrack`, caisse ≥ voie + une rame ;
   - pose des **cases intérieures** ;
   - pose des **PBS_ONEWAY** ;
   - pose **en dernier des deux raccords aux quais**. La voie 2 n'est jamais atteignable sans
     son sens unique ; un échec avant raccordement démolit seulement la voie 2.
3. **Armement de la voie 1** (`OpexRailLoopArm`) :
   - uniquement quand **toutes les rames roulent vers la gare aval** (ordre courant), donc dans
     le sens des futurs PBS ;
   - pose la courbe de sortie du dépôt, le PBS de garde puis la série de PBS ;
   - en cas d'échec, retire les PBS et la courbe posés.
4. **Certification** : `railLoop=2` et clonage immédiat d'une deuxième rame.

**Échec** : après raccordement, rien n'est démoli, car une rame peut rouler sur la voie 2. La voie
2 reste une voie de retour à sens unique, sûre pour une rame unique. La ligne n'est plus
représentée.

**Persistance** : `railLoop`, `railLoopTrack2`, `railLoopFlow`, `railLoopPbs2`, `railLoopCap`,
`railLoopNextGrow`. Après un Load, une voie 2 posée mais non armée reprend en armement ; une
recherche perdue redevient admissible 30 jours plus tard.

**Journal** : `OpexDecide("RLOOP", "phase=…")` sous `decision_log` ou `--probes 6`, avec les
phases `search`, `reject reason=…`, `defer`, `cash`, `track2`, `fail reason=…`, `resume`,
`commit`, `grow`. Le tag historique `RAIL_LOOP` reste réservé à la conversion V181
(`builder_rail.nut:7192`).

### Validations faites dans cette session

- `python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` : **3 387 tests**,
  4 échecs et 13 erreurs, **identiques à la référence d'avant intervention**, aucun nouvel échec.
  Les 17 sont préexistants dans cette session :
  - `test_b6_portfolio_causality` : échec connu ;
  - deux `test_rail_long_v3_multi` ;
  - quatorze `test_v166_aaahogex_settings` : `ai/AAAHogEx-115/info.nut` absent du clone cloud ;
  - `test_v279_reselect_memo` : erreur d'environnement.
- `test_rail_loop_20261104.py` : **20/20**. Il couvre notamment :
  - la projection OFF égale aux SHA d'avant intervention ;
  - l'échec franc d'un hunk modifié ou dupliqué ;
  - l'ordre « intérieur → PBS → raccords » ;
  - l'armement après `ArmSafe` ;
  - l'absence de démolition dans `Fail` ;
  - le non-accès à `_railSearch` ;
  - **l'existence et l'arité de chacun des 44 `Opex*` appelés**. Un test de mutation confirme
    que le contrôle détecte une arité fausse et un nom inconnu.
- `git diff --check` : propre.
- **Non fait : compilation Squirrel.** Aucun compilateur n'est disponible ici ; la compilation
  du module tiers a été refusée. Le smoke 1×1 du §6 est donc **la première exécution réelle**.

## 5. Risques moteur non vérifiés, à regarder au smoke

1. **Orientation des PBS** : convention `front = case amont`, reprise telle quelle
   d'`OpexV190Fix2PlaceSignal`. Elle a été validée en moteur par V190-FIX2 : six rames
   bénéficiaires, aucun `Lost` sur 512 (§J.3–J.4).
2. **Traversée de quai.** Les rames entrent par l'avant du quai aval et ressortent par
   l'arrière. Les ordres existants sont `OF_NON_STOP_INTERMEDIATE` (`builder_rail.nut:4517`) :
   une rame traversant une gare qui n'est pas sa destination ne s'y arrête pas. À vérifier : la
   rame ne rebrousse pas en gare. Le rebroussement passerait un PBS_ONEWAY par l'arrière, ce
   que YAPF doit refuser.
3. **Entretien au dépôt** : entrée par la courbe amont existante, sortie par la courbe aval
   ajoutée. À vérifier : aucune rame `Lost` près du dépôt.
4. **Exposition.** Les arrières de quai libres et plats sont de fréquence inconnue. Le
   histogramme `RLOOP phase=reject reason=back_lead_A|back_lead_B` le dira. Prochain correctif
   si besoin : prolonger le quai d'une case ou décaler le lead.
5. **Interblocage** : `cap = cantons − 2` laisse au moins deux cantons libres sur la boucle. À
   vérifier sur les sauvegardes : aucun canton plein durablement.
6. **Interaction C41** : la réparation de raccord sur `VehicleLost` ne doit pas toucher les
   lignes en boucle. À surveiller dans les journaux.

## 6. Plan de bancs pour le PC (PowerShell, depuis la racine du dépôt)

Le code est sur la branche `ccr-6d627d08-tlnphk` (commit de cette session, poussé). Selon
AGENTS.md §3, l'utilisateur travaille sur `master` : fusionner ou extraire la branche relève de
sa décision. **Le défaut reste `rail_loop=0`.**

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_loop=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
$common = @('--mount-root','C:\Users\jr\vscode\openttd-ml\openttd-ml',
            '--cpus','10','--memory','8g','--max-workers','10',
            '--start-year','1970','--map-size','8','--repeats','1','--primary-metric','profit_year')

# 0. Contrats (aucune partie)
python -X utf8 -m unittest discover -s sweeps -p 'test_rail_loop_20261104.py'

# 1. Smoke de compilation et d'exécution 1x1 (solo)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[rail_loop=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/rail_loop_smoke_1x1_20261104.json

# 2. Smoke physique 4x6 rail seul (diagnostic, garde de valeur neutralisée)
python -X utf8 sweeps/run_c66_reference.py --campaign rail_loop_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id rail_loop `
  --reference $ref --variant $on --decision-rule gain_short --min-useful-primary-delta-pct 4 `
  --required-seeds 4 --required-years 6 --years 6 --seeds 17 512 314 8191 `
  --probes 6 --script-debug --line-telemetry --line-telemetry-monthly `
  --retain-savegames results/rail_loop_smoke_4x6_20261104_saves `
  --value-guard-max-loss-pct 100 --out results/rail_loop_smoke_4x6_20261104.json @common @aaa
```

### Critères d'exposition physique du smoke 4×6

À lire dans `results/rail_loop_smoke_4x6_20261104_engine/*.log` (bras ON), dans la télémétrie
de ligne et dans les sauvegardes.

**Conditions toutes exigées avant la porte A :**

| # | Critère | Où le lire |
|---:|---|---|
| E1 | ≥ 1 `RLOOP phase=commit` **par graine** | `grep -c "RLOOP phase=commit"` par journal ON |
| E2 | ≥ 1 ligne par graine à **≥ 3 rames** | `RLOOP phase=grow`, puis `line_telemetry` `vehicles ≥ 3` sur cette ligne |
| E3 | **0 rame perdue sur les lignes en boucle** | Sauvegardes : `PathfinderLost` / `ET_VEHICLE_LOST [0]` ; décodeur `results/rail_depot_signal_20261103/analyser_sauvegardes.py` |
| E4 | Toutes les rames des boucles ont un profit **> 0** après 6 mois de service | `line_telemetry`, `vehicle_financials` |
| E5 | Portefeuille non dégradé : `RAIL_BUILD` et `search_in_progress` ON à ±10 % de OFF | Comptes `RAIL_BUILD` / `PROJECT_DISCARD reason=search_in_progress` |
| E6 | `game_ok` 8/8, aucune erreur NoAI | Manifeste, journaux |

**Si E1 échoue**, lire l'histogramme `RLOOP phase=reject reason=*` et `phase=fail reason=*`.
`back_lead_*` majoritaire → prolonger le quai ou décaler le lead. `depot_flow` ou
`depot_front_curve` → dépôt sur une case droite. `astar_*` → budget. **Si E3 échoue**,
autopsier l'emplacement des rames perdues dans les sauvegardes avant tout autre banc.

### Portes économiques, seulement si E1–E6 tiennent

Le prompt demande une porte A 40×5 (`--required-years 5 --years 5`). Le protocole V102 de
CLAUDE.md fixe la porte A à 40×3 : pour une adoption, remplacer `5` par `3`.

```powershell
# Porte A — 40 graines canoniques x 5 ans, gain_short
python -X utf8 sweeps/run_c66_reference.py --campaign rail_loop_gain_short_40x5_20261104 `
  --policy-id reference --variant-policy-id rail_loop --reference $ref --variant $on `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 `
  --required-years 5 --years 5 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_loop_gain_short_40x5_20261104.json @common @aaa

# Porte B — 20 graines canoniques x 10 ans, non_erosion (si A passe)
python -X utf8 sweeps/run_c66_reference.py --campaign rail_loop_non_erosion_20x10_20261104 `
  --policy-id reference --variant-policy-id rail_loop --reference $ref --variant $on `
  --decision-rule non_erosion --min-useful-primary-delta-pct 4 --required-seeds 20 `
  --required-years 10 --years 10 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_loop_non_erosion_20x10_20261104.json @common @aaa
```

Lire le verdict économique (Δ `profit_year` propre d'Opex, V/D, p, IC95, garde de valeur), pas
seulement le ratio Opex/AAA. En plus du verdict, regarder sur les 40 graines :
- le nombre de rames par ligne fret, attendu > 1,2 ;
- la flotte à 5 ans, attendue au-delà de ~55 véhicules ;
- la caisse dormante après 1973.

Un multimodal 20×10 ne vient qu'après les deux portes rail.
