# Fusion RAIL vers master — 5 novembre 2026

## Portée et précautions

- Référence distante après `git fetch origin` : `origin/master` = `44d9313eab12e08685ac1bf0cc6254fe0257ba4d`.
- Branche source locale `ccr-6d627d08-tlnphk` = `056dae12a67b15ae1dedca43493ec9035578cb48`, contenant notamment RAIL-LOOP défaut 1, RAIL-FILL défaut 0 et V257-DEMAND défaut 1.
- Worktree neuf de fusion : `.wt_merge_master_20261105` sur `merge/rail-20261105`. Checkout principal et `.wt_rail_loop_20261104` volontairement laissés intacts (notamment les travaux RAIL-LOOP v2/v3, INVEST-STALL et RAIL-KEEP non committés).
- Worktree de référence séparé : `.wt_origin_master_baseline_20261105` détaché de `origin/master`, avec copie non suivie de `ai/AAAHogEx-115`.

## Référence avant fusion (origin/master seul)

Commande : `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'`.

Résultat constaté : **3 563 tests ; 123 FAIL ; 17 ERROR ; 9 skipped ; 2 expected failures** (71,379 s). Ces 140 cas préexistants ne sont pas à attribuer à la fusion et doivent être comparés nominativement aux résultats du worktree fusionné. Journal : `%TEMP%/origin_master_44d9313e_suite_20261105.log`.

## Fusion et garde-fou de publication

Commande : `git merge --no-ff --no-edit ccr-6d627d08-tlnphk`.

La fusion automatique a signalé **21 fichiers conflictuels**, notamment `ai/OpexAI/info.nut`, `settings.nut`, `globals_pre.nut`, `builder_rail.nut`, `candidates.nut`, `economy.nut`, `persist.nut`, `task_rail.nut`, les scripts de projections OFF et leurs tests. Les deux branches contiennent des paramètres complémentaires : ROAD1Y sur master ; RAIL-LOOP/RAIL-FILL/V257-DEMAND sur la branche source. Une résolution « ours » ou « theirs » globale perdrait des fonctionnalités. Tout conflit doit être résolu sémantiquement avant validation.

**Décision de sûreté : aucun push `origin/master` tant que l'ensemble des conflits, tests, compilation NoAI et smokes 1×1 et 4×6 n'a pas été validé.** Pas de force-push. Les validations non encore exécutées ne sont pas présumées réussies.

## À compléter après résolution

- Commit de fusion et liste exacte des conflits résolus.
- Comparaison nominative des échecs avant/après (en conservant les échecs connus sur la référence).
- Smoke 1×1, smoke rail seul 4×6 graines 17, 512, 314, 8191, santé 8/8 et erreurs NoAI = 0.
- Contrôle exhaustif des defaults/projections OFF ROAD1Y et RAIL.
- Verdict push/non-push et hash distant après éventuel fast-forward.

## Qualification intermédiaire de la fusion (08:58–09:01)

Après traitement manuel des 42 blocs conflictuels, les 21 chemins ne sont plus en état *unmerged* dans l'index. Aucun marqueur `<<<<<<<` n'est présent dans les `.nut` vérifiés. Les deux inventaires de réglages ROAD1Y et RAIL figurent dans `info.nut` (157 `AddSetting` distincts recensés) ; `rail_sibling=1`, `rail_open=1`, `rail_loop=1`, `rail_fill=0`, `v257_demand=1`, `road1y_load_orders=1` et `road1y_spread_stops=2` sont visibles. Un conflit d'interface V233 (`v233Single` contre `railLongFill`) a nécessité de réconcilier une signature et son appel. Contrats ciblés RAIL-SIBLING 6/6 et RAIL-OPEN 5/5 PASS d'après l'audit de fusion.

Une **suite complète intermédiaire** a été exécutée sur l'arbre résolu, mais **non encore committé** (et susceptible d'une modification très ponctuelle du test V257 pendant le démarrage du banc) : `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'`. Résultat : **3816 tests, 213 FAIL, 19 ERROR, 13 skipped, 2 expected failures, 84,705 s**, journal `%TEMP%/merge_rail_20261105_precommit_suite.log`. Comparée au master propre : 3563 tests, 123 FAIL, 17 ERROR. Les sorties comportent notamment deux erreurs nouvelles `test_invest_stall_20261103.TestInvestStall.test_strict_projector` et `test_v269_rail_late_relax.TestV269RailLateRelax.setUpClass`, ainsi que de nombreux échecs des empreintes/projections OFF historiques. Comparaison préliminaire des lignes d'incidents : 87 non communes au baseline, sans préjuger du nombre de tests ajoutés ni de la cause exacte. Les suites ne sont donc **pas validées**.

Les projections strictes `road100_off_projection.py` (ancrages textuels ROAD1Y) et `invest_stall_v2_off.py`/`invest_stall_v3_off.py` (SHA de bundles historiques) ne composent pas directement les ajouts RAIL sur les mêmes sources. Il faut une projection composite justifiée qui restaure strictement les sources attendues, plutôt qu'une modification opportuniste des fixtures. Les fixtures existantes ont été préservées.

La vérification `git diff --cached --check` a également signalé des espaces finaux dans des journaux `.console.txt` historiques apportés par la branche RAIL ; il s'agit de traces brutes à conserver et non d'un correctif du code.

**Verdict : HOLD / NON-PUSH.** Vu les échecs supplémentaires et l'absence de qualification du binaire fusionné, les smoke 1×1 et 4×6 ne constituent pas une porte de publication franchie et ne doivent pas être revendiqués comme réussis. `origin/master` doit rester à `44d9313e` tant que tous les contrôles ne sont pas conformes ; aucune commande `git push` n'a été lancée.

### Analyse nominative et environnement

L'analyse comparée des journaux par identifiant de méthode fait apparaître **118 identifiants communs**, **32 nouveaux cas FAIL/ERROR** (dont deux nouveaux ERROR) et un ancien cas disparu dans le rapport de fusion ; les nombres de sous-tests et de fichiers diffèrent, ce décompte n'est donc pas un calcul direct `213-123`. L'erreur de décodage dans `sweeps/road100_off_projection.py` (lecture sans encodage explicite de `road100_bus_districts_hunks.json` sous Windows) a été isolée : la lecture UTF-8 rend les 33/33 ancrages présents, contre 26/33 avec l'encodage système. Correction minimale `read_text(encoding="utf-8")` appliquée séparément ; la suite de 3816 tests est **antérieure** à cette correction et ne constitue pas sa revalidation finale.

Contrôle Docker à 09:04 : `docker ps` ne peut pas joindre `npipe:////./pipe/dockerDesktopLinuxEngine` (socket absent). Aucun conteneur n'a été arrêté ou relancé ; les smokes 1×1 et 4×6 sont **non exécutables dans cet état**, indépendamment du résultat statique. Cela constitue une deuxième raison autonome de **non-push**.

**Mise à jour du 5 novembre, 09:20 : Docker rétabli.** L'exécutable réellement installé est `%LOCALAPPDATA%/Programs/DockerDesktop/Docker Desktop.exe`. Lancement de Docker Desktop, `docker info` retourne la version serveur 29.8.2 et `docker run --rm hello-world` retourne 0. La procédure de coupure du service et `wsl --shutdown` n'a pas été nécessaire, aucun disque/volume effacé. Les smokes redeviennent possibles, mais restent subordonnés à une source fusionnée figée et qualifiée.

### Tests ciblés supplémentaires et piste de réparation

- `python -X utf8 -m unittest sweeps.test_v257_demand_20261104 sweeps.test_rail_open_contracts sweeps.test_rail_sibling_lot1 -q` : **16/16 PASS** sur l'arbre fusionné courant.
- Après correction d'encodage JSON, `python -X utf8 -m unittest discover -s sweeps -p test_road100_off_projection.py -q` : **2 tests exécutés, 4 sous-échecs** (`candidates.nut`, `globals_pre.nut`, `info.nut`, `settings.nut`). Ce résultat confirme que l'encodage UTF-8 n'explique pas à lui seul l'incompatibilité de la projection avec le bundle combiné.
- Audit de la chaîne `invest_stall_source_off.project_off` : elle passe sur la branche RAIL seule, mais échoue sur le bundle fusionné (`candidates.nut`, `builder_rail.nut`, `po01c_generators.nut`) où les anciennes empreintes de fichiers entiers ne correspondent plus. Les fragments littéraux des anciens projecteurs demeurent individuellement présents après retrait des couches intervenantes, mais la sortie est structurellement différente de l'ancien bundle. La piste de correction est une **projection spécifique au bundle fusionné**, avec empreintes d'entrée et sortie figées et vérifiées, tout en conservant l'ancienne projection fail-closed intacte. Aucun assouplissement général des SHA n'est autorisé.

### Reprise de validation (après rétablissement de Docker)

L'adaptateur ROAD1Y-B2 merge (`road100_off_projection.py`) distingue sous SHA strict le bundle fusionné des anciennes sources et conserve sept hunks RAIL que la fixture ROAD1Y englobait historiquement. Nouveaux contrats de projection ROAD : **6/6 PASS**, anciens contrats ROAD : **2/2 PASS**. Le projecteur INVEST-STALL composite ajoute une nouvelle fixture propre au merge sans changer les témoins historiques : contrats INVEST, platform, diagnostic, origin et merge ciblés PASS. Un contrat de défauts ROAD+RAIL ajoute **2/2 PASS** (157 réglages, aucun doublon, défauts des quatre difficultés).

Nouvelle suite complète sur l'arbre encore non committé : **3 836 tests, 186 FAIL, 17 ERROR, 13 skipped, 2 expected failures**, 91,491 s. Journal `%TEMP%/merge_rail_20261105_after_proj_suite.log`. Baseline `origin/master` : 3 563 tests, 123 FAIL, 17 ERROR. La comparaison exacte des lignes d'échec indique encore **27 nouveaux identifiants** (au lieu de 32 avant ces corrections), principalement dans les chaînes de projections OFF RAIL-OPEN/SIBLING/LONG. Les 17 erreurs de la fusion sont au même total que la référence, mais une égalité de nombres ne garantit pas l'égalité nominative : **porte non passée**. Aucun push.

Correction séparée : l'appel économique V233L conserve `longGood=true`, `railLongFill=false` et `v233Single=true` sur la signature fusionnée ; **5/5 tests V233L-CONSTRUCTIBILITÉ PASS**. Le projecteur RAIL-LONG retire `railLongFill` sans supprimer `v233Single` ; le contrat RAIL-LONG n'a plus que la cascade RAIL-OPEN en échec lors du dernier contrôle ciblé.

### Validation statique finale de la reprise

La dernière cascade restante de `task_rail.nut` provenait du fait que RAIL-OPEN
avait déjà retiré la couche INVEST-STALL platform lorsque son projecteur était
appelé à nouveau. Deux témoins SHA256 exacts ont été ajoutés pour ces deux
états **déjà OFF** (après RAIL-OPEN et après une projection ESTIM complète).
Le projecteur continue à rejeter une couche présente, partielle ou de SHA inconnu.
Les fixtures historiques et les sources de l'IA n'ont pas été modifiées par ce
correctif de projection.

Suite complète relancée sur l'arbre fusionné : `python -X utf8 -m unittest
discover -s sweeps -p 'test_*.py'` : **3 867 tests ; 83 FAIL ; 17 ERROR ;
13 skipped ; 2 expected failures**, 95,985 s, journal
`%TEMP%/merge_rail_20261105_final_suite.log`. Comparaison avec le baseline
`origin/master` (3 563 tests, 123 FAIL et 17 ERROR) par
`sweeps/compare_merge_suite_20261105.py` : **100 incidents communs,
0 incident nouveau et 40 incidents historiques disparus**. La preuve nominative
complète est dans `results/fusion_final_cases_20261105.json`. Les échecs
historiques n'ont pas été modifiés pour rendre la suite artificiellement verte.
Les defaults ROAD1Y et RAIL restent séparés et contrôlés par les contrats
`test_merge_roadrail_defaults_20261105.py`.

Le script de smoke conserve les réglages `rail_sibling=1`, `rail_open=1` de part
et d'autre, ne change que `rail_loop=0,v257_demand=0` dans le bras témoin,
et utilise `--cpus 10 --memory 8g --max-workers 10` avec le montage explicite.

### Compilation et smoke moteur du commit de fusion

- Commit de fusion : `6f57003fb781ab6bdb65fca4fe1321d86f6b43a` (parents `44d9313e`,
  `056dae12` ; co-auteur demandé présent).
- `results/fusion_master_compile_smoke_1x1_20261105.json` : 2 duels de
  1 graine × 1 an, `failed_runs=[]`, 4/4 compagnies saines, pas d'erreur NoAI
  dans les deux journaux moteur. `fail_primary` économique dû à l'égalité,
  sans incidence sur le contrôle de compilation.
- `results/fusion_master_rail_smoke_4x6_20261105.json` : 8 duels
  (4 graines × 2 politiques), 16/16 compagnies saines, `failed_runs=[]`,
  toutes au 1er décembre 1975, zéro occurrence d'erreur fatale NoAI dans les
  8 journaux sous `results/fusion_master_rail_smoke_4x6_20261105_engine`.
  Le smoke ne démontre pas un gain économique : c'est un contrôle de
  construction, chargement et exécution de l'IA fusionnée.
- Images/montage : `openttd-lab:latest` (image
  `sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`),
  `--mount-root C:\Users\jr\vscode\openttd-ml\openttd-ml`, 10 CPU, 8 GiB,
  10 workers. Aucun banc simultané.

Les validations demandées pour la fusion sont satisfaites. Il reste à
vérifier `origin/master` après `git fetch` et effectuer le push fast-forward
seulement si le parent attendu est inchangé ; cette ligne est actualisée
dans le journal au moment du push.
