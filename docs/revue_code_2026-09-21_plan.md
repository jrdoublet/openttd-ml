# Plan de revue de code — 2026-09-21

Demandée le 2026-09-21, sur le modèle des revues du 2026-09-06 et du 2026-09-15 : un lot cohérent
par étape, un fichier de constats par étape, **rien de corrigé pendant la revue**, puis une étape
de réconciliation qui produit `docs/revue_code_2026-09-21_correctifs.md`.

## Périmètre

Tout ce qui a changé depuis `master` (`62179fb`) sur la branche `c80-orchestrateur`, qui contient
aussi `c69-goulot-decision` :

| zone | lignes ajoutées | ce que c'est |
|---|--:|---|
| `ai/OpexAI/` | ~2 840 (dont la tranche 2 de C80, à committer avant l'étape 3) | C69, C69 bis, C70, C75 (**actifs par défaut depuis le 2026-09-21**), C72 (inactif), sondes C69/C72/C73/C76, orchestrateur C80 (tranches 0-2, inactif) |
| `sweeps/` | ~4 100 (scripts neufs) | harnais de diagnostic et d'analyse qui ont fondé les décisions du jour |

⚠️ **Pourquoi cette revue est urgente** : quatre réglages ont été adoptés par défaut aujourd'hui
(`c75_multi_build`, `c69_decision_bottleneck`, `c69_fleet_exempt`, `c70_mode_calibration`) sur un
banc à 14/20 (p = 0,12), par décision utilisateur. Leur code, écrit en partie par agy dans la
journée, n'a été relu qu'au fil de l'eau.

## Méthode

Reprise du 2026-09-15 :

- **Diagnostic seulement.** Aucun correctif, même évident : noter, ne pas coder.
- **Vérifier à la main, pas par grep seul**, et **vérifier le défaut avant de crier au code mort**
  (la plupart des réglages ajoutés aujourd'hui sont à 0 par conception).
- **Noter aussi ce qui n'est pas un bug**, pour ne pas le relitiger à la correction.
- **Un constat de mesure vaut un constat de logique.** Plusieurs décisions du jour reposent sur des
  sondes écrites le jour même ; ce qu'elles prétendent mesurer compte autant que ce qu'elles
  calculent.
- **Ancrer chaque constat sur `fichier:ligne` et le SHA revu.**
- *(neuf)* **Le code par défaut n'est plus identique à `master` au bit près, et c'est attendu** :
  tout test de drapeau ajouté décale les opcodes, et la trajectoire est chaotique (fiche 11
  §13.4). Un écart de résultat entre deux versions n'est pas, à lui seul, un constat.
- *(neuf)* **Réécritures d'agy dans le chemin par défaut** : plusieurs sondes ont restructuré des
  conditions existantes (`if (a || b) continue` éclatés en blocs avec compteurs). Leur équivalence
  n'a été vérifiée qu'à la lecture ; c'est un point de contrôle explicite de l'étape 2.

## Discipline de quota

- **1 étape = 1 session neuve.** Ne jamais enchaîner deux étapes.
- **Plafond ≈ 2 200 lignes de source lues par étape.**
- **Contexte d'amorçage** : `ai/OpexAI/CLAUDE.md` + la ligne de l'étape + ses fichiers. Pour situer
  un réglage : `grep -n "<nom>" info.nut settings.nut globals_*.nut`.
- **Interdits** : `docs/taches.md` et les journaux en entier, `results/*.json`, `ai/library/`.
  Les fiches du jour (`docs/11` à `docs/18`) ne se lisent qu'à la section citée dans l'étape.
- **Un fichier de constats par étape** : `docs/revue/2026-09-21_etape_<N>_<sujet>.md`.

## Tableau des étapes

Modèle et effort sur l'échelle du skill `/code-review`. Ordre = ordre de priorité : le code actif
par défaut d'abord.

| # | Fichiers et zones | L. (≈) | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 1 | **Chemin par défaut adopté (C69, C69 bis, C70, C75).** `projects.nut` : `OpexProjectSelectAffordable`, `OpexC70Factor`, `OpexC70Profit`, retours `c69Best` ; `task_projects.nut` : `_tryBuildProjects` en entier ; `probes.nut` : `OpexComputeOperatingCashFlow`, `OpexC69ComputeKDec`, `OpexC75*` ; `task_report.nut` : bloc C70 et `line_calib` ; champs `trains0`/`planeId` dans `task_air`, `task_road`, `task_rail` ; câblage des 4 réglages et de `C69_TRACK_BUILDS`/`C75_TRACK_PASSES` dans `info`/`settings`/`globals_pre` ; `persist.nut` pour ce qui survit à un chargement | 1 600 | **Opus 5 / xhigh** | Le code qui décide aujourd'hui. Voir l'encadré A. |
| 2 | **Sondes et réécritures dans le chemin par défaut.** `builder_air.nut` (diff complet, `OpexAirChooseRoutePlane` avec la sonde C72 et le levier `c72_plane_choice`, blocs de filtres de `OpexAirPlans`), `builder_water.nut`, `candidates.nut`, `task_air.nut` (refus de flotte), compteurs C73 dans `projects.nut`, `ledgers.nut` (`_recordC69BuildingPass`), `probes.nut` (C72, C73, C76), `task_report.nut` (`_c76RecordRegen`), `events.nut` | 1 900 | **Opus 5 / high** | Équivalence des conditions réécrites par agy (un `continue` déplacé change une décision) ; toutes les sondes gardées par leur drapeau ; coût des sondes ; ce qu'elles mesurent vraiment. Voir l'encadré B. |
| 3 | **Orchestrateur C80, tranches 0 à 2** (inactif par défaut, mais qui touche le chemin par défaut). `orchestrator.nut` en entier, boucle de `main.nut`, `scheduler.nut` (tranche A* déplacée dans `_advanceRailSearchSliceWithLedgers`, drapeaux `_railWorkerSteppedThisTick`), `scheduler_tasks.nut` (`_dispatchTownGrowth`), `task_town.nut` en entier (refactor `_prepareTownGrowth` / `_tryTownGrowthCity`), enregistrements dans `task_rail.nut`, travailleurs dans `persist.nut` | 1 500 | **Opus 5 / xhigh** | **Préalable : committer la tranche 2 après son smoke.** Le refactor de `town_growth` et le déplacement de la tranche A* sont exécutés **au défaut** : ils doivent être strictement équivalents. Voir l'encadré C. |
| 4 | **Harnais de banc et de diagnostic.** `sweeps/diag_c69_bottleneck_probe.py` (harnais multi-usage : `--arm`, `--raw`, `--extra-tags`, `--grep`, calcul de C1-C5), `diag_c69_paired_solo_duel_5x6.py`, `diag_c69_bis_solo_5x6.py`, `diag_c69_fleet_batch_solo_5x6.py`, `diag_c72_plane_choice_solo_5x6.py`, `diag_c69_duel_erosion.py`, `run_c66_reference.py` (option `--memory`) | 1 550 | Sonnet 5 / high | Appariement des bras, sélection de la dernière sauvegarde, lecture de `profit_year` dans `PLYR`, traitement des échecs, hypothèse de déterminisme (le duel ne l'est pas), égalité réelle des réglages entre bras. |
| 5 | **Scripts d'analyse.** `sweeps/analyse_c70_calibration.py`, `analyse_c72_plane_choice.py`, `analyse_c73_vivier.py`, `analyse_c75_multibuild.py`, `analyse_c76_regen.py` | 1 700 | Sonnet 5 / high | Vérité des chiffres publiés aujourd'hui : étiquettes d'année (le rapport du 1er janvier publie l'année précédente), agrégation entre graines (somme ou médiane), correction d'amortissement, médianes par ligne, selftests qui testent vraiment le code. |
| 6 | **Réconciliation.** Les 5 fichiers de constats, et eux seuls | — | Opus 5 / high | Produire `docs/revue_code_2026-09-21_correctifs.md` (constat, gravité, correctif proposé, banc requis), mettre à jour `ai/OpexAI/CLAUDE.md` (4 nouveaux défauts, C80, retrait du « 93 % ») et `docs/taches.md`. |

## Encadrés — pistes déjà connues (point de départ, pas conclusions)

**A. Étape 1, chemin adopté.**

- **Rien de C69/C75/C70 ne survit à un chargement** : `C69_BUILD_DATES`, `C75_PASS_DATES` et
  `C70_MODE_FACTOR` ne sont pas dans `persist.nut`. Après rechargement d'une vraie partie, K_dec et
  K_pass valent 0 et les facteurs C70 reviennent à 1 jusqu'au prochain rapport annuel : le
  comportement change brutalement. Les champs `c70Real`/`c70Pred` des lignes sont des flottants,
  arrondis en entiers par la projection de sauvegarde existante (`persist.nut:~447`) : pas de
  plantage, à confirmer.
- **Deux définitions de τ coexistent** : C69 prend 365 / chantiers de l'année, C75 la durée réelle
  entre deux passes. Sous C75, les chantiers sont plus nombreux, donc K_dec (C69) plus petit.
- **C75** : après un chantier, la passe continue dans la liste classée sans la régénérer. Deux
  projets de la même passe peuvent viser le même aéroport ou la même ville ; un projet de flotte
  peut viser une ligne modifiée par le chantier précédent. Vérifier que ces cas échouent proprement
  et ne coûtent pas de capital.
- **C70** : k = (Σ ratios + 1) / (n + 1), sans borne : un ratio aberrant (négatif ou très grand)
  d'une ligne pèse autant qu'une ligne normale.
- **C69 bis** exempte la flotte dans `fundScore`, mais C75 compare le coût de tout projet, flotte
  comprise, à K_pass : cohérent ou non ?
- `C69_TRACK_BUILDS` enregistre les dates de chantier de tous les modes, flotte comprise : N (donc
  τ) compte-t-il ce qu'il doit compter ?

**B. Étape 2, sondes.**

- Réécritures d'agy à vérifier une par une contre `master` : filtres de `OpexAirPlans` (trois
  boucles), refus de flotte dans `_resizeAirFleets`, filtres route dans `candidates.nut`, eau, et
  l'appel de flotte dans `OpexBuildProjects` (une vérification de `null` ajoutée).
- La sonde C76 annonce un champ « jours » qui n'a jamais été renseigné.
- Les compteurs C73 cumulent sur tous les appels de génération de l'année : ce ne sont pas des
  candidats distincts.
- Sonde C69 : le « premier rang actuel » est figé au début de la passe ; la ligne est publiée par
  passe qui construit, pas par chantier.

**C. Étape 3, orchestrateur.**

- Sous `c80_worker_rail=1`, identité non démontrée au smoke (graine 100 : 1,78 contre 1,80 M£),
  attribuée aux opcodes ; aucune différence de logique trouvée à la première lecture.
- Le travailleur `town_growth` perd sa référence à l'IA au rechargement (non sauvegardée) : il est
  annulé puis recréé par la tâche.
- Registre à un emplacement : sous recherche rail, `town_growth` retombe sur le chemin monolithique.

## Sorties attendues

- `docs/revue/2026-09-21_etape_1_defaut_adopte.md`
- `docs/revue/2026-09-21_etape_2_sondes.md`
- `docs/revue/2026-09-21_etape_3_orchestrateur.md`
- `docs/revue/2026-09-21_etape_4_harnais_banc.md`
- `docs/revue/2026-09-21_etape_5_analyses.md`
- `docs/revue_code_2026-09-21_correctifs.md` (étape 6)
