/* Module AIR extrait de builder_air.nut (R11) : choix moteur, politiques historiques et sondes M3. */
/* Evalue et planifie la meilleure liaison aerienne en testant les combinaisons
 * grand aeroport (+gros/petit avion) et petit aeroport (+petit avion strictement). */
function OpexAirPlanBetter(plan, bestPlan)
{
  if (bestPlan == null) return true;
  if (!C111_AIR_C100_DECISION_SHADOW && !C121_AIR_ECONOMICS) {
    if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
    if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
    return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
  }
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

/* V92 : pose le service retenu et, s'il differe, la variante a un appareil bon marche.
 * Les deux portent la meme cle de paire pour qu'un seul soit construit. */
function OpexAirV92PairBlocked(lines, plan)
{
  if (!V92_AIR_SERVICE_CHOICE || plan == null || !("v92PairKey" in plan)) return false;
  if (plan.v92PairKey in V92_CLOSED_PAIRS) return true;
  if (lines == null || !("siteA" in plan) || !("siteB" in plan)) return false;
  local tileA = plan.siteA.town.tile;
  local tileB = plan.siteB.town.tile;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local originA = ("originA" in line) ? line.originA : -1;
    local originB = ("originB" in line) ? line.originB : -1;
    if ((originA == tileA && originB == tileB) || (originA == tileB && originB == tileA)) return true;
  }
  return false;
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
  if (V92_AIR_SERVICE_CHOICE && routeChoice != null && ("alternate" in routeChoice)
      && routeChoice.alternate != null && routeChoice.alternate.economics != null
      && routeChoice.alternate.economics.profitAnnual > 0) {
    local alt = routeChoice.alternate;
    local townA = plan.siteA.town.id;
    local townB = plan.siteB.town.id;
    if (townA > townB) {
      local swap = townA;
      townA = townB;
      townB = swap;
    }
    local key = townA + "|" + townB + "|" + plan.airport.type;
    plan.v92PairKey <- key;
    plan.v92Role <- "service";
    local cheap = {};
    foreach (k, v in plan) cheap[k] <- v;
    cheap.plane = alt.plane;
    cheap.economics = alt.economics;
    cheap.planes = alt.economics.planes;
    cheap.capital = alt.economics.capital;
    cheap.v92Role = "cheap";
    if ("targetPlanes" in cheap) cheap.targetPlanes = alt.economics.planes;
    if (projects != null) projects.append(cheap);
    if (OpexAirPlanBetter(cheap, bestPlan)) bestPlan = cheap;
  }
  if (projects != null) projects.append(plan);
  if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
  return bestPlan;
}

/* C82 : arbitrage d'appareil par route evalue sur les profits et ROI calibres par moteur.
 * L'objet economics renvoye reste brut (non modifie). */
function OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
{
  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestK = (selectedPlane != null) ? OpexC82EngineFactor(selectedPlane.id) : 1.0;
  local bestCalProfit = (selectedEconomics != null) ? (selectedEconomics.profitAnnual * bestK) : 0.0;
  local bestCalRoi = (selectedEconomics != null) ? (selectedEconomics.roi * bestK) : 0.0;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (bestCalProfit.tofloat() * 1000.0) / denom : 0.0;
  }

  local rawPlane = null;
  local rawEconomics = null;
  local rawScore = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      rawPlane = selectedPlane;
      rawEconomics = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      rawScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, false);
    if (economics == null) continue;

    local k = OpexC82EngineFactor(plane.id);
    local calProfit = economics.profitAnnual * k;
    local calRoi = economics.roi * k;

    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || calRoi > bestCalRoi ||
          (calRoi == bestCalRoi && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (calProfit.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else {
      if (bestEconomics == null || calProfit > bestCalProfit ||
          (calProfit == bestCalProfit && calRoi > bestCalRoi)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    }

    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (C72_PLANE_CHOICE == 1) {
        if (rawEconomics == null || economics.roi > rawEconomics.roi ||
            (economics.roi == rawEconomics.roi && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      } else if (C72_PLANE_CHOICE == 2) {
        local curDenom = economics.capital > kDec ? economics.capital : kDec;
        local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
        if (rawEconomics == null || curScore > rawScore ||
            (curScore == rawScore && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
          rawScore = curScore;
        }
      } else {
        if (rawEconomics == null || economics.profitAnnual > rawEconomics.profitAnnual ||
            (economics.profitAnnual == rawEconomics.profitAnnual && economics.roi > rawEconomics.roi)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C82_CHOICE_CALLS++;
    local idBrut = (rawPlane != null) ? rawPlane.id : -1;
    local idCalibre = (bestPlane != null) ? bestPlane.id : -1;
    if (idCalibre != idBrut) {
      C82_CHOICE_DIFFER++;
      local kBrut = (idBrut >= 0) ? OpexC82EngineFactor(idBrut) : 1.0;
      local kCalibre = (idCalibre >= 0) ? OpexC82EngineFactor(idCalibre) : 1.0;
      OpexC69Log("phase=c82_choice raw=" + idBrut + " cal=" + idCalibre
          + " k_raw=" + kBrut + " k_cal=" + kCalibre + " c72=" + C72_PLANE_CHOICE);
    }
  }

  return { plane = bestPlane, economics = bestEconomics };
}

/* C68 : transforme le contre-factuel passif M3 en intervention minimale. Le caller a deja choisi
 * le type d'aeroport, les sites, la paire et la demande avec le chemin historique. Sous le switch,
 * on ne change donc que l'appareil et l'economie de cette route, avec exactement le meme modele
 * OpexAirEconomics que M3. Sous 0, le resultat est strictement le couple historique. */
/* C80 tranche 5 : `memoKey` identifie la route (villes ou gares, type d'aeroport, avion du combo).
 * Etat 1 (generation complete) : choix complet, memorise. Etat 2 (mise a jour apres chantier) :
 * seule l'economie de l'avion memorise est recalculee ; sans memo valide, choix complet memorise.
 * Un appel plafonne en capital (construction, `maxCapital` > 0) ne lit ni n'ecrit le memo. */
function OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
                                  newAirportCount, opcodePadding, choice)
{
  if (choice == null || choice.plane == null || choice.economics == null) return choice;
  local targetEconomics = OpexAirTargetEconomics(catalog, airport, choice.plane, distance, monthlyPax,
      infrastructureMaintenance, newAirportCount, opcodePadding);
  if (targetEconomics != null) {
    choice.targetEconomics <- targetEconomics;
    choice.targetPlanes <- targetEconomics.planes;
  }
  return choice;
}

/* Lit la soute des avions deja en vol de cette compagnie, une fois par mois.
 * AIVehicleList ne voit pas les avions des autres compagnies. */
function OpexAirLearnMailCaps(catalog)
{
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0
      || !("paxCargo" in catalog) || catalog.paxCargo < 0) return;
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now);
  if (AIR_MAIL_LEARN_MONTH == month) return;
  AIR_MAIL_LEARN_MONTH = month;
  local list = AIVehicleList();
  list.Valuate(AIVehicle.GetVehicleType);
  list.KeepValue(AIVehicle.VT_AIR);
  for (local v = list.Begin(); !list.IsEnd(); v = list.Next()) {
    local engine = AIVehicle.GetEngineType(v);
    if (engine < 0 || (engine in AIR_MAIL_CAP)) continue;
    local pax = AIVehicle.GetCapacity(v, catalog.paxCargo);
    local mail = AIVehicle.GetCapacity(v, catalog.mailCargo);
    if (pax > 0 && mail >= 0) AIR_MAIL_CAP.rawset(engine, mail);
  }
}

function OpexAirApplyKnownMail(plane)
{
  if (plane == null || !("id" in plane)) return;
  if (plane.id in AIR_MAIL_CAP) plane.mailCapacity = AIR_MAIL_CAP[plane.id];
}

function OpexAirPlaneInRange(plane, distance)
{
  return plane != null && !(plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance);
}

function OpexAirServiceBetter(candidate, incumbent)
{
  if (candidate == null || candidate.profitAnnual <= 0) return false;
  if (incumbent == null) return true;
  if (candidate.profitAnnual > incumbent.profitAnnual) return true;
  if (candidate.profitAnnual == incumbent.profitAnnual && candidate.roi > incumbent.roi) return true;
  return false;
}

/* V92 : pour chaque moteur compatible, le nombre d'appareils au meilleur profit,
 * puis la meilleure variante a un seul appareil dont le prix ne depasse pas
 * le gros jet le moins cher (ou le moins cher tout court sur un petit aeroport). */
function OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
                                   infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
{
  OpexAirLearnMailCaps(catalog);
  local bestPlane = null;
  local bestEcon = null;
  local cheapPlane = null;
  local cheapEcon = null;
  if (airport == null || catalog == null || catalog.airPlaneChoicesByAirport == null
      || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    local econ = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        1, false, false, false, false);
    return { plane = selectedPlane, economics = econ };
  }
  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  local cheapLimit = -1;
  local anyPrice = -1;
  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    OpexAirApplyKnownMail(plane);
    if (anyPrice < 0 || plane.price < anyPrice) anyPrice = plane.price;
    if (("isBig" in plane) && plane.isBig && (cheapLimit < 0 || plane.price < cheapLimit)) {
      cheapLimit = plane.price;
    }
  }
  if (cheapLimit < 0) cheapLimit = anyPrice;
  if (selectedPlane != null) OpexAirApplyKnownMail(selectedPlane);

  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    local scanned = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, true, false, false);
    if (OpexAirServiceBetter(scanned, bestEcon)) {
      bestPlane = plane;
      bestEcon = scanned;
    }
    if (cheapLimit >= 0 && plane.price <= cheapLimit) {
      local one = (scanned != null && scanned.planes == 1) ? scanned
          : OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
              infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
              1, false, false, false, false);
      if (OpexAirServiceBetter(one, cheapEcon)) {
        cheapPlane = plane;
        cheapEcon = one;
      }
    }
  }
  if (bestPlane == null && selectedPlane != null) {
    bestEcon = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        1, false, false, false, false);
    bestPlane = selectedPlane;
  }
  local choice = { plane = bestPlane, economics = bestEcon };
  if (cheapPlane != null && bestPlane != null && cheapEcon != null
      && (cheapPlane.id != bestPlane.id || cheapEcon.planes != bestEcon.planes)) {
    choice.alternate <- { plane = cheapPlane, economics = cheapEcon };
  }
  return choice;
}

function OpexAirChooseRoutePlane(catalog, airport, selectedPlane, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount,
                                 opcodePadding, memoKey = null)
{
  if (V92_AIR_SERVICE_CHOICE) {
    return OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  /* Le memo historique ne stocke qu'un EngineID : il perdrait decisionEconomics
   * (C111) et l'economie replay conditionnelle C115. */
  if (C111_AIR_C100_DECISION_SHADOW
      || C115_AIR_C100_CAPITAL_REPLAY
      || !C80_AIR_CHOICE_MEMO || memoKey == null
      || maxCapital != 0 || AIR_CHOICE_MEMO_STATE == 0) {
    local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (C84_AIR_TARGET_FLEET) {
      return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
          newAirportCount, opcodePadding, choice);
    }
    return choice;
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
        local choice = { plane = memoPlane, economics = economics };
        if (C84_AIR_TARGET_FLEET) {
          return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
              newAirportCount, opcodePadding, choice);
        }
        return choice;
      }
    }
  }
  local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (choice.plane != null) AIR_CHOICE_MEMO.rawset(memoKey, choice.plane.id);
  if (C84_AIR_TARGET_FLEET) {
    return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
        newAirportCount, opcodePadding, choice);
  }
  return choice;
}

/* C101 : corrige uniquement le CHOIX DU MOTEUR. Chaque appareil doit d'abord
 * rester viable sous l'economie historique ; le classement entre appareils se
 * fait ensuite avec le timing physique C100.1. L'economie retournee au plan est
 * toujours l'economie historique du moteur gagnant : admission, capital, score
 * projet et expansion restent donc sur le modele du defaut. */
function OpexC101ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local viable = [];
  local rawPlane = selectedEconomics != null ? selectedPlane : null;
  local rawLegacy = selectedEconomics;

  if (selectedPlane != null && selectedEconomics != null) {
    viable.append({ plane = selectedPlane, legacy = selectedEconomics });
  }

  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  foreach (plane in choices) {
    if (selectedPlane != null && plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;

    /* La viabilite/admission reste volontairement celle du defaut. */
    local legacy = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (legacy == null) continue;
    viable.append({ plane = plane, legacy = legacy });
    if (rawLegacy == null || legacy.profitAnnual > rawLegacy.profitAnnual ||
        (legacy.profitAnnual == rawLegacy.profitAnnual && legacy.roi > rawLegacy.roi)) {
      rawPlane = plane;
      rawLegacy = legacy;
    }
  }

  if (rawPlane == null || rawLegacy == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }

  local bestPlane = rawPlane;
  local bestLegacy = rawLegacy;
  local bestPhysical = null;
  foreach (item in viable) {
    /* Le gagnant C68 maximise deja le profit legacy. Un candidat qui exige
     * davantage de capital ne peut donc pas justifier sa substitution sans
     * ralentir l'expansion : C101 reste strictement capital-neutre. */
    if (item.legacy.capital > rawLegacy.capital) continue;
    local physical = OpexAirEconomics(catalog, airport, item.plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true);
    if (physical == null) continue;
    if (bestPhysical == null || physical.profitAnnual > bestPhysical.profitAnnual ||
        (physical.profitAnnual == bestPhysical.profitAnnual && physical.roi > bestPhysical.roi)) {
      bestPlane = item.plane;
      bestLegacy = item.legacy;
      bestPhysical = physical;
    }
  }

  if (bestPhysical == null) return { plane = rawPlane, economics = rawLegacy };
  if (C69_BOTTLENECK_PROBE && rawPlane != null && rawLegacy != null
      && rawPlane.id != bestPlane.id) {
    OpexC69Log("phase=c101_choice policy=capital_neutral dist=" + distance
        + " raw_id=" + rawPlane.id + " raw_name=" + OpexPlaneName(rawPlane.id)
        + " raw_price=" + rawPlane.price + " raw_P=" + rawLegacy.profitAnnual
        + " raw_C=" + rawLegacy.capital + " raw_roi=" + rawLegacy.roi
        + " pick_id=" + bestPlane.id + " pick_name=" + OpexPlaneName(bestPlane.id)
        + " pick_price=" + bestPlane.price + " pick_legacy_P=" + bestLegacy.profitAnnual
        + " pick_legacy_C=" + bestLegacy.capital + " pick_legacy_roi=" + bestLegacy.roi
        + " pick_physical_P=" + bestPhysical.profitAnnual + " pick_physical_C=" + bestPhysical.capital
        + " pick_physical_roi=" + bestPhysical.roi);
  }
  return { plane = bestPlane, economics = bestLegacy };
}

/* C103 : isolation causale du signal du premier C100 positif.
 *
 * On rejoue uniquement son CLASSEMENT moteur : vitesse NoAI directe et ancien
 * helper de manoeuvre pessimiste. Ce score n'est jamais retourne au portefeuille.
 * Chaque candidat doit rester calculable sous l'economie legacy, et le gagnant
 * retourne son objet legacy : admission, capital et score projet restent donc
 * strictement ceux du defaut. Contrairement a C101, aucun filtre capital-neutre
 * n'est ajoute, afin de reproduire fidelement l'argmax du premier C100. */
function OpexC103ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local bestPlane = null;
  local bestLegacy = null;
  local bestReplay = null;
  local rawPlane = selectedEconomics != null ? selectedPlane : null;
  local rawLegacy = selectedEconomics;

  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  foreach (plane in choices) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;

    local legacy = null;
    if (selectedPlane != null && plane.id == selectedPlane.id) {
      legacy = selectedEconomics;
    } else {
      legacy = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    }
    if (legacy == null) continue;

    if (rawLegacy == null || legacy.profitAnnual > rawLegacy.profitAnnual ||
        (legacy.profitAnnual == rawLegacy.profitAnnual && legacy.roi > rawLegacy.roi)) {
      rawPlane = plane;
      rawLegacy = legacy;
    }

    local replay = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, true);
    if (replay == null) continue;
    if (bestReplay == null || replay.profitAnnual > bestReplay.profitAnnual ||
        (replay.profitAnnual == bestReplay.profitAnnual && replay.roi > bestReplay.roi)) {
      bestPlane = plane;
      bestLegacy = legacy;
      bestReplay = replay;
    }
  }

  if (bestPlane == null || bestLegacy == null || bestReplay == null) {
    return { plane = rawPlane, economics = rawLegacy };
  }
  if (C69_BOTTLENECK_PROBE && rawPlane != null && rawLegacy != null
      && rawPlane.id != bestPlane.id) {
    OpexC69Log("phase=c103_choice policy=c100_rank_replay dist=" + distance
        + " raw_id=" + rawPlane.id + " raw_name=" + OpexPlaneName(rawPlane.id)
        + " raw_price=" + rawPlane.price + " raw_P=" + rawLegacy.profitAnnual
        + " raw_C=" + rawLegacy.capital + " raw_roi=" + rawLegacy.roi
        + " pick_id=" + bestPlane.id + " pick_name=" + OpexPlaneName(bestPlane.id)
        + " pick_price=" + bestPlane.price + " pick_legacy_P=" + bestLegacy.profitAnnual
        + " pick_legacy_C=" + bestLegacy.capital + " pick_legacy_roi=" + bestLegacy.roi
        + " pick_replay_P=" + bestReplay.profitAnnual + " pick_replay_C=" + bestReplay.capital
        + " pick_replay_roi=" + bestReplay.roi);
  }
  return { plane = bestPlane, economics = bestLegacy };
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

/* C106 candidat : frontiere marginale purement relative sur l'economie C100.1.
 * On part du profit physique maximal. Tant qu'un palier moins capitalistique
 * offre le meilleur profit sous ce capital et que le ROI marginal de l'upgrade
 * reste inferieur au ROI de ce palier, on redescend. Aucun montant de caisse,
 * EngineID ni seuil de richesse n'intervient ; le seul seuil est l'egalite des
 * deux rendements (ratio dimensionless = 1). Son usage reste passif sous C104. */
function OpexC106MarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
                                        infrastructureMaintenance, maxCapital,
                                        newAirportCount, opcodePadding,
                                        relativeRoiPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  while (true) {
    local runner = null;
    foreach (item in items) {
      if (item.economics.capital >= current.economics.capital) continue;
      if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
          (item.economics.profitAnnual == runner.economics.profitAnnual
           && item.economics.roi > runner.economics.roi)) runner = item;
    }
    if (runner == null) return current;
    local deltaCapital = current.economics.capital - runner.economics.capital;
    local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
    if (deltaCapital <= 0 || deltaProfit <= 0) return runner;
    local marginalRoi = (deltaProfit * 1000.0) / deltaCapital;
    if (marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille) return current;
    current = runner;
  }
}

/* C107 candidat passif : meme test marginal que C106, mais une seule marche.
 * Partir de l'argmax profit C100.1, prendre le meilleur profit strictement moins
 * capitalistique, puis refuser l'upgrade si son rendement marginal est inferieur
 * au ROI du palier moins cher. Pas de recursion : on evite ainsi de descendre
 * 218 -> 217 -> 216 quand seul le premier upgrade est mal remunere. */
function OpexC107OneStepMarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
                                               infrastructureMaintenance, maxCapital,
                                               newAirportCount, opcodePadding,
                                               relativeRoiPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  local runner = null;
  foreach (item in items) {
    if (item.economics.capital >= current.economics.capital) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
        (item.economics.profitAnnual == runner.economics.profitAnnual
         && item.economics.roi > runner.economics.roi)) runner = item;
  }
  if (runner == null) return current;
  local deltaCapital = current.economics.capital - runner.economics.capital;
  local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
  if (deltaCapital <= 0 || deltaProfit <= 0) return runner;
  local marginalRoi = (deltaProfit * 1000.0) / deltaCapital;
  if (marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille) return current;
  return runner;
}

/* C106 candidat principal : score C69 sur l'economie C100.1. */
function OpexC106PhysicalC69Choice(catalog, airport, distance, monthlyPax,
                                   infrastructureMaintenance, maxCapital,
                                   newAirportCount, opcodePadding)
{
  local kDec = C69_DECISION_BOTTLENECK ? OpexC69CachedKDec() : 0;
  local margin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local best = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local financeCapital = economics.capital + margin;
    if (("immobilise" in economics) && economics.immobilise > 0) financeCapital += economics.immobilise;
    local denom = financeCapital > kDec ? financeCapital : kDec;
    if (denom <= 0) continue;
    local score = OpexProjectScore(economics.profitAnnual, denom);
    local point = { plane = plane, economics = economics, financeCapital = financeCapital, score = score };
    if (best == null || point.score > best.score
        || (point.score == best.score && economics.profitAnnual > best.economics.profitAnnual)
        || (point.score == best.score && economics.profitAnnual == best.economics.profitAnnual
            && financeCapital < best.financeCapital)) best = point;
  }
  return best;
}

/* C106 : interpolation continue entre profit pur (alpha=0) et ROI-like
 * (alpha=1), sur le capital de financement AIR. alpha est code en seiziemes
 * afin de n'utiliser que sqrt(), deja disponible dans NoAI/Squirrel. */
function OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
                                     infrastructureMaintenance, maxCapital,
                                     newAirportCount, opcodePadding, alpha16)
{
  local margin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local best = null;
  local bestScore = -1.0;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local financeCapital = economics.capital + margin;
    if (("immobilise" in economics) && economics.immobilise > 0) financeCapital += economics.immobilise;
    if (financeCapital <= 0) continue;
    local c = financeCapital.tofloat();
    local r2 = sqrt(c);
    local r4 = sqrt(r2);
    local r8 = sqrt(r4);
    local r16 = sqrt(r8);
    local denom = 1.0;
    if ((alpha16 & 8) != 0) denom *= r2;
    if ((alpha16 & 4) != 0) denom *= r4;
    if ((alpha16 & 2) != 0) denom *= r8;
    if ((alpha16 & 1) != 0) denom *= r16;
    local score = economics.profitAnnual.tofloat() / denom;
    if (best == null || score > bestScore
        || (score == bestScore && economics.profitAnnual > best.economics.profitAnnual)
        || (score == bestScore && economics.profitAnnual == best.economics.profitAnnual
            && financeCapital < best.financeCapital)) {
      best = { plane = plane, economics = economics, financeCapital = financeCapital, score = score };
      bestScore = score;
    }
  }
  return best;
}

/* C108 candidat passif : regularisation de l'avantage de vitesse, sans capital
 * ni seuil de richesse. Le score est P / v^beta avec beta en quarts. Comme le
 * facteur d'unite de vitesse est commun a tous les moteurs, le classement est
 * invariant a un changement d'unite ; il s'agit d'une penalite relative, pas
 * d'un nouveau modele physique de temps de trajet. */
function OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
                                         infrastructureMaintenance, maxCapital,
                                         newAirportCount, opcodePadding, beta4)
{
  local best = null;
  local bestScore = -1.0;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    if (plane.speed <= 0) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local v = plane.speed.tofloat();
    local r2 = sqrt(v);
    local r4 = sqrt(r2);
    local denom = 1.0;
    if (beta4 == 1) denom = r4;
    else if (beta4 == 2) denom = r2;
    else if (beta4 == 3) denom = r2 * r4;
    else if (beta4 == 4) denom = v;
    local score = economics.profitAnnual.tofloat() / denom;
    if (best == null || score > bestScore
        || (score == bestScore && economics.profitAnnual > best.economics.profitAnnual)
        || (score == bestScore && economics.profitAnnual == best.economics.profitAnnual
            && economics.capital < best.economics.capital)) {
      best = { plane = plane, economics = economics, score = score };
      bestScore = score;
    }
  }
  return best;
}

/* C109 candidat passif : elasticite du profit au gain de vitesse.
 * On compare l'argmax de profit C100.1 au meilleur moteur strictement plus lent.
 * L'upgrade rapide n'est retenu que si (dP/P) / (dv/v) depasse un seuil relatif.
 * Aucun prix, capital, montant de caisse, EngineID ou temps fixe n'intervient. */
function OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
                                             infrastructureMaintenance, maxCapital,
                                             newAirportCount, opcodePadding,
                                             relativeElasticityPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    if (plane.speed <= 0) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  local runner = null;
  foreach (item in items) {
    if (item.plane.speed >= current.plane.speed) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
        (item.economics.profitAnnual == runner.economics.profitAnnual
         && item.economics.roi > runner.economics.roi)) runner = item;
  }
  if (runner == null) return current;
  local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
  local deltaSpeed = current.plane.speed - runner.plane.speed;
  if (deltaProfit <= 0 || deltaSpeed <= 0 || runner.economics.profitAnnual <= 0 || runner.plane.speed <= 0) {
    return runner;
  }
  local profitGainPermille = (deltaProfit * 1000.0) / runner.economics.profitAnnual;
  local speedGainPermille = (deltaSpeed * 1000.0) / runner.plane.speed;
  if (profitGainPermille * 1000.0 >= speedGainPermille * relativeElasticityPermille) return current;
  return runner;
}

/* C116 passif : regularisation du C68 legacy sur le cout incremental de
 * l'upgrade, sans timing C100/C100.1. */
function OpexC116LegacyIncrementalCandidates(catalog, airport, distance, monthlyPax,
                                             infrastructureMaintenance, maxCapital,
                                             newAirportCount, opcodePadding, legacy)
{
  if (legacy == null || legacy.plane == null || legacy.economics == null
      || legacy.economics.capital <= 0 || legacy.economics.profitAnnual <= 0) return null;
  local runner = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null || economics.capital <= 0 || economics.profitAnnual <= 0
        || economics.capital >= legacy.economics.capital) continue;
    if (runner == null || economics.profitAnnual > runner.economics.profitAnnual
        || (economics.profitAnnual == runner.economics.profitAnnual
            && economics.roi > runner.economics.roi)) runner = { plane = plane, economics = economics };
  }
  if (runner == null) return { runner = legacy, gate = legacy, score = legacy, marginal = legacy,
      opportunity = legacy, opportunitySteps = 0,
      deltaCapital = 0, deltaProfit = 0, kDec = OpexC69CachedKDec(), legacyScore = 0.0,
      runnerScore = 0.0, marginalRoi = 0.0 };

  local kDec = OpexC69CachedKDec();
  local deltaCapital = legacy.economics.capital - runner.economics.capital;
  local deltaProfit = legacy.economics.profitAnnual - runner.economics.profitAnnual;
  local legacyDenom = legacy.economics.capital > kDec ? legacy.economics.capital : kDec;
  local runnerDenom = runner.economics.capital > kDec ? runner.economics.capital : kDec;
  local legacyScore = legacyDenom > 0 ? (legacy.economics.profitAnnual.tofloat() * 1000.0) / legacyDenom : 0.0;
  local runnerScore = runnerDenom > 0 ? (runner.economics.profitAnnual.tofloat() * 1000.0) / runnerDenom : 0.0;
  local marginalRoi = deltaCapital > 0 ? (deltaProfit.tofloat() * 1000.0) / deltaCapital : 0.0;
  local gateChoice = legacy;
  local scoreChoice = legacy;
  local marginalChoice = legacy;
  local opportunityChoice = legacy;
  local opportunitySteps = 0;
  if (kDec > 0) {
    if (deltaCapital > kDec) gateChoice = runner;
    if (runnerScore > legacyScore) scoreChoice = runner;
    if (deltaCapital > kDec && deltaProfit > 0 && marginalRoi < runnerScore) marginalChoice = runner;

    /* C116.1 passif : cout d'opportunite relatif a chaque cran de la frontiere.
     * Refuser l'upgrade si son gain relatif de profit est inferieur a la part
     * d'un budget de decision K_dec qu'il immobilise : dP/P_runner < dC/K_dec. */
    local current = legacy;
    while (true) {
      local next = null;
      foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
        if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
        local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
            infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
        if (economics == null || economics.capital <= 0 || economics.profitAnnual <= 0
            || economics.capital >= current.economics.capital) continue;
        if (next == null || economics.profitAnnual > next.economics.profitAnnual
            || (economics.profitAnnual == next.economics.profitAnnual
                && economics.roi > next.economics.roi)) next = { plane = plane, economics = economics };
      }
      if (next == null) break;
      local stepCapital = current.economics.capital - next.economics.capital;
      local stepProfit = current.economics.profitAnnual - next.economics.profitAnnual;
      local relativeProfit = next.economics.profitAnnual > 0
          ? stepProfit.tofloat() / next.economics.profitAnnual.tofloat() : 0.0;
      local relativeCapital = stepCapital.tofloat() / kDec.tofloat();
      if (!(stepProfit > 0 && relativeProfit < relativeCapital)) break;
      current = next;
      opportunitySteps++;
    }
    opportunityChoice = current;
  }
  return { runner = runner, gate = gateChoice, score = scoreChoice, marginal = marginalChoice,
      opportunity = opportunityChoice, opportunitySteps = opportunitySteps,
      deltaCapital = deltaCapital, deltaProfit = deltaProfit, kDec = kDec,
      legacyScore = legacyScore, runnerScore = runnerScore, marginalRoi = marginalRoi };
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

function OpexC104ProbeAirEngineCompare(catalog, airport, distance, monthlyPax,
                                      infrastructureMaintenance, maxCapital,
                                      newAirportCount, opcodePadding)
{
  if (!C104_AIR_C100_COMPARE_PROBE || C104_AIR_C100_COMPARE_COUNT >= 600) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (!("__year" in C104_AIR_C100_COMPARE_SEEN) || C104_AIR_C100_COMPARE_SEEN["__year"] != year) {
    C104_AIR_C100_COMPARE_SEEN.rawset("__year", year);
    C104_AIR_C100_COMPARE_SEEN.rawset("__year_count", 0);
  }
  if (C104_AIR_C100_COMPARE_SEEN["__year_count"] >= 150) return;
  local key = airport.type + "|" + distance + "|" + monthlyPax + "|" + newAirportCount
      + "|" + maxCapital + "|" + opcodePadding;
  if (key in C104_AIR_C100_COMPARE_SEEN) return;
  C104_AIR_C100_COMPARE_SEEN.rawset(key, true);
  C104_AIR_C100_COMPARE_COUNT++;
  C104_AIR_C100_COMPARE_SEEN["__year_count"] = C104_AIR_C100_COMPARE_SEEN["__year_count"] + 1;

  local legacy = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0);
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  local physical = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 2);
  local c69Physical = OpexC106PhysicalC69Choice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local marginal = OpexC106MarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local oneStep = OpexC107OneStepMarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local power7 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 7);
  local power8 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 8);
  local power9 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 9);
  local power10 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 10);
  local speed1 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  local speed2 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 2);
  local speed3 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 3);
  local speed4 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 4);
  local elastic25 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 250);
  local elastic50 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 500);
  local elastic75 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 750);
  local elastic100 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1000);
  local c116 = OpexC116LegacyIncrementalCandidates(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, legacy);
  if (legacy == null || replay == null || physical == null || c69Physical == null || marginal == null
      || oneStep == null
      || power7 == null || power8 == null || power9 == null || power10 == null
      || speed1 == null || speed2 == null || speed3 == null || speed4 == null
      || elastic25 == null || elastic50 == null || elastic75 == null || elastic100 == null
      || c116 == null) return;
  local replayLegacy = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local replayPhysical = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, true, false);
  local physicalLegacy = OpexAirEconomics(catalog, airport, physical.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local physicalReplay = OpexAirEconomics(catalog, airport, physical.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, false, true);
  local marginalLegacy = OpexAirEconomics(catalog, airport, marginal.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local arm = newAirportCount == 2 ? "newpair" : (newAirportCount == 1 ? "hubsite" : "hubhub");
  local kDec = C69_DECISION_BOTTLENECK ? OpexC69CachedKDec() : 0;
  local available = OpexAvailableCapital();
  local financeMargin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local legacyFinance = legacy.economics.capital + financeMargin;
  if (("immobilise" in legacy.economics) && legacy.economics.immobilise > 0) legacyFinance += legacy.economics.immobilise;
  local runnerFinance = c116.runner.economics.capital + financeMargin;
  if (("immobilise" in c116.runner.economics) && c116.runner.economics.immobilise > 0) runnerFinance += c116.runner.economics.immobilise;
  local selfGap = legacyFinance > available ? legacyFinance - available : 0;
  local selfUnlock = legacyFinance > available && runnerFinance <= available ? 1 : 0;
  AILog.Warning("C104_COMPARE year=" + year + " arm=" + arm + " airport=" + airport.type
      + " dist=" + distance + " pax=" + monthlyPax + " maxC=" + maxCapital + " kdec=" + kDec
      + " " + OpexC104FormatAirChoice("legacy", legacy)
      + " " + OpexC104FormatAirChoice("replay", replay)
      + " " + OpexC104FormatAirChoice("physical", physical)
      + " " + OpexC104FormatAirChoice("c69phys", c69Physical)
      + " " + OpexC104FormatAirChoice("marginal", marginal)
      + " " + OpexC104FormatAirChoice("onestep", oneStep)
      + " " + OpexC104FormatAirChoice("p7", power7)
      + " " + OpexC104FormatAirChoice("p8", power8)
      + " " + OpexC104FormatAirChoice("p9", power9)
      + " " + OpexC104FormatAirChoice("p10", power10)
      + " " + OpexC104FormatAirChoice("s1", speed1)
      + " " + OpexC104FormatAirChoice("s2", speed2)
      + " " + OpexC104FormatAirChoice("s3", speed3)
      + " " + OpexC104FormatAirChoice("s4", speed4)
      + " " + OpexC104FormatAirChoice("e25", elastic25)
      + " " + OpexC104FormatAirChoice("e50", elastic50)
      + " " + OpexC104FormatAirChoice("e75", elastic75)
      + " " + OpexC104FormatAirChoice("e100", elastic100)
      + " " + OpexC104FormatAirChoice("replay_legacy", { plane = replay.plane, economics = replayLegacy })
      + " " + OpexC104FormatAirChoice("replay_physical", { plane = replay.plane, economics = replayPhysical })
      + " " + OpexC104FormatAirChoice("physical_legacy", { plane = physical.plane, economics = physicalLegacy })
      + " " + OpexC104FormatAirChoice("physical_replay", { plane = physical.plane, economics = physicalReplay })
      + " " + OpexC104FormatAirChoice("marginal_legacy", { plane = marginal.plane, economics = marginalLegacy })
      + " " + OpexC104FormatAirChoice("c116_runner", c116.runner)
      + " " + OpexC104FormatAirChoice("c116_gate", c116.gate)
      + " " + OpexC104FormatAirChoice("c116_score", c116.score)
      + " " + OpexC104FormatAirChoice("c116_marg", c116.marginal)
      + " " + OpexC104FormatAirChoice("c116_opp", c116.opportunity)
      + " c116_dC=" + c116.deltaCapital + " c116_dP=" + c116.deltaProfit
      + " c116_lscore=" + c116.legacyScore + " c116_rscore=" + c116.runnerScore
      + " c116_mroi=" + c116.marginalRoi + " c116_opp_steps=" + c116.opportunitySteps
      + " c116_avail=" + available + " c116_legacy_fin=" + legacyFinance
      + " c116_runner_fin=" + runnerFinance + " c116_self_gap=" + selfGap
      + " c116_self_unlock=" + selfUnlock
      + OpexC116FormatProjectSnapshot(c116.deltaCapital));
}

/* C105 : cellule manquante du factoriel C100/C103.
 * Le timing global est C100.1 via C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS,
 * mais le moteur est classe avec le replay du premier C100. L'economie rendue
 * au portefeuille est ensuite recalculee en C100.1 pour CE moteur. */
function OpexC105ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  if (replay == null) return { plane = selectedPlane, economics = selectedEconomics };
  local physical = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, true, false);
  if (physical == null) return { plane = selectedPlane, economics = selectedEconomics };
  return { plane = replay.plane, economics = physical };
}


/* C111 : cellule d'isolation manquante apres C103/C109.
 * - equipement : meme replay moteur que le premier C100 positif (C103), avec
 *   economie LEGACY du moteur effectivement achete ;
 * - decision : argmax C68 legacy conserve dans decisionEconomics.
 * Le portefeuille peut donc garder sa valeur de marche C68 tandis que la caisse
 * et le constructeur voient le vrai moteur choisi. */
function OpexC111ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local decision = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0);
  if (decision == null || decision.plane == null || decision.economics == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  local equipment = OpexC103ChooseRoutePlane(catalog, airport, decision.plane, decision.economics,
      distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (equipment == null || equipment.plane == null || equipment.economics == null
      || equipment.economics.revenueAnnual <= 0 || equipment.economics.capital <= 0
      || (!C113_AIR_C100_FULL_DECISION_SHADOW && equipment.economics.profitAnnual <= 0)) {
    return { plane = decision.plane, economics = decision.economics,
        decisionEconomics = decision.economics };
  }
  return { plane = equipment.plane, economics = equipment.economics,
      decisionEconomics = decision.economics };
}

/* C116.3 passif : reproduit l'argmax C68 et conserve les evaluations pour
 * trouver le meilleur runner moins capitalistique sans second scan moteur. */
function OpexC116LegacyDecisionRunner(catalog, airport, distance, monthlyPax,
                                      infrastructureMaintenance, maxCapital,
                                      newAirportCount, opcodePadding)
{
  local items = [];
  local decision = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, false);
    if (economics == null) continue;
    local item = { plane = plane, economics = economics };
    items.append(item);
    if (decision == null || economics.profitAnnual > decision.economics.profitAnnual
        || (economics.profitAnnual == decision.economics.profitAnnual
            && economics.roi > decision.economics.roi)) decision = item;
  }
  if (decision == null) return null;
  local runner = null;
  foreach (item in items) {
    if (item.economics.capital >= decision.economics.capital) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual
        || (item.economics.profitAnnual == runner.economics.profitAnnual
            && item.economics.roi > runner.economics.roi)) runner = item;
  }
  return { decision = decision, runner = runner, items = items };
}

function OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
                                 newAirportCount, opcodePadding,
                                 scan, chosen, kDec, replayUsed)
{
  if (!C116_AIR_PROJECT_PROBE || scan == null || scan.decision == null || chosen == null) return;
  if (C116_AIR_PROJECT_SNAPSHOT == null) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (C116_AIR_PROJECT_PROBE_YEAR != year) {
    C116_AIR_PROJECT_PROBE_YEAR = year;
    C116_AIR_PROJECT_PROBE_YEAR_COUNT = 0;
  }
  if (C116_AIR_PROJECT_PROBE_COUNT >= 600 || C116_AIR_PROJECT_PROBE_YEAR_COUNT >= 150) return;
  local key = year + "|" + airport.type + "|" + distance + "|" + monthlyPax + "|"
      + newAirportCount + "|" + maxCapital + "|" + opcodePadding;
  if (key in C116_AIR_PROJECT_PROBE_SEEN) return;
  C116_AIR_PROJECT_PROBE_SEEN.rawset(key, true);
  C116_AIR_PROJECT_PROBE_COUNT++;
  C116_AIR_PROJECT_PROBE_YEAR_COUNT++;

  local decision = scan.decision;
  local runner = scan.runner;
  local deltaCapital = 0;
  local deltaProfit = 0;
  local marginalRoi = 0.0;
  if (runner != null) {
    deltaCapital = decision.economics.capital - runner.economics.capital;
    deltaProfit = decision.economics.profitAnnual - runner.economics.profitAnnual;
    if (deltaCapital > 0) marginalRoi = (deltaProfit.tofloat() * 1000.0) / deltaCapital.tofloat();
  }
  local available = OpexAvailableCapital();
  local financeMargin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local legacyFinance = decision.economics.capital + financeMargin;
  if (("immobilise" in decision.economics) && decision.economics.immobilise > 0) legacyFinance += decision.economics.immobilise;
  local runnerFinance = runner != null ? runner.economics.capital + financeMargin : legacyFinance;
  if (runner != null && ("immobilise" in runner.economics) && runner.economics.immobilise > 0) runnerFinance += runner.economics.immobilise;
  local selfGap = legacyFinance > available ? legacyFinance - available : 0;
  local selfUnlock = runner != null && legacyFinance > available && runnerFinance <= available ? 1 : 0;
  local arm = newAirportCount == 2 ? "newpair" : (newAirportCount == 1 ? "hubsite" : "hubhub");
  local runnerText = runner != null ? OpexC104FormatAirChoice("runner", runner) : "runner_id=-1";
  AILog.Warning("C116_PROJECT year=" + year + " arm=" + arm + " airport=" + airport.type
      + " dist=" + distance + " pax=" + monthlyPax + " maxC=" + maxCapital
      + " kdec=" + kDec + " avail=" + available + " replay_used=" + replayUsed
      + " " + OpexC104FormatAirChoice("legacy", decision)
      + " " + OpexC104FormatAirChoice("c115", chosen)
      + " " + runnerText
      + " dC=" + deltaCapital + " dP=" + deltaProfit + " mroi=" + marginalRoi
      + " legacy_fin=" + legacyFinance + " runner_fin=" + runnerFinance
      + " self_gap=" + selfGap + " self_unlock=" + selfUnlock
      + OpexC116FormatProjectSnapshot(deltaCapital));
}

/* C115 : conserver le couplage choix moteur + economie de route qui porte le
 * signal C114, mais seulement lorsque le capital est encore le goulot de la
 * decision. K_dec = flux * temps entre constructions : si K_dec >= C68.capital,
 * economiser davantage de capital n'augmente plus le debit d'investissement et
 * on garde donc le profit absolu C68. Sinon on utilise le replay exact du premier
 * C100, sans constante de richesse ni seuil temporel. */
function OpexC115ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  /* selectedEconomics est seulement l'economie de l'appareil d'entree de
   * OpexAirChooseRoutePlaneFull. Recalculer explicitement l'argmax C68 avant de
   * tester le goulot, sinon K_dec serait compare au mauvais capital. */
  local scan = C116_AIR_PROJECT_PROBE
      ? OpexC116LegacyDecisionRunner(catalog, airport, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
      : null;
  local decision = scan != null ? scan.decision
      : OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0);
  if (decision == null || decision.plane == null || decision.economics == null
      || decision.economics.capital <= 0) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  local kDec = OpexC69CachedKDec();
  if (kDec >= decision.economics.capital) {
    if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
        newAirportCount, opcodePadding, scan, decision, kDec, 0);
    local result = { plane = decision.plane, economics = decision.economics };
    return result;
  }
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  if (replay == null || replay.plane == null || replay.economics == null) {
    if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
        newAirportCount, opcodePadding, scan, decision, kDec, 0);
    local result = { plane = decision.plane, economics = decision.economics };
    return result;
  }
  if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
      newAirportCount, opcodePadding, scan, replay, kDec, 1);
  local result = { plane = replay.plane, economics = replay.economics };
  return result;
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
  if (C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY
      && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION
      && !C85_AIR_EQUIPMENT_FRONTIER && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C111_AIR_C100_DECISION_SHADOW) {
    OpexC104ProbeAirEngineCompare(catalog, airport, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER
      && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C111_AIR_C100_DECISION_SHADOW) {
    return OpexC105ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION
      && !C85_AIR_EQUIPMENT_FRONTIER && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C104_AIR_C100_COMPARE_PROBE && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS) {
    return OpexC111ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY
      && !C85_AIR_EQUIPMENT_FRONTIER && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C111_AIR_C100_DECISION_SHADOW) {
    return OpexC115ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY) {
    return OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance,
        monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C103_AIR_C100_RANK_REPLAY && C72_PLANE_CHOICE == 0
      && !C100_AIR_TRIP_PHYSICAL
      && !C85_AIR_EQUIPMENT_FRONTIER && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C111_AIR_C100_DECISION_SHADOW) {
    return OpexC103ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C101_AIR_PHYSICAL_ENGINE_CHOICE && C72_PLANE_CHOICE == 0
      && !C100_AIR_TRIP_PHYSICAL
      && !C85_AIR_EQUIPMENT_FRONTIER && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C111_AIR_C100_DECISION_SHADOW) {
    return OpexC101ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
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
  /* C85 ne change que l'objectif C68 historique (profit max). Les modes C72/C82 ont des
   * objectifs differents ; ils conservent volontairement la liste complete. Le selectedPlane
   * reste evalue separement ci-dessus, meme s'il est domine et absent de la frontier. */
  if (C85_AIR_EQUIPMENT_FRONTIER && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION
      && ("airPlaneFrontierByAirport" in catalog)
      && airport.type in catalog.airPlaneFrontierByAirport
      && catalog.airPlaneFrontierByAirport[airport.type].len() > 0) {
    routePlaneChoices = catalog.airPlaneFrontierByAirport[airport.type];
  }

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
