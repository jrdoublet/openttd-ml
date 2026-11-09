# Revue de Diff — Activation par défaut de idle1_slack_worker et eb7_detailed_accounting à 1

## 1. Périmètre du Diff

Conformément à la décision utilisateur, deux réglages passent à 1 par défaut :
- `idle1_slack_worker` : valorisation du reliquat de tick pour tâches de fond (OPCODES/IDLE-1).
- `eb7_detailed_accounting` : comptabilité fine et passive des dépenses réelles AIR/ROUTE (EB-7 Phase 2).

### Fichiers modifiés :

1. **Squirrel (runtime AI) :**
   - `ai/OpexAI/globals_pre.nut` :
     - `IDLE1_SLACK_WORKER <- 1;`
     - `EB7_DETAILED_ACCOUNTING <- 1;`
   - `ai/OpexAI/info.nut` :
     - `idle1_slack_worker` : 4 difficultés (`easy_value`, `medium_value`, `hard_value`, `custom_value`) passées de 0 à 1.
     - `eb7_detailed_accounting` : 4 difficultés (`easy_value`, `medium_value`, `hard_value`, `custom_value`) passées de 0 à 1.
   - *Aucun autre fichier `.nut` ni réglage n'a été modifié.*

2. **Tests de contrat et fixtures :**
   - `sweeps/test_idle1_contract.py` :
     - Assertions mises à jour pour attendre les 4 valeurs de difficulté à 1 et la globale initiale à 1.
   - `sweeps/test_eb7_detailed_accounting.py` :
     - Assertions mises à jour pour attendre les 4 valeurs de difficulté à 1 et la globale initiale à 1.

3. **Projections et adaptateurs d'héritage (legacy & merge) :**
   - `sweeps/road100_off_projection.py` :
     - Mise à jour des empreintes SHA de `globals_pre.nut` et `info.nut` dans `ROAD1Y_B2_RAIL_MERGE`.
     - Ajout des étapes intermédiaires (`rail_long_off`, `rail_search_prio_off`, `rail_depot_signal_off`) dans `ROAD1Y_B2_RAIL_MERGE_STAGES` pour `globals_pre.nut` et `info.nut`.
   - `sweeps/rail_open_legacy.py` :
     - Ajout des nouveaux SHA de `globals_pre.nut` et `info.nut` dans `_MERGE_SHA`.
   - `sweeps/rail_sibling_legacy.py` :
     - Ajout des nouveaux SHA de `globals_pre.nut` et `info.nut` dans `_MERGE_SHA`.

---

## 2. Vérifications de Non-Régression et Invariants

1. **Conservation stricte du chemin OFF :**
   - Les projections « OFF » (`off_source`, `historical_info`, etc.) continuent d'autoriser et de reproduire exactement les sources historiques lorsque les réglages sont à 0.
   - Testé et validé par `test_origin_master_keeps_all_historical_projector_bytes` et `test_no_new_public_setting`.

2. **Aucune assertion affaiblie ou supprimée :**
   - Seules les valeurs attendues (0 → 1) et les empreintes cryptographiques SHA256 associées ont été actualisées.

3. **Résultats des suites de tests unitaires :**
   - `test_road1y*.py` : 74/74 tests passés avec succès.
   - `test_road100*.py` : 236/236 tests passés avec succès (3 skipped).
   - `test_v251*.py` : 7/7 tests passés avec succès.
   - Suite complète (`sweeps/test_*.py`, 3885 tests) :
     - Échecs/erreurs sur `HEAD` propre : 91 (157 failures, 15 errors, 29 skipped, 2 expected failures).
     - Échecs/erreurs sur l'arbre de travail : exactement les 91 mêmes échecs/erreurs.
     - **0 nouvelle défaillance, 0 régression.**

4. **Hygiène Git :**
   - `git diff --check` : code retour 0, aucun problème de fin de ligne ou d'espace.

---

## 3. Conclusion

La mise à jour des tests et adaptateurs après passage à 1 par défaut des deux réglages est complète, cohérente et rigoureusement vérifiée contre la référence `HEAD`.
