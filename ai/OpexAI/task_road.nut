/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C38 etape 2 : tentative synchrone route, y compris le siting vivant. */
function OpexAI::_tryBuildRoadProject(year, project, rank, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = project.src, dst = project.dst, reason = "road_disabled", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local candidate = project.payload;

      local isSubsidy = ("isSubsidy" in candidate) && candidate.isSubsidy;
      if (isSubsidy) {
        local subId = candidate.subsidyId;
        local today = AIDate.GetCurrentDate();
        local oneWay = ("oneWayDays" in candidate) ? candidate.oneWayDays : -1;
        // Au moment de la construction immediate, la latence d'attente de cycle de batch (30j) est deja ecoulee
        local chantier = ("chantierDays" in candidate)
            ? (candidate.chantierDays - 30) : (OpexSubsidyChantierDays(oneWay) - 30);
        if (chantier < 30) chantier = 30;
        if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)
            || (AISubsidy.GetExpireDate(subId) - today < chantier)) {
          if (DECISION_LOG) {
            OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road reason=subsidy_lost sub=" + subId);
          }
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          this._purgeSubsidyFromProjects(subId);
          this._portfolioInvalidated = true;
          this._hadAbandonsThisPass = true;
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local towns = OpexGetCandidateTownEndpoints(candidate);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("road", "build_precheck", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("road", "build_precheck", towns.dstTown);
      }
      if (candidate.kind == "pax") {
        /* Dernier verrou contre un candidat cache : des qu'une des communes a recu une ligne bus,
         * sa croissance passe exclusivement par une extension de cette ligne. */
        if (!((("road100MultiCatchment" in candidate) && candidate.road100MultiCatchment)
              && ROAD100_MULTICATCHMENT)
            && ((towns.srcTown >= 0 && OpexTownBusPaxServed(this._lines, towns.srcTown)) ||
                (towns.dstTown >= 0 && OpexTownBusPaxServed(this._lines, towns.dstTown)))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
            passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
                                  reason = "town_already_bus_served", extra = "" });
          }
          /* ROAD100-25b : le veto est fonde sur les lignes LIVE, pas sur une
           * faillite de la paire. Demander une reelection en fin de passe
           * (sans tombstone persistant ni faux bump de revision `lines`) :
           * le filtre LIVE de la selection retirera la tete perimee. */
          if (ROAD100_PAX_LIVE_FILTER) this._hadAbandonsThisPass = true;
          return { outcome = "rejected", discards = passDiscards };
        }
        local alreadyServed = OpexRoadPairServed(this._lines, candidate.src, candidate.dst);
        if (alreadyServed) {
          if (DECISION_LOG || C63_INVEST_PROBE
              || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "pair_already_served", extra = "" });
          local abandonedKey = OpexAbandonedPairKey(candidate);
          this._markPairAbandoned(abandonedKey);
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexTownRoadLineCount(this._lines, candidate.src) >= 4) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexTownRoadLineCount(this._lines, candidate.dst) >= 4) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else {
        if ((ROAD100_FREIGHT_CARGO_ORIGIN && V276_CAND_SLICES <= 0
                ? OpexRoadFreightOriginServedCargo(this._lines, candidate.src, candidate.cargo)
                : OpexOriginServed(this._lines, candidate.src, true))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "src_origin_served", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if ((ROAD100_FREIGHT_CARGO_ORIGIN && V276_CAND_SLICES <= 0
                ? OpexRoadFreightOriginServedCargo(this._lines, candidate.dst, candidate.cargo)
                : OpexOriginServed(this._lines, candidate.dst, true))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "dst_origin_served", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if ((abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local need = candidate.capital + ROAD_CAPITAL_MARGIN;
      if ((ESTIM_UNIFIE & 2) != 0)
        need = OpexEstimFinanceCapital("road", candidate.capital, candidate.distance,
            ("capitalIsActual" in candidate) && candidate.capitalIsActual,
            ("immobilise" in candidate) ? candidate.immobilise : 0);
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("road", i, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE
            || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|R|" + project.budgetScore + "|" + project.opcodeScore);

      this._budget.begin();
      local planning = OpexRoadPlanFor(this._catalog, candidate);
      local planOps = this._budget.end("build_road_plans");
      local plan = planning.plan;
      local idx = this._nextLineId;
      if (plan == null) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({
          rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
          reason = "plan_failed", detail = planning.reason, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=plan_failed detail=" + planning.reason);
        }
        this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
        OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      /* ROAD100-20e : eviter le second inventaire natif de quartiers si la
       * geometrie et le type routier n'ont PAS change depuis generation.
       * Le constructeur refait les AITest, la connectivite, la couverture
       * marginale et les controles de caisse APRES pose des racines.
       * Tout changement de facade ou de plan force la relecture complete. */
      if (ROAD100_PAX_PORTFOLIO && ("road100PaxPortfolio" in candidate)
          && candidate.road100PaxPortfolio && candidate.kind == "pax") {
        local portfolioLive = null;
        local savedPreview = ("road100PaxPortfolioPreview" in candidate)
            ? candidate.road100PaxPortfolioPreview : null;
        local previewCacheHit = savedPreview != null && savedPreview.ok &&
            ("siteA" in savedPreview) && ("siteB" in savedPreview) &&
            ("frontA" in savedPreview) && ("frontB" in savedPreview) &&
            ("roadType" in savedPreview) &&
            savedPreview.siteA == plan.stopA.tile &&
            savedPreview.siteB == plan.stopB.tile &&
            savedPreview.frontA == plan.stopA.front &&
            savedPreview.frontB == plan.stopB.front &&
            savedPreview.roadType == this._catalog.roadType;
        if (previewCacheHit) portfolioLive = savedPreview;
        else portfolioLive = OpexRoad100PaxPortfolioPreview(this._catalog,
                candidate, plan);
        plan.road100PortfolioPreview <- portfolioLive;
        candidate.road100PaxPortfolioPreview <- portfolioLive;
        if (DECISION_LOG && portfolioLive != null)
          OpexDecide("ROAD100_PAX_PORTFOLIO",
              "phase=recheck src=" + candidate.src + " dst=" + candidate.dst
              + " union=" + portfolioLive.monthly
              + " marginal_a=" + portfolioLive.marginalA
              + " marginal_b=" + portfolioLive.marginalB
              + " ops=" + (previewCacheHit ? 0 : portfolioLive.ops)
              + " cached=" + (previewCacheHit ? 1 : 0)
              + " reason=" + portfolioLive.reason);
      }
      if (("road100SiteFirst" in candidate) && candidate.road100SiteFirst && DECISION_LOG) {
        local initialA = ("road100GenSiteA" in candidate) ? candidate.road100GenSiteA : -1;
        local initialB = ("road100GenSiteB" in candidate) ? candidate.road100GenSiteB : -1;
        local initialDepot = ("road100GenDepot" in candidate) ? candidate.road100GenDepot : -1;
        local latestA = plan.stopA.tile;
        local latestB = plan.stopB.tile;
        OpexDecide("ROAD100_PLAN_DRIFT", "src=" + candidate.src + " dst=" + candidate.dst
            + " genA=" + initialA + " genB=" + initialB + " genDepot=" + initialDepot
            + " liveA=" + latestA + " liveB=" + latestB + " liveDepot=" + plan.depot.tile
            + " frontA=" + plan.stopA.front + " frontB=" + plan.stopB.front
            + " changed=" + ((initialA != latestA || initialB != latestB
                               || initialDepot != plan.depot.tile) ? 1 : 0)
            + " route=" + plan.routeDistance + " planOps=" + planOps);
      }
      local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
      if (actualDist < 1) actualDist = 1;
      if ((("road100IntercitySiteFleet" in candidate) && candidate.road100IntercitySiteFleet)
          || (("road100SiteFirst" in candidate) && candidate.road100SiteFirst)) {
        /* La production reelle au rayon de couverture des DEUX sites remplace
         * la demande totale des villes avant tout achat de vehicule. */
        local hasSiteDemand = ("value" in plan.stopA) && ("value" in plan.stopB)
            && plan.stopA.value != null && plan.stopB.value != null;
        /* V27 MAIL : un quai B qui ACCEPTE 8/8 ne produit pas
         * huit sacs de courrier. Le revenu initial est 100% A->B. */
        local siteDemand = hasSiteDemand ? plan.stopA.value + plan.stopB.value : -1;
        if (("road100SegmentedUnits" in candidate) &&
            candidate.road100SegmentedUnits && ROAD100_SEGMENTED_CORRIDOR) {
          local radius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
          local aUnits = OpexRoad100PaxSiteMonthly(candidate.srcTown,
              candidate.cargo, plan.stopA.tile, radius);
          local bUnits = OpexRoad100PaxSiteMonthly(candidate.dstTown,
              candidate.cargo, plan.stopB.tile, radius);
          siteDemand = aUnits.monthly + bUnits.monthly;
          if (DECISION_LOG) OpexDecide("ROAD100_SEGMENTED",
              "phase=live root_monthly_a=" + aUnits.monthly
              + " root_monthly_b=" + bUnits.monthly
              + " producers_a=" + aUnits.siteProducers
              + " producers_b=" + bUnits.siteProducers
              + " ops=" + (aUnits.ops + bUnits.ops));
        }
        if ((("road100SparseUnits" in candidate) &&
             candidate.road100SparseUnits && ROAD100_SPARSE_CORRIDOR) ||
            (("road100GraphRequested" in candidate) &&
             candidate.road100GraphRequested && ROAD100_PAX_GRAPH_BRIDGE) ||
            (("road100LongUnits" in candidate) &&
             candidate.road100LongUnits)) {
          local sparseRadius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
          local sparseA = OpexRoad100PaxSiteMonthly(candidate.srcTown,
              candidate.cargo, plan.stopA.tile, sparseRadius);
          local sparseB = OpexRoad100PaxSiteMonthly(candidate.dstTown,
              candidate.cargo, plan.stopB.tile, sparseRadius);
          siteDemand = sparseA.monthly + sparseB.monthly;
          if (DECISION_LOG) OpexDecide(
              ("road100GraphRequested" in candidate) && candidate.road100GraphRequested
                  ? "ROAD100_GRAPH" : "ROAD100_SPARSE",
              "phase=live root_monthly_a=" + sparseA.monthly
              + " root_monthly_b=" + sparseB.monthly
              + " producers_a=" + sparseA.siteProducers
              + " producers_b=" + sparseB.siteProducers
              + " ops=" + (sparseA.ops + sparseB.ops));
        }
        if (("road100PaxProducerUnits" in candidate) && candidate.road100PaxProducerUnits) {
          /* Reviser la meme estimation que la generation et le preflight,
           * depuis les VRAIES stations candidates et les donnees LIVE.
           * Un plan sans re-calcul dimensionnel est refuse, pas reinterprete
           * en PASS/mois. Le scoring OFF n'entre jamais ici. */
          siteDemand = ("road100PaxUnitsMonthly" in plan)
              ? plan.road100PaxUnitsMonthly : -1;
          if (DECISION_LOG && siteDemand >= 0) {
            local a = plan.road100PaxUnitA;
            local b = plan.road100PaxUnitB;
            OpexDecide("ROAD100_PAX_UNITS",
                "phase=live src_town=" + candidate.srcTown
                + " dst_town=" + candidate.dstTown
                + " producers_a=" + a.siteProducers + " producers_b=" + b.siteProducers
                + " producers_total_a=" + a.townProducers
                + " producers_total_b=" + b.townProducers
                + " city_monthly_a=" + a.townMonthly
                + " city_monthly_b=" + b.townMonthly
                + " site_monthly_a=" + a.monthly + " site_monthly_b=" + b.monthly
                + " ops=" + (a.ops + b.ops));
          }
        }
        if (("road100MailIntertown" in candidate) && candidate.road100MailIntertown) {
          /* Le marché source est mesuré à nouveau sous le snapshot LIVE,
           * avec toute station propre construite depuis le PO01C. */
          siteDemand = hasSiteDemand
              ? OpexRoad100MailMarginalSource(candidate.cargo, plan.stopA.tile,
                  OpexRoad100MailOwnedCoverage()) : -1;
          if (plan.vehType != AIRoad.ROADVEHTYPE_TRUCK ||
              plan.stationType != AIStation.STATION_TRUCK_STOP ||
              plan.stopB.value < ROAD_ACCEPTANCE_FULL_UNIT) siteDemand = -1;
        }
        if (DECISION_LOG) {
          OpexDecide("ROAD100_SITE_FLEET", "phase=site src=" + candidate.src
              + " dst=" + candidate.dst + " town_a=" + candidate.srcTown
              + " town_b=" + candidate.dstTown + " initial_monthly=" + candidate.monthly
              + " site_monthly=" + siteDemand + " plan_ops=" + planOps);
        }
        if (siteDemand <= 0) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
            passDiscards.append({ rank = i, mode = "road", src = candidate.src,
                dst = candidate.dst, reason = "road100_site_no_demand", extra = "" });
          this._markPairAbandoned(abandonedKey);
          return { outcome = "rejected", discards = passDiscards };
        }
        candidate.monthly = siteDemand;
      }
      local economics = OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,
                                              candidate.monthly, candidate.engine, candidate.kind,
                                              plan.routeDistance,
                                              ("road100FleetCap" in candidate) ? candidate.road100FleetCap : 0);
      if (("road100MailLongExisting" in candidate) && candidate.road100MailLongExisting)
        economics = OpexRoad100MailExistingEconomics(this._catalog, economics, plan);
      if (("road100LongBuild" in candidate) && candidate.road100LongBuild)
        economics = OpexRoad100LongQuotedEconomics(this._catalog, economics, plan);
      if (EQUIPMENT_ROI_PROBE) {
        OpexM3ProbeRoadEquipment(this._catalog, candidate, actualDist, plan.routeDistance,
                                 economics, "post_route");
      }
      if (economics == null || economics.profitAnnual <= 0) {
        if (C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "unprofitable_after_siting", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=unprofitable_after_siting");
        }
        this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|ECON|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      if (ROAD100_MAIL_LONG_EXISTING
          && ("road100MailIntertown" in candidate) && candidate.road100MailIntertown
          && (economics.profitAnnual < 3000 || economics.roi < 250)) {
        if (DECISION_LOG) OpexDecide("ROAD100_MAIL",
            "phase=reject reason=PROFIT_GUARD profit=" + economics.profitAnnual
            + " roi=" + economics.roi + " src=" + candidate.src
            + " dst=" + candidate.dst);
        return { outcome = "rejected", discards = passDiscards };
      }
      if ((("road100IntercitySiteFleet" in candidate) && candidate.road100IntercitySiteFleet)
          || (("road100SiteFirst" in candidate) && candidate.road100SiteFirst)) {
        local siteNeed = OpexEstimFinanceCapital("road", economics.capital, actualDist,
                                                 false, economics.immobilise);
        local available = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        local physicalSlots = OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, economics.trains);
        local cashMargin = (("road100LongBuild" in candidate) && candidate.road100LongBuild)
            ? 50000 : 25000;
        local siteOK = available >= siteNeed + cashMargin && physicalSlots;
        if (("road100LongBuild" in candidate) && candidate.road100LongBuild) {
          if (!("road100LongCashNeed" in plan) ||
              available < plan.road100LongCashNeed) siteOK = false;
        }
        if (DECISION_LOG) {
          OpexDecide("ROAD100_SITE_FLEET", "phase=finance src=" + candidate.src
              + " dst=" + candidate.dst + " monthly=" + candidate.monthly
              + " raw_vehs=" + economics.vehiclesForVolume
              + " selected_vehs=" + economics.trains
              + " profit=" + economics.profitAnnual + " capital=" + economics.capital
              + " finance=" + siteNeed + " cash=" + available
              + " action=" + (siteOK ? "keep" : "reject"));
        }
        if (!siteOK) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
            passDiscards.append({ rank = i, mode = "road", src = candidate.src,
                dst = candidate.dst, reason = "road100_site_finance", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      /* ROAD100-5 : economie nette REVALIDEE apres selection des deux arrets
       * et du trajet, mais avant de construire la moindre tuile. */
      if (ROAD100_TOWN_ROI_POST && candidate.kind == "pax"
          && candidate.srcTown >= 0 && candidate.srcTown == candidate.dstTown) {
        local estimatedPermille = economics.capital > 0
            ? (economics.profitAnnual * 1000) / economics.capital : 0;
        local passRoi = economics.capital > 0 && estimatedPermille >= 250;
        if (DECISION_LOG) {
          OpexDecide("ROAD100_TOWN_ROI", "src=" + candidate.src + " dst=" + candidate.dst
              + " profit=" + economics.profitAnnual + " capital=" + economics.capital
              + " roi_permille=" + estimatedPermille
              + " action=" + (passRoi ? "keep" : "reject"));
        }
        if (!passRoi) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
            passDiscards.append({ rank = i, mode = "road", src = candidate.src,
                dst = candidate.dst, reason = "road100_town_roi_post", extra = "" });
          }
          this._markPairAbandoned(abandonedKey);
          OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|ROI|0");
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      OpexApplyRoadEconomics(candidate, economics, actualDist);
      if (("road100SiteFirst" in candidate) && candidate.road100SiteFirst) {
        candidate.immobilise = economics.immobilise;
        candidate.iterations = OpexRoadIterations(actualDist);
        candidate.ratio = (economics.profitAnnual * 1000) / candidate.iterations;
      }

      if (isSubsidy) {
        candidate.baseRevenueAnnual = economics.revenueAnnual;
        candidate.baseProfitAnnual = economics.profitAnnual;
        candidate.baseRoi = economics.roi;
        local mult = ("effectiveMultiplier" in candidate)
            ? candidate.effectiveMultiplier
            : (("subsidyMultiplier" in candidate) ? candidate.subsidyMultiplier : 1.0);
        local subRev = (economics.revenueAnnual * mult).tointeger();
        local subProfit = subRev - economics.runningAnnual - economics.amortAnnual;
        local freightBonus = ("freightBonus" in candidate) ? candidate.freightBonus : 100;
        local subRoi = (subProfit > 0 && candidate.capital > 0) ? (subProfit * 1000) / candidate.capital : 0;
        if (freightBonus != 100) subRoi = (subRoi * freightBonus) / 100;

        candidate.subsidyRevenueAnnual = subRev;
        candidate.subsidyProfitAnnual = subProfit;
        candidate.subsidyRoi = subRoi;

        // Le candidat actif utilise l'economie subventionnee pour sa premiere annee
        candidate.revenueAnnual = subRev;
        candidate.profitAnnual = subProfit;
        candidate.roi = subRoi;
      }
      if (isSubsidy) {
        local subId = candidate.subsidyId;
        if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)) {
          if (DECISION_LOG) {
            OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road reason=subsidy_lost_during_planning sub=" + subId);
          }
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          this._purgeSubsidyFromProjects(subId);
          this._portfolioInvalidated = true;
          this._hadAbandonsThisPass = true;
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
      if (DECISION_LOG && ("road100SiteFirst" in candidate) && candidate.road100SiteFirst) {
        OpexDecide("ROAD100_REPRICE", "src=" + candidate.src + " dst=" + candidate.dst
            + " gen_capital=" + project.capital + " live_capital=" + candidate.capital
            + " actual_paid=" + result.actualCost + " game_cash="
            + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
            + " gen_profit=" + project.profitAnnual + " live_profit=" + candidate.profitAnnual
            + " gen_vehicles=" + project.selectedRoadVehicles + " live_vehicles=" + candidate.trains
            + " bought=" + result.vehicles.len() + " build_ops=" + result.opcodes
            + " ok=" + (result.ok ? 1 : 0) + " reason=" + result.reason
            + " error=" + result.error);
      }

      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("road", result, candidate.capital);
      OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|" + result.opcodes);
      if (ROAD_COST_PROBE) {
        OpexSign(anchor, "RP|" + idx + "|" + result.plannedCapital + "|" + result.actualCost
                               + "|" + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({
          rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
          reason = "build_failed", detail = result.reason, error = result.error, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
        return { outcome = "rejected", discards = passDiscards };
      }

      if (DECISION_LOG) {
        foreach (d in passDiscards) {
          OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
        }
        passDiscards = [];
        local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
        local extraSub = (isSubsidy && ("baseProfitAnnual" in candidate))
            ? (" base_profit=" + candidate.baseProfitAnnual + " base_roi=" + candidate.baseRoi
               + " mult=" + candidate.subsidyMultiplier
               + (("subsidyDuration" in candidate) ? (" dur=" + candidate.subsidyDuration) : "")
               + (("slackDays" in candidate) ? (" slack=" + candidate.slackDays) : ""))
            : "";
        local fleetDiag = ("vehiclesForVolume" in candidate)
            ? (" raw_vehs=" + candidate.vehiclesForVolume
               + " berth_cap=" + (("roadBerthCapacity" in candidate) ? candidate.roadBerthCapacity
                                  : OpexRoadPhysicalVehicleCap(1, 1))
               + " fleet_cap=" + (("roadVehicleCap" in candidate) ? candidate.roadVehicleCap : candidate.trains)
               + " capped_vehs=" + candidate.trains)
            : "";
        OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=road kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi + fleetDiag + extraSub);
        OpexDecide("ROAD_BUILD", "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + result.cost + " vehicles=" + result.vehicles.len());
      }

      OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
      OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
      OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
      OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains);
      OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays + "|" + candidate.distance);
      OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                               + "|" + candidate.monthly);
      OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
      OpexSign(anchor, "PM|" + idx + "|R|" + candidate.distance + "|"
                               + AICargo.GetCargoLabel(candidate.cargo));
      OpexSign(anchor, "RC|" + yy + "|" + idx + "|1|" + result.cost
                               + "|" + result.vehicles.len());
      if (C56_TASK_TRACE) {
        OpexC56TaskLog("ROAD_BUILT", candidate.kind, "-",
                       "line=" + idx + " cost=" + candidate.capital + " dist=" + candidate.distance
                       + " veh=" + result.vehicles.len() + " profit=" + candidate.profitAnnual);
      }
      OpexAir0310InvalidateSiteValidity();
      this._lines.append({
        stationA = result.stopA, stationB = result.stopB,
        originA = candidate.src, originB = candidate.dst,
        cargo = candidate.cargo,
        predicted = candidate.profitAnnual, iterations = candidate.iterations,
        trains = result.vehicles.len(), trains0 = result.vehicles.len(), distance = candidate.distance, year = year,
        predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
        predAmort = candidate.amortAnnual, predCarried = candidate.carried,
        predVehiclesForVolume = ("vehiclesForVolume" in candidate) ? candidate.vehiclesForVolume : candidate.trains,
        predRoadBerthCapacity = ("roadBerthCapacity" in candidate) ? candidate.roadBerthCapacity
                               : OpexRoadPhysicalVehicleCap(1, 1),
        predRoadVehicleCap = ("roadVehicleCap" in candidate) ? candidate.roadVehicleCap : candidate.trains,
        predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
        effectiveSpeed = candidate.effectiveSpeed,
        catalogSpeed = candidate.engine.speed,
        bridges = ("bridges" in result && result.bridges != null) ? result.bridges : [],
        mode = "road", kind = candidate.kind, depot = result.depot,
        nStopsA = result.nStopsA, nStopsB = result.nStopsB,
        capacity = ("capacity" in result) ? result.capacity : 25,
        srcTown = ("srcTown" in candidate) ? candidate.srcTown : -1,
        dstTown = ("dstTown" in candidate) ? candidate.dstTown : -1,
        srcIndustry = (candidate.kind == "freight" && candidate.srcTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.src) : -1,
        dstIndustry = (candidate.kind == "freight" && candidate.dstTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.dst) : -1,
        deadStreak = 0, scrapping = false, scrapVehicles = [],
        isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
        opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
        purpose = "profit",
        isSubsidy = (("isSubsidy" in candidate) && candidate.isSubsidy),
        subsidyId = (("subsidyId" in candidate) ? candidate.subsidyId : -1),
        baseProfit = (isSubsidy && ("baseProfitAnnual" in candidate)) ? candidate.baseProfitAnnual : candidate.profitAnnual,
        baseRevenue = (isSubsidy && ("baseRevenueAnnual" in candidate)) ? candidate.baseRevenueAnnual : candidate.revenueAnnual,
        subsidyProfit = (isSubsidy && ("subsidyProfitAnnual" in candidate)) ? candidate.subsidyProfitAnnual : candidate.profitAnnual,
        subsidyRevenue = (isSubsidy && ("subsidyRevenueAnnual" in candidate)) ? candidate.subsidyRevenueAnnual : candidate.revenueAnnual,
        subsidyMultiplier = (isSubsidy && ("subsidyMultiplier" in candidate)) ? candidate.subsidyMultiplier : 1.0,
        lineId = idx,
      });
      if (("road100PaxInitialBays" in result) &&
          result.road100PaxInitialBays != null)
        this._lines[this._lines.len() - 1].rawset(
            "road100PaxInitialBays", result.road100PaxInitialBays);
      if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;
      if (("isSubsidy" in candidate) && candidate.isSubsidy) {
        if (this._activeSubsidies != null && (candidate.subsidyId in this._activeSubsidies)) {
          delete this._activeSubsidies[candidate.subsidyId];
        }
        this._purgeSubsidyFromProjects(candidate.subsidyId);
        if (DECISION_LOG) {
          OpexDecide("C42_SUBSIDY_BUILD", "line=" + idx + " sub=" + candidate.subsidyId
                     + " cargo=" + AICargo.GetCargoLabel(candidate.cargo)
                     + " mult=" + (("subsidyMultiplier" in candidate) ? candidate.subsidyMultiplier : 1));
        }
      }
      this._nextLineId++;
      this._c76BumpLayer("lines", false);
      return { outcome = "built", discards = passDiscards };

  return { outcome = "rejected", discards = passDiscards };
}
/* Une ligne routiere a zero (ou trop peu de) vehicules avec arrets et depot encore la :
 * l'infrastructure est payee, auto-renouvellement n'a pas suivi. Mesure, plusieurs campagnes
 * graine 42 : 2 -> 1 -> 0, notes 54 -> -1, plus jamais de reconstitution. On complete jusqu'au
 * predTrains d'origine, borne par les quais de la ligne (2 x min(nStops), sinon
 * OpexRoadPhysicalVehicleCap). Avant _tryBuild : un camion sur une route
 * deja posee rapporte plus, a l'opcode, qu'une ligne neuve. Panneau RF|year|id|added|after
 * (succes) ou RF|year|id|0|REASON (echec). */
function OpexAI::_refleetRoadLines(year)
{

  local anchor = AIMap.GetTileIndex(1, 1);
  local road100FreightBerthAttempted = false;
  local road100PaxBalanceAttempts = 0;
  local road100PaxBalanceBuilt = false;
  local road100PaxDoubleAttempts = 0;
  local road100PaxDoubleBuilt = false;
  if (ROAD100_PAX_DOUBLE_BERTHS) {
    foreach (oldLine in this._lines) {
      if (("road100PaxDoubleTryYear" in oldLine)
          && oldLine.road100PaxDoubleTryYear == year)
        road100PaxDoubleAttempts++;
      if (("road100PaxDoubleBuiltYear" in oldLine)
          && oldLine.road100PaxDoubleBuiltYear == year)
        road100PaxDoubleBuilt = true;
    }
  }
  if (ROAD100_PAX_BERTH_BALANCE) {
    foreach (oldLine in this._lines) {
      if (("road100PaxBerthTryYear" in oldLine)
          && oldLine.road100PaxBerthTryYear == year) {
        road100PaxBalanceAttempts++;
        if (("road100PaxBalanceTile" in oldLine)
            && oldLine.road100PaxBalanceTile != null)
          road100PaxBalanceBuilt = true;
      }
    }
  }
  if (ROAD100_FREIGHT_BERTHS) {
    foreach (oldLine in this._lines) {
      if (("road100FreightBerthTryYear" in oldLine) &&
          oldLine.road100FreightBerthTryYear == year) {
        road100FreightBerthAttempted = true;
        break;
      }
    }
  }
  /* ROAD100-14 : une conversion experimentale par exercice maximum, quelle
   * que soit la frequence d'appel de cette tache. Le marqueur est sur la
   * ligne et traverse Save/Load via OpexSaveProjectLine. Chemin OFF intact. */
  local road100TourAttempted = false;
  if (ROAD100_TOUR) {
    foreach (oldLine in this._lines) {
      if (("road100TourAttemptYear" in oldLine) && oldLine.road100TourAttemptYear == year) {
        road100TourAttempted = true;
        break;
      }
    }
  }
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    /* ROAD100-31 : les tuiles physiques des deux quais ayant
     * permis quatre bus initiaux traversent Save/Load. Meme
     * avec le reglage OFF au rechargement, une destruction
     * externe n'autorise plus de nouvelles acquisitions selon
     * un plafond de qua i fantome. Ne touche pas le chemin
     * historique sans marqueur. */
    if (("road100PaxInitialBays" in line) &&
        line.road100PaxInitialBays != null) {
      local pairValid = typeof line.road100PaxInitialBays == "array"
          && line.road100PaxInitialBays.len() == 2;
      if (!pairValid) {
        line.nStopsA = 1;
        line.nStopsB = 1;
        line.road100PaxInitialBays = null;
        if (DECISION_LOG) OpexDecide("ROAD100_PAX_INITIAL_FLEET",
            "phase=recover line=" + line.lineId + " reason=BAD_BAYS");
      } else {
        for (local side = 0; side < 2; side++) {
          local bay = line.road100PaxInitialBays[side];
          if (bay == -1) continue;
          local root = side == 0 ? line.stationA : line.stationB;
          local good = typeof bay == "integer" && AIMap.IsValidTile(bay)
              && AIRoad.IsRoadStationTile(root)
              && AIRoad.IsRoadStationTile(bay)
              && AICompany.IsMine(AITile.GetOwner(bay))
              && AIStation.GetStationID(bay) == AIStation.GetStationID(root);
          if (!good) {
            line.road100PaxInitialBays[side] = -1;
            if (side == 0) line.nStopsA = 1;
            else line.nStopsB = 1;
            if (DECISION_LOG) OpexDecide("ROAD100_PAX_INITIAL_FLEET",
                "phase=recover line=" + line.lineId
                + " side=" + side + " reason=LOST_BAY");
          }
        }
      }
    }
    /* ROAD100-24 : le Load et la destruction externe ne doivent jamais
     * laisser le refleet croire à deux quais sans deux vraies stations.
     * Ce contrôle survit même si l'option de CREATION repasse à OFF. */
    if (("road100FreightBerths" in line) &&
        typeof line.road100FreightBerths == "array") {
      local bays = line.road100FreightBerths;
      local validBays = bays.len() == 2;
      if (validBays) {
        local roots = [line.stationA, line.stationB];
        for (local side = 0; side < 2; side++) {
          local bay = bays[side];
          if (typeof bay != "integer" || !AIMap.IsValidTile(bay) ||
              !AIRoad.IsRoadStationTile(bay) ||
              !AICompany.IsMine(AITile.GetOwner(bay)) ||
              AIStation.GetStationID(bay) != AIStation.GetStationID(roots[side])) {
            validBays = false; break;
          }
        }
      }
      if (!validBays) {
        line.nStopsA = 1; line.nStopsB = 1;
        line.road100FreightBerths = null;
        if (DECISION_LOG) OpexDecide("ROAD100_FREIGHT_BERTHS",
            "phase=recover line=" + line.lineId + " reason=LOST_BAY");
      }
    }
    /* ROAD100-26 : un quai PAX disparu ne laisse pas un plafond fantôme.
     * Ce contrôle fonctionne aussi après retour du setting à OFF. */
    if (("road100PaxBalanceTile" in line)
        && line.road100PaxBalanceTile != null) {
      local bayTile = line.road100PaxBalanceTile;
      local baySide = ("road100PaxBalanceSide" in line)
          ? line.road100PaxBalanceSide : -1;
      local bayRoot = baySide == 0 ? line.stationA : line.stationB;
      local bayOk = (baySide == 0 || baySide == 1)
          && typeof bayTile == "integer" && AIMap.IsValidTile(bayTile)
          && AIRoad.IsRoadStationTile(bayTile)
          && AICompany.IsMine(AITile.GetOwner(bayTile))
          && AIRoad.IsRoadStationTile(bayRoot)
          && AIStation.GetStationID(bayTile) == AIStation.GetStationID(bayRoot);
      if (!bayOk) {
        local previousStops = ("road100PaxBalancePreviousStops" in line)
            ? line.road100PaxBalancePreviousStops : 1;
        if (previousStops < 1) previousStops = 1;
        if (baySide == 0) line.nStopsA = previousStops;
        else if (baySide == 1) line.nStopsB = previousStops;
        line.road100PaxBalanceTile = null;
        if (DECISION_LOG) OpexDecide("ROAD100_PAX_BERTH",
            "phase=recover line=" + line.lineId + " reason=LOST_BAY");
      }
    }
    /* ROAD100-28 : deux vrais quais distincts de terminus, chacun joint
     * au StationID d'origine. Leurs tuiles sont sauvegardées dans la ligne.
     * La récupération vérifie chaque côté même si le réglage est OFF :
     * une démolition extérieure ne laisse aucun plafond fantôme. */
    if (("road100PaxDoubleBays" in line)
        && line.road100PaxDoubleBays != null
        && (typeof line.road100PaxDoubleBays != "array"
            || line.road100PaxDoubleBays.len() != 2)) {
      /* Un marqueur corrompu ne peut justifier aucune place de quai
       * additionnelle et ne doit pas bloquer un nouveau depart 1/1. */
      line.nStopsA = 1;
      line.nStopsB = 1;
      line.road100PaxDoubleBays = null;
      if (DECISION_LOG) OpexDecide("ROAD100_PAX_DOUBLE",
          "phase=recover line=" + line.lineId + " reason=BAD_BAYS");
    }
    if (("road100PaxDoubleBays" in line)
        && typeof line.road100PaxDoubleBays == "array"
        && line.road100PaxDoubleBays.len() == 2) {
      local doubleRoots = [line.stationA, line.stationB];
      for (local dbSide = 0; dbSide < 2; dbSide++) {
        local bay = line.road100PaxDoubleBays[dbSide];
        if (bay == -1) continue;
        local root = doubleRoots[dbSide];
        local valid = typeof bay == "integer" && AIMap.IsValidTile(bay)
            && AIRoad.IsRoadStationTile(root) && AIRoad.IsRoadStationTile(bay)
            && AICompany.IsMine(AITile.GetOwner(bay))
            && AIStation.GetStationID(bay) == AIStation.GetStationID(root);
        if (!valid) {
          line.road100PaxDoubleBays[dbSide] = -1;
          if (dbSide == 0) line.nStopsA = 1;
          else line.nStopsB = 1;
          if (DECISION_LOG) OpexDecide("ROAD100_PAX_DOUBLE",
              "phase=recover line=" + line.lineId
              + " side=" + dbSide + " reason=LOST_BAY");
        }
      }
      /* Les deux poses ont disparu : revenir a l'etat initial 1/1
       * plutot que garder [-1,-1] et bloquer toute premiere pose. */
      if (line.road100PaxDoubleBays[0] == -1
          && line.road100PaxDoubleBays[1] == -1)
        line.road100PaxDoubleBays = null;
    }
    /* ROAD100-14 : Save/Load ou demolition externe de A1 peuvent invalider
     * un circuit deja paye. Restaurer les DEUX ordres historiques sur les
     * listes partagees pendant la tache normale, jamais dans Load(). Ce
     * garde s'applique meme si le switch de creation est repasse a OFF. */
    if (("road100TourActive" in line) && line.road100TourActive) {
      local tourBroken = ("road100TourNeedsRepair" in line) && line.road100TourNeedsRepair;
      local tourStop = -1;
      if (!("road100TourStops" in line) || typeof line.road100TourStops != "array"
          || line.road100TourStops.len() != 4) {
        tourBroken = true;
      } else {
        tourStop = line.road100TourStops[2];
        if (typeof tourStop != "integer" || !AIMap.IsValidTile(tourStop)
            || !AIRoad.IsRoadStationTile(tourStop)
            || !AICompany.IsMine(AITile.GetOwner(tourStop))) {
          tourBroken = true;
        } else {
          local extraId = AIStation.GetStationID(tourStop);
          if (!AIStation.IsValidStation(extraId)
              || extraId == AIStation.GetStationID(line.stationA)
              || extraId == AIStation.GetStationID(line.stationB)) tourBroken = true;
        }
      }
      if (tourBroken) {
        local allRestored = true;
        local primaryId = AIStation.GetStationID(line.stationA);
        if (AIStation.IsValidStation(primaryId)) {
          foreach (bus in OpexLineVehicleIds(line, primaryId)) {
            if (!AIVehicle.IsValidVehicle(bus)) continue;
            local count = AIOrder.GetOrderCount(bus);
            /* Deux suppressions max, meme si un autre vehicule partage ces
             * ordres. Ne jamais effacer les ordres originaux 0/1. */
            for (local removeCount = 0; count > 2 && removeCount < 2; removeCount++) {
              if (!AIOrder.RemoveOrder(bus, count - 1)) { allRestored = false; break; }
              count = AIOrder.GetOrderCount(bus);
            }
            if (count != 2) allRestored = false;
            if (!allRestored) break;
          }
        }
        if (!allRestored) {
          if (DECISION_LOG) OpexDecide("ROAD100_TOUR", "phase=repair_failed line=" + line.lineId);
          continue;
        }
        line.road100TourActive = false;
        line.road100TourNeedsRepair <- false;
        if (DECISION_LOG) OpexDecide("ROAD100_TOUR", "phase=recover line=" + line.lineId
            + " reason=INVALID_A1 orders=2");
      }
    }
    if (("expandBlocked" in line) && line.expandBlocked) continue;
    if (("expandRetryCycle" in line) && line.expandRetryCycle > this._taskCycle) continue;
    if (!("depot" in line) || !AIRoad.IsRoadDepotTile(line.depot)) continue;
    if (("deadStreak" in line) && line.deadStreak > 0) continue;
    local have = 0;
    if ("vehCount" in line) {
      have = line.vehCount;
    } else if (("trains" in line)) {
      have = line.trains;
    }
    local target = ("predTrains" in line) ? line.predTrains : (("trains" in line) ? line.trains : 1);
    if (("trains" in line) && line.trains > target) target = line.trains;
    if (target < 1) target = 1;

    /* Une ligne passagers rentable existe deja : plutot que construire un
     * autre depot + 2 terminus, experimenter UN vrai arret complementaire
     * avec StationID autonome et quatre ordres sur la flotte existante.
     * Une absence de site ne change ni la ligne ni ses deux ordres. */
    if (ROAD100_TOUR && !road100TourAttempted && ("kind" in line)
        && line.kind == "pax" && ("year" in line) && year >= line.year + 2
        && (!("road100TourActive" in line) || !line.road100TourActive)
        && have > 0 && ("lastProfit" in line) && line.lastProfit > 3000
        && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= 60000
        && AIRoad.IsRoadStationTile(line.stationA)
        && AIRoad.IsRoadStationTile(line.stationB)) {
      local ownStation = AIStation.GetStationID(line.stationA);
      local model = null;
      if (AIStation.IsValidStation(ownStation)) {
        foreach (v in OpexLineVehicleIds(line, ownStation)) {
          if (AIVehicle.IsValidVehicle(v) &&
              AIVehicle.GetVehicleType(v) == AIVehicle.VT_ROAD) {
            model = v;
            break;
          }
        }
      }
      if (model != null) {
        line.road100TourAttemptYear <- year;
        road100TourAttempted = true;
        local tourResult = OpexRoad100TryTourAddStop(this._catalog, line, model);
        if (tourResult.ok) {
          line.road100TourActive <- true;
          line.road100TourVersion <- 1;
          line.road100TourStops <- [line.stationA, line.stationB,
                                     tourResult.tile, line.stationB];
          line.road100TourMarginal <- tourResult.marginal;
          line.road100TourCost <- tourResult.cost;
          OpexAir0310InvalidateSiteValidity();
        }
      }
    }

    // Dimensionnement dynamique intelligent basé sur les flux physiques
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local waitingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : 0;
    local waitingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
    local ratingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoRating(stationA, line.cargo) : 100;
    local ratingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoRating(stationB, line.cargo) : 100;
    local minRating = (ratingA < ratingB) ? ratingA : ratingB;
    local totalWaiting = waitingA + waitingB;

    // Analyse des véhicules de la ligne : y en a-t-il qui attendent à l'arrêt ?
    local vehicles = OpexLineVehicleIds(line, stationA);
    local isAnyWaiting = false;
    local movingCount = 0;
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.GetCurrentSpeed(v) == 0) {
        isAnyWaiting = true;
      } else movingCount++;
    }

    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    local dedupRoad = false;
    if (!("c50_road_ym" in line) || line.c50_road_ym != ym) {
      line.c50_road_ym <- ym;
      dedupRoad = true;
    }

    if (("lastProfit" in line) && line.lastProfit < -200 && have >= 2) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.loss_hit++;
      }
      continue;
    }

    local capacity = ("capacity" in line && line.capacity > 0) ? line.capacity : 25;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local extraNeeded = 0;

    /* ROAD100-26 : deux essais sur des lignes distinctes dans l'année,
     * mais une seule construction. Les villes/stations/origines restent
     * identiques : seul le côté min(nStopsA,B)==1 peut monter à 2.
     * Les attentes sont celles d'une ligne EXISTANTE, jamais un devis. */
    if (ROAD100_PAX_BERTH_BALANCE && !road100PaxBalanceBuilt
        && road100PaxBalanceAttempts < 2 && ("kind" in line)
        && line.kind == "pax" && ("year" in line) && year > line.year
        && have == 2 && movingCount > 0 && capacity > 0
        && ("lastProfit" in line) && line.lastProfit >= 5000
        && totalWaiting >= 3 * capacity && money >= 100000
        && ("nStopsA" in line) && ("nStopsB" in line)
        && ((line.nStopsA == 1 && line.nStopsB >= 2)
            || (line.nStopsB == 1 && line.nStopsA >= 2))
        && (!("road100PaxBalanceTile" in line) || line.road100PaxBalanceTile == null)
        && (!("road100PaxBerthTryYear" in line) || line.road100PaxBerthTryYear != year)) {
      local weakSide = line.nStopsA == 1 ? 0 : 1;
      road100PaxBalanceAttempts++;
      line.rawset("road100PaxBerthTryYear", year);
      local expandedPax = OpexRoad100PaxBalanceBerth(this._catalog, line, weakSide);
      if (expandedPax.ok) {
        line.rawset("road100PaxBalanceTile", expandedPax.tile);
        line.rawset("road100PaxBalanceSide", weakSide);
        line.rawset("road100PaxBalancePreviousStops", 1);
        if (weakSide == 0) line.nStopsA = 2;
        else line.nStopsB = 2;
        road100PaxBalanceBuilt = true;
        OpexAir0310InvalidateSiteValidity();
        if (DECISION_LOG) OpexDecide("ROAD100_PAX_BERTH",
            "phase=adopt line=" + line.lineId + " side=" + weakSide
            + " wait_a=" + waitingA + " wait_b=" + waitingB
            + " profit_real=" + line.lastProfit + " cash="
            + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    }

    /* ROAD100-28 : la plupart des PAX encore à 1/1 quai ne sont pas
     * éligibles à V26. Deux poses réelles, dans des exercices distincts,
     * préservent A/B, StationIDs, dépôts, véhicules et ordres. Aucune
     * production de nouveau quartier n'est jamais créditée.
     * Une ligne sans deuxième pose reste plafonnée à deux bus. */
    if (ROAD100_PAX_DOUBLE_BERTHS && !road100PaxDoubleBuilt
        && road100PaxDoubleAttempts < 2 && ("kind" in line)
        && line.kind == "pax" && ("year" in line)
        && year >= line.year + 2 && have == 2 && movingCount > 0
        && !isAnyWaiting && capacity > 0
        && ("lastProfit" in line) && line.lastProfit >= 5000
        && totalWaiting >= 3 * capacity && money >= 100000
        && ("nStopsA" in line) && ("nStopsB" in line)
        && line.nStopsA >= 1 && line.nStopsA <= 2
        && line.nStopsB >= 1 && line.nStopsB <= 2
        && ((line.nStopsA == 1 && line.nStopsB == 1
             && (!("road100PaxDoubleBays" in line)
                 || line.road100PaxDoubleBays == null))
            || (("road100PaxDoubleBays" in line)
                && typeof line.road100PaxDoubleBays == "array"
                && line.road100PaxDoubleBays.len() == 2
                && ((line.nStopsA == 2 && line.nStopsB == 1
                     && line.road100PaxDoubleBays[0] != -1)
                    || (line.nStopsA == 1 && line.nStopsB == 2
                        && line.road100PaxDoubleBays[1] != -1))))
        && (!("road100PaxDoubleTryYear" in line)
            || line.road100PaxDoubleTryYear != year)) {
      local doubleBays = ("road100PaxDoubleBays" in line)
          && typeof line.road100PaxDoubleBays == "array"
          && line.road100PaxDoubleBays.len() == 2
          ? line.road100PaxDoubleBays : [-1, -1];
      local doubleSide = line.nStopsA == 1 && line.nStopsB == 1
          ? (waitingA >= waitingB ? 0 : 1)
          : (line.nStopsA == 1 ? 0 : 1);
      if (doubleBays[doubleSide] == -1) {
        road100PaxDoubleAttempts++;
        line.rawset("road100PaxDoubleTryYear", year);
        local expandedDouble = OpexRoad100PaxBalanceBerth(
            this._catalog, line, doubleSide);
        if (expandedDouble.ok) {
          doubleBays[doubleSide] = expandedDouble.tile;
          line.rawset("road100PaxDoubleBays", doubleBays);
          if (doubleSide == 0) line.nStopsA = 2;
          else line.nStopsB = 2;
          line.rawset("road100PaxDoubleBuiltYear", year);
          road100PaxDoubleBuilt = true;
          OpexAir0310InvalidateSiteValidity();
          if (DECISION_LOG) OpexDecide("ROAD100_PAX_DOUBLE",
              "phase=adopt line=" + line.lineId + " side=" + doubleSide
              + " tile=" + expandedDouble.tile
              + " a=" + line.nStopsA + " b=" + line.nStopsB
              + " waiting=" + totalWaiting + " profit_real=" + line.lastProfit
              + " paid=" + expandedDouble.paid + " ops=" + expandedDouble.ops
              + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
        } else if (DECISION_LOG) {
          OpexDecide("ROAD100_PAX_DOUBLE",
              "phase=reject line=" + line.lineId + " side=" + doubleSide
              + " reason=" + expandedDouble.reason
              + " ops=" + expandedDouble.ops);
        }
      }
    }

    /* ROAD100-24 : uniquement après une année effectivement bénéficiaire,
     * si les camions circulent et que la production attend réellement.
     * Waiting est ici POST-construction, jamais utilisé pour classer un
     * candidat neuf. Une tentative annuelle totale, pas une par tick. */
    if (ROAD100_FREIGHT_BERTHS && !road100FreightBerthAttempted &&
        ("kind" in line) && line.kind == "freight" &&
        ("year" in line) && year > line.year && have >= 2 &&
        movingCount > 0 && !isAnyWaiting &&
        ("lastProfit" in line) && line.lastProfit >= 3000 &&
        waitingA >= 3 * capacity && money >= 100000 &&
        (!("road100FreightBerths" in line) || line.road100FreightBerths == null)) {
      road100FreightBerthAttempted = true;
      line.rawset("road100FreightBerthTryYear", year);
      local expanded = OpexRoad100FreightBerthGrow(this._catalog, line, have, waitingA);
      if (expanded.ok) {
        line.rawset("road100FreightBerths", [expanded.a, expanded.b]);
        line.nStopsA = 2; line.nStopsB = 2;
        OpexAir0310InvalidateSiteValidity();
        if (DECISION_LOG) OpexDecide("ROAD100_FREIGHT_BERTHS",
            "phase=adopt line=" + line.lineId + " source_wait=" + waitingA
            + " profit_real=" + line.lastProfit + " cash="
            + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    }

    /* Plafond physique historique des arrets. */
    local physicalCap = OpexRoadPhysicalVehicleCap(
        ("nStopsA" in line) ? line.nStopsA : 1, ("nStopsB" in line) ? line.nStopsB : 1);
    if (("road100FreightBerths" in line) && line.road100FreightBerths != null &&
        ("kind" in line) && line.kind == "freight" &&
        have < physicalCap && !isAnyWaiting && capacity > 0 &&
        ("lastProfit" in line) && line.lastProfit >= 3000 &&
        money >= 50000) {
      /* La demande observée commande la flotte, non un cap arbitraire :
       * un camion supplémentaire exige un chargement complet en stock. */
      local wanted = waitingA / capacity - have;
      if (wanted > 2) wanted = 2;
      if (wanted > physicalCap - have) wanted = physicalCap - have;
      local unitPrice = 0;
      foreach (vehicle in vehicles) {
        if (AIVehicle.IsValidVehicle(vehicle)) {
          unitPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(vehicle));
          if (unitPrice > 0) break;
        }
      }
      if (unitPrice <= 0) wanted = 0;
      else {
        local affordable = (money - 50000) / unitPrice;
        if (wanted > affordable) wanted = affordable;
      }
      if (wanted > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, wanted))
        wanted = 0;
      if (wanted > extraNeeded) extraNeeded = wanted;
    }
    /* ROAD100-10 : AAAHogEx renforce ses bus interurbains d'apres le stock
     * reelement en attente et le rendement realise. Tester cette politique
     * APRES un exercice rentable et sans toucher au dimensionnement initial
     * ni aux plafonds historiques (ROAD100_WAIT_FLEET=0). Le trafic de retour
     * aux terminus peut justifier plusieurs bus sur une longue liaison ; la
     * cadence tient compte du temps de rotation, pas de la quantite de quais
     * seulement. Rien n'autorise a ajouter des bus au fret. */
    local dynamicWaitFleet = ROAD100_WAIT_FLEET && ("kind" in line)
        && line.kind == "pax" && ("year" in line) && year > line.year;
    local incrementalWanted = 0;
    local waitFleetPrice = 0;
    if (dynamicWaitFleet) {
      local oneWay = ("predOneWayDays" in line) ? line.predOneWayDays : 0;
      local timeCap = (2 * oneWay) / 3;
      if (timeCap < 2) timeCap = 2;
      if (timeCap > 16) timeCap = 16;
      if (timeCap > physicalCap) physicalCap = timeCap;
      local lastProfit = ("lastProfit" in line) ? line.lastProfit : 0;
      local age = year - line.year;
      if (lastProfit > 2000 && movingCount > 0 && have < physicalCap
          && capacity > 0 && totalWaiting >= capacity * (have + 1)) {
        local vehicleIds = OpexLineVehicleIds(line, stationA);
        foreach (v in vehicleIds) {
          if (!AIVehicle.IsValidVehicle(v)) continue;
          waitFleetPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
          if (waitFleetPrice > 0) break;
        }
        if (waitFleetPrice > 0 && money >= 50000 + waitFleetPrice) {
          incrementalWanted = totalWaiting / capacity - have;
          if (incrementalWanted < 1) incrementalWanted = 1;
          if (incrementalWanted > 2) incrementalWanted = 2;
          local affordable = (money - 50000) / waitFleetPrice;
          if (incrementalWanted > affordable) incrementalWanted = affordable;
          if (incrementalWanted > physicalCap - have)
            incrementalWanted = physicalCap - have;
          local currentMonth = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (("road100WaitFleetMonth" in line) && line.road100WaitFleetMonth == currentMonth)
            incrementalWanted = 0;
          else if (incrementalWanted > 0) line.road100WaitFleetMonth <- currentMonth;
        }
      }
      if (DECISION_LOG && dedupRoad) {
        OpexDecide("ROAD100_WAIT_FLEET", "line=" + line.lineId
            + " age=" + age + " have=" + have + " cap=" + physicalCap
            + " wait_a=" + waitingA + " wait_b=" + waitingB + " capacity=" + capacity
            + " moving=" + movingCount + " last_profit=" + lastProfit
            + " rating=" + minRating + " unit_price=" + waitFleetPrice
            + " cash=" + money + " want=" + incrementalWanted);
      }
    }

    if (have >= physicalCap) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.physical_cap_hit++;
      }
    } else if (isAnyWaiting) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.congestion_hit++;
      }
    }

    // 1. S'il y a du stock en attente et que les véhicules circulent bien
    if (totalWaiting >= capacity && !isAnyWaiting) {
      extraNeeded = totalWaiting / capacity;
      if (extraNeeded > 3) extraNeeded = 3;
    }
    // 2. Si la note de station s'effondre faute de fréquence (distance longue)
    else if (minRating < 65 && have < physicalCap && !isAnyWaiting && money > 35000) {
      extraNeeded = 1;
    }
    // 3. Si la ligne est très rentable (> 1000 £) et qu'on a du cash
    else if (("lastProfit" in line) && line.lastProfit > 1000 && have < physicalCap && money > 60000 && !isAnyWaiting) {
      extraNeeded = 1;
    }
    /* La politique d'attente reste soumise a la caisse et au plafond
     * temporel et n'ajoute jamais plus de deux bus par mois. */
    if (dynamicWaitFleet && have >= 2) extraNeeded = incrementalWanted;
    else if (dynamicWaitFleet && incrementalWanted > extraNeeded)
      extraNeeded = incrementalWanted;

    if (("road100PaxBalanceTile" in line)
        && line.road100PaxBalanceTile != null
        && ("kind" in line) && line.kind == "pax") {
      /* Achat à vrai prix, réserve 50k, bénéfice clos et stock de la ligne.
       * Pas de crédit de profit pour le quai ; refleet garde les ordres.
       * Limiter l'achat à deux bus par appel au plafond physique courant. */
      if (("lastProfit" in line) && line.lastProfit >= 5000
          && totalWaiting >= 3 * capacity && movingCount > 0
          && !isAnyWaiting && have < physicalCap) {
        local busPrice = 0;
        foreach (bus in vehicles) {
          if (!AIVehicle.IsValidVehicle(bus)) continue;
          busPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(bus));
          if (busPrice > 0) break;
        }
        local wanted = totalWaiting / capacity - have;
        if (wanted > 2) wanted = 2;
        if (wanted > physicalCap - have) wanted = physicalCap - have;
        if (busPrice <= 0) wanted = 0;
        else {
          local canPay = (money - 50000) / busPrice;
          if (wanted > canPay) wanted = canPay;
        }
        if (wanted > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, wanted))
          wanted = 0;
        if (wanted > extraNeeded) extraNeeded = wanted;
      } else if (have >= 2) extraNeeded = 0;
      /* Le refleet historique peut demander plus que la réserve de cash :
       * conserver la même garde sous le nouveau quai PAX. */
      local busUnitPrice = 0;
      foreach (bus in vehicles) {
        if (AIVehicle.IsValidVehicle(bus)) {
          busUnitPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(bus));
          if (busUnitPrice > 0) break;
        }
      }
      if (busUnitPrice > 0) {
        local affordableAboveReserve = (money - 50000) / busUnitPrice;
        if (extraNeeded > affordableAboveReserve) extraNeeded = affordableAboveReserve;
      } else extraNeeded = 0;
    }
    /* Aucun bus supplémentaire sur un bonus de quai purement théorique.
     * Avec 2/2 vrais quais récupérés au début de la tâche, financer
     * au plus deux bus par exercice et conserver 50k de caisse. */
    if (ROAD100_PAX_DOUBLE_BERTHS && ("kind" in line)
        && line.kind == "pax"
        && ("road100PaxDoubleBays" in line)
        && typeof line.road100PaxDoubleBays == "array"
        && line.road100PaxDoubleBays.len() == 2) {
      extraNeeded = 0;
      if (line.nStopsA >= 2 && line.nStopsB >= 2
          && have >= 2 && have < physicalCap && movingCount > 0
          && !isAnyWaiting && ("lastProfit" in line)
          && line.lastProfit >= 5000 && totalWaiting >= 3 * capacity) {
        local doubleCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        local doublePrice = 0;
        foreach (bus in vehicles) {
          if (AIVehicle.IsValidVehicle(bus)) {
            doublePrice = AIEngine.GetPrice(AIVehicle.GetEngineType(bus));
            if (doublePrice > 0) break;
          }
        }
        if (doublePrice > 0 && doubleCash >= 50000 + doublePrice) {
          extraNeeded = totalWaiting / capacity - have;
          if (extraNeeded > 2) extraNeeded = 2;
          if (extraNeeded > physicalCap - have)
            extraNeeded = physicalCap - have;
          local aboveReserve = (doubleCash - 50000) / doublePrice;
          if (extraNeeded > aboveReserve) extraNeeded = aboveReserve;
          if (extraNeeded > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, extraNeeded))
            extraNeeded = 0;
        }
      }
    }

    /* B3 : `physicalCap` garde son ancien nom pour préserver le chemin 0 ; sous le switch pax,
     * sa valeur devient le plafond temporel de flotte. La capacité de quai reste reportée à part. */
    if (have + extraNeeded > physicalCap) extraNeeded = physicalCap - have;
    if (extraNeeded < 0) extraNeeded = 0;

    if (have + extraNeeded > target) target = have + extraNeeded;
    if (target > physicalCap) target = physicalCap;

    /* ROAD100-24 : la cible finale transmise à refleet pour une ligne
     * doubles quais fret ne doit pas être écrasée par la logique historique :
     * réserve 50k, bénéfice clos >= 3000 £, circulation, slots et plafond 2. */
    if (("road100FreightBerths" in line) && line.road100FreightBerths != null &&
        ("kind" in line) && line.kind == "freight") {
      if (target > have) {
        if (target > have + 2) target = have + 2;
        if (!("lastProfit" in line) || line.lastProfit < 3000 || isAnyWaiting || capacity <= 0) {
          target = have;
        } else {
          local demandWanted = waitingA / capacity - have;
          if (demandWanted <= 0) target = have;
          else {
            if (target > have + demandWanted) target = have + demandWanted;
            local freightCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
            local freightPrice = 0;
            foreach (v in vehicles) {
              if (AIVehicle.IsValidVehicle(v)) {
                freightPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
                if (freightPrice > 0) break;
              }
            }
            if (freightPrice <= 0 || freightCash < 50000) {
              target = have;
            } else {
              local canPay = (freightCash - 50000) / freightPrice;
              if (target - have > canPay) target = have + canPay;
              local missing = target - have;
              if (missing > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, missing)) {
                if (missing > 1 && OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1))
                  target = have + 1;
                else
                  target = have;
              }
            }
          }
        }
      }
    }

    if (have >= target) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null && have < physicalCap && !isAnyWaiting) {
        C50_NON_EXPANSION_LEDGER.road.no_demand++;
      }
      if (("needsRefleet" in line) && line.needsRefleet) line.needsRefleet = false;
      continue;
    }
    local refill = OpexRoadRefleet(this._catalog, line, have, target);
    if (refill.added > 0) {
      line.vehCount <- refill.after;
      if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
      if (refill.after >= target && ("needsRefleet" in line)) line.needsRefleet = false;
      if (C50_CHRONOLOGY_PROBE) {
        if (C50_NON_EXPANSION_LEDGER != null) C50_NON_EXPANSION_LEDGER.road.refill_built += refill.added;
        OpexC50ChronologyLog("phase=fleet_built mode=road line=" + line.lineId + " added=" + refill.added + " total=" + refill.after + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    } else if (C50_CHRONOLOGY_PROBE) {
      if (C50_NON_EXPANSION_LEDGER != null) {
        if (refill.reason == "CASH") C50_NON_EXPANSION_LEDGER.road.cash_refused++;
        else C50_NON_EXPANSION_LEDGER.road.other_refused++;
      }
      if (refill.reason == "CASH") {
        this._logC50CashRefusal("road_refleet", line.lineId, 0, 0, 0, line.stationA, line.stationB, 0, AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    }
    if (DECISION_LOG) {
      if (refill.added > 0) {
        OpexDecide("ROAD_REFLEET", "action=refill line=" + line.lineId + " added=" + refill.added + " total=" + refill.after);
      } else {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (!("lastRefleetRefuseMonth" in line) || line.lastRefleetRefuseMonth != ym) {
          line.lastRefleetRefuseMonth <- ym;
          OpexDecide("ROAD_REFLEET", "action=refuse line=" + line.lineId + " reason=" + refill.reason + " have=" + have + " target=" + target);
        }
      }
    }
    OpexSign(anchor, "RF|" + year + "|" + line.lineId + "|" + refill.added + "|"
                     + (refill.added > 0 ? refill.after : refill.reason));
  }
}
