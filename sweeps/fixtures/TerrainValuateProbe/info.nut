class TerrainValuateProbeInfo extends AIInfo {
  function GetAuthor() { return "OpenTTD-ML"; }
  function GetName() { return "TerrainValuateProbe"; }
  function GetShortName() { return "C67V"; }
  function GetDescription() { return "C67 Valuate terrain reader benchmark"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-10-11"; }
  function CreateInstance() { return "TerrainValuateProbe"; }
  function GetAPIVersion() { return "15"; }
  function GetSettings() {
    AddSetting({name = "blocks", description = "Number of sample blocks (default 64)",
      min_value = 1, max_value = 256, easy_value = 64, medium_value = 64,
      hard_value = 64, custom_value = 64, flags = 0});
  }
}
RegisterAI(TerrainValuateProbeInfo());
