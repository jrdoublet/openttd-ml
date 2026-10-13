# OpexAI — verdict de l'étude P2–P4 des scores (13 octobre 2026)

## Décision

**Aucune augmentation robuste du profit annuel terminal à cinq ans n'est
démontrée par les candidats P2–P4 étudiés.** Ne pas adopter les flags
économiques P3 ou P4, ne pas inventer de coefficient P2, ne pas changer de
défaut économique. P1/V165 demeure acquis. La demande d'un *gain effectivement
démontré* reste donc **non atteinte**, et non remplacée par une hausse de
score, de classement ou de nombre de candidats.

Point de départ : `codex/scores-p0-diagnostics-20261013` à
`c2a5be39043e64c754d9f659057dab3221e3e935`. Études dans quatre
worktrees isolés :
`results/scores_p2_stage_20261013`,
`results/scores_p3_stage_20261013`,
`results/scores_p4_stage_20261013`,
`results/scores_p4_behavior_stage_20261013`.
Pas de commit/push ni édition de `master` ou `origin/master`.

## Méthode économique

Même seed et même bundle, bras OpexAI séparément en duel contre
AAAHogEx-115 figé ; 40 graines canoniques × 5 ans pour les portes P3/P4,
40 paires saines exigées. Critère principal : différence **variante − référence**
de `profit_year` terminal 1974, et non duel seul contre AAAHogEx.
Seuil positif de gain utile de 4 % de la référence, Wilcoxon bilatéral
exact `p<0,05`, bootstrap IC95 basse strictement positive,
garde `company_value` à −5 %. Une campagne diagnostique à sonde
active ne permet pas de conclure sur le gain d'une politique.

| Piste | Preuve / échantillon | Profit annuel terminal | Verdict |
|---|---|---|---|
| P2 — prior initial 1970–71 | Sonde 5×5, 202 passes de sélection non vides, 57 observations provisoires jointes | Aucun essai de politique recevable | Pas de coefficient étalonné ni de flip utile démontré |
| P3 — tampon AIR séparé du score | Gate pure 40×5, 40/40 paires | **−58 915,725 £/an**, 15V/25D | `fail_primary` |
| P4 — C70 sur cohortes candidates | Gate pure 40×5, 40/40 paires | **−43 730,3 £/an**, 18V/21D/1E | `fail_primary` |

Les références P3 et P4 ont **des bundles différents**, et leurs
moyennes de base ne sont pas strictement identiques : les comparer en
niveau comme si elles formaient un seul A/B serait incorrect.
Les bornes **hautes** des IC95 bootstrap (P3 **+10,1 k£/an**,
P4 **+7,8 k£/an**) sont toutes deux très inférieures au gain utile
préenregistré de **+4 %** (respectivement **+86,2** et **+84,8 k£/an**).
Il ne s'agit donc pas seulement d'un résultat non significatif autour
d'une estimation positive ambitieuse : le signal de gain utile manque.

## P2 — étalonnage froid, 1970–1971

La sonde `score_cold_prior_shadow=1` (défaut OFF), dans
`results/scores_p2_stage_20261013`, capture candidats après budget et
plancher, même priorité C77, chaîne V88, moteur, OD, profit brut et financé,
bonus, devis et classement réel avant TopK. L'analyseur
`sweeps/analyse_score_cold_p2.py` reproduit le top de référence et
ne traite pas des candidats incomplets comme des décisions indépendantes.

Campagne `scores_p2_dev5x5_20261013`, bundle
`e9f750665f438d28f82a6e7cd93659a04472eedd4899ae6b6688289e2b708227` :
5/5 paires saines, 202 passes complètes non vides, 1 804 vides.
L'analyseur `sweeps/analyse_score_cold_execution_p2.py` joint
281 constructions AIR et 83 têtes de vivier aux choix/constructions,
dont seulement 57 observations de réalisation **provisoirement comparables**
(11 newpair, 35 hubsite, 11 hubhub). Les rapports annuels antérieurs à
1972 ne contiennent pas de cohorte C70 à âge ≥2 suffisamment mûre pour
calibrer les décisions de 1970–71. Même parmi ces 57 cas, modifications
de flotte, amortissement, route et cannibalisation ne sont pas contrôlés.

Rejeu de classements dans **les 202 passes non vides** (ce ne sont
pas 202 achats indépendants) :
prior AIR 0,7/famille : zéro flip de tête ; prior AIR commun 0,4 :
zéro ; prior commun 0,25 : un ; 0,1 : quatre. Les médianes exploratoires
réalisé/prédit des 57 cas (newpair 0,323, hubsite 0,387, hubhub 0,509)
ne donnent **aucun flip** appliquées comme facteurs par famille.
Il est interdit de transformer 0,1 ou 0,25 en coefficients arbitraires
simplement parce qu'ils inversent des classements.

Le delta positif d'une sonde P2 active (+174 728 £/an en moyenne sur 5×5)
est **diagnostique uniquement** : coût de journalisation et trajectoire
d'ordonnancement différents, pas une calibration P2.
Verdict : pas de candidat comportemental défendable pour 40×5.
Il faudrait des réalisations hors échantillon de même bundle, contrôlées
par famille/OD/moteur/flotte, et des inversions parmi projets de même
priorité effectivement finançables.

## P3 — AIR : score corrigé sans modifier le cash

Le flag `score_air_buffer_separate=1` n'affecte que le dénominateur du
classement AIR, sans changer `OpexProjectFinanceCapital`, l'admission
au cash, le plan de financement ni les constructeurs. Le cache C121
`lastScore` garde l'ancien score de catalogue. Sonde de rang distincte
`score_air_buffer_shadow` OFF à la gate.

`scores_p3_gateA40x5_20261013` ; bundle
`f0711fb57620e9218a67e301d2a64064bc4c357de5c67d7364f327601415930a`,
80/80 parties saines, 40/40 paires, couverture primaire et protocole
d'adoption complets :

- Profit terminal ON−OFF moyen **−58 915,725 £/an**,
  médiane **−76 425 £/an**, 15V/25D, Wilcoxon **p=0,13868**,
  bootstrap IC95 **[−128 221,6 ; +10 102,875]**.
- `company_value` ratio des moyennes **0,990051** (−0,995 %),
  garde tenue mais pas de gain primaire.
- Sonde P3 séparée : milliers de scores différents mais zéro flip
  en 1970, un seul en 1971 et neuf en 1972 dans son échantillon
  exploratoire 5×5 ; inversions majoritairement AIR↔AIR.
- Relevé terminal SIGNS `h5.observed-v1` : **82,376 M**
  opcodes publiés par graine en moyenne sous référence contre
  **83,412 M** sous P3, soit **+1,035 M** en moyenne. Ces compteurs
  sont **incomplets** (`observed_opcode_complete_cpu=false`) et ne
  mesurent pas le coût total VM. En parallèle, la variante présente
  **+1,30 panneaux de constructions survivants**, **+1,25 véhicule
  primaire** et **+1,43 gare** en moyenne au terminal : un volume
  physique un peu supérieur n'implique pas une meilleure rentabilité.

La direction de perte n'est pas établie au seuil 5 %,
mais le gain utile est absent : **P3 rejeté**, pas de B20×10 ni
combinaison sur simple espoir d'interaction.
Preuves `results/scores_p3_stage_20261013/results/scores_p3_gateA40x5_20261013.json`
et `docs/scores_p3_protocol_20261013.md` dans ce stage.

## P4 — C70 : cohortes candidates de flotte

Source de biais plausible : `GetProfitLastYear` couvre l'année des
véhicules survivants tandis que `vehCount` observe la flotte
au rapport annuel. Achats, ventes et remplacements pendant l'année
faussent le rapport réalisé/prédit. La sonde
`score_c70_cohort_probe=1` (défaut OFF) a trouvé dans son 5×5
306 exercices AIR matures dont 237 candidats, et 40 exercices
RAIL matures dont 32 candidats ; **« candidat stable » n'est pas
« stable prouvé sur l'année »**.

Le flag expérimental `score_c70_stable_cohort=1` (défaut 0), en stage
séparé, change **directement** le seul `C70_MODE_FACTOR` depuis ces
observations, laisse le C82 historique et le financement inchangés et
coupe les logs de sonde pendant la gate. Il **active aussi** les hooks
d'observation/mutation `SCORE_C70_COHORT_PROBE=LOG||STABLE`, avec un
coût VM potentiel même avant toute cohorte mature ; le gain ou la perte
de politique ne peut être automatiquement attribué au seul classement.

`scores_p4_stable_gateA40x5_20261013`, bundle
`a6fd1a93c3230c3000462646368c476aa764b7ebc58529efe68e98f6ec3c5531` :
80/80 parties saines, 40/40 paires, `comparison_complete`,
`adoption_sample_complete`, `metric_coverage_complete` :

- Profit terminal moyen **−43 730,3 £/an** (**−2,0633 %**
  de la référence), médiane **−24 164,5 £/an**, **18V/21D/1E**,
  Wilcoxon **p=0,258568**, bootstrap IC95
  **[−100 828,35 ; +7 772,25] £/an**.
- `company_value` −97 540,4 £ en moyenne, ratio des moyennes
  **0,986385** (−1,3615 %) ; `primary_vehicles` **−1,125**
  par graine en moyenne, `n_stations` **−1,075**.
- Pour le contexte concurrentiel (et **non** pour décider de l'adoption),
  le témoin OpexAI produit **2,119 M£/an** contre **3,200 M£/an**
  pour AAAHogEx figé dans son duel : écart moyen
  **−1,080 M£/an**. Le duel variant présente un écart moyen
  **−1,132 M£/an**. L'effet de politique demeure le **−43 730 £/an**
  Opex ON−OFF, et non la différence entre deux duels Opex/AAA.
- Moyennes annuelles du delta de profit ON−OFF : 1970 **−2 084,85**,
  1971 **−4 279,675**, 1972 **−14 033,1**,
  1973 **−35 633,6**, 1974 **−43 730,3 £/an**.
  En 1970–71, 39/40 graines restent identiques. La graine 1
  diverge pourtant dès février 1970 sur la trésorerie du snapshot,
  avant une calibration C70 mature :
  l'effet de coût/ordonnancement ON doit être distingué du score.
- Relevés **partiels** d'opcodes publiés par SIGNS en décembre 1974 :
  référence **84,116 M**, variante **84,881 M**, delta moyen
  **+0,765 M**. `observed_opcode_complete_cpu=false` ;
  ce ne sont **pas** des coûts VM totaux comparables à un profilage exhaustif.
- Panneaux de constructions `IB|` survivants au relevé terminal
  (non un journal exhaustif des constructions) : différence
  moyenne ON−OFF de **−1,975 en 1973**, puis **+1,25 en 1974**.
  L'association à un profit plus faible (−57 207 £/an parmi les 28 graines
  ayant moins de panneaux de construction en 1973) est **exploratoire**,
  non preuve d'un déplacement causal de chantiers, car ces panneaux
  peuvent être incomplets et ne sont pas un ledger exhaustif.

L'audit Save/Load et cohorte signale en outre : un achat puis une vente
entre rapports peut se dissimuler derrière mêmes IDs survivants ;
le cache de sauvegarde mensuel pour au moins 64 lignes peut dater d'avant
le rapport, perdre les nouveaux cumuls avec `lastReportYear` pourtant
actualisé ; les flottants `p4C70Real/Pred` subissent une conversion
en entier, et le transfert de wagons change une flotte sans changer l'ID
train. **Une gate positive n'aurait pas suffi pour l'adoption** ;
ici la gate est de toute façon négative. P4 rejeté sous sa forme testée.
Preuves : `results/scores_p4_behavior_stage_20261013/results/scores_p4_stable_gateA40x5_20261013.json`
et `docs/scores_p4_behavior_protocol_20261013.md` dans ce stage.

## Limites, suites et invariants

### Validation hôte et régressions

- Stage P2 : **2 102 / 2 102 tests verts**.
- Stage P3 : **2 098 / 2 098 tests verts**.
- Stage P4 sonde passive : **2 099 / 2 099 tests verts**.
- Stage P4 variante économique : **2 101 / 2 101 tests verts**.
- Stage P4 sonde duale C77 : **2 117 / 2 117 tests verts**, dont
  quatre contrôles du nouvel analyseur de logs.

Les échecs initiaux de P3 provenaient de deux assertions figées sur le code
inline du score, désormais factorisé dans le helper P3, et de deux lectures
des archives AC04 ignorées par Git et stockées dans le worktree frère. Les
tests ont été ajustés pour vérifier le même invariant et retrouver **les
preuves originales** à leur emplacement réel ; aucune assertion économique
ni aucun code moteur n'a été neutralisé pour les faire passer. Les corrections
de chemins AC04 ont aussi été appliquées aux autres stages ; leurs suites
complètes sont vertes. `git diff --check` est vert.

1. Une inversion de tête C77 n'est **pas** la même chose qu'une construction
   différente ou un gain. P2 montre une exposition négligeable pour des
   priors plausibles ; P3 a des inversions rares ; P4 n'a pas encore
   de contrefactuel de tête strictement finançable par tier C77 pour
   attribution fine de ses pertes. Une sonde minimale peut établir ce
   mécanisme, mais ne transforme pas la gate négative en gain.
2. Aucun portage des politiques P3/P4, aucune valeur de défaut changée.
   Ne pas tester P3+P4 pour choisir opportunément graines ou paramètres :
   leur interaction devrait avoir une justification causale et un protocole
   indépendant pré-enregistré. Un éventuel P4 *rail-only*, *air-only* ou
   inverse du facteur, inventé après lecture de la gate 40×5, serait une
   hypothèse **post hoc** et exigerait exposition causale, données de
   développement distinctes et nouveau jeu de validation indépendant.
3. Pour P2, acquérir observations de réalisations hors échantillon et
   même bundle, contrôler flotte/âge/amortissement, vérifier flips
   simultanément finançables en 1970–71. Pour P4, construire un registre
   de mutations de flotte exhaustif et une persistance de cohortes
   fidèle après rapport, puis seulement tester une variante corrigée
   si des inversions utiles sont prouvées.
4. Respecter 10 CPU/10 workers au maximum, un seul banc Docker à la fois,
   mêmes seeds, bundles et paramètres, Save/Load et politiques C77/V88
   invariantes. Aucun push sans approbation.

### Sonde P4 complémentaire sur classements C77

Nouveau worktree isolé
`results/scores_p4_flip_stage_20261013`, flag
`score_p4_flip_shadow=0` par défaut aux quatre difficultés.
Il rejoue le score C70 historique et le score de cohorte sur le **même
vivier réellement admis**, après fit/cash/plancher, en gardant les
priorités C77/V88, le dénominateur décisionnel K_dec, le bonus AIR,
les exemptions R2/C121/V161/C82 et le tie-break par revenu. Le candidat
initial choisi par le moteur doit être reproduit par identité avant de
déclarer un flip, sinon `P4_FLIP_CONTRACT` invalide l'épisode. Les
tentatives sont tracées séparément des constructions, et la sonde modifie
le coût VM (toute différence de profit sous la sonde reste diagnostique).

Smoke moteur `scores_p4_flips_smoke_2x3_20261013` :
2 graines (1 et 314159) × 3 ans, **4/4 parties saines**,
`mismatch=0`, **aucune inversion de tête** jusqu'à 1972, malgré
un facteur AIR distinct dès l'exercice 1971 pour la graine 1.
Preuves et contrat :
`results/scores_p4_flip_stage_20261013/docs/scores_p4_flip_contract_20261013.md`.
La collecte diagnostique **5×5 sur cinq ans a été achevée** avec bundle
identique entre ses deux bras, 10/10 parties saines. L'analyse des dix
logs (`results/scores_p4_flip_stage_20261013/results/scores_p4_flips_dev5x5_20261013_flip_analysis.json`)
relève **5 878 passes aux rapports annuels** (1 249 doublement rejouées,
4 629 sans deux candidats, **0 désaccord de classement**). Elle confirme
**25 événements de bascule de tête au même tier C77/V88, même budget
admissible, services OD et modes distincts**, dont **15 ont atteint la
branche constructeur**. Ils surviennent **14 fois en 1972**,
**7 fois en 1973** et **4 fois en 1974** (aucun en 1970–71).
Quatre événements de tête et deux tentatives
surviennent après le dernier rapport annuel, d'où leur absence des
compteurs de résumé, mais ils sont présents dans les logs. Parmi les
cas explicites : RAIL passagers ↔ AIR hubhub en 1972, RAIL fret ↔ AIR
hubhub en 1972, AIR hubhub ↔ RAIL passagers en 1974. Les cinq graines
exposent au moins un épisode.

L'inversion **réelle de classement local** par P4 est donc enfin
démontrée ; une tentative demeure différente d'un build réussi, et
25 événements des deux bras de 5 graines ne font pas 25 observations
indépendantes. La perte du 5×5 avec la sonde active
(−42 405,4 £/an, 1V/3D/1E) est purement diagnostique, car la sonde
coûte des opcodes. L'effet économique demeure celui de la **porte pure
40×5 négative** (−43 730,3 £/an, 18V/21D/1E).

**Statut global :** étude des candidats concrets P2/P3/P4 menée jusqu'aux
portes économiques justifiables, aucune amélioration de 4 % démontrée
à cinq ans. La recherche de nouvelles politiques de score validées
reste ouverte, sans adoption prématurée des hypothèses rejetées.

## Complément de recherche causale P2/P4 (13 octobre 2026)

**Portée :** investigations supplémentaires après la sonde 25 flips/15
tentatives ci-dessus. Les chiffres du premier bilan demeurent valides ; les
nouveaux *stages* sont isolés, détachés de `c2a5be3`, sans modifier
`master` ou les défauts économiques. Les campagnes précédentes n'ont
**pas** été rejouées pour leur seul résultat négatif.

### P4 : résultat constructeur réel et première divergence

Stage `results/scores_p4_chain_stage_20261013`, rapport détaillé
`docs/scores_p4_chain_outcomes_20261013.md`, analyseurs
`sweeps/analyse_scores_p4_chain_20261013.py` et
`sweeps/analyse_scores_p4_chain_trajectories_20261013.py`.
Les nouvelles sondes de résultat constructeur restent sous le flag
`score_p4_flip_shadow=0` par défaut. Elles relient les IDs de
`P4_FLIP_HEAD` à `ATTEMPT`, au résultat effectif `OUTCOME`,
aux reprises A* RAIL `RESUME` et à `AIR_BUILD/RAIL_BUILD` et
`LINE_REVENUE` sur ID de ligne identique.

Smoke 2 graines × 3 ans sain, puis 5 graines développement × 5 ans,
**10/10 parties saines** avec `decision_log=1` et shadow actif dans
les deux bras (bundle
`c61d66dfb12174bfe79928da058d8e44efdb92004b5fa2592c937ddc407422ee`).
Ce 5×5 donne **30 événements de tête C77**, **18 tentatives constructeur**,
**6 builds AIR immédiats**, **4 RAIL différés** dont **3 repris puis
construits**, **8 rejets** et **12 têtes jamais tentées** : **9 nouvelles
lignes confirmées** par ID et marqueur constructeur. Une attribution
`pending → built` est admise uniquement après `P4_FLIP_RESUME`.

Quatre de ces lignes ont un relevé mature : RAIL historique L37
graine 123457, profit réalisé −2 531 £ contre prévu 40 074 £ ;
AIR P4 L29 même graine, 15 266 £ contre 79 076 £ ;
AIR P4 L26 graine 314159, 39 002 £ contre 101 641 £ ;
AIR P4 L41 graine 987653, 28 335 £ contre 74 036 £.
Ce sont profits **de ligne**, non profits nets du réseau C121.
La flotte a changé sur certaines AIR, empêchant d'y voir un estimateur
universalement transposable.

Première divergence mensuelle : graine 271828, trésorerie dès juin 1972
**avant** sa première inversion C77 observée en janvier 1973 ; graine
161803, trésorerie dès mai 1973 **sans aucun flip de tête enregistré**.
La sonde et ses opcodes peuvent déplacer le planning indépendamment du
score. Sur ce 5×5 *instrumenté*, ON−OFF vaut +4 976,2 £/an (2V/3D),
IC95 [−135 651,4 ; +174 321,8] £/an, **strictement diagnostic**.
Les SIGNS n'offrent pas de couverture opcode totale. Aucun gain de
politique P4 n'en est inféré.

### P2 : recalibration leave-one-seed-out

Nouveau stage `results/scores_p2_recal_stage_20261013`, script de preuve
`sweeps/analyse_p2_recal_oos_20261013.py`, rapport
`docs/scores_p2_recal_20261013.md`. Après dédoublement d'un premier
exercice par ligne : **43 lignes indépendantes**, dont **6 newpair sur
4 graines**, **28 hubsite sur 5**, **9 hubhub sur 2** ; les observations
réalisées proviennent d'un même bundle P2 et les 5 graines de
développement sont disjointes des 40 graines réservées à l'adoption.
Les amortissements C121_BUILD ont été joints **43/43**.

Médianes des médianes par graine (descriptives) : newpair 0,4493,
hubsite 0,3872, hubhub 0,4967. Bootstrap par graine 20 000 :
IC95 du **rapport newpair/hubsite [0,5815 ; 1,4690]**, qui inclut 1.
Le rejeu strict leave-one-seed-out trouve **3 inversions de tête
finançables de même C77** hubsite→newpair, sur trois graines distinctes,
en 1970–1971. Les trois têtes historiques ont été construites rapidement ;
**aucune alternative renversée n'a été construite dans le témoin**.
Faible support et absence de rendement contrefactuel empêchent de
qualifier un multiplicateur P2 ; ne pas choisir un coefficient agressif
post hoc. Tests hôte P2 **2 110/2 110** verts.

### P4 : panel véhicule-année en croissance (candidat, pas adoption)

Stage `results/scores_p4_adjust_stage_20261013`, protocole
`docs/scores_p4_vyear_contract_20261013.md`. Flag expérimental
`score_c70_vyear_cohort=0` aux quatre niveaux et C70 historique
inchangé OFF. Le calcul prend les profits de tous les véhicules
incumbents encore présents au rapport annuel et ignore les profits
partiels des nouveaux renforts : une flotte **augmentée** reste
mesurable, contrairement au filtrage stable-cohort rejeté. La perte
d'un incumbent ou une mutation non réconciliable retourne à un
échantillon neutre, pas à une sélection des seuls survivants.
Les véhicules vendus/crashés avant le rapport n'ont plus de profit
`GetProfitLastYear` interrogeable ; aucune allocation exhaustive
vehicle-year n'est prétendue. Les agrégats stockés sont des entiers
permille et un sidecar Save/Load vit hors du cache mensuel périmable
de >64 lignes.

Un **premier smoke Squirrel 314159 ×3 ans** est sain (2/2 parties),
le facteur AIR mesuré de l'exercice 1971 est 0,467625 et le profit
variante − témoin est +3 135 £/an ; **ce résultat d'une seule graine
est non qualifiant**. La première différence de trésorerie apparaît
en septembre 1971, avant le premier facteur C70 non neutre publié
en janvier 1972. Un flag diagnostique supplémentaire, indépendant et
OFF par défaut sur les quatre difficultés,
`score_c70_vyear_measure_shadow`, fait mesurer et sauver exactement
le même panel coûteux dans le témoin sans appliquer le facteur.

Le smoke **matched-shadow** `scores_p4_vyear_matched_smoke2x3_20261013`
(bundle `6d0e1ee55f31aa9d4640706cbf5a336219134ae9e8b6939a1a00074507526894`)
a terminé **4/4 parties saines** : graine 123457 rigoureusement identique
entre politiques sur trois ans ; graine 314159 avec delta terminal
−40 755 £/an, première divergence de caisse **01/09/1971** alors que
le premier facteur P4 différent n'est appliqué qu'en janvier 1972.
Le smoke seul ne permet donc pas de conclure à un effet du score.

Le **Save→Load moteur réel** `scores_p4_vyear_roundtrip_seed123457_7plus1_20261013.json`
du worktree isolé `results/scores_p4_vyear_roundtrip_stage_20261013`
a validé 7 années, recharge de `000000076.sav` (1er juin 1976), puis
un an supplémentaire, sans erreur Squirrel/Save : `LOAD_RECONCILE`
**saved=80, kept=79, dropped=1**. Le facteur AIR de l'exercice 1975
avant et immédiatement après reload est **identique : 0,55353385**,
avec `covered=58, neutral=6`. ROAD garde son repli C70 historique ;
RAIL change après une ligne supprimée à la réconciliation et n'est
pas une preuve de corruption de l'état. Cela démontre la persistance
réelle du sidecar au-delà de 64 lignes, mais pas la tenue du budget
Save 100k vers 150 lignes.

Deux campagnes **A/A de référence à politique identique** sur
`seed=314159`, trois ans, workers=1, même bundle ci-dessus et mêmes
réglages (`cohort=0, measure_shadow=1`) ont donné des résultats
distincts, sans intervention P4 : `profit_year` terminal
1 450 024 £/an et 1 453 159 £/an ; `company_value` 2 610 180 £
et 2 748 374 £. Premier écart des logs moteur le **13 août 1971**
sur `AAAHogEx CheckRenewal` (`0` contre `1` tick, 11 658 contre
11 659 opcodes), puis décalage d'un jour dans l'exécution du rival ;
premier écart mensuel de trésorerie OpexAI le **1er septembre 1971**
(`91 464` contre `91 468 £`), stations en octobre et flotte AIR en
novembre. Ce bruit de calendrier A/A explique pourquoi une divergence
ON/OFF avant la première application effective du score ne peut pas
être attribuée au calibrateur. L'origine technique première de ce
non-déterminisme reste à confirmer ; une différence de manifeste SHA
due aux identifiants de campagne ne doit pas être confondue avec une
différence de réglages explicites ou de bundle.

Contrôle contradictoire fort sur l'ancien bundle matched : le bras
**P4 ON** `seed314159` et la répétition **P4 OFF A/A ref2** sont
identiques aux **36/36 checkpoints**, sur **3 312 champs OpexAI** et
**2 592 champs AAAHogEx**, après retrait des seuls identifiants de
campagne. Les 10 354 lignes moteur par exécution présentent, après
normalisation des horodatages hôte et du simple `applied=0/1`, seulement
**17 différences de compteurs AAAHogEx**, sans divergence métier.
Pourtant le facteur AIR de janvier 1972 est différent :
`effective=0.46762502` contre `legacy=0.41249317`. Ce contrôle ne
prouve pas que le nouveau score est généralement inerte, mais **prouve
sur cette trajectoire qu'un score différent n'a modifié ni les choix
observés ni la performance**, et que le delta du smoke ON/OFF était
compatible avec une bifurcation d'exécution indépendante. Les compteurs
de `PerformanceCounter` AAAHogEx combinent opcodes et franchissements
de suspension (`tick×10 000`) ; les écarts de ~10k ne sont pas une
preuve d'autant de calculs métier supplémentaires.

### P4 véhicule-année : deux portes de développement 5×5, sans adoption

**Validation globale de l'implémentation :** 2 127 tests hôte passent après
correction minimale du chemin de sérialisation OFF B3 dans le seul stage
P4-adjust ; `git diff --check` est propre. Tests et logs :
`results/scores_p4_adjust_stage_20261013/results/scores_p4_vyear_host_suite_after_b3_fix_20261013.log`.

Les deux nouveaux bancs sont **strictement appariés à l'intérieur de chacun**
(5 graines communes, 5 ans, même bundle entre bras, 10/10 parties complètes),
avec image moteur `sha256:f4b2b9...`, max 10 CPU/10 workers, et bundle
`01f22c957c52c531092b92a84d87cf929f54073a662d74ef5a3c97d540b392ce`.
Ils sont **différents entre eux** par activation de la mesure coûteuse et
des sondes, et leurs écarts ne forment pas un nouveau A/B apparié entre
méthodes d'instrumentation.

| Banc | `profit_year` ON−OFF moyen | V/D/E | p Wilcoxon | IC95 bootstrap | `company_value` |
|---|---:|---:|---:|---:|---:|
| **Clean** (`measure_shadow=0`, `cohort_probe=0`, `decision_log=0`) | **+19 039,6 £/an** | 3/2/0 | 0,625 | [−23 875,8 ; +68 703,8] | −0,3144 % |
| **Matched-shadow** (`measure_shadow=1`, `cohort_probe=1`, `decision_log=1` dans les deux bras) | **−19 231,2 £/an** | 2/3/0 | 0,625 | [−81 545,6 ; +43 083,2] | +0,5069 % |

Seuil économique de la porte `gain_short` **+4 % de la référence** :
**+75 197 £/an** en clean et **+76 066 £/an** en matched. Les deux portes
affichent `fail_primary`, aucune borne inférieure de l'IC95 positive et
aucun signal de gain utile. Le 5×5 est une **porte de développement**, pas
une preuve d'un effet économique nul à toutes les graines. Ni le 40×5
P3 négatif ni le 40×5 stable-cohort négatif ne sont rejoués ; aucun 40×5
vehicle-year n'est indiqué sans nouveau signal plus robuste.

Écarts clean par graine (`profit_year` terminal ON−OFF, 1974) :
314159 **+40 210**, 271828 **−40 096**, 161803 **+10 565**,
123457 **−24 876**, 987653 **+109 395** £/an. Pour 314159, le premier
écart monétaire est en septembre 1971, avant la première correction
P4 publiée : impossible d'en inférer un gain dû au score. Les autres
premiers écarts clean apparaissent en 1973, après publication.

Écarts matched-shadow par graine : 314159 **−117 186**,
271828 **−80 195**, 161803 **+58 356**, 123457 **−12 966**,
987653 **+55 835** £/an. Premières divergences monétaires en
1972-08, 1972-12, 1973-03, 1972-04, 1972-05 respectivement, donc
toutes **postérieures** au premier facteur C70 vyear non neutre publié
entre le **10 janvier et le 6 juin 1972 selon la graine** (date
inférée de la dernière trace `OPEX` immédiatement précédente, et non
du seul numéro d'exercice). La chronologie est compatible avec une influence
du score, mais elle ne prouve ni une inversion C77 précise ni un
profit marginal d'une construction contrefactuelle. L'analyseur
reproductible du stage est
`sweeps/analyse_scores_p4_vyear_effect_20261013.py` ; provenance
`results/scores_p4_vyear_effect_comparison_20261013.json` et les deux
JSON/JSONL/logs de campagne dans le même worktree.

**Verdict à ce stade :** P2 sans calibration initiale hors échantillon
recevable, P3 et P4 stable-cohort économiquement rejetés sur 40×5,
P4 véhicule-année techniquement viable mais non convaincant sur deux
5×5 complémentaires et sensible au bruit d'ordonnancement. N'intégrer
aucun flag comportemental dans `master` sans une nouvelle hypothèse
testable et de nouvelles preuves de gain terminal robuste.

### Nouveaux rapprochements événementiels et test de causalité (suite)

Variante et analyseur conservés sur la branche distante expérimentale
`codex/scores-p4-vyear-experimental-20261013` ; données dérivées
`docs/scores_p4_causal_exposure_20261013.json`, script
`sweeps/analyse_scores_p4_causal_exposure_20261013.py`, **7 tests ciblés
verts** et suite complète hôte précédente **2 133 tests OK**.
Le rapprochement exact se fait par **politique / graine / chronologie /
mode / cargo / OD**, par identifiant de ligne `AIR_BUILD/RAIL_BUILD →
LINE_REVENUE`, et par `age>=2` pour les réalisations matures ; un
`PROJECT_CHOSEN` n'est jamais assimilé à une construction.

**Différence décisive :** les décalages de la **même OD** dans le calendrier
ne sont plus faussement comptés comme des changements de projet. Les
premiers choix d'une **OD réellement différente** interviennent aux
dates 1972-08-02 (314159), 1972-11-02 (271828), 1973-03-08 (161803),
1972-04-03 (123457), 1972-04-23 (987653). Seule 987653 a son
premier changement d'OD avant toute divergence *mensuelle de trésorerie*
observée dans **les deux compagnies du duel**. Pour 271828, AAAHogEx
diverge déjà au 1er novembre, avant la décision du 2 novembre, bien
que la caisse Opex reste apparemment identique jusqu'au 1er décembre.
**Aucune des cinq graines ne construit une OD différente avant
le premier écart de caisse mensuel de l'une ou l'autre compagnie.**
Les écarts intra-mensuels restent inconnus, donc aucun contrefactuel
C77 même état et aucune causalité de score ne sont démontrés.

**Échantillon de réalisation :** AIR/RAIL ont respectivement
58/67, 63/61, 56/52, 64/69, 72/75 constructions (référence/ON)
dans les cinq graines. **328 paires de lignes-années matures de même
mode/cargo/OD** sont retrouvées entre politiques. **280** ont la même
date de construction et le même nombre de véhicules au rapport,
mais **219/280** affichent des profits de ligne différents. Ni
véhicules/ordres identiques ni neutralité du réseau ne sont garantis ;
les 328 paires restent corrélées sur cinq graines et ne sont pas
328 observations indépendantes d'un effet marginal.

**Point d'appui concret suivant :** instrumenter, sous flag OFF par défaut,
une confrontation des classements **au même instant et dans le même monde**
à l'emplacement C77 : ensemble réellement finançable, mêmes priorités,
K_dec, coût de financement, facteur C70 alternatif et tête effective,
puis lier l'épisode au constructeur réel et à `lineId`/reprise RAIL.
Une telle sonde et un replay depuis une sauvegarde gelée sont les
prochaines épreuves nécessaires avant de financer d'autres gates
40×5 ou d'inférer un bénéfice contrefactuel.

**Critère inchangé :** seules les parties appariées à cinq ans avec
sondes OFF, budget VM contrôlé, Save/Load valide, valeur d'entreprise,
matériel/constructions et robustesse statistique peuvent justifier
l'intégration. Les résultats historiques rejetés P3 et P4 stable-cohort
ne sont pas remis en cause.
