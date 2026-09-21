# C70 — Calibration réalisé/prédit par mode, préalable à l'étape 2 de C69

**Contrat écrit avant la mesure, 2026-09-21.** Ouvert parce que le critère C5 de C69 a échoué
(`11_goulot_decision.md` §13.3). **Décision utilisateur du 2026-09-21 : respecter C5.** L'étape 2
de C69 attend la fermeture de cette fiche.

## 1. Pourquoi C5 compte pour C69

En régime « décision », C69 classe par profit **absolu** prédit. Un mode surestimé gagne alors les
arbitrages entre modes, et l'argmax choisit en priorité les projets les plus surestimés (§9 de
C69, risques 2 et 3). Le ratio actuel `P/C` est moins exposé, parce que le biais se divise
partiellement par le capital.

## 2. Ce que l'on sait, et ce qui ne fait plus foi

| mode | mesure | source | statut |
|---|---|---|---|
| air | 0,93–1,31 par convoi, 8 à 28 lignes par graine | C69 §13.3 (6 ans) | mesuré, échantillon suffisant |
| route | 1,6–1,8, **une seule ligne** par graine | C69 §13.3 | non concluant |
| rail | 0,46–1,14, **une seule ligne** par graine | C69 §13.3 | non concluant |
| route, rail, air | 0,93 / corrigé / 1,04 (D4) | `taches_archive_2026-09-09.md` | ⛔ antérieur au 09-09, ne fait plus foi |

Les autres lignes de bus viennent de `task_town` (`purpose = "town_growth"`, prédiction nulle
par construction) : elles sont hors du portefeuille et restent exclues.

## 3. Étape 1 — mesure, aucune décision changée

**Instrumentation** (sous `probe_portfolio`) : une ligne `C69_BOTTLENECK phase=line_calib` par
ligne mature et par an : mode, identifiant, âge, profit et revenu prédits, profit et revenu
réalisés, convois à la construction (`trains0`) et convois actuels.

**Protocole** : 20 graines × 10 ans, solo, graines de `bench_v2.py`. Les longues parties sont
nécessaires parce que route et rail ouvrent environ une ligne de portefeuille par partie.

**Mesures, par mode** (médiane par ligne sur ses années pleines, puis médiane entre lignes : chaque
ligne pèse autant) :

⚠️ **Année pleine = `age ≥ 2`.** Une ligne bâtie en 1970 a `age = 1` au rapport du 1er janvier
1971, mais son `GetProfitLastYear` ne couvre qu'une fraction de 1970. Le C5 de C69 retenait
`age ≥ 1` et mélangeait donc des années partielles : ses ratios sont biaisés, dans un sens inconnu.

- **M1** : médiane du ratio profit réalisé/prédit **par convoi** (réalisé × `trains0` / convois) ;
- **M2** : la même médiane, restreinte aux lignes-années où la flotte n'a pas changé
  (`convois == trains0`). Elle écarte le biais de la normalisation par convoi : un convoi ajouté
  partage la demande, donc M1 sous-estime ;
- **M3** : nombre de lignes distinctes et de lignes-années ;
- **M4** : dispersion, comme écart interquartile.

## 4. Critères de fermeture — écrits d'avance

| cas | condition | suite |
|---|---|---|
| **A. pas de biais** | ≥ 20 lignes distinctes pour chaque mode présent dans les divergences C69, et max/min des M2 par mode ≤ 1,5 | C5 levé ; étape 2 de C69 |
| **B. biais mesurable** | ≥ 20 lignes, et max/min > 1,5 | étape 2 de C70 : facteur par mode (§5), puis re-mesure |
| **C. échantillon insuffisant** | < 20 lignes distinctes pour un mode | ce mode est déclaré **non mesurable** ; revenir vers l'utilisateur avec les effectifs, **sans** décider seul d'une dérogation |

M2 est retenu plutôt que M1 parce qu'il ne dépend d'aucune hypothèse de linéarité. Si M2 a moins
de 20 lignes, on décide sur M1 et on le signale.

## 5. Étape 2 conditionnelle — facteur glissant, sans constante

Seulement dans le cas B. Chaque mode reçoit un facteur `k_m` égal à la médiane glissante M1 sur les
lignes mûres de **la partie en cours**, et `k_m = 1` tant que le mode n'a aucune ligne mûre. Le
profit prédit est multiplié par `k_m` avant le classement. C'est le « facteur de calibration
mesuré par mode » du §12 de C69 : il n'introduit pas de constante, et il remplacerait
`AIR_PAX_REVENUE_CALIBRATION_PCT = 104` si le banc le confirme.

⚠️ Question ouverte, à trancher avant le code de l'étape 2 : avec une seule ligne mûre, le facteur
est très bruité. Soit on attend deux lignes, et c'est un seuil ; soit on accepte ce bruit.

## 6. Hors périmètre

- Recalibrer les estimateurs physiques eux-mêmes (traction, demande, temps de trajet).
- Le fret : il n'apparaît pas dans les divergences de C69.
- Les lignes `town_growth`.

---

## 7. Résultats de l'étape 1 (2026-09-21)

20 graines × 10 ans, solo, **0 échec**. Brut : `results/c70_calib_raw_10y_20seeds.jsonl` ;
analyse : `sweeps/analyse_c70_calibration.py` (selftest inclus).

🔴 **Correction de mesure avant verdict.** `profitAnnual` retire l'amortissement prédit, alors que
`GetProfitLastYear` n'amortit rien. Comparés tels quels, les deux profits donnaient un écart
apparent sur les coûts (0,58–0,73) qui n'existe pas. Le réalisé est donc diminué de `pred_amort`
(par convoi initial) avant le ratio. Le premier passage, sans cette correction, donnait air 1,51,
route 1,73, rail 0,90.

| mode | lignes (M2) | lignes-années | M1 | **M2** | IQR M1 |
|---|---:|---:|---:|---:|---:|
| air | 684 (424) | 3 508 | 1,27 | **1,44** | 0,75 |
| route | 58 (58) | 438 | 1,51 | **1,51** | 0,27 |
| rail | 27 (24) | 143 | 0,68 | **0,87** | 1,11 |

**Verdict : cas B.** Tous les modes dépassent 20 lignes, et le max/min de M2 vaut **1,74**, au-delà
de 1,5.

**Décomposition** (lignes-années à flotte inchangée) : le coût de fonctionnement réel/prédit vaut
**1,00** dans les trois modes. **Tout le biais est dans le revenu** : air 1,28, route 1,35, rail
0,90. Le modèle sous-estime les revenus de l'air et de la route, et surestime légèrement ceux du
rail.

**Deux observations qui pèsent sur l'étape 2 :**

- **L'air dérive avec l'âge de la ligne** : 1,80 à 2 ans, 1,39 à 4 ans, 1,07 à 6 ans. Un facteur
  glissant calculé sur toutes les lignes mûres mélange ces âges ; il colle mieux s'il est calculé
  sur les jeunes lignes, qui ressemblent aux projets classés.
- **Le rail est rare** : environ 1,4 ligne par partie de 10 ans. Un facteur glissant rail restera à
  1 la plupart du temps, alors que la route atteint 2 à 3 lignes et l'air plusieurs dizaines.
