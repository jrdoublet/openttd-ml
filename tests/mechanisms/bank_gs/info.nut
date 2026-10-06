class FixtureBankInfo extends GSInfo {
  function GetAuthor() { return "OpexAI tests"; }
  function GetName() { return "FixtureBank"; }
  function GetDescription() { return "Test-only real bank-balance setup. Never an economic game."; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-10-01"; }
  function CreateInstance() { return "FixtureBank"; }
  function GetShortName() { return "FXBK"; }
  function GetAPIVersion() { return "15"; }
}
RegisterGS(FixtureBankInfo());