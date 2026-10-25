# Inventaire de nettoyage — 25 octobre 2026

> **Proposition en lecture seule.** Aucun fichier, résultat, worktree ou branche n'a été supprimé,
> déplacé, désindexé, modifié ou committé pendant cet audit. Ce document est le seul livrable écrit.
> **Ne rien supprimer avant validation explicite de l'utilisateur.**

## 1. Périmètre, méthode et règle de conservation

- Dépôt local Windows `/openttd-ml`, branche `master`, HEAD `a0bf7fc6`.
  `origin/master` était identique au début, puis a avancé à `f09baa90`
  pendant l'audit : **aucun pull/rebase n'a été effectué**.
- Inventaire physique des fichiers (tailles en octets, MiB/Gio binaires), comparaison à
  `git ls-files` et `git worktree list --porcelain`. Les dates de campagnes proviennent
  **des noms** (`YYYYMMDD`), ou à défaut le fichier est classé *sans date certaine*.
  Les dates de modification locales ne prouvent ni la date du banc ni son obsolescence.
- Recherche de références explicites par chemins, noms et noms de campagnes dans
  `docs/taches.md`, `AGENTS.md`, le journal nocturne du 24–25/10 et les deux rapports
  N75 du 25/10. Ce **filtre lexical** n'est pas une preuve d'absence de dépendance :
  d'autres docs, tests, scripts, manifests ou variantes de nom peuvent citer un résultat.
- **« Récent » = campagne datée du 20/10/2026 inclus au 25/10/2026 : conserver
  intégralement pour l'instant**, y compris les traces brutes et les campagnes négatives.
- **Conserver indépendamment de l'âge** tout résultat directement ou indirectement
  nécessaire à `docs/taches.md`, `AGENTS.md`, une baseline de référence ou un
  **réglage actuellement actif par défaut** ; garder aussi les manifests/bundles nécessaires
  à l'audit de ces résultats. En cas de doute ou d'absence de date, **conserver**.
- Préserver les fichiers possédant des changements locaux, ainsi que les `worktrees`
  et leurs données ignorées ; leur date ou l'absence de modifications Git ne suffit pas
  à autoriser un retrait.

## 2. Occupation mesurée

| Emplacement / nature | Fichiers | Occupation locale | État |
|---|---:|---:|---|
| `results/` **total**, worktrees compris | 279 878 | **77,657 Gio** | Mélange de résultats et de vrais dépôts de travail |
| `results/` ignorés/non suivis, hors worktrees | 119 858 | **51,576 Gio** | Données potentiellement nettoyables sous conditions |
| `results/` suivis par Git | **395** | **240,15 MiB** | Nécessite une modification de l'arbre Git pour être retiré du dépôt |
| `results/` — **62 worktrees Git imbriqués** | 159 625 | **25,847 Gio** | Ne pas traiter comme des répertoires de résultats ordinaires |
| `.worktrees/` — **21 worktrees Git** | 69 738 | **8,837 Gio** | Expériences récentes et états locaux, actuellement protégés |
| `sweeps/` total (dont 809 fichiers suivis) | 2 975 | 35,98 MiB | Scripts et caches ; seuls certains scripts sont candidats |
| `docs/` | 503 | 30,25 MiB | Documentation et historique, à garder sauf arbitrage ciblé |
| `evidence/` | 527 | 62,84 MiB | Corpus d'évidence, à garder |
| `.venv/` | 40 790 | 506,76 MiB | Environnement régénérable, **à garder pour ne pas gêner le travail** |
| `.scratch_saveload/` | 1 048 | **49,82 MiB** | Cache local récréable (13–21/10) |
| `.pytest_cache/` | 5 | **0,260 MiB** | Cache local récréable (21/10) |
| `__pycache__/` à la racine | 5 | **0,033 MiB** | Cache Python local (09–10/10) |

Le nombre de worktrees enregistrés par Git est **94** au total : 62 dans `results/`,
21 dans `.worktrees/`, et 11 autres (dont le dépôt principal et des worktrees situés
hors de cette arborescence). **Les tailles ci-dessus ne doivent pas être sommées deux
fois : les worktrees sous `results/` sont déjà compris dans ses 77,657 Gio.**

### Détail des seuls résultats hors worktrees

| Catégorie / campagne | Fichiers | Taille | Décision proposée |
|---|---:|---:|---|
| Ignorés, datés **avant 20/10**, sans mention textuelle trouvée dans les cinq sources prioritaires | **42 696** | **32,746 Gio** | **Pré-candidats** au nettoyage local, après deuxième contrôle des dépendances et fichiers associés |
| Ignorés, datés **avant 20/10**, avec mention du fichier/de la campagne | 49 116 | **4,634 Gio** | **Conserver** ; preuve ou campagne citée |
| Ignorés, datés **20–25/10** | 12 415 | **13,077 Gio** | **Conserver** en entier selon la règle de récence |
| Ignorés, **sans date identifiable** | 15 631 | **1,117 Gio** | **Conserver**, provenance à clarifier |
| Suivis Git, datés avant 20/10 | 17 | **32,71 MiB** | **Examiner**, ne pas désindexer automatiquement |
| Suivis Git, datés 20–25/10 | 93 | **19,00 MiB** | **Conserver** |
| Suivis Git, sans date dans le nom | 285 | **188,44 MiB** | **Conserver** en l'absence de preuve d'obsolescence |

L'absence de référence signifie uniquement « pas de référence littérale détectée par
le filtre de cet audit ». Elle **ne signifie pas** que le fichier est inutile ou
qu'il est sûr de le supprimer.

## 3. Fichiers ignorés locaux : propositions et exceptions

### Groupe A — anciennes traces volumineuses, à soumettre au nettoyage après contre-vérification

Échantillon des principaux **pré-candidats** (dates de campagne, tailles physiques
arrondies ; hors tout worktree) :

| Chemin ou motif | Date | Taille | Pourquoi le proposer ? |
|---|---|---:|---|
| `results/rail_origin_reuse_costcal_20x5_20261005.jsonl` | 05/10 | **3,586 Gio** | JSONL brut volumineux, aucune citation littérale détectée dans les sources prioritaires |
| `results/rail_origin_reuse_*_4x5_20261005*.jsonl` | 05/10 | Environ **10 Gio cumulés**, ordre de grandeur | Multiples smokes / traces d'une campagne ancienne ; garder les synthèses utiles |
| `results/c121_nuit_20261003_203842/` | 03–04/10 | **1,411 Go** au total (dont 1,099 Gio non cités) | Anciens diagnostics détaillés ; contrôler les rapports dérivés |
| `results/c121_numeric10_20261004_161323/` | 04–12/10 | **894 Mo** au total (dont 0,725 Gio non cités) | Données détaillées anciennes, pas de suppression sans preuve |
| `results/c121_station_supply_20261008/` | 08/10 | **0,600 Gio** non cités | Diagnostic C121 ancien |
| `results/c121_town_flux_20261008/` | 08/10 | **0,548 Gio** non cités | Diagnostic C121 ancien |
| `results/v267_main_x10_pc_20261019.jsonl` | 19/10 | **0,558 Gio** | Trace brute avant le seuil, à comparer à l'artefact résumé |

**Protection explicite :** ne pas effacer par motif `results/c121_*` :
`results/c121_suite5_20261004_112415/` représente **0,702 Gio** et
est reconnu comme cité par le corpus prioritaire. De même, les JSONL cités des
campagnes `v273_40x10_pc_20261019`, `upgmem_40x10_20261010_r1`, etc.,
restent du côté « conserver ». Les suppressions éventuelles doivent se faire
par **liste fermée vérifiée**, jamais par `Remove-Item results/*` ou glob large.

### Groupe B — données locales de référence ou récentes : à garder

- `results/nuit75_master83e_baseline20x10_20261024*` : baseline 1970–1979
  **56,5519 % / 58,9112 %** ; référence historique explicite de `docs/taches.md`.
- `results/nuit75_multicargo_default_20x10_seedsfix_20261025*`, les six
  `nuit75_*_porteA_40x5_20261025*`, leurs analyses, manifestes et bundles :
  campagne récente, références du nouveau défaut `n75_multi_cargo=2`.
- `results/bench_1v1_5y_20seeds_reference.json` : ancienne baseline
  autorisée explicitement dans `.gitignore` ; garder sans condition de date.
- Toutes les données datées **20/10 ou après**, y compris par exemple
  `results/opcode_ailist_L6_v284_wagon_3x6_20261023.jsonl`
  (**2,685 Go**) et `results/opcode_ailist_L4_v257_filter_3x5_20261023.jsonl`
  (**2,078 Go**) : elles sont volumineuses **mais récentes**.
- Les fichiers sans date fiable, les sources de décisions courantes et les
  sources d'une baseline : maintien jusqu'à identification positive.

## 4. Résultats suivis par Git : 395 fichiers, 240,15 MiB

Seulement **17** fichiers ont une date de campagne antérieure au 20/10 :

| Famille de chemins suivis | Date | Taille approx. | Qualification |
|---|---|---:|---|
| `results/diff_n0_vs_n2_20x10_pc_20261018.*` (JSON, `.jsonl.gz`, manifest) | 18/10 | 6,88 MiB | Revue des comparatifs de difficulté avant retrait |
| `results/diff_n1_vs_n2_10x10_pc_20261018.*` (3 fichiers) | 18/10 | 6,89 MiB | Idem |
| `results/v250_mode4_vs_master_n2_20x10_pc_20261018.*` (3 fichiers) | 18/10 | 7,14 MiB | Vérifier les décisions / défauts V250 |
| `results/v256_v252opt_20x10_pc_20261018.*` (3 fichiers) | 18/10 | 6,96 MiB | **Conserver au moins le JSON explicitement cité**, préserver sa provenance |
| `results/v257rev_20x10_pc_20261019.*` (JSON, manifest) | 19/10 | 1,46 MiB | **JSON cité**, préserver sa provenance |
| `results/v261_n2_20x10_pc_20261018.*` (3 fichiers) | 18/10 | 3,39 MiB | **JSON cité**, préserver sa provenance |

Le filtre textuel marque **3 JSON** (environ **3,19 MiB**) directement
référencés et **14 autres fichiers** (environ **29,52 MiB**) non
directement référencés. **Les 14 ne sont pas déclarés supprimables** :
certains sont le manifest ou le brut associé aux trois JSON cités ;
les autres ont une valeur potentielle de comparaison historique ou de
qualification des défauts. Proposition : **revue manuelle par famille,
sans suppression Git dans la première passe**.

Les **285 fichiers suivis sans date dans le nom**, soit **188,44 MiB**
(`results/phase2_*.json`, `results/bench_*.json`,
`results/p1_*.jsonl`, `results/opex_*.json`, etc.), sont historiques,
mais leur ancienneté ne peut pas être déduite sûrement du nom.
Ils sont **conservés** dans cette proposition, même s'ils représentent
la majorité du poids suivi.

## 5. Worktrees Git : ne pas confondre avec les traces

### Sous `results/`

Les **62 worktrees sous `results/` occupent 25,847 Gio**.
Ne jamais retirer un de ces répertoires au moyen d'une suppression
directe ou d'un nettoyage de résultats. Parmi eux, **9 worktrees
datés du 18–19/10**, totalisant environ **4,815 Gio**, méritent
une revue spécifique :

| Worktree `results/<nom>/` | Date du nom | Occupation | Modifications Git suivies |
|---|---|---:|---|
| `v265_40x10_pc_stage_20261019/` | 19/10 | 0,760 Gio | 0 |
| `v264_40x10_pc_stage_20261019/` | 19/10 | 0,757 Gio | 0 |
| `v229_40x10_pc_stage_20261019/` | 19/10 | 0,750 Gio | 0 |
| `v268_porteB_stage_20261019/` | 19/10 | 0,692 Gio | 0 |
| `v228_pc_stage_20261019/` | 19/10 | 0,525 Gio | 0 |
| `archive_p0_p2_p4_stage_20261018/` | 18/10 | 0,380 Gio | 0 |
| `volume_rva_audit_stage_20261019/` | 19/10 | 0,320 Gio | 0 |
| `v229_v264_v265_evidence_stage_20261019/` | 19/10 | 0,319 Gio | 0 |
| `v257rev_run_stage_20261019/` | 19/10 | 0,312 Gio | 0 |

**« 0 modification Git suivie » ne signifie pas « vide » :** les
`results/` ignorés internes, les branches et les HEAD détachés doivent
être inspectés individuellement avant tout `git worktree remove`.
Leur retrait éventuel constitue une **étape séparée à valider** et les
**4,815 Gio ne figurent pas** dans le gain de la première passe.

Les six worktrees sans date dans le nom
`results/porteB-{adapt400,finpartie,v296a,v296clean,v297,v301}/`
restent conservés. `porteB-v296clean` et `porteB-v301` ont chacun
**une modification suivie** observée. Tous les worktrees du 20/10 et
après sont conservés par défaut.

### Sous `.worktrees/` et ailleurs

Les **21 worktrees** de `.worktrees/` (8,837 Gio) comprennent
`.worktrees/nuit75-*`, `carto1*`, `rlw04*`, `rlw06*` et `ailist-push`.
Leurs fichiers présentent des activités jusqu'aux **24–25/10** :
**tout garder pour l'instant** même si certains HEAD sont anciens.
Les **11 autres worktrees** enregistrés hors de ces deux dossiers, y compris
la racine principale, sont **hors périmètre de suppression**.

## 6. Scripts d'une seule campagne, anciens briefs et caches

| Chemins / motifs | Quantité et taille | Période / raison | Proposition |
|---|---:|---|---|
| `sweeps/_tmp_*.py` **suivis Git** | **23 scripts, 60 490 octets** (0,058 MiB) | Autopsies C121/C122, analyses et résumés ponctuels, majoritairement sans date dans le nom | **Revue avant retrait**, chercher imports/appels, sauver scripts de reproduction encore utilisés |
| `sweeps/analyse_rail_n2_{fastpath_comparison,first_divergence}_20261009.py` | 2 fichiers, très petits | Analyse ponctuelle du 09/10 | Revue, sans suppression immédiate |
| `sweeps/fixtures/c121_kdec_cold_*_20261002.log` | 2 logs, très petits | Traces de fixtures du 02/10 | **Conserver tant que les tests/fixtures en dépendent** |
| `sweeps/bench_v2.py`, `run_c66_reference.py`, `bench_1v1_5y_20seeds.py`, `physical_counters.py`, `game_health.py`, `campaign_freeze.py`, `sweeps/test_*.py`, `sweeps/archive/` | Harnais/tests/archives | Références explicites d'`AGENTS.md` et contrats de non-régression | **Conserver** |
| `docs/brief_idle1_20261024.md`, `docs/brief_rlw04b_20261024.md` | 2 briefs, **5 937 octets** ensemble | Du **24/10** : récents, possiblement liés aux worktrees | **Conserver** |
| `docs/archives/`, `docs/journaux/`, `docs/taches.md`, `AGENTS.md`, `CLAUDE.md`, `walkthrough.md` | Documentation | Décisions, instructions et historique potentiellement référencés | **Ne pas supprimer à l'aveugle** ; ancienne documentation ≠ fichier inutile |
| `.scratch_saveload/` | **49,82 MiB** | Sauvegardes/états de bancs du 13/10, cache daté jusqu'au 21/10 | **Pré-candidat local**, seulement si aucune reprise/test en cours |
| `.pytest_cache/` et `__pycache__/` racine | **0,293 MiB** | Cache de tests et bytecode Python | Pré-candidats locaux récréables |
| `.venv/` | **506,76 MiB** | Dépendances de développement installées | **Conserver** ; reconstitution possible mais non souhaitable pendant le travail |
| `evidence/`, `content_download/`, `qualifications/` | 62,84 MiB, 0,61 MiB et ~0,006 MiB | Sources et preuves de qualification | **Conserver** jusqu'à audit de références ciblé |

Le gain potentiel des scripts `_tmp_` et des anciens briefs est **négligeable
face aux JSONL** ; leur suppression doit être justifiée par l'absence d'usage,
et non par l'envie de simplifier la liste de fichiers.

## 7. Gains réalistes, sans réécriture de l'historique

| Scénario **hypothétique après approbation** | Gain local brut estimé | Effet sur la version courante de Git | Effet sur l'historique |
|---|---:|---|---|
| **A. Anciennes données ignorées <20/10, non détectées comme citées**, après audit fichier par fichier | **Jusqu'à 32,746 Gio** (35 160 907 924 octets) | Aucun : données déjà ignorées | Aucun |
| **B. Caches locaux régénérables** (`.scratch_saveload/`, `.pytest_cache/`, `__pycache__/` racine) | Jusqu'à **50,11 MiB** supplémentaires | Aucun | Aucun |
| **C. 14 résultats Git antérieurs au 20/10 sans citation littérale** | **Jusqu'à 29,52 MiB**, mais **pas retenu sans revue** | Jusqu'à 29,52 MiB en taille non comprimée du snapshot courant si les fichiers sont effectivement retirés | Aucun gain historique immédiat |
| **D. 23 scripts `sweeps/_tmp_*.py`** | 0,058 MiB (si vérifiés inutilisés) | Minime | Aucun |
| **E. 9 worktrees Git datés 18–19/10** | **4,815 Gio théoriques**, totalement **hors scénario A/B** | Leur enregistrement Git doit être retiré proprement, après sauvegarde des ignorés | Aucun gain garanti dans le pack |

**Première passe maximale mais conditionnelle : environ 32,795 Gio
(A + B)**, sans toucher à aucun fichier suivi Git ni worktree.
Ce n'est **pas un gain déjà réalisé** et ce plafond doit encore être réduit
des références retrouvées lors de la contre-vérification finale.

Pour le **dépôt Git**, la première passe économiserait **0 octet suivi** :
les données de A et B sont déjà ignorées. Une deuxième passe C pourrait
faire baisser la **taille non comprimée de l'arbre courant** jusqu'à
29,52 MiB, mais **pas le pack historique** immédiatement.

À la date de l'inventaire, les fichiers `.pack` de
`.git/objects/pack/` totalisent **445 495 324 octets = 424,86 MiB**
(426,3 MiB en incluant les index et fichiers auxiliaires du dossier).
**Retirer des fichiers de HEAD ne supprime pas leurs anciens objets Git.**
Une réécriture de l'historique, un `git filter-repo` ou un force-push
est **hors périmètre** et n'est pas proposé.

## 8. Liste soumise à validation — aucune opération exécutée

1. **Valider ou ajuster le seuil du 20/10 inclus.** Conserver toutes les
   campagnes plus récentes, toutes les références/baselines et les réglages
   actuels, tous les cas ambigus.
2. **Autoriser, pour une étape ultérieure**, une liste fermée des anciens
   fichiers ignorés **A**, issue d'un contrôle complémentaire sur
   *l'ensemble* du dépôt (documents, scripts, manifests, imports et
   provenance), avec conservation des résumés. Plafond mesuré : **32,746 Gio**.
3. **Facultatif :** autoriser la purge ciblée des caches **B** (~50,11 MiB)
   après vérification qu'aucune reprise SaveLoad n'est attendue.
4. **Différer** tout `git rm` (catégorie C), suppression de scripts (D),
   retrait de worktree (E), rebase, commit, push ou réécriture historique.
   Un audit spécifique serait présenté avant chacun de ces actes.

**État après la présente étape : aucune suppression, aucun commit, aucun push.**
Seul `docs/nettoyage_inventaire_20261025.md` est nouveau et attend
la validation de l'utilisateur.
