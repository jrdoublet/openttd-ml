/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Les docks sont des sites figes, contrairement au trace routier qui est recalcule juste avant
 * OpexBuildRoadRoute. La connexion eau elle-meme n'est pas re-scannee : aucun premier chantier
 * non maritime ne peut modifier ses aretes, et un premier chantier maritime met _waterBuilt a 1.
 * Ce probe couvre donc le seul etat que le batch peut invalider sans payer un BFS inutile. */
function OpexWaterBatchSiteStillBuildable(site)
{
  if (site != null && ("hasBuiltInDock" in site) && site.hasBuiltInDock) return true;
  local ok = false;
  { local probe = AITestMode(); ok = AIMarine.BuildDock(site.dock, AIStation.STATION_NEW); }
  return ok;
}
/* C38 etape 2 : tentative synchrone eau, au meme contrat que le rail. */
function OpexAI::_tryBuildWaterProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (V220_SHIPS == 0) {
        if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = project.src, dst = project.dst, reason = "water_unavailable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else {
        if (this._catalog.ships.len() == 0 && (("shipsByCargo" in this._catalog) ? this._catalog.shipsByCargo.len() == 0 : true)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = project.src, dst = project.dst, reason = "water_unavailable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local plan = project.payload;
      local planCargo = ("cargo" in plan) ? plan.cargo : this._catalog.paxCargo;
      local planKind = ("kind" in plan) ? plan.kind : "pax";
      local srcDesc = ("town" in plan.siteA) ? plan.siteA.town.id : plan.siteA.dock;
      local dstDesc = ("town" in plan.siteB) ? plan.siteB.town.id : plan.siteB.dock;

      if (V220_SHIPS != 0 && planKind == "freight") {
        if (!("shipsByCargo" in this._catalog) || !(planCargo in this._catalog.shipsByCargo) || this._catalog.shipsByCargo[planCargo].len() == 0) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = srcDesc, dst = dstDesc, reason = "water_unavailable", extra = "no_freight_ship" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }

      if (builtCount > 0 && (!OpexWaterBatchSiteStillBuildable(plan.siteA) ||
                             !OpexWaterBatchSiteStillBuildable(plan.siteB))) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = srcDesc, dst = dstDesc, reason = "batch_site_unbuildable", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local capital = (V220_SHIPS != 0)
          ? OpexWaterPlannedCapital(this._catalog, plan)
          : (2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice);
      local need = capital + OpexCashReserve() + WATER_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("water", i, capital, plan.economics.profitAnnual, project.roi, srcDesc, dstDesc, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = srcDesc, dst = dstDesc, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|W|" + project.budgetScore + "|" + project.opcodeScore);
      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      local result = OpexBuildWaterRoute(this._catalog, this._budget, plan);
      if (CAPITAL_QUOTE_LEARNING) OpexCapitalQuoteObserve("water", project, result, project.capital);
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("water", result, capital);
      if (result.ok) OpexSign(anchor, "OM|W|" + year + "|" + plan.distance + "|" + planOps);
      else OpexSign(anchor, "ON|W|" + result.reason + "|" + result.error);
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = srcDesc, dst = dstDesc, reason = "build_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=water src=" + srcDesc + " dst=" + dstDesc + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        return { outcome = "rejected", discards = passDiscards };
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(planCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=water cargo=" + cargoStr + " src=" + result.dockA + " dst=" + result.dockB + " dist=" + plan.distance + " cost=" + capital + " roi=" + project.roi);
          OpexDecide("WATER_BUILD", "line=" + this._nextLineId + " src=" + result.dockA + " dst=" + result.dockB + " cargo=" + cargoStr + " dist=" + plan.distance + " cost=" + capital);
        }
        if (C56_TASK_TRACE) {
          OpexC56TaskLog("WATER_BUILT", "water", "-",
                         "line=" + this._nextLineId + " cost=" + capital + " dist=" + plan.distance
                         + " profit=0");
        }
        this._waterBuilt = true;
        if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
        local lineEntry = {
          stationA = result.dockA, stationB = result.dockB,
          originA = result.dockA, originB = result.dockB,
          cargo = planCargo,
          predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
          mode = "water", vehicle = result.vehicle, vehicles = [result.vehicle],
          depot = result.depot, refleetEngine = AIVehicle.GetEngineType(result.vehicle), vehCount = 1,
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        };
        if (V220_SHIPS != 0) {
          lineEntry.kind <- planKind;
          lineEntry.capacity <- ("capacity" in result) ? result.capacity : 0;
          lineEntry.engineId <- ("engineId" in result) ? result.engineId : -1;
          if (planKind == "freight") {
            if (("industry" in plan.siteA) && plan.siteA.industry != null) lineEntry.srcIndustry <- plan.siteA.industry.id;
            if (("industry" in plan.siteB) && plan.siteB.industry != null) lineEntry.dstIndustry <- plan.siteB.industry.id;
          }
        }
        this._lines.append(lineEntry);
        OpexSign(anchor, "PM|" + this._nextLineId + "|W|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(planCargo));
        this._nextLineId++;
        if (C76_REGEN_TARGETED) this._c76BumpLayer("lines", false);
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

/* V220 : renfort de flotte pour les lignes de bateaux actives quand la marchandise attend. */
function OpexAI::_refleetWaterLines(year)
{
  this._refleetCrashedWaterLines(year);
  if (V220_SHIPS == 0) return;

  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("mode" in line) || line.mode != "water") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("depot" in line) || !AIMarine.IsWaterDepotTile(line.depot)) continue;
    if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
    local firstVeh = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(firstVeh)) continue;

    local stA = AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(stA)) continue;
    local waiting = AIStation.GetCargoWaiting(stA, line.cargo);
    local cap = ("capacity" in line && line.capacity > 0) ? line.capacity : AIVehicle.GetCapacity(firstVeh, line.cargo);
    if (cap <= 0) continue;

    /* Regle du tampon : du stock attend au quai au moins egal a la capacite d'un navire */
    if (waiting < cap) continue;

    /* Plafond de production : ne pas depasser 110 % de la production mensuelle */
    local monthlyProd = 0;
    if (("srcIndustry" in line) && AIIndustry.IsValidIndustry(line.srcIndustry)) {
      monthlyProd = AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo);
    } else {
      local nearestTown = AIStation.GetNearestTown(stA);
      if (AITown.IsValidTown(nearestTown)) {
        monthlyProd = AITown.GetLastMonthProduction(nearestTown, line.cargo);
      }
    }
    if (monthlyProd > 0) {
      local effectiveSpeed = AIVehicle.GetMaxSpeed(firstVeh) / 2;
      if (effectiveSpeed < 1) effectiveSpeed = 1;
      local oneWayDays = (line.distance * 1000) / (36 * effectiveSpeed);
      if (oneWayDays < 1) oneWayDays = 1;
      local roundTripDays = 2 * oneWayDays;
      local tripsPerMonth = 30.0 / roundTripDays.tofloat();
      local monthlyCapPerShip = (cap * tripsPerMonth).tointeger();
      if (monthlyCapPerShip < 1) monthlyCapPerShip = 1;
      local currentShips = line.vehicles.len();
      if ((currentShips + 1) * monthlyCapPerShip > (monthlyProd * 110) / 100) continue;
    }

    /* Plafond de securite de navires par ligne pour eviter l'engorgement des quais */
    if (line.vehicles.len() >= 10) continue;

    local engineId = ("engineId" in line && line.engineId >= 0) ? line.engineId : AIVehicle.GetEngineType(firstVeh);
    local price = AIEngine.GetPrice(engineId);
    if (price <= 0) continue;
    local need = price + OpexCashReserve() + WATER_CAPITAL_MARGIN;
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < need) continue;

    local extraShip = AIVehicle.CloneVehicle(line.depot, firstVeh, true);
    if (!AIVehicle.IsValidVehicle(extraShip)) continue;
    if (!AIVehicle.StartStopVehicle(extraShip)) {
      if (AIVehicle.IsStoppedInDepot(extraShip)) AIVehicle.SellVehicle(extraShip);
      continue;
    }

    line.vehicles.append(extraShip);
    line.vehCount <- line.vehicles.len();
    line.trains = line.vehicles.len();

    if (DECISION_LOG) {
      OpexDecide("WATER_REFLEET", "line=" + line.lineId + " added=1 total=" + line.vehicles.len() + " waiting=" + waiting + " cap=" + cap);
      OpexDecide("WATER_BUY", "line=" + line.lineId + " vehicle=" + extraShip + " engine=" + engineId + " cost=" + price);
    }
  }
}
