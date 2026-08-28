/* Le modele economique d'une ligne : du REVENU au PROFIT.
 *
 * L'etage 1 estimait le revenu brut et supposait implicitement que toute la production etait
 * captee. Les deux hypotheses sont fausses, et docs/mecanique_jeu.md dit exactement en quoi :
 *
 *  - §3 : "un pourcentage des marchandises disponibles EGAL A LA NOTE DE LA GARE lui est
 *    distribue toutes les 2,5 journees". Le cargo capte est donc production x note, pas
 *    production.
 *  - §3 : le plus gros facteur de cette note (51 %) est le DELAI DEPUIS LE DERNIER RAMASSAGE.
 *    La frequence bat la capacite -- d'ou le nombre de convois calcule ci-dessous a partir d'un
 *    intervalle cible, et non d'une constante arbitraire.
 *  - §2 : 100 km/h ~ 3,6 tuiles par jour. L'ancien TILES_PER_DAY = 2 etait faux d'un facteur ~3,
 *    ce qui surestimait le temps de trajet, donc les penalites de retard, donc sous-estimait le
 *    revenu D'AUTANT PLUS QUE LA LIGNE EST LONGUE.
 *  - §1 : les penalites de retard sont deja dans AICargo.GetCargoIncome ; on ne les reimplemente
 *    pas, on lui passe un nombre de jours honnete.
 */

/* Rendement de vitesse : vitesse effective / vitesse catalogue. HYPOTHESE a calibrer.
 * Justification : le bridage en courbe est severe (61 km/h sur un virage a 90 degres, contre
 * 111 a courbure 2 -- docs/mecanique_jeu.md §2), auxquels s'ajoutent acceleration et arrets. */
const SPEED_EFFICIENCY_PCT = 70;

/* Note de gare supposee en regime etabli, en pourcent.
 * CALIBRE le 2026-08-28 sur 9 lignes pax reelles (2 campagnes de 10 ans, graine 42, OpenTTD
 * 15.3) : AIStation.GetCargoRating() mesure en regime etabli donne 49-55 par ligne (moyenne
 * 52,8), tres loin des 75 supposes ici avant. Voir docs/opex_predict_vs_actual.json et le rapport
 * de la tache "predit vs reel" pour le detail ligne par ligne. */
const STATION_RATING_PCT = 50;

/* Intervalle cible entre deux ramassages, en jours. Vient du bareme : la tranche la mieux notee
 * est "moins de 15 s" de temps reel, soit ~6,8 jours de jeu a 74 ticks/jour. */
const TARGET_HEADWAY_DAYS = 7;

const WAGONS_PER_TRAIN = 5;
const MAX_TRAINS = 8;

/* Duree d'amortissement de l'infrastructure, en annees. Convention deja utilisee par les
 * campagnes (profit_ligne), gardee pour rester comparable. */
const INFRA_LIFE_YEARS = 30;

function OpexCeilDiv(a, b)
{
  if (b <= 0) return 0;
  return (a + b - 1) / b;
}

/* Economie complete d'une ligne rail. Rend null si le materiel manque. */
function OpexLineEconomics(catalog, cargo, distance, monthlyUnits)
{
  if (catalog.loco == null) return null;
  if (!(cargo in catalog.wagonByCargo)) return null;
  local wagon = catalog.wagonByCargo[cargo];
  local loco = catalog.loco;

  local effectiveSpeed = (loco.speed * SPEED_EFFICIENCY_PCT) / 100;
  if (effectiveSpeed < 1) return null;

  /* 100 km/h ~ 3,6 tuiles/jour  =>  jours = distance / (0,036 * vitesse). */
  local oneWayDays = (distance * 1000) / (36 * effectiveSpeed);
  if (oneWayDays < 1) oneWayDays = 1;
  local roundTripDays = 2 * oneWayDays;

  /* Cargo reellement capte : la note de gare est un multiplicateur, pas un detail. */
  local offered = (monthlyUnits * STATION_RATING_PCT) / 100;
  if (offered <= 0) return null;

  /* Nombre de convois : le maximum de ce qu'exige la FREQUENCE et de ce qu'exige la CAPACITE.
   * La contrainte de frequence est celle qui tient la note de gare en haut du bareme. */
  local trainsForHeadway = OpexCeilDiv(roundTripDays, TARGET_HEADWAY_DAYS);
  local perTrain = WAGONS_PER_TRAIN * wagon.capacity;
  local tripsPerMonth = OpexCeilDiv(30, roundTripDays);
  if (tripsPerMonth < 1) tripsPerMonth = 1;
  local trainsForVolume = OpexCeilDiv(offered, perTrain * tripsPerMonth);

  local trains = trainsForHeadway > trainsForVolume ? trainsForHeadway : trainsForVolume;
  if (trains < 1) trains = 1;
  if (trains > MAX_TRAINS) trains = MAX_TRAINS;

  local monthlyCapacity = trains * perTrain * tripsPerMonth;
  local carried = offered < monthlyCapacity ? offered : monthlyCapacity;

  local revenueAnnual = 12 * carried * AICargo.GetCargoIncome(cargo, distance, oneWayDays);

  /* Capital immobilise. La voie est comptee sur la distance Manhattan : c'est une borne basse,
   * le trace reel est plus long (detour). */
  local vehicleCost = trains * (loco.price + WAGONS_PER_TRAIN * wagon.price);
  local infraCost = distance * catalog.costTrackPerTile + 2 * catalog.costStation;

  local locoLife = loco.ageYears > 0 ? loco.ageYears : 20;
  local amortAnnual = vehicleCost / locoLife + infraCost / INFRA_LIFE_YEARS;
  local runningAnnual = trains * loco.runningCost;

  local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;

  return {
    oneWayDays = oneWayDays,
    trains = trains,
    carried = carried,
    revenueAnnual = revenueAnnual,
    runningAnnual = runningAnnual,
    amortAnnual = amortAnnual,
    capital = vehicleCost + infraCost,
    profitAnnual = profitAnnual,
  };
}
