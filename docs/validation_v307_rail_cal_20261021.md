# Contrôle de publication V307 / RAIL-CAL-1 — 21 octobre 2026

## Périmètre effectivement livré

Le dépôt `master` comporte les travaux V307 1.7 (sonde et autopsie des extrémités),
V307 1.10 (comptage des jointures aux gares de destination), RAIL-PROFIT-1
(diagnostic statistique hors ligne), et RAIL-CAL-1 (variante `rail_cal=1`
uniquement sur le classement RAIL, défaut `0`). Les rapports d'origine sont
`docs/v307_extremites_20261021.md`, `docs/calibration_rail_jointe_20261021.md`,
`docs/diag_rail_profit_components_20261021.md` et
`docs/rail_cal4_active_20261021.md`.

**V307 1.8 (emplacements de gare dispersés par octant) reste à faire.**
La présence d'une tuile plate dans un autre octant n'établit pas qu'une gare
constructible, desservant correctement le cargo, y soit disponible. Les gares
multi-quais V307 1.9 ne sont pas implémentées non plus ; rien n'est activé en jeu
à leur sujet.

## Validation renouvelée

- `python -X utf8 -m unittest sweeps.test_v307_long_probe sweeps.test_v307_sink_joins sweeps.test_rail_cal sweeps.test_rail_profit_components_20261021 -q` : **23 tests OK**.
- `python -X utf8 sweeps/test_v307_sink_joins.py -q` : **2 tests OK**. Le test
  `test_v307_sink_joins.py` reconnaît désormais l'import en module `sweeps.*`
  ainsi que l'exécution directe, sans changement de la logique du lecteur.
- `python -X utf8 -m py_compile sweeps/diag_v307_long_paths.py sweeps/diag_v307_sink_joins.py sweeps/diag_rail_profit_components_20261021.py sweeps/demo_rail_cal_profit_safe_20261021.py` : OK.
- Relecture du diagnostic sur
  `results/v307_endpoints_3x10_20261021_engine` par
  `python -X utf8 sweeps/diag_v307_long_paths.py results/v307_endpoints_3x10_20261021_engine` :
  **11 autopsies**, 7 inversions `CAP→OK`, 3 `OK→OK`, 1 `CAP→CAP` ;
  **22/22 côtés** avec une tuile libre dans un octant non représenté parmi
  les plans. Reproduction du constat publié, pas validation d'un site de gare.
- `git diff --check` : aucune erreur d'espacement.

Le contrôle est **ciblé** : ce n'est ni une qualification économique de V307
1.8, ni une nouvelle exécution de toute la suite `pytest sweeps -q`.
Le Python local et l'image Docker `openttd-lab` ne contiennent pas `pytest`
dans cette session ; les tests ci-dessus utilisent `unittest`.

## État des bancs

Le 3×10 des extrémités et le smoke RAIL-CAL-1 1×1 ainsi que le 3×3 avaient
déjà été menés et publiés. Pour le 3×3 RAIL-CAL-1 : +140 645 £/an,
3 victoires / 0 défaites, mais p de Wilcoxon = 0,25, donc **non qualifié** ;
`rail_cal=0` demeure le défaut.

Un **40×10 multimodal** `rail_cal4_40x10_multimodal_pc_20261021` a été lancé
séparément : référence `OpexAI[rail_cal=0,decision_log=1]` contre
`OpexAI[rail_cal=1,decision_log=1]`, chacun contre AAAHogEx, 40 graines,
10 ans, un seul Docker jusqu'à 10 workers / 10 CPU. **Au moment de ce contrôle,
la campagne était en cours et le fichier JSON terminal n'existait pas encore.**
Ne pas présenter une partie des journaux comme une campagne complète ni
déduire de verdict statistique avant les 80 parties. Les résultats ne seront
publiables qu'une fois complets et vérifiés (échecs moteurs, erreurs Squirrel,
profils des lignes et valeurs/profits par graine).

## Conclusion

Travaux déjà implémentés : tests de contrat repassés et preuve V307 1.7
reproduite, correctif de portabilité du test 1.10 apporté ; le code
comportemental n'a pas été modifié. Les pistes V307 1.8/1.9 restent ouvertes.
Pas de changement de défaut, pas de réduction AIR ni de porte A engagée.
