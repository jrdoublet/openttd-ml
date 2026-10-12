# AIR catalogue CD00–CD07 — validation des sources séparées

Le chantier structurel rassemble CD01–05 dans
`OpexAirPlans` et CD06 dans `scheduler_tasks.nut`.
CD00 a gelé les contrats. CD07 retient une seule entrée
globale `catalog` : ni nouvelle `_taskQueue` ni migration
des indices Save/Load. Le lot ne cherche aucun gain économique
et ne réintroduit pas V142/V143.

## Porte diagnostique appariée 40×4, avec sondes symétriques

Le C66.3 gèle un seul répertoire OpexAI. Deux arbres de code
distincts ne peuvent pas coexister sous le même nom
`OpexAI` dans une unique partie OpenTTDLab (risque de
remplacement silencieux du chemin source). Deux campagnes
mono-politique **successives** sont donc rapprochées
strictement par graine, horodatage final et configuration.

Populations : 10 graines
`42 100 7 999 2026 1 17 73 314 512`, puis les
30 graines complémentaires canoniques. Source de référence
`results/cd_baseline_stage_20261012` (HEAD `a09a7b2`),
variante `results/cd_combined_stage_20261012`, dérivée du
même HEAD avec CD01–06. Chaque camp utilise exactement le
même AAAHogEx figé, `probe_loop_ops=1` et
`--script-debug`, 4 ans, 10 CPU / 10 workers maximum,
**aucun Docker simultané**.

Comparateur : `sweeps/compare_cd_cross_tree_c66.py` puis
`sweeps/aggregate_cd_cross_tree.py`. Il exige une source
adverse identique, des bibliothèques/versions/options
identiques, un changement de source OpexAI attendu,
une santé complète, les paires exactes et des dumps
annuels LOOP_OPS non vides et synchronisés.

Résultat **40/40 paires saines** :
- profit terminal variante−référence **−4 389,2 £/an**
  (−0,234 %), IC95 bootstrap **[−77 637 ; +65 790]**,
  22 hausses / 18 baisses ;
- valeur entreprise **+1 050 £** (+0,020 %),
  IC95 [−169 860 ; +165 366] ;
- LOOP_OPS 1970–1971 **−4 826** (−0,0038 %),
  IC95 [−227 979 ; +219 322] ;
- LOOP_OPS 1970–1972 **+362 455** (+0,1884 %),
  IC95 [−1 268 967 ; +2 080 063],
  21 hausses / 19 baisses.

Ces résultats ne démontrent **ni une perte significative ni
une stricte égalité**. La faible hausse opcode moyenne
sur une fenêtre ne peut être requalifiée automatiquement
en « gain » ou en « régression structurelle » : elle est
principalement compatible avec la variabilité des
trajectoires. Aucun effet économique positif n'est
promis par l'extraction.

## Porte indépendante préenregistrée B20×10 : économie sans sonde

Exécuter deux C66.3 mono-politique séquentiels, mêmes sources
que la porte précédente, **sans** `probe_loop_ops` actif
et sans `--script-debug`. L'horizon terminal est 1979.
Vingt graines inédites, générées par
`random.Random(20261013).randrange(2**31)`, en excluant
les 40 graines du diagnostic et les 20 de l'expérience
AC04-A B :

`1963387146 830507039 1408425178 2034226161 416523699
1782306345 229354457 1017947981 316355598 80387861
950196877 448764950 1073424914 553728032 862964756
1940583833 2102004328 657551918 200536595 597921439`.

Critère de non-érosion économique préenregistré :
**20/20 paires saines**, IC95 bootstrap apparié
du profit annuel dont **la borne supérieure ≥ 0**,
ratio de moyennes de valeur de compagnie **≥ 0,95** ;
ne pas exiger un gain de profit positif pour une
refactorisation structurelle. Le test du profit ne
prouve pas équivalence stricte : publier moyenne,
intervalle et signes. En cas de baisse économiquement
établie, ne pas adopter le lot complet ; isoler la
phase responsable plutôt que nier le signal.

Cette porte est indépendante de la correction AC04-A v3
qui a été validée séparément. L'activation AC04-A par
défaut sur master et toute modification C121 en cours
ne doivent pas contaminer ces snapshots CD construits
depuis le même HEAD original.

## Verdict de qualification et intégration — 12 octobre 2026

**CD01–CD06 ACCEPTÉS selon le contrat utilisateur d'absence de dégradation
démontrée, et portés dans `master` sans commit ni push.** Le jugement porte
sur le découpage interne du catalogue, et non sur une hypothétique égalité
bit à bit des opcodes ou des trajectoires. CD07 conserve une unique tâche
globale `catalog` ; aucun `dueCycle`, `_taskCursor`, ordre de publication
V141, ni contrat de persistance n'a été refondu.

### Porte B indépendante : désormais achevée et vérifiée

Le calcul reproductible a été exécuté à partir des deux JSON C66.3 avec
`sweeps/compare_cd_cross_tree_c66.py --economic-only` ; résultat :
`results/cd_combined_B20x10_20261012_r1_comparison.json` **dans le
worktree `results/cd_combined_stage_20261012`**. Les 20 paires inédites
ont toutes terminé dix ans avec économie couverte, même seed/repeat,
config effective, versions et AAAHogEx source ; les empreintes OpexAI
sont volontairement distinctes. Profit terminal variante−référence
**+70 240,2 £/an** (**+2,436 %**), médiane +122 898,
**12 hausses / 8 baisses**, IC95 bootstrap apparié
**[−73 286,4 ; +203 040,45]**. Valeur de compagnie
**+299 567 £** (**+1,9949 %**), 13 hausses / 7 baisses,
IC95 **[−159 557 ; +762 847]**. Le critère préenregistré est rempli :
borne supérieure du profit >= 0, ratio des valeurs >= 0,95 et 20/20
paires saines. **Absence de perte démontrée, pas preuve d'équivalence**.

### Attribution opcode VM

40 paires inédites ou complémentaires à horizon quatre ans, années
`LOOP_OPS` **1970–1972** seules clôturées : **+362 455 opcodes globaux**
en moyenne (+0,1884 %), IC95 bootstrap
**[−1 268 967 ; +2 080 063]**, 21 hausses / 19 baisses. Sur
1970–1971 : **−4 826 opcodes** (−0,0038 %), IC95
[−227 979 ; +219 322]. Le collecteur des postes disjoints
`sweeps/analyse_cd_phases_20261012.py` (dans le worktree CD combiné)
retrouve la somme globale et ventile notamment `orchestrator`
**+1 293 850** et `catalog_continuation` **−816 487** opcodes,
mais leurs IC95 franchissent zéro ; ce sont des changements de charge
de trajectoire, pas le coût intrinsèque d'un appel CD prouvé.

**Limite des phases AIR :** les anciennes campagnes C40×4 ont activé
`probe_loop_ops`, **pas de `AIR_LIGHT` exploitable**. Le champ
`air_light_coverage.measured=false` du nouveau diagnostic signale des
phases **non mesurées**, jamais une différence nulle. Une campagne
spécifique avec sondes symétriques serait nécessaire pour attribuer
les coûts de `sites`, `new_pairs`, `hub_site`, `hub_hub` séparément ;
elle n'est pas indispensable au verdict global ici et n'a pas été inventée.

### Exécution et reprise après intégration

- Dans le worktree CD+AC04-A-v3 : **682/682 tests AIR** et les
  **39 tests CD/AC ciblés** passent ; les fonctions CD sont des sous-étapes
  explicitement appelables, sans nouveau yield ; tests de `scanIndex`,
  `rankIndex`, `a/b`, `hubSiteI/J`, `hubHubI/J`, publication/apply V141
  et version V93 conservés.
- Save/Load **moteur OpenTTD réel sous Docker 3 CPU/2 Go**, graine 512,
  deux années A puis une année B, réussi sur le worktree CD seul puis
  sur le worktree CD+AC04-A-v3. **25 sauvegardes A, 13 B**, reprise
  `000000011.sav` datée 1971-01-01, **`LOAD_RECONCILE` détecté**,
  aucune erreur moteur, 8→35 gares, 13→50 véhicules. Réserve connue :
  compagnie fantôme inactive du harnais, indépendante de l'IA mesurée.
- Portage sur `master` de **`ai/OpexAI/air_planning.nut`** et
  **`ai/OpexAI/scheduler_tasks.nut`** exclusivement pour le découpage,
  plus les tests de non-régression CD concernés. Les deux fichiers
  provenaient du stage de réconciliation intégrant déjà AC04-A v3 ;
  les nettoyages C121 concurrents n'ont pas été recopiés depuis le stage.
  Suite `test_*air*.py` **682/682 PASS** sur le `master` après adaptation
  de la fixture CD00 aux transactions CD06.
- Save/Load **moteur réel sur `master` intégré** :
  `results/cd_master_saveload_seed512_2p1_20261012.json`, statut OK,
  25+13 sauvegardes, `LOAD_RECONCILE` positif, aucune erreur moteur,
  même reprise effective 8→35 gares et 13→50 véhicules.

La découverte, les filtres et l'économie C121 existants sont conservés.
Les deux fonctions métiers du driver et les transactions CD06 restent
sous l'unique ordonnanceur C78 ; **autonomie fonctionnelle par sous-étapes,
pas huit nouvelles entrées globales `_taskQueue`**. V142 et V143 restent
rejetées. Un A/B de l'ensemble de l'arbre *courant* incluant les retraits
C121 concurrents n'a **pas** été effectué : les preuves A/B qualifient
précisément les deux arbres gelés basés sur `a09a7b2`, et les contrôles
moteur ultérieurs vérifient leur coexistence avec les changements locaux,
sans transformer cela en nouvelle prétention d'équivalence économique.

## Contrôle final de reprise et archive durable (12/10, après intégration)

La suite générale du `master` complet, après portage CD, AC04-A v3 et
nettoyages C121 locaux, a exécuté **1 963 tests Python : 1 963 PASS**
(dont deux nouveaux tests de reproductibilité B20×10/C40×4 sur l'archive).
Un premier passage comportait un unique échec :
`test_parallel_fleet_amort_shadow.SourceTests.test_preexisting_builder_entirely_preserved`
utilisait une empreinte SHA256 **déjà obsolète au HEAD a09a7b2**.
`ai/OpexAI/projects_builders.nut` n'a pas changé ; seul le hash figé du
test a été réépinglé à la valeur réelle de référence
`b468ea6a580cf99188c72e4531cbc43efbc20be8752432dabcc0497cd40c49ec`.
L'assertion d'intégrité du code hors helper est toujours active.
`git diff --check` reste propre. Aucune nouvelle campagne Docker n'a
été nécessaire pour cette correction strictement hôte.

Les **20 artefacts bruts, manifestes et comparaisons**, plus leur README,
sont désormais copiés durablement sous
[`evidence/review/air_catalogue_cd_20261012`](../evidence/review/air_catalogue_cd_20261012/README.md)
(environ 3,1 Mo, sans les logs moteur volumineux). Les scripts de
reproductibilité économique ont été conservés dans `sweeps/`.
Le comparateur B20×10 relancé **sur les copies de l'archive** a reproduit
un JSON de comparaison **strictement identique octet pour octet**.
Les logs opcode détaillés restent dans les worktrees source, mais les
**80 compteurs annuels source VM** sont également archivés sous
`cd_combined_C40x4_20261012_opcode_annual_raw.json`. La commande
`python -X utf8 sweeps/verify_cd_opcode_archive.py` recalcule et
contrôle hors Docker **chaque delta annuel et agrégé des 40 graines**,
incluant +362 454,8 opcodes, +0,188438 % et 21 hausses/19 baisses.
La ventilation déjà calculée est archivée et précise son absence de
mesures `AIR_LIGHT`. Toutes les références au statut « à faire » de CD00–CD07
dans le plan historique sont désormais explicitement marquées closes.

**Livraison locale finale : code CD01–CD06 portés, tests et rapports
archivés, architecture CD07 inchangée ; aucun commit ni push.**

**Concurrence Git observée lors du contrôle final :** un autre commit
`5e6fe47` (« Remove superseded C121 cadence and realization parameters »)
a avancé `master` pendant cette qualification, sans inclure nos sources CD.
Le dernier passage **1 963/1 963 tests verts**, daté après ce commit,
qualifie aussi leur coexistence en test hôte. La branche locale était
alors **ahead 1 / behind 14** de `origin/master` ; aucune opération de
merge/rebase/pull/push n'a été tentée sur cet état divergent et sale.
