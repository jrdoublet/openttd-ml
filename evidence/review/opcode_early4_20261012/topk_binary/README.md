# P0 Top-K binaire — archive gelée du 12/10/2026

**Décision : gain local documenté ; innocuité économique C66 franchie ; adoption opcode globale NON DÉMONTRÉE.** Voir le [rapport détaillé](../../../../docs/p0_topk_binary_qualification_20261012.md). Aucun commit/push ni changement de défaut.

## Provenance

- Arbre expérimental : `results/p0_topk_binary_stage_20261012`, worktree détaché `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f` avec modifications expérimentales **non commitées**.
- Bundle identique pour check moteur et B20×10 : `def46d6313e572fa4b4067b383b64e841009cec22c8d03c855ea563f33cb8d80`.
- Docker image `openttd-lab:latest`, digest `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ; OpenTTD 15.3, OpenGFX 7.1, configuration partagée C66, 10 CPU, 10 workers, 8 Go/swap8 Go.
- Les traces moteur brutes, jeux mensuels volumineux et bundles sont sous `results/p0_topk_binary_stage_20261012/results/` ; **ils sont ignorés par Git**. Les résultats principaux et manifestes de freeze sont copiés ci-dessous pour inspection pérenne.

## Fichiers

| Fichier | Interprétation / limites |
|---|---|
| `stage_protocol.md` | Pré-enregistrement et exposition du candidat ; conserver l'historique, y compris sections « prochaine campagne » devenues révolues. |
| `topk_candidate.patch` | Diff du prototype Squirrel depuis le HEAD du stage, **sans** le fichier `probes.nut` copié du principal. |
| `shadow_parity_5x5.json`, `shadow_parity_5x5.manifest.json` | 57 859 comparaisons en VM, 0 mismatch ; coût local ancien / nouveau sur mêmes entrées, check double non neutre. |
| `probe1_b20x10.json`, `probe1_b20x10.manifest.json` | C66 apparié 20×10, `probe_loop_ops=1` dans les deux bras : santé et économie, pas mesure VM pure. |
| `probe1_b20x10_global.json` | `LOOP_OPS` top-level disjoints sur 1970–1978, référence/variante par graine, IC95. |
| `probe1_b20x10_global_early4.json` | Sous-période P0 1970–1973, mêmes traces, sans sommer registres imbriqués. |
| `probe0_b20x10.json`, `probe0_b20x10.manifest.json` | C66 indépendant sans `probe_loop_ops`, contrôle économique de non-érosion ; 20/20 paires saines. |
| `probe1_b20x10_construction.json`, `probe0_b20x10_construction.json` | Analyse physique et mensuelle : stocks par mode, activité, santé, proxy IB ; **lignes AIR/RAIL construites = non mesurées**. |
| `save_load_on_2plus1.json` | Save/Load moteur avec variante ON, 25/13 sauvegardes et `LOAD_RECONCILE`. |
| `analyse_check.py`, `analyse_global.py`, `analyse_construction.py` | Décodeurs copiés du stage utilisé pour obtenir les rapports. |
| `test_stable_order.py`, `test_adversarial.py`, `test_construction.py` | Tests de parité mécanique, hypothèses comparateur et validité de l'attribution physique. |

Les sources principales des scripts sont également présentes dans le stage sous `sweeps/`, avec leurs noms complets (`analyse_p0_topk_*.py`, `test_analyse_p0_topk_*.py`). La copie d'archive conserve leurs contenus, pas les chemins d'import Python ; exécuter la suite depuis le **stage**.

## Résultats indépendamment vérifiables

- **Check moteur** : 57 859 insertion old/new, 0 mismatch, old 103 690 025 fenêtres, new 34 584 049, réduction locale **−66,65 %**.
- **B avec LOOP_OPS** : 20/20 paires, profit terminal variante−référence **+97 898,55 £/an**, IC95 bootstrap [−44 484,6 ; +253 697,85], valeur **+1,725 %**, C66 `pass`. Delta global fenêtres d'opcodes 1970–1978 **−1 043 759,55** par graine, IC95 [−3 849 968 ; +1 770 812] : pas de gain global significatif.
- **B sans LOOP_OPS** : 20/20 paires, profit terminal **−8 341,25 £/an**, IC95 Student [−174 611,88 ; +157 929,38], IC95 bootstrap [−159 372,7 ; +141 663,45], signes p=0,8238, valeur **−0,708 %**, C66 `pass`.
- **Santé et croissance** : 20/20 paires/120 checkpoints mensuels chacune par bras, aucune faillite ni alerte globale de stagnation ; signes indirects favorables en moyenne, **`strict_non_famine_certified=false`** faute de `line_telemetry`/P5_BUILD_LINE.
- **Save/Load** : `LOAD_RECONCILE` moteur avec variante ON, pas de motif de chargement erroné.

Ces résultats ne qualifient pas une augmentation du budget worker utilisable (toujours **0 opcode récupéré effectivement** sur les études tail précédentes) ni une accélération nette démontrée de créations de lignes. Ne pas additionner C39, `PROJECTS_COST`, `SPAN`, `SPAN_AGG` et catégories `LOOP_OPS` imbriquées.

### Reproduction hôte

Depuis `results/p0_topk_binary_stage_20261012` :

```powershell
python -B -X utf8 -m unittest discover -s sweeps -p test_p0_topk_binary_adversarial.py -v
python -B -X utf8 -m unittest discover -s sweeps -p test_analyse_p0_topk_construction.py -v
python -B -X utf8 sweeps/analyse_p0_topk_global.py results/p0_topk_binary_b20x10_20261012_engine --out results/p0_topk_binary_b20x10_20261012_global.json
python -B -X utf8 sweeps/analyse_p0_topk_construction.py results/p0_topk_binary_noprobe_b20x10_20261012.json --out results/p0_topk_binary_noprobe_b20x10_construction.json --fail-on-qa
```

Pas de relance du B20×10 pour chercher un meilleur résultat. Si une future campagne distincte est autorisée pour qualifier la construction, spécifier en amont quelle donnée prouve de **nouvelles lignes AIR/RAIL** ; `--line-telemetry` reconstruit des *services actifs* à partir des savegames et n'est pas un journal direct des créations.
