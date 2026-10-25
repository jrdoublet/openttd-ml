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
