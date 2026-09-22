class TerrainMapProbeInfo extends AIInfo {
  function GetAuthor() { return "OpenTTD-ML"; }
  function GetName() { return "TerrainMapProbe"; }
  function GetShortName() { return "C67P"; }
  function GetDescription() { return "C67.2 isolated terrain contract tests"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-09-22"; }
  function CreateInstance() { return "TerrainMapProbe"; }
  function GetAPIVersion() { return "15"; }
}
RegisterAI(TerrainMapProbeInfo());
