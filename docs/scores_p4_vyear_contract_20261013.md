# P4-adjust — panel complet d'incumbents en véhicule-année

**13 octobre 2026 — expérimentation, non validée économiquement.**

## Isolation et décision

Worktree `results/scores_p4_adjust_stage_20261013` créé depuis `c2a5be3`,
avec les **10 overlays comportementaux P4** repris à l'identique du stage testé
avant les seules modifications P4-adjust. AAAHogEx-115 est copié (ignoré de Git).
Ni `master`, ni le stage de P4 testé ne sont modifiés ; le rapport consolidé
de la branche de diagnostic est mis à jour séparément. La variante a été
archivée sur `origin/codex/scores-p4-vyear-experimental-20261013` sans merge
sur `master` ; les résultats économiques ne l'autorisent pas.

P4 `score_c70_stable_cohort` est rejeté sur 40×5 (**−43 730 £/an** en profit
terminal moyen, 18V/21D/1E). P4-adjust n'est pas son adoption : c'est une
variante causale supplémentaire à **prouver** au moteur et économiquement.

Flags **indépendants**, à `0` sur **easy, medium, hard, custom** :
`score_c70_vyear_cohort` (application économique du facteur vyear) et
`score_c70_vyear_measure_shadow` (même mesure complète, sans application).
Pour éviter deux politiques concurrentes, chacun est automatiquement inactif si
`score_c70_stable_cohort=1` ou `save_full_state=0` ; C70 désactivé rend aussi
ce calibrateur sans effet économique. Les routines historiques C70/C82 sont
préservées, et les cumuls C82 par moteur restent les historiques.

**Contrôle critique après smoke 314159×3** : 2/2 parties saines et
`P4_VYEAR_MODE exercise=1971 mode=air covered=6 neutral=0 factor=0.4676`, mais
première divergence d'argent entre les bras **le 01/09/1971**, avant la
publication du premier facteur non neutre en **janvier 1972**. Cette divergence
est donc **incompatible avec une explication par un score vyear appliqué** :
effet de calendrier VM/opcodes, instrumentation ou source de divergence
indépendante. Aucun gain/perte du premier smoke n'est causalement attribuable
au facteur.

## Pourquoi le véhicule-année exact n'est pas possible

`task_report.nut::_reportLines` somme `AIVehicle.GetProfitLastYear(v)` des
véhicules **encore valides** au rapport de janvier. Le véhicule vendu, remplacé,
crashé ou attribué ailleurs entre deux rapports n'a alors plus de profit
`GetProfitLastYear` interrogeable. Il manque les comptes annuels clos à la date
de vente et une chronologie exhaustive des transactions/ordres/wagons. Ni une
formule `profit * trains0 / vehCount courant`, ni `same_ids` aux deux rapports
ne permettent de reconstruire l'exposition véritable de chaque véhicule.
Les anciens `p4C70MutationYear/PreviousYear` sont des signaux événementiels
partiels. P4-adjust conserve aussi ses propres marqueurs structurels
`dirtyYear/dirtyPriorYear` lors des crashes, autoreplacements, ventes AIR et
retraits unitaires attribuables, ainsi que de l'ajout d'un wagon à un train.
Ces marqueurs **ne constituent pas un registre exhaustif**. **Aucun profit
perdu n'est inventé ni imputé.**

## Estimateur retenu : panel complet *sans attrition*

À chaque rapport de janvier Y, snapshot de la ligne (sauf ROAD) :
`[vehicle_id, engine_id, capacity(line.cargo), order_count,
order_dest_0, order_flags_0, ...]` pour les véhicules
attribués via `line.vehicles`. L'exercice mesuré est Y−1. Le premier rapport
fournit uniquement un baseline ; il ne produit jamais une observation rentable.

Une observation est admise uniquement si :

1. La ligne a `age >=2`, `trains0>0`, `predicted>0`, une identité de flotte
   explicite (pas la route reconstructible seulement par les stations), et un
   snapshot au rapport **Y−1**, sans marqueur structurel connu pendant
   l'exercice mesuré.
2. **Tous** les véhicules du snapshot précédent sont encore valides, de même
   moteur/capacité/**liste complète des destinations et drapeaux d'ordres**,
   et ont l'âge requis pour avoir vécu la
   totalité de l'exercice précédent.
3. Des véhicules supplémentaires peuvent apparaître, mais leur profit
   `GetProfitLastYear` n'entre **jamais** dans le numérateur de cette année.
   C'est la différence essentielle avec P4 « flotte exactement stable » :
   une ligne en croissance demeure observable via ses incumbents de départ.

Pour N incumbents survivants **tous** présents en début de période :

`real_per_initial_fleet = (Σ profitLastYear(incumbents)) × trains0 / N − predAmort`

`ratio_pm = clamp(real_per_initial_fleet / predicted, −0.5, 2.5) × 1000`

`ratio_pm` est converti en **entier** et cumulé pour la ligne ; après
20 observations, l'historique est diminué de moitié pour éviter le débordement
et amortir les régimes anciens. Les bornes `−0.5` et `2.5` ainsi que la
régularisation ci-dessous sont **hypothèses de robustesse à tester** ; elles ne
sont pas prétendues statistiquement calibrées.

Après une année **non valide** (refit, changement d'ordres, attrition,
événement connu, cargo invalide), `sumPm=0, count=0` : aucun historique
antérieur ne recontamine les années valides ultérieures. Le contrat de
snapshot passe à **version=2** ; une sauvegarde version=1 est traitée comme
mesure absente (repli historique), pas reinterpretée artificiellement.

**Attrition, mutation détectable, baseline absent, ID non attribuable** →
la ligne vaut **1.0 neutre** dans le facteur C70 de ce rapport, et pas une
moyenne biaisée des seuls survivants. Les 4 modes comptent chaque ligne mûre
et prédictible une fois : ligne mesurée = moyenne de son historique permille,
ligne non mesurée = 1.0. Deux pseudo-lignes neutres stabilisent l'ensemble :

`K_mode = (2.0 + Σ ratio_eligible_lines) / (2 + N_eligible_lines)`.

Si **aucun panel n'est couvert** pour un mode, `K_mode=K_C70_historique`
(aucune correction vyear). En particulier ROAD reste sur C70 historique
malgré l'impossibilité actuelle de lui attribuer des incumbents fiables.
Lorsqu'au moins une ligne est couverte, le repli des autres lignes reste
neutre selon la formule ci-dessus. Une ligne qui perd un ancien
véhicule ne garde **pas** son facteur favorable des années antérieures : cette
année elle redevient neutre. Pour ROAD, l'attribution des véhicules par
station+ordres peut partager des véhicules entre lignes de même OD : neutralité
systématique jusqu'à identité explicite prouvée.

### Hypothèses et limites d'inférence

Le panel mesure les profits d'incumbents complets **conditionnellement à la
survie de tous les incumbents**, et non une décomposition exacte du profit de
la flotte totale. Des transactions intra-annuelles réversibles, un wagon
modifié puis restauré, une modification d'ordres à nombre constant ou un ID
réutilisé avec âge cohérent peuvent échapper aux snapshots. Une ligne
abandonnée/démolie sort de `_lines` ; cette survie des *lignes* introduit un
biais distinct qui n'est pas éliminé. Les profits des nouveaux appareils sont
exclus pendant l'exercice où ils entrent, et la congestion qu'ils imposent
aux anciens reste dans le profit des anciens. La neutralité du repli n'est pas
une estimation de la performance économique des services perdus.

L'emploi des facteurs sur de nouveaux projets suppose la transférabilité des
cohortes historiques aux projets finançables, **non prouvée**. Il faut encore
observer les flips effectifs C77 et les constructions au moteur ; la sonde
`scores_p4_flip_stage_20261013` peut servir de référence de méthode.

## Save/Load exact pour le **nouvel état**, même >64 lignes

`p4VYear` est une table sérialisable **sans flottant** :
`version=2, reportYear, snapshot, sumPm:int, count:int, valid:int,
dirtyYear:int, dirtyPriorYear:int`.

`OpexSaveProjectLine` historique reste *byte-identique*, afin de limiter
les opcodes sous flag OFF. En ON, le wrapper `OpexSaveProjectLineVYear` supprime
seulement `p4VYear` de la projection mensuelle, évitant le double volume et
la copie périmée. `Save()` reconstruit un sidecar `p4Adjust[lineId]` **frais**,
dans le passage sur les lignes qu'il effectue déjà, et l'ajoute au saveObj.
`Load()` capture ce sidecar **sans conditionner à des settings pas encore lus** ;
`_reconcileAfterLoad()` le vérifie et le restitue aux lignes conservées avant
`OpexC70VYearRecomputeFactors`. Si le sidecar manque/corrompt la ligne, l'état
est absent et le facteur neutre. La perte des vieux champs C70 projetés reste
la limitation historique, mais **le nouveau ratio ne dépend plus de leurs
floats arrondis** : il utilise le permille integer du sidecar.

`save_full_state=0` ne sauve pas `_lines` : la variante est **inactivée**.
L'état vivant sidecar augmente la taille du graphe sérialisé et les opcodes de
`Save()` de **O(nombre de lignes + véhicules et ordres présents dans les snapshots)**.
L'ancien cache mensuel >64 évite les conversions lourdes sous le budget Save
100k. Un **roundtrip moteur réel avec 80 lignes sauvegardées** a réussi
(détails ci-dessous) ; il n'existe toutefois **aucune garantie à 150+ lignes**.
La validation
au chargement impose `valid` booléen entier, `count ∈ [0,20]`, cumuls
permille cohérents, `dirtyYear/dirtyPriorYear` entiers et pour chaque entrée
`4 + 2×order_count` entiers ; le constructeur ne sollicite
`AIVehicle.GetCapacity` qu'après confirmation de `IsValidVehicle` et
`AICargo.IsValidCargo`.

## Validation hôte, critères de décision et protocole moteur

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_scores_p4_vyear_20261013.py -v
python -X utf8 -m unittest discover -s sweeps -p test_scores_p4_behavior_20261013.py -q
python -X utf8 -m unittest discover -s sweeps -p test_scores_p4_cohort_probe.py -q
python -X utf8 -m unittest discover -s sweeps -p test_c69_reload_contract.py -q
python -X utf8 -m unittest discover -s sweeps -p test_b5_rail_persistence.py -q
git diff --check
```

Ces tests incluent un modèle Python de roundtrip sur **90 lignes** (cache
mensuel volontairement obsolète), des cumuls entiers conservés, expansion
d'avions sans attribuer les entrants, perte et refit neutres, et ligne ROAD
exclue. **Ce n'est pas une compilation Squirrel ni un roundtrip OpenTTD.**

Commande **historique** du premier smoke, **déjà exécuté et validé par le
prime sur 314159×3, 2/2 parties saines** (ne pas le relancer pour qualifier
le matched-shadow) :

```powershell
python sweeps/run_c66_reference.py `
  --campaign scores_p4_vyear_smoke_314159_3y_20261013 `
  --container-name scores-p4-vyear-smoke-314159 `
  --reference "OpexAI[score_c70_vyear_cohort=0,score_c70_cohort_probe=1]" `
  --variant "OpexAI[score_c70_vyear_cohort=1,score_c70_cohort_probe=1]" `
  --policy-id p4_vyear_off --variant-policy-id p4_vyear_on `
  --years 3 --seeds 314159 --repeats 1 --script-debug `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 `
  --required-seeds 1 --required-years 3 --primary-metric profit_year `
  --value-guard-max-loss-pct 5 --cpus 3 --max-workers 2 --memory 4g `
  --out results/scores_p4_vyear_smoke_314159_3y_20261013.json
```

Smoke à vérifier : syntaxe Squirrel, couverture `P4_VYEAR_LINE` et
`P4_VYEAR_MODE`, existence d'une flotte croissante avec panel accepté,
`mode=road` neutre, croissance des opcodes, santé du duel, et test séparé
Save→Load depuis une **véritable** sauvegarde `>64` lignes. Après smoke,
**une seule** campagne A/B économique à la fois, si justifiée : même graines,
horizon 5 ans, `profit_year` terminal primaire ; ne pas adopter un facteur
sur le seul changement de classement. L'analyse par année 1972–74 et les
flips C77 stricts sont requis pour attribuer les différences aux scores.

### Statut final

**Candidat implémenté, OFF préservé, sidecar Save/Load moteur validé à 80 lignes,
smoke matched-shadow 2×3 complet et 2 127 tests hôte verts.** La faisabilité
exacte du vehicle-year reste négative ; les marqueurs ne sont pas exhaustifs.
La qualification économique à cinq ans n'est pas acquise et aucune adoption
ne découle des seuls smokes. Le benchmark clean 5×5 est en cours de qualification.

## Complément : diagnostic `matched-shadow` (après le smoke 314159×3)

**Cause de ce contrôle :** première divergence de trésorerie ON−OFF au
**01/09/1971**, alors que le premier facteur C70 vyear non neutre n'est
publié qu'en **janvier 1972**. Ce n'est pas une divergence démontrée de score.

`score_c70_vyear_measure_shadow=1` est un flag **indépendant** ajouté après le
premier smoke. Il active **exactement les chemins lourds vyear des deux bras** :
snapshots à chaque rapport, vérification des véhicules (y compris commandes,
moteur, capacité, profit des incumbents), compteurs, marqueurs structurels,
projections de ligne sans vyear et sidecar *frais* `p4Adjust` à chaque `Save`,
reprise à `Load`, calcul des facteurs vyear au rapport et après reload.

| Bras | `score_c70_vyear_cohort` | `score_c70_vyear_measure_shadow` | Mesure vyear | Facteur C70 **appliqué** |
|---|---|---|---|---|
| OFF historique | 0 | 0 | Non | C70 historique |
| **Référence matched-shadow** | 0 | 1 | Oui, complète | **C70 historique** |
| **Variante matched-shadow** | 1 | 1 | Oui, complète | vyear si `covered>0`, sinon C70 historique |

Seule différence économique voulue sous mesure commune :
`C70_MODE_FACTOR[mode] = (policy ? effectiveK : legacyK)` lors du calcul
vyear. **Les deux bras effectuent cette unique affectation**, même quand le
facteur vaut 1, pour éviter le coût d'une écriture supplémentaire uniquement
dans le bras ON avant la première correction. La condition mesure commune
est évaluée avant l'appel : sous les **deux flags à 0**, les chemins historiques
de mesure/score/Save sont conservés ; les fonctions de calibration historiques
et `OpexSaveProjectLine` sont contrôlées *byte-identical* à `c2a5be3`.

`P4_VYEAR_MODE` publie `factor` (candidat effectif), `measured_k`,
`legacy_k`, `fallback_legacy`, `covered`, `neutral`, `applied` dans les
**deux bras** si `score_c70_cohort_probe=1` ; le journal n'est pas une preuve
que le facteur candidat a été appliqué en référence. `C69_BOTTLENECK
phase=c70_factor` conserve le facteur historique publié avant la mesure.

**C82 :** `c82_engine_calibration=0` sur les quatre difficultés de la
configuration de base (`info.nut`). Si C82 est activé manuellement, les
projets AIR à moteur connu utilisent le facteur C82 à la place du facteur
C70 : il faut bloquer ce réglage à 0 dans le diagnostic P4 et ne pas inférer
de flips AIR C70 là où C82 l'emporte.

### Contrat moteur de la campagne appariée 5×5

Commande à lancer **uniquement par le prime**, depuis ce worktree, **une seule
campagne à la fois**, avec les cinq graines du diagnostic P4 C77 :

```powershell
python sweeps/run_c66_reference.py `
  --campaign scores_p4_vyear_matched_shadow_5x5_20261013 `
  --container-name scores-p4-vyear-matched-shadow-5x5 `
  --policy-id p4_vyear_measure_ref `
  --variant-policy-id p4_vyear_measure_on `
  --reference "OpexAI[score_c70_vyear_cohort=0,score_c70_vyear_measure_shadow=1,score_c70_cohort_probe=1,c82_engine_calibration=0,decision_log=1]" `
  --variant "OpexAI[score_c70_vyear_cohort=1,score_c70_vyear_measure_shadow=1,score_c70_cohort_probe=1,c82_engine_calibration=0,decision_log=1]" `
  --seeds 314159 271828 161803 123457 987653 `
  --years 5 --repeats 1 --max-workers 10 --cpus 10 --memory 8g `
  --script-debug `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 `
  --required-seeds 5 --required-years 5 --primary-metric profit_year `
  --value-guard-max-loss-pct 5 `
  --out results/scores_p4_vyear_matched_shadow_5x5_20261013.json
```

La règle C66 économique sert au harnais, **pas à une décision d'adoption sur
5 graines**. Étudier par graine et par date : premier écart de caisse/finance
et d'opcodes, premier rapport dont `applied=1` avec `factor != legacy_k`,
première sélection/tentative dont la politique peut changer le rang, flottes
et constructions AIR/RAIL ultérieures. Un écart antérieur au premier facteur
effectivement différent est encore **non causal pour le score**, même sous
matched-shadow ; les différences de VM dues à la valeur des settings, aux
branches et au calendrier des opcodes ne sont pas mathématiquement nulles.

Le test initial de sûreté doit comparer `P4_VYEAR_LINE` et
`P4_VYEAR_MODE` **sur une trajectoire encore commune** ; toute première
divergence antérieure aux facteurs doit être signalée, non attribuée à une
inversion de rang. Contrôles supplémentaires : Save/Load réel à 65 et 150+
lignes, budget Save 100k, aucune erreur Squirrel, mode ROAD sans observations
conservant C70 historique, aucun nouveau ratio après un refit en cours.

**Une comparaison économique propre A/B sans sondes reste indispensable**
si un diagnostic matched-shadow rend un candidat crédible ; ni le vieux 40×5
P4 stable-cohort, ni ce 5×5 apparié ne suffisent à l'adopter.

## Moteur et sûreté déjà vérifiés au 13 octobre

- Smoke matched-shadow `scores_p4_vyear_matched_smoke2x3_20261013`, bundle
  `6d0e1ee55f31aa9d4640706cbf5a336219134ae9e8b6939a1a00074507526894` :
  **4/4 parties saines**, `seed123457` égalité stricte sur trois ans ;
  `seed314159` Δ terminal ON−OFF de **−40 755 £/an**, premier écart de caisse
  en septembre 1971, **avant** toute correction C70 vyear non neutre.
- Deux références indépendantes avec politique **identique** (`cohort=0`,
  `measure_shadow=1`), même seed314159, bundle et un seul worker, ont produit
  `profit_year=1 450 024` et `1 453 159 £/an` ; `company_value=2 610 180`
  et `2 748 374 £`. Premier écart de log le 13 août 1971 chez AAAHogEx,
  `CheckRenewal 0[ticks] 11658[ops]` contre `1[ticks] 11659[ops]`, puis
  des décalages de calendrier. Cela montre une variabilité inter-exécutions
  même sans politique différente ; **aucun delta 3×3 n'est causalement
  attribuable** à P4 à ce stade.
- Roundtrip moteur depuis la copie byte-identique
  `results/scores_p4_vyear_roundtrip_stage_20261013`, seed123457,
  **7 années + reload au 1er juin 1976 + 1 année** : sauvegarde avec
  `LOAD_RECONCILE saved=80 kept=79 dropped=1`, aucune erreur Save/Load.
  Pour AIR, `covered=58, neutral=6, factor=0.55353385` exactement identique
  avant/après reload sur exercice 1975. ROAD garde son repli legacy, RAIL
  perd une ligne à la réconciliation et son facteur recalculé diffère.
  **Au-delà de 80 lignes**, la tenue du budget Save 100k reste inconnue.
- Suite complète hôte après correctif de branche OFF dans `persist.nut` :
  **2 127 tests OK**, `git diff --check` propre. L'ancien test B3 exigeait
  `projectedLines.append(OpexSaveProjectLine(line));` : le `else` OFF reprend
  désormais exactement cette instruction, ON conserve le sidecar vyear.
  Preuve : `results/scores_p4_vyear_host_suite_after_b3_fix_20261013.log`.

## Résultats économiques 5×5 sur le code final

Campagnes **successives** avec les mêmes 5 graines de développement et
5 ans, bundle commun entre politiques et entre campagnes
`01f22c957c52c531092b92a84d87cf929f54073a662d74ef5a3c97d540b392ce`,
10 CPU/10 workers maximum, **10/10 parties complètes dans les deux** :

| Campagne | Flags de mesure du témoin | Δ `profit_year` terminal moyen ON−OFF | V/D/E | Wilcoxon | IC95 bootstrap | Δ CV |
|---|---|---:|---:|---:|---:|---:|
| `scores_p4_vyear_clean_dev5x5_20261013` | shadow=0, probe=0, decision_log=0 | **+19 039,6 £/an** | 3/2/0 | 0,625 | [−23 875,8 ; +68 703,8] | −0,3144 % |
| `scores_p4_vyear_matched_dev5x5_20261013` | shadow=1, probe=1, decision_log=1 | **−19 231,2 £/an** | 2/3/0 | 0,625 | [−81 545,6 ; +43 083,2] | +0,5069 % |

Les deux ont le verdict `fail_primary` et aucune borne IC95 basse positive.
Le seuil de +4 % vaut environ +75k £/an sur ces échantillons. Ces
expériences appariées *intra-campagne* n'autorisent pas de comparaison
causale *inter-campagnes*, car sondes/logs et cadence changent. Le clean
présente encore un premier écart de caisse **1971-09** sur 314159, avant
premier facteur vyear actif. Le matched a des premiers écarts monétaires
entre **avril 1972 et mars 1973** sur les cinq graines, après les premières
publications effectives observées du facteur vyear **du 10 janvier au
6 juin 1972 selon la graine** : cette chronologie reste nécessaire mais
non suffisante pour établir des flips/builds causaux.

Preuves et analyseur local (aucun Docker supplémentaire requis) :
`sweeps/analyse_scores_p4_vyear_effect_20261013.py`,
`results/scores_p4_vyear_effect_comparison_20261013.json`,
ainsi que les JSON/JSONL/logs engine des deux campagnes. **Aucune gate 40×5
ni intégration n'est déclenchée par ces résultats de développement** ;
un signal économique robuste ou une hypothèse causale nouvelle serait requis.

## Audit événementiel complémentaire : choix ≠ calendrier ≠ nouvelle ligne

Le script `sweeps/analyse_scores_p4_causal_exposure_20261013.py` rapproche,
sur les **10 journaux du 5×5 matched**, `P4_VYEAR_MODE`,
`PROJECT_CHOSEN`, `AIR_BUILD`/`RAIL_BUILD`, `LINE_REVENUE`, et les
snapshots de trésorerie mensuels. Il compare séparément un désaccord
**date+OD** et un véritable premier désaccord **d'identité OD** dans les
séquences de choix et de construction ; le rang dans le journal ne
reconstitue pas le classement C77 d'un même état. Le marqueur BUILD
avec `line` est obligatoire avant qu'une ligne soit comptée comme
construite, et les revenus ne sont joints que par cet ID au sein du
même bras ; un rapport de ligne n'est retenu comme mature qu'à `age>=2`.

| Seed | Première publication C70-vyear non neutre (dernière date OPEX tracée) | Première caisse Opex / AAA différente | Premier choix autre OD | Première construction autre OD |
|---|---|---|---|---|
| 314159 | 1972-06-06 | 1972-08-01 / 1972-09-01 | 1972-08-02 | 1972-08-02 |
| 271828 | 1972-01-10 | 1972-12-01 / **1972-11-01** | 1972-11-02 | 1972-11-02 |
| 161803 | 1972-01-12 | 1973-03-01 / 1973-04-01 | 1973-03-08 | 1973-03-08 |
| 123457 | 1972-03-04 | 1972-04-01 / 1972-05-01 | 1972-04-03 | 1972-04-03 |
| 987653 | 1972-04-08 | 1972-05-01 / 1972-06-01 | **1972-04-23** | 1972-05-05 |

Pour 314159/161803/123457, le premier choix du même OD se décale
dans le calendrier et le premier **changement d'OD** intervient alors
que la trésorerie Opex mensuelle est **déjà divergente** : celui-ci ne
peut être identifié comme le premier mécanisme causal. Pour 271828,
le premier autre OD intervient le 2 novembre 1972 avant le premier
écart de caisse Opex, **mais AAAHogEx avait déjà divergé au checkpoint
du 1er novembre**. Ainsi **une seule graine, 987653**, présente une
première identité OD différente **avant** tout écart de trésorerie
mensuel des deux compagnies, le 23 avril 1972. Cependant sa première
construction d'un OD différent n'arrive que le 5 mai, après la
divergence de caisse Opex le 1er mai. **0/5 construction d'OD différent
avant toute divergence financière mensuelle des deux compagnies.**
Ces constats ne prouvent pas l'absence d'effet du facteur, mais ne
permettent **aucune attribution marginale sûre** : une divergence
physique intra-mensuelle peut en outre précéder le premier relevé
de caisse, et la même admissibilité C77/K_dec/capital au moment du
choix n'est pas reconstituée.

Constructions explicites AIR+RAIL observées par politique (ref/on) :
314159 **58/67**, 271828 **63/61**, 161803 **56/52**,
123457 **64/69**, 987653 **72/75**. Lien aux revenus de lignes
à âge ≥2 : respectivement **33/34**, **41/44**, **28/28**, **53/59**,
**50/55** lignes construites (ref/on). Ce relevé ne prouve pas
combien de lignes nouvelles sont marginalement rentables pour la
compagnie, ni celles que l'autre politique aurait construites.

Appariement **même mode/cargo/OD et année mature** sur les deux bras :
**53, 68, 46, 72, 89**, soit **328 paires de lignes-années**.
Parmi elles **280** ont la même date de construction ET le même
nombre de véhicules au relevé, mais **219/280** ont malgré tout un
profit de ligne différent. Le même OD et le même compte de véhicules
ne garantissent ni moteur/ordres/temps d'exploitation identiques,
ni absence de concurrence/cannibalisation, et les lignes survivantes
sont sélectionnées. **Ces 328 sont des observations répétées de
5 graines, pas 328 répliques statistiques indépendantes.**

**Conclusion expérimentale :** plus précis que le simple premier écart
mensuel, cet audit identifie **1 graine à potentiel d'exposition
avant divergence financière mensuelle du duel** mais zéro
contrefactuel de même état C77 prouvé et zéro
rendement réseau marginal attribuable. La prochaine expérience utile
est un *shadow* sans choix modifié qui capture **au même instant**
les projets tous simultanément financables, leur tier C77, K_dec,
les facteurs C70 legacy/vyear, les scores de chaque alternative et
l'identité de la tête réelle, puis le choix réellement tenté et
la construction/réconciliation par lineId. Une comparaison
ON/OFF entre calendriers divergents ne remplace pas ce replay.

Fichier de preuve compact contenant toutes les liaisons et lignes-années :
`docs/scores_p4_causal_exposure_20261013.json` ; 7/7 tests ciblés
`test_analyse_scores_p4_causal_exposure_20261013.py` verts.
