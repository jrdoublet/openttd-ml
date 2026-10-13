# Expérience P0 spans du portefeuille — protocole diagnostic

**12 octobre 2026 — aucun changement de politique ni adoption.**

Après `p0_tail_shadow_ab5_5y_20261012`, le worktree stage
`results/p0_opcode_tail_stage_20261012` reste au même HEAD
`f6139d8` et possède `probe_span_trace`, OFF par défaut ; le nouveau
`probe_tail_shadow` restera OFF dans les deux bras.

Objectif : produire des arbres de spans `select.reselect`, `select.full`,
`projects.post_regen.incremental`, `select.incremental`, `fleet.resize`
jusqu'à la clôture de 1973 afin de **localiser des coûts intrinsèques** :
flatten, merge, filtre, score, comparateurs Top-K, revalidation et
rafraîchissements post-build. Les sous-fenêtres parent/enfant ne sont pas
additionnables ; seule la différence parent moins ses enfants directs
est attribuable aux instructions hors sous-spans, elle-même comprenant
les attentes intercalées.

Première porte de santé : smoke moteur 42 × 1 an, bras
`OpexAI[probe_loop_ops=1,probe_span_trace=1,probe_tail_shadow=0]`.
Deuxième diagnostic si smoke sain : C66.3 `p0_spans_ab2_5y_20261012`,
graines **42 et 999**, `--years 5`, référence
`OpexAI[probe_loop_ops=1,probe_span_trace=0,probe_tail_shadow=0]`,
variante `OpexAI[probe_loop_ops=1,probe_span_trace=1,probe_tail_shadow=0]`,
réglages restants identiques, script-debug, 4 workers et 10 CPU locaux,
8 Go. Ce ne sont que deux graines exploratoires choisies avant l'essai
pour examiner **deux profils opposés** (seed42 portefeuille souvent vide ;
seed999 passes extrêmes). Aucun seuil de gain/adoption n'est applicable :
la règle `gain_short`/4 %/garde5 % avec échantillon insuffisant doit
rester `diagnostic_only`.

La sonde SPAN écrit potentiellement beaucoup de traces et modifie le coût
de l'ordonnanceur. L'analyseur `sweeps/analyse_spans_intrinsic_p0.py`
du worktree principal est à exécuter **sur les logs de la variante** ;
il conserve le coût du hook, les spans orphelins et les traversées de
tick. Aucun coût mesuré par la sonde ne sera extrapolé en économie
possible avant une mesure à entrées identiques et un flag isolé.
