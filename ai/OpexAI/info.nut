class OpexAI extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA qui traite les opcodes comme une ressource de jeu : chaque candidat porte un profit attendu ET un cout en opcodes attendu, et le budget va au meilleur rapport."; }
  function GetVersion()     { return 2; }
  function GetDate()        { return "2026-08-28"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }
}

RegisterAI(OpexAI());
