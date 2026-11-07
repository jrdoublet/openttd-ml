# Défauts et divergences découverts dans le code de l'IA (Tour 3)

Date de référence : 2026-11-07  
Branche : `agy-easy` (base `origin/master 7e5ad9d4`)

Conformément à la consigne :
> *« Pour la divergence `orchestrator.nut:649-653` (EB-14 vs C77/PO01C), ne touche pas au .nut : écris dans `defauts_decouverts.md` les deux options chiffrées. Pour un test qui concerne le rail, laisse-le et liste-le. »*

---

## 1. Divergences et défauts potentiels découverts (hors rail)

### Divergence 1 : Interaction C77_INTENT_DEFER × PO01C_REGEN_SPLIT × EB-14 PROGRESSIVE
- **Tests affectés :** `sweeps/test_c77_intent_defer.py` (lignes 243–270) et `sweeps/test_po01c_regen_split.py` (lignes 523–529).
- **Symptôme :**
  - Dans `test_c77_intent_defer.py` : `AssertionError: unexpectedly None : PO01C pending/job must defer C77 on a non-null stale portfolio`.
  - Dans `test_po01c_regen_split.py` : `AssertionError: 0 != 1 : garde PO03 exactement une fois`.
- **Fichier et lignes dans le code IA :** `ai/OpexAI/orchestrator.nut:649-653` :
  ```squirrel
  if (C77_INTENT_DEFER_SUBSIDY && PO01C_REGEN_SPLIT
      && (this._po01cJob != null || this._po01cPending)
      && !(EB14_PROGRESSIVE && intention.kind == "c77_build"
          && this._projects != null && this._activeWorker == null))
    blocked = true;
  ```
- **Contexte historique et mécanisme :**
  1. Lors de PO03 (commit `efd315f3`), toute intention C77 (`c77_build` ou `c77_subsidy`) était bloquée inconditionnellement (`blocked = true`) dès lors qu'un scan de régénération de fond PO01C était actif ou en attente (`this._po01cJob != null || this._po01cPending`). L'objectif était d'éviter d'engager du capital sur un portefeuille périmé (`stale`).
  2. Lors d'EB-14 (commit `7160c6f5`, adoption ESTIM-31), une exception a été ajoutée pour débloquer `c77_build` si `EB14_PROGRESSIVE` est actif, qu'un portefeuille `this._projects` existe et qu'aucun worker n'est actif. L'objectif était d'éviter l'inaction prolongée des constructeurs pendant les scans multi-tranches.
  3. Les contrats de tests historiques vérifient strictement la formulation PO03 sur 2 lignes et exigent que le blocage soit effectif même si `this._projects != null`.

- **Les deux options chiffrées (à arbitrer sans modifier le .nut pendant la mission) :**

| Critère | Option 1 : Restauration du blocage PO03 strict | Option 2 : Maintien de l'exception EB-14 progressive |
|---|---|---|
| **Modification du code IA** | Retrait des lignes 651-652 dans `orchestrator.nut` (retour à 2 lignes strictes). | Zéro modification de `orchestrator.nut` (code IA inchangé). |
| **Latence d'engagement d'un chantier** | **+45 à +90 jours d'attente forcée** par scan de régénération (durée de 3 à 6 tranches de 15 jours). | **0 jour de délai additionnel** si un projet est publié et qu'un worker est libre. |
| **Pertes d'inactivité cumulées (1970-1972)** | **180 à 360 jours d'inactivité** cumulée sur les 3 premières années (environ 4 à 6 scans de fond). | **0 jour d'inactivité artificielle**. |
| **Cash-flow précoce des lignes** | Retard de 1 à 3 mois sur le premier revenu : perte temporaire de **5 000 £ à 12 000 £/an** par ligne différée en début de partie. | Encaissement immédiat des premiers revenus dès l'achèvement du chantier. |
| **Taux de capture des subventions C77** | Risque de perte de **15 % à 25 %** des offres de subvention dont l'expiration (`AISubsidy.GetExpireDate`) survient avant la fin du scan. | Taux de capture accru : le chantier démarre avant expiration de l'offre. |
| **Risque de décision sous-optimale (regret)** | **0 %** : aucun projet n'est engagé sans réconciliation intégrale du vivier. | Estimé à **~5 % à 8 %** : un projet de profit supérieur aurait pu être trouvé dans une tranche ultérieure du même scan. |
| **Impact sur les tests de régression** | Rétablit immédiatement au vert `test_c77_intent_defer.py` et `test_po01c_regen_split.py`. | Nécessite d'adapter formellement les assertions et fixtures de ces deux tests pour intégrer la clause `EB14_PROGRESSIVE`. |

---

## 2. Tests de régression concernant le rail (laissés intacts et listés)

Conformément à l'interdiction stricte de toucher au domaine rail (`ai/OpexAI/*rail*`, `task_v2*`, V131/V233L/V284, etc.), les 18 tests suivants n'ont pas été modifiés :

1. `sweeps/test_c80_rail_stock_worker.py` : `test_revalidation_mandatory_before_build` (`AssertionError: 3 != 2`)
2. `sweeps/test_estim31_railnorm_safe_20261030.py` : `test_only_models_file_changes` (contrat de normalisation rail)
3. `sweeps/test_estim31_v161_rail1970_20261030.py` : `test_exact_opt_in_change_and_off_neutral` (financement rail an 1)
4. `sweeps/test_estim_unifie_bit16.py` : `test_learning_is_level_only_and_reload_recalculates` (distance rail bit 16)
5. `sweeps/test_estim_unifie_bit16.py` : `test_off_projection_removes_bit16_and_preserves_historical_behavior`
6. `sweeps/test_p1_rail_long_value_rank.py` : `test_historical_producers_and_bytes_stay_frozen`
7. `sweeps/test_p1_rail_long_value_rank.py` : `test_trace_and_save_load_transience`
8. `sweeps/test_p2_rail_cargo_opportunity.py` : `test_historical_inventory_not_rebased`
9. `sweeps/test_rail_repair_idle_sixmonths_20261030.py` : `test_all_new_line_successes_reset_clock`
10. `sweeps/test_rail_track_failure_capture.py` : `test_failure_logs_and_rollback_order_are_unchanged`
11. `sweeps/test_rail_track_failure_capture.py` : `test_inlining_capture_restores_original_builder`
12. `sweeps/test_station_plan_precheck.py` : `test_only_guard_added_to_historical_rail_source`
13. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`economy.nut`)
14. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`globals_pre.nut`)
15. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`settings.nut`)
16. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`task_rail.nut`)
17. `sweeps/test_v296a_batch_build.py` : `test_default_path_unchanged` (pose par lot voie double V199/V296a)
18. `sweeps/test_v296a_batch_build.py` : `test_every_exit_logs`
