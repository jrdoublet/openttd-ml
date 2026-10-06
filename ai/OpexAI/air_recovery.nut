/* R19 : liquidations de chantiers AIR inacheves. Seulement entiers/chaines/tableaux
 * pour Save, y compris le format court. Aucun reglage experimental ne desarme
 * la recuperation d'avions deja achetes. Un refus ne vaut jamais vente/retrait. */
OPEX_AIR_ROLLBACKS <- [];

function OpexAirRecoveryOwnsAirport(anchor)
{
  foreach (ticket in OPEX_AIR_ROLLBACKS) {
    foreach (tile in ticket.airports) {
      if (tile == anchor) return true;
    }
  }
  return false;
}

function OpexAirRecoveryBlocksPlan(plan)
{
  if (OPEX_AIR_ROLLBACKS.len() == 0) return false;
  /* Passage unique sur les tickets (au lieu de trois balayages). */
  local a = plan.siteA.anchor;
  local b = plan.siteB.anchor;
  local pairKey = OpexAirPairKey(plan.siteA, plan.siteB);
  foreach (ticket in OPEX_AIR_ROLLBACKS) {
    if (ticket.pairKey != "" && ticket.pairKey == pairKey) return true;
    foreach (tile in ticket.airports) {
      if (tile == a || tile == b) return true;
    }
  }
  return false;
}

/* Rend true uniquement apres disparition des avions ET des aeroports neufs.
 * Les hubs reutilises ne sont jamais inscrits dans ticket.airports. */
function OpexAirContinueRollback(ticket, lines = null)
{
  ticket.nextDate = AIDate.GetCurrentDate() + 30;
  local remaining = [];
  foreach (vehicle in ticket.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle)) continue;
    if (AIVehicle.IsStoppedInDepot(vehicle)) {
      if (AIVehicle.SellVehicle(vehicle)) continue;
    } else {
      /* SendVehicleToDepot bascule un ordre halt existant : ne pas le renvoyer.
       * Un ordre de simple entretien peut en revanche etre converti en halt. */
      local halted = false;
      if (AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)) {
        local flags = AIOrder.GetOrderFlags(vehicle, AIOrder.ORDER_CURRENT);
        halted = flags == AIOrder.OF_INVALID || (flags & AIOrder.OF_STOP_IN_DEPOT) != 0;
      }
      if (!halted) AIVehicle.SendVehicleToDepot(vehicle);
    }
    remaining.append(vehicle);
  }
  ticket.vehicles = remaining;
  if (remaining.len() > 0) return false;

  local airportCount = ticket.airports.len();
  local airports = [];
  foreach (tile in ticket.airports) {
    if (!AIAirport.IsAirportTile(tile)) continue;
    /* Ne jamais toucher une installation qui n'est plus a nous. */
    if (!AICompany.IsMine(AITile.GetOwner(tile))) continue;
    local used = false;
    if (lines != null) {
      foreach (line in lines) {
        if (line.stationA == tile || line.stationB == tile) { used = true; break; }
      }
    }
    /* Garde physique en plus des lignes : couvre aussi le format court et un
     * service apparu pendant une suspension. Un aeroport occupe reste suivi. */
    local station = AIStation.GetStationID(tile);
    if (AIStation.IsValidStation(station)) {
      local users = AIVehicleList_Station(station);
      if (users.Count() > 0) used = true;
    }
    if (!used && AIAirport.RemoveAirport(tile)) continue;
    airports.append(tile);
  }
  ticket.airports = airports;
  if (AIR0310_SITE_VALIDITY_CACHE && airports.len() != airportCount)
    OpexAir0310InvalidateSiteValidity();
  return airports.len() == 0;
}

/* Un seul ticket par passage ordinaire de scrap, sans Sleep ni boucle d'attente.
 * Rotation meme avant echeance : aucun ticket bloque ne monopolise la file. */
function OpexAirProcessRollbacks(lines)
{
  if (OPEX_AIR_ROLLBACKS.len() == 0) return;
  local ticket = OPEX_AIR_ROLLBACKS[0];
  if (AIDate.GetCurrentDate() >= ticket.nextDate && OpexAirContinueRollback(ticket, lines)) {
    AILog.Info("AIR_ROLLBACK_DONE pair=" + ticket.pairKey);
    OPEX_AIR_ROLLBACKS.remove(0);
    return;
  }
  /* Construire hors de la file publiee : Save ne doit jamais voir le ticket
   * absent entre remove et append si la VM suspend sur son budget d'opcodes. */
  local rotated = OPEX_AIR_ROLLBACKS.slice(1);
  rotated.append(ticket);
  OPEX_AIR_ROLLBACKS = rotated;
}

/* Une sauvegarde peut couper entre vente et mise a jour du tableau. Purger les
 * IDs deja disparus avant toute nouvelle construction pouvant les recycler. */
function OpexAirReconcileRollbacks()
{
  local pending = [];
  foreach (ticket in OPEX_AIR_ROLLBACKS) {
    local vehicles = [];
    foreach (vehicle in ticket.vehicles) {
      if (AIVehicle.IsValidVehicle(vehicle)) vehicles.append(vehicle);
    }
    ticket.vehicles = vehicles;
    local airports = [];
    foreach (tile in ticket.airports) {
      if (AIAirport.IsAirportTile(tile) && AICompany.IsMine(AITile.GetOwner(tile))) airports.append(tile);
    }
    ticket.airports = airports;
    if (vehicles.len() > 0 || airports.len() > 0) pending.append(ticket);
  }
  OPEX_AIR_ROLLBACKS = pending;
}

/* Load : validation de forme uniquement, sans API du monde ni commandes.
 * L'etat est recopie ; les identifiants disparus seront purges par scrap. */
function OpexLoadAirRollbacks(data)
{
  local out = [];
  if (typeof data != "array") return out;
  foreach (ticket in data) {
    if (typeof ticket != "table" || !("version" in ticket)
        || typeof ticket.version != "integer" || ticket.version != 1
        || !("vehicles" in ticket) || typeof ticket.vehicles != "array"
        || !("airports" in ticket) || typeof ticket.airports != "array"
        || !("pairKey" in ticket) || typeof ticket.pairKey != "string"
        || !("nextDate" in ticket) || typeof ticket.nextDate != "integer" || ticket.nextDate < 0) continue;
    local valid = true;
    foreach (ids in [ticket.vehicles, ticket.airports]) {
      foreach (id in ids) {
        if (typeof id != "integer" || id < 0) { valid = false; break; }
      }
    }
    if (!valid) continue;
    out.append({ version = 1, vehicles = clone ticket.vehicles,
        airports = clone ticket.airports, pairKey = ticket.pairKey, nextDate = ticket.nextDate });
  }
  return out;
}