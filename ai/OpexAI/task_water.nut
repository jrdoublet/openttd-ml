/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Les docks sont des sites figes, contrairement au trace routier qui est recalcule juste avant
 * OpexBuildRoadRoute. La connexion eau elle-meme n'est pas re-scannee : aucun premier chantier
 * non maritime ne peut modifier ses aretes, et un premier chantier maritime met _waterBuilt a 1.
 * Ce probe couvre donc le seul etat que le batch peut invalider sans payer un BFS inutile. */
function OpexWaterBatchSiteStillBuildable(site)
{
  local ok = false;
  { local probe = AITestMode(); ok = AIMarine.BuildDock(site.dock, AIStation.STATION_NEW); }
  return ok;
}
/* C38 etape 2 : tentative synchrone eau, au meme contrat que le rail. */
function OpexAI::_tryBuildWaterProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = project.src, dst = project.dst, reason = "water_unavailable", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local plan = project.payload;
      if (builtCount > 0 && (!OpexWaterBatchSiteStillBuildable(plan.siteA) ||
                             !OpexWaterBatchSiteStillBuildable(plan.siteB))) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "batch_site_unbuildable", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local capital = 2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice;
      local need = capital + OpexCashReserve() + WATER_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("water", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.id, plan.siteB.town.id, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|W|" + project.budgetScore + "|" + project.opcodeScore);
      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      local result = OpexBuildWaterRoute(this._catalog, this._budget, plan);
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("water", result, capital);
      if (result.ok) OpexSign(anchor, "OM|W|" + year + "|" + plan.distance + "|" + planOps);
      else OpexSign(anchor, "ON|W|" + result.reason + "|" + result.error);
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "build_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=water src=" + plan.siteA.town.id + " dst=" + plan.siteB.town.id + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        return { outcome = "rejected", discards = passDiscards };
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=water cargo=" + cargoStr + " src=" + result.dockA + " dst=" + result.dockB + " dist=" + plan.distance + " cost=" + capital + " roi=" + project.roi);
          OpexDecide("WATER_BUILD", "line=" + this._nextLineId + " src=" + result.dockA + " dst=" + result.dockB + " cargo=" + cargoStr + " dist=" + plan.distance + " cost=" + capital);
        }
        this._waterBuilt = true;
        this._lines.append({
          stationA = result.dockA, stationB = result.dockB,
          originA = result.dockA, originB = result.dockB,
          cargo = this._catalog.paxCargo,
          predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
          mode = "water", vehicle = result.vehicle, vehicles = [result.vehicle],
          depot = result.depot, refleetEngine = AIVehicle.GetEngineType(result.vehicle), vehCount = 1,
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        OpexSign(anchor, "PM|" + this._nextLineId + "|W|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        this._nextLineId++;
        return { outcome = "built", discards = passDiscards };
      }
  return { outcome = "rejected", discards = passDiscards };
}
/* L'eau a une flotte unitaire et un depot propre : le meme contrat durable que
 * l'air suffit pour reconstruire un navire perdu. Le rail reste volontairement
 * hors de ce chemin : reconstituer un consist entier exige davantage que le
 * moteur de la locomotive (wagons, ordres partages et infrastructure), donc il
 * ne doit pas etre presente comme automatiquement repare. */
function OpexAI::_refleetCrashedWaterLines(year)
{
  foreach (line in this._lines) {
    if (!("mode" in line) || line.mode != "water" ||
        !(("needsRefleet" in line) && line.needsRefleet)) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    local recovered = OpexWaterRefleetCrashedShip(line);
    if (recovered.added > 0) {
      if ("vehCount" in line) line.vehCount = 1;
      else line.vehCount <- 1;
      if ("trains" in line) line.trains = 1;
      else line.trains <- 1;
      line.needsRefleet = false;
      if (DECISION_LOG || C52_CRASH_LOG) {
        OpexDecide("CRASH_REFLEET", "mode=water line=" + line.lineId + " vehicle=" + line.vehicle);
      }
    } else if (DECISION_LOG || C52_CRASH_LOG) {
      OpexDecide("CRASH_REFLEET", "mode=water line=" + line.lineId + " reason=" + recovered.reason);
    }
  }
}
