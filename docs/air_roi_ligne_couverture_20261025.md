# AIR-ROI-LIGNE-1 — couverture observable des constructions nouvelles

**25 octobre 2026 — audit hôte uniquement, aucun banc et aucun réglage modifié.**

Entrée : 40 journaux `reference_seed*_r0.log` de
`results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine`.
Reproduction :

```powershell
python -X utf8 sweeps/diag_air_roi_ligne_coverage.py `
  --logs results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine `
  --out results/air_roi_ligne_coverage_20261025.json
python -X utf8 -m unittest discover -s sweeps -p test_diag_air_roi_ligne_coverage.py
```

## Couverture réelle de la jointure

| Mesure | Effectif |
|---|---:|
| Parties indépendantes analysées | 40 |
| Événements `AIR_BUILD` / IDs de ligne distincts | 1 932 / 1 932 |
| Correspondance chronologique `PROJECT_CHOSEN` AIR, même paire de tuiles et même date | 1 932 |
| Relevés annuels `LINE_REVENUE` AIR | 14 457 |
| Relevés immatures (`age` inférieur à 2), censurés | 1 948 |
| Relevés mûrs (`age` au moins 2), joints par `line` et année | 12 509 |
| Lignes construites avec au moins un relevé mûr | 1 921 |
| Lignes construites sans relevé mûr | 11 |
| Lignes mûres dont la flotte diffère au moins une fois de la flotte initiale | **1 808 / 1 921 (94,1 %)** |
| Relevés mûrs avec flotte différente | **10 225 / 12 509 (81,7 %)** |
| Coûts `AIR_BUILD` renseignés mais uniquement devis de plan | 1 932 |
| CAPEX d'infrastructure réellement payé isolable | **0** |
| Profit marginal contrefactuel avec et sans construction | **0** |

La jointure événementielle est disponible ; la **calibration d'un ROI réellement
marginal** ne l'est pas. `LINE_REVENUE.real_prof` porte le profit de la ligne entière
et peut inclure renforts, rénovations et churn. Une conversion en rendement du
capital sur `AIR_BUILD.cost` utiliserait un *devis* pour dénominateur et un
profit de flotte évolutive pour numérateur ; ce ne serait pas un ROI réalisé.

La correspondance `PROJECT_CHOSEN` est celle de la paire `src/dst` le même
jour, pas une identité persistante du projet sous Save/Load, et ne peut pas
garantir à elle seule les coûts/alternatives réellement exécutables.
Le lecteur ignore les relevés immatures, refuse les doublons `.log/.gz`
contradictoires (même si les seuls comptages coïncident), signale les IDs
réutilisés et les doublons année/ligne. Quatre contrats host-only vérifiés.

**À faire avant clôture de la tâche :** attribuer les dépenses réelles aux
gares/aéroports, avions et terrassements du nouveau chantier ; distinguer
renforts V161 et renouvellements V252, traiter la censure des vieux avions,
ajouter un témoin comparable au moment de la décision et mesurer l'opportunité
écartée. Ne pas calibrer un coefficient financier avec les seuls ratios de
revenu ligne entière / coût prévu, et ne pas lancer de qualification A/B sans
nouvelle hypothèse et protocole figé.
