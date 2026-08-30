/* CatalogProbe -- combien coute un rafraichissement de catalogue, et qu'est-ce qui change ?
 *
 * Cette IA ne joue pas : elle mesure. Chaque annee de jeu elle refait les enumerations qu'une
 * vraie IA devrait refaire, et compte les opcodes que chacune consomme. C'est la moitie
 * manquante de la question "faut-il rafraichir le catalogue tous les ans ?" : la churn dit ce
 * qu'on gagne a rafraichir, ce compteur dit ce qu'on paie.
 *
 * Comptabilite des opcodes : GetOpsTillSuspend() donne le RESTE du budget du tick courant, qui
 * se recharge a chaque tick. Un bloc de travail qui traverse des ticks doit donc etre compte
 * comme "ce qui restait au depart + les ticks pleins traverses + ce qui a ete consomme dans le
 * tick d'arrivee". C'est exactement la comptabilite dont la vraie IA aura besoin.
 *
 * Sortie par panneaux : AILog.Info n'apparait PAS dans la sortie capturee par OpenTTDLab (il
 * faudrait -d script=N, que le harnais ne passe pas). Seules les erreurs de script y arrivent.
 * Les panneaux sont donc le seul canal, comme dans le reste du projet -- et ils sont poses
 * APRES chaque mesure, jamais pendant, pour ne pas la fausser. Un nom de panneau est court :
 * plusieurs panneaux par annee plutot qu'une longue ligne.
 */

// Confirme dans le binaire 15.3 : script_max_opcode_till_suspend = 10000.
const OPS_PER_TICK = 10000;

class CatalogProbe extends AIController {
  function Start();
}

/* Debut d'une mesure : [tick, budget restant]. */
function _opsBegin()
{
  local tick = AIController.GetTick();
  local left = AIController.GetOpsTillSuspend();
  return [tick, left];
}

/* Fin d'une mesure : opcodes consommes depuis _opsBegin(). */
function _opsEnd(begin)
{
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - begin[0];
  if (elapsed <= 0) return begin[1] - left;
  return begin[1] + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
}

/* Enumeration des villes avec les grandeurs qu'un etage 1 lirait vraiment. */
function _scanTowns(out)
{
  local list = AITownList();
  local ids = [];
  local pops = [];
  for (local t = list.Begin(); !list.IsEnd(); t = list.Next()) {
    ids.append(t);
    pops.append(AITown.GetPopulation(t));
  }
  /* Squirrel : '<-' cree la fente, '=' exige qu'elle existe deja. */
  out.town_ids <- ids;
  out.town_pops <- pops;
  return ids.len();
}

/* Enumeration des industries : localisation et type, ce que lit un etage 1. */
function _scanIndustries(out)
{
  local list = AIIndustryList();
  local ids = [];
  for (local i = list.Begin(); !list.IsEnd(); i = list.Next()) {
    ids.append(AIIndustry.GetLocation(i));
  }
  out.industry_count <- ids.len();
  return ids.len();
}

/* Le vrai cout de l'etage 1 : toutes les paires ordonnees, avec un score. */
function _scorePairs(ids, pops)
{
  local n = ids.len();
  local best = 0;
  for (local a = 0; a < n; a++) {
    local la = AITown.GetLocation(ids[a]);
    local pa = pops[a];
    for (local b = a + 1; b < n; b++) {
      local d = AIMap.DistanceManhattan(la, AITown.GetLocation(ids[b]));
      if (d < 10) continue;
      local score = pa * pops[b] / d;
      if (score > best) best = score;
    }
  }
  return best;
}

/* Moteurs constructibles par mode. */
function _countBuildable(vehicleType)
{
  local list = AIEngineList(vehicleType);
  local n = 0;
  for (local e = list.Begin(); !list.IsEnd(); e = list.Next()) {
    if (AIEngine.IsBuildable(e)) n++;
  }
  return n;
}

/* Locos (pas wagons) avec puissance sur chaque type de rail disponible.
 * API 15.3 : pas de RAILTYPE_RAIL, seulement AIRailTypeList().
 * "CE|2000|4|12|8|4|2" = 18 caracteres. nTypes puis jusqu'a 4 comptes, 0 si absent. */
function _railTypeCounts()
{
  local counts = [0, 0, 0, 0];
  local nTypes = 0;
  local types = AIRailTypeList();
  for (local rt = types.Begin(); !types.IsEnd(); rt = types.Next()) {
    if (!AIRail.IsRailTypeAvailable(rt)) continue;
    local n = 0;
    local engines = AIEngineList(AIVehicle.VT_RAIL);
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
      if (!AIEngine.IsBuildable(e) || AIEngine.IsWagon(e)) continue;
      if (AIEngine.HasPowerOnRail(e, rt)) n++;
    }
    if (nTypes < 4) counts[nTypes] = n;
    nTypes++;
  }
  return { nTypes = nTypes, n0 = counts[0], n1 = counts[1], n2 = counts[2], n3 = counts[3] };
}

function CatalogProbe::Start()
{
  AICompany.SetName("CatalogProbe");

  local airportTypes = [
    ["SMALL", AIAirport.AT_SMALL], ["LARGE", AIAirport.AT_LARGE],
    ["METROPOLITAN", AIAirport.AT_METROPOLITAN], ["INTERNATIONAL", AIAirport.AT_INTERNATIONAL],
    ["COMMUTER", AIAirport.AT_COMMUTER], ["INTERCON", AIAirport.AT_INTERCON],
    ["HELIPORT", AIAirport.AT_HELIPORT], ["HELISTATION", AIAirport.AT_HELISTATION],
    ["HELIDEPOT", AIAirport.AT_HELIDEPOT],
  ];

  local lastYear = -1;
  while (true) {
    local year = AIDate.GetYear(AIDate.GetCurrentDate());
    if (year != lastYear) {
      lastYear = year;
      local out = {};

      local b = _opsBegin();
      local nTowns = _scanTowns(out);
      local opsTowns = _opsEnd(b);

      b = _opsBegin();
      local nIndustries = _scanIndustries(out);
      local opsIndustries = _opsEnd(b);

      b = _opsBegin();
      _scorePairs(out.town_ids, out.town_pops);
      local opsPairs = _opsEnd(b);

      b = _opsBegin();
      local nRail = _countBuildable(AIVehicle.VT_RAIL);
      local nRoad = _countBuildable(AIVehicle.VT_ROAD);
      local nWater = _countBuildable(AIVehicle.VT_WATER);
      local nAir = _countBuildable(AIVehicle.VT_AIR);
      local railTypes = _railTypeCounts();
      local opsEngines = _opsEnd(b);

      b = _opsBegin();
      local airportMask = 0;
      for (local i = 0; i < airportTypes.len(); i++) {
        if (AIAirport.IsValidAirportType(airportTypes[i][1])) airportMask = airportMask | (1 << i);
      }
      local opsAirports = _opsEnd(b);

      local anchor = AIMap.GetTileIndex(1, 1);
      AISign.BuildSign(anchor, "CA|" + year + "|" + nTowns + "|" + nIndustries);
      AISign.BuildSign(anchor, "CB|" + year + "|" + nRail + "|" + nRoad + "|" + nWater
                               + "|" + nAir + "|" + airportMask);
      AISign.BuildSign(anchor, "CO|" + year + "|" + opsTowns + "|" + opsIndustries);
      AISign.BuildSign(anchor, "CP|" + year + "|" + opsPairs + "|" + opsEngines
                               + "|" + opsAirports);
      AISign.BuildSign(anchor, "CE|" + year + "|" + railTypes.nTypes + "|"
                               + railTypes.n0 + "|" + railTypes.n1 + "|"
                               + railTypes.n2 + "|" + railTypes.n3);
    }
    AIController.Sleep(74 * 10);
  }
}
