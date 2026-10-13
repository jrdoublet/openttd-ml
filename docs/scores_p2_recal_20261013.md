# P2 — réétalonnage hors graine depuis les 57 exercices joints (13/10/2026)

## Verdict et limites de cette étape

**Aucun coefficient P2 comportemental économiquement défendable n'est adopté ni
implémenté.** Il existe désormais une exposition mesurée de **trois flips de tête
C77 parmi 202 sélections complètes non vides** (dans trois graines de validation
laissées successivement de côté), mais le signe relatif de l'avantage
newpair/hubsite n'est pas robuste au bootstrap par *graine*, et le profit des
trois alternatives n'a pas été réalisé. Un flip de tête finançable n'est pas une
construction réussie ni une amélioration économique de cinq ans.

Stage exclusif : `results/scores_p2_recal_stage_20261013`, worktree détaché
depuis `c2a5be39043e64c754d9f659057dab3221e3e935`. Les overlays du P2
précédent (4 fichiers `.nut` d'instrumentation, ses 2 analyseurs et tests) ont
été copiés à l'identique ; la sonde `score_cold_prior_shadow` reste **OFF aux
quatre difficultés**. Aucun flag de score comportemental `score_cold_prior`
n'est ajouté. Aucun autre worktree/master modifié, aucun Docker/commit/push.

## Sources, provenance et hypothèses hors échantillon

- `../scores_p2_stage_20261013/results/scores_p2_dev5x5_20261013.json`,
  `.manifest.json`, `_execution_analysis.json` et cinq journaux
  `scores_p2_shadow_seed*_r0.log` du dossier `_engine`.
- Campagne `scores_p2_dev5x5_20261013` : un seul bundle
  `e9f750665f438d28f82a6e7cd93659a04472eedd4899ae6b6688289e2b708227`
  sur les dix parties. Les cinq variantes de développement ont
  `score_cold_prior_shadow=1,decision_log=1`, les cinq références
  `score_cold_prior_shadow=0,decision_log=1`. Ce ne sont **pas** deux politiques
  de score différentes. Les journaux de réalisation sont ceux du bras sonde.
- Développement : graines **123457, 161803, 271828, 314159, 987653**. Les
  40 graines de validation pré-enregistrées ont été contrôlées **uniquement
  pour leurs identifiants** via la gate P4 (pas pour leurs gains ou résultats) :
  **intersection vide**. Les prévisions LOSO n'emploient jamais les mesures
  de la graine évaluée. Il ne s'agit **pas** d'une validation économique sur
  ces 40 graines : aucun bras P2 score modifié n'existe.
- Les ratios historiques (44 newpair/102 hubsite/117 hubhub/17 RAIL fret)
  du document `docs/estime_realise_par_ligne_20261012.md` ont été mesurés
  sur des anciens bundles, horizons, modèles et profondeurs différents. **Ils
  ne sont pas fusionnés** avec le bundle P2 de cette étude.

## Exposition et maturité des données

La jointure existante `SCORE_COLD_P2_*` →
`PROJECT_CHOSEN/AIR_BUILD/C121_BUILD` → `LINE_REVENUE` totalise
**281 constructions AIR**, **83 liaisons à une tête de sélection P2**, et
**327 lignes-années matures**. La garde existante (choix et construction joints,
absence de mutation *connue*, N présent au rapport égal au N construit,
profit prédit au rapport égal à celui de la construction et tête avec candidat)
ne retient que **57 lignes-années provisoirement comparables**. Une ligne peut
fournir plusieurs années : il ne reste que **43 lignes initiales distinctes**
avec première année admissible. Toutes les 43 ont une première observation
d'âge **2** au rapport : 4 exercices clos en 1971, 39 en 1972.

| Famille AIR | Lignes-années provisoires | Lignes distinctes | Graines distinctes | Même prédiction à l'élection et à l'achat, sur premières lignes |
|---|---:|---:|---:|---:|
| newpair | 11 | **6** | **4** | **4/6** |
| hubsite | 35 | **28** | **5** | **28/28** |
| hubhub | 11 | **9** | **2** | **9/9** |
| Total | **57** | **43** | **5** | **41/43** |

Les chiffres du tableau sont des lignes d'une même partie, **non** 43 graines
indépendantes. Les 2 nouvelles lignes newpair dont la prédiction évolue entre
sélection et construction démontrent que la clé OD/moteur ne garantit pas la
même décision économique. Les flottes qui achètent puis revendent un appareil
avant l'exercice annuel peuvent encore passer les gardes de N et d'événements
connus. Les 17 anciennes lignes fret ne donnent aucune cohorte RAIL de ce
bundle et aucun coefficient voyageurs.

La source `C121_BUILD` contient `actual_amort`, joint à **43/43 lignes**
initiales, autorisant une **sensibilité descriptive** où le ratio brut
`LINE_REVENUE.real_prof / pred_prof` devient
`(LINE_REVENUE.real_prof − C121_BUILD.actual_amort) / pred_prof`. Cette
soustraction évite de traiter l'amortissement initial comme un revenu, mais
ne corrige **ni** les achats/renouvellements cachés, **ni** la cannibalisation de
revenus entre lignes et hubs, ni les variations de réseau. Elle **ne produit
pas** un rendement marginal contrefactuel de l'investissement nouveau.

## Estimation inter-graines et incertitude

Pour chaque famille, prendre la première année par ligne, faire la médiane
**au sein de chaque graine**, puis la médiane de ces **médianes de graines**.
Bootstrap **20 000 rééchantillonnages des cinq graines entières**, seed 0,
en conservant leurs groupes de lignes ; aucune ligne annuelle n'est rééchantillonnée
comme si elle était indépendante.

| Famille | Facteur descriptif corrigé amortissement | Intervalle bootstrap 95 % par graine | Support |
|---|---:|---|---|
| newpair | 0,4493 | **[0,1902 ; 0,4963]** | 6 lignes / 4 graines |
| hubsite | 0,3872 | **[0,3147 ; 0,4154]** | 28 lignes / 5 graines |
| hubhub | 0,4967 | [0,4788 ; 0,5146] **non interprétable** | 9 lignes / **2 graines** |

La quantité cruciale pour arbitrer **newpair plutôt que hubsite** est le ratio
relatif des deux facteurs, pas leur seule distance à 1 :
**IC95 cluster-bootstrap [0,5815 ; 1,4690]**. Le ratio dépasse 1 dans
**85,26 % des tirages** seulement : les graines disponibles ne démontrent pas
un avantage relatif de signe stable à 95 %. La pseudo-précision de l'intervalle
hubhub sur seulement deux graines interdit son utilisation.

Le rejeu LOSO *descriptif* sur les cinq graines (quatre pour entraîner,
une exclue pour mesurer l'exposition) emploie uniquement les deux familles
ayant au moins trois graines et quatre lignes dans l'échantillon
d'entraînement. Il laisse hubhub et tout RAIL à facteur **1**, faute de support.
Les facteurs s'échelonnent entre **0,418–0,480** (newpair) et
**0,357–0,399** (hubsite), sans aucune sélection de coefficient sur la réussite
des inversions. Une sensibilité linéaire pré-déclarée vers le facteur neutre 1
(`alpha=0,0.25,0.5,0.75,1`) donne respectivement **0, 1, 2, 2, 3**
flips ; ce n'est **pas** une recherche de réglage ni une proposition de
paramètre. Les écarts prédictifs au ratio réalisé diminuent en LOSO par
rapport au facteur neutre, mais cette cible est imparfaite et non économique.

## Flips C77 : preuve exacte et ce qu'elle ne démontre pas

L'analyseur existant rejoue **202 passes non vides** après budget et plancher
à priorité C77/V88 constante, avec **zéro mismatch** entre la tête recalculée
et la tête réelle. **126 passes** disposent d'un autre service OD dans le même
tier, dont **108** avec concurrent AIR éligible au prior et **12** avec
concurrent RAIL ; aucune inversion RAIL n'est observée.

| Graine laissée hors apprentissage | Passe et date | Tier C77 | Tête historique réellement bâtie | Projet alternatif sous ratio LOSO |
|---|---|---:|---|---|
| **314159** | 174 — **19/12/1970** | **2** | `hubsite 56868→34988` bâti **21/12/1970** | `newpair 34988→6934` |
| **161803** | 296 — **06/09/1971** | **2** | `hubsite 61276→16326` bâti **08/09/1971** | `newpair 16326→49193` |
| **987653** | 379 — **18/10/1971** | **0** | `hubsite 14027→59431` bâti **19/10/1971** | `newpair 22228→59431` |

Les trois alternatives sont **simultanément finançables** dans le snapshot
de sélection et ont un C77/V88 identique à la tête historique, mais
**0/3 n'ont été construites dans le témoin** pendant cette partie. Leur
constructibilité réelle après les autres tâches, leurs nouveaux délais,
leurs mutations de hubs et leurs profits ne sont pas connus. Par exemple,
l'existence d'un projet de nouvelle ligne au rang 0 contrefactuel ne garantit
pas un site aéroportuaire constructible ni l'absence d'effet négatif sur le
revenu des lignes existantes. Le profit du témoin sur son choix effectif ne
peut pas être attribué au candidat alternatif non réalisé.

Ces 3 inversions valident l'existence d'une **exposition C77 réelle au score**,
non la rentabilité du prior. Elles sont compatibles avec l'incertitude sur
le ratio inter-familles ; choisir aujourd'hui un niveau de shrinkage qui
préserve ces inversions serait un *tuning a posteriori* interdit.

## Critères non franchis et décision

1. **Validité économique** non établie : rendement observé individuel
   non équivalent à l'accroissement de profit consolidé net C121/effets de hub ;
   correction d'amortissement limitée au plan initial.
2. **Indépendance et précision** insuffisantes : 6 newpair/4 graines,
   9 hubhub/2 graines ; ratio relatif déterminant **incluant 1** en IC95.
3. **Hors échantillon économique** absent : LOSO fait un vrai split par graine
   pour le **rejeu de classement**, pas une comparaison de profits 5 ans de
   politique; les 40 graines restent réservées et intouchées.
4. **Causalité d'achat** non close : 3 changements de tête hypothétiques et
   aucun de leurs achats alternatifs, aucun chemin complet
   choix→tentative→construction→effets flottes/hubs→profit terminal.
5. **Portabilité** non démontrée : corpus de 2026-10-12 mêlé à d'anciens
   bundles et variantes; aucun coefficient RAIL commun au stage P2.

**Conséquence : aucun flag comportemental P2, aucun smoke moteur de variante
ni A40×5 économique à lancer aujourd'hui.** Un nouveau candidat devra
d'abord répondre à ces cinq critères, avec un modèle des externalités et
une règle de shrinkage fixés *avant* toute nouvelle mesure des flips/gains.
Il faudrait une validation indépendante de l'impact de construction et de
profit sur les 40 graines **après** définition d'une politique économiquement
identifiée. Ne pas utiliser les 3 flips LOSO pour choisir les coefficients.

## Reproduction hôte, sans Docker

Depuis le nouveau worktree :

```powershell
python -X utf8 sweeps/analyse_p2_recal_oos_20261013.py `
  --execution ../scores_p2_stage_20261013/results/scores_p2_dev5x5_20261013_execution_analysis.json `
  --manifest ../scores_p2_stage_20261013/results/scores_p2_dev5x5_20261013.manifest.json `
  --campaign ../scores_p2_stage_20261013/results/scores_p2_dev5x5_20261013.json `
  --validation-gate ../scores_p4_behavior_stage_20261013/results/scores_p4_stable_gateA40x5_20261013.json `
  --engine-dir ../scores_p2_stage_20261013/results/scores_p2_dev5x5_20261013_engine `
  --out docs/p2_recal_oos_resultats_20261013.json
python -X utf8 -m unittest discover -s sweeps -p "test_analyse_p2_recal_oos_20261013.py" -v
```

Preuves quantitatives générées :
`docs/p2_recal_oos_resultats_20261013.json` (profils descriptifs par graine,
bootstrap cluster et tous les flips avec lien aux constructions du témoin).
