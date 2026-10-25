# Sondes en partie normale — 20×10 de non-érosion et profil opcodes

25 octobre 2026. **Verdict : PASS `non_erosion` ; les trois gardes de diagnostics
`DEBUG_SIGNS` sont retenues comme optimisation d'opcodes.** Aucun réglage de
publication ou valeur par défaut n'a été changé. L'adoption porte sur ces trois
gardes, **pas** sur toute la tâche générale « sondes non essentielles ».

## Intervention figée

- Référence : commit `2be4692500c2e85e31a475f8ea9c852c957eadd6`,
  `ai/OpexAI/task_report.nut` sans changement ; extrait de checkout détaché
  `.worktrees/probe_gate_ref_20261025`.
- Variante : même commit et **seul `task_report.nut` différent** : garde VS/VL
  autour de `GetState/ResolveOrderPosition/GetCurrentSpeed/GetCargoLoad`, garde
  RV autour des vitesses et médianes RAIL, retour anticipé de `_reportYear`
  quand `!DEBUG_SIGNS && !C69_BOTTLENECK_PROBE`.
- `probes=0` effectif dans **les deux** bras. Le harnais C66.3, en général,
  force `probes=2` et aurait rendu les gardes inopérantes : autorisation hôte
  explicite `--probes 0 --allow-panel-free` ajoutée, avec transmission
  `C66_ALLOW_PANEL_FREE=1` au parseur ; sans ce drapeau l'interdiction reste
  inchangée. Le vrai moteur vérifie aussi les réglages effectifs du manifeste.
- Deux campagnes C66.3 du même harnais, déroulées **successivement**, combinées
  par le calcul C66.4 officiel `build_policy_comparison`. 20 graines du script
  `sweeps/run_v277v279_pc.sh` avec 373684 à la place de 73, une répétition,
  1970–1979, cartes 256², duel OpexAI/AAAHogEx identique, 9 workers,
  Docker 10 CPU/8 GiB, OpenTTD 15.3, OpenGFX 7.1, réseau hôte.
- Vérification préalable : suite `unittest discover` **2 498 tests OK**, 5
  ignorés, 2 échecs attendus ; `git diff --check` OK. Aucun Docker concurrent.

Le contrôle hors moteur compare tous les fichiers gelés : `ai/OpexAI` diffère
**seulement** par `task_report.nut`, 17 fichiers AAAHogEx identiques. Les 16
fichiers de harnais sont identiques après normalisation LF : un seul,
`sweeps/paired_statistics.py`, possède des fins CRLF Windows contre LF dans
le worktree détaché. Aucune autre exception d'empreinte. Les bundles et leurs
manifestes originaux n'ont pas été retouchés après le gel.

## Résultat économique (Opex variante − Opex référence)

| Indicateur | Résultat |
|---|---:|
| Parties / paires complètes et saines | 40/40 parties, **20/20 paires**, 0 erreur |
| Δ `profit_year` en 1979, moyenne | **+80 834,55 £/an** |
| Médiane | +106 801,50 £/an |
| Victoires / défaites / égalités | **12 / 8 / 0** |
| Wilcoxon exact bilatéral | **p=0,3682766** |
| Test des signes bilatéral (descriptif) | p=0,503445 |
| IC95 bootstrap percentile de la moyenne, 20 000 rééchantillonnages | **[−133 622 ; +298 352,20] £/an** |
| Ratio des moyennes `company_value` (variante vs référence) | **+2,549863 %** ; garde −5 % passée |
| Verdict du comparateur `non_erosion` | **PASS** (borne haute IC95 ≥ 0 et garde de valeur) |

| Bras | `profit_year` Opex moyen | `profit_year` AAA moyen | Opex / AAA, ratio des moyennes |
|---|---:|---:|---:|
| Référence | 4 128 479,50 £/an | 7 492 137,70 £/an | **55,1042 %** |
| Variante | 4 209 314,05 £/an | 7 206 273,25 £/an | **58,4118 %** |

L'amélioration moyenne d'OpexAI n'est **pas significativement positive** et
le ratio contre AAA n'isole pas la cause de ses fluctuations. L'exigence
non-érosion est néanmoins remplie, avec toutes les paires vérifiées. Durée
manifeste→rapport : référence **1 027,42 s (17 min 07 s)**, variante
**908,64 s (15 min 09 s)**, total ≈ **32 min 16 s** ; aucune partie ne s'est
superposée à un autre Docker.

## Gain d'opcodes : mesure moteur dédiée, non économique

Un microprofilage **séparé**, sur copies isolées des deux sources (pas dans les
bundles économiques), entoure `_reportYear` et `_reportLines` avec
`OpexOpsMeasureBegin/End` puis journalise **après** les mesures. Deux parties
graine 42 × 3 ans, `probes=0`, un worker, chacune complète et sans erreur.

| Exercice | `_reportYear` ancien → gardé (ops) | `_reportLines` ancien → gardé (ops) | Lignes ancien → gardé |
|---|---:|---:|---:|
| 1970 | **9 306 → 20** | 361 → 361 | 0 → 0 |
| 1971 | **6 464 → 20** | 6 963 → 6 568 | 15 → 14 |
| 1972 | **11 345 → 20** | 23 337 → 21 157 | 47 → 43 |

Les **9 286 opcodes économisés par `_reportYear` en 1970** sont une preuve
directe de gain sur un même cas avec zéro ligne et mêmes réglages ; les coûts
mesurés des deux chemins annuels restent positivement différents par la suite.
La diminution totale de `_reportLines` en 1971–1972 **n'est pas une estimation
causale du gain VS/VL/RV**, car la flotte et le nombre de lignes divergent :
ne pas la retrancher du budget ni prétendre à une identité des trajectoires.
Les 4 appels de VS/VL par véhicule fret et les parcours RV évités au défaut
restent garantis statiquement par les 8 contrats hôte. Le microprofil ne sert
**pas** à mesurer un delta de profits ni à changer les seuils économiques.

## Artefacts et décision

- Référence : `.worktrees/probe_gate_ref_20261025/results/probe_gates_ref_20x10_20261025b.json`, manifeste, JSONL, bundle et 20 journaux.
- Variante : `results/probe_gates_variant_20x10_20261025.json`, manifeste, JSONL, bundle et 20 journaux.
- Comparaison et contrôle intégrité :
  `results/probe_gates_non_erosion_20x10_20261025_comparison.json` ; outil
  `sweeps/compare_probe_gates_20x10.py` (source identique hors
  `task_report.nut`, paires, chiffres et règle C66.4).
- Microprofil référence : `.worktrees/probe_gate_ref_20261025/results/probe_gates_opmicro_ref_3y_20261025_engine/` ;
  variante : `.worktrees/probe_gate_micro_var_20261025/results/probe_gates_opmicro_var_3y_20261025_engine/`.

**Décision technique : retenir les gardes déjà présentes** avec le profil
`probes=0` publié, au titre de « gain d'opcodes observé + B20×10 sans perte ».
Le mode banc `probes=2` continue à produire VS/VL/RV/TV ; la santé, C70/C121,
le journal `RY/LINE_REVENUE` et la sonde C69 sont conservés. Il reste à auditer
les autres sondes résiduelles et les états décisionnels : la tâche générale
reste donc ouverte. Aucun commit ou push n'a été effectué.
