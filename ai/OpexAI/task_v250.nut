/* V250 : droits de transport exclusifs (AITown.TOWN_ACTION_BUY_RIGHTS).
 * 0 : la tache retourne avant toute API.
 * 1 : ville la plus disputee (gares a nous et gares rivales dans la meme
 *     desserte), seulement si OPEX_DIFFICULTY vaut 2 ou 3 et si l'on est
 *     riche au sens V249. Facile et moyen restent coupes.
 * 2 : test. Villes ou le regime sans bruit (meme porte que C83) a
 *     GetAllowedNoise == 0 et ou nous n'avons aucun aeroport. On rachete a
 *     chaque expiration tant que la caisse couvre cout + reserve. Plafond N =
 *     (caisse - reserve) / cout : un achat pose exclusive_counter = 12 mois
 *     economiques, donc un achat couvre un an. Pas de plafond arbitraire.
 * L'echeance est relue via IsActionAvailable (exclusive_counter != 0 refuse
 * l'achat, town_cmd.cpp). GetExclusiveRightsCompany / Duration existent en
 * API 15 mais le mode compagnie de la premiere rend une date sauvee inutile.
 * 3 : test elargi. Les ordres d'AAA sont invisibles (AIVehicleList filtre sur
 *     le proprietaire, script_vehiclelist.cpp) : on ne sait pas quelles villes
 *     sont reliees a une ville saturee. On prend donc toutes les villes ou un
 *     rival a un aeroport (2 - bruit - les notres > 0), saturees d'abord, pour
 *     que les deux extremites des routes d'AAA ne chargent plus rien.
 * Un creneau libere (bruit >= 1, y compris un saut 0 -> 2) est seulement
 * journalise : C83 reagit deja a GetAllowedNoise == 1. Seules les villes
 * saturees a l'achat (marque 1) sont suivies ; marque 2 = ville non saturee. */

/* Cout que PerformTownAction paierait. AITestMode n'achete rien.
 * AIAccounting imbriquee isole le cout simule du compteur de la compagnie. */
function OpexV250MeasureRightsCost(townId)
{
  local account = AIAccounting();
  {
    local test = AITestMode();
    AITown.PerformTownAction(townId, AITown.TOWN_ACTION_BUY_RIGHTS);
  }
  return account.GetCosts();
}

/* 1 achete, 0 indisponible ou refus, -1 caisse insuffisante (arreter la passe). */
function OpexV250BuyRights(ai, townId, mode, pop, reserve, mark = 1)
{
  if (!AITown.IsValidTown(townId)) return 0;
  if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUY_RIGHTS)) return 0;
  local cost = OpexV250MeasureRightsCost(townId);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = reserve;
  if (mode == 1) need += OpexV249MaxListedCapital(ai._projects);
  if (cost <= 0 || cash - cost < need) return -1;
  local bought = AITown.PerformTownAction(townId, AITown.TOWN_ACTION_BUY_RIGHTS);
  if (!bought) return 0;
  if (mode >= 2 && ai._v250Targets != null && !(townId in ai._v250Targets)) ai._v250Targets.rawset(townId, mark);
  local noise = AITown.GetAllowedNoise(townId);
  if (DECISION_LOG) OpexDecide("V250_RIGHTS", "town=" + townId + " cost=" + cost + " mode=" + mode + " pop=" + pop + " noise=" + noise);
  return 1;
}

/* Un achat = un an de droits. N est le nombre de villes que la caisse
 * au-dessus de la reserve peut tenir une annee, pas un constant de carte. */
function OpexV250YearSlots(cash, reserve, cost)
{
  if (cost <= 0) return 0;
  local spendable = cash - reserve;
  if (spendable < cost) return 0;
  return (spendable / cost).tointeger();
}

/* Population decroissante, puis identifiant croissant. */
function OpexV250InsertByPop(ordered, townId, pop)
{
  local pos = ordered.len();
  while (pos > 0) {
    local cur = ordered[pos - 1];
    if (cur.pop > pop) break;
    if (cur.pop == pop && cur.id < townId) break;
    pos--;
  }
  ordered.insert(pos, { id = townId, pop = pop });
}

function OpexV250SampleTown(ordered)
{
  foreach (item in ordered) {
    if (AITown.IsActionAvailable(item.id, AITown.TOWN_ACTION_BUY_RIGHTS)) return item.id;
  }
  return -1;
}

function OpexV250TargetCount(ai)
{
  local n = 0;
  if (ai == null || ai._v250Targets == null) return 0;
  foreach (townId, mark in ai._v250Targets) n++;
  return n;
}

function OpexV250WatchTown(ai, townId, date, ownCounts)
{
  if (!AITown.IsValidTown(townId)) return;
  local noise = AITown.GetAllowedNoise(townId);
  local own = 0;
  if (ownCounts != null && (townId in ownCounts)) own = ownCounts[townId];
  if (DECISION_LOG) OpexDecide("V250_WATCH", "town=" + townId + " noise=" + noise + " own=" + own);
  if (noise >= 1 && (ai._v250Freed == null || !(townId in ai._v250Freed))) {
    if (ai._v250Freed == null) ai._v250Freed = {};
    ai._v250Freed.rawset(townId, 1);
    if (DECISION_LOG) OpexDecide("V250_SLOT_FREED", "town=" + townId + " date=" + date);
  }
}

function OpexV250Watch(ai, date, ownCounts)
{
  if (ai._v250Targets == null) return;
  foreach (townId, mark in ai._v250Targets) {
    if (mark == 1) OpexV250WatchTown(ai, townId, date, ownCounts);
  }
}

/* Une passe : nos gares, puis les tuiles de desserte. Une gare rivale compte
 * une fois par ville, des qu'elle dessert les memes habitants qu'une gare a nous. */
function OpexV250Contested()
{
  local byTown = {};
  local selfId = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local stations = AIStationList(AIStation.STATION_ANY);
  for (local st = stations.Begin(); !stations.IsEnd(); st = stations.Next()) {
    local townId = AIStation.GetNearestTown(st);
    if (!AITown.IsValidTown(townId)) continue;
    if (!(townId in byTown)) {
      byTown[townId] <- { own = 0, rivals = 0, pop = AITown.GetPopulation(townId), seen = {} };
    }
    byTown[townId].own++;
    local tiles = AITileList_StationCoverage(st);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) {
      if (!AITile.IsStationTile(tile)) continue;
      local owner = AITile.GetOwner(tile);
      if (owner == selfId || AICompany.ResolveCompanyID(owner) == AICompany.COMPANY_INVALID) continue;
      /* IsValidStation est faux pour une gare rivale : ne pas le tester. */
      local rival = AIStation.GetStationID(tile);
      if (rival == st || rival < 0) continue;
      if (rival in byTown[townId].seen) continue;
      byTown[townId].seen[rival] <- 1;
      byTown[townId].rivals++;
    }
  }
  return byTown;
}

function OpexV250RunNormal(ai)
{
  local cashStop = V250_CASH_STOP;
  ::V250_CASH_STOP = false;
  if (AICompany.GetLoanAmount() > 0 || cashStop) return true;
  local byTown = OpexV250Contested();
  local bestTown = -1;
  local bestRivals = -1;
  local bestPop = -1;
  local found = false;
  foreach (townId, info in byTown) {
    if (info.rivals <= 0) continue;
    if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUY_RIGHTS)) continue;
    if (!found || info.rivals > bestRivals
        || (info.rivals == bestRivals && info.pop > bestPop)
        || (info.rivals == bestRivals && info.pop == bestPop && townId < bestTown)) {
      found = true;
      bestTown = townId;
      bestRivals = info.rivals;
      bestPop = info.pop;
    }
  }
  if (!found) return true;
  local reserve = OpexCashReserve();
  OpexV250BuyRights(ai, bestTown, 1, bestPop, reserve);
  return true;
}

function OpexV250RunTest(ai, date, allRival = false)
{
  local ownCounts = OpexAirOwnSlotTownCounts();
  OpexV250Watch(ai, date, ownCounts);
  if (!OpexAirC83SlotSignalEnabled()) return true;

  local ordered = [];
  local others = [];
  local towns = AITownList();
  for (local townId = towns.Begin(); !towns.IsEnd(); townId = towns.Next()) {
    local noise = AITown.GetAllowedNoise(townId);
    local own = (townId in ownCounts) ? ownCounts[townId] : 0;
    if (!allRival) {
      if (AITown.GetAllowedNoise(townId) != 0) continue;
      if (own != 0) continue;
      OpexV250InsertByPop(ordered, townId, AITown.GetPopulation(townId));
      continue;
    }
    /* Mode 3 : aeroports rivaux = creneaux pris moins les notres. */
    local rival = 2 - noise - own;
    if (rival <= 0) continue;
    if (noise == 0 && own == 0) OpexV250InsertByPop(ordered, townId, AITown.GetPopulation(townId));
    else OpexV250InsertByPop(others, townId, AITown.GetPopulation(townId));
  }
  foreach (item in others) ordered.append(item);

  local renew = [];
  if (ai._v250Targets != null) {
    foreach (townId, mark in ai._v250Targets) {
      if (!AITown.IsValidTown(townId)) continue;
      if (ai._v250Freed != null && (townId in ai._v250Freed)) continue;
      OpexV250InsertByPop(renew, townId, AITown.GetPopulation(townId));
    }
  }

  local sample = OpexV250SampleTown(ordered);
  if (sample < 0) sample = OpexV250SampleTown(renew);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local reserve = OpexCashReserve();
  local cost = sample >= 0 ? OpexV250MeasureRightsCost(sample) : 0;
  local slots = OpexV250YearSlots(cash, reserve, cost);

  local kept = 0;
  foreach (item in renew) {
    if (kept >= slots) break;
    kept++;
    if (!AITown.IsActionAvailable(item.id, AITown.TOWN_ACTION_BUY_RIGHTS)) continue;
    if (OpexV250BuyRights(ai, item.id, allRival ? 3 : 2, item.pop, reserve) < 0) break;
  }
  foreach (item in ordered) {
    if (OpexV250TargetCount(ai) >= slots) break;
    if (ai._v250Targets != null && (item.id in ai._v250Targets)) continue;
    local saturated = AITown.GetAllowedNoise(item.id) == 0
        && !(item.id in ownCounts && ownCounts[item.id] > 0);
    local bought = OpexV250BuyRights(ai, item.id, allRival ? 3 : 2, item.pop, reserve, saturated ? 1 : 2);
    if (bought < 0) break;
    if (bought > 0 && saturated) OpexV250WatchTown(ai, item.id, date, ownCounts);
  }
  return true;
}

function OpexAI::_dispatchV250Rights(task, year)
{
  if (V250_RIGHTS == 0) return false;
  if (V250_RIGHTS == 1 && OPEX_DIFFICULTY < 2) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v250Month == ym) return false;
  this._v250Month = ym;
  if (this._v250Targets == null) this._v250Targets = {};
  if (this._v250Freed == null) this._v250Freed = {};
  if (V250_RIGHTS >= 2) return OpexV250RunTest(this, date, V250_RIGHTS == 3);
  return OpexV250RunNormal(this);
}
