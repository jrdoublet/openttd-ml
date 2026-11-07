# Défauts et divergences découverts dans le code de l'IA (Tour 2)

Date de référence : 2026-11-07  
Branche : `agy-easy` (base `origin/master 7e5ad9d4`)

Conformément à la consigne :
> *« Pour un test dont l'échec révèle un vrai défaut du code de l'IA (et non une attente périmée), ne corrige PAS le `.nut` : consigne-le dans `docs/agy_specs/defauts_decouverts.md` (test, symptôme, fichier:ligne, hypothèse) pour que je le traite. Pour un test qui concerne le rail, laisse-le et liste-le. »*

---

## 1. Divergences et défauts potentiels découverts (hors rail)

### Divergence 1 : Interaction C77_INTENT_DEFER × PO01C_REGEN_SPLIT × EB-14 PROGRESSIVE
- **Tests affectés :** `sweeps/test_c77_intent_defer.py` (ligne 251) et `sweeps/test_po01c_regen_split.py` (lignes 523–529).
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
- **Hypothèse / Analyse :**
  Historiquement (commit `efd315f3`, correctif PO03), toute intention C77 (`c77_build` ou `c77_subsidy`) était bloquée (`blocked = true`) dès lors qu'une passe de régénération PO01C était en cours ou en attente (`this._po01cJob != null || this._po01cPending`), afin d'éviter d'engager un chantier sur un portefeuille obsolète.
  Lors de l'introduction d'EB-14 (commit `7160c6f5`), une exception a été ajoutée pour débloquer `c77_build` si `EB14_PROGRESSIVE` est actif et qu'un portefeuille `this._projects` existe sans worker actif (`!(EB14_PROGRESSIVE && intention.kind == "c77_build" && this._projects != null && this._activeWorker == null)`).
  Cependant :
  1. Si `this._projects` est périmé (`stale`), autoriser `c77_build` pendant qu'un scan rail PO01C tourne peut injecter un chantier basé sur des données non réconciliées.
  2. Le contrat de `test_c77_intent_defer.py` exige que même avec un portefeuille non nul, si celui-ci est périmé, le report s'applique.
  À arbitrer par le chef de session : conserver l'exception EB-14 en adaptant le test, ou restaurer le blocage strict sur portefeuille périmé dans `orchestrator.nut`.

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
