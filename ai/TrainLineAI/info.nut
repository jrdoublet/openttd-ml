class TrainLineAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "TrainLineAI"; }
  function GetDescription() { return "Builds a single train line between the two largest towns in year 1, then idles."; }
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
  }
}
RegisterAI(TrainLineAIInfo());
