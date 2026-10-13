# P0 RAIL — exposition du verrou A* sur parties C66 instrumentées (12/10/2026)

**Verdict : blocage sériel exposé, détournement d'un chantier alternatif rentable et constructible NON DÉMONTRÉ. Aucun correctif comportemental autorisé par cette preuve.** P0 1973 demeure ouvert. Pas de commit/push ni de nouveau moteur dans cette phase de dépouillement.

## Périmètre réel et santé

- Stage isolé `results/p0_rail_block_exposure_stage_20261012`, dérivé de `f6139d8` avec overlays causaux AIR identiques et adversaire AAAHogEx-115 figé ; `p0_rail_block_exposure_shadow=0` au défaut.
- C66 `p0_rail_block_exposure_diag3x5_20261012` : graines 42, 100, 999, années **1970–1974**, une réalisation OFF et ON par graine, **6/6 jeux sains**, 0 `failed_runs`, même bundle SHA256 `8d5bddab4abe76a6d70914ea556ab1cfe9bf1cb81c7df0aa2c1d94f64ec59065`.
- `--script-debug` a capturé les lignes du seul bras ON ; leur absence dans les trois logs OFF a été vérifiée indépendamment. Les flags OFF/ON sont les seules différences de réglage déclarées dans le manifeste. Les événements entre les deux bras **ne sont pas appariables** : la sonde coûte des opcodes et peut décaler l'ordonnanceur.
- Source des nombres : [résultat avec SHA256 des huit entrées](../evidence/review/p0_projects_conversion_20261012/p0_rail_block_exposure_diag3x5_20261012.json), décodeur [Python](../sweeps/analyse_p0_rail_block_exposure_20261012.py), **6 tests hôte verts** et `git diff --check` sans erreur. Les logs/manifestes originaux restent dans le stage gelé.

## Unités de mesure à ne pas confondre

`P0_RAIL_BLOCK` est émis aux deux refus `search_in_progress` de `_tryBuildRailProject` **après** éventuelle supersession ; la troisième branche `prep_dropped` n'est pas couverte. Le tableau `p0Seen` est stocké dans **l'objet `_railSearch` courant**, avec une clé OD/cargo/kind, une fois par épisode et clé ; le même OD peut donc reparaître dans un épisode ultérieur. `self_revisit=1` est une demande de l'OD déjà occupante, pas un projet concurrent. Pour un upgrade, l'OD affichée de l'occupant n'est qu'indicative. La sonde lit une fois `OpexAvailableCapital()` après dédup ; `pred_budget_capital` et `pred_profit` sont les estimations **du portefeuille**, pas un nouveau devis ni une preuve de constructibilité.

## Exposition effective du seul bras ON en 1973

| Graine | Toutes observations dédupliquées par épisode | Réobservations de la même OD occupante | Observations concurrentes | OD/cargo/kind concurrentes uniques | Uniques avec `cash_available >= pred_budget_capital` ET profit prédit positif | Observations concurrentes au rang 0 | Occupant des observations concurrentes |
|---|---:|---:|---:|---:|---:|---:|---|
| **42** | 77 | 3 | **74** | **26** | **25** | 2 | 57 recherche primaire, 17 upgrade |
| **100** | 5 | 1 | **4** | **4** | **4** | 2 | 1 primaire, 3 upgrade |
| **999** | 0 | 0 | **0** | **0** | **0** | 0 | aucune occurrence |

Les 74 refus non-self de la graine 42 comprennent plusieurs apparitions des mêmes OD dans des épisodes différents : **26 clés uniques seulement**. L'âge d'occupation calculable atteint **113 jours** sur 42 et **109 jours** sur 100 ; les upgrades ont souvent `startDate=-1`/âge inconnu. Sur la graine 999, la sonde voit deux OD bloquées en 1972 puis **165 observations concurrentes / 81 OD uniques en 1974** : cette concentration tardive du *bras ON* ne démontre aucun blocage alternatif en 1973 du témoin historique. L'absence d'exposition ON en 1973 interdit de généraliser un diagnostic RAIL identique aux trois graines.

**La plupart des projets bloqués ne sont pas au rang 0**. Même une OD unique disposant d'une trésorerie supérieure à son capital prévu n'est pas un chantier immédiatement réalisable : contrôles de sites, environnement et emplacement, trajet A*, coût réel, matériel et lignes existantes demeurent inconnus. La déclaration `physical=unknown` dans chaque trace n'est pas cosmétique. On ne peut ni totaliser les 25/4 comme « lignes perdues », ni additionner les profits prédits comme gain récupérable.

## Intrusion et résultat économique ON−OFF : ne pas qualifier comme variante

Le `profit_year` comptable 1973 varie sur les trois mêmes graines (sonde ON moins sonde OFF) de **−75 831 £** (42), **−22 251 £** (100), **−48 941 £** (999). Il s'agit d'un **effet de la présence de la sonde / trajectoire**, sans modification volontaire de règle d'admission et sans puissance de gate. C66 3×5 n'est pas une porte V102 ; il n'établit ni gain potentiel ni bénéfice d'un scheduler concurrent. La divergence des parties impose de conserver chaque observation dans sa propre trajectoire.

## Ce qu'exige le prochain contrefactuel transactionnel

1. **Exposition → admissibilité** : capturer à l'épisode exact, pour une *OD prioritaire réellement concurrente*, les origines, cargo/kind, projet, devis disponible, état de la ligne/admission, et les données de site. N'ajouter aucun calcul de vérification potentiellement mutateur dans le bras témoin. Une sonde ON/OFF ne suffit pas à appairer deux épisodes.
2. **Admissibilité → constructibilité** : il faut soit une branche contrefactuelle du **même état moteur pré-décision** avec contexte A* et projets injectés/reconstitués sans changement économique antérieur, soit reconnaître le verdict `unknown`. Les campagnes présentes n'ont pas de `.sav` brutes retenues. C66 `--retain-savegames` archive des sauvegardes périodiques, **pas** un checkpoint au tick précis du refus ; `Load` réinitialise `_railSearch`/pathfinder et le portefeuille, donc rejouer `-g` n'est **pas** une intervention équivalente.
3. **Constructibilité → adoption** : une fois un autre chantier prouvé réalisable dans les conditions du blocage, isoler le mécanisme sans nouveau score/seuil arbitraire derrière un flag OFF ; tests Squirrel, Save/Load, smoke 1×1, A40×3 `gain_short` puis B20×10 si A survit, opcodes globaux et services AIR/RAIL. Une seule campagne Docker, jamais en concurrence.

**Priorité P0 parallèle :** la rupture AIR 1973 a une exposition bien plus large (18/19 pertes de cohorte d'avions sur mêmes OD ; 310 lignes à flotte élargie sur 19 graines avec anciens avions en fort recul). Auditer débit réel, charge et coût marginal de renfort avec les compteurs C117 avant tout changement de cible de flotte ; la concurrence visible C121 a déjà échoué à sa porte A et reste OFF.
