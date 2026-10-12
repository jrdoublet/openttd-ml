# CD01–CD02 — sous-étapes d'exécution AIR (worktree isolé)

**Date** : 12/10/2026. **Base figée** : `a09a7b2` (`master` au
moment de la création), HEAD détaché dans
`results/cd_air_catalogue_stage_20261012`.
**Statut** : patch expérimental préparé, contrôles hôte uniquement,
**pas de qualification moteur ni d'adoption**. La campagne AC04-v3 a
franchi sa porte économique A40×4 ; B20×10 est encore active et réserve
Docker sur un bundle distinct. Aucune source du worktree principal
ni tâche Docker n'a été modifiée par ce lot.

## Changement effectué

`ai/OpexAI/air_planning.nut` expose maintenant trois unités
d'exécution réutilisables depuis le driver ou depuis un futur
ordonnanceur interne au **même** `catalog` :

| Sous-étape | Entrée et calcul réellement exécuté | Sortie et transition |
|---|---|---|
| `OpexAirPlansStepPrepare(ctx, light)` | Appelle `OpexAirPlansPrepare(ctx)` avec les mêmes traces `air_prepare`, `air.prepare` et `prepare`. Lit `ctx.targetTownId` au lieu du paramètre local identique de l'ancien driver. | Booléen `prepared` ; faux si le scan est déjà fini ou sans combo. Le driver conserve le retour `prepare_return`. |
| `OpexAirPlansStepFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo, light)` | Exécute `OpexAirPlansFindSites` et garde `air_find_sites`, `air.sites` et `sites`. | Booléen `sitesOk` ; `false` entraîne au même endroit `sites_yield`, sans passage à `NewPairs`. |
| `OpexAirPlansStepNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo, light)` | Exécute `OpexAirPlansNewPairs` et garde `air_new_pairs`, `air.new_pairs` et `new_pairs`. | Booléen `pairsOk` ; `false` entraîne au même endroit `pairs_yield`, sans découverte des hubs. |

Le contexte `ctx` reste **éphémère par appel**. Tous les objets de
reprise (combos, villes, sites, curseurs `scanIndex/rankIndex/a/b`,
compteurs, `bestPlan`, listes de projets) restent exactement là où
ils étaient, dans le `resumeState` du C78 ou du scan ciblé.
Les corps des trois fonctions métier `Prepare`, `FindSites` et
`NewPairs` ont été conservés octet pour octet : seules leurs
invocations accompagnées des spans et des logs ont été déplacées du
driver vers les trois sous-étapes.

## Bornes et cas difficiles préservés

- Scan des sites : les indices `scanIndex=i+1` et
  `rankIndex=rankIndex+1` sont stockés **avant** les contrôles de
  budget/deadline ; V93, la cible C83, les probes partagés et la
  revalidation restent dans `FindSites`. Le curseur `c83Repair.scan`
  et son fallback restent dans `air_c83_repair.nut`.
- Paires : `(a,b)` avance vers la paire **suivante** avant les filtres,
  y compris abandoned et revalidation des sites ; le garde
  `pairProgress` assure au moins une paire par invocation, et le
  checkpoint après la dernière paire coûteuse reste intact.
- Le driver continue de prendre le `bestPlan` courant en cas de
  suspension, sans publication supplémentaire, puis exécute les hubs
  et la clôture des combos selon l'ordre antérieur. Saut V93 après
  grand gagnant, AC04‑B, AC05, V141 et AC06 restent hors du patch.
- `OpexC78ContinueCatalogAirRebuild`, `_taskQueue`, les réglages,
  `Save` et `Load` n'ont pas été touchés.

Les appels `OpexAirPlansStep*` ajoutent **un dispatch Squirrel
par sous-étape** : une fois pour `Prepare` à chaque invocation du
planificateur, puis une fois par combo visité pour chacun de
`FindSites` et `NewPairs` s'ils sont atteints. Les spans/probes
mettent ces appels dans les mêmes catégories mais la différence
d'opcodes intrinsèques n'est **pas zéro par construction**.
`OpexAirCalcDeltaOps` reste calculé depuis `t0_all/l0_all` :
sur un coût proche d'une borne `opsBudget` ou
`BUILD_TICK_MARGIN`, un surcoût même petit peut décaler de **une
visite** le point de suspension effectif. Les gardes logiques sont
inchangés ; l'égalité bit à bit des ticks/yields demande une
comparaison VM dédiée. La différence d'opcodes et ses conséquences
économiques éventuelles doivent être vérifiées **après** AC04, avec
un banc A/B sur bundle figé si le patch est retenu.

## Tests et portée

Les tests historiques AC02, AC03, AC04, AC05, V93/C83, V141 restent
les sources du contrat des fonctions métier. Deux tests de source
historiques ont été adaptés à **l'indirection** : les assertions
de `test_ac_catalogue_accepted.py` et
`test_air_selection_light.py` suivent désormais les appels
`driver → Step* → fonction métier`, en exigeant une seule visite
de chaque phase et les mêmes sondes.

`sweeps/test_cd01_cd02_air_stage.py` ajoute trois tests :

1. ordre des sous-étapes, protection des sorties avant les hubs,
   unicité des appels et maintien des raisons de yield ;
2. absence de point de suspension ou mutation de curseur dans les
   wrappers, spans/logs inchangés, checkpoints conservés dans les
   fonctions métier ;
3. modèle figé séquentiel `Sites → NewPairs` appuyé sur les fixtures
   AC02/AC03, avec budgets variables, cible absente/présente,
   validité de site et politique V93/C83.

Exécution depuis le **worktree** :

```powershell
python -X utf8 -m unittest sweeps.test_cd01_cd02_air_stage sweeps.test_ac02_air_site_resume sweeps.test_ac03_air_new_pairs_resume sweeps.test_ac_catalogue_accepted sweeps.test_air_selection_light sweeps.test_v93_small_airport sweeps.test_air0310_2_hub_snapshot -q
git diff --check
git diff -- ai/OpexAI/air_planning.nut sweeps/test_ac_catalogue_accepted.py sweeps/test_air_selection_light.py
```

**Résultats hôte vérifiés le 12/10 :**

| Contrôle | Résultat |
|---|---|
| Tests CD01/CD02 et régressions AIR ciblées, 18 modules (AC02–AC07, V93/C83, V133/V134, C121, V141, snapshots, probes) | **139/139 PASS** |
| Tests CD01/CD02 et suite ciblée minimale de 7 modules | **65/65 PASS** |
| Suite hôte générale `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py' -q` | **1 944 exécutés, 2 FAIL**, les deux préexistants sur `a09a7b2` (voir ci-dessous) |
| Corps source de `OpexAirPlansPrepare`, `OpexAirPlansFindSites`, `OpexAirPlansNewPairs` comparés avec `git show HEAD` | **Identiques octet pour octet** |
| `git diff --check` | PASS |
| `git apply --reverse --check results/cd01_cd02_stage_20261012.patch` | PASS |

Les deux échecs de la suite générale **ne sont pas causés** par
CD01–CD02, car les sources et les tests concernés sont identiques au
HEAD de départ :

1. `test_parallel_fleet_amort_shadow.SourceTests.test_preexisting_builder_entirely_preserved`
   épingle le SHA256 obsolète `0ebdb62d7c92c91ee1fa86482612eb5c52d0363018b595027bf2f78bdd14ce48`
   tandis que `ai/OpexAI/projects_builders.nut` au HEAD donne
   `b468ea6a580cf99188c72e4531cbc43efbc20be8752432dabcc0497cd40c49ec`.
   Le fichier source et le test sont inchangés.
2. `test_v86_hubhub_contract.V86HubHubContractTest.test_variante_a_hubhub_marginal_deduction_and_precalc`
   attend textuellement `if (AIR_HUBHUB_MARGINAL)`, mais le HEAD
   contient déjà la condition AC05 adoptée
   `if (AIR_HUBHUB_MARGINAL && !(AC05_SKIP_UNUSED_HUB_INCOME && C121_AIR_ECONOMICS))`.
   Le corps de `OpexAirPlansHubToHub` et le test sont inchangés.

Ces échecs sont consignés et non « corrigés » en élargissant le patch
CD01–CD02 à des assertions historiques sans rapport avec sa portée.
Cette suite hôte n'exécute ni NoAI ni les opcodes du moteur, donc la
qualification VM/économie reste ouverte. Le patch complet incluant les
nouveaux fichiers est situé dans
`results/cd01_cd02_stage_20261012.patch` **à l'intérieur de ce worktree**.

L'examen du diff est indispensable avant toute reprise par le prime,
car l'AC04‑v3 du principal n'est **pas présent** dans ce worktree
base `a09a7b2`. Intégrer les changements par patch ciblé, sans
écraser les modifications parallèles du principal. Pas de commit/push,
pas de campagne Docker pendant B20×10.
