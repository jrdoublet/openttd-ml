/* OpexAI -- une IA qui traite les opcodes comme une ressource de jeu.
 *
 * Principe directeur : le budget du VM (10 000 opcodes par tick) n'est pas un stock qu'on
 * economise mais un DEBIT non reportable. La seule decision est donc l'ALLOCATION : a quel
 * candidat va le prochain tick de calcul. D'ou deux metriques :
 *   - externe, l'arbitre : company_value au banc (sweeps/bench.py) ;
 *   - interne, la regle d'allocation : profit par opcode.
 * En cas de desaccord, le banc gagne.
 *
 * Quatre etages :
 *   0  catalog.nut       -- villes, industries, cargos, materiel roulant (rafraichi chaque annee)
 *   1  economy.nut       -- profit annuel attendu d'une ligne
 *   2  candidates.nut    -- cout en iterations d'A* attendu, et le classement par rapport
 *   3  builder_rail.nut  -- construction, sous budget d'iterations calcule par l'arret optimal
 *
 * Instrumentation : AILog.Info n'apparait PAS dans la sortie capturee par OpenTTDLab (verifie le
 * 2026-08-28), et un nom de panneau echoue SILENCIEUSEMENT au-dela de 31 caracteres. D'ou des
 * panneaux courts et nombreux plutot que de longues lignes.
 */

import("pathfinder.rail", "RailPathFinder", 1);

require("budget.nut");
require("catalog.nut");
require("economy.nut");
require("candidates.nut");
require("builder_rail.nut");

/* Distance minimale entre une nouvelle extremite et une gare deja posee par nous. Evite de
 * redesservir la meme ville et de se cannibaliser -- meme motif que la contrainte de villes
 * disjointes de TrainLineAI, mais sur nos propres gares uniquement. */
const MIN_SEPARATION = 15;

/* Fenetre de temps accordee a une tentative, en plus du budget d'iterations. A ~3,7 iterations
 * par tick, N iterations demandent ~N/3,7 ticks ; la marge couvre la pose elle-meme. */
const BUILD_TICK_MARGIN = 3000;

/* Reserve de tresorerie. Sans elle l'IA construit jusqu'a la ruine : mesure du 2026-08-28,
 * 4 lignes construites puis solde a -542 avec l'emprunt au maximum. Une compagnie a sec ne peut
 * plus ni renouveler ses vehicules ni saisir une occasion, et la valeur d'entreprise tombe a 1. */
const CASH_RESERVE = 50000;

class OpexAI extends AIController {
  _budget = null;
  _catalog = null;
  _startTick = 0;
  _lines = null;        // [{stationA, stationB, cargo, predicted, iterations, trains, ...}]

  constructor()
  {
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
  }

  function Start();
  function _tooClose(candidate);
  function _tryBuild(ranked, year);
  function _reportYear(year, ranked);
  function _reportLines(year);
}

/* Une extremite deja desservie par nous ne merite pas un second raccordement. */
function OpexAI::_tooClose(candidate)
{
  foreach (line in this._lines) {
    if (AIMap.DistanceManhattan(candidate.src, line.stationA) < MIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(candidate.src, line.stationB) < MIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(candidate.dst, line.stationA) < MIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(candidate.dst, line.stationB) < MIN_SEPARATION) return true;
  }
  return false;
}

/* Le coeur de l'allocation : on descend le classement tant qu'il reste de l'argent, et chaque
 * tentative recoit un budget d'iterations egal a ce qu'il faut pour continuer a battre le
 * candidat SUIVANT. Le seuil d'abandon n'est donc pas une constante : c'est l'alternative. */
function OpexAI::_tryBuild(ranked, year)
{
  local best = ranked.best;
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < best.len(); i++) {
    local candidate = best[i];
    if (this._tooClose(candidate)) continue;

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < candidate.capital + CASH_RESERVE) break;  // classement decroissant

    local alternativeRatio = (i + 1 < best.len()) ? best[i + 1].ratio : 0;
    local iterationBudget = OpexIterationBudget(candidate.profitAnnual, alternativeRatio);
    local deadline = AIController.GetTick() + iterationBudget / 3 + BUILD_TICK_MARGIN;

    local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio, deadline);

    AISign.BuildSign(anchor, "OR|" + this._lines.len() + "|" + candidate.distance
                             + "|" + result.iterations + "|" + result.reason);
    if (result.error != 0) AISign.BuildSign(anchor, "OV|" + this._lines.len() + "|" + result.error);
    if (result.diag != null) {
      AISign.BuildSign(anchor, "OG|" + result.diag.railtype + "|" + result.diag.isDepot
                               + "|" + result.diag.buildable + "|" + result.diag.canRun);
      AISign.BuildSign(anchor, "OH|" + result.diag.price + "|" + result.diag.cash);
      AISign.BuildSign(anchor, "OI|" + result.diag.engineRail + "|" + result.diag.depotRail
                               + "|" + result.diag.vehType + "|" + result.diag.testOk);
    }

    if (result.ok) {
      this._lines.append({
        stationA = result.stationA, stationB = result.stationB, cargo = candidate.cargo,
        predicted = candidate.profitAnnual, iterations = result.iterations,
        trains = result.trains, distance = candidate.distance, year = year,
      });
    }
  }
}

/* Le releve qui permet de calibrer l'etage 1 : pour chaque ligne, la note de gare REELLE (on
 * suppose STATION_RATING_PCT = 75) et le profit REEL des vehicules (on a predit profitAnnual).
 * C'est exactement la mesure qui manquait a la campagne v3. */
function OpexAI::_reportLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    if (!AIStation.IsValidStation(stationA)) continue;

    local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
    local ratingB = AIStation.IsValidStation(stationB)
        ? AIStation.GetCargoRating(stationB, line.cargo) : -1;
    AISign.BuildSign(anchor, "OY|" + i + "|" + year + "|" + ratingA + "|" + ratingB);

    local profit = 0;
    local vehicles = AIVehicleList_Station(stationA);
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
      profit += AIVehicle.GetProfitLastYear(v);
    }
    AISign.BuildSign(anchor, "OZ|" + i + "|" + year + "|" + profit);
  }
}

function OpexAI::_reportYear(year, ranked)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local best = ranked.best.len() > 0 ? ranked.best[0] : null;

  AISign.BuildSign(anchor, "OX|" + year + "|" + this._catalog.towns.len()
                           + "|" + this._catalog.industries.len() + "|" + ranked.all);
  AISign.BuildSign(anchor, "OC|" + year + "|" + this._budget.get("cat_towns")
                           + "|" + this._budget.get("cat_industries")
                           + "|" + this._budget.get("cat_rail"));
  AISign.BuildSign(anchor, "OP|" + year + "|" + this._budget.get("cand_pax")
                           + "|" + this._budget.get("cand_freight"));
  AISign.BuildSign(anchor, "OS|" + year + "|" + this._budget.get("cand_rank")
                           + "|" + this._budget.utilisationPerMille(this._startTick));

  /* Le poste qui domine tout le reste : la recherche de chemin et la construction. */
  local buildOps = this._budget.get("build_plans") + this._budget.get("build_search")
                 + this._budget.get("build_stations") + this._budget.get("build_track")
                 + this._budget.get("build_trains");
  AISign.BuildSign(anchor, "OW|" + year + "|" + buildOps + "|" + this._lines.len());

  if (best != null) {
    AISign.BuildSign(anchor, "OB|" + year + "|" + best.distance
                             + "|" + best.monthly + "|" + best.ratio);
    AISign.BuildSign(anchor, "OE|" + year + "|" + best.trains
                             + "|" + best.profitAnnual + "|" + best.capital);
  }
  AISign.BuildSign(anchor, "OD|" + year + "|" + ranked.bands[0] + "|" + ranked.bands[1]
                           + "|" + ranked.bands[2] + "|" + ranked.bands[3]);
  if (this._catalog.loco != null) {
    AISign.BuildSign(anchor, "OL|" + year + "|" + this._catalog.loco.speed
                             + "|" + this._catalog.costTrackPerTile
                             + "|" + this._catalog.costStation);
  }
}

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  /* L'emprunt maximal des le depart : la note de compagnie recompense l'emprunt a zero (5 %),
   * mais une ligne non construite faute de tresorerie coute bien davantage. Le remboursement
   * viendra quand la tresorerie le permettra. */
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

  local lastYear = -1;
  while (true) {
    local year = AIDate.GetYear(AIDate.GetCurrentDate());
    if (year != lastYear) {
      lastYear = year;
      this._catalog.refresh(this._budget, year);
      local ranked = OpexBuildCandidates(this._catalog, this._budget);
      this._reportYear(year, ranked);
      this._reportLines(year);
      this._tryBuild(ranked, year);
    }
    AIController.Sleep(74 * 10);
  }
}
