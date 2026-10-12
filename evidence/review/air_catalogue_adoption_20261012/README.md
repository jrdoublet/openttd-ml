# AC06 v2 adopté — preuve compacte du 12/10/2026

Cette archive versionnable accompagne l'adoption explicite d'AC06 v2,
aux côtés d'AC04-B et AC05. Elle **ne contient pas le code expérimental
rejeté** : celui-ci reste dans les worktrees archivés
`results/ac_fixes_worktree_20261011` et
`results/ac_opcode_opt_worktree_20261011`.

`validation.json` contient les identifiants de campagne, l'empreinte du
bundle figé, les SHA256 des quatre fichiers bruts de la session, les
deltas opcodes par graine et année complète, les fenêtres bootstrap
appariées, les statistiques économiques terminales, ainsi que la santé
du smoke et du Save/Load. Les données sont dérivées du banc, pas
d'observations reconstruites manuellement.

Les fichiers bruts sont conservés localement sous `results/` (ignoré par
Git) :

- `ac06v2_combo_opcode_10x4_20261012.json` et son
  `_phase_summary.json`, plus `_engine/` (logs source `LOOP_OPS`),
  `.jsonl`, bundle et manifeste gelés ;
- `ac06v2_master_smoke_20261012_r2.json` et son manifeste ;
- `ac06v2_saveload_on_seed512_2p1_20261012.json`.

L'analyseur versionné `sweeps/analyse_ac_loop_opcode.py` reproduit
le résumé opcode à partir des journaux moteur du banc :

```powershell
python -X utf8 sweeps/analyse_ac_loop_opcode.py results/ac06v2_combo_opcode_10x4_20261012.json --out results/ac06v2_combo_opcode_10x4_20261012_phase_summary.json
```

**Contrat d'interprétation :** 10 graines × 4 ans, travail VM annuel
clôturé seulement en 1970–1972 ; moyenne opcode globale négative
mais **9/10 graines en hausse**, notamment +32 opcodes dès 1970.
Les deux bras sont identiques, hormis `ac06_c76_snapshot_ack=0/1`.
La B20×10 historique concerne AC06 **v1** et ne peut démontrer
l'équivalence économique de v2. L'acceptation de v2 est une **décision
utilisateur malgré le résidu opcode**, pas une requalification des versions
AC04-A et AC06 v1/v3.

Voir [la décision complète](../../../docs/ac06_v2_adoption_20261012.md).
