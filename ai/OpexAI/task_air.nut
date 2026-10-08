/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C56 follow-up: only airport placement failures identify a bad physical site.
 * A plane/order/cash failure must not poison either endpoint. */
function OpexAI::_padAirFailedSites(plan, result)
{
  if ((!OPEX_AIR_SITE_PAD && !OPEX_AIR_TOWN_PAD) || plan == null || result == null || !("reason" in result)) return;
  if (!("airport" in plan) || plan.airport == null || !("error" in result)) return;
  local reason = result.reason;
  if (OPEX_AIR_TOWN_PAD && result.error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) {
    if ((reason == "PREA" || reason == "AFAIL") && ("siteA" in plan) && plan.siteA != null) {
      this._markPairAbandoned(OpexAirTownPaddingKey(plan.siteA));
    }
    if ((reason == "PREB" || reason == "BFAIL") && ("siteB" in plan) && plan.siteB != null) {
      this._markPairAbandoned(OpexAirTownPaddingKey(plan.siteB));
    }
  }
  if (!OPEX_AIR_SITE_PAD) return;
  /* Only terrain failures survive a different route, date or town rating. */
  if (result.error != AIError.ERR_FLAT_LAND_REQUIRED
      && result.error != AIError.ERR_LAND_SLOPED_WRONG
      && result.error != AIError.ERR_AREA_NOT_CLEAR
      && result.error != AIError.ERR_SITE_UNSUITABLE) return;
  if ((reason == "PREA" || reason == "AFAIL") && ("siteA" in plan) && plan.siteA != null) {
    this._markPairAbandoned(OpexAirSitePaddingKey(plan.siteA, plan.airport.type));
  }
  if ((reason == "PREB" || reason == "BFAIL") && ("siteB" in plan) && plan.siteB != null) {
    this._markPairAbandoned(OpexAirSitePaddingKey(plan.siteB, plan.airport.type));
  }
}

/* Exposition only (probe_air_finance_margin). Jamais lue par un choix. */
function OpexAirFinanceMarginDate(date)
{
  if (date == null || date <= 0) return "0000-00-00";
  local month = AIDate.GetMonth(date);
  local day = AIDate.GetDayOfMonth(date);
  return AIDate.GetYear(date) + "-"
      + (month < 10 ? "0" + month : "" + month) + "-"
      + (day < 10 ? "0" + day : "" + day);
}

function OpexAirFinanceMarginLogTry(path, rank, srcTown, dstTown, newAirports, margin, reserve, capital, need, money, outcome, extra)
{
  local msg = "AIR_FINANCE_TRY date=" + OpexAirFinanceMarginDate(AIDate.GetCurrentDate())
      + " rank=" + rank
      + " src_town=" + srcTown
      + " dst_town=" + dstTown
      + " new_airports=" + newAirports
      + " margin=" + margin
      + " reserve=" + reserve
      + " capital=" + capital
      + " need=" + need
      + " cash=" + money
      + " outcome=" + outcome
      + " path=" + path;
  if (extra != null) msg += extra;
  AILog.Info(msg);
}

/* Exposition only (probe_air_finance_margin). Jamais lue par un choix. */
function OpexAirV126FinanceFields(plan)
{
  /* Champs V126 d'une ligne de sonde de marge, lus sur l'etat C121 du plan. Sans devis
   * calcule (profil sans C121, plan sans etat) seul le drapeau est rendu. margin_v126
   * reprend la formule de OpexAirRequiredMargin pour comparer les deux marges meme quand
   * le reglage vaut 0 et que la marge historique reste appliquee. */
  local flag = AIR_SITE_COST_QUOTE ? 1 : 0;
  local st = (plan != null && ("c121EngineStatic" in plan)) ? plan.c121EngineStatic : null;
  if (st == null || !("v126Quoted" in st) || st.v126Quoted != true) {
    return " v126=" + flag + " quoted=0";
  }
  return " v126=" + flag + " quote_a=" + st.v126LevelA + " quote_b=" + st.v126LevelB
      + " quote_fail=" + st.v126QuoteFail + " stops_model=" + st.v126StopsModel
      + " site_cost=" + st.v126SiteCost + " extra=" + st.v126Extra
      + " margin_legacy=" + OpexAirRequiredMargin(st.newAirportCount)
      + " margin_v126=" + (2000 + (st.v126SiteCost * AIR_SITE_COST_MARGIN_PCT) / 100)
      + " airport_price=" + plan.airport.price;
}

function OpexAirV126CostFields(result)
{
  /* Cout reel ventile par etape, rempli par OpexBuildAirRoute quand la sonde est active.
   * Absent sur les sorties anticipees d'avant le compteur de cout : aucun champ. */
  if (result == null || !("costBreakdown" in result)) return "";
  local brk = result.costBreakdown;
  return " c_level_a=" + brk.levelA + " c_airport_a=" + brk.airportA
      + " c_level_b=" + brk.levelB + " c_airport_b=" + brk.airportB
      + " c_planes=" + brk.planes + " c_stops=" + brk.stops;
}

function OpexAirFinanceMarginInitLine(line, year, money)
{
  line.finProbePrev <- { profit = 0, year = year, cashMin = money };
}

function OpexAirFinanceMarginProfitSum(line)
{
  local sum = 0;
  if (!("vehicles" in line) || line.vehicles == null) return sum;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) sum += AIVehicle.GetProfitThisYear(v);
  }
  return sum;
}

function OpexAirFinanceMarginTick(lines, year)
{
  if (lines == null) return;
  local now = AIDate.GetCurrentDate();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (AIR_FINANCE_MARGIN_YEAR >= 0 && AIR_FINANCE_MARGIN_YEAR != year) {
    foreach (line in lines) {
      if (line == null || typeof line != "table") continue;
      if (!("mode" in line) || line.mode != "air") continue;
      if (!("finProbePrev" in line) || line.finProbePrev == null) continue;
      local buildDate = ("buildDate" in line) ? line.buildDate : 0;
      AILog.Info("AIR_FINANCE_PENDING line=" + (("lineId" in line) ? line.lineId : -1)
          + " build_date=" + OpexAirFinanceMarginDate(buildDate)
          + " days=" + (now - buildDate));
    }
  }
  AIR_FINANCE_MARGIN_YEAR = year;
  foreach (line in lines) {
    if (line == null || typeof line != "table") continue;
    if (!("mode" in line) || line.mode != "air") continue;
    if (!("finProbePrev" in line) || line.finProbePrev == null) continue;
    local prev = line.finProbePrev;
    if (money < prev.cashMin) prev.cashMin = money;
    local sum = OpexAirFinanceMarginProfitSum(line);
    local gotRevenue = false;
    if (prev.year == year) {
      if (sum > prev.profit) gotRevenue = true;
    } else if (sum > 0) {
      gotRevenue = true;
    }
    if (gotRevenue) {
      local buildDate = ("buildDate" in line) ? line.buildDate : 0;
      AILog.Info("AIR_FINANCE_FIRST_REVENUE line=" + (("lineId" in line) ? line.lineId : -1)
          + " build_date=" + OpexAirFinanceMarginDate(buildDate)
          + " first_date=" + OpexAirFinanceMarginDate(now)
          + " days=" + (now - buildDate)
          + " cash_min=" + prev.cashMin);
      line.finProbePrev = null;
    } else {
      prev.profit = sum;
      prev.year = year;
    }
  }
}

/* Liaison aerienne passagers a fort ROI. Deploie la tresorerie excedentaire sans A*. */
function OpexAI::_tryBuildAir(year)
{
  /* La garde testait `airCombos == null && airport == null`. Deux defauts (docs/taches.md
   * S0 sexies) : `_refreshAir` pose TOUJOURS une liste, meme vide (catalog.nut met `[]` avant sa
   * sortie anticipee), donc la garde ne pouvait jamais se declencher sur « aucun avion
   * disponible » et la fonction partait dans sa boucle sur des cartes sans combo ; et le seul etat
   * qu'elle laissait passer -- `airCombos == null` avec `airport != null` -- faisait dereferencer
   * `airCombos.len()` plus bas, ce qui TUE l'IA. On teste desormais la vacuite reelle, et le
   * deref est protege a son propre site. */
  local combos = this._catalog.airCombos;
  if ((combos == null || combos.len() == 0) && this._catalog.airport == null) {
    if (DECISION_LOG) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (_lastAirRefuseMonth != ym) {
        _lastAirRefuseMonth = ym;
        OpexDecide("AIR_REFUSE", "reason=no_aircraft_and_airport");
      }
    }
    return;
  }
  local maxPerYear = 30;
  local maxTotal = 250;
  local maxBatch = 12;
  local builtCount = 0;
  while (builtCount < maxBatch) {
    local airLinesThisYear = 0;
    local totalAirLines = 0;
    foreach (line in this._lines) {
      if (("mode" in line) && line.mode == "air") {
        totalAirLines++;
        if (line.year == year) airLinesThisYear++;
      }
    }
    if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=line_cap_reached lines_year=" + airLinesThisYear + " max_year=" + maxPerYear + " total=" + totalAirLines + " max_total=" + maxTotal);
        }
      }
      break;
    }

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local baseReserve = OpexCashReserve();
    /* ⚠️ NE PAS « CORRIGER » CE 2 000 EN LE PORTANT A LA MARGE MAXIMALE. Essaye et MESURE le
     * 2026-09-02 (results/bench_lotE_air_marge_3y.json) : -11,5 % de valeur (t = -2,66), -9,8 % de
     * note officielle (t = -3,25), -11,2 % de gares.
     *
     * Le defaut apparent est reel : le test d'acceptation plus bas exige `requiredMargin` (jusqu'a
     * 30 000 pour deux aeroports neufs), donc un plan tombant dans cette bande est trouve puis
     * rejete, et le `break` gache le cycle. Mais `maxCapital` n'est PAS qu'un filtre : c'est le
     * budget avec lequel OpexAirPlans CHOISIT le plan a proposer. Le reduire de 30 000 partout
     * appauvrit la selection dans tous les cas ou l'ancienne marge suffisait -- notamment le
     * hub-a-hub, dont la marge reelle n'est que 2 000. On echange une boucle bloquee rare contre
     * une degradation systematique.
     *
     * La bonne correction passerait par le plan, pas par le budget : soit passer la marge exigee a
     * OpexAirPlans pour qu'il l'applique par plan, soit ne pas `break` sur rejet et reessayer avec
     * un budget rabote. Voir docs/taches.md. */
    local maxCapital = money - baseReserve - 2000;
    if (maxCapital <= 0) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=insufficient_capital cash=" + money + " reserve=" + baseReserve);
        }
      }
      break;
    }

    this._budget.begin();
    local plan = OpexAirPlans(this._catalog, this._lines, maxCapital, null,
                              (AIR_ABANDON && ABANDON_MEMORY) ? this._abandonedPairs : null);
    local planOps = this._budget.end("build_air_plans");
    if (plan == null) {
      local nCombos = (this._catalog.airCombos == null) ? -1 : this._catalog.airCombos.len();
      if (builtCount == 0) {
        /* airCombos peut etre null : ne jamais dereferencer pour un panneau de diagnostic. */
        OpexSign(AIMap.GetTileIndex(1, 1), "AD|NULL|C=" + nCombos);
      }
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=no_candidate combos=" + nCombos);
        }
      }
      break;
    }

    local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
    if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "direct_selected");
    local requiredMargin = OpexAirRequiredMargin(newAirports, plan);
    local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
    local need = capital + baseReserve + requiredMargin;
    if (PROBE_AIR_FINANCE_MARGIN && money < need) {
      local outcome = (money >= capital + baseReserve) ? "refused_margin" : "refused_capital";
      OpexAirFinanceMarginLogTry("legacy", builtCount, plan.siteA.town.id, plan.siteB.town.id,
          newAirports, requiredMargin, baseReserve, capital, need, money, outcome,
          OpexAirV126FinanceFields(plan));
    }
    if (money < need) {
      if (money < need) {
        if (DECISION_LOG) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (_lastAirRefuseMonth != ym) {
            _lastAirRefuseMonth = ym;
            OpexDecide("AIR_REFUSE", "reason=insufficient_cash cash=" + money + " need=" + need + " capital=" + capital + " margin=" + requiredMargin);
          }
        }
        break;
      }
    }

    if (B9_AIR_DEMAND_SHADOW || C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
      OpexC121PrepareDemandShadow(this._catalog, plan, this._lines);
    }
    local result = V93_AIR_DEMAND_PRODUCTION
        ? OpexBuildAirRoute(this._catalog, this._budget, plan, this._lines)
        : OpexBuildAirRoute(this._catalog, this._budget, plan);
    if (PROBE_AIR_FINANCE_MARGIN) {
      OpexAirFinanceMarginLogTry("legacy", builtCount, plan.siteA.town.id, plan.siteB.town.id,
          newAirports, requiredMargin, baseReserve, capital, need, money,
          result.ok ? "built" : "failed",
          " planned=" + result.plannedCapital + " actual=" + result.actualCost
              + " reason=" + result.reason + " line=" + this._nextLineId
              + OpexAirV126FinanceFields(plan) + OpexAirV126CostFields(result));
    }
    if (PROBE_SPAN_TRACE) {
      local evtTowns = plan.siteA.town.id + "," + plan.siteB.town.id;
      local evtPlanes = result.ok ? result.vehicles.len() : 0;
      local evtCap = ("capital" in plan) ? plan.capital : 0;
      if (result.ok) OpexSpanEvent("line_built", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes);
      else OpexSpanEvent("build_fail", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes + " reason=" + result.reason);
    }
    if (C63_INVEST_PROBE) OpexC63RecordSpendResult("air", result, plan.capital);
    local anchor = AIMap.GetTileIndex(1, 1);
    OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
    if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
    if (AIR_COST_PROBE) {
      OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                             + result.actualCost + "|"
                             + (("planes" in plan) ? plan.planes : 1) + "|"
                             + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (DECISION_LOG) {
        OpexDecide("AIR_REFUSE", "reason=build_failed detail=" + result.reason + " error=" + result.error + " error_text=" + result.errorText + " dist=" + plan.distance + " cost=" + result.actualCost);
      }
      /* air_abandon : sans cette memorisation, le cycle suivant re-scanne tous les sites pour
       * reproposer EXACTEMENT le meme bestPlan et echouer de la meme facon. Le chemin
       * portefeuille memorise deja ses echecs (voir plus bas) ; ce chemin-ci ne le faisait pas. */
      if (AIR_ABANDON && ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) {
        this._markPairAbandoned(OpexAirPairKey(plan.siteA, plan.siteB));
        this._padAirFailedSites(plan, result);
      }
      break;
    }

    this._airBuilt = true;
    if (C56_TASK_TRACE) OpexC56TaskLog("AIR_BUILT", ("arm" in plan) ? plan.arm : "unknown", "-",
        "line=" + this._nextLineId + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital
        + " stA=" + AIStation.GetStationID(result.stationA) + " stB=" + AIStation.GetStationID(result.stationB));
    if (DECISION_LOG) {
      OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital + " planes=" + result.vehicles.len());
    }
    if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
      cargo = this._catalog.paxCargo,
      predicted = ("economics" in plan && "profitAnnual" in plan.economics) ? plan.economics.profitAnnual : 0,
      predRevenue = plan.economics.revenueAnnual, predRunning = plan.economics.runningAnnual,
      predVehicleRunning = plan.planes * plan.plane.runningCost,
      predAmort = plan.economics.amortAnnual, predCarried = plan.economics.carried,
      predTrains = plan.planes, predOneWayDays = plan.economics.oneWayDays,
      planeCapacity = plan.plane.capacity,
      planeId = plan.plane.id,
      sharedAirportA = ("reuseA" in plan) && plan.reuseA,
      hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
      joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
      joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
      actualCapital = plan.capital,
      iterations = 0, trains = result.vehicles.len(), trains0 = result.vehicles.len(), distance = plan.distance, year = year,
      buildDate = AIDate.GetCurrentDate(),
      mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
      refleetEngine = AIVehicle.GetEngineType(result.vehicle),
      vehCount = result.vehicles.len(),
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
      isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
      lineId = this._nextLineId,
    });
    if (PROBE_AIR_FINANCE_MARGIN) {
      OpexAirFinanceMarginInitLine(this._lines[this._lines.len() - 1], year,
          AICompany.GetBankBalance(AICompany.COMPANY_SELF));
    }
    if (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
      OpexC121AttachLineShadow(this._lines[this._lines.len() - 1], this._nextLineId, plan, result);
    }
    if (C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS || V92_AIR_SERVICE_CHOICE || C98_AIR_REALIZED_PROBE
        || C117_AIR_THROUGHPUT_PROBE) {
      if (C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS) {
        local builtLine = this._lines[this._lines.len() - 1];
        builtLine.targetAirPlanes <- C121_AIR_ECONOMICS && ("c121TargetPlanes" in builtLine)
            ? builtLine.c121TargetPlanes
            : (("targetPlanes" in plan) ? plan.targetPlanes : result.vehicles.len());
        if (C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT) {
          local modelTarget = builtLine.targetAirPlanes;
          builtLine.targetAirPlanes = OpexC121AirPhysicalTarget(builtLine, this._catalog, this._lines);
          if (DECISION_LOG) OpexDecide("C121_TARGET_LIMIT", "phase=build line=" + builtLine.lineId
              + " model=" + modelTarget + " limit=" + builtLine.targetAirPlanes);
        }
      }
      this._lines[this._lines.len() - 1].airMonthlyPax <- ("monthlyPax" in plan) ? plan.monthlyPax : 0;
      if (C98_AIR_REALIZED_PROBE) {
        this._lines[this._lines.len() - 1].c98Arm <- ("arm" in plan) ? plan.arm : "unknown";
      }
      if (C117_AIR_THROUGHPUT_PROBE) {
        this._lines[this._lines.len() - 1].c117Arm <- ("arm" in plan) ? plan.arm : "unknown";
        this._lines[this._lines.len() - 1].c117ShadowMonthly <-
            ("b9ShadowMonthly" in plan) ? plan.b9ShadowMonthly : -1;
      }
    }
    if (V92_AIR_SERVICE_CHOICE && ("v92PairKey" in plan)) {
      V92_CLOSED_PAIRS.rawset(plan.v92PairKey, true);
    }
    OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                           + plan.economics.profitAnnual);
    OpexSign(anchor, "AH|" + this._nextLineId + "|"
                     + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                     + plan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
    OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                     + AICargo.GetCargoLabel(this._catalog.paxCargo));
    this._nextLineId++;
    if (C76_REGEN_TARGETED) this._c76BumpLayer("lines", false);
    builtCount++;
  }
}
/* Revalidation air : un plan garde ses sites depuis la generation, mais le monde peut changer
 * avant son classement puis son chantier. Rejouer les preconditions utiles de
 * OpexAirFindSite sans relancer le balayage des villes. */
function OpexAirBatchSiteStillBuildable(site, airport, plane, reuse)
{
  return OpexAirSiteStillBuildable(site, airport, plane, reuse);
}
/* Un hub garde une limite de routes liee a son aeroport. La generation l'avait controlee sur
 * l'ancien this._lines ; apres un succes de batch, seul ce comptage vivant peut dire si le plan
 * reste admissible. Pas de controle de taille de flotte ici : plan.planes ne depend d'aucun etat
 * modifie par le chantier precedent et le relire serait du cout d'opcodes sans information. */
function OpexAirBatchHubHasCapacity(anchor, plane, lines)
{
  if (!AIAirport.IsAirportTile(anchor) ||
      !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(anchor), plane.planeType)) return false;
  local station = AIStation.GetStationID(anchor);
  if (!AIStation.IsValidStation(station)) return false;
  local routes = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    /* this._lines garde les tuiles d'aeroport, pas les StationID. Comparer les tuiles au
     * StationID du hub laisserait passer le plafond apres le premier succes du batch. */
    if (AIStation.GetStationID(line.stationA) == station ||
        AIStation.GetStationID(line.stationB) == station) routes++;
  }
  local airportType = AIAirport.GetAirportType(anchor);
  local maxRoutes = OpexAirAirportMaxRoutes(airportType);
  return routes < maxRoutes;
}
/* La paire O/D et les bouts nouveaux etaient valides lors de la generation. Avant toute tentative,
 * revalider l'etat vivant : une autre construction ou le monde peut avoir rendu le plan caduc. */
function OpexAirBatchPlanStillLive(plan, lines)
{
  if (OpexAirRecoveryBlocksPlan(plan)) return false;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local c83OwnSecondA = ("c83OwnSecondSlotA" in plan) && plan.c83OwnSecondSlotA;
  local c83OwnSecondB = ("c83OwnSecondSlotB" in plan) && plan.c83OwnSecondSlotB;
  if (!reuseA) {
    local servedA = OpexAirTownServed(plan.siteA.town, lines);
    if (c83OwnSecondA) {
      if (!servedA || !OpexAirC83SecondSlotOpen(plan.siteA.town)) return false;
    } else if (servedA) {
      return false;
    }
  }
  if (!reuseB) {
    local servedB = OpexAirTownServed(plan.siteB.town, lines);
    if (c83OwnSecondB) {
      if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;
    } else if (servedB) {
      return false;
    }
  }
  if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == plan.siteA.town.tile && line.originB == plan.siteB.town.tile) ||
        (line.originA == plan.siteB.town.tile && line.originB == plan.siteA.town.tile)) return false;
  }
  return true;
}
/* C38 etape 2 : tentative synchrone air, incluant les gardes de site et de flotte. */
function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local plan = project.payload;
      if (OpexAirV92PairBlocked(this._lines, plan)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "v92_pair_taken", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
      }
      if (!OpexAirBatchPlanStillLive(plan, this._lines)) {
          if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveNote("batch_plan_dead", 1);
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "batch_plan_dead", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
      }
      if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                             ("reuseA" in plan) && plan.reuseA)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteA_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                             ("reuseB" in plan) && plan.reuseB)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteB_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      local townAId = ("siteA" in plan && "town" in plan.siteA && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
      local townBId = ("siteB" in plan && "town" in plan.siteB && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
      if (C60_TOWN_RATING_PROBE) {
        if (townAId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townAId);
        if (townBId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townBId);
      }
      if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
      local maxPerYear = 30;
      local maxTotal = 250;
      local airLinesThisYear = 0;
      local totalAirLines = 0;
      foreach (line in this._lines) {
        if (("mode" in line) && line.mode == "air") {
          totalAirLines++;
          if (line.year == year) airLinesThisYear++;
        }
      }
      if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "line_cap_reached", extra = "lines_year=" + airLinesThisYear + " total=" + totalAirLines });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = OpexAirPairKey(plan.siteA, plan.siteB);
      local abandonedSiteA = OpexAirSitePaddingKey(plan.siteA, plan.airport.type);
      local abandonedSiteB = OpexAirSitePaddingKey(plan.siteB, plan.airport.type);
      local abandonedTownA = OpexAirTownPaddingKey(plan.siteA);
      local abandonedTownB = OpexAirTownPaddingKey(plan.siteB);
      if (ABANDON_MEMORY && (OpexAirPairIsAbandoned(this._abandonedPairs, plan.siteA, plan.siteB)
          || (OPEX_AIR_TOWN_PAD && ((!(("reuseA" in plan) && plan.reuseA) && (abandonedTownA in this._abandonedPairs))
              || (!(("reuseB" in plan) && plan.reuseB) && (abandonedTownB in this._abandonedPairs))))
          || (OPEX_AIR_SITE_PAD && ((abandonedSiteA in this._abandonedPairs)
              || (abandonedSiteB in this._abandonedPairs))))) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local spChoose = PROBE_SPAN_TRACE ? OpexSpanBegin("build.air.choose_plan") : null;
      local buildChoice = C118_AIR_TERRITORIAL_EXPANSION
          ? OpexC118ChooseBuildPlan(this._catalog, plan, project)
          : OpexC116ChooseBuildPlan(this._catalog, plan);
      if (spChoose != null) OpexSpanEnd(spChoose);
      local buildPlan = buildChoice.plan;
      if (C118_AIR_TERRITORIAL_EXPANSION && (C118_AIR_COVERAGE_PROBE || DECISION_LOG)) {
        local c118Now = AIDate.GetCurrentDate();
        AILog.Info("C118_DECISION date=" + c118Now
            + " y=" + AIDate.GetYear(c118Now) + " m=" + AIDate.GetMonth(c118Now)
            + " d=" + AIDate.GetDayOfMonth(c118Now)
            + " rank=" + i + " arm=" + (("arm" in plan) ? plan.arm : "unknown")
            + " active=" + ((("active" in buildChoice) && buildChoice.active) ? 1 : 0)
            + " new_towns=" + (("newTowns" in buildChoice) ? buildChoice.newTowns : 0)
            + " base_engine=" + ((("c118C68Plane" in plan) && plan.c118C68Plane != null)
                ? plan.c118C68Plane.id : plan.plane.id) + " engine=" + buildPlan.plane.id
            + " available=" + (("available" in buildChoice) ? buildChoice.available : 0)
            + " base_finance=" + (("baselineFinance" in buildChoice) ? buildChoice.baselineFinance : 0)
            + " finance=" + (("chosenFinance" in buildChoice) ? buildChoice.chosenFinance : 0)
            + " base_cash_after=" + (("baselineCashAfter" in buildChoice) ? buildChoice.baselineCashAfter : 0)
            + " cash_after=" + (("chosenCashAfter" in buildChoice) ? buildChoice.chosenCashAfter : 0)
            + " base_flow_after=" + (("baselineFlowAfter" in buildChoice) ? buildChoice.baselineFlowAfter : 0)
            + " flow_after=" + (("chosenFlowAfter" in buildChoice) ? buildChoice.chosenFlowAfter : 0)
            + " next_capital=" + (("nextCapital" in buildChoice) ? buildChoice.nextCapital : 0)
            + " next_town=" + (("nextTown" in buildChoice) ? buildChoice.nextTown : -1)
            + " base_days=" + (("baselineDays" in buildChoice) ? buildChoice.baselineDays : 0)
            + " days=" + (("chosenDays" in buildChoice) ? buildChoice.chosenDays : 0)
            + " base_profit=" + (("baselineProfit" in buildChoice) ? buildChoice.baselineProfit : plan.economics.profitAnnual)
            + " profit=" + (("chosenProfit" in buildChoice) ? buildChoice.chosenProfit : buildPlan.economics.profitAnnual)
            + " changed=" + (buildChoice.changed ? 1 : 0));
        /* Le harness ne conserve pas AILog. En mode probe uniquement, publier
         * une version compacte via SIGN, le canal durable deja utilise par les
         * sweeps. Plusieurs panneaux courts evitent la troncature a 31 chars. */
        if (C118_AIR_COVERAGE_PROBE && ("active" in buildChoice) && buildChoice.active) {
          C118_AIR_DECISION_SEQ++;
          local c118Seq = C118_AIR_DECISION_SEQ;
          local c118YY = AIDate.GetYear(c118Now) % 100;
          local c118BaseEngine = (("c118C68Plane" in plan) && plan.c118C68Plane != null)
              ? plan.c118C68Plane.id : plan.plane.id;
          local c118BaseDays = (("baselineDays" in buildChoice) ? buildChoice.baselineDays : 0.0).tointeger();
          local c118Days = (("chosenDays" in buildChoice) ? buildChoice.chosenDays : 0.0).tointeger();
          OpexSign(anchor, "C8D|" + c118Seq + "|" + c118YY + "|" + AIDate.GetMonth(c118Now)
              + "|" + AIDate.GetDayOfMonth(c118Now) + "|" + buildChoice.newTowns);
          OpexSign(anchor, "C8R|" + c118Seq + "|" + plan.siteA.town.id + "|" + plan.siteB.town.id);
          OpexSign(anchor, "C8E|" + c118Seq + "|" + c118BaseEngine + "|" + buildPlan.plane.id
              + "|" + buildChoice.nextTown);
          OpexSign(anchor, "C8C|" + c118Seq + "|" + (buildChoice.baselineCashAfter / 1000)
              + "|" + (buildChoice.chosenCashAfter / 1000) + "|" + (buildChoice.nextCapital / 1000));
          OpexSign(anchor, "C8F|" + c118Seq + "|" + buildChoice.baselineFlowAfter.tointeger()
              + "|" + buildChoice.chosenFlowAfter.tointeger());
          OpexSign(anchor, "C8T|" + c118Seq + "|" + c118BaseDays + "|" + c118Days);
        }
      }
      if (buildChoice.changed && DECISION_LOG) {
        OpexDecide(C118_AIR_TERRITORIAL_EXPANSION ? "C118_EQUIPMENT" : "C116_EQUIPMENT", "rank=" + i
            + " arm=" + (("arm" in plan) ? plan.arm : "unknown")
            + " base_engine=" + ((("c118C68Plane" in plan) && plan.c118C68Plane != null)
                ? plan.c118C68Plane.id : plan.plane.id) + " engine=" + buildPlan.plane.id
            + (C118_AIR_TERRITORIAL_EXPANSION
                ? " next_capital=" + buildChoice.nextCapital
                    + " base_days=" + buildChoice.baselineDays + " days=" + buildChoice.chosenDays
                : " gap=" + buildPlan.c116TargetGap
                    + " dC=" + buildChoice.deltaCapital + " dP=" + buildChoice.deltaProfit
                    + " base_C=" + buildPlan.c116BaselineCapital + " C=" + buildPlan.economics.capital
                    + " base_P=" + buildPlan.c116BaselineProfit + " P=" + buildPlan.economics.profitAnnual));
      }

      local spCash = PROBE_SPAN_TRACE ? OpexSpanBegin("build.air.cash") : null;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected");
      local requiredMargin = OpexAirRequiredMargin(newAirports, buildPlan);
      local capital = ("capital" in buildPlan) ? buildPlan.capital
          : (newAirports * buildPlan.airport.price + buildPlan.plane.price);
      local need = capital + OpexCashReserve() + requiredMargin;
      if (spCash != null) OpexSpanEnd(spCash);
      if (PROBE_AIR_FINANCE_MARGIN && money < need) {
        local reserve = need - capital - requiredMargin;
        local outcome = (money >= capital + reserve) ? "refused_margin" : "refused_capital";
        OpexAirFinanceMarginLogTry("portfolio", i, plan.siteA.town.id, plan.siteB.town.id,
            newAirports, requiredMargin, reserve, capital, need, money, outcome,
            OpexAirV126FinanceFields(buildPlan));
      }
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("air", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.tile, plan.siteB.town.tile, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|A|" + project.budgetScore + "|" + project.opcodeScore);
      if (AIR_EARLY_SLOT && ("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
        local earlyTownA = ("earlySlotTownA" in project) ? project.earlySlotTownA : townAId;
        local earlyTownB = ("earlySlotTownB" in project) ? project.earlySlotTownB : townBId;
        OpexSign(anchor, "SK|" + yy + "|" + earlyTownA + "|" + earlyTownB + "|"
                         + project.earlySlotBonusPct);
        if (DECISION_LOG) {
          local earlyScoreKey = "fundScore";
          local earlyBaseScore = project[earlyScoreKey];
          local earlyBoostedScore = OpexProjectSelectionScore(project, earlyScoreKey);
          local popA = ("earlySlotPopA" in project) ? project.earlySlotPopA : -1;
          local popB = ("earlySlotPopB" in project) ? project.earlySlotPopB : -1;
          OpexDecide("EARLY_SLOT_SELECT", "town_a=" + earlyTownA + " pop_a=" + popA
                     + " town_b=" + earlyTownB + " pop_b=" + popB
                     + " claims=" + project.earlySlotClaims
                     + " bonus_claims=" + project.earlySlotBonusClaims
                     + " secured_before=" + project.earlySlotServedBefore
                     + " target=" + AIR_EARLY_SLOT_TARGET_TOWNS
                     + " bonus_pct=" + project.earlySlotBonusPct
                     + " base_score=" + earlyBaseScore
                     + " boosted_score=" + earlyBoostedScore);
        }
      }

      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      if (B9_AIR_DEMAND_SHADOW || C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
        OpexC121PrepareDemandShadow(this._catalog, buildPlan, this._lines);
      }
      local result = V93_AIR_DEMAND_PRODUCTION
          ? OpexBuildAirRoute(this._catalog, this._budget, buildPlan, this._lines)
          : OpexBuildAirRoute(this._catalog, this._budget, buildPlan);
      if (PROBE_AIR_FINANCE_MARGIN) {
        OpexAirFinanceMarginLogTry("portfolio", i, plan.siteA.town.id, plan.siteB.town.id,
            newAirports, requiredMargin, need - capital - requiredMargin, capital, need, money,
            result.ok ? "built" : "failed",
            " planned=" + result.plannedCapital + " actual=" + result.actualCost
                + " reason=" + result.reason + " line=" + this._nextLineId
                + OpexAirV126FinanceFields(buildPlan) + OpexAirV126CostFields(result));
      }
      if (PROBE_SPAN_TRACE) {
        local evtTowns = plan.siteA.town.id + "," + plan.siteB.town.id;
        local evtPlanes = result.ok ? result.vehicles.len() : 0;
        local evtCap = ("capital" in buildPlan) ? buildPlan.capital : 0;
        if (result.ok) OpexSpanEvent("line_built", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes);
        else OpexSpanEvent("build_fail", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes + " reason=" + result.reason);
      }
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("air", result, buildPlan.capital);
      OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
      if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
      if (AIR_COST_PROBE) {
        OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                               + result.actualCost + "|"
                               + (("planes" in buildPlan) ? buildPlan.planes : 1) + "|"
                               + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        local errorAnchor = null;
        if ((result.reason == "PREA" || result.reason == "AFAIL") && plan.siteA != null) {
          errorAnchor = plan.siteA.anchor;
        } else if ((result.reason == "PREB" || result.reason == "BFAIL") && plan.siteB != null) {
          errorAnchor = plan.siteB.anchor;
        }
        local errorTown = (errorAnchor != null && AIMap.IsValidTile(errorAnchor))
            ? AITile.GetClosestTown(errorAnchor) : -1;
        local errorOwnAirports = -1;
        if (result.error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN && errorTown >= 0
            && (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE)) {
          local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
          ownAirports.Valuate(AIStation.GetNearestTown);
          ownAirports.KeepValue(errorTown);
          errorOwnAirports = ownAirports.Count();
        }
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({
          rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile,
          reason = "build_failed", detail = result.reason, error = result.error,
          error_anchor = errorAnchor, error_town = errorTown,
          error_own_airports = errorOwnAirports, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=air src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " reason=build_failed detail=" + result.reason + " error=" + result.error + " error_text=" + result.errorText);
        }
        if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) {
          this._markPairAbandoned(abandonedKey);
          this._padAirFailedSites(plan, result);
        }
        local ret = { outcome = "rejected", discards = passDiscards };
        if (C69_BOTTLENECK_PROBE) ret.reason <- result.reason;
        return ret;
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=air cargo=" + cargoStr + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " dist=" + plan.distance + " cost=" + plan.capital + " profit=" + plan.economics.profitAnnual + " roi=" + project.roi);
          OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + buildPlan.economics.profitAnnual + " cost=" + buildPlan.capital + " planes=" + result.vehicles.len() + " engine=" + buildPlan.plane.id);
        }
        if (C118_AIR_COVERAGE_PROBE) {
          local c118Covered = OpexC118OwnCoveredTownSet(this._catalog.paxCargo);
          local c118Airports = AIStationList(AIStation.STATION_AIRPORT);
          local c118Now = AIDate.GetCurrentDate();
          AILog.Info("C118_COVERAGE date=" + c118Now
              + " y=" + AIDate.GetYear(c118Now) + " m=" + AIDate.GetMonth(c118Now)
              + " d=" + AIDate.GetDayOfMonth(c118Now)
              + " year=" + year + " line=" + this._nextLineId
              + " towns=" + c118Covered.len() + " airports=" + c118Airports.Count()
              + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id
              + " reuse_a=" + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0)
              + " reuse_b=" + ((("reuseB" in plan) && plan.reuseB) ? 1 : 0));
          OpexSign(anchor, "C8V|" + (AIDate.GetYear(c118Now) % 100) + "|" + AIDate.GetMonth(c118Now)
              + "|" + AIDate.GetDayOfMonth(c118Now) + "|" + c118Covered.len() + "|" + c118Airports.Count());
        }
        if (C56_TASK_TRACE) OpexC56TaskLog("AIR_BUILT", ("arm" in plan) ? plan.arm : "unknown", "-",
            "line=" + this._nextLineId + " profit=" + buildPlan.economics.profitAnnual + " cost=" + buildPlan.capital
            + " stA=" + AIStation.GetStationID(result.stationA) + " stB=" + AIStation.GetStationID(result.stationB));
        this._airBuilt = true;
        if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
        this._lines.append({
          stationA = result.stationA, stationB = result.stationB,
          originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
          cargo = this._catalog.paxCargo,
          predicted = ("economics" in buildPlan && "profitAnnual" in buildPlan.economics) ? buildPlan.economics.profitAnnual : 0,
          predRevenue = buildPlan.economics.revenueAnnual, predRunning = buildPlan.economics.runningAnnual,
          predVehicleRunning = buildPlan.planes * buildPlan.plane.runningCost,
          predAmort = buildPlan.economics.amortAnnual, predCarried = buildPlan.economics.carried,
          predTrains = buildPlan.planes, predOneWayDays = buildPlan.economics.oneWayDays,
          planeCapacity = buildPlan.plane.capacity,
          planeId = buildPlan.plane.id,
          sharedAirportA = ("reuseA" in plan) && plan.reuseA,
          hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
          joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
          joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
          actualCapital = buildPlan.capital,
          iterations = 0, trains = result.vehicles.len(), trains0 = result.vehicles.len(), distance = plan.distance, year = year,
          buildDate = AIDate.GetCurrentDate(),
          mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
          refleetEngine = AIVehicle.GetEngineType(result.vehicle),
          vehCount = result.vehicles.len(),
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        if (PROBE_AIR_FINANCE_MARGIN) {
          OpexAirFinanceMarginInitLine(this._lines[this._lines.len() - 1], year,
              AICompany.GetBankBalance(AICompany.COMPANY_SELF));
        }
        if (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
          OpexC121AttachLineShadow(this._lines[this._lines.len() - 1], this._nextLineId, buildPlan, result);
        }
        if (C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS || V92_AIR_SERVICE_CHOICE || C98_AIR_REALIZED_PROBE
            || C117_AIR_THROUGHPUT_PROBE) {
          if (C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS) {
            local builtLine = this._lines[this._lines.len() - 1];
            builtLine.targetAirPlanes <- C121_AIR_ECONOMICS && ("c121TargetPlanes" in builtLine)
                ? builtLine.c121TargetPlanes
                : (("targetPlanes" in buildPlan) ? buildPlan.targetPlanes : result.vehicles.len());
            if (C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT) {
              local modelTarget = builtLine.targetAirPlanes;
              builtLine.targetAirPlanes = OpexC121AirPhysicalTarget(builtLine, this._catalog, this._lines);
              if (DECISION_LOG) OpexDecide("C121_TARGET_LIMIT", "phase=build line=" + builtLine.lineId
                  + " model=" + modelTarget + " limit=" + builtLine.targetAirPlanes);
            }
          }
          this._lines[this._lines.len() - 1].airMonthlyPax <- ("monthlyPax" in buildPlan) ? buildPlan.monthlyPax : 0;
          if (C98_AIR_REALIZED_PROBE) {
            this._lines[this._lines.len() - 1].c98Arm <- ("arm" in plan) ? plan.arm : "unknown";
          }
          if (C117_AIR_THROUGHPUT_PROBE) {
            this._lines[this._lines.len() - 1].c117Arm <- ("arm" in plan) ? plan.arm : "unknown";
            this._lines[this._lines.len() - 1].c117ShadowMonthly <-
                ("b9ShadowMonthly" in buildPlan) ? buildPlan.b9ShadowMonthly : -1;
          }
        }
        if (V92_AIR_SERVICE_CHOICE && ("v92PairKey" in plan)) {
          V92_CLOSED_PAIRS.rawset(plan.v92PairKey, true);
        }
        OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                               + buildPlan.economics.profitAnnual);
        OpexSign(anchor, "AH|" + this._nextLineId + "|"
                         + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                         + buildPlan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
        OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        if (AIR_EARLY_SLOT && ("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
          local earlyTownA = ("earlySlotTownA" in project) ? project.earlySlotTownA : townAId;
          local earlyTownB = ("earlySlotTownB" in project) ? project.earlySlotTownB : townBId;
          OpexSign(anchor, "SB|" + yy + "|" + earlyTownA + "|" + earlyTownB + "|"
                           + project.earlySlotClaims);
          if (DECISION_LOG) {
            OpexDecide("EARLY_SLOT_BUILD", "line=" + this._nextLineId
                       + " town_a=" + earlyTownA + " town_b=" + earlyTownB
                       + " claims=" + project.earlySlotClaims
                       + " bonus_claims=" + project.earlySlotBonusClaims
                       + " secured_before=" + project.earlySlotServedBefore
                       + " secured_after=" + (project.earlySlotServedBefore + project.earlySlotClaims)
                       + " target=" + AIR_EARLY_SLOT_TARGET_TOWNS
                       + " bonus_pct=" + project.earlySlotBonusPct);
          }
        }
        this._nextLineId++;
        if (C76_REGEN_TARGETED) this._c76BumpLayer("lines", false);
        return { outcome = "built", discards = passDiscards };
      }

  return { outcome = "rejected", discards = passDiscards };
}
/* Dimensionnement progressif de l'air. Une prediction de population ne peut plus acheter une
 * flotte entiere au demarrage. Apres au moins une annee, on ajoute au plus UN avion par ligne et
 * par an si (1) les appareils existants gagnent de l'argent et (2) au moins une charge utile
 * complete attend dans les deux aeroports. Un echec de cash est reporte a l'annee suivante : la
 * file ne le resonde pas a chaque cycle et ne gaspille donc pas d'opcodes. */
/* Cause du refus de croissance d'une flotte aerienne, une seule fois par ligne et par an.
 * Codes : Y deja grandie cette annee, V aucun avion vivant, D ligne morte, L profit negatif,
 * C plafond physique de l'aeroport atteint, S un an de mauvaise sante,
 * K ligne en cours de rebut, M tresorerie, X l'achat a echoue. */
function OpexAirFleetRefusal(line, year, code)
{
  if (C50_CHRONOLOGY_PROBE) {
    if (code == "M") {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local stA = ("stationA" in line) ? line.stationA : 0;
      local stB = ("stationB" in line) ? line.stationB : 0;
      OpexC50LogCashRefusal("air_fleet", line.lineId, 30000, 0, 0, stA, stB, 30000, money);
    }
    if (C50_NON_EXPANSION_LEDGER != null && ("air" in C50_NON_EXPANSION_LEDGER)) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      local dedupKey = "c50_ref_" + code;
      if (!(dedupKey in line) || line[dedupKey] != ym) {
        line[dedupKey] <- ym;
        local k = "ref_" + code;
        if (k in C50_NON_EXPANSION_LEDGER.air) C50_NON_EXPANSION_LEDGER.air[k]++;
        else C50_NON_EXPANSION_LEDGER.air[k] <- 1;
      }
    }
  }
  if (!AIR_FLEET_PROBE && !DECISION_LOG) return;
  if (!("lineId" in line)) return;
  /* rabattage_diag (2026-09-02) : dedup resserre au MOIS, pas a l'annee -- le dedup annuel
   * masquait un blocage de plusieurs mois derriere un seul motif fige au premier refus de
   * l'annee, alors que la tresorerie disponible changeait entre-temps. Diagnostic uniquement. */
  local month = AIDate.GetMonth(AIDate.GetCurrentDate());
  local ym = year * 12 + month;
  if (("lastFleetProbeMonth" in line) && line.lastFleetProbeMonth == ym) return;
  line.lastFleetProbeMonth <- ym;
  if (AIR_FLEET_PROBE) {
    OpexSign(AIMap.GetTileIndex(2, 10 + line.lineId),
             "FR|" + (year % 100) + (month < 10 ? "0" + month : "" + month) + "|" + line.lineId + "|" + code);
  }
  if (DECISION_LOG) {
    local yieldVal = OpexAirFleetYield(line);
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    local reasonStr = code;
    if (code == "Y") reasonStr = "already_grown_this_year";
    else if (code == "V") reasonStr = "no_live_aircraft";
    else if (code == "D") reasonStr = "dead_line";
    else if (code == "L") reasonStr = "negative_profit";
    else if (code == "C") reasonStr = "airport_capacity_reached";
    else if (code == "S") reasonStr = "poor_health_streak";
    else if (code == "K") reasonStr = "scrapping";
    else if (code == "M") reasonStr = "insufficient_cash";
    else if (code == "X") reasonStr = "purchase_failed";
    OpexDecide("AIR_FLEET", "action=refuse line=" + line.lineId + " reason=" + reasonStr + " planes=" + have + " yield=" + yieldVal);
  }
}
/* Rendement marginal d'une ligne aerienne : profit PAR APPAREIL deja en service. C'est le
 * predicteur du remboursement de l'appareil SUIVANT -- une ligne qui gagne 100 k£ avec 2 avions
 * rembourse deux fois plus vite que celle qui gagne 100 k£ avec 8. `lastProfit` (mesure ecrite
 * par _reportLines) prime sur `predicted` (modele) des qu'il existe ; une ligne neuve jamais
 * rapportee tombe donc sur sa prevision plutot que sur zero, sinon elle serait servie en dernier
 * pendant toute sa premiere annee. */
function OpexAirFleetYield(line)
{
  local fleet = ("vehCount" in line) ? line.vehCount
              : (("vehicles" in line) ? line.vehicles.len() : 1);
  if (fleet < 1) fleet = 1;
  local profit = ("lastProfit" in line) ? line.lastProfit
               : (("predicted" in line) ? line.predicted : 0);
  return profit / fleet;
}
/* Comparateur de tete de file pour la croissance aerienne : meilleur rendement d'abord.
 * Fonction NOMMEE au niveau module : dans cet environnement
 * Squirrel une closure imbriquee ne capture jamais les locales englobantes. */
function OpexAirFleetPriorityCompare(a, b)
{
  local ya = OpexAirFleetYield(a);
  local yb = OpexAirFleetYield(b);
  if (ya > yb) return -1;
  if (ya < yb) return 1;
  return 0;
}
/* C34.2 : `plan` non nul = MODE A BLANC. La fonction traverse exactement les memes treize gardes
 * de refus, mais au lieu d'acheter elle enregistre ce qu'elle achererait dans `plan`, sous la forme
 * { line, want, planePrice }. C'est volontairement une reutilisation et non une extraction : les
 * gardes sont trop nombreuses et trop calibrees pour etre dupliquees sans divergence silencieuse.
 * Le portefeuille appelle ainsi la meme decision que la tache, puis l'arbitre contre les lignes
 * neuves au lieu de la servir d'office avant elles. */
/* C121 : nombre d'avions justifies par le stock en gare (0 = aucun). Meme regle
 * qu'AAAHogEx : (stock - min(50, capacite)) / capacite, ou au moins un avion si plus
 * d'un quart d'avion attend alors que la note de gare est sous 50 %. */
function OpexC121FleetStockEvidence(line)
{
  local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
  if (planeCap <= 0 && ("vehicles" in line)) {
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) {
        planeCap = AIVehicle.GetCapacity(v, line.cargo);
        if (planeCap > 0) { line.planeCapacity <- planeCap; break; }
      }
    }
  }
  if (planeCap <= 0) return 0;
  local best = 0;
  foreach (tile in [line.stationA, ("stationB" in line) ? line.stationB : null]) {
    if (tile == null) continue;
    local st = AIStation.GetStationID(tile);
    if (!AIStation.IsValidStation(st)) continue;
    local wait = AIStation.GetCargoWaiting(st, line.cargo);
    local bottom = planeCap < 50 ? planeCap : 50;
    local n = wait > bottom ? (wait - bottom) / planeCap : 0;
    if (n < 1 && wait > planeCap / 4 && AIStation.GetCargoRating(st, line.cargo) < 50) n = 1;
    if (n > best) best = n;
  }
  return best;
}

function OpexAI::_resizeAirFleets(year, plan = null)
{
  if (PROBE_AIR_FINANCE_MARGIN) OpexAirFinanceMarginTick(this._lines, year);
  local spFleet = PROBE_SPAN_TRACE ? OpexSpanBegin("fleet.resize") : null;
  local anchor = AIMap.GetTileIndex(1, 1);
  /* air_roi_order : servir la ligne qui rembourse le plus vite, pas la plus ancienne. Le tri
   * porte sur une COPIE de references : _lines garde son ordre, dont depend l'indexation de
   * _scrapDeadLines (retrait par position). */
  local airLines = [];
  foreach (line in this._lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    /* Opcode optimisation: a line still inside the growth cooldown cannot
     * contribute a fleet project and used to pay the ROI sort cost anyway.
     * Keep the three pre-cadence priority paths in the list: scrapping must
     * reject before refleet, V92 may need to resume a reequipment, and a crash
     * refleet explicitly bypasses the growth cadence. */
    /* V92 pending is not a cheap flag: discovering it scans live vehicles.
     * Do not pay that scan once here and again in the historical guard below.
     * V92 is OFF in the current defaults; if explicitly enabled, keep the
     * historical path rather than changing its priority semantics. */
    local priorityPath = (("scrapping" in line) && line.scrapping)
        || (("needsRefleet" in line) && line.needsRefleet);
    if (AIR_FLEET_COOLDOWN_PREFILTER && !V92_AIR_SERVICE_CHOICE && !priorityPath) {
      local cooldown = false;
      if (AIR_FLEET_CADENCE_DAYS >= 365) {
        cooldown = ("lastAirFleetYear" in line) && line.lastAirFleetYear == year;
      } else {
        local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate
            : (("buildDate" in line) ? line.buildDate : 0);
        cooldown = lastDate > 0
            && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS;
      }
      if (cooldown) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "already_grown_this_year", 1);
        continue;
      }
    }
    airLines.append(line);
  }
  if (AIR_ROI_ORDER) {
    if (EXP_OPCODE_EXACT_ON) airLines = OpexAirFleetSortSelect(airLines);
    else airLines.sort(OpexAirFleetPriorityCompare);
  }
  foreach (line in airLines) {
    if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordExamined("fleet", 1);
    /* B8 / G10 : une ligne en liquidation ne peut recevoir aucun appareil neuf, y compris une
     * reconstitution de crash. Ce garde doit preceder needsRefleet : pendant la fenetre de vente,
     * les avions encore vivants peuvent redevenir profitables et remettre deadStreak a zero. */
    if (("scrapping" in line) && line.scrapping) {
      OpexAirFleetRefusal(line, year, "K");
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "scrapping", 1);
      continue;
    }
    /* V92 : finir un remplacement même si la ligne n'est plus candidate à la croissance.
     * Sinon les avions déjà envoyés au hangar y restent. */
    if (V92_AIR_SERVICE_CHOICE && OpexAirLineReequipPending(line)) {
      local resumed = OpexAirAddPlane(line, this._catalog, this._lines);
      if (!(("reason" in resumed) && (resumed.reason == "NOLIVE" || resumed.reason == "NOVEH"))) continue;
    }
    /* Reconstitution de crash : elle passe avant les gardes de croissance
     * (have=0, profit ancien negatif, cadence), sinon le dernier avion ne peut
     * jamais redevenir un template. OpexAirRefleetCrashedPlane reconstruit les
     * ordres depuis les metadonnees durables de la ligne. */
    if (("needsRefleet" in line) && line.needsRefleet) {
      local recovered = OpexAirRefleetCrashedPlane(line);
      if (recovered.added > 0) {
        local afterCrash = (("vehCount" in line) ? line.vehCount : 0) + recovered.added;
        if ("vehCount" in line) line.vehCount = afterCrash;
        else line.vehCount <- afterCrash;
        if ("trains" in line) line.trains = afterCrash;
        else line.trains <- afterCrash;
        line.needsRefleet = false;
        if (DECISION_LOG || C52_CRASH_LOG) {
          OpexDecide("CRASH_REFLEET", "mode=air line=" + line.lineId + " vehicle=" + line.vehicle);
        }
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "crash_refleeted", 1);
      } else {
        OpexAirFleetRefusal(line, year, "R");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "refleet_failed", 1);
      }
      continue;
    }
    /* C15 : Cadence d'extension de flotte aerienne.
     * Si AIR_FLEET_CADENCE_DAYS >= 365 : conservation exacte du verrou annuel historique.
     * Sinon : verrou glissant en jours depuis la derniere extension (ou la creation de la ligne). */
    if (AIR_FLEET_CADENCE_DAYS >= 365) {
      if (("lastAirFleetYear" in line) && line.lastAirFleetYear == year) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "already_grown_this_year", 1);
        continue;
      }
    } else {
      local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate : (("buildDate" in line) ? line.buildDate : 0);
      if (lastDate > 0 && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "already_grown_this_year", 1);
        continue;
      }
    }
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    if (have < 1) {
      OpexAirFleetRefusal(line, year, "V");
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "no_live_aircraft", 1);
      continue;
    }
    OpexC121RefreshVisibleFleet(this._catalog, line, this._lines);
    if (C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT) {
      /* Garde scalaire avant les gardes d'observation. La cadence partagee
       * est deja recalculee une seule fois, plus bas, pour un renfort eligible :
       * ne pas rebalayer tous les aeroports des lignes encore trop jeunes. */
      local limit = OpexC121AirTargetLimit(line, AIR_MAX_PLANES_PER_ROUTE);
      if (have >= limit) {
        OpexAirFleetRefusal(line, year, "T");
        if (DECISION_LOG) OpexDecide("C121_TARGET_LIMIT", "phase=resize line=" + line.lineId
            + " have=" + have + " limit=" + limit);
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "c121_target_reached", 1);
        continue;
      }
    }
    if (C121_AIR_VISIBLE_COMPETITION && ("targetAirPlanes" in line) && have >= line.targetAirPlanes) {
      OpexAirFleetRefusal(line, year, "T");
      continue;
    }
    local c84BelowTarget = C84_AIR_TARGET_FLEET && ("targetAirPlanes" in line)
        && line.targetAirPlanes > have;
    local c121BelowTarget = C121_AIR_ECONOMICS && ("targetAirPlanes" in line)
        && line.targetAirPlanes > have;
    local belowTarget = c84BelowTarget || c121BelowTarget;
    local c121StockGrowth = 0;
    local c121FirstLiveEntry = false;
    if (c121BelowTarget && C121_FLEET_STOCK_GROWTH) {
      /* Variante AAAHogEx (route.nut:2904-2915) : la preuve d'une demande non servie est
       * le stock en gare, pas une annee d'observation. Un renfort au plus tous les 60 jours
       * pour laisser le nouvel avion agir sur le stock. */
      if (("lastAirFleetDate" in line)
          && AIDate.GetCurrentDate() - line.lastAirFleetDate < 60) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_stock_cooldown", 1);
        continue;
      }
      c121StockGrowth = OpexC121FleetStockEvidence(line);
      if (c121StockGrowth < 1) {
        OpexAirFleetRefusal(line, year, "W");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_low_stock", 1);
        continue;
      }
    } else if (c121BelowTarget && C121_AIR_OBSERVATION_GROWTH) {
      /* Variante distincte du stock-growth : la cible reste seulement une borne
       * et le portefeuille continue d'arbitrer le +1. On accepte le dernier
       * rapport annuel reel des que la ligne a traverse un changement d'annee,
       * mais une meme observation ne peut financer qu'un seul renfort. La cadence
       * AIR_FLEET_CADENCE_DAYS ci-dessus reste applicable. */
      local c121Age = ("year" in line) ? year - line.year : -1;
      local reportYear = this._lastReportYear;
      if (reportYear != year || c121Age < 1
          || !("lastProfit" in line) || line.lastProfit <= 0) {
        OpexAirFleetRefusal(line, year, "O");
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "c121_no_positive_annual_observation", 1);
        continue;
      }
      if (("c121GrowthReportYear" in line) && line.c121GrowthReportYear == reportYear) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "c121_observation_already_consumed", 1);
        continue;
      }
    } else if (c121BelowTarget && C121_AIR_FIRST_LIVE_GROWTH
        && (C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0
            || year - OPEX_START_YEAR < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS)
        && have == 1 && !("lastAirFleetYear" in line)) {
      /* C121 cadence live : seul 1->2 est avance, sur preuve d'exploitation
       * recente deja agregee passivement par C117. Le projet reste un +1 normal
       * et passe ensuite par exactement le meme portefeuille/financement.
       * IMPORTANT : le signal live est uniquement un raccourci. S'il n'est pas
       * pret, la garde C121 historique reprend la main a deux ans ; cette
       * experience ne doit jamais retarder un 1->2 que le baseline accepterait. */
      if (!OpexC121FirstLiveBalanced90(line)) {
        local c121Age = ("year" in line) ? year - line.year : -1;
        if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0) {
          OpexAirFleetRefusal(line, year, "O");
          if (plan != null && C69_BOTTLENECK_PROBE)
            OpexC73RecordRejection("fleet", "c121_first_live_not_ready", 1);
          continue;
        }
      }
      c121FirstLiveEntry = true;
    } else if (c121BelowTarget && C121_AIR_FIRST_OBSERVATION_GROWTH
        && have == 1 && !("lastAirFleetYear" in line)) {
      /* Experience cadence isolee : seul le passage 1->2 est avance. Le projet
       * reste un +1 C121 normal et passe par le meme portefeuille ; aucun autre
       * renfort n'utilise cette garde. */
      local c121Age = ("year" in line) ? year - line.year : -1;
      local reportYear = this._lastReportYear;
      local c121AgeDays = ("buildDate" in line) ? AIDate.GetCurrentDate() - line.buildDate : -1;
      local c121FirstGrowthMinDays = C121_AIR_FIRST_GROWTH_MIN_DAYS;
      if (C121_AIR_FIRST_GROWTH_PHASE_YEARS > 0
          && year - OPEX_START_YEAR >= C121_AIR_FIRST_GROWTH_PHASE_YEARS) {
        c121FirstGrowthMinDays = C121_AIR_FIRST_GROWTH_LATE_DAYS;
      }
      if (c121FirstGrowthMinDays > 0
          && (c121AgeDays < 0 || c121AgeDays < c121FirstGrowthMinDays)) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "c121_first_growth_too_young", 1);
        continue;
      }
      if (reportYear != year || c121Age < 1
          || !("lastProfit" in line) || line.lastProfit <= 0) {
        OpexAirFleetRefusal(line, year, "O");
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "c121_first_growth_no_positive_observation", 1);
        continue;
      }
      if (C121_AIR_FIRST_GROWTH_MIN_WAIT_PCT > 0) {
        local firstCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
        if (firstCap <= 0 && ("vehicles" in line)) {
          foreach (v in line.vehicles) {
            if (!AIVehicle.IsValidVehicle(v)) continue;
            firstCap = AIVehicle.GetCapacity(v, line.cargo);
            if (firstCap > 0) break;
          }
        }
        local stA = AIStation.GetStationID(line.stationA);
        local hasB = ("stationB" in line) && line.stationB != null;
        local stB = hasB ? AIStation.GetStationID(line.stationB) : -1;
        local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
        local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
        local maxWait = waitA > waitB ? waitA : waitB;
        if (firstCap <= 0 || maxWait * 100 < firstCap * C121_AIR_FIRST_GROWTH_MIN_WAIT_PCT) {
          OpexAirFleetRefusal(line, year, "W");
          if (plan != null && C69_BOTTLENECK_PROBE)
            OpexC73RecordRejection("fleet", "c121_first_growth_low_wait", 1);
          continue;
        }
      }
    } else if (c121BelowTarget) {
      /* Une mesure annuelle complete est le premier feedback fiable apres le
       * cold-start C121. Ne jamais acheter plusieurs renforts sur la meme
       * observation : une nouvelle annee doit confirmer le palier suivant. */
      local c121Age = ("year" in line) ? year - line.year : -1;
      if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0) {
        OpexAirFleetRefusal(line, year, "O");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_no_full_year_observation", 1);
        continue;
      }
      if (("lastAirFleetYear" in line) && (year - line.lastAirFleetYear) < 2) {
        OpexAirFleetRefusal(line, year, "Y");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_wait_full_year_after_growth", 1);
        continue;
      }
    }
    if (("deadStreak" in line) && line.deadStreak >= 2) {
      OpexAirFleetRefusal(line, year, "D");
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "dead_line", 1);
      continue;
    }

    // Condition 1 : Les appareils existants ne doivent pas etre deficitaires
    if (!belowTarget && ("lastProfit" in line) && line.lastProfit < 0) {
      OpexAirFleetRefusal(line, year, "L");
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "negative_profit", 1);
      continue;
    }

    if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE && AIR_FLEET_BUFFER < 0) {}
    local isSmallAirport = false;
    if ((AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
        (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL)) {
      isSmallAirport = true;
    }
    local physicalMaxPlanes = isSmallAirport ? 4 : AIR_MAX_PLANES_PER_ROUTE;
    if (AIR_CADENCE_CAP) {
      physicalMaxPlanes = OpexAirCadenceCap(line, this._catalog, this._lines);
    }
    if (have >= physicalMaxPlanes) { OpexAirFleetRefusal(line, year, "C"); if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "airport_capacity_reached", 1); continue; }
    local maxPlanesForAirport = physicalMaxPlanes;
    if (OPEX_AIR_CAP_PAD) maxPlanesForAirport = maxPlanesForAirport;
    if (!belowTarget && ("deadStreak" in line) && line.deadStreak >= 1) { OpexAirFleetRefusal(line, year, "S"); if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "poor_health_streak", 1); continue; }
    if (!belowTarget && ("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "negative_profit", 1); continue; }

    local planePrice = (this._catalog.plane != null) ? this._catalog.plane.price : 30000;
    if ((OPEX_ECONOMY_OPCODE_COMPAT_FALSE || AIR_FLEET_LINE_PRICE) && ("vehicles" in line)) {
      foreach (v in line.vehicles) {
        if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
        local ownPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
        if (ownPrice > 0) planePrice = ownPrice;
        break;
      }
    }
    /* Croissance d'une ligne aerienne EXISTANTE : aucun aeroport a batir, donc rien que
     * cette marge doive couvrir. 88 refus insufficient_cash pour 3 acceptations mesures
     * sur 3 parties x 2 ans (results/diag_1v1_decisions.json). */
    local need = planePrice + OpexCashReserve() + 2000;
    local addedThisPass = 0;
    local maxAddedPerPass = OPEX_ECONOMY_OPCODE_COMPAT_FALSE ? 1 : 4;
    /* C14 : Dimensionnement dynamique de flotte par le stock au sol (AAAHogEx route.nut:2896-2921).
     * Si AIR_FLEET_BUFFER >= 0 : calcule buildNum = (maxWait - bottom) / capacity.
     * Si buildNum < 1 : refus W (pas assez de cargo au sol).
     * Sinon : autorise jusqu'a buildNum (c69_fleet_demand_batch) ou min(buildNum, 4) par defaut. */
    if (c121BelowTarget) {
      /* C121 dimensionne sur flux + rating : attendre une capacite entiere au
       * sol cree une boucle morte (faible frequence -> faible rating -> faible
       * stock). Le portefeuille arbitre donc un seul renfort a la fois jusqu'a
       * la cible, avec le marginal C121 compact publie sur la ligne. */
      maxAddedPerPass = c121StockGrowth > 0 ? (c121StockGrowth < 4 ? c121StockGrowth : 4) : 1;
    } else if (AIR_FLEET_BUFFER >= 0) {
      local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
      if (planeCap <= 0 && ("vehicles" in line)) {
        foreach (v in line.vehicles) {
          if (AIVehicle.IsValidVehicle(v)) {
            planeCap = AIVehicle.GetCapacity(v, line.cargo);
            if (planeCap > 0) { line.planeCapacity <- planeCap; break; }
          }
        }
      }
      local stA = AIStation.GetStationID(line.stationA);
      local hasB = ("stationB" in line) && line.stationB != null;
      local stB = hasB ? AIStation.GetStationID(line.stationB) : 0;
      local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
      local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
      local maxWait = (waitA > waitB) ? waitA : waitB;

      local bottom = (AIR_FLEET_BUFFER < planeCap) ? AIR_FLEET_BUFFER : planeCap;
      local buildNum = 0;
      if (maxWait > bottom && planeCap > 0) {
        buildNum = (maxWait - bottom) / planeCap;
      }
      if (buildNum < 1) {
        OpexAirFleetRefusal(line, year, "W");
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "low_stock_buffer", 1);
        continue;
      }
      maxAddedPerPass = C69_FLEET_DEMAND_BATCH ? buildNum : ((buildNum < 4) ? buildNum : 4);
    }
    if (belowTarget) {
      local targetNeed = line.targetAirPlanes - have;
      if (targetNeed > 0 && maxAddedPerPass > targetNeed) maxAddedPerPass = targetNeed;
    }
    if (plan != null) {
      /* Mode a blanc : on ne touche ni a la tresorerie ni a la ligne. Le test de capital est celui
       * du portefeuille, pas celui d'ici -- c'est tout l'objet de l'arbitrage. */
      local room = maxPlanesForAirport - have;
      local want = (room < maxAddedPerPass) ? room : maxAddedPerPass;
      if (want > 0) {
        local fleetEntry = { line = line, want = want, planePrice = planePrice, baseVehicles = have };
        if (c121FirstLiveEntry) fleetEntry.c121FirstLive <- true;
        if (c84BelowTarget) {
          /* R1 : seuls les cargos sont lus par le modele marginal. Cette
           * petite vue transitoire permet de recalculer une tranche finançable. */
          fleetEntry.c84Catalog <- { paxCargo = this._catalog.paxCargo,
              mailCargo = ("mailCargo" in this._catalog) ? this._catalog.mailCargo : -1 };
          local marginal = OpexAirExistingLineMarginalEconomics(this._catalog, line, have, want);
          if (marginal != null) {
            fleetEntry.c84MarginalProfit <- marginal.profitAnnual;
            fleetEntry.c84MarginalRevenue <- marginal.revenueAnnual;
          }
        }
        plan.append(fleetEntry);
        if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (!("c50_want_ym" in line) || line.c50_want_ym != ym) {
            line.c50_want_ym <- ym;
            C50_NON_EXPANSION_LEDGER.air.want_sum += want;
          }
        }
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("fleet", "no_room", 1);
      }
      continue;
    }
    while (have < maxPlanesForAirport && addedThisPass < maxAddedPerPass) {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need) { OpexAirFleetRefusal(line, year, "M"); break; }
      local grown = OpexAirAddPlane(line, this._catalog, this._lines);
      if (("reason" in grown) && (grown.reason == "REEEQUIP_WAIT" || grown.reason == "REPLACE" || grown.reason == "REEEQUIP_FAIL" || grown.reason == "REEEQUIP_ABORT")) {
        if (grown.reason == "REPLACE" && ("vehCount" in grown)) {
          have = grown.vehCount;
          line.vehCount <- have;
          line.trains = have;
        }
        break;
      }
      if (grown.added <= 0) { OpexAirFleetRefusal(line, year, "X"); break; }
      have += grown.added;
      addedThisPass += grown.added;
      line.vehCount <- have;
      line.trains = have;
    }
    if (addedThisPass > 0) {
      line.lastAirFleetYear <- year;
      line.lastAirFleetDate <- AIDate.GetCurrentDate();
      if (C121_AIR_OBSERVATION_GROWTH && c121BelowTarget) {
        line.c121GrowthReportYear <- this._lastReportYear;
      }
      if (DECISION_LOG) {
        local yieldVal = OpexAirFleetYield(line);
        OpexDecide("AIR_FLEET", "action=grow line=" + line.lineId + " yield=" + yieldVal + " planes_before=" + (have - addedThisPass) + " planes_after=" + have + " added=" + addedThisPass);
      }
      AILog.Info("[AIR_FLEET] line=" + line.lineId + " added=" + addedThisPass + " total=" + have);
      OpexSign(AIMap.GetTileIndex(1, 10 + line.lineId), "FG|" + (year % 100) + "|" + line.lineId + "|" + have + "|K");
    }
  }
  if (spFleet != null) OpexSpanEnd(spFleet);
  return true;
}
