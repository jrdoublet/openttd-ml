# AIR catalogue CD00–CD07 — archive durable de qualification (12/10/2026)

## Décision

**CD01–CD06 adoptés et portés localement dans `master` sans commit/push.**
Architecture CD07 : une seule entrée globale `catalog`, sous-étapes
fonctionnelles internes et transactions `PublishPartial` / `Apply`.
L'extraction n'est pas censée procurer de gain économique ou opcode.
L'adoption suit la porte préenregistrée de **non-érosion**, pas une preuve
d'équivalence stricte ou une promesse de gain.

## Campagnes et provenance

- Témoin : `results/cd_baseline_stage_20261012`, HEAD `a09a7b2`,
  OpexAI SHA256 `9dce7c432c28232695297266909657f5b3bdbd131209a4c146fa90cb7efb3578`.
- Variante CD01–CD06 : `results/cd_combined_stage_20261012`, même HEAD
  initial, OpexAI SHA256
  `c2336561f5325283e6932806b14291e014f6d8691c200c98b186d5fb02641fbe`.
- AAAHogEx partagé : SHA256
  `eaec19151d118daad80eddab437180402764e1c919f48904cc22cbf71cb80bc7`.
- Deux C66.3 mono-politiques **successifs par population** : impossible de
  faire coexister deux AI distinctes toutes deux nommées `OpexAI` dans une
  même exécution OpenTTDLab sans risque d'écrasement de source.
  Les manifestes figés prouvent mêmes configurations effectives, moteurs,
  versions, bibliothèques, graines et adversaire. Les empreintes sources
  OpexAI doivent précisément différer.
- 40 paires, 4 ans, avec `probe_loop_ops=1` / `--script-debug` :
  profit terminal variante−référence **−4 389 £/an**, IC95
  [−77 637 ; +65 790] ; opcodes exécutés globaux **1970–1972**
  **+362 455** (+0,1884 %), IC95 [−1 268 967 ; +2 080 063],
  21 hausses / 19 baisses. Année terminale 1973 censurée dans les
  dumps LOOP_OPS. Rapports C10×4 + C30×4 et agrégat C40×4 ci-présents.
- **B20×10 indépendant**, 20 nouvelles graines, 10 ans, sans sondes :
  toutes les paires saines ; profit terminal **+70 240,2 £/an**
  (+2,436 %), IC95 bootstrap apparié [−73 286,4 ; +203 040,45],
  12 hausses / 8 baisses ; valeur d'entreprise **+299 567 £**
  (+1,9949 %), IC95 [−159 557 ; +762 847]. Porte préenregistrée
  franchie : 20/20 paires, borne supérieure du profit >= 0,
  valeur variante/référence >= 0,95.

Les six couples `.json` et `.manifest.json` contiennent **les données
brutes de campagne et le gel de provenance**, pas seulement les moyennes.
Les cinq fichiers `*_comparison.json` permettent de vérifier les
résultats publiés. Les logs moteur VM textuels C40×4 (environ 147 Mo)
ne sont **pas** dupliqués dans Git. À leur place,
`cd_combined_C40x4_20261012_opcode_annual_raw.json` archive **les
compteurs annuels réels par graine, année, poste, et bras** extraits
des 80 journaux originaux, y compris `loop_executed_ops` et
`sleep_left_ops`. Il reste possible de retrouver les journaux intégraux
dans les quatre répertoires `results/*_engine` des arbres figés.

La ventilation calculée à partir de ces logs figure dans
`cd_combined_C40x4_20261012_phase_comparison.json`. Elle donne
`air_light_coverage.measured=false` : **aucune ventilation intrinsèque
AIR_LIGHT n'a été mesurée** et ses différences ne doivent pas être
interprétées comme nulles. `analyse_cd_phases_20261012.py` est une
copie du collecteur de cette preuve, conçu pour les worktrees nommés
ci-dessus.

## Reproduction du contrôle économique sans Docker

Depuis la racine de `master`, exécuter :

```powershell
python -X utf8 sweeps/compare_cd_cross_tree_c66.py `
  evidence/review/air_catalogue_cd_20261012/cd_baseline_B20x10_20261012_r1.json `
  evidence/review/air_catalogue_cd_20261012/cd_combined_B20x10_20261012_r1.json `
  --economic-only --out results/cd_master_B20x10_evidence_recomputed.json
```

Le résultat ainsi reproduit le 12/10/2026 possède une **empreinte SHA256
identique** au fichier
`cd_combined_B20x10_20261012_r1_comparison.json` de l'archive.
Le comparateur est dans `sweeps/compare_cd_cross_tree_c66.py` ;
`sweeps/aggregate_cd_cross_tree.py` permet de regrouper des lots de graines
disjoints de même horizon/sources.

Contrôle **opcode C40×4 sans Docker ni anciens logs** :

```powershell
python -X utf8 sweeps/verify_cd_opcode_archive.py
```

Cette vérification a été exécutée avec succès. Elle recalcule **pour
chaque graine** les sommes de postes exécutés (hors `_year` et
`sleep_left`), compare les 40 deltas par graine avec le rapport agrégé,
puis revérifie les moyennes, ratios et nombres de hausses/baisses des
fenêtres 1970–1971 et 1970–1972. Elle confirme +362 454,8 opcodes et
+0,188438 % sur la fenêtre longue, 21 hausses / 19 baisses.

## Contrats et contrôle moteur après intégration

- `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py' -q` :
  **1 963/1 963 PASS** sur master, dont deux tests de reproduction
  d'archive (`sweeps/test_cd_cross_tree_evidence.py`). Une empreinte
  obsolète du test
  `test_parallel_fleet_amort_shadow` a été actualisée sur le HEAD de
  référence *inchangé* : `projects_builders.nut` n'a pas été modifié.
- Contrôles AIR : **682/682 PASS**, contrôles ciblés CD/AC : **44/44 PASS**.
- Save/Load OpenTTD exécuté sous Docker sur le lot CD, sur CD+AC04-A v3,
  puis sur `master` intégré. La preuve brute du dernier est
  `cd_master_saveload_seed512_2p1_20261012.json` : graine 512, 2 ans,
  sauvegarde 1971-01-01, reload + 1 an, 25 sauvegardes A / 13 B,
  `LOAD_RECONCILE` positif, 8→35 stations, 13→50 véhicules,
  zéro erreur moteur. Une compagnie fantôme du harnais est signalée,
  sans effet observé sur l'entreprise OpexAI mesurée.

**Limite de portée :** les A/B indépendants comparent les arbres gelés
avant certains nettoyages C121 simultanément effectués dans `master`.
Les tests et Save/Load confirment leur coexistence et l'absence de panne,
mais ne sont pas un nouvel A/B économique de la **somme de tous les
nettoyages C121**. AC04-A v3 avait été qualifié par ses propres campagnes.

Documents de décision : `docs/cd_air_catalogue_validation_20261012.md`,
`docs/cd07_air_catalogue_ordonnanceur_20261012.md` et journal du 12/10.
V142/V143, AC04-A v1/v2 et AC06 v1/v3 demeurent rejetées.
