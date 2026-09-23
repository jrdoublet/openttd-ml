class TerrainBenchProbeInfo extends AIInfo {
  function GetAuthor() { return "OpenTTD-ML"; }
  function GetName() { return "TerrainBenchProbe"; }
  function GetShortName() { return "C67B"; }
  function GetDescription() { return "C67.3 terrain size measurement"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-09-22"; }
  function CreateInstance() { return "TerrainBenchProbe"; }
  function GetAPIVersion() { return "15"; }
  function GetSettings() {
    AddSetting({name = "allocate", description = "0 control, 5 or 10 tile blocks",
      min_value = 0, max_value = 10, easy_value = 0, medium_value = 0,
      hard_value = 0, custom_value = 0, flags = 0});
    AddSetting({name = "full", description = "Stream entire map after localized phases",
      min_value = 0, max_value = 1, easy_value = 0, medium_value = 0,
      hard_value = 0, custom_value = 0, flags = 0});
    AddSetting({name = "scan_blocks", description = "0 full scan, otherwise bounded block count",
      min_value = 0, max_value = 200000, easy_value = 0, medium_value = 0,
      hard_value = 0, custom_value = 0, flags = 0});
  }
}
RegisterAI(TerrainBenchProbeInfo());
