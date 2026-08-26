class TrainLineAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "TrainLineAI"; }
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
      name = "engine_rank",
      description = "Rank of the engine in the speed-sorted engine list (0 = fastest)",
      /* Borne 6 et non 7 : mesuree sur les 50 graines de la campagne
       * phase2_hurdle_dataset_v1 (2026-08-26). Le rang 7 sort de la plage reelle sur 6 graines
       * (moins de 8 moteurs constructibles a cette date/carte) et produit alors ENGOOR, un echec
       * de configuration qui pollue la classe negative du classifieur. Aucun ENGOOR observe au
       * rang <= 6 sur ces 50 graines. */
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
  }
}
RegisterAI(TrainLineAIInfo());
