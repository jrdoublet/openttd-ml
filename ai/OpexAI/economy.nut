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

/* 🔴 TRAJETS CHARGES PAR MOIS -- corrige le 2026-08-29 (docs/mecanique_jeu.md S1 ter).
 *
 * La grandeur utile n'est pas "aller-retours par mois" mais "trajets CHARGES par mois", et les deux
 * ne coincident que pour le fret :
 *
 *   - une ligne PASSAGERS ville <-> ville est BIDIRECTIONNELLE. Chaque ville produit pour l'autre,
 *     donc le vehicule est charge a l'aller ET au retour : DEUX trajets payants par aller-retour ;
 *   - une ligne de FRET est a SENS UNIQUE par construction -- OpexFreightCandidates n'apparie qu'un
 *     producteur a un accepteur du MEME cargo, et l'accepteur ne produit pas ce cargo. Le retour se
 *     fait a vide : UN seul trajet payant par aller-retour. C'est la meme asymetrie qui impose
 *     OF_NONE au puits (un convoi qui attend un chargement de retour inexistant reste bloque pour
 *     toujours, mesure du 2026-08-28).
 *
 * LE DEFAUT CORRIGE : le modele comptait deja la demande des DEUX villes pour le passager
 * (monthly = production_A + production_B) mais ne lui accordait qu'un seul trajet charge par
 * aller-retour, comme au fret. Les deux cotes de l'equation etaient incoherents. Effet, et il faut
 * savoir lequel mord quand : la flotte demandee etait TOUJOURS doublee sur une ligne passagers
 * (donc cout de fonctionnement et capital surestimes, profit sous-estime, bons candidats ecartes) ;
 * le tonnage, lui, n'etait sous-estime que sur les lignes limitees par la CAPACITE et non par la
 * demande.
 *
 * Le fret est inchange au bit pres : legDays y vaut roundTripDays, exactement l'ancien calcul. */
function OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, bidirectional)
{
  local legDays = bidirectional ? oneWayDays : roundTripDays;
  local trips = OpexCeilDiv(30, legDays);
  return trips < 1 ? 1 : trips;
}

/* Economie complete d'une ligne rail. `kind` vaut "pax" (bidirectionnel) ou "freight" (sens
 * unique) -- cf. OpexLoadedTripsPerMonth. Rend null si le materiel manque. */
function OpexLineEconomics(catalog, cargo, distance, monthlyUnits, kind)
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
  /* Trajets CHARGES, pas aller-retours : deux par cycle pour le pax, un pour le fret. La contrainte
   * de FREQUENCE ci-dessus reste sur l'aller-retour -- une gare n'est visitee qu'une fois par
   * cycle, quel que soit le nombre de sens charges. */
  local tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, kind == "pax");
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

/* --- Economie d'une ligne ROUTIERE (2026-08-29) --------------------------------------------
 *
 * Le modele rail ci-dessus n'est PAS transposable tel quel, pour trois raisons mesurees ou
 * documentees, et chacune donne une constante propre :
 *
 *  1. Le plafond de quai. docs/mecanique_jeu.md S11 : "un arret de bus n'accueille au plus que
 *     DEUX bus a la fois", idem pour une aire de chargement camion. Au-dela les vehicules font la
 *     queue SUR LA ROUTE et se bloquent. Le modele rail ne connait que MAX_TRAINS = 8 et
 *     prescrirait donc une flotte auto-congestionnee. MAX_ROAD_VEHICLES = 2 est la traduction
 *     directe de la regle du jeu, pas une precaution. Le levier de volume est le multistop
 *     (AIStation.STATION_JOIN_ADJACENT), pas le vehicule supplementaire -- non implemente ici.
 *  2. Le rendement de vitesse. Un vehicule routier traverse des villes, s'arrete a chaque
 *     extremite et suit un trace en L (deux angles droits par sens) sur des distances ou
 *     l'acceleration compte proportionnellement bien plus que sur une ligne rail de 50 tuiles.
 *     60 % est une HYPOTHESE, plus severe que les 70 % du rail, a recalibrer sur la premiere
 *     campagne qui produira des lignes routieres reelles (le releve annuel OY/OZ/OU/OO les couvre
 *     deja, cf. _reportLines).
 *  3. La duree de trajet reelle suit le TRACE, pas la distance a vol d'oiseau. Ici les deux
 *     coincident : le trace est un L de Manhattan, dont la longueur EST la distance Manhattan
 *     entre les deux facades. C'est la seule raison pour laquelle on peut reutiliser la meme
 *     formule jours = distance / (0,036 * vitesse) sans facteur de detour.
 */
const ROAD_SPEED_EFFICIENCY_PCT = 60;
const MAX_ROAD_VEHICLES = 2;

/* Economie complete d'une ligne routiere. Rend null si le materiel manque pour ce cargo.
 * `engine` vient de catalog.roadEngineByCargo[cargo] ; sa capacite est celle du cargo d'origine
 * (approximation assumee au classement, cf. catalog.nut) -- le constructeur relit la vraie
 * capacite apres refit depuis le depot. */
function OpexRoadLineEconomics(catalog, cargo, distance, monthlyUnits, engine, kind)
{
  if (engine == null) return null;
  local effectiveSpeed = (engine.speed * ROAD_SPEED_EFFICIENCY_PCT) / 100;
  if (effectiveSpeed < 1) return null;

  local oneWayDays = (distance * 1000) / (36 * effectiveSpeed);
  if (oneWayDays < 1) oneWayDays = 1;
  local roundTripDays = 2 * oneWayDays;

  local offered = (monthlyUnits * STATION_RATING_PCT) / 100;
  if (offered <= 0) return null;

  /* Meme arbitrage que le rail : le maximum de ce qu'exige la FREQUENCE et de ce qu'exige la
   * CAPACITE -- puis le plafond de quai tranche, et il est bas. Sur une ligne courte la contrainte
   * de frequence rend presque toujours 1 : c'est voulu, un seul vehicule qui repasse souvent tient
   * la note de gare mieux que deux qui se genent au meme arret. */
  local vehiclesForHeadway = OpexCeilDiv(roundTripDays, TARGET_HEADWAY_DAYS);
  /* Meme lecture qu'au rail : un bus ville <-> ville est charge dans les deux sens, un camion
   * revient a vide -- cf. OpexLoadedTripsPerMonth. */
  local tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, kind == "pax");
  local vehiclesForVolume = OpexCeilDiv(offered, engine.capacity * tripsPerMonth);

  local vehicles = vehiclesForHeadway > vehiclesForVolume ? vehiclesForHeadway : vehiclesForVolume;
  if (vehicles < 1) vehicles = 1;
  if (vehicles > MAX_ROAD_VEHICLES) vehicles = MAX_ROAD_VEHICLES;

  local monthlyCapacity = vehicles * engine.capacity * tripsPerMonth;
  local carried = offered < monthlyCapacity ? offered : monthlyCapacity;

  local revenueAnnual = 12 * carried * AICargo.GetCargoIncome(cargo, distance, oneWayDays);

  /* Capital : le trace lui-meme (le L de Manhattan, donc `distance` tuiles), les deux arrets et le
   * depot. La borne est basse pour la meme raison que sur le rail -- les tuiles de route deja
   * presentes ne sont pas payees, ce qui joue en notre defaveur dans le classement, jamais en
   * notre faveur. */
  local stopCost = AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)
      ? catalog.costRoadBusStop : catalog.costRoadTruckStop;
  local vehicleCost = vehicles * engine.price;
  local infraCost = distance * catalog.costRoadPerTile + 2 * stopCost + catalog.costRoadDepot;

  local life = engine.ageYears > 0 ? engine.ageYears : 12;
  local amortAnnual = vehicleCost / life + infraCost / INFRA_LIFE_YEARS;
  local runningAnnual = vehicles * engine.runningCost;

  return {
    oneWayDays = oneWayDays,
    trains = vehicles,            // meme nom que le rail : _tryBuild/_reportLines sont communs
    carried = carried,
    revenueAnnual = revenueAnnual,
    runningAnnual = runningAnnual,
    amortAnnual = amortAnnual,
    capital = vehicleCost + infraCost,
    profitAnnual = revenueAnnual - runningAnnual - amortAnnual,
  };
}
