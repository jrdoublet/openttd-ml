class IndustryCensusProbeInfo extends AIInfo {
  function GetAuthor() { return "OpenTTD-ML"; }
  function GetName() { return "IndustryCensusProbe"; }
  function GetShortName() { return "V290"; }
  function GetDescription() { return "V290: Industry and water connectivity census probe"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-10-20"; }
  function CreateInstance() { return "IndustryCensusProbe"; }
  function GetAPIVersion() { return "15"; }
}
RegisterAI(IndustryCensusProbeInfo());
