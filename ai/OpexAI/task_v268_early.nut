/* V268 : estimation precoce du rendement realise des lignes a 3, 6, 12, 24 mois.
 * Etape 1 (shadow) : observation et journalisation seulement, aucune decision modifiee.
 *
 * Mesure du profit d'exploitation par differences de AIVehicle.GetProfitThisYear()
 * entre deux observations, passage d'annee compris (logique de C117, probes.nut:574-600,
 * generalisee aux modes AIR, RAIL, ROAD et aux genres pax et fret).
 *
 * Suivi par vehicule et par ligne : chaque vehicule ajoute ou remplace ouvre sa
 * propre fenetre temporelle (startDate = now, profitObs = 0, trips = 0).
 * Comptage des trajets charges termines par transition d'ordre NoAI (comme C117).
 * AICargoMonitor (disponible en 15.3) n'est pas utilise a cette etape.
 *
 * Aux paliers 3, 6, 12 et 24 mois (~90, 180, 365, 730 jours), journalisation :
 * OpexDecide("V268_EST", "palier=... line=... mode=... kind=... veh=... days=... trips=... profit_obs=... p_annual=... pred_amort=... predicted=...")
 * Formule : P_annuel = 365,25 / J * P_obs - A_annuel (predAmort de la ligne).
 *
 * Cout d'opcodes : O(nombre de vehicules), aucun balayage de carte.
 * Etat non sauvegarde (en memoire seule pour le banc).
 */

function OpexV268Step(lines, catalog = null, forceSample = false)
{
  if (V268_C70_EARLY <= 0) return;
  /* Le mode 1 n'est qu'un journal : sans decision_log, rien a faire. Le mode 2 echantillonne
   * toujours, C70 en depend. */
  if (V268_C70_EARLY == 1 && !DECISION_LOG) return;
  if (lines == null) return;

  local now = AIDate.GetCurrentDate();
  if (!forceSample && V268_LAST_SAMPLE_DATE >= 0 && now - V268_LAST_SAMPLE_DATE < 2) return;
  V268_LAST_SAMPLE_DATE = now;
  local nowYear = AIDate.GetYear(now);

  local mailActive = false;
  local mailCargoId = -1;
  if (catalog != null && ("mailCargo" in catalog) && catalog.mailCargo >= 0
      && AICargo.IsValidCargo(catalog.mailCargo)) {
    mailActive = true;
    mailCargoId = catalog.mailCargo;
  }

  local paliers = [
    [3, 90],
    [6, 180],
    [12, 365],
    [24, 730]
  ];

  foreach (line in lines) {
    if (line == null || !("mode" in line) || !("lineId" in line)) continue;
    local mode = line.mode;
    if (mode != "air" && mode != "rail" && mode != "road") continue;

    local vehicles = null;
    if (("vehicles" in line) && line.vehicles != null) {
      vehicles = line.vehicles;
    } else if (mode == "road" && ("stationA" in line)) {
      local stA = AIStation.GetStationID(line.stationA);
      if (AIStation.IsValidStation(stA)) {
        vehicles = OpexLineVehicleIds(line, stA);
      }
    }
    if (vehicles == null || vehicles.len() == 0) continue;

    local expectedVt = -1;
    if (mode == "air") expectedVt = AIVehicle.VT_AIR;
    else if (mode == "rail") expectedVt = AIVehicle.VT_RAIL;
    else if (mode == "road") expectedVt = AIVehicle.VT_ROAD;

    local cargo = ("cargo" in line) ? line.cargo : -1;
    /* Les lignes AIR et ROAD ne portent pas toujours `kind` : classer par la cargaison. */
    local kindStr = ((("kind" in line) && line.kind == "pax")
        || (cargo >= 0 && (AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)
            || AICargo.HasCargoClass(cargo, AICargo.CC_MAIL)))) ? "pax" : "fret";
    local predAmort = ("predAmort" in line) ? line.predAmort : 0;
    local predProfit = ("predicted" in line) ? line.predicted : 0;

    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) {
        if (v in V268_VEHICLE_STATE) delete V268_VEHICLE_STATE[v];
        continue;
      }
      if (expectedVt >= 0 && AIVehicle.GetVehicleType(v) != expectedVt) continue;

      local engine = AIVehicle.GetEngineType(v);
      local inOrderList = AIOrder.IsCurrentOrderPartOfOrderList(v);
      local curOrder = inOrderList
          ? AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT) : AIOrder.ORDER_INVALID;
      local vehicleRunning = AIVehicle.GetState(v) == AIVehicle.VS_RUNNING;
      local thisProfit = AIVehicle.GetProfitThisYear(v);

      local cap = (cargo >= 0) ? AIVehicle.GetCapacity(v, cargo) : 0;
      if (cap < 0) cap = 0;
      local load = (cap > 0 && cargo >= 0) ? AIVehicle.GetCargoLoad(v, cargo) : 0;
      if (load <= 0 && mailActive) {
        local mailCap = AIVehicle.GetCapacity(v, mailCargoId);
        if (mailCap > 0 && AIVehicle.GetCargoLoad(v, mailCargoId) > 0) {
          load = AIVehicle.GetCargoLoad(v, mailCargoId);
        }
      }

      local vehicleState = (v in V268_VEHICLE_STATE) ? V268_VEHICLE_STATE[v] : null;
      if (vehicleState == null || vehicleState.lineId != line.lineId
          || vehicleState.engine != engine) {
        V268_VEHICLE_STATE.rawset(v, {
          lineId = line.lineId,
          engine = engine,
          order = curOrder,
          legLoadMax = vehicleRunning ? load : 0,
          legMoving = vehicleRunning,
          startDate = now,
          lastDate = now,
          profitYear = nowYear,
          profitThisYear = thisProfit,
          profitObs = 0,
          trips = 0,
          milestones = {}
        });
        continue;
      }

      local deltaDays = now - vehicleState.lastDate;
      if (deltaDays > 0) {
        local profitDelta = 0;
        if (vehicleState.profitYear == nowYear) {
          profitDelta = thisProfit - vehicleState.profitThisYear;
        } else if (vehicleState.profitYear + 1 == nowYear) {
          profitDelta = (AIVehicle.GetProfitLastYear(v) - vehicleState.profitThisYear) + thisProfit;
        }
        vehicleState.profitObs += profitDelta;
      }
      vehicleState.profitYear = nowYear;
      vehicleState.profitThisYear = thisProfit;
      vehicleState.lastDate = now;

      if (curOrder != AIOrder.ORDER_INVALID && curOrder >= 0) {
        if (vehicleState.order == AIOrder.ORDER_INVALID || vehicleState.order < 0) {
          vehicleState.order = curOrder;
          vehicleState.legLoadMax = vehicleRunning ? load : 0;
          vehicleState.legMoving = vehicleRunning;
        } else if (curOrder == vehicleState.order) {
          if (vehicleRunning) {
            vehicleState.legMoving = true;
            if (load > vehicleState.legLoadMax) vehicleState.legLoadMax = load;
          }
        } else {
          if (vehicleState.legMoving && vehicleState.legLoadMax > 0) {
            vehicleState.trips++;
          }
          vehicleState.order = curOrder;
          vehicleState.legLoadMax = vehicleRunning ? load : 0;
          vehicleState.legMoving = vehicleRunning;
        }
      }

      local daysObs = now - vehicleState.startDate;
      if (daysObs > 0) {
        foreach (entry in paliers) {
          local p = entry[0];
          local minDays = entry[1];
          if (daysObs >= minDays && !(p in vehicleState.milestones)) {
            vehicleState.milestones.rawset(p, true);
            if (!DECISION_LOG) continue;
            local pAnnual = (365.25 / daysObs.tofloat() * vehicleState.profitObs - predAmort).tointeger();
            local fields = "palier=" + p
                + " line=" + line.lineId
                + " mode=" + mode
                + " kind=" + kindStr
                + " veh=" + v
                + " days=" + daysObs
                + " trips=" + vehicleState.trips
                + " profit_obs=" + vehicleState.profitObs
                + " p_annual=" + pAnnual
                + " pred_amort=" + predAmort
                + " predicted=" + predProfit;
            OpexDecide("V268_EST", fields);
          }
        }
      }
    }
  }
}

/* V268 mode 2 : profit annualise moyen par vehicule de la ligne, sur les vehicules observes
 * depuis au moins V268_EARLY_MIN_DAYS (6 mois : biais ~0 contre le realise a 12 mois,
 * exposition 3x5 du 19/10 ; 3 mois sous-estime de moitie). Brut : sans amortissement,
 * comme GetProfitLastYear dans C70. null sans vehicule assez ancien. */
function OpexV268LineEarlyProfit(line)
{
  if (!("vehicles" in line) || line.vehicles == null || !("lineId" in line)) return null;
  local now = AIDate.GetCurrentDate();
  local sum = 0.0;
  local n = 0;
  foreach (v in line.vehicles) {
    if (!(v in V268_VEHICLE_STATE)) continue;
    local st = V268_VEHICLE_STATE[v];
    if (st.lineId != line.lineId) continue;
    local days = now - st.startDate;
    if (days < V268_EARLY_MIN_DAYS) continue;
    sum += 365.25 / days.tofloat() * st.profitObs;
    n++;
  }
  if (n == 0) return null;
  return sum / n;
}

function OpexV268MonthlyReport(lines, catalog = null)
{
  if (V268_C70_EARLY <= 0) return;
  OpexV268Step(lines, catalog, true);
}
