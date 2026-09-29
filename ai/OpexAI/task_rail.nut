/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexC41RailApproachLead(platform, fallbackExit = null)
{
  if (platform == null) return null;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  if (exit == null) return null;
  if ("lead" in platform) return platform.lead;
  if (("anchor" in platform) && ("step" in platform) && ("length" in platform)) {
    return exit == platform.anchor ? exit - platform.step : exit + platform.step;
  }
  return null;
}
/* Un fait local par quai : la voie de sortie existe-t-elle, combien de branches porte-t-elle,
 * et quel signal regarde le quai ? -1 signifie que l'approche ne peut pas etre lue. */
function OpexC41RailApproachFacts(platform, fallbackExit = null)
{
  local facts = { rail = 0, tracks = 0, signal = -1 };
  if (platform == null) return facts;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  if (exit == null) return facts;
  local lead = OpexC41RailApproachLead(platform, fallbackExit);
  /* Les plateformes secondaires anciennes enregistrent ancre/pas/longueur mais pas lead.
   * stationA2/B2 est leur sortie persistée : on reconstitue exactement le voisin immediat,
   * sans explorer la carte. */
  if (lead == null) return facts;
  if (!AIMap.IsValidTile(lead) || !AIMap.IsValidTile(exit) || AIMap.DistanceManhattan(lead, exit) != 1) return facts;
  facts.rail = AIRail.IsRailTile(lead) ? 1 : 0;
  if (!facts.rail) return facts;
  facts.tracks = OpexTileTrackCount(lead);
  facts.signal = AIRail.GetSignalType(lead, exit);
  return facts;
}
/* C41.8 : PBS seulement. Une approche a deux branches est un aiguillage : le moteur refuse
 * souvent d'y poser un signal et C41.7 ne permet pas encore d'en choisir une branche sure.
 * 2=deja PBS, 1=pose, 0=refus, -1=emplacement non eligible, -2=signal non-PBS existant. */
function OpexC41BuildPbsAtApproach(platform, fallbackExit = null)
{
  if (platform == null) return -1;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  local lead = OpexC41RailApproachLead(platform, fallbackExit);
  if (exit == null || lead == null || !AIMap.IsValidTile(exit) || !AIMap.IsValidTile(lead) ||
      AIMap.DistanceManhattan(lead, exit) != 1 || !AIRail.IsRailTile(lead) ||
      AIRail.IsRailStationTile(lead) || AIRail.IsRailDepotTile(lead) || OpexTileTrackCount(lead) != 1) return -1;
  local type = AIRail.GetSignalType(lead, exit);
  if (type == AIRail.SIGNALTYPE_PBS) return 2;
  if (type != AIRail.SIGNALTYPE_NONE) return -2;
  return AIRail.BuildSignal(lead, exit, AIRail.SIGNALTYPE_PBS) ? 1 : 0;
}
function OpexC41RailDepotFrontFacts(depot)
{
  local facts = { rail = 0, tracks = 0 };
  if (!AIMap.IsValidTile(depot) || !AIRail.IsRailDepotTile(depot)) return facts;
  local front = AIRail.GetRailDepotFrontTile(depot);
  if (!AIMap.IsValidTile(front)) return facts;
  facts.rail = AIRail.IsRailTile(front) ? 1 : 0;
  if (facts.rail) facts.tracks = OpexTileTrackCount(front);
  return facts;
}
/* Compte au plus les quatre voisins contigus. Si `exclude` est fourni (sortie de quai ou depot),
 * `links` est le nombre de branches que le moteur reconnait reellement reliees de l'autre cote de
 * la tuile centrale. Ce n'est pas un pathfinding global. */
function OpexC41RailLocalLinks(center, exclude = null)
{
  local facts = { rail = 0, branches = 0, links = -1 };
  /* C41.10 : AIMap.IsValidTile leve une erreur Squirrel sur `null` au lieu de rendre faux --
   * crash reproduit le 2026-09-08 (ligne sans platformA2/B2 emettant VehicleLost, leadA2 null
   * passe ici depuis le sondage C41.9 dans _processEvents). Garde ajoutee, aucun changement pour
   * un center non-null : le comportement pour toute tuile valide est inchange. */
  if (center == null || !AIMap.IsValidTile(center) || !AIRail.IsRailTile(center)) return facts;
  facts.rail = 1;
  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local offsets = [xStep, -xStep, yStep, -yStep];
  if (exclude != null && AIMap.IsValidTile(exclude) && AIMap.DistanceManhattan(exclude, center) == 1) facts.links = 0;
  foreach (offset in offsets) {
    local neighbor = center + offset;
    if (!AIMap.IsValidTile(neighbor) || AIMap.DistanceManhattan(center, neighbor) != 1 || !AIRail.IsRailTile(neighbor)) continue;
    facts.branches++;
    if (facts.links >= 0 && neighbor != exclude && AIRail.AreTilesConnected(exclude, center, neighbor)) facts.links++;
  }
  return facts;
}
/* C41.10 : repare le seul raccord manquant trouve par C41.9 -- PAS n'importe quelle branche non
 * reconnue, seulement le cas ou l'approche n'a RECONNU AUCUNE branche sortante du tout
 * (OpexC41RailLocalLinks(center, exclude).links == 0), exactement le critere de C41.9. Verifie
 * au smoke le 2026-09-08 : un premier essai qui acceptait toute branche non connectee, meme aux
 * cotes de branches deja reconnues (links >= 1), s'est revele reparer des jonctions hors du
 * perimetre du constat C41.9 (a2/b2/depot avec links=1 ou 2, jamais 0) des le premier VehicleLost
 * rencontre -- au-dela de « ce seul raccord », contrairement a la consigne. Corrige avant tout
 * autre test.
 *
 * Uniquement si UNE seule branche est candidate. Meme prudence que C41.8 pour les aiguillages a
 * plusieurs branches, ou C41.7 ne permet pas encore de choisir une sortie sure : 0 ou plusieurs
 * candidats n'est jamais tente. D'abord AITestMode (le meme AIRail.BuildRail que le reel, sans le
 * payer ni modifier la carte) ; commande reelle seulement si ce test reussit. AreTilesConnected
 * est revérifié APRES la pose reelle : une commande acceptee par le moteur ne garantit pas la
 * connexion recherchee (une piece compatible mais differente peut satisfaire BuildRail).
 * -3 = position illisible (tuiles invalides, pas adjacentes, ou centre non-rail).
 * -2 = links != 0 (hors perimetre C41.9), ou 0/plusieurs branches candidates (rien a faire, ou
 *      ambigu -- jamais tente).
 * -4 = AITestMode accepte, mais la commande reelle refuse la pose.
 *  0 = AITestMode refuse la pose.
 *  1 = pose reelle et connexion confirmees.
 *  2 = pose reelle acceptee mais connexion toujours absente (a investiguer). */
function OpexC41RepairJunction(center, exclude)
{
  if (center == null || exclude == null || !AIMap.IsValidTile(center) || !AIMap.IsValidTile(exclude)
      || AIMap.DistanceManhattan(exclude, center) != 1 || !AIRail.IsRailTile(center)) return -3;
  local facts = OpexC41RailLocalLinks(center, exclude);
  if (facts.links != 0) return -2;
  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local offsets = [xStep, -xStep, yStep, -yStep];
  local candidate = null;
  local nCandidates = 0;
  foreach (offset in offsets) {
    local neighbor = center + offset;
    if (!AIMap.IsValidTile(neighbor) || AIMap.DistanceManhattan(center, neighbor) != 1 ||
        neighbor == exclude || !AIRail.IsRailTile(neighbor)) continue;
    nCandidates++;
    candidate = neighbor;
  }
  if (nCandidates != 1) return -2;
  local testOk = false;
  {
    local testMode = AITestMode();
    testOk = AIRail.BuildRail(exclude, center, candidate);
  }
  if (!testOk) return 0;
  if (!AIRail.BuildRail(exclude, center, candidate)) return -4;
  return AIRail.AreTilesConnected(exclude, center, candidate) ? 1 : 2;
}
/* C38 etape 2 : une tentative rail est une transaction explicite. Le balayage decide
 * seulement quoi faire ensuite ; cette fonction decide si le candidat a ete construit,
 * refuse, ou suspendu par A*. `passDiscards` reste une reference partagee pour
 * conserver le journal dans le meme ordre que le passage historique. */
function OpexAI::_tryBuildRailProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local candidate = project.payload;
      if (C80_RAIL_STOCK_GATE) {
        local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
        if (C80_RAIL_STOCK_WORKER && (this._railReadyStock == null
            || !(pairKey in this._railReadyStock)
            || this._railReadyStock[pairKey].project != project)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
            passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                                  reason = "no_ready_route", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (this._railReadyStock != null && (pairKey in this._railReadyStock)) {
          local entry = this._railReadyStock[pairKey];
          if (entry != null && ("plan" in entry) && entry.plan != null && (!("ok" in entry.plan) || entry.plan.ok)) {
            candidate.rawset("railPlan", entry.plan);
          }
        }
        if (!C80_RAIL_STOCK_WORKER && builtCount > 0 && ("railPlan" in candidate)) {
          candidate.railPlan = null;
        }
        if (RAIL_SEARCH_RESUMABLE && this._railSearch != null && !(("railPlan" in candidate) && candidate.railPlan != null)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "search_in_progress", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else {
        if (builtCount > 0 && ("railPlan" in candidate)) {
          /* Le trace A* memorise vise la carte de la generation. Le premier chantier peut avoir
           * occupe un quai, un depot ou une tuile du trace ; le jeter force OpexBuildLine a
           * replanifier sur la carte vivante. Inerte pour maxBatch=1, precedent mesure. */
          candidate.railPlan = null;
        }
        /* Une recherche est deja en cours (autre candidat, ou upgrade) : ne pas en lancer une
         * seconde, et laisser air/route du portefeuille tourner. */
        if (RAIL_SEARCH_RESUMABLE && this._railSearch != null) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "search_in_progress", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      if (V88_STEP2_RAIL_PRIO && this._activeGoodsChain != null && this._activeGoodsChain.step == 2
          && !(("isChainStep2" in candidate) && candidate.isChainStep2)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "chain_step2_prio", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      /* V88 : Projet chaine industrielle complete (intrant -> usine -> biens -> ville) */
      if (("isChain" in candidate) && candidate.isChain) {
        if (this._activeGoodsChain != null) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "chain_in_progress", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!OpexRailVehicleSlotAvailable()) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "vehicle_limit", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        local inputCand = candidate.inputCandidate;
        local close = this._tooClose(inputCand);
        if (close.hard >= 0) {
          if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_hard", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (close.blocking >= 0) {
          if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        local need = inputCand.capital + OpexCashReserve();
        local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        local lowCash = (money < need);
        local willStartSearch = RAIL_SEARCH_RESUMABLE && !(("railPlan" in inputCand) && inputCand.railPlan != null);
        if (lowCash && !willStartSearch) {
          if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("rail", i, inputCand.capital, inputCand.profitAnnual, inputCand.roi, inputCand.src, inputCand.dst, need, money);
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
          return { outcome = "rejected", discards = passDiscards };
        }
        OpexSign(anchor, "IP|" + yy + "|T|" + project.budgetScore + "|" + project.opcodeScore);
        inputCand.chainParent <- candidate;
        inputCand.isChainStep1 <- true;
        local alternativeRatio = MIN_RATIO;
        local hardCap = OpexDynamicHardCap(this._lines.len(), lowCash);
        local posPacked = i * TOP_K + this._projects.best.len();
        if (RAIL_SEARCH_RESUMABLE && !(("railPlan" in inputCand) && inputCand.railPlan != null)) {
          if (C80_RAIL_STOCK_GATE) {
            if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
              passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "no_ready_route", extra = "chain=step1" });
            }
            return { outcome = "rejected", discards = passDiscards };
          }
          if (DECISION_LOG) {
            foreach (d in passDiscards) {
              OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
            }
            passDiscards = [];
            local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
            OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
            OpexDecide("CHAIN_CHOSEN", "fact=" + candidate.factoryId + " town=" + candidate.dstTown + " goodsCargo=" + candidate.goodsCargo);
          }
          OpexV88Log("CHAIN_CHOSEN", "fact=" + candidate.factoryId + " town=" + candidate.dstTown
                     + " inCargo=" + candidate.inputCargo + " goodsCargo=" + candidate.goodsCargo
                     + " src=" + candidate.src + " dst=" + candidate.dst);
          local start = this._startRailSearch(inputCand, alternativeRatio, hardCap, posPacked);
          OpexV88Log("CHAIN_STEP1_SEARCH", "pending=" + (start.pending ? 1 : 0));
          if (start.pending) return { outcome = "pending", discards = passDiscards };
          inputCand.railPlan <- start.plan;
        }
        local result = OpexBuildLine(this._catalog, this._budget, inputCand, alternativeRatio,
                                     OpexCashReserve(), hardCap);
        if (result.reason == "CASH") {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "cash_at_build", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if ("railPlan" in inputCand) inputCand.railPlan = null;
        if (DECISION_LOG && !RAIL_SEARCH_RESUMABLE) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
          OpexDecide("CHAIN_CHOSEN", "fact=" + candidate.factoryId + " town=" + candidate.dstTown + " goodsCargo=" + candidate.goodsCargo);
        }
        if (!RAIL_SEARCH_RESUMABLE) {
          OpexV88Log("CHAIN_CHOSEN", "fact=" + candidate.factoryId + " town=" + candidate.dstTown
                     + " inCargo=" + candidate.inputCargo + " goodsCargo=" + candidate.goodsCargo
                     + " src=" + candidate.src + " dst=" + candidate.dst);
        }
        local recorded = this._recordRailAttempt(inputCand, result, posPacked, year);
        if (recorded) {
          local inputLine = this._lines[this._lines.len() - 1];
          this._setActiveGoodsChain({
            step = 2,
            factoryId = candidate.factoryId,
            townId = candidate.dstTown,
            inputLineId = inputLine.lineId,
            factoryStationId = inputLine.stationB,
            factoryPlatform = {
              anchor = inputLine.platformB.anchor,
              direction = inputLine.platformB.direction,
              length = inputLine.platformB.length,
              step = inputLine.platformB.step
            },
            goodsCandidate = candidate.goodsCandidate,
            year = year
          });
          OpexV88Log("CHAIN_STEP1", "line=" + inputLine.lineId + " fact=" + candidate.factoryId);
          OpexSign(anchor, "C1|" + yy + "|" + inputLine.lineId + "|" + candidate.factoryId);
          local step2Need = candidate.goodsCandidate.capital + OpexCashReserve();
          if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= step2Need && this._railSearch == null) {
            this._tryBuildGoodsChainStep2(year, passDiscards, anchor, yy);
          }
          return { outcome = "built", discards = passDiscards };
        }
        this._setActiveGoodsChain(null);
        OpexV88Log("CHAIN_FAIL", "step=1 reason=" + result.reason);
        OpexSign(anchor, "CF|" + yy + "|1|" + OpexAttemptReasonCode(result.reason));
        local failReason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
        local failError = ("error" in result) ? result.error : 0;
        passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                              reason = failReason, extra = "", error = failError });
        return { outcome = "rejected", discards = passDiscards };
      }
      /* M4/16.2 : aucun A* ni devis terrain pour un projet qui ne pourra physiquement acheter
       * aucun train. OpexExecuteRailPlan refait la meme garde juste avant la premiere depense pour
       * couvrir la course avec une recherche reprenable. */
      if (!OpexRailVehicleSlotAvailable()) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "vehicle_limit", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local towns = OpexGetCandidateTownEndpoints(candidate);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("rail", "build_precheck", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("rail", "build_precheck", towns.dstTown);
      }

      if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}

      local close = this._tooClose(candidate);
      if (close.hard >= 0) {
        if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_hard", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      if (close.blocking >= 0) {
        if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local need = candidate.capital + OpexCashReserve();
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local lowCash = (money < need);
      /* G3§2 : pour le chemin reprenable sans railPlan, la recherche A* ne coute aucune
       * tresorerie et le cash peut arriver pendant les tranches. On ne saute que le chemin
       * non reprenable (construction immediate). _consumeRailSearch verifiera la caisse a
       * la fin. Cela active aussi la branche isPreplanOrLowCash de OpexDynamicHardCap, qui
       * remonte au plafond dur pour exploiter les opcodes dormants pendant l'attente. */
      local willStartSearch = RAIL_SEARCH_RESUMABLE
          && !(("railPlan" in candidate) && candidate.railPlan != null);
      if (lowCash && !willStartSearch) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("rail", i, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|T|" + project.budgetScore + "|" + project.opcodeScore);

      local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
      local alternativeRatio = isPaxNear ? 0 : MIN_RATIO;
      local hardCap = OpexDynamicHardCap(this._lines.len(), lowCash);
      local posPacked = i * TOP_K + this._projects.best.len();
      if (RAIL_SEARCH_RESUMABLE &&
          !(("railPlan" in candidate) && candidate.railPlan != null)) {
        if (C80_RAIL_STOCK_GATE) {
          if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
            passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "no_ready_route", extra = "" });
          }
          return { outcome = "rejected", discards = passDiscards };
        }
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          /* Meme contrat qu'air/route/eau : une fois ces rejets publies avant le choix,
           * ils ne doivent pas etre republies au candidat/tour suivant. */
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
        }
        local start = this._startRailSearch(candidate, alternativeRatio, hardCap, posPacked);
        if (start.pending) return { outcome = "pending", discards = passDiscards };
        /* Le candidat n'a pas encore cette cle dans le chemin qui termine sa
         * recherche dans le meme tour : creation de slot Squirrel avec `<-`. */
        candidate.railPlan <- start.plan;
      }
      if (C80_RAIL_STOCK_GATE) {
        local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
        if (C80_RAIL_STOCK_WORKER && (pairKey in this._railReadyStock)) {
          local entry = this._railReadyStock[pairKey];
          local reval = this._revalidateRailStockPlan(candidate, entry.plan);
          if (!reval.ok) {
            if (C56_TASK_TRACE) {
              local failMsg = "src=" + candidate.src + " dst=" + candidate.dst + " reason=" + reval.reason;
              if ("failedSegments" in reval) {
                failMsg += " failed=" + reval.failedSegments;
              }
              if ("firstSegment" in reval && reval.firstSegment != null) {
                failMsg += " first=" + reval.firstSegment;
              }
              if ("firstTile" in reval && reval.firstTile != null) {
                failMsg += " first_tile=" + reval.firstTile;
              }
              OpexC56TaskLog("RAIL_STOCK_REVALIDATE_FAIL", "rail_stock", this._taskCycle, failMsg);
            }
            if (reval.reason == "cash") {
              if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
                passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                                      reason = "cash_at_revalidate", extra = "" });
              }
              return { outcome = "rejected", discards = passDiscards };
            }
            delete this._railReadyStock[pairKey];
            if ("railPlan" in candidate) candidate.railPlan = null;
            if (reval.reason == "industry_closed") {
              this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
              if (C56_TASK_TRACE) {
                OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                               "src=" + candidate.src + " dst=" + candidate.dst
                               + " reason=" + reval.reason + " issue=abandoned");
              }
              if (this._activeWorker == null) this._tryStartRailStockWorker();
            } else {
              // Règle 3 : relancer en priorité un A* pour la même paire (nouvelle recherche)
              local started = this._startRailStockSearch(candidate, true, reval.reason);
              if (!started) {
                this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 180;
                if (this._activeWorker == null) this._tryStartRailStockWorker();
              }
            }
            if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
              passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                                    reason = "revalidate_fail", extra = reval.reason });
            }
            return { outcome = "rejected", discards = passDiscards };
          }
        }
      }
      local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio,
                                   OpexCashReserve(), hardCap);
      if (result.reason == "CASH") {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "cash_at_build", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      if (("railPlan" in candidate)) candidate.railPlan = null;
      if (DECISION_LOG && !RAIL_SEARCH_RESUMABLE) {
        foreach (d in passDiscards) {
          OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
        }
        passDiscards = [];
        local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
        OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
      }
      local recorded = this._recordRailAttempt(candidate, result, posPacked, year);
      if (C80_RAIL_STOCK_GATE) {
        local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
        if (recorded) {
          if (pairKey in this._railReadyStock) {
            local entry = this._railReadyStock[pairKey];
            local delayDays = AIDate.GetCurrentDate() - entry.readyDate;
            delete this._railReadyStock[pairKey];
            if (C56_TASK_TRACE) {
              OpexC56TaskLog("RAIL_STOCK_CONSUME", "rail_stock", this._taskCycle,
                             "src=" + candidate.src + " dst=" + candidate.dst + " delay_days=" + delayDays);
            }
            if (C80_RAIL_STOCK_WORKER && this._activeWorker == null) {
              this._tryStartRailStockWorker();
            }
          }
        } else {
          if (pairKey in this._railReadyStock) {
            delete this._railReadyStock[pairKey];
            this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
            if (C80_RAIL_STOCK_WORKER && this._activeWorker == null) {
              this._tryStartRailStockWorker();
            }
          }
        }
      }
      if (!recorded && (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL)) {
        local failReason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
        local failError = ("error" in result) ? result.error : 0;
        passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                              reason = failReason, extra = "", error = failError });
      }
      return { outcome = recorded ? "built" : "rejected", discards = passDiscards };

}
/* V88 : Mutateur centralise de _activeGoodsChain pour synchroniser la reserve de tresorerie */
function OpexAI::_setActiveGoodsChain(chain)
{
  this._activeGoodsChain = chain;
  V88_STEP2_RESERVE_AMOUNT = (chain != null && chain.step == 2 && ("goodsCandidate" in chain) && chain.goodsCandidate != null && ("capital" in chain.goodsCandidate)) ? chain.goodsCandidate.capital : 0;
}

/* V88 : Construction de l'etape 2 d'une chaine de biens (troncon usine -> ville avec quai joint) */
function OpexAI::_tryBuildGoodsChainStep2(year, passDiscards, anchor, yy)
{
  if (this._activeGoodsChain == null || this._activeGoodsChain.step != 2) return false;
  local chain = this._activeGoodsChain;
  local goodsCand = chain.goodsCandidate;
  if (goodsCand == null) {
    OpexV88Log("CHAIN_FAIL", "step=2 reason=no_goods_candidate");
    this._setActiveGoodsChain(null);
    return false;
  }

  if (!AIIndustry.IsValidIndustry(chain.factoryId)) {
    OpexV88Log("CHAIN_FAIL", "step=2 reason=factory_gone");
    this._setActiveGoodsChain(null);
    return false;
  }

  local inputLine = null;
  foreach (line in this._lines) {
    if (line.lineId == chain.inputLineId) { inputLine = line; break; }
  }
  if (inputLine == null) {
    OpexV88Log("CHAIN_FAIL", "step=2 reason=input_line_gone line=" + chain.inputLineId);
    this._setActiveGoodsChain(null);
    return false;
  }

  goodsCand.joinPlatform <- chain.factoryPlatform;
  goodsCand.joinStationId <- chain.factoryStationId;
  goodsCand.joinLineId <- chain.inputLineId;
  goodsCand.isChainStep2 <- true;
  goodsCand.townId <- chain.townId;
  goodsCand.factoryId <- chain.factoryId;

  local abandonedKey = OpexAbandonedPairKey(goodsCand);
  if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
    OpexV88Log("CHAIN_FAIL", "step=2 reason=abandoned_pair");
    this._setActiveGoodsChain(null);
    return false;
  }

  local close = this._tooClose(goodsCand);
  if (close.hard >= 0 || close.blocking >= 0) {
    OpexV88Log("CHAIN_FAIL", "step=2 reason=too_close");
    this._markPairAbandoned(abandonedKey);
    this._setActiveGoodsChain(null);
    return false;
  }

  local need = goodsCand.capital + OpexCashReserve();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local lowCash = (money < need);
  local willStartSearch = RAIL_SEARCH_RESUMABLE && !(("railPlan" in goodsCand) && goodsCand.railPlan != null);
  if (lowCash && !willStartSearch) {
    OpexV88Log("CHAIN_WAIT", "step=2 reason=cash need=" + need + " money=" + money);
    return false;
  }

  local alternativeRatio = MIN_RATIO;
  local hardCap = OpexDynamicHardCap(this._lines.len(), lowCash);
  local posPacked = 0;

  if (RAIL_SEARCH_RESUMABLE && !(("railPlan" in goodsCand) && goodsCand.railPlan != null)) {
    if (C80_RAIL_STOCK_GATE) {
      OpexV88Log("CHAIN_FAIL", "step=2 reason=no_ready_route");
      return false;
    }
    local start = this._startRailSearch(goodsCand, alternativeRatio, hardCap, posPacked);
    OpexV88Log("CHAIN_STEP2_SEARCH", "pending=" + (start.pending ? 1 : 0));
    if (start.pending) return true;
    goodsCand.railPlan <- start.plan;
  }

  local result = OpexBuildLine(this._catalog, this._budget, goodsCand, alternativeRatio,
                               OpexCashReserve(), hardCap);
  if (result.reason == "CASH") {
    return false;
  }
  if ("railPlan" in goodsCand) goodsCand.railPlan = null;

  local recorded = this._recordRailAttempt(goodsCand, result, posPacked, year);
  if (recorded) {
    local goodsLine = this._lines[this._lines.len() - 1];
    OpexV88Log("CHAIN_STEP2", "line=" + goodsLine.lineId + " town=" + chain.townId);
    OpexSign(anchor, "C2|" + yy + "|" + goodsLine.lineId + "|" + chain.townId);
    this._setActiveGoodsChain(null);
    return true;
  } else {
    local failReason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
    OpexV88Log("CHAIN_FAIL", "step=2 reason=" + failReason);
    OpexSign(anchor, "CF|" + yy + "|2|" + OpexAttemptReasonCode(failReason));
    this._markPairAbandoned(abandonedKey);
    this._setActiveGoodsChain(null);
    return false;
  }
}
/* Choisit au plus UNE expansion par an. L'infrastructure est deja payee et aucun pathfinder ne
 * tourne : le classement porte donc sur le gain annuel marginal, les candidats ayant tous le
 * meme ordre de grandeur d'opcodes. Le revenu a capacite pleine de N+1 wagons est recale par le
 * revenu REEL de N wagons ; ce ratio conserve la physique (traction, temps, capacite) sans croire
 * la demande pax surestimee du catalogue. */
function OpexAI::_expandRailLines(year)
{
  /* G6§1 : la garde d'entree coupait TOUT sur !RAIL_EXPAND, y compris le bloc RAIL_REFLEET
   * plus bas -- seul site d'appel de OpexBuildSecondTrain et OpexUpgradeRailLineToDoubleTrack.
   * Avec les defauts livres (rail_expand = 0, rail_refleet = 1) aucune ligne rail ne pouvait donc
   * JAMAIS gagner un second train ni une seconde voie. Desormais inconditionnel. */
  if ((!RAIL_EXPAND && !RAIL_REFLEET) || this._railExpansion != null) return;
  /* Une recherche A* en cours (ligne neuve ou upgrade) : ne pas en empiler une seconde. */
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null) return;
  this._budget.begin();
  local best = null;
  local nEligible = 0;
  local nSaturated = 0;
  local nPersistent = 0;
  local nPositive = 0;
  foreach (line in this._lines) {
    /* G6§1 : quand on n'est entre QUE pour le refleet (rail_expand = 0, rail_refleet = 1),
     * l'expansion de wagons ne doit pas s'exercer -- on ne fait que traverser vers le bloc
     * RAIL_REFLEET, `best` restant nul. */
    if (!RAIL_EXPAND) break;
    if ((("mode" in line) && line.mode != "rail") || !("wagons" in line) || !("platformLength" in line) ||
        !("loco" in line) || !("kind" in line)) continue;
    if (line.trains != 1 || !("vehCount" in line) || line.vehCount != 1) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("lastProfit" in line) || line.lastProfit <= 0 ||
        !("lastRevenue" in line) || line.lastRevenue <= 0) continue;
    if (!(line.cargo in this._catalog.wagonByCargo)) continue;
    if (line.wagons >= OpexRailNominalMaxWagons(line.platformLength)) continue;
    nEligible++;

    local oldEcon = OpexRailFixedConsist(this._catalog, line.cargo, line.distance,
                                         line.kind, line.loco, line.wagons);
    local newEcon = OpexRailFixedConsist(this._catalog, line.cargo, line.distance,
                                         line.kind, line.loco, line.wagons + 1);
    if (oldEcon == null || newEcon == null || oldEcon.capacityRevenueAnnual <= 0) continue;

    local wagon = this._catalog.wagonByCargo[line.cargo];
    local waitingA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
    local waitingB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
    local waiting = line.kind == "freight" ? waitingA : waitingA + waitingB;
    local backlogThreshold = line.kind == "freight" ? wagon.capacity : 2 * wagon.capacity;
    local utilPermille = (line.lastRevenue * 1000) / oldEcon.capacityRevenueAnnual;
    if (utilPermille > 1000) utilPermille = 1000;
    local saturated = waiting >= backlogThreshold || utilPermille >= RAIL_EXPAND_UTIL_PERMILLE;
    if (saturated) nSaturated++;
    local priorStreak = ("expandStreak" in line) ? line.expandStreak : 0;
    /* Un tour de file peut finir sans qu'une annee de jeu passe. Ne jamais compter deux fois le
     * meme GetProfitLastYear / backlog comme deux confirmations independantes. */
    if (!("lastExpandCheckYear" in line) || line.lastExpandCheckYear != year) {
      line.expandStreak <- saturated ? priorStreak + 1 : 0;
      line.lastExpandCheckYear <- year;
    }
    if (line.expandStreak < RAIL_EXPAND_STREAK) continue;
    nPersistent++;

    local capacityDelta = newEcon.capacityRevenueAnnual - oldEcon.capacityRevenueAnnual;
    if (capacityDelta <= 0) continue;
    local grossGain = (line.lastRevenue * capacityDelta) / oldEcon.capacityRevenueAnnual;
    local marginalProfit = grossGain - newEcon.wagonRunningAnnual - newEcon.wagonAmortAnnual;
    if (marginalProfit <= 0) continue;
    nPositive++;

    local vehicle = null;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsPrimaryVehicle(v) &&
          AIVehicle.GetVehicleType(v) == AIVehicle.VT_RAIL) { vehicle = v; break; }
    }
    if (vehicle == null) continue;
    if (best == null || marginalProfit > best.gain) {
      best = { line = line, vehicle = vehicle, wagon = wagon, oldEcon = oldEcon,
               newEcon = newEcon, gain = marginalProfit, waiting = waiting,
               util = utilPermille };
    }
  }
  local decisionOps = this._budget.end("expand_rail_decide");
  /* La tache est aussi active en refleet-only (default livre : expand=0/refleet=1).
   * Publier EU dans les deux cas rend son execution observable au lieu de masquer le chemin
   * par defaut. Les compteurs d'expansion restent naturellement a zero si RAIL_EXPAND=0. */
  if (RAIL_EXPAND || RAIL_REFLEET) {
    OpexSign(AIMap.GetTileIndex(1, 1), "EU|" + (year % 100) + "|" + nEligible + "|"
             + nSaturated + "|" + nPersistent + "|" + nPositive + "|" + decisionOps);
  }
  if (best == null) {
    if (RAIL_REFLEET) {
      foreach (line in this._lines) {
        if ((("mode" in line) && line.mode != "rail") || !("wagons" in line) || !("loco" in line) || !("kind" in line)) continue;
        if (line.trains >= 2 || line.vehicles.len() >= 2) continue;
        if (("scrapping" in line) && line.scrapping) continue;
        if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
        if (!(line.cargo in this._catalog.wagonByCargo)) continue;

        local wagon = this._catalog.wagonByCargo[line.cargo];
        local waitingA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
        local waitingB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
        local waiting = line.kind == "freight" ? waitingA : waitingA + waitingB;
        local backlogThreshold = line.kind == "freight" ? (2 * wagon.capacity) : (4 * wagon.capacity);
        if (waiting < backlogThreshold) continue;

        // Cas 1 : Ligne deja doublee avec depot2 -> ajout immediat du 2e train
        if (("doubleTrack" in line) && line.doubleTrack == 1 && ("depot2" in line) && line.depot2 != null) {
          local trainCost = line.loco.price + line.wagons * wagon.price;
          local need = trainCost + OpexCashReserve();
          local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (money >= need) {
            local secondTrain = OpexBuildSecondTrain(this._catalog, line, OpexCashReserve());
            if (secondTrain.ok) {
              line.vehicles.append(secondTrain.train);
              line.trains = line.vehicles.len();
              line.vehCount <- line.vehicles.len();
              if (C50_CHRONOLOGY_PROBE) {
                if (C50_NON_EXPANSION_LEDGER != null) C50_NON_EXPANSION_LEDGER.rail.second_built++;
                OpexC50ChronologyLog("phase=fleet_built mode=rail line=" + line.lineId + " added=1 total=" + line.trains + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
              }
              local anchor = AIMap.GetTileIndex(1, 1);
              OpexSign(anchor, "RD|" + (year % 100) + "|" + line.lineId + "|" + line.trains);
              if (DECISION_LOG) {
                OpexDecide("RAIL_EXPAND", "action=second_train line=" + line.lineId + " trains=" + line.trains);
              }
              return;
            }
          } else if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
            local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
            if (!("c50_rail_cash_ym" in line) || line.c50_rail_cash_ym != ym) {
              line.c50_rail_cash_ym <- ym;
              C50_NON_EXPANSION_LEDGER.rail.cash_refused++;
            }
          }
        }
        // Cas 2 : Ligne a voie unique -> doublement d'infrastructure et 2e train
        else if ((!("doubleTrack" in line) || line.doubleTrack == 0) &&
                 ("platformA" in line) && ("platformB" in line) &&
                 line.platformA != null && line.platformB != null) {
          local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
          local trackCost = line.distance * this._catalog.costTrackPerTile + 2 * line.platformLength * this._catalog.costStation + depotCost;
          local trainCost = line.loco.price + line.wagons * wagon.price;
          local need = trackCost + trainCost + OpexCashReserve();
          local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (money >= need) {
            if (RAIL_SEARCH_RESUMABLE) {
              local prep = OpexPrepareUpgradeSearch(line, HARD_ITERATION_CAP);
              local anchor = AIMap.GetTileIndex(1, 1);
              if (!prep.ok) {
                if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
                  C50_NON_EXPANSION_LEDGER.rail.prep_failed++;
                }
                OpexSign(anchor, "RU|" + (year % 100) + "|" + line.lineId + "|" + prep.reason);
              } else {
                this._startRailUpgradeSearch(line, prep);
                return;
              }
            } else {
              local upgrade = OpexUpgradeRailLineToDoubleTrack(this._catalog, this._budget, line, OpexCashReserve(), HARD_ITERATION_CAP);
              local anchor = AIMap.GetTileIndex(1, 1);
              OpexSign(anchor, "RU|" + (year % 100) + "|" + line.lineId + "|" + upgrade.reason);
              if (DECISION_LOG) {
                OpexDecide("RAIL_EXPAND", "action=double_track line=" + line.lineId + " reason=" + upgrade.reason + " ok=" + (upgrade.ok ? 1 : 0));
              }
              if (upgrade.ok) {
                line.rawset("doubleTrack", 1);
                line.rawset("depot2", upgrade.depot2);
                line.rawset("stationA2", upgrade.stationA2);
                line.rawset("stationB2", upgrade.stationB2);
                line.rawset("platformA2", upgrade.platformA2);
                line.rawset("platformB2", upgrade.platformB2);
                line.vehicles.append(upgrade.train);
                line.trains = line.vehicles.len();
                line.vehCount <- line.vehicles.len();
                if (C50_CHRONOLOGY_PROBE) {
                  if (C50_NON_EXPANSION_LEDGER != null) C50_NON_EXPANSION_LEDGER.rail.double_built++;
                  OpexC50ChronologyLog("phase=fleet_built mode=rail line=" + line.lineId + " added=1 total=" + line.trains + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
                }
                return;
              } else if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
                if (upgrade.reason == "CASH") C50_NON_EXPANSION_LEDGER.rail.cash_refused++;
                else C50_NON_EXPANSION_LEDGER.rail.upgrade_failed++;
              }
            }
          } else if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
            local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
            if (!("c50_rail_cash_ym" in line) || line.c50_rail_cash_ym != ym) {
              line.c50_rail_cash_ym <- ym;
              C50_NON_EXPANSION_LEDGER.rail.cash_refused++;
            }
          }
        }
      }
    }
    return;
  }

  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = best.wagon.price + OpexCashReserve();
  if (money < need) {
    if (money < need) return;
  }

  local waitDays = (2 * best.oldEcon.oneWayDays).tointeger() + 60;
  if (waitDays < 120) waitDays = 120;
  if (waitDays > 730) waitDays = 730;
  this._railExpansion = {
    lineId = best.line.lineId, vehicle = best.vehicle, wagonId = best.wagon.id,
    oldWagons = best.line.wagons, newWagons = best.line.wagons + 1,
    oldTrainLength = AIVehicle.GetLength(best.vehicle),
    oldExpansionCount = ("railExpansions" in best.line) ? best.line.railExpansions : 0,
    decisionYear = year,
    newSpeed = best.newEcon.effectiveSpeed, newOneWayDays = best.newEcon.oneWayDays,
    gain = best.gain, waiting = best.waiting, util = best.util,
    decisionDate = AIDate.GetCurrentDate(), waitDays = waitDays,
    startDate = AIDate.GetCurrentDate(), phase = "approach", dispatchAttempts = 0,
    resumeAttempts = 0,
    temporaryOrder = false, temporaryOrderPosition = -1,
    /* Frontiere de commit persistable. build_started signifie volontairement "commande peut-etre
     * partie" : au reload on ne reconstruit jamais un second wagon sur cet etat ambigu. */
    commitStage = "idle", pendingWagon = -1,
    /* EU porte le cout de selection ; EX ne porte que dispatch + polls + construction, afin
     * que leur somme soit le debit total sans double comptage. */
    ops = 0, cost = 0,
  };
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "EG|" + (year % 100) + "|" + best.line.lineId + "|"
                   + best.line.wagons + "|" + (best.line.wagons + 1) + "|" + best.gain);
  OpexSign(anchor, "ES|" + (year % 100) + "|" + best.line.lineId + "|"
                   + best.waiting + "|" + best.util + "|" + best.line.expandStreak);
  if (DECISION_LOG) {
    OpexDecide("RAIL_EXPAND", "action=wagon_expansion line=" + best.line.lineId + " old_wagons=" + best.line.wagons + " new_wagons=" + (best.line.wagons + 1) + " gain=" + best.gain + " waiting=" + best.waiting + " util=" + best.util);
  }
  /* Si le train passe deja pres du depot, l'interception peut commencer dans ce meme tour. */
  if (AIVehicle.IsStoppedInDepot(best.vehicle) ||
      AIMap.DistanceManhattan(AIVehicle.GetLocation(best.vehicle), best.line.depot)
          <= RAIL_EXPAND_APPROACH_TILES) this._continueRailExpansion();
}
/* Avance la transaction sans attente bloquante. Tant que la rame est loin du depot, elle garde
 * ses ordres et son revenu normaux ; l'ordre d'arret temporaire n'est injecte qu'a l'approche. */
function OpexAI::_continueRailExpansion()
{
  if (this._railExpansion == null) return false;
  local state = this._railExpansion;
  local line = this._findLineById(state.lineId);
  local anchor = AIMap.GetTileIndex(1, 1);
  local year = AIDate.GetYear(AIDate.GetCurrentDate()) % 100;
  this._budget.begin();

  if (line == null || !AIVehicle.IsValidVehicle(state.vehicle)) {
    state.ops += this._budget.end("expand_rail_build");
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|V|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  if (state.phase == "resume") {
    local resumed = AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    if (resumed) {
      OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|K|" + state.ops + "|" + state.cost);
      this._railExpansion = null;
    } else {
      if (!("resumeAttempts" in state)) state.resumeAttempts <- 0;
      state.resumeAttempts++;
      if (state.resumeAttempts >= 3) {
        line.expandRetryCycle <- this._taskCycle + 3;
        OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|R|" + state.ops
                         + "|" + AIError.GetLastError());
        this._railExpansion = null;
      }
    }
    return true;
  }

  if (state.phase == "approach") {
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) {
      state.phase = "depot";
    } else {
      if (AIDate.GetCurrentDate() - state.decisionDate > state.waitDays) {
        state.ops += this._budget.end("expand_rail_dispatch");
        line.expandStreak <- 0;
        line.expandRetryCycle <- this._taskCycle + 3;
        OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|W|" + state.ops + "|0");
        this._railExpansion = null;
        return true;
      }
      if (!("depot" in line) || !AIRail.IsRailDepotTile(line.depot) ||
          AIMap.DistanceManhattan(AIVehicle.GetLocation(state.vehicle), line.depot)
              > RAIL_EXPAND_APPROACH_TILES) {
        state.ops += this._budget.end("expand_rail_dispatch");
        return true;
      }

      local dispatched = false;
      local position = AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT);
      if (position != AIOrder.ORDER_INVALID &&
          AIOrder.InsertOrder(state.vehicle, position, line.depot, AIOrder.OF_STOP_IN_DEPOT)) {
        if (AIOrder.SkipToOrder(state.vehicle, position)) {
          dispatched = true;
          state.temporaryOrder = true;
          state.temporaryOrderPosition = position;
        } else {
          AIOrder.RemoveOrder(state.vehicle, position);
        }
      }
      if (!dispatched) dispatched = AIVehicle.SendVehicleToDepot(state.vehicle);
      state.dispatchAttempts++;
      state.ops += this._budget.end("expand_rail_dispatch");
      if (!dispatched) {
        if (state.dispatchAttempts >= 3) {
          line.expandRetryCycle <- this._taskCycle + 3;
          OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|G|" + state.ops
                           + "|" + AIError.GetLastError());
          this._railExpansion = null;
        }
        return true;
      }
      state.phase = "depot";
      state.startDate = AIDate.GetCurrentDate();
      return true;
    }
  }

  if (!AIVehicle.IsStoppedInDepot(state.vehicle)) {
    if (AIDate.GetCurrentDate() - state.startDate > RAIL_EXPAND_TIMEOUT_DAYS) {
      if (state.temporaryOrder &&
          AIOrder.IsValidVehicleOrder(state.vehicle, state.temporaryOrderPosition)) {
        AIOrder.RemoveOrder(state.vehicle, state.temporaryOrderPosition);
      } else {
        /* Deuxieme appel = annulation documentee de l'ordre depot automatique. */
        AIVehicle.SendVehicleToDepot(state.vehicle);
      }
      state.ops += this._budget.end("expand_rail_build");
      line.expandStreak <- 0;
      line.expandRetryCycle <- this._taskCycle + 3;
      OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|T|" + state.ops + "|0");
      this._railExpansion = null;
      return true;
    }
    state.ops += this._budget.end("expand_rail_build");
    return true;
  }

  if (state.temporaryOrder) {
    if (AIOrder.IsValidVehicleOrder(state.vehicle, state.temporaryOrderPosition) &&
        AIOrder.IsGotoDepotOrder(state.vehicle, state.temporaryOrderPosition)) {
      if (!AIOrder.RemoveOrder(state.vehicle, state.temporaryOrderPosition)) {
        /* Ne jamais abandonner un train arrete avec notre ordre temporaire encore attache. */
        state.ops += this._budget.end("expand_rail_build");
        return true;
      }
    }
    state.temporaryOrder = false;
  }

  local depot = AIVehicle.GetLocation(state.vehicle);
  if (!AIRail.IsRailDepotTile(depot)) {
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|D|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }
  local wagonPrice = AIEngine.GetPrice(state.wagonId);
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < wagonPrice + OpexCashReserve()) {
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|C|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  local cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  state.commitStage = "build_started";
  state.pendingWagon = -1;
  local car = AIVehicle.BuildVehicle(depot, state.wagonId);
  if (!AIVehicle.IsValidVehicle(car)) {
    state.commitStage = "idle";
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|B|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  state.pendingWagon = car;
  state.commitStage = "wagon_built";
  if (AIVehicle.GetLength(state.vehicle) + AIVehicle.GetLength(car) > line.platformLength * 16) {
    AIVehicle.SellVehicle(car);
    state.pendingWagon = -1;
    state.commitStage = "idle";
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandBlocked <- true;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|L|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }
  if (!AIVehicle.MoveWagon(car, 0, state.vehicle, 0)) {
    if (AIVehicle.IsValidVehicle(car)) AIVehicle.SellVehicle(car);
    state.pendingWagon = -1;
    state.commitStage = "idle";
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|M|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  state.pendingWagon = -1;
  state.commitStage = "wagon_moved";
  state.cost = cashBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  line.wagons = state.newWagons;
  line.wagonId <- state.wagonId;
  line.effectiveSpeed = state.newSpeed;
  line.predOneWayDays = state.newOneWayDays;
  line.headwayDays = 2 * state.newOneWayDays;
  line.expandStreak <- 0;
  local expansionCount = ("railExpansions" in line) ? line.railExpansions : 0;
  line.railExpansions <- expansionCount + 1;
  line.lastExpansionYear <- AIDate.GetYear(AIDate.GetCurrentDate());
  state.commitStage = "metadata_done";
  state.phase = "resume";
  local resumed = AIVehicle.StartStopVehicle(state.vehicle);
  state.ops += this._budget.end("expand_rail_build");
  if (resumed) {
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|K|" + state.ops + "|" + state.cost);
    this._railExpansion = null;
  }
  return true;
}
/* Demarre une recherche A* ferroviaire reprenable. Premiere tranche dans ce tour ; si elle
 * ne suffit pas, l'etat vit dans this._railSearch et _continueRailSearch reprend au suivant.
 * Fonction de classe, pas une closure : Squirrel ne capture jamais les locales englobantes. */
function OpexAI::_startRailSearch(candidate, alternativeRatio, hardCap, posPacked)
{
  local plan = OpexPrepareRailRoute(this._catalog, this._budget, candidate, alternativeRatio, hardCap);
  if (plan.plansA == null) return { pending = false, plan = plan };
  local pathfinder = null;
  local segmented = null;
  if (RAIL_SEGMENTED_SEARCH) {
    segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, plan.iterationBudget, null);
    if (segmented == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + plan.iterationBudget);
      plan.reason = "NOPA";
      return { pending = false, plan = plan };
    }
  } else {
    pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, null);
    if (pathfinder == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + plan.iterationBudget);
      plan.reason = "NOPA";
      return { pending = false, plan = plan };
    }
  }
  local curDate = AIDate.GetCurrentDate();
  local curTick = AIController.GetTick();
  if (C56_TASK_TRACE) {
    if (!("v89SelectedDate" in candidate)) candidate.v89SelectedDate <- curDate;
    else candidate.v89SelectedDate = curDate;
    if (!("v89SelectedTick" in candidate)) candidate.v89SelectedTick <- curTick;
    else candidate.v89SelectedTick = curTick;
  }
  this._railSearch = {
    kind = "primary",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = plan.iterationBudget,
    /* Borne horaire large : le budget d'iterations est la vraie limite (piege 1). */
    safetyDeadline = curTick + RAIL_SEARCH_SAFETY_TICKS,
    plan = plan,
    candidate = candidate,
    alternativeRatio = alternativeRatio,
    hardCap = hardCap,
    posPacked = posPacked,
    startDate = curDate,
    startTick = curTick,
  };
  if (C56_TASK_TRACE) {
    OpexC56TaskLog("RAIL_SEARCH_START", "primary", this._taskCycle,
                   "src=" + candidate.src + " dst=" + candidate.dst
                   + " budget=" + plan.iterationBudget + " hard_cap=" + hardCap);
  }
  if (C80_DOUBLE_REGISTER && C80_WORKER_RAIL) {
    if (this._activeWorker == null || this._activeWorker.kind == "rail_search") {
      this._activeWorker = {
        kind = "rail_search",
        state = {
          ai = this,
          search = this._railSearch
        }
      };
    }
  }
  this._continueRailSearch();
  if (this._railSearch == null) {
    if (C80_DOUBLE_REGISTER && C80_WORKER_RAIL && this._activeWorker != null && this._activeWorker.kind == "rail_search") {
      this._activeWorker = null;
    }
    return { pending = false, plan = (("railPlan" in candidate) ? candidate.railPlan : plan) };
  }
  if (this._railSearch.phase == "build") {
    local completed = candidate.railPlan;
    this._railSearch = null;
    if (C80_DOUBLE_REGISTER && C80_WORKER_RAIL && this._activeWorker != null && this._activeWorker.kind == "rail_search") {
      this._activeWorker = null;
    }
    return { pending = false, plan = completed };
  }
  return { pending = true, plan = null };
}
/* Avance d'une tranche, ou consomme un plan/upgrade pret. Appele en TETE de _runNextTask. */
function OpexAI::_continueRailSearch()
{
  if (this._railSearch == null) return;
  local state = this._railSearch;
  if (state.phase == "build") {
    if (state.kind == "upgrade") this._consumeRailUpgrade();
    return;
  }
  if (state.phase != "search") return;

  this._budget.begin();
  local deadlineTick = state.safetyDeadline;
  if (RAIL_MICRO_DEADLINE) {
    /* C20 : echeance locale par micro-etape. 50 iters prennent ~17 ticks ; BUILD_TICK_MARGIN (3000)
     * laisse une large marge de securite contre un blocage dans la tranche sans jamais
     * imputer le temps des autres taches de la file (docs/cible.md §2.1). */
    deadlineTick = AIController.GetTick() + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;
  }
  local slice;
  local spentBefore = state.spent;
  if (("segmented" in state) && state.segmented != null) {
    slice = OpexAdvanceSegmentedSearch(state.segmented, RAIL_SEARCH_SLICE, deadlineTick);
  } else {
    slice = OpexAdvanceRailPathfinder(state.pathfinder, state.spent, state.iterationBudget,
                                      deadlineTick, RAIL_SEARCH_SLICE);
  }
  /* spent est le CUMUL de toutes les tranches : c'est le denominateur du classement. */
  state.spent = slice.iterations;
  local sliceIters = state.spent - spentBefore;
  if (C56_TASK_TRACE) {
    this._v89YearIters += sliceIters;
    this._v89YearSlices++;
  }
  if (state.kind == "primary") {
    state.plan.opcodes += this._budget.end("build_search");
    state.plan.iterations = state.spent;
  } else {
    this._budget.end("build_search");
  }
  if (C56_TASK_TRACE) {
    OpexC56TaskLog("RAIL_SLICE", (state.kind == "primary" ? "primary" : "upgrade"), this._taskCycle,
                   "slice_iters=" + sliceIters + " spent=" + state.spent
                   + " budget=" + state.iterationBudget + " done=" + (slice.done ? 1 : 0)
                   + " stop=" + slice.stop);
  }
  if (!slice.done) {
    /* C41.48 : sonde passive a chaque frontiere de tranche (slice.stop == "CONT" ici, la SEULE
     * valeur qui rend done=false -- OpexSegmentedResult, builder_rail.nut). Rien n'est coupe :
     * mesure si un test de domination (C41.49) aurait seulement l'occasion de se declencher.
     * kind == "primary" seulement : une recherche d'upgrade n'a ni candidate ni profit/capital
     * au meme sens (state.line, pas state.candidate). */
    if (C41_RAIL_DOMINATION_PROBE && state.kind == "primary"
        && ("segmented" in state) && state.segmented != null) {
      local seg = state.segmented;
      local prefixLen = (seg.prefix != null) ? seg.prefix.len() : 0;
      local distRemaining = -1;
      if (prefixLen > 0) {
        distRemaining = AIMap.DistanceManhattan(seg.prefix[prefixLen - 1], seg.destinationCenter);
      }
      /* Le meilleur projet FINANCABLE, pas seulement le mieux classe : rang 0 peut deja etre
       * le candidat rail en cours de recherche (capital estime, pas encore construit) ou un
       * projet hors de portee de la caisse -- OpexAvailableCapital() est la meme formule
       * centralisee que _consumeRailSearch/_tryBuildProjects utilisent pour decider. */
      local bestRank = -1;
      local bestMode = "none";
      local bestScore = 0;
      local bestCost = 0;
      if (this._projects != null && this._projects.best != null) {
        local available = OpexAvailableCapital();
        for (local i = 0; i < this._projects.best.len(); i++) {
          local p = this._projects.best[i];
          if (p == null || p.capital > available) continue;
          bestRank = i;
          bestMode = p.mode;
          bestScore = p.budgetScore;
          bestCost = p.capital;
          break;
        }
      }
      OpexC41RailDominationLog("src=" + state.candidate.src + " dst=" + state.candidate.dst
          + " spent=" + state.spent + " remaining=" + (state.iterationBudget - state.spent)
          + " segments=" + slice.segments + " backtracks=" + slice.backtracks
          + " prefix_len=" + prefixLen + " dist_remaining=" + distRemaining
          + " rail_profit=" + state.candidate.profitAnnual + " rail_capital=" + state.candidate.capital
          + " best_rank=" + bestRank + " best_mode=" + bestMode + " best_score=" + bestScore
          + " best_cost=" + bestCost);
    }
    return;
  }

  if (DECISION_LOG) {
    OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " iters=" + state.spent + " budget=" + state.iterationBudget);
  }

  if (state.kind == "primary") {
    if (C56_TASK_TRACE) {
      local curDate = AIDate.GetCurrentDate();
      local curTick = AIController.GetTick();
      if (!("v89SearchEndDate" in state.candidate)) state.candidate.v89SearchEndDate <- curDate;
      else state.candidate.v89SearchEndDate = curDate;
      if (!("v89SearchEndTick" in state.candidate)) state.candidate.v89SearchEndTick <- curTick;
      else state.candidate.v89SearchEndTick = curTick;
      local searchDays = ("startDate" in state) ? (curDate - state.startDate) : -1;
      local searchTicks = ("startTick" in state) ? (curTick - state.startTick) : -1;
      local outcome = slice.stop;
      local result = (outcome == "OK") ? "found" : ((outcome == "ABND" || outcome == "DEAD") ? "cap" : "none");
      local pathLen = (outcome == "OK" && slice.path != null && slice.path != false) ? OpexResolveSearchTiles(slice).len() : 0;
      local weightUsed = (V90_FAST_PATHFINDER) ? V91_ASTAR_WEIGHT_PCT : 100;
      OpexC56TaskLog("RAIL_SEARCH_END", "primary", this._taskCycle,
                     "src=" + state.candidate.src + " dst=" + state.candidate.dst
                     + " outcome=" + outcome + " result=" + result + " iters=" + state.spent
                     + " len=" + pathLen + " weight=" + weightUsed
                     + " budget=" + state.iterationBudget + " days=" + searchDays
                     + " ticks=" + searchTicks);
    }
    if (V88_GOODS_CHAIN && (DECISION_LOG || C56_TASK_TRACE) && state.candidate != null) {
      if (("isChainStep1" in state.candidate) && state.candidate.isChainStep1) {
        local pathLen = (slice.stop == "OK" && slice.path != null && slice.path != false) ? OpexResolveSearchTiles(slice).len() : 0;
        local weightUsed = (V90_FAST_PATHFINDER) ? V91_ASTAR_WEIGHT_PCT : 100;
        OpexV88Log("CHAIN_SEARCH_END", "step=1 iters=" + state.spent + " len=" + pathLen
                   + " weight=" + weightUsed + " outcome=" + slice.stop);
      } else if (("isChainStep2" in state.candidate) && state.candidate.isChainStep2) {
        local pathLen = (slice.stop == "OK" && slice.path != null && slice.path != false) ? OpexResolveSearchTiles(slice).len() : 0;
        local weightUsed = (V90_FAST_PATHFINDER) ? V91_ASTAR_WEIGHT_PCT : 100;
        OpexV88Log("CHAIN_SEARCH_END", "step=2 iters=" + state.spent + " len=" + pathLen
                   + " weight=" + weightUsed + " outcome=" + slice.stop);
      }
    }
    local plan = OpexCompleteRailRouteAfterSearch(this._catalog, state.candidate, state.plan, slice);
    state.candidate.railPlan <- plan;
    state.pathfinder = null;
    state.phase = "build";
    return;
  }
  if (state.kind == "upgrade") {
    if (C56_TASK_TRACE) {
      local outcome = slice.stop;
      local result = (outcome == "OK") ? "found" : ((outcome == "ABND" || outcome == "DEAD") ? "cap" : "none");
      local pathLen = (outcome == "OK" && slice.path != null && slice.path != false) ? OpexResolveSearchTiles(slice).len() : 0;
      local weightUsed = (V90_FAST_PATHFINDER) ? V91_ASTAR_WEIGHT_PCT : 100;
      OpexC56TaskLog("RAIL_SEARCH_END", "upgrade", this._taskCycle,
                     "outcome=" + outcome + " result=" + result + " iters=" + state.spent
                     + " len=" + pathLen + " weight=" + weightUsed
                     + " budget=" + state.iterationBudget);
    }
    /* `search` n'existe pas dans l'etat initial : en Squirrel, une nouvelle
     * cle de table exige `<-`, sinon le premier upgrade leve une exception. */
    state.search <- slice;
    state.pathfinder = null;
    state.phase = "build";
    return;
  }
}
/* Consomme le railPlan produit par la recherche reprenable et conserve le motif
 * d'echec pour les ledgers de la passe appelante. */
function OpexAI::_consumeRailSearch(year)
{
  if (V88_GOODS_CHAIN && this._railSearch != null && ("candidate" in this._railSearch)
      && this._railSearch.candidate != null && ("isChainStep2" in this._railSearch.candidate)) {
    OpexV88Log("CHAIN_CONSUME", "step=2");
  }
  local state = this._railSearch;
  local candidate = state.candidate;
  /* G3§1 : Un plan en echec (ABND/NOPA/DEAD) n'a besoin d'aucune tresorerie : OpexBuildLine
   * retourne immediatement sans construction. Le test de cash ne doit pas bloquer un plan
   * invalide en phase build indefiniment, sinon _railSearch ne se libere jamais et le
   * pipeline rail est neutralise (l'echec n'est pas non plus transmis a C22). */
  local planFailed = ("railPlan" in candidate) && candidate.railPlan != null
                     && !candidate.railPlan.ok;
  if (!planFailed) {
    local need = candidate.capital + OpexCashReserve();
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("rail", -1, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
      /* C41.47 : pendant de la garde G3S1 ci-dessus, applique au motif tresorerie -- des le
       * premier blocage constate, liberer _railSearch pour que _expandRailLines et les AUTRES
       * candidats rail du portefeuille ne soient plus geles (main.nut:4445, 2574). candidate.
       * railPlan n'est PAS efface : OpexBuildLine le reutilise deja sans replanification quand
       * la carte n'a pas change (main G3S2), donc rien a revalider en plus du chemin existant. */
      if (C41_RAIL_CASH_RELEASE) {
        this._railSearch = null;
        OpexC41RailCashReleaseLog("reason=precheck src=" + candidate.src + " dst=" + candidate.dst
                                  + " need=" + need + " money=" + money);
      }
      if (("isChainStep2" in candidate) && candidate.isChainStep2) OpexV88Log("CHAIN_WAIT", "step=2 reason=cash_after_search need=" + need + " money=" + money);
      return { outcome = "cash", reason = "insufficient_cash", error = 0 };
    }
  }

  local result = OpexBuildLine(this._catalog, this._budget, candidate, state.alternativeRatio,
                               OpexCashReserve(), state.hardCap);
  /* Ne pas jeter le plan sur CASH : on reessaiera au prochain tour, sans refaire l'A*. */
  if (result.reason == "CASH") {
    if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("rail", -1, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, candidate.capital, AICompany.GetBankBalance(AICompany.COMPANY_SELF));
    if (C41_RAIL_CASH_RELEASE) {
      this._railSearch = null;
      OpexC41RailCashReleaseLog("reason=build_cash src=" + candidate.src + " dst=" + candidate.dst
                                + " capital=" + candidate.capital);
    }
    local cashError = ("error" in result) ? result.error : 0;
    return { outcome = "cash", reason = "cash_at_build", error = cashError };
  }
  candidate.railPlan = null;
  local built = this._recordRailAttempt(candidate, result, state.posPacked, year);
  local reason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
  local error = ("error" in result) ? result.error : 0;
  if (("isChainStep1" in candidate) && candidate.isChainStep1) {
    local anchor = AIMap.GetTileIndex(1, 1);
    local yy = year % 100;
    if (built) {
      local inputLine = this._lines[this._lines.len() - 1];
      local chainParent = candidate.chainParent;
      this._setActiveGoodsChain({
        step = 2,
        factoryId = chainParent.factoryId,
        townId = chainParent.dstTown,
        inputLineId = inputLine.lineId,
        factoryStationId = inputLine.stationB,
        factoryPlatform = {
          anchor = inputLine.platformB.anchor,
          direction = inputLine.platformB.direction,
          length = inputLine.platformB.length,
          step = inputLine.platformB.step
        },
        goodsCandidate = chainParent.goodsCandidate,
        year = year
      });
      OpexV88Log("CHAIN_STEP1", "line=" + inputLine.lineId + " fact=" + chainParent.factoryId);
      OpexSign(anchor, "C1|" + yy + "|" + inputLine.lineId + "|" + chainParent.factoryId);
    } else {
      this._setActiveGoodsChain(null);
      OpexV88Log("CHAIN_FAIL", "step=1 reason=" + result.reason);
      OpexSign(anchor, "CF|" + yy + "|1|" + OpexAttemptReasonCode(result.reason));
    }
  } else if (("isChainStep2" in candidate) && candidate.isChainStep2) {
    local anchor = AIMap.GetTileIndex(1, 1);
    local yy = year % 100;
    if (built) {
      local goodsLine = this._lines[this._lines.len() - 1];
      OpexV88Log("CHAIN_STEP2", "line=" + goodsLine.lineId + " town=" + candidate.townId);
      OpexSign(anchor, "C2|" + yy + "|" + goodsLine.lineId + "|" + candidate.townId);
      this._setActiveGoodsChain(null);
    } else {
      OpexV88Log("CHAIN_FAIL", "step=2 reason=" + result.reason);
      OpexSign(anchor, "CF|" + yy + "|2|" + OpexAttemptReasonCode(result.reason));
      this._markPairAbandoned(OpexAbandonedPairKey(candidate));
      this._setActiveGoodsChain(null);
    }
  }
  return { outcome = built ? "built" : "failed", reason = reason, error = error };
}
/* Panneaux + enregistrement d'une tentative rail, reussie ou non. Facteur commun au chemin
 * bloquant et au chemin reprenable, pour que le denominateur (result.iterations) et les
 * panneaux OR/OB restent identiques. */
function OpexAI::_recordRailAttempt(candidate, result, posPacked, year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  local budgetInfo = (("budgetInfo" in result) && result.budgetInfo != null)
      ? result.budgetInfo : { path = "Z" };
  local iterationBudget = ("iterationBudget" in result) ? result.iterationBudget : 0;
  OpexSign(anchor, "OR|" + yy + "|" + this._nextLineId + "|" + posPacked
                           + "|" + budgetInfo.path + "S"
                           + OpexAttemptReasonCode(result.reason) + "|" + iterationBudget
                           + "|" + result.iterations);
  /* Bras experimental seulement. Sous 31 caracteres : SG|yy|lineId|seg|bt|loc. */
  if (RAIL_SEGMENTED_SEARCH) {
    local segs = ("segmentedSegments" in result) ? result.segmentedSegments : 0;
    local backs = ("segmentedBacktracks" in result) ? result.segmentedBacktracks : 0;
    local locs = ("segmentedLocalChoices" in result) ? result.segmentedLocalChoices : 0;
    OpexSign(anchor, "SG|" + yy + "|" + this._nextLineId + "|" + segs + "|" + backs + "|" + locs);
  }
  OpexSign(anchor, "OB|A|" + yy + "|" + this._nextLineId + "|" + posPacked
                           + "|" + result.opcodes + "|" + candidate.distance);
  if (result.reason == "SITEA" || result.reason == "SITEB" || result.reason == "SITEAB") {
    OpexSign(anchor, "PS|" + yy + "|" + this._nextLineId + "|" + posPacked
                            + "|" + result.siteClear + "|" + result.siteCargo + "|"
                            + result.siteCmd + "|" + result.siteKind + "|N");
  }
  if (result.error != 0) OpexSign(anchor, "OV|" + this._nextLineId + "|" + result.error);
  if (C63_INVEST_PROBE) {
    local railPlanned = ("capital" in result) ? result.capital : candidate.capital;
    local railActual = ("actualCost" in result) ? result.actualCost : 0;
    OpexC63RecordSpend("rail", railPlanned, railActual, result.ok);
  }

  if (DECISION_LOG) {
    /* C67.6 rail : une ligne par tentative, reussie ou non, pour l'exposition du cout terrain. */
    OpexDecide("RAIL_ATTEMPT", "src=" + candidate.src + " dst=" + candidate.dst
               + " kind=" + candidate.kind + " manh=" + candidate.distance
               + " pre=" + (("preCapital" in candidate) ? candidate.preCapital : -1)
               + " model=" + (("modelCapital" in candidate) ? candidate.modelCapital : -1)
               + " quote=" + (("capital" in result) ? result.capital : -1)
               + " actual=" + (("actualCost" in result) ? result.actualCost : -1)
               + " ok=" + (result.ok ? 1 : 0) + " reason=" + (result.reason == "" ? "-" : result.reason)
               + " iters=" + result.iterations + " ops=" + result.opcodes);
    if (result.ok) {
      local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
      OpexDecide("RAIL_BUILD", "line=" + this._nextLineId + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " cost=" + result.actualCost + " trains=" + result.trains + " wagons=" + result.wagons);
    } else {
      OpexDecide("RAIL_BUILD_FAIL", "line=" + this._nextLineId + " reason=" + result.reason + " error=" + result.error + " iters=" + result.iterations + " budget=" + iterationBudget);
    }
  }

  if (result.ok) {
    local idx = this._nextLineId;
    if (C56_TASK_TRACE) {
      local curDate = AIDate.GetCurrentDate();
      local selectDate = ("v89SelectedDate" in candidate) ? candidate.v89SelectedDate : -1;
      local searchEndDate = ("v89SearchEndDate" in candidate) ? candidate.v89SearchEndDate : -1;
      local delaySelectDays = (selectDate >= 0) ? (curDate - selectDate) : -1;
      local delaySearchDays = (searchEndDate >= 0) ? (curDate - searchEndDate) : -1;
      OpexC56TaskLog("RAIL_COMMISSION", "primary", this._taskCycle,
                     "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst
                     + " cost=" + result.capital + " dist=" + candidate.distance + " trains=" + result.trains
                     + " iters=" + result.iterations + " delay_days=" + delaySelectDays
                     + " search_to_service_days=" + delaySearchDays);
    }
    local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
    OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
    OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
    OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
    OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains
                            + "|" + candidate.wagons + "|" + candidate.perTrain);
    OpexSign(anchor, "PT|" + idx + "|" + candidate.offered.tointeger() + "|"
                            + candidate.monthlyCapacity.tointeger() + "|"
                            + candidate.headwayDays.tointeger() + "|"
                            + candidate.stationRating.tointeger() + "|"
                            + candidate.trainsForHeadway);
    OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays.tointeger() + "|" + candidate.distance
                            + "|" + candidate.platformLength + "|" + candidate.effectiveSpeed.tointeger());
    OpexSign(anchor, "OL|" + idx + "|" + candidate.loco.id + "|" + candidate.loco.speed
                            + "|" + candidate.effectiveSpeed.tointeger() + "|" + candidate.loco.power
                            + "|" + candidate.loco.tractiveEffort);
    OpexSign(anchor, "PL|" + idx + "|" + result.platformLength + "|" + result.wagons
                            + "|" + result.trainLength + "|" + result.locoLength
                            + "|" + result.wagonLength);
    OpexSign(anchor, "PD|" + idx + "|" + result.wantedPlatformLength + "|"
                            + result.platformLength + "|" + result.plansA + "|"
                            + result.plansB + "|" + result.slopeRelaxed);
    OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                             + "|" + candidate.monthly);
    OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
    if (RAIL_COST_PROBE) {
      OpexSign(anchor, "DC|" + idx + "|" + result.capital + "|" + result.actualCost + "|"
                             + candidate.trains + "|" + result.trains + "|"
                             + result.doubleTrack);
    }
    if (isPaxNear) OpexSign(anchor, "PY|" + idx);

    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = candidate.profitAnnual, iterations = result.iterations,
      trains = result.trains, trains0 = result.trains, distance = candidate.distance, year = year,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      wagons = candidate.wagons, platformLength = result.platformLength,
      monthly = candidate.monthly, wagonId = this._catalog.wagonByCargo[candidate.cargo].id,
      loco = candidate.loco, effectiveSpeed = candidate.effectiveSpeed,
      headwayDays = candidate.headwayDays, stationRating = candidate.stationRating,
      vehicles = result.vehicles, platformA = result.platformA, platformB = result.platformB,
      depot = result.depot,
      doubleTrack = ("doubleTrack" in result) ? result.doubleTrack : 0,
      depot2 = ("depot2" in result) ? result.depot2 : null,
      stationA2 = ("stationA2" in result) ? result.stationA2 : null,
      stationB2 = ("stationB2" in result) ? result.stationB2 : null,
      platformA2 = ("platformA2" in result) ? result.platformA2 : null,
      platformB2 = ("platformB2" in result) ? result.platformB2 : null,
      mode = "rail", kind = candidate.kind,
      srcIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.src) : -1,
      dstIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.dst) : -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.trains, suspectedCrashes = 0,
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = idx,
    });
    this._nextLineId++;
    if (C76_REGEN_TARGETED) this._c76BumpLayer("lines", false);
    return true;
  }
  if (RAIL_COST_PROBE && ("actualCost" in result) && result.actualCost != 0) {
    OpexSign(anchor, "DC|" + this._nextLineId + "|" + result.capital + "|" + result.actualCost + "|"
                           + candidate.trains + "|0|0");
  }
  if (ABANDON_MEMORY && (result.reason == "ABND" || result.reason == "SITEA" || result.reason == "SITEB" ||
                         result.reason == "SITEAB" || result.reason == "NOPA" || result.reason == "STNFAIL")) {
    this._markPairAbandoned(OpexAbandonedPairKey(candidate));
  }
  return false;
}
function OpexAI::_startRailUpgradeSearch(line, prep)
{
  local pathfinder = null;
  local segmented = null;
  if (RAIL_SEGMENTED_SEARCH) {
    segmented = OpexCreateSegmentedSearch(prep.dualA, prep.dualB, prep.iterationBudget, prep.ignored);
    if (segmented == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + prep.iterationBudget);
      OpexSign(AIMap.GetTileIndex(1, 1), "RU|" + (AIDate.GetYear(AIDate.GetCurrentDate()) % 100)
               + "|" + line.lineId + "|NOPATH");
      return;
    }
  } else {
    pathfinder = OpexCreateRailPathfinder(prep.dualA, prep.dualB, prep.ignored);
    if (pathfinder == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + prep.iterationBudget);
      OpexSign(AIMap.GetTileIndex(1, 1), "RU|" + (AIDate.GetYear(AIDate.GetCurrentDate()) % 100)
               + "|" + line.lineId + "|NOPATH");
      return;
    }
  }
  this._railSearch = {
    kind = "upgrade",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = prep.iterationBudget,
    safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
    line = line,
    prep = prep,
  };
  if (C80_DOUBLE_REGISTER && C80_WORKER_RAIL) {
    if (this._activeWorker == null || this._activeWorker.kind == "rail_search") {
      this._activeWorker = {
        kind = "rail_search",
        state = {
          ai = this,
          search = this._railSearch
        }
      };
    }
  }
  this._continueRailSearch();
  if (this._railSearch == null || this._railSearch.phase != "search") {
    if (C80_DOUBLE_REGISTER && C80_WORKER_RAIL && this._activeWorker != null && this._activeWorker.kind == "rail_search") {
      this._activeWorker = null;
    }
  }
}
function OpexAI::_consumeRailUpgrade()
{
  local state = this._railSearch;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local upgrade = OpexExecuteUpgradeAfterSearch(this._catalog, this._budget, state.line,
                                                OpexCashReserve(), state.search, state.prep);
  /* Appliquer au doublement la meme politique de liberation cash que pour
   * une recherche primaire, sinon l'unique slot _railSearch gele tout le rail. */
  if (upgrade.reason == "CASH") {
    if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (!("c50_rail_cash_ym" in state.line) || state.line.c50_rail_cash_ym != ym) {
        state.line.c50_rail_cash_ym <- ym;
        C50_NON_EXPANSION_LEDGER.rail.cash_refused++;
      }
    }
    if (C41_RAIL_CASH_RELEASE) {
      OpexC41RailCashReleaseLog("reason=upgrade_cash line=" + state.line.lineId);
      this._railSearch = null;
    }
    return;
  }
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "RU|" + (year % 100) + "|" + state.line.lineId + "|" + upgrade.reason);
  if (DECISION_LOG) {
    OpexDecide("RAIL_EXPAND", "action=double_track line=" + state.line.lineId + " reason=" + upgrade.reason + " ok=" + (upgrade.ok ? 1 : 0));
  }
  if (upgrade.ok) {
    local line = state.line;
    line.rawset("doubleTrack", 1);
    line.rawset("depot2", upgrade.depot2);
    line.rawset("stationA2", upgrade.stationA2);
    line.rawset("stationB2", upgrade.stationB2);
    line.rawset("platformA2", upgrade.platformA2);
    line.rawset("platformB2", upgrade.platformB2);
    line.vehicles.append(upgrade.train);
    line.trains = line.vehicles.len();
    line.vehCount <- line.vehicles.len();
    if (C50_CHRONOLOGY_PROBE) {
      if (C50_NON_EXPANSION_LEDGER != null) C50_NON_EXPANSION_LEDGER.rail.double_built++;
      OpexC50ChronologyLog("phase=fleet_built mode=rail line=" + line.lineId + " added=1 total=" + line.trains + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
    }
  } else if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
    C50_NON_EXPANSION_LEDGER.rail.upgrade_failed++;
  }
  this._railSearch = null;
}

/* ============================================================================
 * C80 Étape 2 : Worker RailSearchStock autonome (N=1) sur reliquat
 * ============================================================================ */

/* C80 étape 2 : met à jour le seuil de sélection mémorisé à partir du dernier projet financé
 * lors de la dernière sélection qui a financé au moins un projet.
 * Mémoire transitoire (vidée au chargement). Si aucune sélection n'a encore financé de projet,
 * le seuil reste à 0.0 (pas de filtre). */
function OpexAI::_updateRailStockSelectionThreshold()
{
  if (!C80_RAIL_STOCK_WORKER || !C80_RAIL_STOCK_GATE) return;
  if (this._projects == null || !("best" in this._projects) || this._projects.best == null) return;
  if (this._projects.best.len() == 0) return;

  local lastFunded = this._projects.best[this._projects.best.len() - 1];
  if (lastFunded != null && ("fundScore" in lastFunded) && lastFunded.fundScore != null) {
    this._railStockLastFundedScore = lastFunded.fundScore;
    this._railStockLastFundedDate = AIDate.GetCurrentDate();
  }
}

/* C80 étape 2 : sélectionne le meilleur candidat rail de tête et lance sa recherche de stock.
 * Règle §2.2.B : liste ordonnée existante, pas de balayage du vivier, filtres de trésorerie et cooldown.
 * Révision 3.2 ter : seuil = fundScore du dernier projet financé à la dernière sélection non vide. */
function OpexAI::_tryStartRailStockWorker()
{
  if (!C80_RAIL_STOCK_WORKER || !C80_RAIL_STOCK_GATE) return false;
  this._updateRailStockSelectionThreshold();
  if (this._railReadyStock.len() >= 1) return false;
  if (this._railSearch != null) return false;
  if (this._projects == null) return false;

  local railCandidates = null;
  if (("rail" in this._projects) && this._projects.rail != null) {
    if (("best" in this._projects.rail) && this._projects.rail.best != null && this._projects.rail.best.len() > 0) {
      railCandidates = this._projects.rail.best;
    } else if (("candidates" in this._projects.rail) && this._projects.rail.candidates != null) {
      railCandidates = this._projects.rail.candidates;
    }
  }
  if (railCandidates == null || railCandidates.len() == 0) return false;

  // Seuil de score grossier : fundScore du dernier projet financé lors de la dernière sélection non vide.
  // Question posée : « ce candidat aurait-il été financé à la dernière vraie sélection ? ».
  // Si aucune sélection n'a encore financé de projet (début de partie), le seuil reste à 0.0 (aucun filtre).
  local threshold = this._railStockLastFundedScore;
  local thresholdDate = this._railStockLastFundedDate;

  local available = OpexAvailableCapital();
  local maxCost = (available * 3) / 2;
  if (maxCost < 30000) maxCost = 30000;
  local curDate = AIDate.GetCurrentDate();

  foreach (candidate in railCandidates) {
    if (candidate == null) continue;
    local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
    if (pairKey in this._railReadyStock) continue;
    if (pairKey in this._railStockCooldown) {
      if (curDate <= this._railStockCooldown[pairKey]) continue;
      delete this._railStockCooldown[pairKey];
    }
    local abndKey = OpexAbandonedPairKey(candidate);
    if (abndKey in this._abandonedPairs) continue;
    if (candidate.capital > maxCost) continue;

    if (candidate.kind != "pax") {
      if (!AIIndustry.IsValidIndustry(candidate.src) || !AIIndustry.IsValidIndustry(candidate.dst)) continue;
    }

    local paperProject = OpexProjectFromCandidate(candidate);
    if (paperProject == null) continue;
    local paperFinanceCapital = OpexProjectFinanceCapital(paperProject);
    local paperProfit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(paperProject) : paperProject.profitAnnual;
    local coarseFundScore = OpexProjectScore(paperProfit, paperFinanceCapital);

    if (threshold > 0.0 && coarseFundScore < threshold) {
      if (C56_TASK_TRACE) {
        local thresholdDateStr = (thresholdDate >= 0)
            ? (AIDate.GetYear(thresholdDate) + "-" + AIDate.GetMonth(thresholdDate) + "-" + AIDate.GetDayOfMonth(thresholdDate))
            : "none";
        OpexC56TaskLog("RAIL_STOCK_SKIP_BELOW_THRESHOLD", "rail_stock", this._taskCycle,
                       "src=" + candidate.src + " dst=" + candidate.dst
                       + " score=" + coarseFundScore + " threshold=" + threshold
                       + " threshold_date=" + thresholdDateStr);
      }
      continue;
    }

    return this._startRailStockSearch(candidate, false, null, coarseFundScore);
  }

  return false;
}

/* C80 étape 2 : initialise la recherche A* d'un candidat de tête pour le stock de tracés. */
function OpexAI::_startRailStockSearch(candidate, isRepair = false, repairReason = null, coarseScore = null)
{
  if (coarseScore == null) {
    local paperProject = OpexProjectFromCandidate(candidate);
    if (paperProject != null) {
      local paperFinanceCapital = OpexProjectFinanceCapital(paperProject);
      local paperProfit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(paperProject) : paperProject.profitAnnual;
      coarseScore = OpexProjectScore(paperProfit, paperFinanceCapital);
    } else {
      coarseScore = 0.0;
    }
  }

  local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
  local alternativeRatio = isPaxNear ? 0 : MIN_RATIO;
  local hardCap = OpexDynamicHardCap(this._lines.len(), false);
  local posPacked = 0;

  local plan = OpexPrepareRailRoute(this._catalog, this._budget, candidate, alternativeRatio, hardCap);
  if (plan.plansA == null) {
    local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
    this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
    if (isRepair && C56_TASK_TRACE) {
      OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " reason=" + repairReason + " issue=failed");
    }
    return false;
  }

  local pathfinder = null;
  local segmented = null;
  if (RAIL_SEGMENTED_SEARCH) {
    segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, plan.iterationBudget, null);
    if (segmented == null) {
      local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
      this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
      if (isRepair && C56_TASK_TRACE) {
        OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                       "src=" + candidate.src + " dst=" + candidate.dst
                       + " reason=" + repairReason + " issue=failed");
      }
      return false;
    }
  } else {
    pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, null);
    if (pathfinder == null) {
      local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
      this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
      if (isRepair && C56_TASK_TRACE) {
        OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                       "src=" + candidate.src + " dst=" + candidate.dst
                       + " reason=" + repairReason + " issue=failed");
      }
      return false;
    }
  }

  local curDate = AIDate.GetCurrentDate();
  local curTick = AIController.GetTick();
  this._railSearch = {
    kind = "primary",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = plan.iterationBudget,
    safetyDeadline = curTick + RAIL_SEARCH_SAFETY_TICKS,
    plan = plan,
    candidate = candidate,
    alternativeRatio = alternativeRatio,
    hardCap = hardCap,
    posPacked = posPacked,
    startDate = curDate,
    startTick = curTick,
    isStockSearch = true,
    isRepair = isRepair,
    repairReason = repairReason,
    coarseScore = coarseScore
  };

  this._activeWorker = {
    kind = "rail_stock",
    state = {
      ai = this
    }
  };

  if (C56_TASK_TRACE) {
    local threshold = this._railStockLastFundedScore;
    local thresholdDate = this._railStockLastFundedDate;
    local thresholdDateStr = (thresholdDate >= 0)
        ? (AIDate.GetYear(thresholdDate) + "-" + AIDate.GetMonth(thresholdDate) + "-" + AIDate.GetDayOfMonth(thresholdDate))
        : "none";
    OpexC56TaskLog("RAIL_STOCK_START", "rail_stock", this._taskCycle,
                   "src=" + candidate.src + " dst=" + candidate.dst
                   + " budget=" + plan.iterationBudget + " hard_cap=" + hardCap
                   + " threshold=" + threshold + " threshold_date=" + thresholdDateStr);
    if (isRepair) {
      OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " reason=" + repairReason + " issue=started");
    }
  }

  return true;
}

/* C80 étape 2 : gestion du dépassement de durée maximale (180 jours de jeu) d'une recherche rail. */
function OpexAI::_handleRailStockSearchTimeout()
{
  if (this._railSearch == null) return;
  local state = this._railSearch;
  local candidate = state.candidate;
  local iters = state.spent;
  local curDate = AIDate.GetCurrentDate();
  local days = ("startDate" in state) ? (curDate - state.startDate) : 180;
  local ticks = ("startTick" in state) ? (AIController.GetTick() - state.startTick) : 0;
  local isRepair = ("isRepair" in state) && state.isRepair;
  local repairReason = ("repairReason" in state && state.repairReason != null) ? state.repairReason : "";

  if (C56_TASK_TRACE) {
    OpexC56TaskLog("RAIL_STOCK_TIMEOUT", "rail_stock", this._taskCycle,
                   "src=" + candidate.src + " dst=" + candidate.dst
                   + " iters=" + iters + " days=" + days + " ticks=" + ticks);
    if (isRepair) {
      OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " reason=" + repairReason + " issue=timeout");
    }
  }

  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  // Retrait temporaire pendant 365 jours de jeu (1 an)
  this._railStockCooldown[pairKey] <- curDate + 365;

  if (("pathfinder" in state) && state.pathfinder != null) state.pathfinder = null;
  if (("segmented" in state) && state.segmented != null) state.segmented = null;
  this._railSearch = null;
  this._tryStartRailStockWorker();
}

/* C80 étape 2 : gestion de la complétion d'une recherche rail par le worker. */
function OpexAI::_handleRailStockSearchCompleted()
{
  if (this._railSearch == null) return;
  local state = this._railSearch;
  local candidate = state.candidate;
  local plan = ("railPlan" in candidate && candidate.railPlan != null) ? candidate.railPlan : state.plan;
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  local curDate = AIDate.GetCurrentDate();
  local iters = state.spent;
  local days = ("startDate" in state) ? (curDate - state.startDate) : 0;
  local ticks = ("startTick" in state) ? (AIController.GetTick() - state.startTick) : 0;
  local opcodes = (plan != null && ("opcodes" in plan)) ? plan.opcodes : 0;
  local isRepair = ("isRepair" in state) && state.isRepair;
  local repairReason = ("repairReason" in state && state.repairReason != null) ? state.repairReason : "";

  local readyProject = (plan != null && ("ok" in plan) && plan.ok)
      ? OpexProjectFromCandidate(candidate) : null;
  if (readyProject != null) {
    local readyFinanceCapital = OpexProjectFinanceCapital(readyProject);
    local readyProfit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(readyProject) : readyProject.profitAnnual;
    local readyFundScore = OpexProjectScore(readyProfit, readyFinanceCapital);
    readyProject.fundScore <- readyFundScore;

    this._railReadyStock[pairKey] <- {
      plan = plan,
      candidate = candidate,
      project = readyProject,
      pairKey = pairKey,
      readyDate = curDate,
      depositTick = AIController.GetTick()
    };
    if (C56_TASK_TRACE) {
      OpexC56TaskLog("RAIL_STOCK_DEPOSIT", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " iters=" + iters + " days=" + days + " ticks=" + ticks
                     + " opcodes=" + opcodes);

      local scoreBefore = ("coarseScore" in state && state.coarseScore != null) ? state.coarseScore : 0.0;
      local scoreAfter = readyFundScore;
      local scoreDiff = scoreAfter - scoreBefore;
      OpexC56TaskLog("RAIL_STOCK_SCORE", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " before=" + scoreBefore + " after=" + scoreAfter + " diff=" + scoreDiff);

      if (isRepair) {
        OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                       "src=" + candidate.src + " dst=" + candidate.dst
                       + " reason=" + repairReason + " issue=repaired");
      }
    }
  } else {
    // Échec de recherche : retrait temporaire 365 jours
    this._railStockCooldown[pairKey] <- curDate + 365;
    if (C56_TASK_TRACE && isRepair) {
      OpexC56TaskLog("RAIL_STOCK_REPAIR", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst
                     + " reason=" + repairReason + " issue=failed");
    }
    this._tryStartRailStockWorker();
  }

  if (readyProject == null && "railPlan" in candidate) candidate.railPlan = null;
  this._railSearch = null;
}

/* C80 étape 2 : contrôle de la durée de vie (TTL = 180 jours de jeu) des tracés prêts non financés. */
function OpexAI::_checkRailStockExpiry()
{
  if (!C80_RAIL_STOCK_GATE || !C80_RAIL_STOCK_WORKER || this._railReadyStock == null) return;
  if (this._railReadyStock.len() == 0) return;

  local curDate = AIDate.GetCurrentDate();
  local expiredKeys = [];
  foreach (pairKey, entry in this._railReadyStock) {
    if (entry == null || !("readyDate" in entry)) continue;
    local age = curDate - entry.readyDate;
    if (age > 180) {
      expiredKeys.append({ key = pairKey, age = age, src = entry.candidate.src, dst = entry.candidate.dst });
    }
  }

  foreach (exp in expiredKeys) {
    local expired = this._railReadyStock[exp.key];
    if (expired != null && ("candidate" in expired) && expired.candidate != null
        && ("railPlan" in expired.candidate)) expired.candidate.railPlan = null;
    delete this._railReadyStock[exp.key];
    this._railStockCooldown[exp.key] <- curDate + 180;
    if (C56_TASK_TRACE) {
      OpexC56TaskLog("RAIL_STOCK_EXPIRE", "rail_stock", this._taskCycle,
                     "src=" + exp.src + " dst=" + exp.dst + " age=" + exp.age);
    }
  }
  if (expiredKeys.len() > 0 && this._activeWorker == null) {
    this._tryStartRailStockWorker();
  }
}

/* C80 étape 2 : re-vérification obligatoire sur la carte vivante avant construction.
 * Vérifie capital, slots de véhicules, gares, voies et possibilité de dépôt sous AITestMode. */
function OpexAI::_revalidateRailStockPlan(candidate, plan)
{
  if (candidate == null || plan == null) return { ok = false, reason = "null_plan" };

  local need = candidate.capital + OpexCashReserve();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) return { ok = false, reason = "cash" };

  if (!OpexRailVehicleSlotAvailable()) return { ok = false, reason = "no_vehicle_slot" };

  if (candidate.kind != "pax") {
    if (!AIIndustry.IsValidIndustry(candidate.src) || !AIIndustry.IsValidIndustry(candidate.dst)) {
      return { ok = false, reason = "industry_closed" };
    }
  }

  local planA = plan.planA;
  local planB = plan.planB;
  local tiles = plan.tiles;
  if (planA == null || planB == null || tiles == null || tiles.len() < 3) {
    return { ok = false, reason = "invalid_plan_structure" };
  }

  {
    local testMode = AITestMode();
    local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
    local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
    local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA);
    local okB = AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length, stIdB);
    if (!okA || !okB) return { ok = false, reason = "station_blocked" };

    local trackRes = OpexTestRailTrack(tiles, (("structures" in plan) ? plan.structures : null));
    if (trackRes.failed > 0) {
      return {
        ok = false,
        reason = "track_blocked",
        failedSegments = trackRes.failed,
        firstSegment = trackRes.firstSegment,
        firstTile = trackRes.firstTile
      };
    }

    local depotFound = false;
    local offsets = [
      AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
      AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)
    ];
    for (local idx = 1; idx < tiles.len() - 1 && !depotFound; idx++) {
      local anchor = tiles[idx];
      foreach (offset in offsets) {
        local cand = anchor + offset;
        if (AIMap.IsValidTile(cand) && AIRail.BuildRailDepot(cand, anchor)) {
          depotFound = true;
          break;
        }
      }
    }
    if (!depotFound) return { ok = false, reason = "depot_blocked" };
  }

  return { ok = true, reason = "ok" };
}
