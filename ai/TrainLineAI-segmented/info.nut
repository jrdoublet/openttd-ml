class TrainLineAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
function GetName()        { return "TrainLineAISegmented20260828"; }
  function GetDescription() { return "Builds a single train line between two towns, chosen by population rank, in year 1, then idles."; }
  function GetVersion()     { return 1; }
  function GetDate()        { return "2026-08-25"; }
  function CreateInstance() { return "TrainLineAI"; }
  function GetShortName()   { return "TRLN"; }
  function GetAPIVersion()  { return "13"; }

  function GetSettings() {
    AddSetting({
      name = "num_trains",
      description = "Number of trains to run on the line",
      min_value = 1, max_value = 10,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = 0
    });
    AddSetting({
      name = "wagons_per_train",
      description = "Number of wagons per train (excluding the engine)",
      min_value = 1, max_value = 10,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2,
      flags = 0
    });
    AddSetting({
      name = "town_a_rank",
      description = "Rank of town A in the population-sorted town list (0 = largest)",
      min_value = 0, max_value = 15,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
    AddSetting({
      name = "town_b_rank",
      description = "Rank of town B in the population-sorted town list (0 = largest)",
      min_value = 0, max_value = 15,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = 0
    });
    AddSetting({
      name = "pair_rank",
      description = "Rank of the town pair in the score-sorted (population_a*population_b/distance) list, 0 = best",
      min_value = 0, max_value = 500,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
    AddSetting({
      /* Borne 6 et non 7 : mesuree sur les 50 graines de la campagne
       * phase2_hurdle_dataset_v1 (2026-08-26). Le rang 7 sort de la plage reelle sur 6 graines
       * (moins de 8 moteurs constructibles a cette date/carte) et produit alors ENGOOR, un echec
       * de configuration qui pollue la classe negative du classifieur. Aucun ENGOOR observe au
       * rang <= 6 sur ces 50 graines.
       */
      name = "engine_rank",
      description = "Rank of the engine in the speed-sorted engine list (0 = fastest)",
      min_value = 0, max_value = 6,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
    AddSetting({
      name = "line_index",
      description = "Identifier of this line/attempt, echoed in the status sign (does not schedule it)",
      min_value = 0, max_value = 99,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
    AddSetting({
      name = "stagger_slot",
      description = "Multi-company construction order slot; 0 disables stagger in isolated games",
      min_value = 0, max_value = 99,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
    AddSetting({
      /* COUPLE A barrier_base_k : ne jamais relever l'un sans l'autre. Mesure du
       * 2026-08-27 : une iteration d'A* coute ~2700 opcodes pour un budget VM de ~10000 par tick,
       * soit 3,7 iterations par tick. Les 30000 iterations par defaut consomment donc 7337 a 10519
       * ticks, contre une barriere a 11000 -- on est a ~96 % de saturation. Relever ce budget seul
       * ferait basculer barrier_flag a O et casserait en silence la comparabilite temporelle.
       */
      name = "pathfinder_iterations_k",
      description = "A* search-iteration budget, in thousands (30 = historical 30000)",
      min_value = 1, max_value = 300,
      easy_value = 30, medium_value = 30, hard_value = 30,
      custom_value = 30,
      flags = 0
    });
    AddSetting({
      /* COUPLE A pathfinder_iterations_k -- voir sa note. Ordre de grandeur mesure :
       * les 9 pires cas PATHLIM demandent 41200 a 89350 iterations et jusqu'a 27858 ticks de
       * pathfinding, donc un budget de 90 exigerait une barriere vers 33.
       */
      name = "barrier_base_k",
      description = "Base construction-barrier tick, in thousands (11 = historical 11000)",
      min_value = 1, max_value = 60,
      easy_value = 11, medium_value = 11, hard_value = 11,
      custom_value = 11,
      flags = 0
    });
  }
}
RegisterAI(TrainLineAIInfo());
