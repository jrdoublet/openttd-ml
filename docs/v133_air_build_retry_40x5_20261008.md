# V133 — diagnostic 40 graines × 5 ans (08/10/2026)

Demande utilisateur : après synchronisation Git, exécuter V133 sur 40 graines × 5 ans. V133 est `v133_air_build_retry` : une quarantaine temporaire (730 jours) de villes après échec physique AIR et un sauvetage local des autres paires d'un lot `batch_plan_dead`. La porte A standard à 40×3 figurant déjà dans `docs/taches.md` sur `origin/master` a échoué (`fail_primary`, −10,3 k£/an). Cette nouvelle mesure à 5 ans est **diagnostique**, sans remplacement rétrospectif de la porte A V102 40×3.

## Pré-enregistrement avant partie

- Source : `origin/master` à `11261de03d715bbcf7152f70e341becd86f12aee` (les commits distants `9df6e9f` et `11261de` ont été récupérés). `master` local contient `7b5964b` qui diverge et des edits concurrents : aucun merge/rebase appliqué ; code exécuté dans la copie isolée `.wt_v133_diag_20261008` issue du dernier `origin/master`. Le répertoire AAAHogEx ignoré par Git est relié à la référence locale et copié par le gel du harnais.
- Bras exacts : référence `OpexAI[v133_air_build_retry=0]` ; variante `OpexAI[v133_air_build_retry=1]`. Autres réglages au défaut commun, même arbre de code et adversaire AAAHogEx gelé ; défaut V133 reste 0.
- 40 graines canoniques `SEEDS_40`, une répétition, 5 ans, 80 parties appariées contre AAAHogEx. Métrique primaire = `profit_year` Opex variante moins référence à l'année terminale ; garde `company_value` sur ratio des moyennes, perte tolérée 5 %.
- Règle pré-enregistrée : `gain_short` **à l'horizon explicitement demandé de 5 ans** (`--required-seeds 40 --required-years 5 --years 5`), seuil relatif 4 %, Wilcoxon bilatéral p < 0,05, borne basse IC95 bootstrap de la moyenne > 0, delta moyen ≥ 4 % du profit moyen de référence, valeur ≥ −5 %. Bootstrap standard : 20 000 tirages, graine 0. Couverture : 40/40 paires saines, années/quatre trimestres complets, aucune erreur moteur attribuée.
- Runtime : Docker Desktop local `desktop-linux`, image `openttd-lab` sha256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, volume `openttd-lab-home`, **7 CPU / 7 workers / 8 Go RAM**, swap plafonné à 8 Go. Une seule campagne à la fois ; Docker confirmé libre juste avant le lancement.
- Vérifications préalables : 8/8 contrats ciblés `test_v133_air_build_retry.py` ; `bench_1v1_5y_20seeds.py --selftest` réussi. Smoke V133 actif déjà documenté dans `docs/taches.md` sur la même version V133 ; pas de changement Squirrel supplémentaire.
- Campagne : `v133_air_build_retry_40x5_20261008_r1` ; sortie principale `results/v133_air_build_retry_40x5_20261008_r1.json`, checkpoints `.jsonl`, manifeste `.manifest.json`, bundle `_bundle` et journaux `_engine` dans le répertoire principal `results/`, accessible via `--mount-root` sur la copie isolée.

Verdict et contrôle final : à consigner après exécution. Ne pas modifier le défaut et ne pas déclencher de porte B automatiquement.

## Exécution démarrée

La campagne `v133_air_build_retry_40x5_20261008_r1` est terminée, code retour **0**, avec **80 parties** et **7 workers**. Source gelée, Git `11261de03d715bbcf7152f70e341becd86f12aee`, **dirty=0** ; bundle SHA256 `f1cbcb7dcee190c01be6d14d2c70fb09a0295fef56ed341b2bb966b7c6f5c059` ; manifeste SHA256 `96207ca5bb9b91653f0d0790ed959a9704fc2f13fde2f20635dac26e691abbf0`. Docker image ID SHA256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.

## Résultats finaux

Le rapport `results/v133_air_build_retry_40x5_20261008_r1.json` indique : **80/80 parties `complete`**, `failed_runs=0`, **40/40 paires**, `comparison_complete=true`, `adoption_sample_complete=true`, `metric_coverage_complete=true` ; pas de problème de santé ou de couverture.

`profit_year` terminal (Opex V133=1 − Opex V133=0) : moyenne **−45 801,25 £/an**, médiane **−73 787,5 £/an**, V/D/E **15/25/0**, Wilcoxon bilatéral **p=0,0770006**, IC95 bootstrap 20 000 tirages **[−96 405,825 ; +7 295,475] £/an**. Seuil positif préenregistré de 4 % : **+66 843,959 £/an**. `company_value` : ratio des moyennes **−2,146231 %** ; garde de valeur −5 % tenue. Verdict brut **`fail_primary`** : absence de gain démontré à cinq ans. Le delta négatif est descriptif, l'IC traversant zéro ne démontre pas une perte significative à ce niveau de confiance.

La porte A 40×3 de V133 avait aussi échoué ; la demande de 40×5 ne constitue pas une qualification V102 permettant l'adoption. Le réglage demeure à défaut **0**, aucune porte B automatique. `master` local reste divergent avec `origin/master` et ses modifications de travail sont préservées ; l'expérience a exécuté exactement le dernier code distant dans la copie isolée, sans fusion/commit/push supplémentaire.

## Analyse des mécanismes après banc

La lecture causale du code et les trajectoires physiques sont détaillées
dans le [diagnostic commun V133/V134](diagnostic_v133_v134_air_20261008.md).
La quarantaine agit à l'échelle de la **ville**, alors qu'un échec peut ne
concerner qu'un seul site, et bloque même la réutilisation des hubs ; le
compteur `V133_BATCH_SALVAGE` ne prouve pas de construction supplémentaire.
La part exacte de ces mécanismes dans le recul observé reste non instrumentée.
