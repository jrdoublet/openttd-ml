# CD03–CD05 — clôture du staging hubs AIR (12 octobre 2026)

## Portée et statut

**Worktree exclusivement utilisé** :
`results/cd_hubs_stage_20261012`, HEAD détaché `a09a7b2`.
Le prime avait déjà implémenté les trois helpers et adapté les tests
`test_ac04_air_hub_site_resume`, `test_ac05_air_hub_hub_resume`
et `test_v93_small_airport`. Le présent contrôle **préserve** ces
changements, réconcilie les autres tests source et ajoute des gardes
dedicées. Aucune source du principal, de CD01–CD02 ou de CD06 n'a été
modifiée. Aucune campagne Docker, aucun commit ou push.

**Verdict** : staging source et tests hôte **verts**, prêt pour revue
du prime ; validation VM des opcodes et de l'économie **non réalisée**.

## Contrat examiné

| Étape | Exécution et invariants |
|---|---|
| CD03 `OpexAirPlansHubDiscoveryPhase` | Appel après NewPairs terminé, avant HubToSite. Compte une action snapshot par invocation. Si signature de snapshot valide : réutilise les hubs sans span de découverte ni reconstruction ; sinon vide la liste d'orphelins, ouvre le span, découvre, clôt le span, stocke le snapshot, puis émet le diagnostic V95. `lightMark` est **local au helper**. |
| CD04 `OpexAirPlansHubToSitePhase` | Lorsque `hubPhase>=1` avec tranche C121 : ne recommence pas le builder. Sinon, appelle `OpexAirPlansHubToSite` et renvoie `false` sur sa suspension ; `hubPhase=1` n'est écrit **qu'après succès**. Le driver conserve le même `hub_site_yield`, le `bestPlan` et les fermetures de spans/logs. |
| CD05 `OpexAirPlansCompleteCombo` | Appelé uniquement après HubToHub terminé. Conserve les signes `AU`/`AE`, écrit `combo+1`, remet à zéro `a/b`, `sites`, les scans `scanIndex/rankIndex`, les curseurs C121 `hubSiteI/J`, `hubHubI/J`, `hubPhase`, efface le snapshot/skip, sauvegarde `bestPlan` et les compteurs. Puis retourne `-1` (break) ou l'indice du prochain combo. Le driver applique `comboIndex=nextCombo-1` avant le `for++`. |

Le cas **V93** demeure subtil : après un premier grand combo gagnant,
le helper passe au prochain petit combo ; après un petit, le grand
suivant est encore exécuté avant de chercher de nouveau un petit.
Exemple avec `[large,large,small,large,small,large]` :
`[0,2,3,4,5]` si grand gagnant dès 0 et V93 activé ; `[0]` si
V93 désactivé.

Le contrôle statique des trois helpers ne révèle **aucune variable
locale hors portée** : `ctx` porte l'état partagé, `lightMark` est
déclaré dans CD03, et CD04/CD05 ne capturent pas les `local` du
driver. Les six fonctions métier
`Prepare/FindSites/NewPairs/DiscoverHubs/HubToSite/HubToHub`
ne sont pas modifiées par l'extraction. Les limites de tranche
restent dans leurs corps, et aucun nouveau point de yield ni nouvelle
entrée `_taskQueue` n'a été créé.

**Réserve VM** : CD03, CD04 et CD05 ajoutent chacun un appel Squirrel
sur les chemins visités ; le coût de dispatch peut faire franchir
`opsBudget` ou `deadlineTick` à un autre élément à la frontière.
Seul un banc VM/moteur après la campagne AC04 permettra de qualifier
parité d'opcodes et neutralité économique ; les tests Python figent
l'ordre et les états, **pas** les opcodes exécutés.

## Correction des tests source

Les échecs legacy étaient des assertions structurelles qui exigeaient
la présence du corps métier *directement dans* `OpexAirPlans`, alors
que le refactor l'a extrait :

- `test_air0310_2_hub_snapshot` : extraction de
  `discovery_phase` et `complete_combo` ; rétablit les contrôles
  d'unicité du vrai DiscoverHubs, de span uniquement si non-réutilisation,
  de comptage, de rafraîchissement et de nettoyage du snapshot.
  L'ancienne `setUpClass` et une seconde assertion de parse ont été
  rectifiées.
- `test_ac02_air_site_resume` : vérifie le raccord direct
  `driver → CompleteCombo`, puis les resets de scan/rank/sites **dans
  le helper**, sans retirer les assertions sur les curseurs métier.
- `test_ac03_air_new_pairs_resume` : vérifie
  `driver → CompleteCombo` et le reset `a=0,b=1` dans le helper,
  en conservant les assertions de position du checkpoint avant filtre.
- `test_air_selection_light` : exige toujours **un appel de chaque
  phase** et leur ordre ; suit l'indirection CD03/CD04, vérifie
  l'unicité des invocations métier et l'ensemble inchangé des
  phases de mesure `air.light`.
- Contrôle transversal **supplémentaire** :
  `test_ac_catalogue_accepted` supposait également les appels inline ;
  désormais il vérifie le raccord
  `driver → HubDiscoveryPhase → DiscoverHubs` et
  `driver → HubToSitePhase → HubToSite`, chacun exactement une fois,
  sans perdre ses contrats C78/V141.

`sweeps/test_cd03_cd05_hub_stages.py` fournit **5 nouveaux tests** :
contrat d'ordre des phases et sorties de suspension ; isolation de
la découverte/snapshot ; transition `hubPhase` après succès ;
inventaire et ordre des resets ; comparaison indépendante du contrôle
de boucle ancien et de l'indice retourné par CD05, y compris V93.
Ce modèle à état figé ne prétend pas exécuter Squirrel.

## Validation hôte

| Commande | Résultat |
|---|---|
| `python -X utf8 -m unittest discover -s sweeps -p 'test_*air*.py' -q` | **671/671 PASS** |
| `python -X utf8 -m unittest sweeps.test_cd03_cd05_hub_stages -q` | **5/5 PASS** (non compris dans le glob AIR) |
| Les 7 suites des quatre régressions legacy, AC04/05 et V93 + nouvelles fixtures | **79/79 PASS** |
| `python -X utf8 -m unittest sweeps.test_ac_catalogue_accepted sweeps.test_ac06_catalog_lifecycle sweeps.test_ac07_air_partial_publish sweeps.test_c83_fixes sweeps.test_c83_local_repair sweeps.test_v931_air_demand sweeps.test_cd03_cd05_hub_stages -q` | **44/44 PASS** |

**Bilan sans double comptage au minimum : 676 tests AIR et CD03–CD05
verts** (671 de `test_*air*.py` + 5 spécifiques).
Les sous-suites de 79 et 44 chevauchent ce total. Aucune erreur
supplémentaire sur ces validations.

**Run combiné explicitement exécuté** : `unittest.TestSuite` de
`loader.discover('sweeps', pattern='test_*air*.py')` plus
`loader.loadTestsFromName('sweeps.test_cd03_cd05_hub_stages')` :
**676 tests, PASS**, confirmé après les dernières adaptations.

## Intégration future

Le patch du worktree est distinct de CD01–CD02 et CD06, également
basés sur `a09a7b2` mais possédant des changements propres. Ne
jamais appliquer globalement ces trois arbres les uns sur les
autres sans rebasage/contrôle des fonctions touchées et des tests.
Le présent staging ne doit pas être adopté par défaut avant contrôle
VM/opcodes et A/B économique si la politique de validation le requiert.
