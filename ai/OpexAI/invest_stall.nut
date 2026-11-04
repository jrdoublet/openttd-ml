/* INVEST-STALL v2 : 1974+ cash dormant + sous-transport FREIGHT sur les
 * industries DEJA servies. Aucun doublement de flotte sur voie unique ici.
 * Les decisions physiques passent par invest_stall_fleet.nut ou les plans
 * station distincte certifies par le constructeur standard.
 *
 * La v1 de balayage multicargo a ete abandonnee : 157 scans sans un projet
 * publie en 1979 sur les quatre graines du smoke R1. Le moindre changement
 * de politique reste strictement protege par INVEST_STALL (defaut false). */

/* Seuil unique du mandat : 750 k£ disponibles, a lire sans modifier le budget.
 * Renvoyer false aussi quand le jeu n'est pas encore en 1974. */
function OpexInvestStallReady()
{
  return INVEST_STALL && MODE_RAIL
      && AIDate.GetYear(AIDate.GetCurrentDate()) >= OPEX_START_YEAR + 4
      && OpexAvailableCapital() >= 750000;
}

/* Une transaction V284 deja entamee reste a reconcilier et, si necessaire,
 * a annuler meme si l'option est retiree entre Save et Load. Cela n'arme
 * aucun nouvel investissement et ne touche pas une partie OFF historique. */
function OpexInvestStallPending(owner)
{
  if (owner == null || owner._v284State == null
      || !("pending" in owner._v284State)) return false;
  local pending = owner._v284State.pending;
  return pending != null && ("investStall" in pending) && pending.investStall;
}

/* Capacite REELLE approximative mensuelle de la rame (offres sur 30 jours) :
 * meme formule trajet + temps de gare que V233L, AUCUNE ecriture en jeu.
 * Une rame non valide n'ajoute pas de capacite fictive. */
function OpexInvestStallLineCapacity(line)
{
  /* La formule monohead ne peut pas etre appliquee a un multihead : ni
   * nombre de wagons = total-1, ni vitesse d'un seul moteur. La porte
   * SourceGap refusera toute origine concerneee plutot que creer une
   * offre fictive a partir de ce zero conservateur. */
  if (OpexRailLongV3MultiLine(line)) return 0.0;
  if (line == null || !("vehicles" in line) || line.vehicles == null
      || !("cargo" in line) || !("distance" in line)) return 0.0;
  local dist = ("routeDistance" in line) && line.routeDistance > 0
      ? line.routeDistance : line.distance;
  if (dist <= 0) return 0.0;
  local total = 0.0;
  foreach (train in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(train)
        || AIVehicle.GetVehicleType(train) != AIVehicle.VT_RAIL
        || AIVehicle.GetNumWagons(train) < 2) continue;
    local wagonId = AIVehicle.GetWagonEngineType(train, 1);
    if (!AIEngine.IsWagon(wagonId)) continue;
    local wagon = OpexV257Engine(wagonId, line.cargo, true);
    local loco = OpexV257Engine(AIVehicle.GetEngineType(train), line.cargo, false);
    if (wagon == null || loco == null || wagon.capacity <= 0) continue;
    local speed = OpexRailEffectiveSpeed(loco, wagon,
        AIVehicle.GetNumWagons(train) - 1, dist);
    if (speed <= 0) continue;
    local oneWay = dist / (0.036 * speed);
    local cycle = 2.0 * oneWay + OpexRailStationDwellDays(wagon);
    if (cycle <= 0) continue;
    local capacity = AIVehicle.GetCapacity(train, line.cargo);
    if (capacity > 0) total += capacity * 30.0 / cycle;
  }
  return total;
}

/* Pourcentage transporte = statistique de l'industrie (y compris autres
 * transporteurs) ; rating = note reelle de la gare de la ligne. La capacité
 * agrège toutes les lignes ferroviaires de cette origine et de ce cargo :
 * une gare existante n'est pas un monopole, et le besoin n'est pas compte
 * plusieurs fois. Le besoin d'une gare neuve et d'une rame neuve utilise
 * exactement cette porte, sans surestimer le fret restant. */
function OpexInvestStallSourceGap(owner, line)
{
  local missing = { ok = false, reason = "missing", production = 0, pct = -1,
                    rating = -1, waiting = -1, capacity = 0.0, industry = -1 };
  if (!INVEST_STALL || owner == null || line == null
      || !("kind" in line) || line.kind != "freight"
      || !(("mode" in line) && line.mode == "rail")
      || !("originA" in line) || !("cargo" in line)
      || !("vehicles" in line) || line.vehicles == null
      || line.vehicles.len() == 0
      || (("scrapping" in line) && line.scrapping)) return missing;
  local industry = ("srcIndustry" in line) ? line.srcIndustry
      : AIIndustry.GetIndustryID(line.originA);
  if (!AIIndustry.IsValidIndustry(industry)) {
    missing.reason = "industry"; return missing;
  }
  local production = AIIndustry.GetLastMonthProduction(industry, line.cargo);
  local pct = AIIndustry.GetLastMonthTransportedPercentage(industry, line.cargo);
  local station = OpexLineStationId(line, "A");
  if (station < 0 || !AIStation.IsValidStation(station)) {
    missing.reason = "station"; return missing;
  }
  /* NoAI 15.3 retourne deja GetCargoRating en pourcentage 0..100
   * (conversion ToPercent8 faite par l'API). Ne pas diviser une seconde
   * fois par 255 : cela sous-evaluerait l'offre captee par 2,55. */
  local rawRating = AIStation.GetCargoRating(station, line.cargo);
  local rating = (rawRating >= 0 && rawRating <= 100) ? rawRating : -1;
  local waiting = AIStation.GetCargoWaiting(station, line.cargo);
  local total = 0.0;
  foreach (existing in owner._lines) {
    if (existing == null || !("kind" in existing) || existing.kind != "freight"
        || !("mode" in existing) || existing.mode != "rail"
        || !("cargo" in existing) || existing.cargo != line.cargo) continue;
    local existingId = ("srcIndustry" in existing) ? existing.srcIndustry
        : AIIndustry.GetIndustryID(existing.originA);
    if (existingId == industry && OpexRailLongV3MultiLine(existing)) {
      missing.reason = "multihead_unmodelled";
      return missing;
    }
    if (existingId == industry) total += OpexInvestStallLineCapacity(existing);
  }
  local info = { ok = false, reason = "", production = production, pct = pct,
                 rating = rating, waiting = waiting, capacity = total,
                 industry = industry };
  if (production <= 0 || pct < 0 || pct > 100 || rating < 0 || rating > 100
      || total <= 0.0) {
    info.reason = "bad_measurement"; return info;
  }
  if (pct >= 75 && rating >= 75) {
    info.reason = "carried_or_rated"; return info;
  }
  if (production.tofloat() <= total) {
    info.reason = "capacity_enough"; return info;
  }
  info.reason = "shortfall";
  info.ok = true;
  return info;
}

/* Sonde annuelle / mensuelle, sans generation et sans achat.
 * Le controle de caisse et la date sont releves explicitement, meme quand
 * aucune origine n'est retenue. Les decisions fleet/origins sont ailleurs. */
function OpexInvestStallTick(ai)
{
  if (!INVEST_STALL || ai == null || ai._lines == null) return;
  local date = AIDate.GetCurrentDate();
  local year = AIDate.GetYear(date);
  if (year < OPEX_START_YEAR + 4) return;
  local month = year * 12 + AIDate.GetMonth(date);
  if (INVEST_STALL_LAST_MONTH == month) return;
  INVEST_STALL_LAST_MONTH = month;
  local cash = OpexAvailableCapital();
  if (DECISION_LOG) OpexDecide("INVEST_STALL", "event=gate month=" + month
      + " cash=" + cash + " min_cash=750000 ready=" + (OpexInvestStallReady() ? 1 : 0));
  if (!OpexInvestStallReady()) return;
  local count = 0;
  local total = 0;
  foreach (line in ai._lines) {
    if (!("kind" in line) || line.kind != "freight" || !("mode" in line)
        || line.mode != "rail") continue;
    total++;
    local gap = OpexInvestStallSourceGap(ai, line);
    if (gap.ok) count++;
    if (DECISION_LOG) OpexDecide("INVEST_STALL", "event=screen line=" + line.lineId
        + " reason=" + gap.reason + " accepted=" + (gap.ok ? 1 : 0)
        + " production=" + gap.production + " pct=" + gap.pct
        + " rating=" + gap.rating + " waiting=" + gap.waiting
        + " capacity_month=" + gap.capacity);
  }
  if (DECISION_LOG) OpexDecide("INVEST_STALL", "event=summary month=" + month
      + " cash=" + cash + " freight_lines=" + total + " underserved=" + count);
}
