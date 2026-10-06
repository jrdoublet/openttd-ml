/* Module AIR extrait de builder_air.nut (R11) : demande passagers par ville (V93.1). */
/* V93.1 : memos du mois, meme horloge que C80 (AIR_MEMO_MONTH / AIR_ECONOMICS_MEMO).
 * Les cles v93t| et v93c| ne collisionnent pas avec les cles d'economie. */
function OpexAirDemandTouchMemo()
{
  local nowDate = AIDate.GetCurrentDate();
  if (nowDate == AIR_DEMAND_MEMO_DATE) return;
  AIR_DEMAND_MEMO_DATE = nowDate;
  local month = AIDate.GetYear(nowDate) * 12 + AIDate.GetMonth(nowDate);
  if (AIR_MEMO_MONTH != month) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
    AIR_MEMO_MONTH = month;
  }
}

/* Cargo passagers du catalogue. Repli : premiere classe CC_PASSENGERS, sans identifiant fixe. */
function OpexAirDemandPaxCargo()
{
  if (AIR_DEMAND_PAX_CARGO >= 0) return AIR_DEMAND_PAX_CARGO;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    if (AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) {
      AIR_DEMAND_PAX_CARGO = c;
      return c;
    }
  }
  return -1;
}

function OpexAirDemandTownRecord(town, paxCargo)
{
  local townId = town.id;
  local key = "v93t|" + townId;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AITown.IsValidTown(townId)) return null;
  local pop = ("pop" in town) ? town.pop : AITown.GetPopulation(townId);
  local produced = AITown.GetLastMonthProduction(townId, paxCargo);
  if (pop >= 0 && produced > pop) produced = pop / 8;
  if (produced < 0) produced = 0;
  local transported = AITown.GetLastMonthTransportedPercentage(townId, paxCargo);
  if (transported < 0) transported = 0;
  /* AITile.GetCargoProduction compte des tuiles productrices, pas des passagers :
   * on ne s'en sert que comme proportion (tuiles couvertes par l'aeroport / tuiles
   * productrices de la ville), rayon croissant avec la population. */
  local townRadius = 4 + (sqrt(pop > 0 ? pop : 0) / 8).tointeger();
  if (townRadius > 20) townRadius = 20;
  local producerTiles = AITile.GetCargoProduction(AITown.GetLocation(townId), paxCargo, 1, 1, townRadius);
  if (producerTiles < 0) producerTiles = 0;
  local record = { produced = produced, transported = transported, pop = pop, producerTiles = producerTiles };
  AIR_ECONOMICS_MEMO.rawset(key, record);
  return record;
}

/* Lignes aeriennes Opex qui partent de cette ville (origin = centre-ville) ou de cet
 * aeroport (station = tuile d'aeroport). Le compte est stable tant que la liste ne change
 * pas de longueur : la boucle de paires ne la reparcourt pas. */
function OpexAirDemandOwnLines(town, siteAnchor, lines)
{
  if (lines == null) return 0;
  local nLines = lines.len();
  if (AIR_DEMAND_LINE_MEMO_LEN != nLines) {
    AIR_DEMAND_LINE_MEMO = {};
    AIR_DEMAND_LINE_MEMO_LEN = nLines;
  }
  local townId = ("id" in town) ? town.id : -1;
  local anchorKey = siteAnchor == null ? -1 : siteAnchor;
  local cacheKey = townId + "|" + anchorKey;
  if (cacheKey in AIR_DEMAND_LINE_MEMO) return AIR_DEMAND_LINE_MEMO[cacheKey];
  local townTile = ("tile" in town) ? town.tile : -1;
  local n = 0;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air") continue;
    local hit = false;
    if (townTile >= 0) {
      if (("originA" in line) && line.originA == townTile) hit = true;
      else if (("originB" in line) && line.originB == townTile) hit = true;
    }
    if (!hit && siteAnchor != null) {
      if (("stationA" in line) && line.stationA == siteAnchor) hit = true;
      else if (("stationB" in line) && line.stationB == siteAnchor) hit = true;
    }
    if (hit) n++;
  }
  AIR_DEMAND_LINE_MEMO.rawset(cacheKey, n);
  return n;
}

/* Type reel si l'ancre est deja un aeroport, sinon le type que l'on s'apprete a poser.
 * -1 dans le memo : ancre encore libre, le type vient de l'argument. */
function OpexAirDemandAirportType(siteAnchor, airport)
{
  if (airport == null || !("type" in airport)) return -1;
  if (siteAnchor == null) return airport.type;
  local key = "v93a|" + siteAnchor;
  if (key in AIR_ECONOMICS_MEMO) {
    local cached = AIR_ECONOMICS_MEMO[key];
    if (cached >= 0) return cached;
    return airport.type;
  }
  local resolved = -1;
  if (AIAirport.IsAirportTile(siteAnchor)) {
    local existing = AIAirport.GetAirportType(siteAnchor);
    if (AIAirport.IsValidAirportType(existing)) resolved = existing;
  }
  AIR_ECONOMICS_MEMO.rawset(key, resolved);
  if (resolved >= 0) return resolved;
  return airport.type;
}

/* -1 si l'ancre est inconnue : pas de borne. Sinon le nombre de tuiles productrices
 * du bassin (GetCargoProduction compte des producteurs), en cache par ancre et par
 * type pour le mois. */
function OpexAirDemandCatchment(siteAnchor, airportType, paxCargo)
{
  if (siteAnchor == null || airportType < 0) return -1;
  local key = "v93c|" + siteAnchor + "|" + airportType + "|" + paxCargo;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AIMap.IsValidTile(siteAnchor) || !AIAirport.IsValidAirportType(airportType)) return -1;
  local sum = OpexAirAirportCatchmentProduction(siteAnchor, airportType, paxCargo);
  if (sum < 0) sum = 0;
  AIR_ECONOMICS_MEMO.rawset(key, sum);
  return sum;
}

/* Passagers mensuels d'une extremite. Appele pour les deux bouts quand
 * V93_AIR_DEMAND_PRODUCTION est arme. Sans ligne Opex au depart, la part deja
 * transporte est celle des autres : production * 70 / (pourcentage + 70).
 * Avec des lignes, ce pourcentage melange nos avions : on partage seulement
 * la production par (lignes + 1). Le / (lignes + 1) est toujours applique
 * (il vaut 1 tant qu'aucune ligne ne part). Puis part des tuiles productrices captees, puis
 * plafond de ligne (200, ou 100 sous 700 habitants). */
function OpexAirTownMonthlyPax(town, siteAnchor, airport, lines)
{
  if (town == null || !("id" in town)) return 0;
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) return 0;
  OpexAirDemandTouchMemo();
  local record = OpexAirDemandTownRecord(town, paxCargo);
  if (record == null) return 0;
  local ownLines = OpexAirDemandOwnLines(town, siteAnchor, lines);
  local pax = record.produced;
  if (ownLines == 0) {
    pax = (record.produced * V93_AIR_COMPETITOR_WEIGHT) / (record.transported + V93_AIR_COMPETITOR_WEIGHT);
  }
  pax = pax / (ownLines + 1);
  /* Part de la ville reellement captee par l'emprise : proportion de ses tuiles
   * productrices dans le rayon de l'aeroport (unite commune, tuiles). */
  local catchment = OpexAirDemandCatchment(siteAnchor, OpexAirDemandAirportType(siteAnchor, airport), paxCargo);
  if (catchment >= 0 && record.producerTiles > 0 && catchment < record.producerTiles) {
    pax = (pax * catchment) / record.producerTiles;
  }
  local cap = V93_AIR_LINE_PAX_CAP;
  if (record.pop >= 0 && record.pop < V93_AIR_LINE_PAX_SMALL_POP) cap = V93_AIR_LINE_PAX_CAP / 2;
  if (pax > cap) pax = cap;
  if (pax < 0) pax = 0;
  return pax;
}
