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

/* Note de gare supposee en regime etabli, en pourcent.
 * CALIBRE le 2026-08-28 sur 9 lignes pax reelles (2 campagnes de 10 ans, graine 42, OpenTTD
 * 15.3) : AIStation.GetCargoRating() mesure en regime etabli donne 49-55 par ligne (moyenne
 * 52,8), tres loin des 75 supposes ici avant. Voir docs/opex_predict_vs_actual.json et le rapport
 * de la tache "predit vs reel" pour le detail ligne par ligne. */
const STATION_RATING_PCT = 50;

/* Intervalle cible entre deux ramassages, en jours. Vient du bareme : la tranche la mieux notee
 * est "moins de 15 s" de temps reel, soit ~6,8 jours de jeu a 74 ticks/jour. */
const TARGET_HEADWAY_DAYS = 7;

const MAX_TRAINS = 8;

/* Duree d'amortissement de l'infrastructure, en annees. Convention deja utilisee par les
 * campagnes (profit_ligne), gardee pour rester comparable. */
const INFRA_LIFE_YEARS = 30;

function OpexCeilDiv(a, b)
{
  if (b <= 0) return 0;
  local quotient = a.tofloat() / b;
  local floor = quotient.tointeger();
  return floor < quotient ? floor + 1 : floor;
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
  if (legDays <= 0) return 0;
  /* 30 / duree, sans plafond : ceil(30 / legDays) etait favorable de 1,20x a 1,63x sur les
   * 155 lignes mesurees (mediane 1,27x). Une fraction est une capacite MENSUELLE moyenne, pas un
   * demi-convoi a construire ; les arrondis ne reviennent qu'au nombre entier de convois. */
  return 30.0 / legDays;
}

/* Le bareme du jeu donne 130 / 95 / 50 / 25 points de ramassage sous 6,8 / 13,5 / 27 / 47 jours
 * (docs/mecanique_jeu.md section 3). STATION_RATING_PCT = 50 a ete calibre sur des lignes dont le
 * headway cible etait 7 jours, donc dans la tranche 95. Les autres facteurs observes a ce regime
 * valent 50 % * 255 - 95 = 32,5 points ; on les conserve et on ne fait varier QUE le facteur que
 * le nombre de convois change reellement. Ce n'est pas une nouvelle constante calibree : c'est la
 * decomposition algebrique du 50 % deja mesure et du bareme documente.
 *
 * Elle rend visible le conflit que l'ancien `max(headway, volume)` cachait : ajouter une locomotive
 * raccourcit le headway et augmente le cargo capte, mais coute son capital et son entretien. */
function OpexPickupRatingPoints(headwayDays)
{
  if (headwayDays < 6.8) return 130;
  if (headwayDays < 13.5) return 95;
  if (headwayDays < 27.0) return 50;
  if (headwayDays < 47.0) return 25;
  return 0;
}

function OpexStationRatingForHeadway(headwayDays)
{
  local otherPoints = STATION_RATING_PCT * 255.0 / 100.0 - 95.0;
  local rating = 100.0 * (otherPoints + OpexPickupRatingPoints(headwayDays)) / 255.0;
  if (rating < 0) return 0;
  if (rating > 100) return 100;
  return rating;
}

/* Economie complete d'une ligne rail. `fixedPlatformLength` vaut 0 au classement : on peut alors
 * choisir la rame jusqu'au maximum du jeu, puis lui donner le quai voulu avec sa marge. Apres la
 * recherche de site, il vaut le quai reellement trouvable : wagons, locomotive, capital et profit
 * sont alors recalcules sur cette longueur, jamais sur le souhait initial. */
function OpexLineEconomics(catalog, cargo, distance, monthlyUnits, kind, fixedPlatformLength = 0)
{
  if (!(cargo in catalog.wagonByCargo)) return null;
  if (!(cargo in catalog.locoByCargoWagons)) return null;
  local wagon = catalog.wagonByCargo[cargo];

  /* Les wagons et la locomotive sont couples. Le maximum de jeu ne sert ici qu'a trouver la rame
   * cible ; son quai voulu est derive plus bas de cette rame et de sa marge. Cela n'autorise PAS a
   * rabougrir chaque rame a un wagon parce que le headway a deja achete 3 a 5 locomotives. On
   * dimensionne d'abord UNE rame pour emporter l'offre au regime calibre de 50 %,
   * puis seulement on arbitre le nombre de rames. Ainsi une ligne de 36 tuiles qui offrait 68
   * unites/mois avec 1,9 trajet charge par mois demande ceil(68/(30*1,9)) = 2 wagons, pas le wagon
   * unique produit par la formule ancienne qui le divisait d'abord par ses 3 trains.
   *
   * La seconde boucle est bornee par MAX_TRAINS = 8, deja plafond de gare du modele. Elle ne boucle
   * jamais sur les moteurs : pour chaque nombre de rames elle compare le revenu de la note issue du
   * bareme au capital et au cout courant. Le gagnant est le profit maximal, et l'egalite garde moins
   * de trains parce qu'ils n'apportent alors aucun point de note ni cargo supplementaire. */
  local choices = catalog.locoByCargoWagons[cargo];
  local maxWagons = choices.len();
  /* Le cache catalogue va jusqu'a station_spread ; une longueur imposee apres recherche doit
   * couper cette table a la meme capacite nominale que OpexBuildTrains. */
  if (fixedPlatformLength > 0) {
    local platformMaxWagons = OpexRailNominalMaxWagons(fixedPlatformLength);
    if (platformMaxWagons < maxWagons) maxWagons = platformMaxWagons;
  }
  if (maxWagons < 1) return null;
  local referenceLoco = choices[maxWagons - 1];
  if (referenceLoco == null) return null;

  local referenceSpeed = OpexRailEffectiveSpeed(referenceLoco, wagon, maxWagons, distance);
  if (referenceSpeed < 1) return null;
  local referenceOneWayDays = distance.tofloat() / (0.036 * referenceSpeed);
  if (referenceOneWayDays < 1) referenceOneWayDays = 1;
  local referenceRoundTripDays = 2 * referenceOneWayDays;
  local referenceTrips = OpexLoadedTripsPerMonth(referenceOneWayDays, referenceRoundTripDays,
                                                  kind == "pax");
  local calibrationOffered = (monthlyUnits * STATION_RATING_PCT) / 100.0;
  if (calibrationOffered <= 0) return null;
  local wagons = OpexCeilDiv(calibrationOffered, wagon.capacity * referenceTrips);
  if (wagons < 1) wagons = 1;
  if (wagons > maxWagons) wagons = maxWagons;

  local loco = choices[wagons - 1];
  if (loco == null) return null;
  local effectiveSpeed = OpexRailEffectiveSpeed(loco, wagon, wagons, distance);
  if (effectiveSpeed < 1) return null;
  local oneWayDays = distance.tofloat() / (0.036 * effectiveSpeed);
  if (oneWayDays < 1) oneWayDays = 1;
  local roundTripDays = 2 * oneWayDays;
  local tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, kind == "pax");

  /* La locomotive de la rame deja remplie peut modifier le cycle ; une correction referme ce
   * couplage sans reintroduire les trains dans le denominateur des wagons. */
  local correctedWagons = OpexCeilDiv(calibrationOffered, wagon.capacity * tripsPerMonth);
  if (correctedWagons < 1) correctedWagons = 1;
  if (correctedWagons > maxWagons) correctedWagons = maxWagons;
  if (correctedWagons != wagons) {
    wagons = correctedWagons;
    loco = choices[wagons - 1];
    if (loco == null) return null;
    effectiveSpeed = OpexRailEffectiveSpeed(loco, wagon, wagons, distance);
    if (effectiveSpeed < 1) return null;
    oneWayDays = distance.tofloat() / (0.036 * effectiveSpeed);
    if (oneWayDays < 1) oneWayDays = 1;
    roundTripDays = 2 * oneWayDays;
    tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, kind == "pax");
  }

  local perTrain = wagons * wagon.capacity;
  /* Le modele de cycle conserve les jours fractionnaires, mais l'API de revenu et le moteur
   * comptent des jours calendaires entiers. Arrondir vers le haut evite de crediter un trajet de
   * 4,01 jours du tarif de 4 jours ; c'est un choix discret impose par l'API, pas un rendement. */
  local incomeDays = OpexCeilDiv(oneWayDays, 1);

  /* Au classement, la rame cible choisit son quai : 1 tuile = 2 wagons vanilla de 8/16 et la
   * marge de 2 wagons ajoute donc la plus petite croissance geometrique non nulle. Apres le site,
   * `fixedPlatformLength` ecrase ce souhait. Le capital compte ainsi 2 quais de la longueur qui
   * sera effectivement posee, pas `station.station_spread` lu a 12. */
  local platformLength = fixedPlatformLength > 0
      ? fixedPlatformLength
      : OpexRailWantedPlatformLength(wagons, catalog.platformLength);
  local infraCost = distance * catalog.costTrackPerTile + 2 * platformLength * catalog.costStation;
  local locoLife = loco.ageYears > 0 ? loco.ageYears : 20;
  local best = null;
  for (local trains = 1; trains <= MAX_TRAINS; trains++) {
    local headwayDays = roundTripDays / trains;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = monthlyUnits * stationRating / 100.0;
    local monthlyCapacity = trains * perTrain * tripsPerMonth;
    local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();
    local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(cargo, distance, incomeDays)).tointeger();
    local vehicleCost = trains * (loco.price + wagons * wagon.price);
    local amortAnnual = vehicleCost / locoLife + infraCost / INFRA_LIFE_YEARS;
    local runningAnnual = trains * loco.runningCost;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    if (best == null || profitAnnual > best.profitAnnual) {
      best = { trains = trains, headwayDays = headwayDays, stationRating = stationRating,
               offered = offered, monthlyCapacity = monthlyCapacity, carried = carried,
               revenueAnnual = revenueAnnual, vehicleCost = vehicleCost, amortAnnual = amortAnnual,
               runningAnnual = runningAnnual, profitAnnual = profitAnnual };
    }
  }
  if (best == null) return null;
  local trainsForHeadway = OpexCeilDiv(roundTripDays, TARGET_HEADWAY_DAYS);
  local trainsForVolume = OpexCeilDiv(best.offered, perTrain * tripsPerMonth);

  return {
    oneWayDays = oneWayDays,
    incomeDays = incomeDays,
    trains = best.trains,
    wagons = wagons,
    perTrain = perTrain,
    platformLength = platformLength,
    loco = loco,
    effectiveSpeed = effectiveSpeed,
    tripsPerMonth = tripsPerMonth,
    headwayDays = best.headwayDays,
    stationRating = best.stationRating,
    offered = best.offered,
    monthlyCapacity = best.monthlyCapacity,
    trainsForHeadway = trainsForHeadway,
    trainsForVolume = trainsForVolume,
    carried = best.carried,
    revenueAnnual = best.revenueAnnual,
    runningAnnual = best.runningAnnual,
    amortAnnual = best.amortAnnual,
    capital = best.vehicleCost + infraCost,
    profitAnnual = best.profitAnnual,
  };
}

/* Le candidat est cree avec l'economie du quai voulu, puis devient le contrat du quai trouve.
 * Cette copie explicite empeche le cas dangereux "quai court, wagons longs, capital long" : tous
 * les champs qui alimentent construction, panneaux, classement local et suivi de ligne changent
 * ensemble apres la seconde evaluation. */
function OpexApplyRailEconomics(candidate, economics)
{
  candidate.oneWayDays = economics.oneWayDays;
  candidate.trains = economics.trains;
  candidate.wagons = economics.wagons;
  candidate.perTrain = economics.perTrain;
  candidate.platformLength = economics.platformLength;
  candidate.loco = economics.loco;
  candidate.effectiveSpeed = economics.effectiveSpeed;
  candidate.tripsPerMonth = economics.tripsPerMonth;
  candidate.headwayDays = economics.headwayDays;
  candidate.stationRating = economics.stationRating;
  candidate.offered = economics.offered;
  candidate.monthlyCapacity = economics.monthlyCapacity;
  candidate.trainsForHeadway = economics.trainsForHeadway;
  candidate.trainsForVolume = economics.trainsForVolume;
  candidate.carried = economics.carried;
  candidate.revenueAnnual = economics.revenueAnnual;
  candidate.runningAnnual = economics.runningAnnual;
  candidate.amortAnnual = economics.amortAnnual;
  candidate.capital = economics.capital;
  candidate.profitAnnual = economics.profitAnnual;
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
 *     (reglage road_multistop, defaut 0) : un arret extra joint par bout, clones seulement
 *     si les deux bouts ont double. Le classement ici reste borne a 2.
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
  /* OpexLoadedTripsPerMonth est aussi partage par la route. Sa capacite moyenne peut etre
   * fractionnaire depuis la suppression du ceil favorable ; les cargaisons et les panneaux restent
   * entiers, donc on ne credite jamais 28,57 unites qui n'existent pas dans le moteur. */
  carried = carried.tointeger();

  local incomeDays = OpexCeilDiv(oneWayDays, 1);
  local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(cargo, distance, incomeDays)).tointeger();

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
