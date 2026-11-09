# Revue de code : SkipTest sur artefacts transitoires de campagne absents (Famille J)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre :
- `sweeps/test_estim31_c121_no_upper_20261030.py`
- `sweeps/test_estim31_final_rank_20261030.py`
- `sweeps/test_estim31_joint_next_prepare.py`
- `sweeps/test_estim31_joint_safe_20261030.py`
- `sweeps/test_estim31_motor_joint_20261030.py`
- `sweeps/test_estim31_v161_capcombo_20261030.py`
- `sweeps/test_estim31_v161_coeff_20261030.py`
- `sweeps/test_estim31_v161_policy_20261030.py`
- `sweeps/test_estim31_v161_safe_20261030.py`
- `sweeps/test_estim31_v161_motorcap_20261030.py`

## 1. Contexte et objectif
Ces 10 fichiers de tests ont été créés lors de la phase de préparation et de validation combinatoire ESTIM-31 (du 29 au 30 octobre 2026).
Ils vérifient la cohérence structurelle de dossiers de campagne générés à la volée dans `results/` (`results/estim31_joint_dispatch20261029`, `results/estim31_v161_safe20261030`, etc.).
Puisque le répertoire `results/` est ignoré par Git (fichiers de simulation volumineux non versionnés), ces dossiers ne sont pas présents lors d'un clone, d'une découverte unitaire standard ou dans un worktree dédié. Leur absence levait des `FileNotFoundError` ou des `AssertionError` sur `.is_dir()`.

## 2. Analyse ligne à ligne du diff
Pour chaque fichier, une garde `setUp()` ou une condition sur l'existence des répertoires cibles dans `results/` lève `unittest.SkipTest("artefacts transitoires de campagne absents")` lorsque les données de campagne préalables ne sont pas présentes sur la machine.
Dans `test_estim31_final_rank_20261030.py`, le test mathématique pur `test_ratio_of_means_is_not_mean_of_individual_ratios` continue de s'exécuter et de valider le comportement algorithmique.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant. Les tests restent pleinement fonctionnels et s'exécutent dès lors que la campagne de simulation ou les dossiers de préparation correspondants sont générés dans `results/`.
