class CatalogProbe extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "CatalogProbe"; }
  function GetDescription() { return "Mesure la churn du catalogue et le cout en opcodes d'un rafraichissement."; }
  function GetVersion()     { return 1; }
  function GetDate()        { return "2026-08-28"; }
  function CreateInstance() { return "CatalogProbe"; }
  function GetShortName()   { return "CATP"; }
  function GetAPIVersion()  { return "15"; }
}
RegisterAI(CatalogProbe());
