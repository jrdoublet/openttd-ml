/* Module AIR extrait de builder_air.nut (R11) : choix moteur, politiques historiques et sondes M3. */
/* Evalue et planifie la meilleure liaison aerienne en testant les combinaisons
 * grand aeroport (+gros/petit avion) et petit aeroport (+petit avion strictement). */
function OpexAirPlanBetter(plan, bestPlan)
{
  if (bestPlan == null) return true;
  local planEconomics = (("decisionEconomics" in plan) && plan.decisionEconomics != null)
      ? plan.decisionEconomics : plan.economics;
  local bestEconomics = (("decisionEconomics" in bestPlan) && bestPlan.decisionEconomics != null)
      ? bestPlan.decisionEconomics : bestPlan.economics;
  /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
   * il deploie le capital plus vite et permet de batir plus de lignes. */
  if (planEconomics.roi > (bestEconomics.roi * 1.25).tointeger()) return true;
  if (bestEconomics.roi > (planEconomics.roi * 1.25).tointeger()) return false;
  return planEconomics.profitAnnual > bestEconomics.profitAnnual;
}

/* C97 : capital et profit d'un point virtuel passes par EXACTEMENT le meme
 * chemin que le projet AIR reel. Cela reutilise donc la marge AIR,
 * l'immobilisation et la calibration C70/C82 du portefeuille, sans definition
 * parallele du cout. */
function OpexC97AirPoint(catalog, plan, plane, economics, kDec)
{
  if (catalog == null || plan == null || plane == null || economics == null
      || economics.profitAnnual <= 0) return null;
  local virtualPlan = clone plan;
  virtualPlan.plane = plane;
  virtualPlan.economics = economics;
  virtualPlan.planes = economics.planes;
  virtualPlan.capital = economics.capital;
  local project = OpexProjectFromAir(catalog, virtualPlan, 0);
  if (project == null) return null;
  local financeCapital = OpexProjectFinanceCapital(project);
  if (financeCapital <= 0) return null;
  local calibratedProfit = C70_PROFIT_CALIBRATED
      ? OpexCalibratedProfit(project) : project.profitAnnual;
  local denom = financeCapital > kDec ? financeCapital : kDec;
  return {
    plane = plane,
    economics = economics,
    financeCapital = financeCapital,
    calibratedProfit = calibratedProfit,
    score = OpexProjectScore(calibratedProfit, denom),
  };
}

/* Le score C69 est l'objectif primaire. Les departages ne changent jamais le
 * maximum du score : profit calibre, capital moindre, moteur puis profondeur
 * donnent seulement un ordre deterministe. */
function OpexC97AirPointBetter(candidate, incumbent)
{
  if (candidate == null) return false;
  if (incumbent == null) return true;
  if (candidate.score > incumbent.score) return true;
  if (candidate.score < incumbent.score) return false;
  if (candidate.calibratedProfit > incumbent.calibratedProfit) return true;
  if (candidate.calibratedProfit < incumbent.calibratedProfit) return false;
  if (candidate.financeCapital < incumbent.financeCapital) return true;
  if (candidate.financeCapital > incumbent.financeCapital) return false;
  if (candidate.plane.id < incumbent.plane.id) return true;
  if (candidate.plane.id > incumbent.plane.id) return false;
  return candidate.economics.planes < incumbent.economics.planes;
}

function OpexC97AirMaxPlanes(airport, newAirportCount)
{
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  return (newAirportCount == 2) ? 3 : (isSmall ? 4 : 6);
}

/* C97 : contrairement a V92.2, aucun moteur n'est d'abord reduit a son n de
 * profit maximal. Chaque point (moteur,n) est score directement. fixedPlanes=n
 * est volontaire : serviceScan ferait precisement la reduction V92 a eviter. */
function OpexC97AirFindBest(catalog, plan, kDec)
{
  if (catalog == null || plan == null || !("airport" in plan) || plan.airport == null
      || !("distance" in plan) || !("monthlyPax" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return null;
  local newAirportCount = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local maxPlanes = OpexC97AirMaxPlanes(plan.airport, newAirportCount);
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local best = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    for (local n = 1; n <= maxPlanes; n++) {
      local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
          infrastructureMaintenance, 0, newAirportCount, 0, n, false, false);
      local point = OpexC97AirPoint(catalog, plan, plane, economics, kDec);
      if (OpexC97AirPointBetter(point, best)) best = point;
    }
  }
  return best;
}

function OpexC97ProbeAirEngine(catalog, plan)
{
  if (!C97_AIR_C69_ENGINE_PROBE || catalog == null || plan == null
      || !("plane" in plan) || plan.plane == null
      || !("economics" in plan) || plan.economics == null) return;
  local kDec = OpexC69CachedKDec();
  local baseline = OpexC97AirPoint(catalog, plan, plan.plane, plan.economics, kDec);
  local best = OpexC97AirFindBest(catalog, plan, kDec);
  if (baseline == null || best == null) return;
  local src = (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)
      && plan.siteA.town != null && ("id" in plan.siteA.town)) ? plan.siteA.town.id : -1;
  local dst = (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)
      && plan.siteB.town != null && ("id" in plan.siteB.town)) ? plan.siteB.town.id : -1;
  local route = ("arm" in plan) ? plan.arm : "unknown";
  local disagree = baseline.plane.id != best.plane.id ? 1 : 0;
  AILog.Info("C97_ENGINE route=" + route + " src=" + src + " dst=" + dst
      + " airport_type=" + plan.airport.type
      + " default_engine=" + baseline.plane.id
      + " default_name=" + OpexPlaneName(baseline.plane.id)
      + " default_n=" + baseline.economics.planes
      + " c97_engine=" + best.plane.id + " c97_name=" + OpexPlaneName(best.plane.id)
      + " c97_n=" + best.economics.planes
      + " K_dec=" + kDec + " disagree=" + disagree
      + " default_P=" + baseline.economics.profitAnnual
      + " default_P_cal=" + baseline.calibratedProfit
      + " default_C=" + baseline.financeCapital + " default_score=" + baseline.score
      + " c97_P=" + best.economics.profitAnnual + " c97_P_cal=" + best.calibratedProfit
      + " c97_C=" + best.financeCapital + " c97_score=" + best.score
      + " default_price=" + baseline.plane.price + " c97_price=" + best.plane.price
      + " default_capacity=" + baseline.plane.capacity + " c97_capacity=" + best.plane.capacity
      + " default_speed=" + baseline.plane.speed + " c97_speed=" + best.plane.speed
      + " default_big=" + (("isBig" in baseline.plane) && baseline.plane.isBig ? 1 : 0)
      + " c97_big=" + (("isBig" in best.plane) && best.plane.isBig ? 1 : 0));
}

function OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan)
{
  if (projects != null) projects.append(plan);
  if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
  return bestPlan;
}

function OpexAirPlaneInRange(plane, distance)
{
  return plane != null && !(plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance);
}

/* C68 : transforme le contre-factuel passif M3 en intervention minimale. Le caller a deja choisi
 * le type d'aeroport, les sites, la paire et la demande avec le chemin historique. Sous le switch,
 * on ne change donc que l'appareil et l'economie de cette route, avec exactement le meme modele
 * OpexAirEconomics que M3. Sous 0, le resultat est strictement le couple historique. */
/* C80 tranche 5 : `memoKey` identifie la route (villes ou gares, type d'aeroport, avion du combo).
 * Etat 1 (generation complete) : choix complet, memorise. Etat 2 (mise a jour apres chantier) :
 * seule l'economie de l'avion memorise est recalculee ; sans memo valide, choix complet memorise.
 * Un appel plafonne en capital (construction, `maxCapital` > 0) ne lit ni n'ecrit le memo. */
function OpexAirChooseRoutePlane(catalog, airport, selectedPlane, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount,
                                 opcodePadding, memoKey = null)
{
  if (!C80_AIR_CHOICE_MEMO || memoKey == null
      || maxCapital != 0 || AIR_CHOICE_MEMO_STATE == 0) {
    return OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (AIR_CHOICE_MEMO_STATE == 2 && (memoKey in AIR_CHOICE_MEMO)) {
    local planeId = AIR_CHOICE_MEMO[memoKey];
    local memoPlane = null;
    if (planeId == selectedPlane.id) {
      memoPlane = selectedPlane;
    } else if (airport.type in catalog.airPlaneChoicesByAirport) {
      foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
        if (plane.id == planeId) { memoPlane = plane; break; }
      }
    }
    if (memoPlane != null && (memoPlane.maxOrderDistance <= 0 || distance <= memoPlane.maxOrderDistance)) {
      local economics = OpexAirEconomics(catalog, airport, memoPlane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, false);
      if (economics != null) {
        return { plane = memoPlane, economics = economics };
      }
    }
  }
  local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (choice.plane != null) AIR_CHOICE_MEMO.rawset(memoKey, choice.plane.id);
  return choice;
}

/* C104 : argmax profit/ROI sous un timing force, sans jamais retourner ce choix
 * au chemin decisionnel. mode=0 legacy, 1 replay du premier C100, 2 C100.1. */
function OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
                              infrastructureMaintenance, maxCapital,
                              newAirportCount, opcodePadding, mode)
{
  local bestPlane = null;
  local bestEconomics = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = null;
    if (mode == 1) {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, true);
    } else if (mode == 2) {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, true, false);
    } else {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, false);
    }
    if (economics == null) continue;
    if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
        (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
      bestPlane = plane;
      bestEconomics = economics;
    }
  }
  if (bestPlane == null || bestEconomics == null) return null;
  return { plane = bestPlane, economics = bestEconomics };
}

function OpexC104FormatAirChoice(prefix, choice)
{
  if (choice == null || !("economics" in choice) || choice.economics == null) return prefix + "_id=-1";
  local p = choice.plane;
  local e = choice.economics;
  return prefix + "_id=" + p.id
      + " " + prefix + "_price=" + p.price
      + " " + prefix + "_cap=" + p.capacity
      + " " + prefix + "_speed=" + p.speed
      + " " + prefix + "_n=" + e.planes
      + " " + prefix + "_P=" + e.profitAnnual
      + " " + prefix + "_R=" + e.revenueAnnual
      + " " + prefix + "_run=" + e.runningAnnual
      + " " + prefix + "_amort=" + e.amortAnnual
      + " " + prefix + "_C=" + e.capital
      + " " + prefix + "_imm=" + e.immobilise
      + " " + prefix + "_roi=" + e.roi
      + " " + prefix + "_days=" + e.oneWayDays
      + " " + prefix + "_trips=" + e.tripsPerMonth
      + " " + prefix + "_rating=" + e.stationRating
      + " " + prefix + "_mcap=" + e.monthlyCapacity
      + " " + prefix + "_carried=" + e.carried;
}

/* C116.2 passif : serialisation du snapshot du portefeuille precedent. Aucun
 * calcul de projet n'est declenche ici ; seules des valeurs deja memorisees sont
 * lues. p1/p2/p3 sont les trois premiers projets AIR finançables dans l'ordre
 * reel du portefeuille au dernier OpexProjectSelectAffordable. */
function OpexC116SnapshotBest(frontier, deltaCapital)
{
  if (frontier == null || deltaCapital <= 0) return null;
  local best = null;
  foreach (point in frontier) {
    if (point.gap > deltaCapital) continue;
    if (best == null || point.hurdle > best.hurdle
        || (point.hurdle == best.hurdle && point.profit > best.profit)) best = point;
  }
  return best;
}

function OpexC116FormatSnapshotPoint(prefix, point, frontierN)
{
  local out = " " + prefix + "_n=" + frontierN;
  if (point == null) return out + " " + prefix + "_gap=-1";
  return out + " " + prefix + "_gap=" + point.gap
      + " " + prefix + "_mode=" + point.mode
      + " " + prefix + "_P=" + point.profit
      + " " + prefix + "_C=" + point.finance
      + " " + prefix + "_hurdle=" + point.hurdle
      + " " + prefix + "_roi=" + point.roi
      + " " + prefix + "_dist=" + point.distance;
}

function OpexC116BestUnlockedAirProject(deltaCapital)
{
  local snapshot = C116_AIR_PROJECT_SNAPSHOT;
  if (snapshot == null || !("unlockable" in snapshot) || deltaCapital <= 0) return null;
  local unlocked = null;
  foreach (point in snapshot.unlockable) {
    if (point.gap > deltaCapital) continue;
    if (unlocked == null || point.hurdle > unlocked.hurdle
        || (point.hurdle == unlocked.hurdle && point.profit > unlocked.profit)) unlocked = point;
  }
  return unlocked;
}

function OpexC116FormatProjectSnapshot(deltaCapital)
{
  local snapshot = C116_AIR_PROJECT_SNAPSHOT;
  if (snapshot == null) return " c116p_age=-1 c116p_budget=0 c116p_top_mode=none c116p_n=0 c116u_n=0 c116u_gap=-1 c116g_n=0 c116g_gap=-1";
  local age = AIDate.GetCurrentDate() - snapshot.date;
  local out = " c116p_age=" + age + " c116p_budget=" + snapshot.budget
      + " c116p_top_mode=" + snapshot.topMode + " c116p_n=" + snapshot.air.len();
  if (("top" in snapshot) && snapshot.top != null) {
    out += " c116t_mode=" + snapshot.top.mode
        + " c116t_P=" + snapshot.top.profit
        + " c116t_C=" + snapshot.top.finance
        + " c116t_hurdle=" + snapshot.top.hurdle
        + " c116t_score=" + snapshot.top.score;
  } else {
    out += " c116t_mode=none c116t_P=0 c116t_C=0 c116t_hurdle=0 c116t_score=0";
  }
  for (local i = 0; i < snapshot.air.len() && i < 3; i++) {
    local p = snapshot.air[i];
    local prefix = "c116p" + (i + 1);
    out += " " + prefix + "_rank=" + p.rank
        + " " + prefix + "_P=" + p.profit
        + " " + prefix + "_C=" + p.finance
        + " " + prefix + "_score=" + p.score
        + " " + prefix + "_roi=" + p.roi
        + " " + prefix + "_dist=" + p.distance;
  }
  local airN = ("unlockable" in snapshot) ? snapshot.unlockable.len() : 0;
  local airPoint = ("unlockable" in snapshot) ? OpexC116SnapshotBest(snapshot.unlockable, deltaCapital) : null;
  out += OpexC116FormatSnapshotPoint("c116u", airPoint, airN);
  local globalN = ("unlockableAny" in snapshot) ? snapshot.unlockableAny.len() : 0;
  local globalPoint = ("unlockableAny" in snapshot) ? OpexC116SnapshotBest(snapshot.unlockableAny, deltaCapital) : null;
  out += OpexC116FormatSnapshotPoint("c116g", globalPoint, globalN);
  return out;
}


function OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
                                     infrastructureMaintenance, maxCapital, newAirportCount,
                                     opcodePadding)
{
  local selectedEconomics = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, false, false);
  if (!AIR_ROUTE_PLANE_SELECTION || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }

  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
  }

  local r_plane = null;
  local r_econ = null;
  local c_plane = null;
  local c_econ = null;
  local c_score = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      r_plane = selectedPlane;
      r_econ = selectedEconomics;
      c_plane = selectedPlane;
      c_econ = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      c_score = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  local routePlaneChoices = catalog.airPlaneChoicesByAirport[airport.type];
  foreach (plane in routePlaneChoices) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;
    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || economics.roi > bestEconomics.roi ||
          (economics.roi == bestEconomics.roi && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
      }
    } else {
      if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
          (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    }
    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (r_econ == null || economics.roi > r_econ.roi ||
          (economics.roi == r_econ.roi && economics.profitAnnual > r_econ.profitAnnual)) {
        r_plane = plane;
        r_econ = economics;
      }
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (c_econ == null || curScore > c_score ||
          (curScore == c_score && economics.profitAnnual > c_econ.profitAnnual)) {
        c_plane = plane;
        c_econ = economics;
        c_score = curScore;
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C69_PLANE_CHOICE_CALLS++;
    if (r_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_ROI++;
    if (c_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_C69++;

    if (r_plane.id != bestPlane.id || c_plane.id != bestPlane.id) {
      local avail = OpexAvailableCapital();
      local p_name = OpexPlaneName(bestPlane.id);
      local r_name = OpexPlaneName(r_plane.id);
      local c_name = OpexPlaneName(c_plane.id);
      OpexC69Log("phase=plane_choice dist=" + distance + " kdec=" + kDec + " avail=" + avail
          + " nplanes=" + evalCount
          + " p_id=" + bestPlane.id + " p_name=" + p_name + " p_P=" + bestEconomics.profitAnnual
          + " p_C=" + bestEconomics.capital + " p_roi=" + bestEconomics.roi
          + " r_id=" + r_plane.id + " r_name=" + r_name + " r_P=" + r_econ.profitAnnual
          + " r_C=" + r_econ.capital + " r_roi=" + r_econ.roi
          + " c_id=" + c_plane.id + " c_name=" + c_name + " c_P=" + c_econ.profitAnnual
          + " c_C=" + c_econ.capital + " c_roi=" + c_econ.roi);
    }
  }

  return { plane = bestPlane, economics = bestEconomics };
}

/* M3/G12 : comparaison PASSIVE du plan air deja elu contre les autres appareils compatibles avec
 * le meme type d'aeroport, sur la meme distance/demande et avec le meme nombre initial d'avions. */
function OpexM3ProbeAirEquipment(catalog, plan, phase)
{
  if (!EQUIPMENT_ROI_PROBE || plan == null || !("airport" in plan) || !("plane" in plan) ||
      !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[plan.airport.type];
  if (alternatives.len() == 0) return;
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local fixedPlanes = ("planes" in plan) && plan.planes > 0 ? plan.planes : 1;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && plan.distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
        infrastructureMaintenance, 0, newAirports, 0, fixedPlanes);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + plan.airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + plan.plane.id
      + " selected_refit=" + (plan.plane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_profit=" + plan.economics.profitAnnual + " selected_roi=" + plan.economics.roi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1));
}

function OpexM3ProbeAirPreAdmission(catalog, airport, selectedPlane, distance, monthlyPax,
                                    infrastructureMaintenance, maxCapital, newAirportCount,
                                    opcodePadding, selectedEconomics, phase)
{
  if (!EQUIPMENT_ROI_PROBE || airport == null || selectedPlane == null ||
      !(airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[airport.type];
  if (alternatives.len() == 0) return;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  local selectedProfit = selectedEconomics != null ? selectedEconomics.profitAnnual : -999999999;
  local selectedRoi = selectedEconomics != null ? selectedEconomics.roi : -1;
  local selectedPositive = selectedEconomics != null && selectedEconomics.profitAnnual > 0;
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + selectedPlane.id
      + " selected_refit=" + (selectedPlane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_ok=" + (selectedEconomics != null ? 1 : 0)
      + " selected_profit=" + selectedProfit + " selected_roi=" + selectedRoi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1)
      + " admission_flip=" + ((!selectedPositive && bestProfit != null && bestProfit.profitAnnual > 0) ? 1 : 0)
      + " native_admission_flip="
      + ((!selectedPositive && bestNativeProfit != null && bestNativeProfit.profitAnnual > 0) ? 1 : 0));
}
