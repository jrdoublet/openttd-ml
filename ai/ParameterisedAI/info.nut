class ParameterisedAIInfo extends AIInfo {
  function GetAuthor()      { return "Michal Charemza"; }
  function GetName()        { return "ParameterisedAI"; }
  function GetDescription() { return "An AI to investigate supply chains"; }
  function GetVersion()     { return 1; }
  function GetDate()        { return "2024-02-11"; }
  function CreateInstance() { return "ParameterisedAI"; }
  function GetShortName()   { return "SCLB"; }
  function GetAPIVersion()  { return "13"; }

  function GetSettings() {
    AddSetting({
      name = "maximum_buses",
      description = "Maximum number of buses",
      min_value = 0, max_value = 2147483647,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = 0
    });
  }
}
RegisterAI(ParameterisedAIInfo());
