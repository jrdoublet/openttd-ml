class WaterGraphProbeInfo extends AIInfo {
  function GetAuthor() { return "OpenTTD-ML"; }
  function GetName() { return "WaterGraphProbe"; }
  function GetShortName() { return "C675"; }
  function GetDescription() { return "C67.5 water component graph contract and real-map comparison"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-09-23"; }
  function CreateInstance() { return "WaterGraphProbe"; }
  function GetAPIVersion() { return "15"; }
}
RegisterAI(WaterGraphProbeInfo());
