# Diagnostic opcodes 1970–1973 : archive traçable

Rapport de référence : [`docs/diagnostic_opcodes_1970_1973_20261012.md`](../../../docs/diagnostic_opcodes_1970_1973_20261012.md).
Autopsie P0 complémentaire : [`docs/diagnostic_projects_causal_20261012.md`](../../../docs/diagnostic_projects_causal_20261012.md).
Le profil est descriptif : **cinq graines** en duel partagé avec AAAHogEx ;
les anciens résultats CD40×4 et les anciennes études de cadence restent
des références externes, jamais fusionnées dans ces moyennes.

## Contenu

- `default_4y.json` et `default_4y.manifest.json` :
  campagne C66.3 sans sondes, 1970–1973, code `master` au HEAD
  `f6139d8` propre. Référence de performance économique.
- `profiled_5y.json` et `profiled_5y.manifest.json` :
  campagne C66.3, mêmes cinq graines, sondes
  `probe_loop_ops=1,probe_scheduler=1,catalog_cost_probe=1`
  et `--script-debug`, code `f6139d8` **avec instrumentation
  diagnostique non commitée**. Cinq années simulées, quatre premières
  publiées : nécessité d'atteindre janvier 1974 pour avoir le
  `LOOP_OPS y=1973`.
- `profiled_engine_logs.zip` : cinq journaux moteur complets
  `opcode_detail_worker_seed{42,100,999,1234,5678}_r0.log`, avec
  flux OpexAI (`[0]`) et AAAHogEx (`[1]`) sur la même carte.
- `breakdown.json` : agrégats annuels par graine et moyennes des cinq
  graines, sections `loop`, `task`, `c39`, `air`, `catalog_slice`,
  `projects`, `selection`, `idle`, `aaa_partial` et autres.
  **Les sections imbriquées ne s'additionnent pas** ; `sleep_left`
  n'est pas une dépense.
- `probe_loop_ops_patch.diff` : patch hôte exact du profileur OpexAI
  (parité de la boucle Save et comptage de l'opportunité par type de worker).
  À appliquer uniquement pour reproduire cette instrumentation ;
  aucun code de stratégie n'est changé au défaut.
- `projects_calls.json` : distributions p50/p95/max et coûts par appel
  `PROJECTS_COST`, chemins `SELECTION_LIGHT`, classes `SCHED_IDLE` et
  nombres de constructions, avec détail **par graine** et pooling des
  cinq graines. Il s'agit de sous-fenêtres non additionnables au C39.
- `air_fleet_reselect_calls.json` : attribution temporelle à chaque
  `SCHED_IDLE` du dernier événement `SELECTION_LIGHT path=reselect`
  survenu dans sa fenêtre. En 1973 la resélection expliquée représente
  5,965 M sur 10,886 M unités `air_fleet` moyennes ; les cas où le
  coût attribué excède le coût parent (en 1970 et 1971) sont signalés
  comme **ambiguïtés**, jamais contraints silencieusement à zéro.
- `project_builds_searches.json` : événements `P5_BUILD_LINE` par mode,
  mois, année et graine, et recherches `P5_RAIL_SEARCH` positives ou à
  coût nul, leurs motifs et jours/ticks imputés. **Des événements de
  création ne prouvent ni leur survie ni leur profit final.**
- `project_admission_p2.json` : états `P2_PASS` avant/après dispatch,
  photographie rail `P5_RAIL_PASS` **après dispatch**, attentes et
  résolutions, par graine/année/mois ; notamment les viviers vides
  **concentrés dans une seule graine** en 1972 et 1973. Il ne s'agit
  pas de raisons causales de rejet ni de candidats admissibles à l'entrée.
- `tail_shadow_ab5_5y.json` : cinq paires de duels de **sonde passive**,
  référence OFF/variante ON dans worktree isolé
  `results/p0_opcode_tail_stage_20261012`, 1970–1973 clôturés ;
  distributions de plafond 4k/3k avant/après garde, états UNKNOWN,
  coût total du hook et franchissements de tick. Les plafonds ne sont
  ni CPU récupéré ni admissibilité prouvée ; **0 worker exécuté**.
- `spans_ab2_5y.json` : deux graines opposées 42/999, spans
  `id/par` avec coûts inclusifs et exclusifs, agrégats
  `pub.select.score.insert`, coût de régénération ; signal de mesure
  `negative_exclusive`/`missing_parents` conservé (donc exclusivité
  non certifiée à 100 %). Cette instrumentation **modifie fortement
  l'économie** et reste diagnostique.
- `topk_binary/` : prototype d'accélération de l'insertion stable du
  Top-K, deux B20×10 C66 pass au sens non-érosion économique (avec et
  sans sonde), preuve intrinsèque 57 859 comparaisons/0 mismatch,
  décodage exclusif `LOOP_OPS`, QA physique mensuelle et Save/Load.
  **Gain global d'opcodes et absence stricte de famine de constructions
  AIR/RAIL non démontrés ; défaut OFF, pas d'adoption.**

## Reproduction

Suite de tests :

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_analyse_opcode_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_projects_passes_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_air_fleet_reselect_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_project_output_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_project_admission_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_tail_shadow_early4.py -v
python -X utf8 -m unittest discover -s sweeps -p test_analyse_spans_intrinsic_p0.py -v
```

Recalcul hors Docker depuis les logs extraits :

```powershell
python -X utf8 sweeps/analyse_opcode_early4.py results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine --out results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_breakdown.json --label detail_worker
python -X utf8 sweeps/analyse_projects_passes_early4.py results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine --out evidence/review/opcode_early4_20261012/projects_calls.json
python -X utf8 sweeps/analyse_air_fleet_reselect_early4.py results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine --out evidence/review/opcode_early4_20261012/air_fleet_reselect_calls.json
python -X utf8 sweeps/analyse_project_output_early4.py results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine --out evidence/review/opcode_early4_20261012/project_builds_searches.json
python -X utf8 sweeps/analyse_project_admission_early4.py results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine --out evidence/review/opcode_early4_20261012/project_admission_p2.json
python -X utf8 sweeps/analyse_tail_shadow_early4.py results/p0_opcode_tail_stage_20261012/results/p0_tail_shadow_ab5_5y_20261012_engine --out evidence/review/opcode_early4_20261012/tail_shadow_ab5_5y.json
python -X utf8 sweeps/analyse_spans_intrinsic_p0.py results/p0_opcode_tail_stage_20261012/results/p0_spans_ab2_5y_20261012_engine --prefix p0_spans_intrinsic --seeds 42 999 --out evidence/review/opcode_early4_20261012/spans_ab2_5y.json
```

Les deux campagnes sont gelées via C66.3, mêmes 5 graines, et chacune
a terminé **5/5**. La seconde a été lancée `--years 5` pour mesurer
1970–1973 ; les métriques économiques du rapport viennent de la première
campagne sans sondes `--years 4`. **L'instrumentation perturbe parfois
la trajectoire** : ne pas prétendre que les métriques économiques sont
strictement identiques.

Une analyse exhaustive *du total d'opcodes de AAAHogEx* n'est pas
contenue ici : ses `PerformanceCounter` sont partiels et imbriqués.
La capacité worker mesurée est un **plafond conditionnel avant Sleep**,
et non une économie ou une construction réalisée.
