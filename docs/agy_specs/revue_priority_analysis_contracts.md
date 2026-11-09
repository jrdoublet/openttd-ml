# Revue de code : Alignement des assertions de tâches 20x10 (Famille I)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_estim31_20x10_priority_analysis.py`

## 1. Contexte et objectif
Le test `test_tasks_and_provenance_protect_against_reruns` vérifiait que les chantiers prioritaires et les diagnostics issus des 20×10 ESTIM-31 étaient bien consignés dans `docs/taches.md`.
Depuis le commit `729eafb8`, la tâche préliminaire `AIR-PRODUCTIVITÉ` a été affinée en `AIR-COVERAGE-STOP` (EB-1), et le diagnostic `POST-1974-ENTONNOIR` a été complété et clos (`DIAGNOSTIC_NO_GO`), retirant les mentions transitoires antérieures.

## 2. Analyse ligne à ligne du diff
- `sweeps/test_estim31_20x10_priority_analysis.py` :
  - Remplacement de `AIR-PRODUCTIVITÉ` par `AIR-COVERAGE-STOP` dans la liste des priorités actives vérifiées.
  - Vérification de la présence du diagnostic 1×10 clos dans `docs/taches.md`.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- Tests de la famille : **5 tests OK** (0 échec, 0 erreur).
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant.
