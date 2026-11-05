/* RAIL-FILL (rail_fill=1, defaut 0) : remplir les quais EXISTANTS des lignes
 * fret quand la caisse dort, au lieu d'ajouter un wagon par mois apres 1 M£.
 *
 * Constat du 04/11 (docs/cloud_capacite-rame_20261104.md) :
 *  - les rames Opex sont dimensionnees sur la demande OBSERVEE, elle-meme
 *    plafonnee par la rame courante (V257, V284 : `carried <= captured`
 *    ou `captured` est le fret deja livre) : une rame courte justifie une
 *    rame courte, et V257 departage les ex aequo par le prix -> raccourcit ;
 *  - un quai de 4 cases porte 7 wagons, la mediane en service est 3 ;
 *  - V284 (defaut) n'agit qu'a partir de 1 M£ de caisse et d'un wagon a la fois.
 *
 * RAIL-FILL reutilise la transaction V284 telle quelle (approche du depot,
 * construction, copie des ordres, adoption) et ne change que trois choses :
 *  1. la porte de caisse : 250 k£ et deux ans au lieu de 1 M£ et trois ans,
 *     la seconde rame (`add`, evitement) restant soumise a l'ancienne porte ;
 *  2. la taille visee : production REELLE de l'industrie x note cible 75 %
 *     sur un cycle et demi, bornee par le quai, au lieu de +1 wagon ;
 *  3. la protection : une rame remplie n'est plus revue par V257.
 * Traction : la meme regle que V284 (aucune perte de vitesse) ; si aucune
 * locomotive ne tient la vitesse, la taille descend jusqu'a +1 wagon. */

RAIL_FILL_MIN_CASH <- 250000;
RAIL_FILL_START_YEARS <- 2;
RAIL_FILL_TARGET_RATING <- 75;   // % : une rame toujours en chargement a la source
RAIL_FILL_CYCLES <- 3;           // numerateur : 3/2 cycle de cargaison par rame
RAIL_FILL_RESERVE <- 50000;      // meme reserve que la revalidation V284 au depot

function OpexRailFillLog(line, fields)
{
  if (DECISION_LOG) OpexDecide("RFILL", "line=" + line.lineId + " " + fields);
}

/* Porte de selection V284 sous RAIL-FILL. true = ne rien choisir ce mois-ci. */
function OpexRailFillGateClosed(year)
{
  return year < OPEX_START_YEAR + RAIL_FILL_START_YEARS
      || OpexAvailableCapital() < RAIL_FILL_MIN_CASH;
}

/* La seconde rame avec evitement reste au regime historique (1 M£). */
function OpexRailFillAddAllowed()
{
  return OpexAvailableCapital() >= 1000000;
}

/* Production mensuelle de l'industrie source, non censuree par la rame. */
function OpexRailFillProduction(line)
{
  local industry = -1;
  if ("srcIndustry" in line) industry = line.srcIndustry;
  else if ("originA" in line) industry = AIIndustry.GetIndustryID(line.originA);
  if (!AIIndustry.IsValidIndustry(industry)) return -1;
  return AIIndustry.GetLastMonthProduction(industry, line.cargo);
}

/* Wagons vises : fret capte a la note cible pendant 1,5 cycle aller-retour,
 * pour qu'une rame reste en chargement pendant que la precedente roule
 * (note de prise en charge) sans attendre indefiniment un plein. */
function OpexRailFillTarget(line, wagon, number, maxWagons, speed)
{
  local production = OpexRailFillProduction(line);
  if (production <= 0 || wagon.capacity <= 0 || speed <= 0) return number + 1;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local cycleDays = 2.0 * distance.tofloat() / (0.036 * speed);
  if (cycleDays < 1) cycleDays = 1;
  local monthly = production.tofloat() * RAIL_FILL_TARGET_RATING / 100.0;
  local units = monthly * cycleDays * RAIL_FILL_CYCLES / (2.0 * 30.0);
  local target = OpexCeilDiv(units, wagon.capacity);
  if (target < number + 1) target = number + 1;
  if (target > maxWagons) target = maxWagons;
  return target;
}

/* Plus grande taille <= cible qu'une locomotive tient sans perte de vitesse
 * et que la caisse paie avec la reserve V284. null = garder le +1 historique. */
function OpexRailFillPlan(line, vehicle, wagon, number, maxWagons)
{
  local current = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  if (current == null) return null;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local speed = OpexRailEffectiveSpeed(current, wagon, number, distance);
  local target = OpexRailFillTarget(line, wagon, number, maxWagons, speed);
  for (local n = target; n > number + 1; n--) {
    local equipment = OpexV284Equipment(line, vehicle, wagon, n);
    if (equipment == null) continue;
    local loco = OpexV257Engine(equipment.engine, line.cargo, false);
    if (loco == null) continue;
    local price = loco.price + n * wagon.price;
    if (OpexAvailableCapital() < price + RAIL_FILL_RESERVE) continue;
    OpexRailFillLog(line, "action=plan old_wagons=" + number + " target=" + target
        + " chosen=" + n + " max=" + maxWagons
        + " production=" + OpexRailFillProduction(line)
        + " speed=" + speed.tointeger() + " new_speed=" + equipment.speed.tointeger()
        + " price=" + price);
    return { number = n, equipment = equipment };
  }
  OpexRailFillLog(line, "action=fallback_plus_one old_wagons=" + number
      + " target=" + target + " max=" + maxWagons);
  return null;
}
