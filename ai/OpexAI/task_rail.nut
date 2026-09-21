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
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
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
      if (C60_TOWN_RATING_FILTER) {
        if ((towns.srcTown >= 0 && !OpexTownRatingAllowStation(towns.srcTown)) ||
            (towns.dstTown >= 0 && !OpexTownRatingAllowStation(towns.dstTown))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "town_rating_refusal", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }

      local close = this._tooClose(candidate);
      local join = null;
      local placeJoin = ("placeJoin" in candidate) ? candidate.placeJoin : null;
      if (close.hard >= 0) {
        if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_hard", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      if (placeJoin != null) {
        join = placeJoin;
        local joinEnd = join.candidateEnd;
        local refuse = null;
        if (!AIStation.IsValidStation(join.stationId)) refuse = "N";
        else {
          foreach (conflict in close.conflicts) {
            if (conflict.end != joinEnd || conflict.stationId != join.stationId) {
              refuse = "M";
              break;
            }
          }
        }
        if (refuse == null && JOIN_MAX_DISTANCE > 0 && candidate.distance >= JOIN_MAX_DISTANCE) {
          refuse = "D";
        }
        if (refuse != null) {
          join = null;
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "place_join_refuse", extra = "refuse=" + refuse });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else if (close.blocking >= 0) {
        if (STATION_JOIN) {
          join = OpexFindStationJoin(candidate, close.conflicts);
          if ("refuse" in join) {
            join = null;
          } else if (JOIN_MAX_DISTANCE > 0 && candidate.distance >= JOIN_MAX_DISTANCE) {
            join = null;
          }
        }
        if (join == null) {
          if (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }

      local need = candidate.capital + OpexCashReserve();
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
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
      /* P1.3 : le devis P1.1 porte le chemin complet. Le reutiliser seulement
       * apres une revalidation AITestMode sur la carte vivante ; un join decide
       * au chantier n'etait pas dans le devis et force donc une replannification. */
      if (RAIL_PREQUOTE_KEEP_PLAN && ("quotedPlan" in candidate) && candidate.quotedPlan != null) {
        if (join == null && OpexRailQuotedPlanStillBuildable(candidate.quotedPlan, join)) {
          candidate.railPlan <- candidate.quotedPlan;
          candidate.quotedPlan = null;
          if (DECISION_LOG) OpexDecide("P1_3_PLAN", "action=reuse src=" + candidate.src
                                       + " dst=" + candidate.dst);
        } else {
          candidate.quotedPlan = null;
          candidate.capitalIsActual = false;
          if (DECISION_LOG) OpexDecide("P1_3_PLAN", "action=invalidate src=" + candidate.src
                                       + " dst=" + candidate.dst + " reason="
                                       + (join == null ? "map" : "join"));
        }
      }
      local posPacked = i * TOP_K + this._projects.best.len();
      if (RAIL_SEARCH_RESUMABLE &&
          !(("railPlan" in candidate) && candidate.railPlan != null)) {
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
        local start = this._startRailSearch(candidate, join, placeJoin, alternativeRatio,
                                            hardCap, posPacked);
        if (start.pending) return { outcome = "pending", discards = passDiscards };
        /* Le candidat n'a pas encore cette cle dans le chemin qui termine sa
         * recherche dans le meme tour : creation de slot Squirrel avec `<-`. */
        candidate.railPlan <- start.plan;
      }
      local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio, join,
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
      local recorded = this._recordRailAttempt(candidate, result, join, placeJoin, posPacked, year);
      if (!recorded && (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL)) {
        local failReason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
        local failError = ("error" in result) ? result.error : 0;
        passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst,
                              reason = failReason, extra = "", error = failError });
      }
      return { outcome = recorded ? "built" : "rejected", discards = passDiscards };

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
        local backlogThreshold = C50B_RAIL_BACKLOG_RELAX ? 0
            : (line.kind == "freight" ? (2 * wagon.capacity) : (4 * wagon.capacity));
        if (waiting < backlogThreshold) continue;

        // Cas 1 : Ligne deja doublee avec depot2 -> ajout immediat du 2e train
        if (("doubleTrack" in line) && line.doubleTrack == 1 && ("depot2" in line) && line.depot2 != null) {
          local trainCost = line.loco.price + line.wagons * wagon.price;
          local need = trainCost + OpexCashReserve();
          local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (money < need && REBORROW) money = OpexTryReborrow(need, money);
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
          if (money < need && REBORROW) money = OpexTryReborrow(need, money);
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
    if (REBORROW) money = OpexTryReborrow(need, money);
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
function OpexAI::_startRailSearch(candidate, join, placeJoin, alternativeRatio, hardCap, posPacked)
{
  local plan = OpexPrepareRailRoute(this._catalog, this._budget, candidate, alternativeRatio,
                                    join, hardCap);
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
  this._railSearch = {
    kind = "primary",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = plan.iterationBudget,
    /* Borne horaire large : le budget d'iterations est la vraie limite (piege 1). */
    safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
    plan = plan,
    candidate = candidate,
    join = join,
    placeJoin = placeJoin,
    alternativeRatio = alternativeRatio,
    hardCap = hardCap,
    posPacked = posPacked,
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
  if (("segmented" in state) && state.segmented != null) {
    slice = OpexAdvanceSegmentedSearch(state.segmented, RAIL_SEARCH_SLICE, deadlineTick);
  } else {
    slice = OpexAdvanceRailPathfinder(state.pathfinder, state.spent, state.iterationBudget,
                                      deadlineTick, RAIL_SEARCH_SLICE);
  }
  /* spent est le CUMUL de toutes les tranches : c'est le denominateur du classement. */
  state.spent = slice.iterations;
  if (state.kind == "primary") {
    state.plan.opcodes += this._budget.end("build_search");
    state.plan.iterations = state.spent;
  } else {
    this._budget.end("build_search");
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
          bestScore = ((TENSION_SCORING || SHADOW_PRICING) && ("tensionScore" in p)) ? p.tensionScore : p.budgetScore;
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
    local plan = OpexCompleteRailRouteAfterSearch(this._catalog, state.candidate, state.plan,
                                                  slice, state.join);
    state.candidate.railPlan <- plan;
    state.pathfinder = null;
    state.phase = "build";
    return;
  }
  if (state.kind == "upgrade") {
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
  local state = this._railSearch;
  local candidate = state.candidate;
  local join = state.join;
  /* G3§1 : Un plan en echec (ABND/NOPA/DEAD) n'a besoin d'aucune tresorerie : OpexBuildLine
   * retourne immediatement sans construction. Le test de cash ne doit pas bloquer un plan
   * invalide en phase build indefiniment, sinon _railSearch ne se libere jamais et le
   * pipeline rail est neutralise (l'echec n'est pas non plus transmis a C22). */
  local planFailed = ("railPlan" in candidate) && candidate.railPlan != null
                     && !candidate.railPlan.ok;
  if (!planFailed) {
    local need = candidate.capital + OpexCashReserve();
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need && REBORROW) money = OpexTryReborrow(need, money);
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
      return { outcome = "cash", reason = "insufficient_cash", error = 0 };
    }
  }

  local result = OpexBuildLine(this._catalog, this._budget, candidate, state.alternativeRatio,
                               join, OpexCashReserve(), state.hardCap);
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
  local built = this._recordRailAttempt(candidate, result, join, state.placeJoin,
                                        state.posPacked, year);
  local reason = ("reason" in result && result.reason != "") ? result.reason : "build_failed";
  local error = ("error" in result) ? result.error : 0;
  return { outcome = built ? "built" : "failed", reason = reason, error = error };
}
/* Panneaux + enregistrement d'une tentative rail, reussie ou non. Facteur commun au chemin
 * bloquant et au chemin reprenable, pour que le denominateur (result.iterations) et les
 * panneaux OR/OB restent identiques. */
function OpexAI::_recordRailAttempt(candidate, result, join, placeJoin, posPacked, year)
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
                            + result.siteCmd + "|" + result.siteKind + "|"
                            + result.joinEnd);
  }
  if (result.error != 0) OpexSign(anchor, "OV|" + this._nextLineId + "|" + result.error);
  if (C63_INVEST_PROBE) {
    local railPlanned = ("capital" in result) ? result.capital : candidate.capital;
    local railActual = ("actualCost" in result) ? result.actualCost : 0;
    OpexC63RecordSpend("rail", railPlanned, railActual, result.ok);
  }

  if (DECISION_LOG) {
    if (result.ok) {
      local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
      OpexDecide("RAIL_BUILD", "line=" + this._nextLineId + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " cost=" + result.actualCost + " trains=" + result.trains + " wagons=" + result.wagons);
    } else {
      OpexDecide("RAIL_BUILD_FAIL", "line=" + this._nextLineId + " reason=" + result.reason + " error=" + result.error + " iters=" + result.iterations + " budget=" + iterationBudget);
    }
  }

  if (result.ok) {
    local idx = this._nextLineId;
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
    if (STATION_JOIN || JOIN_PLACE) {
      local joinHow = "";
      if (placeJoin != null) joinHow = "|P";
      else if (join != null) joinHow = "|T";
      OpexSign(anchor, "PJ|" + idx + "|" + (join == null ? "N" : join.candidateEnd)
                               + "|" + (candidate.originServed ? 1 : 0) + joinHow);
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
