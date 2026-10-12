# AC-07 — publication partielle du vivier AIR (11 octobre 2026)

**Décision : audit terminé, aucun changement de production retenu.** Le
chemin courant V141 conserve les alternatives non aériennes, revalide les
anciens projets AIR, insère les nouveaux plans et rejoue la sélection au
capital courant. **Aucune perte involontaire de projet n'a été démontrée**
dans le modèle déterministe de groupes ; il ne s'agit pas d'une preuve de
parité exécutée par la VM, ni d'une égalité exacte dans toutes les phases de
bootstrap. L'exception historique AIR_RAIL comporte des **doublons de
préfixe hérités**, explicitement tolérés par le code.

## 1. Émission d'un lot et identité des projets

- `scheduler_tasks.nut:89–150` : la publication vient **au dispatch suivant**
  la tranche productive (`partialPending`), après restitution du budget.
  Le **premier lot** reconstruit le portefeuille avec
  `_rebuildProjects(...,false)` ; les lots ultérieurs, si
  `AIR0310_INCREMENTAL_PUBLISH` est ON et qu'il existe un portefeuille et
  `lastPublishedCount>0`, appellent `OpexAir0310PublishIncremental`.
  Si l'appel retourne `null`, la reconstruction complète reste le repli.
  `lastPublishedCount` avance **après** publication. Le curseur du scan et
  son `bestPlan` ne sont pas réinitialisés.
- `scheduler_tasks.nut:154–179` : `phase=apply` est la **reconstruction
  complète finale** ; elle n'est pas remplacée par l'incrémental V141.
  `_rebuildProjects(..., advanceStage=false)` pendant les partiels
  préserve les étapes du bootstrap ; seule la publication finale peut
  faire avancer l'étape.
- `projects_update.nut:440–508` : l'incrémental travaille sur
  `scanPlans.slice(publishedCount)`, convertit chaque nouveau plan
  `OpexProjectFromAir` en alternative, en **conservant les listes de même
  clé**. Le dénominateur de `planningOpcodes` est le total des plans du
  scan plus les hérités valides, et non le nombre de plans nouveaux. Un
  plan refusé par la conversion n'est pas inséré : c'est un filtre voulu.
- `projects_update.nut:509–587` : pour chaque groupe, les projets non-AIR
  restent en place. Les projets AIR dont le payload est incomplet sont
  conservés sans reconversion. Les autres sont validés puis actualisés :
  V141 ON conserve l'objet et n'actualise que les champs dérivés ;
  V141 OFF repasse par `OpexProjectFromAir`.
  Si `OpexProjectKeyFor` change, l'objet passe dans `movedAir`,
  sans être laissé dans l'ancienne clé.
- `projects_update.nut:589–673` : `preKeys` (groupes rail/route/air
  en place), `deferred` (clés nouvelles et déplacées) puis `postKeys`
  sont assemblées. Dans un groupe, `keptAir` précède `movedAir`, puis
  `pendingNew` ; `OpexAir0310InsertAirBlock` place l'AIR **avant eau
  et flotte**. Puis nouveaux `candidateGroups`, `airPlans`, compteurs,
  lecture de la trésorerie et **`OpexReselectProjects`** : le classement
  final dépend des filtres d'exécution, du capital, du plancher et de
  `PROJECT_TOP_K`, pas du seul ordre de construction des groupes.

### Exception AIR_RAIL : multiplicité héritée

`projects_update.nut:455–472` prélève, lors du bootstrap AIR_RAIL,
les entrées de `projects.airPlans` situées **après** `publishedCount`.
Les héritées valides sont ajoutées à `storedPlans` après le scan courant
(`:648–654`). Si cette queue contient une entrée présente dans le scan
courant, la même entrée est alors stockée deux fois. Le commentaire du
code relève également qu'une reconstruction complète peut reconstituer
ce préfixe avec une multiplicité différente.

La fixture reproduit explicitement `[a,b]` et queue héritée
`[b,prior-good,prior-bad]` : `storedPlans=[a,b,b,prior-good]`,
le dernier étant filtré. Ce comportement est **une exception de
parité exacte admise**, pas une preuve que la sélection est identique
dans toutes les situations de bootstrap. Une modification toucherait les
alternatives et serait économique : ne pas « dédupliquer » sans campagne.

## 2. V141 et coût résiduel

`V141_CATALOG_INCREMENTAL` est **ON par défaut, validé le 11/10**.
Le raccourci est désactivé sous
`C111_AIR_C100_DECISION_SHADOW`. Le test d'équivalence de décision V141
est facultatif et journalise `V141_CHECK`; il ne change pas le tri.

La mise à jour en place réécrit `planningOpcodes`, `economicsDate`,
`cargo` et, si C118 est actif, les champs de couverture et d'économie
C68. Ces champs ne doivent pas être confondus avec un **nouveau calcul du
choix d'avion**. Les champs de classement économiques sont issus du
payload courant ; la sélection globale est cependant rejouée.

**Preuves historiques réutilisées, non réexécutées :**

- V141 : sur son profil 2×3, `pub.filter` **−25 à −31 %** (environ
  **1,3 M opcodes/an/partie économisés**) ; 818 comparaisons identiques,
  64 écarts `economicsDate` seulement. Porte 20×10 :
  profit annuel +59,8 k£, 11V/9D, IC95
  [−92,5 ; +216,0] k£, valeur +2,4 % ;
  adoption documentée dans `docs/taches.md`.
- V142 : regroupement temporel des publications **rejeté** :
  467 écarts de `candidateGroups`, 36 de capital et 1 de meilleur
  candidat ; `task.catalog` −50 %, `catalog.rebuild` −22..−29 %,
  `loop.orch` +25 %, porte A 40×3 `fail_primary`.

**Coût absolu résiduel de `pub.filter` après V141 : non identifiable
à partir des artefacts accessibles dans le dépôt courant.** Les journaux
historiques donnent **l'économie** et un rapport relatif, pas un compteur
aligné permettant de reconstruire avec certitude les opcodes encore payés
par publication. La trace mono-graine AC-04 possède `AIR_LIGHT` mais **aucun
span `pub.filter`**. Il serait donc incorrect de déduire un coût unitaire
du nombre de `AIR0310_PUBLISH` historiques, ou de confondre le coût
de `catalog.rebuild` avec celui du filtre.

Une mesure future devrait produire, **sur la même exécution V141 ON**,
`pub.filter`, `pub.partition`, `pub.insert`, `pub.recount`,
`pub.select`, le nombre de groupes et les anciens/nouveaux projets ;
les coûts induits sur le scheduler restent indispensables avant toute
optimisation. Une campagne V142 ne doit pas être relancée.

## 3. Fixture de conservation et ses limites

`sweeps/test_ac07_air_partial_publish.py` : **8 tests**, dont **5 760
configurations de groupes synthétiques** à graine déterministe, avec
plusieurs modes, alternatives de même OD, validité refusée, payloads
absents, clés déplacées, étape AIR_RAIL et queue héritée. Contrôle :

- **aucune disparition ni apparition d'un projet non-AIR** dans la partition ;
- mêmes identifiants AIR survivants et nouveaux, avec les mêmes
  multiplicités, selon les filtres synthétiques ;
- aucun projet affecté à une clé incohérente ; eau et flotte après le
  bloc aérien dans chaque groupe ;
- `scanPlans` conservé dans `airPlans`, puis hérités valides, avec
  **doublon bootstrap explicitement attendu** ;
- scénarios ciblés premier lot, insertion rail–AIR–eau, migration de clé
  vers une OD déjà dotée de route, site refusé, payload sans sites,
  mode C111/V141, repli `null`, partiels et `apply` final.

Commandes : `python -X utf8 -m unittest -v
sweeps.test_ac07_air_partial_publish` ⇒ **8/8 OK** ;
avec `sweeps.test_air0310_1_incremental_publish`,
`sweeps.test_ac06_catalog_lifecycle`,
`sweeps.test_ac05_air_hub_hub_resume` et
`sweeps.test_c78_air_candidate_hygiene` ⇒ **42/42 OK**.

**Limites de preuve :** le modèle Python ne reproduit pas la table
Squirrel ni son ordre d'itération, `OpexProjectFromAir`/scores réels
ou la sélection `OpexProjectSelectAffordable`. L'assertion de
« conservation du groupe » ne vaut donc pas preuve d'égalité octet
pour octet du `best` ou des décisions VM ; V141 a déjà son propre
benchmark économique. Aucun smoke ou A/B nouveau n'a été lancé.

**Clôture AC-07 :** aucune régression supplémentaire démontrée, V141
conservé, V142 non rouvert, aucune modification `.nut`, de réglage,
du portefeuille ni de l'invalidation C76. Le coût résiduel absolu
reste une **limite de mesure explicite**, non une économie présumée.
