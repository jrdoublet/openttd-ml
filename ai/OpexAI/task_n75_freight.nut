/* N75-CAP : renfort d'une rame fret seulement apres observations espacees
 * sur au moins 120 jours. Ne remplace pas la transaction physique V284.
 * Les observations et les identifiants sont serialisables (aucun float). */

function OpexN75FreightObserve(owner, line, vehicle, wagons, waiting, requiredWaiting, date)
{
  if (N75_FREIGHT_CAPACITY == 0 || AIDate.GetYear(date) < OPEX_START_YEAR + 2) return false;
  if (owner._n75Freight == null) owner._n75Freight = { samples = {} };
  local samples = owner._n75Freight.samples;
  local id = line.lineId;
  local observation = (id in samples) ? samples[id] : null;
  /* Une rame construite depuis la premiere observation annule la preuve. */
  if (observation == null || observation.vehicle != vehicle || observation.wagons != wagons
      || date < observation.last || date - observation.last > 120) {
    observation = { vehicle = vehicle, wagons = wagons, first = date, last = date, count = 0 };
    samples.rawset(id, observation);
  }
  if (requiredWaiting <= 0 || waiting < requiredWaiting) {
    observation.count = 0;
    observation.first = date;
    observation.last = date;
    return false;
  }
  /* L'intervalle et le minimum de trois mesures evite de confondre
   * une seule arrivee de cargaison avec un goulot durable. */
  if (observation.count == 0) {
    observation.count = 1;
    observation.first = date;
    observation.last = date;
  } else if (date - observation.last >= 60) {
    observation.last = date;
    if (observation.count < 3) observation.count++;
  }
  return observation.count >= 3 && date - observation.first >= 120;
}

/* Borne conservatrice, pas une preuve de demande annuelle : une deuxieme
 * rame identique n'est creditee que de 50 % du revenu recent de la premiere.
 * Le cout complet et l'entretien entier du train neuf sont payes. */
function OpexN75FreightMargin(line, vehicle, wagon, wagons, capacity, equipment)
{
  if (!("lastRevenue" in line) || line.lastRevenue <= 0 || capacity <= 0
      || wagon.capacity <= 0 || equipment == null) return null;
  local replacement = OpexV257Engine(equipment.engine, line.cargo, false);
  local gross = replacement.price + wagons * wagon.price;
  local annualGross = (line.lastRevenue.tofloat() * 0.5).tointeger();
  local extraRunning = replacement.runningCost + wagons * wagon.runningCost;
  local annualMargin = annualGross - extraRunning;
  if (gross <= 0 || annualMargin <= 0 || annualMargin.tofloat() * 3 < gross
      || OpexAvailableCapital() < gross + 50000) return null;
  return { annual = annualMargin, gross = gross };
}
