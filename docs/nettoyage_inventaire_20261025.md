# Nettoyage contrôlé du dépôt — 25 octobre 2026

## État et portée

Exécution de la demande de nettoyage des anciens résultats, caches et worktrees, parallèlement aux
bancs V277+V279 et V282. **Aucun changement de défaut, aucun conteneur Docker touché, aucun
switch/checkout/rebase sur le dépôt principal.**

Le dépôt principal est resté sur `master`, commit `4c64ca2a6822889c148991c5dda14e6d2b77f3cd`,
identique à `origin/master` au dernier contrôle. **Deux fichiers suivis étaient déjà modifiés
par le travail du banc** : `docs/taches.md` et `sweeps/run_v277v279_pc.sh`.
Ces modifications ont été préservées. Les bancs présents dans
`.worktrees/v282`, leurs scripts et sorties n'ont pas été touchés.

### Règles appliquées

- **Conserver toutes les campagnes du 20/10/2026 et après**, même volumineuses, ainsi que les
  fichiers sans datation sûre.
- Conserver toute baseline, tout élément cité dans `docs/taches.md`, `AGENTS.md`,
  les autres docs, `sweeps/`, `ai/`, `src/`, `tests/`,
  `evidence/`, `qualifications/`, et toute preuve nécessaire aux défauts courants.
- Vérifier les noms précis des campagnes dans ces sources, les références indirectes,
  les manifestes et bundles, l'état Git, les dates, les liens symboliques et les chemins
  réels avant suppression.
- Une campagne et ses `.json`/`.jsonl` sont une unité ; les résultats liés à un manifeste
  ou à des fichiers de preuve restent conservés. Les données ignorées d'un worktree
  ne sont **pas** couvertes par une branche Git ordinaire.
- Ne pas toucher aux campagnes et chemins actifs
  `v277v279_porteB_20x10_multicargo_20261025*`,
  `v282_v206m1_v280n3_40x10_pc_20261020*`,
  `sweeps/run_v277v279_pc.sh`, `sweeps/run_v282_40x10_pc.sh` ou
  `.worktrees/v282`.

## 1. Fichiers ignorés locaux supprimés

**31 campagnes du 05/10/2026, 62 fichiers au total, 15 245 805 088 octets
(14,1988 Gio).** Chacune était une paire de fichiers
`results/<campagne>.json` et `results/<campagne>.jsonl`. Pour chaque
paire : date dans le nom et modification locale antérieure au 20/10,
fichiers ignorés et non suivis Git, absence de manifeste associé,
aucune citation exacte du nom complet de campagne dans les documents,
scripts, code, tests, qualifications ou corpus de preuve analysés,
chemins canoniques situés dans `results/` hors worktree, puis
revalidation des deux fichiers juste avant retrait.

Campagnes supprimées (toutes préfixées par `results/`, extensions `.json`
et `.jsonl`) :

```text
rail_origin_reuse_compact_smoke_1x1_20261005
rail_origin_reuse_compat_20x5_20261005
rail_origin_reuse_compat_diag_20x5_20261005
rail_origin_reuse_compat_smoke_4x5_20261005
rail_origin_reuse_context_smoke_seed999_5y_20261005
rail_origin_reuse_costcal_20x5_20261005
rail_origin_reuse_costcal_4x5_20261005
rail_origin_reuse_diag_20x5_20261005
rail_origin_reuse_evaldefer_smoke_1x1_20261005
rail_origin_reuse_evaldefer_smoke_seed999_5y_20261005
rail_origin_reuse_fallback2_20x5_20261005
rail_origin_reuse_fallback2_smoke_4x5_20261005
rail_origin_reuse_fallback_20x5_20261005
rail_origin_reuse_fallback_smoke_4x5_20261005
rail_origin_reuse_freight_air_priority_smoke_4x5_20261005
rail_origin_reuse_freight_air_priority_smoke_4x5_20261005_r2
rail_origin_reuse_freight_only_20x5_20261005
rail_origin_reuse_freight_only_smoke_4x5_20261005
rail_origin_reuse_join_smoke_4x5_20261005
rail_origin_reuse_lazy_fallback_attrib_4x5_20261005
rail_origin_reuse_lazy_fallback_smoke_4x5_20261005_r2
rail_origin_reuse_multiline_smoke_4x5_20261005
rail_origin_reuse_onepass_smoke_1x1_20261005
rail_origin_reuse_onepass_smoke_1x1_20261005_r2
rail_origin_reuse_onepass_smoke_1x1_20261005_r3
rail_origin_reuse_onepass_smoke_1x2_20261005_r4
rail_origin_reuse_onepass_smoke_1x2_20261005_r5
rail_origin_reuse_pax_only_smoke_4x5_20261005
rail_origin_reuse_smoke_4x5_20261005
rail_origin_reuse_strictpass_smoke_seed999_5y_20261005
rail_origin_reuse_strict_join_smoke_4x5_20261005
```

Les autres campagnes `rail_origin_reuse_*` et tout autre résultat ne
réunissant pas ces garanties ont été **conservés** ; ne pas conclure
que tous les résultats anciens sont inutiles à partir de cette liste.

## 2. Caches régénérables supprimés

| Chemin | Fichiers | Octets supprimés | Motif |
|---|---:|---:|---|
| `.scratch_saveload/` | 1 048 | 52 238 694 | Caches et sauvegardes temporaires de tests, sans référence dans les lanceurs actifs |
| `.pytest_cache/` | 5 | 272 149 | Cache local de tests |
| `__pycache__/` à la racine | 5 | 35 066 | Bytecode Python régénérable |
| **Total** | **1 058** | **52 545 909** (**50,112 Mio**) | Aucun fichier suivi Git |

Chaque répertoire a été vérifié comme local au dépôt, ignoré par Git,
sans contenu suivi et sans lien symbolique avant sa suppression.
Les caches peuvent naturellement être recréés lors des tests suivants.

## 3. Worktrees anciens : deux suppressions avec sauvegarde distante

Pour les **neuf worktrees Git** identifiés sous `results/` avec une date du
18 ou 19 octobre, inspection de la branche/du SHA, de
`git status --porcelain --ignored`, des données ignorées et des
références ; comparaison avec les branches `backup/20261025-*`.
**Deux worktrees seulement** ont été jugés sûrs pour retrait.

| Worktree supprimé | HEAD sauvegardé sur `origin` | Fichiers locaux effacés | Octets locaux |
|---|---|---:|---:|
| `results/v229_v264_v265_evidence_stage_20261019/` | `backup/20261025-v229-v264-v265-evidence-stage-20261019` → `e50a46e92328d3fec03ee860bfe8429b76049f69` | 2 137 | 342 936 167 |
| `results/archive_p0_p2_p4_stage_20261018/` | `backup/20261025-archive-p0-p2-p4-stage-20261018` → `626238b903f863e888aaefb49e740726ecf74e43` | 2 118 | 408 005 687 |
| **Total** | Deux branches **poussées avec succès** | **4 255** | **750 941 854 octets** (**0,699 Gio**) |

Le premier était propre, sans fichier ignoré/non suivi ; le second était
propre, avec uniquement `sweeps/__pycache__/` comme contenu ignoré
(récréable). Avant chaque `git worktree remove` **sans `--force`** :
la branche backup a été créée **sans checkout**, poussée sur origin,
et les trois SHA (worktree, branche locale, suivi distant) ont été comparés.
Les deux suppressions ont renvoyé **code 0** et les répertoires
ont été vérifiés absents ensuite.

### Sept worktrees anciens conservés

| Worktree `results/<nom>/` | Motif de conservation |
|---|---|
| `v228_pc_stage_20261019/` | Journaux `map1024`, PID, résultats ignorés, copie AAAHogEx |
| `v229_40x10_pc_stage_20261019/` | Résultats JSON/JSONL, manifeste, bundle, engine |
| `v257rev_run_stage_20261019/` | Bundle historique et cache |
| `v264_40x10_pc_stage_20261019/` | Résultats complets, manifestes, logs, bundle |
| `v265_40x10_pc_stage_20261019/` | Résultats complets, scripts de smoke, manifestes |
| `v268_porteB_stage_20261019/` | Résultats et moteur ignorés, copie AAAHogEx |
| `volume_rva_audit_stage_20261019/` | `results/r1_r3_mechanisms/` et cache |

Une branche Git sauvegarde les **objets suivis** mais **pas ces fichiers
ignorés**. Aucun retrait de ces sept worktrees sans sauvegarde
adaptée et vérification supplémentaire. Les worktrees sans date sûre,
les worktrees du 20 octobre et après, tous ceux de `.worktrees/`
(en particulier `.worktrees/v282`) et les autres emplacements restent intacts.

## 4. Résultats suivis par Git et anciens scripts : conservés

- Les **395 fichiers** initialement suivis dans `results/` représentaient
  environ **240,15 Mio** non comprimés ; les anciens lots des 18–19/10,
  ainsi que les références datées ou sans date dans le nom, n'ont pas été
  modifiés. En particulier, les baselines
  `results/nuit75_master83e_baseline20x10_20261024*`,
  `results/nuit75_multicargo_default_20x10_seedsfix_20261025*`
  et `results/bench_1v1_5y_20seeds_reference.json` sont préservées.
- Les **23 scripts suivis `sweeps/_tmp_*.py`** (60 490 octets)
  et les autres anciens scripts ne sont pas retirés : leurs imports,
  leurs contrats historiques et leurs usages indirects méritent une
  revue isolée. Les tests `test_*.py`, les outils de banc, tous les
  briefs récents et le corpus `evidence/review/` sont préservés.
- Plusieurs anciens fichiers sont cités indirectement via
  `evidence/review/index.json`, des manifestes ou des noms de
  campagne construits dynamiquement. C'est une raison explicite de
  conservation, même en absence de citation littérale par nom de fichier.
- `.venv/` et toute dépendance installée ont été conservées.

**Aucun `git rm` n'a été exécuté.** L'utilisateur exigeait un
`git pull --rebase` avant commit **uniquement si le dépôt principal
ne porte aucune modification d'un banc**. Or `docs/taches.md`
et `sweeps/run_v277v279_pc.sh` étaient et restent modifiés.
Par conséquent, par respect de cette condition :
**pas de pull/rebase, pas de commit sur `master`, pas de push `master`.**
Le présent rapport reste **non committé** jusqu'à libération du dépôt.
Il n'y a donc **pas de hash de commit de nettoyage** ni de sortie de
push `master` à fournir.

## 5. Validation des tests

Commande identique, lancée avant puis après le nettoyage :

```powershell
python -X utf8 -m unittest discover -s sweeps -p "test_*.py"
```

| Exécution | Résultat | Détail |
|---|---|---|
| **Avant** | **Exit 0** | **2 476 tests OK**, 5 `skipped`, 2 `expected failures` ; 164,801 s |
| **Après** | **Exit 0** | **2 476 tests OK**, 5 `skipped`, 2 `expected failures` ; 165,947 s |

**Aucun nouvel échec.** Traces temporaires :
`%TEMP%/openttd_cleanup_tests_before_20261025.log` et
`%TEMP%/openttd_cleanup_tests_after_20261025.log`.

## 6. Espace récupéré et dépôt Git

| Type de suppression | Gain estimé par somme des octets physiques |
|---|---:|
| 31 campagnes ignorées anciennes (62 fichiers) | **15 245 805 088 octets** |
| Trois caches locaux | **52 545 909 octets** |
| Deux worktrees sauvegardés et retirés | **750 941 854 octets** |
| **Total** | **16 049 292 851 octets**, soit **14,947 Gio** |

Il s'agit de l'addition des tailles de fichiers effectivement retirés,
pas d'une mesure indépendante d'espace libre du disque NTFS
(allocation, compression, liens physiques éventuels).

**Réduction des fichiers suivis de l'arbre Git courant : 0 octet.**
Les anciennes données effacées étaient ignorées, et les worktrees
partageaient le dépôt d'objets. Les packs Git historiques (environ
**425 Mio** lors de l'inventaire initial) ne sont **pas** réécrits.
Toute réécriture d'historique et tout force-push restent hors périmètre.
Les deux **push** effectués concernaient seulement les nouvelles
branches de sauvegarde listées en section 3.

## 7. Étapes restant conditionnelles

1. Quand le banc aura libéré le dépôt principal, refaire la vérification
   `git status` et décider **séparément** si les anciens fichiers suivis
   et scripts temporaires peuvent être retirés. Ne pas écraser les
   modifications de banc.
2. Pour les sept worktrees conservés, inventorier/archiver les données
   ignorées utiles **avant** de proposer leur retrait et leur backup.
3. Pour davantage de nettoyage local, établir des listes fermées de
   campagnes entières non référencées : pas de suppression globale
   `results/*`, pas de fichier récent, pas de manifeste/bundle isolé.

**Bilan : 14,947 Gio estimés récupérés ; deux sauvegardes distantes ;
2 476 tests verts avant et après ; aucun résultat récent, défaut, Docker,
script actif ni fichier Git suivi touché.**

---

## 8. Deuxième passe du 25 octobre 2026 — bilan complémentaire

Cette section actualise le bilan des sections 1 à 7 qui décrivent la première passe.
Les deux nettoyages cumulent les économies ci-dessous ; les décisions précédentes
ne doivent pas être interprétées comme le statut final de cette seconde passe.

### Résultats anciens ignorés : vérification et suppression par familles

- 490 familles et 20 527 fichiers supprimés : **6 870 426 662 octets (6,399 Gio)**.
- Les noms de campagne (<20/10), dates de modification, fichiers ignorés, absence de
  suivi Git, chemins réels et absence de liens symboliques ont été revalidés.
- Recherche des références dans docs, scripts, code IA, tests, evidence/review,
  qualifications et manifestes/rapports JSON de results. Les ensembles JSON, JSONL,
  manifest, bundle et engine ont été traités ensemble, jamais comme fichiers isolés.
- **Cinq familles préservées** pour références croisées :
  - `air_p0_direct_realization_holdout_40x10_20261010_r1`
  - `first_observation_smoke_20261011_r1`
  - `observation_growth_smoke_20261011_r1`
  - `rail_origin_exposure_shadow_logs_4x4_20261006`
  - `v217_autopsy_841478_5y_saves_20261016`
- Conservés également : tous les résultats du 20/10 ou après, baselines et
  campagnes des bancs V277+V279/V282, les familles sans date vérifiable,
  les snapshots de code et les résultats anciens cités.
- Exemples de données anciennes conservées :
  `results/c121_nuit_20261003_203842/` (1,314 Gio),
  `results/c121_numeric10_20261004_161323/` (0,832 Gio),
  `results/c121_suite5_20261004_112415/` (0,702 Gio),
  toujours liées à des documents ou à de la preuve historique.

### Worktrees : 21 retraits supplémentaires, 15 sauvegardes nouvelles

- 21 worktrees propres retirés avec git worktree remove **sans --force**.
  Tous les éléments ignorés des worktrees retenus étaient absents ou seulement
  des caches Python/pytest recréables. Les états Git et SHAs ont été revalidés.
- 15 branches de sauvegarde nouvellement poussées sur origin, puis contrôlées
  au même SHA que le worktree avant retrait ; 6 worktrees disposaient
  déjà de la branche exacte sur origin. Aucune branche distante supprimée.
- `git worktree prune` exécuté avec code 0.

| Worktree retiré | Branche poussée vérifiée | Gain (Gio) |
|---|---|---:|
| `C:/Users/jr/.codex/worktrees/github-v102/openttd-ml` | `codex/github-v102` | 0.228 |
| `.worktrees/ailist-push` | `backup/20261025-ailist-push` | 0.318 |
| `.worktrees/nuit75-good-origin-spread-v1` | `backup/20261025-nuit75-good-origin-spread-v1` | 0.319 |
| `results/air_flotte1_publish_20261022` | `backup/20261025-air_flotte1_publish_20261022` | 0.317 |
| `results/air_roi_sondes_docs_stage_20261023` | `backup/20261025-air_roi_sondes_docs_stage_20261023` | 0.318 |
| `results/airr1_offline_postprocess_20261023` | `backup/20261025-airr1_offline_postprocess_20261023` | 0.318 |
| `results/docs_wip_historical_batch_20261023` | `backup/20261025-docs_wip_historical_batch_20261023` | 0.318 |
| `results/master_safe_dirty_replay_20261023` | `backup/20261025-master-safe-dirty-replay-20261023` | 0.318 |
| `results/origin_master_air_roi_audit_stage_20261023` | `backup/20261025-origin_master_air_roi_audit_stage_20261023` | 0.318 |
| `results/origin_master_docs_archive_20261023` | `backup/20261025-origin_master_docs_archive_20261023` | 0.318 |
| `results/origin_master_offline_rail_20261023` | `backup/20261025-origin_master_offline_rail_20261023` | 0.319 |
| `results/param_core_declarations_20261023` | `backup/20261025-param_core_declarations_20261023` | 0.318 |
| `results/param_tests_stage_20261023` | `backup/20261025-param_tests_stage_20261023` | 0.318 |
| `results/params_runtime_removal_w4_20261023` | `backup/20261025-params_runtime_removal_w4_20261023` | 0.319 |
| `results/porteB_publish_20261021` | `publish/porteB-results-20261021` | 0.371 |
| `results/precalc_workers_tasks_stage_20261020` | `backup/20261025-precalc_workers_tasks_stage_20261020` | 0.314 |
| `results/rail_long_windows_publish_20261022` | `backup/20261025-rail_long_windows_publish_20261022` | 0.317 |
| `results/v267_publish_stage_20261020` | `v267` | 0.313 |
| `results/v271_publish_stage_20261020` | `backup/20261025-v271_publish_stage_20261020` | 0.315 |
| `C:/Users/jr/vscode/openttd-ml/wt_portesb_publish` | `publish/portesB-20261024` | 0.320 |
| `C:/Users/jr/vscode/openttd-ml/wt_v294g_base` | `backup/20261025-wt_v294g_base` | 0.324 |

**15 nouvelles branches de sauvegarde créées et poussées :**

- `backup/20261025-ailist-push` → `c03fce93afc1`
- `backup/20261025-air_flotte1_publish_20261022` → `a4bb2e84569c`
- `backup/20261025-air_roi_sondes_docs_stage_20261023` → `cf80b970e029`
- `backup/20261025-airr1_offline_postprocess_20261023` → `59c48065ac5c`
- `backup/20261025-docs_wip_historical_batch_20261023` → `1774b64a9c0f`
- `backup/20261025-origin_master_air_roi_audit_stage_20261023` → `f69427e8b89f`
- `backup/20261025-origin_master_docs_archive_20261023` → `73da3e29638a`
- `backup/20261025-origin_master_offline_rail_20261023` → `08318060b008`
- `backup/20261025-param_core_declarations_20261023` → `b47de67024ac`
- `backup/20261025-param_tests_stage_20261023` → `f576570756a5`
- `backup/20261025-params_runtime_removal_w4_20261023` → `8af1845137ee`
- `backup/20261025-precalc_workers_tasks_stage_20261020` → `27c7ba14de7f`
- `backup/20261025-rail_long_windows_publish_20261022` → `f8212754f0a7`
- `backup/20261025-v271_publish_stage_20261020` → `8a29674c634e`
- `backup/20261025-wt_v294g_base` → `eec5db814734`

**73 worktrees conservés, avec leur raison :**

| Worktree conservé | Motif |
|---|---|
| `C:/Users/jr/vscode/openttd-ml/openttd-ml` | Dépôt principal : banc V277+V279 actif |
| `C:/Users/jr/.codex/worktrees/est-v216-final/openttd-ml` | Dépendance ignorée à vérifier : `ai/AAAHogEx-115/` |
| `C:/Users/jr/.codex/worktrees/v263-results/openttd-ml` | Résultats/code ignorés non archivés : `results/package_v263_evidence.py` |
| `.worktrees/backup-inventory-update` | Worktree potentiellement utilisé par un autre chat |
| `.worktrees/carto1` | Résultats/code ignorés non archivés : `results/carto1_analysis_3x3_20261024.json` |
| `.worktrees/carto1_reference` | Résultats/code ignorés non archivés : `results/carto1_reference_off1024_1x1_20261024.json` |
| `.worktrees/nuit75-air-full-load` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `.worktrees/nuit75-air-grow-corrected` | Résultats/code ignorés non archivés : `results/nuit75_airgrowfix_exposure_5x3_20261025.json` |
| `.worktrees/nuit75-early-c75-refund` | Résultats/code ignorés non archivés : `results/nuit75_c75refund_expo_5x3_20261025.json` |
| `.worktrees/nuit75-early-c75-second` | Résultats/code ignorés non archivés : `results/nuit75_early_c75_expo_2x3_20261025.json` |
| `.worktrees/nuit75-early-multicargo-v1` | Résultats/code ignorés non archivés : `results/nuit75_mc_expo_5x3_20261025.json` |
| `.worktrees/nuit75-early-value-v1` | Résultats/code ignorés non archivés : `results/nuit75_truequote_expo_10x3_20261025_rollup.json` |
| `.worktrees/nuit75-freight-attrition` | Résultats/code ignorés non archivés : `results/nuit75_freight_attr_diag_5x10_20261025.json` |
| `.worktrees/nuit75-freight-capacity-variant` | Résultats/code ignorés non archivés : `results/nuit75_freightcap_exposure_seed100_1x10_20261025.jso` |
| `.worktrees/nuit75-front-pax1` | Résultats/code ignorés non archivés : `results/nuit75_frontpax1_diag_5x5_20261025.json` |
| `.worktrees/nuit75-front-pax2` | Résultats/code ignorés non archivés : `results/nuit75_frontpax2_diag_5x10_20261025.json` |
| `.worktrees/nuit75-good-source-variant` | Résultats/code ignorés non archivés : `results/nuit75_goodsource_exposure_seed100_1x10_20261025.jso` |
| `.worktrees/nuit75-idle1` | Résultats/code ignorés non archivés : `results/nuit75_idle1_reserve_smoke_1x1_20261025.json` |
| `.worktrees/rlw04` | Résultats/code ignorés non archivés : `results/rlw04_cadence2_on1024_20261022.json` |
| `.worktrees/rlw04b` | Résultats/code ignorés non archivés : `results/rlw04b_off1024_smoke_20261024.json` |
| `.worktrees/rlw04b_reference` | Résultats/code ignorés non archivés : `results/rlw04b_reference1024_20261024.json` |
| `.worktrees/rlw06` | Résultats/code ignorés non archivés : `results/rlw06_off1024_20261024.json` |
| `.worktrees/rlw06_reference` | Résultats/code ignorés non archivés : `results/rlw06_reference1024_20261024.json` |
| `.worktrees/v282` | Interdit explicite V282 ; banc actif ou à venir |
| `results/c77_po01c_stale_guard_stage_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/c77_po01c_tests_alignment_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/calibration_pc_20261021` | Résultats/code ignorés non archivés : `results/bandes_distance_roi_20261021.json` |
| `results/master_safe_bridge_sim_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/master_safe_integration_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/origin_master_next_20261023` | Résultats/code ignorés non archivés : `results/merge_po03_guard_smoke_20261023.json` |
| `results/origin_master_offline_tools_stage_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/origin_master_reviewed_safe_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/origin_master_safe_only_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/origin_master_staging_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/param_retirement_baseline_08318060_20261023` | Résultats/code ignorés non archivés : `results/param_baseline_smoke_20261023.json` |
| `results/param_retirement_candidate_20261023` | Résultats/code ignorés non archivés : `results/param_retirement_contracts_postruntime_20261023.log` |
| `results/param_retirement_tests_alignment_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/params_tests_w4_20261023` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/porteB-adapt400` | Résultats/code ignorés non archivés : `results/adapt400_porteB_20x10_pc_20261021.json` |
| `results/porteB-finpartie` | Résultats/code ignorés non archivés : `results/finpartie_porteB_20x10_pc_20261021.json` |
| `results/porteB-v296a` | Résultats/code ignorés non archivés : `results/v296a_porteB_20x10_pc_20261021.manifest.json` |
| `results/porteB-v296clean` | Résultats/code ignorés non archivés : `results/_bananas_offline_cache/` |
| `results/porteB-v297` | Résultats/code ignorés non archivés : `results/v297_porteB_20x10_pc_20261021.json` |
| `results/porteB-v301` | Résultats/code ignorés non archivés : `results/_bananas_offline_cache/` |
| `results/porteB_nuit_runner_master_20261021` | Dépendance ignorée à vérifier : `ai/AAAHogEx-115/` |
| `results/porteB_nuit_runner_stage_20261021` | Résultats/code ignorés non archivés : `results/adapt400.attempt1.stderr.log` |
| `results/revue_code_baseline_20261024` | Résultats/code ignorés non archivés : `results/revue_code_R02R03_base_20x10_20261024.json` |
| `results/revue_code_cleanup_only_20261024` | Résultats/code ignorés non archivés : `results/revue_code_cleanup_only_smoke_1x1_1024_20261024.json` |
| `results/revue_code_R02R03_candidate_20261024` | Résultats/code ignorés non archivés : `results/revue_code_R02R03_candidate_20x10_20261024.json` |
| `results/revue_code_R05_full_candidate_20261024` | Dépendance ignorée à vérifier : `ai/AAAHogEx-115/` |
| `results/rlw03_runtime_stage_20261022` | Résultats/code ignorés non archivés : `results/rlw03_probe_multi_42_3y_20261022_bundle/` |
| `results/v131c_diag_stage_20261020` | Résultats/code ignorés non archivés : `results/inspect_v131c_gate_b.py` |
| `results/v228_pc_stage_20261019` | Résultats/code ignorés non archivés : `results/map1024_manual_20261019.pid` |
| `results/v229_40x10_pc_stage_20261019` | Résultats/code ignorés non archivés : `results/v229_40x10_pc_20261019.json` |
| `results/v257rev_run_stage_20261019` | Résultats/code ignorés non archivés : `results/v257rev_20x10_pc_20261019_bundle/` |
| `results/v264_40x10_pc_stage_20261019` | Résultats/code ignorés non archivés : `results/v264_40x10_pc_20261019.fixed_smoke.sh` |
| `results/v265_40x10_pc_stage_20261019` | Résultats/code ignorés non archivés : `results/v265_40x10_pc_20261019.fixed_smoke.sh` |
| `results/v268_porteB_stage_20261019` | Résultats/code ignorés non archivés : `results/v268_porteB_stage_20261019/` |
| `results/v275_sober_diag_stage_20261020` | Résultats/code ignorés non archivés : `results/v275_sobre_diag_4x3_log_20261020_b.json` |
| `results/v275_sobre_exact_stage_20261020` | Résultats/code ignorés non archivés : `results/v275_sobre_exact_3x3_log_20261020.json` |
| `results/v280b_40x10_stage_20261020` | Résultats/code ignorés non archivés : `results/v280b_n1_v284_40x10_pc_20261020.jsonl` |
| `results/v294all_pc_stage_20261020` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/v294c_adapt_stage_20261020` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/v294g_stage_20261020` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `results/v307r_bench_clean_20261021` | Résultats/code ignorés non archivés : `results/v307r_bit1_expo_3x10_20261021.json` |
| `results/v308_bench_clean_20261021` | Résultats/code ignorés non archivés : `results/v308_3x7_reference_worker_diag.json` |
| `results/v309_bench_clean_20261021` | Résultats/code ignorés non archivés : `results/v309_idle_expo_3x10_20261021.json` |
| `results/volume_rva_audit_stage_20261019` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `C:/Users/jr/vscode/openttd-ml/v263-master-tree` | Résultats/code ignorés non archivés : `results/v263_master_n2_20x10_pc_20261019.json` |
| `C:/Users/jr/vscode/openttd-ml/wt_airload30` | Résultats/code ignorés non archivés : `results/airload30_porteB_20x10_20261024.jsonl` |
| `C:/Users/jr/vscode/openttd-ml/wt_peloton` | Résultats/code ignorés non archivés : `results/peloton_diag_5x5_20261024.json` |
| `C:/Users/jr/vscode/openttd-ml/wt_v294g` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |
| `C:/Users/jr/vscode/openttd-ml/wt_v294g_baseline` | Résultats/code ignorés non archivés : `results/r1_r3_mechanisms/` |

### Fichiers suivis : suppression ciblée et protections

- 21 scripts anciens `sweeps/_tmp_*.py` retirés avec `git rm` :
  **54 144 octets** de fichiers suivis en moins dans le snapshot courant.
  Aucun script, test ou document courant ne les importe ni ne les cite.
  Les noms existent uniquement dans les inventaires historiques de SHA
  `evidence/review/ac04_hubsite_20261011/{plan,report}.json` ;
  les sources restent retrouvables via Git historique.
- 2 scripts temporaires conservés en raison de citations dans des docs :
  `sweeps/_tmp_analyse_railgeom_critical_date.py` et
  `sweeps/_tmp_host_c121_autopsy_frozen_trace.py`.
- 17 fichiers résultats Git anciens conservés : les six familles de campagnes
  datées des 18–19/10 sont citées dans les rapports V250/niveaux, V256, V257rev, V261
  ou `docs/taches.md`. Aucun résultat Git ancien n’a été désindexé.

### Tests et espace : cumul des deux passes

| Test | Résultat |
|---|---|
| Avant la deuxième passe | 2 476 tests OK, 5 ignorés, 2 échecs attendus |
| Après suppressions suivies | 2 476 tests OK, 5 ignorés, 2 échecs attendus ; **aucun nouveau échec** |

Commande : `python -X utf8 -m unittest discover -s sweeps -p test_*.py`.
Traces : `%TEMP%/openttd_cleanup2_before_20261025.log` et
`%TEMP%/openttd_cleanup2_after_20261025.log`.

| Suppressions | Octets | Gio |
|---|---:|---:|
| Première passe | 16,049,292,851 | 14.947 |
| Deuxième passe : anciennes familles locales | 6,870,426,662 | 6.399 |
| Deuxième passe : 21 worktrees | 7,128,927,371 | 6.639 |
| Deuxième passe : 21 scripts suivis | 54,144 | 0.000050 |
| **Total cumulé** | **30,048,701,028** | **27.985** |

Somme des tailles de fichiers retirés, **pas** mesure des octets libres NTFS.
Le pack Git historique (environ 425 Mio) est inchangé par la disparition
des fichiers de HEAD : aucune réécriture de l’historique ni force-push.

### Sécurité de publication

Le commit de nettoyage doit inclure uniquement les 21 retraits et ce rapport.
**Ne pas indexer** `docs/taches.md` ni `sweeps/run_v277v279_pc.sh`,
modifiés par le banc en cours. Aucun switch/checkout/rebase, aucune modification
de défaut, Docker ou contenu de `.worktrees/v282`.
