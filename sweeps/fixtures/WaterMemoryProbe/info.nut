class WaterMemoryProbeInfo extends AIInfo {
  function GetAuthor()      { return "OpenTTD-ML review harness"; }
  function GetName()        { return "WaterMemoryProbe"; }
  function GetShortName()   { return "WMPB"; }
  function GetDescription() { return "Measurement-only AIList-per-map-tile memory probe"; }
  function GetVersion()     { return 2; }
  function GetDate()        { return "2026-09-17"; }
  function CreateInstance() { return "WaterMemoryProbe"; }
  function GetAPIVersion()  { return "15"; }

  function GetSettings() {
    AddSetting({
      name = "allocate",
      description = "Allocate and retain the Lakes-equivalent AIList with one item per map tile",
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
  }
}

RegisterAI(WaterMemoryProbeInfo());
