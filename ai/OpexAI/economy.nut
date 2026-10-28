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
 * 52,8), tres loin des 75 supposes ici avant. Voir results/opex_predict_vs_actual.json et le rapport
 * de la tache "predit vs reel" pour le detail ligne par ligne. */
const STATION_RATING_PCT = 50;

/* Valeur initiale identique au reglage actif (ancien reglage rail_terrain_factor=100, retire en V236).
 * L'ancien initialiseur 170 etait aussitot ecrase par OpexLoadSettings et
 * sa reactivation isolee a echoue a la porte A du 07/10. */
RAIL_TERRAIN_FACTOR <- 100;

/* Coût d'opportunité du capital immobilisé en transit, en pour mille (docs/taches.md §3 quater & C9).
 * 0 = inerte, 1000 = coût complet inspiré de lostOpportunity dans AAAHogEx. */
TRANSIT_COST_PERMILLE <- 0;

/* Intervalle cible entre deux ramassages, en jours. Vient du bareme : la tranche la mieux notee
 * est "moins de 15 s" de temps reel, soit ~6,8 jours de jeu a 74 ticks/jour. */
const TARGET_HEADWAY_DAYS = 7;

/* Le constructeur realise une voie simple avec un train, ou deux voies dediees avec deux
 * trains. Le classement ne doit donc pas attribuer du revenu a une flotte qu'il ne construit
 * pas. Les plafonds routiers ont leur propre constante plus bas. */
const MAX_RAIL_TRAINS = 2;

/* ESTIM-1 lot 4 : primitives physiques communes a tous les modes. Le mois
 * de planification est une moyenne calendaire; l'ancien 30/30.4 reste sous OFF. */
function OpexEstimDaysPerMonth()
{
  return 365.0 / 12.0;
}

function OpexEstimMonthDays(legacyDays)
{
  return (ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : legacyDays;
}

function OpexEstimRivalAvailableMonthly(monthly, transportedPercent)
{
  if (monthly <= 0) return monthly;
  if (transportedPercent < 0) return monthly;
  if (transportedPercent > 100) transportedPercent = 100;
  return (monthly.tofloat() * (100 - transportedPercent) / 100.0).tointeger();
}

/* Le chantier ferroviaire realise au plus deux voies dediees. Cette limite
 * provient du constructeur, et non d'une taille de flotte arbitraire. */
function OpexEstimRailPhysicalTrainCap()
{
  return 2;
}

/* Duree d'amortissement de l'infrastructure, en annees. Convention deja utilisee par les
 * campagnes (profit_ligne), gardee pour rester comparable. */
const INFRA_LIFE_YEARS = 30;
/* D3.2 : Taux d'amortissement de l'infrastructure (100 = defaut historique, 0 = reel OpenTTD, adopte). */
INFRA_AMORT_PCT <- 0;

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
/* V216f : sejour mecanique en gare (EST-16 : 40 ticks par tranche de 5 unites par wagon, wagons
 * en parallele, 74 ticks par jour). Chaque trajet charge finit par un dechargement et repart apres
 * un chargement : deux operations par trajet voyageurs (a chaque extremite) comme par aller-retour
 * fret (dechargement au puits, chargement mecanique a la source ; l'attente de cargaison du plein
 * chargement reste comptee a part dans loadDays). 0 = inerte. */
function OpexRailStationDwellDays(wagon)
{
  if (V216F_DWELL_PCT <= 0 || wagon == null || wagon.capacity <= 0) return 0.0;
  return 2.0 * 40.0 * ((wagon.capacity + 4) / 5) / 74.0 * V216F_DWELL_PCT / 100.0;
}

function OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, bidirectional)
{
  local legDays = bidirectional ? oneWayDays : roundTripDays;
  if (legDays <= 0) return 0;
  /* 30 / duree, sans plafond : ceil(30 / legDays) etait favorable de 1,20x a 1,63x sur les
   * 155 lignes mesurees (mediane 1,27x). Une fraction est une capacite MENSUELLE moyenne, pas un
   * demi-convoi a construire ; les arrondis ne reviennent qu'au nombre entier de convois. */
  return ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0) / legDays;
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
/* economy_fix : les seuils ci-dessus (6,8 / 13,5 / 27 / 47) ne correspondent PAS au source du
 * moteur. docs/mecanique_jeu.md S8.4 enregistre la lecture de la 15.3 : `time_since_pickup` est
 * compare a 3 / 6 / 12 / 21 CYCLES, et un cycle vaut STATION_RATING_TICKS / DAY_TICKS = 185 / 74,
 * soit ~2,5 jours. Les vrais seuils sont donc 7,5 / 15 / 30 / 52,5 jours : chaque palier etait
 * ~10 % trop strict. Le plus couteux est le premier -- TARGET_HEADWAY_DAYS vaut 7, qui tombe entre
 * 6,8 et 7,5 : le modele notait sa PROPRE cible de conception a 95 points quand le moteur en
 * accorde 130 (docs/taches.md S0 octies, trouvaille 3). */
function OpexPickupRatingPoints(headwayDays)
{
  {
    if (headwayDays < 7.5) return 130;
    if (headwayDays < 15.0) return 95;
    if (headwayDays < 30.0) return 50;
    if (headwayDays < 52.5) return 25;
    return 0;
  }

}

function OpexStationRatingForHeadway(headwayDays)
{
  /* 🔴 L'ANCRE RESTE A 95, MEME SOUS economy_fix -- et c'est un choix, pas un oubli.
   *
   * La re-derivation « logique » serait OpexPickupRatingPoints(TARGET_HEADWAY_DAYS), pour que le
   * modele reproduise STATION_RATING_PCT au headway de calibration quels que soient les seuils.
   * Elle a ete implantee, essayee, et RETIREE le 2026-09-02 :
   *
   * 1. Elle repose sur une hypothese que la revue avait explicitement signalee comme non verifiee
   *    (docs/taches.md S0 octies) : la decomposition utilise le headway CIBLE des lignes de
   *    calibration, jamais leur roundTripDays / trains reellement mesure. Si leur headway reel
   *    depassait 7,5 jours, elles n'etaient pas dans la tranche 130 et l'ancre 95 est la bonne.
   * 2. Elle donnerait otherPoints = -2,5, c'est-a-dire que TOUS les autres facteurs de note du
   *    moteur (vitesse, age du materiel, cargo en attente, statue) contribueraient ensemble ~0.
   *    C'est invraisemblable au vu du source.
   * 3. Smoke test 3 graines x 1 an avec la re-derivation : les trois graines s'effondrent et la 42
   *    sort a -185 £ de profit. A n=3 ce n'est pas une preuve statistique, mais un profit negatif
   *    est un changement qualitatif, pas du bruit de trajectoire.
   *
   * Les seuils corriges, eux, sont conserves : ils viennent du source et ne deplacent la courbe
   * qu'au voisinage des bandes-frontieres. Trancher l'ancre demande de MESURER le headway reel des
   * lignes de calibration -- tache ouverte, pas un reglage a deviner. */
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
/* G5§1 : routeDistance (optionnel) : longueur reelle du trace A*, pour recalibrage post-recherche.
 * Quand fourni et > 0, il remplace distance pour le temps de trajet, la vitesse et le
 * cout de voie. `distance` (Manhattan entre extremites) reste la distance TARIFAIRE, exactement
 * comme OpexRoadLineEconomics distingue deja les deux. */
function OpexLineEconomics(catalog, cargo, distance, monthlyUnits, kind, fixedPlatformLength = 0,
                           routeDistance = null, profile = null, cruiseCache = null,
                           wagonOverride = null, locoChoicesOverride = null, secondary = null, longGood = false)
{
  local longModel = V233_LONG_GOOD > 0 && longGood;
  local setupMark = profile != null ? OpexOpsMeasureBegin() : null;
  local freightDetail = profile != null && kind == "freight" && C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE;
  local freightSetupDetail = profile != null && kind == "freight" && C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE;
  local freightConsistDetail = profile != null && kind == "freight" && C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE;
  local freightCruiseProfile = profile != null && kind == "freight" && C41_RAIL_FREIGHT_CRUISE_PROFILE;
  local freightSpeedDetailProfile = profile != null && kind == "freight" && C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE;
  local freightAccelerationCache = kind == "freight";
  local freightEffectiveSpeedProfile = profile != null && kind == "freight" && C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE;
  local travelDist = (routeDistance != null && routeDistance > 0) ? routeDistance : distance;
  if (wagonOverride == null && !(cargo in catalog.wagonByCargo)) return null;
  if (locoChoicesOverride == null && !(cargo in catalog.locoByCargoWagons)) return null;
  local wagon = wagonOverride != null ? wagonOverride : catalog.wagonByCargo[cargo];

  /* Les wagons et la locomotive sont couples. Le maximum de jeu ne sert ici qu'a trouver la rame
   * cible ; son quai voulu est derive plus bas de cette rame et de sa marge. Cela n'autorise PAS a
   * rabougrir chaque rame a un wagon parce que le headway a deja achete 3 a 5 locomotives. On
   * dimensionne d'abord UNE rame pour emporter l'offre au regime calibre de 50 %,
   * puis seulement on arbitre le nombre de rames. Ainsi une ligne de 36 tuiles qui offrait 68
   * unites/mois avec 1,9 trajet charge par mois demande ceil(68/(30*1,9)) = 2 wagons, pas le wagon
   * unique produit par la formule ancienne qui le divisait d'abord par ses 3 trains.
   *
   * La seconde boucle est bornee par MAX_RAIL_TRAINS = 2, le maximum realisable par le
   * constructeur (une rame par voie dediee). Elle ne boucle
   * jamais sur les moteurs : pour chaque nombre de rames elle compare le revenu de la note issue du
   * bareme au capital et au cout courant. Le gagnant est le profit maximal, et l'egalite garde moins
   * de trains parce qu'ils n'apportent alors aucun point de note ni cargo supplementaire. */
  local referenceMark = freightSetupDetail ? OpexOpsMeasureBegin() : null;
  local choices = locoChoicesOverride != null ? locoChoicesOverride : catalog.locoByCargoWagons[cargo];
  local maxWagons = choices.len();
  /* Le cache catalogue va jusqu'a station_spread ; une longueur imposee apres recherche doit
   * couper cette table a la meme capacite nominale que OpexBuildTrains. */
  if (fixedPlatformLength > 0) {
    local platformMaxWagons = OpexRailNominalMaxWagons(fixedPlatformLength);
    if (platformMaxWagons < maxWagons) maxWagons = platformMaxWagons;
  }
  /* V207 : une rame passagers (+ courrier) plus longue que vehicle.max_train_length ne quitte
   * jamais le depot (MoveWagon : ERR_VEHICLE_TOO_LONG, voir V206). Borne limitee aux rames pax
   * V207 : le quai, le fret et les defauts restent inchanges. */
  if ((longModel || (kind == "pax" && OpexV207Active()) || (kind != "pax" && (V301_NOTRAIN_FIX & 2)))
      && catalog.maxTrainLength > 0) {
    local trainMaxWagons = OpexRailNominalMaxWagons(catalog.maxTrainLength);
    if (trainMaxWagons < maxWagons) maxWagons = trainMaxWagons;
  }
  if (maxWagons < 1) return null;
  local referenceLoco = choices[maxWagons - 1];
  if (referenceLoco == null) return null;

  local speedMark = profile != null ? OpexOpsMeasureBegin() : null;
  local referenceSpeed = OpexRailEffectiveSpeed(referenceLoco, wagon, maxWagons, travelDist, profile, cruiseCache, freightCruiseProfile, freightSpeedDetailProfile, freightAccelerationCache, freightEffectiveSpeedProfile);
  if (profile != null) {
    profile.paxSpeedOps += OpexOpsMeasureEnd(speedMark);
    profile.paxSpeedCalls++;
  }
  if (referenceSpeed < 1) return null;
  local referenceOneWayDays = travelDist.tofloat() / (0.036 * referenceSpeed);
  if (referenceOneWayDays < 1) referenceOneWayDays = 1;
  local referenceRoundTripDays = 2 * referenceOneWayDays;
  local referenceTrips = OpexLoadedTripsPerMonth(referenceOneWayDays, referenceRoundTripDays,
                                                  kind == "pax");
  if (freightSetupDetail) {
    profile.freightEconomicsReferenceOps += OpexOpsMeasureEnd(referenceMark);
    profile.freightEconomicsReferenceCalls++;
  }
  local consistMark = freightSetupDetail ? OpexOpsMeasureBegin() : null;
  local calibrationRating = STATION_RATING_PCT;
  if ((ESTIM_UNIFIE & 8) != 0)
    calibrationRating = OpexStationRatingForHeadway(referenceRoundTripDays / OpexEstimRailPhysicalTrainCap());
  local calibrationOffered = (monthlyUnits * calibrationRating) / 100.0;
  if (longModel) calibrationOffered /= 2.0; // deux rames partageant le debit observe.
  if (calibrationOffered <= 0) return null;
  local wagons = OpexCeilDiv(calibrationOffered, wagon.capacity * referenceTrips);
  if (wagons < 1) wagons = 1;
  if (wagons > maxWagons) wagons = maxWagons;

  local loco = choices[wagons - 1];
  if (loco == null) return null;
  speedMark = profile != null ? OpexOpsMeasureBegin() : null;
  local effectiveSpeed = OpexRailEffectiveSpeed(loco, wagon, wagons, travelDist, profile, cruiseCache, freightCruiseProfile, freightSpeedDetailProfile, freightAccelerationCache, freightEffectiveSpeedProfile);
  if (profile != null) {
    local speedOps = OpexOpsMeasureEnd(speedMark);
    profile.paxSpeedOps += speedOps;
    profile.paxSpeedCalls++;
    if (freightConsistDetail) { profile.freightEconomicsConsistInitialSpeedOps += speedOps; profile.freightEconomicsConsistInitialSpeedCalls++; }
  }
  if (effectiveSpeed < 1) return null;
  local oneWayDays = travelDist.tofloat() / (0.036 * effectiveSpeed);
  if (oneWayDays < 1) oneWayDays = 1;
  local roundTripDays = 2 * oneWayDays;
  local dwellDays = OpexRailStationDwellDays(wagon);
  local tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays + dwellDays, roundTripDays + dwellDays, kind == "pax");

  /* La locomotive de la rame deja remplie peut modifier le cycle ; une correction referme ce
   * couplage sans reintroduire les trains dans le denominateur des wagons. */
  local correctedWagons = OpexCeilDiv(calibrationOffered, wagon.capacity * tripsPerMonth);
  if (correctedWagons < 1) correctedWagons = 1;
  if (correctedWagons > maxWagons) correctedWagons = maxWagons;
  if (correctedWagons != wagons) {
    wagons = correctedWagons;
    loco = choices[wagons - 1];
    if (loco == null) return null;
    speedMark = profile != null ? OpexOpsMeasureBegin() : null;
    effectiveSpeed = OpexRailEffectiveSpeed(loco, wagon, wagons, travelDist, profile, cruiseCache, freightCruiseProfile, freightSpeedDetailProfile, freightAccelerationCache, freightEffectiveSpeedProfile);
    if (profile != null) {
      local speedOps = OpexOpsMeasureEnd(speedMark);
      profile.paxSpeedOps += speedOps;
      profile.paxSpeedCalls++;
      profile.paxCorrectedSpeedCalls++;
      if (freightConsistDetail) { profile.freightEconomicsConsistCorrectedSpeedOps += speedOps; profile.freightEconomicsConsistCorrectedSpeedCalls++; }
    }
    if (effectiveSpeed < 1) return null;
    oneWayDays = travelDist.tofloat() / (0.036 * effectiveSpeed);
    if (oneWayDays < 1) oneWayDays = 1;
    roundTripDays = 2 * oneWayDays;
    tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays + dwellDays, roundTripDays + dwellDays, kind == "pax");
  }
  if (freightSetupDetail) {
    profile.freightEconomicsConsistOps += OpexOpsMeasureEnd(consistMark);
    profile.freightEconomicsConsistCalls++;
  }

  /* V163 : second cargo de la MEME rame (ferme -> usine : GRAI + LVST). Ses wagons sont
   * dimensionnes comme ceux du premier, sur sa propre production au regime calibre, puis
   * ajoutes derriere eux dans la limite du quai ; la locomotive est reprise pour le total
   * (table du premier cargo, poids de son wagon), ce qui garde le meme cycle pour les deux.
   * Sans place ou sans locomotive pour le total, la ligne reste mono-cargo. */
  local wagon2 = null;
  local wagons2 = 0;
  if (secondary != null && secondary.monthly > 0 && (secondary.cargo in catalog.wagonByCargo)) {
    wagon2 = catalog.wagonByCargo[secondary.cargo];
    local secondaryRating = (ESTIM_UNIFIE & 8) != 0 ? calibrationRating : STATION_RATING_PCT;
    wagons2 = OpexCeilDiv((secondary.monthly * secondaryRating) / 100.0, wagon2.capacity * tripsPerMonth);
    if (wagons2 < 1) wagons2 = 1;
    if (wagons + wagons2 > maxWagons) wagons2 = maxWagons - wagons;
    local loco2 = wagons2 > 0 ? choices[wagons + wagons2 - 1] : null;
    if (loco2 == null) {
      wagons2 = 0;
    } else {
      local speed2 = OpexRailEffectiveSpeed(loco2, wagon, wagons + wagons2, travelDist, profile, cruiseCache, freightCruiseProfile, freightSpeedDetailProfile, freightAccelerationCache, freightEffectiveSpeedProfile);
      if (speed2 < 1) {
        wagons2 = 0;
      } else {
        loco = loco2;
        effectiveSpeed = speed2;
        oneWayDays = travelDist.tofloat() / (0.036 * effectiveSpeed);
        if (oneWayDays < 1) oneWayDays = 1;
        roundTripDays = 2 * oneWayDays;
        tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays + dwellDays, roundTripDays + dwellDays, kind == "pax");
      }
    }
    if (wagons2 <= 0) wagon2 = null;
  }

  local capitalMark = freightSetupDetail ? OpexOpsMeasureBegin() : null;
  local perTrain = wagons * wagon.capacity;
  local perTrain2 = wagon2 != null ? wagons2 * wagon2.capacity : 0;
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
      : OpexRailWantedPlatformLength(wagons + wagons2, catalog.platformLength);
  local effectiveTrackCost = (catalog.costTrackPerTile * RAIL_TERRAIN_FACTOR) / 100;
  local infraCost = travelDist * effectiveTrackCost + 2 * platformLength * catalog.costStation
      + (RAIL_DEPOT_COST ? catalog.costRailDepot : 0);
  if (OpexV198Active() && kind == "freight") {
    local signalCost = ("costRailSignal" in catalog) ? catalog.costRailSignal : (catalog.costTrackPerTile / 4);
    local numSignals = (2 * travelDist / 7) + 6;
    infraCost = 2 * travelDist * effectiveTrackCost + 3 * platformLength * catalog.costStation
        + 12 * effectiveTrackCost + numSignals * signalCost
        + (RAIL_DEPOT_COST ? catalog.costRailDepot : 0);
  } else if (longModel || (OpexV190Active() && kind == "freight")) {
    infraCost = 2 * travelDist * effectiveTrackCost + 4 * platformLength * catalog.costStation
        + (RAIL_DEPOT_COST ? 2 * catalog.costRailDepot : 0);
  }
  local locoLife = loco.ageYears > 0 ? loco.ageYears : 20;
  if (freightSetupDetail) {
    profile.freightEconomicsCapitalOps += OpexOpsMeasureEnd(capitalMark);
    profile.freightEconomicsCapitalCalls++;
  }
  if (profile != null) {
    local setupOps = OpexOpsMeasureEnd(setupMark);
    profile.paxEconomicsSetupOps += setupOps;
    if (freightDetail) {
      profile.freightEconomicsSetupOps += setupOps;
      profile.freightEconomicsSetupCalls++;
    }
  }
  local loopMark = profile != null ? OpexOpsMeasureBegin() : null;
  local best = null;
  local startTrains = (longModel || (OpexV190Active() && kind == "freight")) ? 2 : 1;
  local maxTrains = (ESTIM_UNIFIE & 8) != 0 ? OpexEstimRailPhysicalTrainCap() : MAX_RAIL_TRAINS;
  for (local trains = startTrains; trains <= maxTrains; trains++) {
    local headwayDays = roundTripDays / trains;
    local effectiveHeadway = headwayDays;
    if (kind == "freight") {
      /* D4/D5 (docs/taches.md S0 septentrigesies / S0 quadragesies) :
       * Un convoi de fret charge a 100 % (OF_FULL_LOAD_ANY, builder_rail.nut:1188).
       * Tant que le train charge a quai, time_since_pickup = 0 (130 points de ramassage).
       * La gare n'est vide que pendant le trajet aller-retour moins le temps passe en chargement. */
      local loadDays = monthlyUnits > 0 ? (perTrain * ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0)) / monthlyUnits : 0;
      /* V163 : OF_FULL_LOAD_ANY part des que l'UN des cargos remplit ses wagons. */
      if (wagon2 != null) {
        local loadDays2 = (perTrain2 * ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0)) / secondary.monthly;
        if (loadDays2 < loadDays) loadDays = loadDays2;
      }
      local absentDays = roundTripDays - loadDays;
      if (absentDays < 0) absentDays = 0;
      effectiveHeadway = absentDays / trains;
    }
    local stationRating = OpexStationRatingForHeadway(effectiveHeadway);
    local offered = monthlyUnits * stationRating / 100.0;
    local monthlyCapacity = trains * perTrain * tripsPerMonth;
    local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();
    local paidDays = incomeDays;
    if (longModel && offered > 0) paidDays = OpexCeilDiv(oneWayDays + dwellDays / 2 + perTrain * 15.0 / offered, 1);
    local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(cargo, distance, paidDays)).tointeger();
    local vehicleCost = trains * (loco.price + wagons * wagon.price);
    local carried2 = 0;
    local revenue2 = 0;
    if (wagon2 != null) {
      local offered2 = secondary.monthly * stationRating / 100.0;
      local capacity2 = trains * perTrain2 * tripsPerMonth;
      carried2 = (offered2 < capacity2 ? offered2 : capacity2).tointeger();
      revenue2 = (12 * carried2 * AICargo.GetCargoIncome(secondary.cargo, distance, incomeDays)).tointeger();
      revenueAnnual += revenue2;
      vehicleCost += trains * wagons2 * wagon2.price;
    }
    local amortAnnual = vehicleCost / locoLife + ((infraCost * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
    local runningAnnual = trains * loco.runningCost;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local capital = vehicleCost + infraCost;
    local immobilise = (TRANSIT_COST_PERMILLE > 0)
        ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
    local totalCapital = capital + immobilise;
    local roi = (profitAnnual > 0 && totalCapital > 0) ? (profitAnnual * 1000) / totalCapital : 0;
    /* economy_fix : la selection maximisait le profit ABSOLU, sans jamais consulter `roi` ni
     * `capital` -- or c'est `roi` que le portefeuille classe en aval. Ajouter un convoi augmente
     * presque toujours profitAnnual et BAISSE roi : le modele livrait donc au portefeuille, pour
     * chaque ligne, la variante la plus gourmande en capital de toutes celles qu'il avait
     * evaluees (docs/taches.md S0 octies, trouvaille 2). On choisit desormais la variante sur le
     * MEME objectif que celui qui l'arbitrera ensuite, le profit par livre de capital, en
     * departageant les egalites -- roi est quantifie par sa division entiere -- au profit absolu. */
    local better = false;
    if (best == null) {
      better = true;
    } else {
      better = (roi != best.roi) ? (roi > best.roi) : (profitAnnual > best.profitAnnual);
    }
    if (better) {
      best = { trains = trains, headwayDays = headwayDays, stationRating = stationRating,
               offered = offered, monthlyCapacity = monthlyCapacity, carried = carried,
               revenueAnnual = revenueAnnual, vehicleCost = vehicleCost, amortAnnual = amortAnnual,
               runningAnnual = runningAnnual, profitAnnual = profitAnnual, capital = capital,
               immobilise = immobilise, roi = roi, carried2 = carried2, revenue2 = revenue2 };
    }
  }
  if (profile != null) {
    local loopOps = OpexOpsMeasureEnd(loopMark);
    profile.paxEconomicsLoopOps += loopOps;
    profile.paxEconomicsLoopCalls++;
    if (freightDetail) {
      profile.freightEconomicsLoopOps += loopOps;
      profile.freightEconomicsLoopCalls++;
    }
  }
  if (best == null) return null;
  local postMark = profile != null ? OpexOpsMeasureBegin() : null;
  local trainsForHeadway = OpexCeilDiv(roundTripDays, TARGET_HEADWAY_DAYS);
  local trainsForVolume = OpexCeilDiv(best.offered, perTrain * tripsPerMonth);

  local result = {
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
    capital = best.capital,
    vehicleCost = best.vehicleCost,
    immobilise = best.immobilise,
    roi = best.roi,
    profitAnnual = best.profitAnnual,
  };
  /* V163 : champs presents des qu'un second cargo a ete demande, a 0 s'il n'a pas trouve place,
   * pour qu'une reevaluation sur le quai reel efface un second cargo devenu impossible. */
  if (secondary != null) {
    result.cargo2 <- secondary.cargo;
    result.monthly2 <- secondary.monthly;
    result.wagons2 <- wagons2;
    result.perTrain2 <- perTrain2;
    result.carried2 <- best.carried2;
    result.revenue2 <- best.revenue2;
  }

  /* V275 bit 2 : recalage pax V212 (revenu 150 %, capital 85 %), qualifie en rail seul,
   * applique APRES le choix du nombre de trains pour ne deplacer que le classement et le
   * budget, jamais la rame ni la double voie. Le devis remplace ensuite le capital
   * (OpexApplyRailActualCapital) : la garde de tresorerie reste sur le cout reel. */
  if (kind == "pax" && (V275_RAIL_PAX_MM & 2)) {
    /* Le recalage porte sur le revenu ; le profit en decoule comme dans
     * OpexApplyRailActualCapital, pour rester coherent apres le devis. */
    result.revenueAnnual = (result.revenueAnnual * 150) / 100;
    result.profitAnnual = result.revenueAnnual - result.runningAnnual - result.amortAnnual;
    result.capital = (result.capital * 85) / 100;
    local totalCapital = result.capital + result.immobilise;
    result.roi = (result.profitAnnual > 0 && totalCapital > 0)
        ? (result.profitAnnual * 1000) / totalCapital : 0;
  }
  if (profile != null) {
    local postOps = OpexOpsMeasureEnd(postMark);
    profile.paxEconomicsPostOps += postOps;
    if (freightDetail) {
      profile.freightEconomicsPostOps += postOps;
      profile.freightEconomicsPostCalls++;
    }
  }
  return result;
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
  candidate.vehicleCost = economics.vehicleCost;
  candidate.immobilise = economics.immobilise;
  candidate.roi = economics.roi;
  candidate.profitAnnual = economics.profitAnnual;
  if ("wagons2" in economics) {
    if (!("wagons2" in candidate)) {
      candidate.cargo2 <- economics.cargo2; candidate.monthly2 <- economics.monthly2;
      candidate.wagons2 <- 0; candidate.perTrain2 <- 0; candidate.carried2 <- 0; candidate.revenue2 <- 0;
    }
    candidate.wagons2 = economics.wagons2;
    candidate.perTrain2 = economics.perTrain2;
    candidate.carried2 = economics.carried2;
    candidate.revenue2 = economics.revenue2;
  } else if ("wagons2" in candidate) {
    candidate.wagons2 = 0;
  }
}

/* V163 : second cargo memorise sur un candidat rail, a repasser a OpexLineEconomics quand le
 * quai ou le trace reels sont connus. Conserve pour V207 courrier ; null hors pax V207. */
function OpexV163CandidateSecondary(candidate)
{
  if (!(V207_RAIL_MAIL && (("kind" in candidate) && candidate.kind == "pax"))) return null;
  if (!("cargo2" in candidate) || !("monthly2" in candidate)) return null;
  return { cargo = candidate.cargo2, monthly = candidate.monthly2 };
}

/* G3 : le devis AITestMode et le cout finalement debite ne doivent pas seulement proteger la
 * caisse. Ils remplacent aussi le capital d'infrastructure du candidat, donc son amortissement,
 * profit et ROI. La cinematique (distance A* / capacite) a deja ete recalculee par
 * OpexLineEconomics ; seul son cout d'infrastructure est ici reconcilie avec la carte reelle.
 * `actualCapital` est le cout total, vehicules inclus. */
function OpexApplyRailActualCapital(candidate, actualCapital)
{
  if (candidate == null || actualCapital <= 0 || candidate.capital <= 0) return;
  /* Un remboursement de demolition ne peut pas rendre les locomotives gratuites dans le modele. */
  local vehicleFloor = ("vehicleCost" in candidate && candidate.vehicleCost > 0)
      ? candidate.vehicleCost : 0;
  if (actualCapital < vehicleFloor) actualCapital = vehicleFloor;
  local previousCapital = candidate.capital;
  local previousAmort = candidate.amortAnnual;
  local infrastructureDelta = actualCapital - previousCapital;
  candidate.capital = actualCapital;
  /* P1 : les appels ulterieurs au filtre de finançabilité doivent preferer ce
   * devis/ce coût physique au facteur empirique rail. */
  candidate.capitalIsActual <- true;
  candidate.amortAnnual = previousAmort
      + ((infrastructureDelta * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
  candidate.profitAnnual = candidate.revenueAnnual - candidate.runningAnnual - candidate.amortAnnual;
  local immobilise = ("immobilise" in candidate) ? candidate.immobilise : 0;
  local totalCapital = candidate.capital + immobilise;
  candidate.roi = (candidate.profitAnnual > 0 && totalCapital > 0)
      ? (candidate.profitAnnual * 1000) / totalCapital : 0;
}

/* Recalibre l'economie d'un candidat routier apres decouverte des sites d'arret reels et du trace
 * (D4 : docs/taches.md S0 quadragesies / S0 trenonagies).
 *
 * La distance centre-a-centre utilisait le vol d'oiseau entre centres urbains ; les arrets reels
 * sont situes en peripherie ou decales (D_real / D_pred in [0.55, 1.20]), ce qui faussait
 * revenueAnnual (loi de paiement OpenTTD = Manhattan entre arrets) et oneWayDays (duree de parcours
 * le long du trace routier).
 * Cette fonction met a jour les champs du candidat de facon atomique, a l'image d'OpexApplyRailEconomics. */
function OpexApplyRoadEconomics(candidate, economics, actualDistance = null)
{
  if (actualDistance != null) candidate.distance = actualDistance;
  candidate.oneWayDays = economics.oneWayDays;
  /* B3 diagnostic-only : conserver la cible de demande brute et la borne de quai deja calculees.
   * Elles ne pilotent aucune decision ; `candidate.trains` reste la cible historique plafonnee. */
  candidate.vehiclesForVolume = economics.vehiclesForVolume;
  candidate.roadBerthCapacity = economics.roadBerthCapacity;
  candidate.roadVehicleCap = economics.roadVehicleCap;
  candidate.trains = economics.trains;
  candidate.carried = economics.carried;
  candidate.revenueAnnual = economics.revenueAnnual;
  candidate.runningAnnual = economics.runningAnnual;
  candidate.amortAnnual = economics.amortAnnual;
  candidate.capital = economics.capital;
  candidate.roi = economics.roi;
  candidate.profitAnnual = economics.profitAnnual;
  candidate.effectiveSpeed = economics.effectiveSpeed;
}

/* --- Economie d'une ligne ROUTIERE (2026-08-29) --------------------------------------------
 *
 * Le modele rail ci-dessus n'est PAS transposable tel quel, pour trois raisons mesurees ou
 * documentees, et chacune donne une constante propre :
 *
 *  1. Le plafond de quai. docs/mecanique_jeu.md S11 : "un arret de bus n'accueille au plus que
 *     DEUX bus a la fois", idem pour une aire de chargement camion. Au-dela les vehicules font la
 *     queue SUR LA ROUTE et se bloquent. Le modele rail a son propre plafond MAX_RAIL_TRAINS et
 *     prescrirait donc une flotte auto-congestionnee. OpexRoadPhysicalVehicleCap(1, 1) = 2 est la traduction
 *     directe de la regle du jeu, pas une precaution. Le classement ici reste borne a 2.
 *  2. Le rendement de vitesse. Un vehicule routier traverse des villes, s'arrete a chaque
 *     extremite et suit un trace en L (deux angles droits par sens) sur des distances ou
 *     l'acceleration compte proportionnellement bien plus que sur une ligne rail de 50 tuiles.
 *     60 % est une HYPOTHESE, plus severe que les 70 % du rail. Wiki 37 km-ish/h/j =
 *     AM_ORIGINAL ; defaut 15.3 = realiste, plafond 3/4 sur un L d'axes. Panneau RY :
 *     instantane en marche, pax 0,75 (= le 3/4), fret 1,00. Pas un temps de trajet.
 *     Ne pas retuner.
 *  3. La duree de trajet reelle suit le TRACE, pas la distance a vol d'oiseau. Ici les deux
 *     coincident : le trace est un L de Manhattan, dont la longueur EST la distance Manhattan
 *     entre les deux facades. C'est la seule raison pour laquelle on peut reutiliser la meme
 *     formule jours = distance / (0,036 * vitesse) sans facteur de detour.
 */
const ROAD_SPEED_EFFICIENCY_PCT = 60;
/* Seuil global entre deux arrets bus. Cette constante est aussi verifiee au dernier moment par
 * le constructeur : un candidat mis en cache ne peut donc pas contourner la regle. */
const ROAD_BUS_STOP_MIN_DISTANCE = 6;

/* ROAD100-30a : AITile.GetCargoProduction ne retourne PAS des PASS/mois
 * mais des PRODUCERS (maisons/industries) dans le bassin de couverture.
 * Comme B9 AIR, convertir seulement la part de producteurs appartenant
 * a la ville cible en part de sa vraie production mensuelle.
 * Ce resultat est une estimation ex ante : chaque maison n'a pas la meme
 * production, la concurrence et la notation devront toujours etre
 * jugees au profit_year reel apres chantier. Aucun waiting AAA.
 * OFF : la fonction n'est jamais appelee. */
function OpexRoad100PaxSiteMonthly(townId, cargo, siteTile, coverage)
{
  local out = { monthly = 0, siteProducers = 0, townProducers = 0,
      townMonthly = 0, totalSiteProducers = 0, ops = 0 };
  if (!AITown.IsValidTown(townId) || !AIMap.IsValidTile(siteTile)
      || cargo < 0 || coverage < 0) return out;
  local mark = OpexOpsMeasureBegin();
  local population = AITown.GetPopulation(townId);
  local radius = 4 + (sqrt(population > 0 ? population : 0) / 8).tointeger();
  if (radius > 20) radius = 20;
  local center = AITown.GetLocation(townId);
  out.townProducers = AITile.GetCargoProduction(center, cargo, 1, 1, radius);
  out.townMonthly = AITown.GetLastMonthProduction(townId, cargo);
  if (out.townProducers <= 0 || out.townMonthly <= 0) {
    out.ops = OpexOpsMeasureEnd(mark);
    return out;
  }
  local x = AIMap.GetTileX(siteTile);
  local y = AIMap.GetTileY(siteTile);
  local xmin = x - coverage;
  local ymin = y - coverage;
  local xmax = x + coverage;
  local ymax = y + coverage;
  if (xmin < 0) xmin = 0;
  if (ymin < 0) ymin = 0;
  if (xmax >= AIMap.GetMapSizeX()) xmax = AIMap.GetMapSizeX() - 1;
  if (ymax >= AIMap.GetMapSizeY()) ymax = AIMap.GetMapSizeY() - 1;
  local producing = AITileList();
  producing.AddRectangle(AIMap.GetTileIndex(xmin, ymin),
      AIMap.GetTileIndex(xmax, ymax));
  producing.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  producing.KeepAboveValue(0);
  foreach (tile, producers in producing) out.totalSiteProducers += producers;
  local fromTown = AITileList();
  fromTown.AddList(producing);
  fromTown.Valuate(AITile.GetClosestTown);
  fromTown.KeepValue(townId);
  producing.KeepList(fromTown);
  foreach (tile, producers in producing) out.siteProducers += producers;
  local usable = out.siteProducers;
  if (usable > out.townProducers) usable = out.townProducers;
  out.monthly = (out.townMonthly * usable) / out.townProducers;
  out.ops = OpexOpsMeasureEnd(mark);
  return out;
}

function OpexRoadPhysicalVehicleCap(nStopsA, nStopsB)
{
  local nMin = nStopsA < nStopsB ? nStopsA : nStopsB;
  if (nMin < 1) nMin = 1;
  return 2 * nMin;
}

/* Economie complete d'une ligne routiere. Rend null si le materiel manque pour ce cargo.
 * `engine` vient de catalog.roadEngineByCargo[cargo] ; sa capacite est celle du cargo d'origine
 * (approximation assumee au classement, cf. catalog.nut) -- le constructeur relit la vraie
 * capacite apres refit depuis le depot.
 * `routeDistance` (optionnel) : longueur reelle du trace routier decouvert, pour recalibrage post-site (D4). */
function OpexRoadLineEconomics(catalog, cargo, distance, monthlyUnits, engine, kind,
                               routeDistance = null, fleetCapOverride = 0)
{
  if (engine == null) return null;
  local effectiveSpeed = (engine.speed * ROAD_SPEED_EFFICIENCY_PCT) / 100;
  if (effectiveSpeed < 1) return null;

  local travelDist = (routeDistance != null && routeDistance > distance) ? routeDistance : distance;
  local transitDays = (travelDist * 1000) / (36 * effectiveSpeed);
  if (transitDays < 1) transitDays = 1;
  /* D4 (docs/taches.md S0 quadragesies / S0 trenonagies) : Dwell time de chargement/dechargement
   * a la station pour les bus passagers (~6 jours par arret). */
  local dwellDays = (kind == "pax") ? ROAD_PAX_STOP_DWELL_DAYS : 0;
  local oneWayDays = transitDays + dwellDays;
  local roundTripDays = 2 * oneWayDays;

  /* Ce `offered` sert au DIMENSIONNEMENT, comme `calibrationOffered` au rail : la note a plat de
   * calibrage, avant de connaitre la frequence reelle. La demande effective est recalculee plus
   * bas sous pricing_fix, une fois le nombre de vehicules connu. */
  local volumeRating = (ESTIM_UNIFIE & 8) != 0
      ? OpexStationRatingForHeadway(roundTripDays / OpexRoadPhysicalVehicleCap(1, 1))
      : STATION_RATING_PCT;
  local offered = (monthlyUnits * volumeRating) / 100;
  if (offered <= 0) return null;

  /* D4 (docs/taches.md S0 quadragesies / S0 trenonagies) :
   * Le dimensionnement routier se fait sur le VOLUME physiquement offert (vehiclesForVolume),
   * et non sur le TARGET_HEADWAY_DAYS ferroviaire (7 jours) qui forcerait 4 a 6 bus sur un
   * simple arret de village, provoquant surendettement, couts d'exploitation destructeurs
   * et saturation de quai. Le plafond physique du cas de base (1 quai a chaque bout) est 2. */
  local tripsPerMonth = OpexLoadedTripsPerMonth(oneWayDays, roundTripDays, kind == "pax");
  local vehiclesForVolume = OpexCeilDiv(offered, engine.capacity * tripsPerMonth);

  local vehicles = vehiclesForVolume;
  if (vehicles < 1) vehicles = 1;
  local roadBerthCapacity = OpexRoadPhysicalVehicleCap(1, 1);
  local roadVehicleCap = roadBerthCapacity;
  /* ROAD100-4 : mesure ciblée d'un plafond plus élevé. Le risque d'attente
   * devant les quais reste réel, et sera jugé sur le revenu effectivement
   * livré (jamais sur le seul score de cet estimateur). */
  if (fleetCapOverride == 8 && kind == "pax") roadVehicleCap = 8;
  /* ROAD100-31 : sur deux vrais quais joints, garder le contrat
   * historique 8 exact et autoriser seulement 3..7 apres preuve
   * physique par le constructeur, jamais pour un preplan. */
  if (ROAD100_PAX_INITIAL_BERTH_FLEET && kind == "pax"
      && fleetCapOverride >= 3 && fleetCapOverride <= 7)
    roadVehicleCap = fleetCapOverride;
  if (fleetCapOverride == 30 && kind == "pax") roadVehicleCap = 30;

  if (vehicles > roadVehicleCap) vehicles = roadVehicleCap;
  local monthlyCapacity = vehicles * engine.capacity * tripsPerMonth;
  local carried = offered < monthlyCapacity ? offered : monthlyCapacity;
  if (kind == "pax" && vehicles > 0 && roundTripDays > 0) {
    /* Flux par rotation : a chaque visite, seulement ce qui s'est accumule pendant le headway,
     * plafonne a la capacite. Deux bus ne doublent pas la demande, ils se partagent le quai. */
    local headwayDays = roundTripDays.tofloat() / vehicles;
    local waitingOneEnd = (monthlyUnits.tofloat() / 2.0) * headwayDays /
        ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0);
    local pickup = waitingOneEnd < engine.capacity ? waitingOneEnd : engine.capacity.tofloat();
    local visitsOneEnd = vehicles.tofloat() *
        ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0) / roundTripDays;
    local flowCarried = (2.0 * visitsOneEnd * pickup).tointeger();
    if (flowCarried < carried) carried = flowCarried;
  }
  /* OpexLoadedTripsPerMonth est aussi partage par la route. Sa capacite moyenne peut etre
   * fractionnaire depuis la suppression du ceil favorable ; les cargaisons et les panneaux restent
   * entiers, donc on ne credite jamais 28,57 unites qui n'existent pas dans le moteur. */
  carried = carried.tointeger();

  /* Le paiement OpenTTD depend du temps de parcours en transit, pas de la duree au terminus */
  local incomeDays = OpexCeilDiv(transitDays, 1);
  local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(cargo, distance, incomeDays)).tointeger();

  /* Capital : le trace lui-meme (le L de Manhattan, ou routeDistance si le trace est connu), les deux arrets et le
   * depot. La borne est basse pour la meme raison que sur le rail -- les tuiles de route deja
   * presentes ne sont pas payees, ce qui joue en notre defaveur dans le classement, jamais en
   * notre faveur. */
  local stopCost = AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)
      ? catalog.costRoadBusStop : catalog.costRoadTruckStop;
  local vehicleCost = vehicles * engine.price;
  local infraDist = (routeDistance != null && routeDistance > 0) ? routeDistance : distance;
  local infraCost = infraDist * catalog.costRoadPerTile + 2 * stopCost + catalog.costRoadDepot;

  local life = engine.ageYears > 0 ? engine.ageYears : 12;
  local amortAnnual = vehicleCost / life + ((infraCost * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
  local runningAnnual = vehicles * engine.runningCost;
  local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
  local capital = vehicleCost + infraCost;
  local immobilise = (TRANSIT_COST_PERMILLE > 0)
      ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
  local totalCapital = capital + immobilise;
  local roi = (profitAnnual > 0 && totalCapital > 0) ? (profitAnnual * 1000) / totalCapital : 0;

  return {
    oneWayDays = oneWayDays,
    transitDays = transitDays,
    vehiclesForVolume = vehiclesForVolume,
    roadBerthCapacity = roadBerthCapacity,
    roadVehicleCap = roadVehicleCap,
    trains = vehicles,            // meme nom que le rail : _tryBuild/_reportLines sont communs
    carried = carried,
    revenueAnnual = revenueAnnual,
    runningAnnual = runningAnnual,
    amortAnnual = amortAnnual,
    capital = capital,
    immobilise = immobilise,
    profitAnnual = profitAnnual,
    roi = roi,
    effectiveSpeed = effectiveSpeed,
  };
}

/* M3/G12 — canal de mesure uniquement. Les alternatives ci-dessous ne sont jamais renvoyees aux
 * generateurs ni aux constructeurs : elles servent a mesurer le regret du pre-choix catalogue sur
 * une route qui a deja franchi le site/pathfinding. `native` signifie seulement que la capacite
 * catalogue porte deja sur le cargo cible ; une alternative refittable reste un PROXY tant qu'un
 * vehicule n'a pas ete construit/refitte dans un depot. */
function OpexM3EquipmentLog(text)
{
  if (!EQUIPMENT_ROI_PROBE) return;
  AILog.Info("M3_EQUIP date=" + AIDate.GetCurrentDate() + " " + text);
}

function OpexM3ProbeRailEquipment(catalog, candidate, fixedPlatformLength, routeDistance,
                                  selectedEconomics, phase = "post_route")
{
  if (!EQUIPMENT_ROI_PROBE || candidate == null ||
      !(candidate.cargo in catalog.wagonChoicesByCargo)) return;
  local alternatives = catalog.wagonChoicesByCargo[candidate.cargo];
  if (alternatives.len() == 0) return;
  local selectedId = (candidate.cargo in catalog.wagonByCargo)
      ? catalog.wagonByCargo[candidate.cargo].id : -1;
  local bestProfit = null;
  local bestProfitId = -1;
  local bestRoi = null;
  local bestRoiId = -1;
  local viable = 0;
  foreach (wagon in alternatives) {
    if (!("m3LocoChoices" in wagon) || wagon.m3LocoChoices == null) continue;
    local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
        candidate.monthly, candidate.kind, fixedPlatformLength, routeDistance, null, null,
        wagon, wagon.m3LocoChoices);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = wagon.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = wagon.id;
    }
  }
  local selectedProfit = selectedEconomics != null ? selectedEconomics.profitAnnual : -999999999;
  local selectedRoi = selectedEconomics != null ? selectedEconomics.roi : -1;
  OpexM3EquipmentLog("mode=rail phase=" + phase + " cargo=" + candidate.cargo
      + " choices=" + alternatives.len() + " viable=" + viable + " selected=" + selectedId
      + " selected_ok=" + (selectedEconomics != null ? 1 : 0)
      + " selected_profit=" + selectedProfit + " selected_roi=" + selectedRoi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_profit_roi=" + (bestProfit != null ? bestProfit.roi : -1)
      + " best_roi_id=" + bestRoiId
      + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_roi_profit=" + (bestRoi != null ? bestRoi.profitAnnual : -999999999)
      + " admission_flip=" + ((selectedEconomics == null || selectedEconomics.profitAnnual <= 0)
          && bestProfit != null && bestProfit.profitAnnual > 0 ? 1 : 0));
}

function OpexM3ProbeRoadEquipment(catalog, candidate, distance, routeDistance, selectedEconomics, phase)
{
  if (!EQUIPMENT_ROI_PROBE || candidate == null ||
      !(candidate.cargo in catalog.roadEngineChoicesByCargo)) return;
  local alternatives = catalog.roadEngineChoicesByCargo[candidate.cargo];
  if (alternatives.len() == 0) return;
  local selectedId = candidate.engine != null ? candidate.engine.id : -1;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (engine in alternatives) {
    local native = engine.defaultCargo == candidate.cargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexRoadLineEconomics(catalog, candidate.cargo, distance, candidate.monthly,
                                             engine, candidate.kind, routeDistance);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = engine.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = engine.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = engine.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = engine.id;
    }
  }
  local selectedProfit = selectedEconomics != null ? selectedEconomics.profitAnnual : -999999999;
  local selectedRoi = selectedEconomics != null ? selectedEconomics.roi : -1;
  OpexM3EquipmentLog("mode=road phase=" + phase + " cargo=" + candidate.cargo
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + selectedId
      + " selected_refit=" + (candidate.engine != null && candidate.engine.defaultCargo != candidate.cargo ? 1 : 0)
      + " selected_ok=" + (selectedEconomics != null ? 1 : 0)
      + " selected_profit=" + selectedProfit + " selected_roi=" + selectedRoi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1)
      + " admission_flip=" + ((selectedEconomics == null || selectedEconomics.profitAnnual <= 0)
          && bestProfit != null && bestProfit.profitAnnual > 0 ? 1 : 0)
      + " native_admission_flip=" + ((selectedEconomics == null || selectedEconomics.profitAnnual <= 0)
          && bestNativeProfit != null && bestNativeProfit.profitAnnual > 0 ? 1 : 0));
}
