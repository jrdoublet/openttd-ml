/* Etages 1 et 2 : ce que rapporte un candidat, et ce qu'il coute en opcodes.
 *
 * Etage 1 -- le profit attendu. Changement de fond par rapport a TrainLineAI : la variable n'est
 * plus population_a * population_b / distance (un proxy) mais la PRODUCTION reelle multipliee par
 * le revenu unitaire reel (AICargo.GetCargoIncome), c'est-a-dire la grandeur physique.
 *
 * Etage 2 -- le cout en opcodes attendu. Pour l'instant c'est un modele lineaire grossier ; il
 * sera remplace par une regression ajustee sur les campagnes, ou le nombre reel d'iterations
 * d'A* par ligne est connu.
 *
 * candidates.nut produit les alternatives : projects.nut choisit d'abord le ROI modal, remplit
 * ensuite le budget sur le revenu/capital, puis seulement ordonne sur le revenu/opcode.
 */

/* Distance minimale commune aux projets terrestres. Le rail et la route doivent se chevaucher
 * entre 5 et 25 tuiles : couper le rail a 25 AVANT le calcul economique empechait precisement de
 * choisir le meilleur mode pour un meme couple origine/destination. Le modele de capital du rail
 * le declasse normalement dans cette bande ; c'est desormais un resultat du ROI, pas un a priori
 * d'orchestration.
 *
 * 🔴 REGRESSION SILENCIEUSE, trouvee le 2026-09-02 (docs/taches.md S0 septdecies) : le texte
 * ci-dessus decrit le comportement voulu, PAS celui livre. Le commit 3467851 avait bien mis la
 * borne a 5 en ecrivant ce commentaire ; 31b13bad l'a repassee a 25 sans toucher un mot du texte
 * ni justifier, au milieu d'un commit melangeant des changements sans rapport. La bande 5-24
 * tuiles etait donc fermee a 100 % au rail par accident, sans arbitrage ROI possible -- et le
 * volume est ~85 % de l'ecart avec AAAHogEx.
 *
 * Devenu le reglage `rail_min_distance` pour que le banc puisse opposer 5 a 25 en une campagne.
 * Repli 25 (comportement livre) jusqu'a la lecture unique dans Start().
 *
 * MESURE le 2026-09-02 (docs/bench_rail_min_distance_3y.json, 20 graines x 3 ans, apparie) : NUL.
 * company_value -0,6 % (t = 0,12), profit_year -1,0 % (t = 0,17), et surtout le compte de signes
 * vaut 8/20, 9/20, 11/20, 7/20, 10/20 -- la signature exacte du rebattage de trajectoires. Le
 * reglage AGIT (les valeurs par graine different, il n'est pas inerte), mais son effet est de
 * signe aleatoire. Defaut LAISSE A 25.
 *
 * Lecture probable, ecrite dans le commentaire d'origine lui-meme : le rail est de toute facon
 * declasse dans cette bande par l'election modale au ROI (projects.nut:127), donc le filtre
 * supprimait en amont ce que l'election supprimait en aval. Filtre REDONDANT, pas nuisible.
 * Non verifie : le confirmer demanderait d'instrumenter combien de candidats 5-24 atteignent
 * l'election modale et la perdent. */
MIN_DISTANCE <- 25;
MAX_DISTANCE <- 200;
JOIN_PLACE_MAX <- 75;
TOP_K <- 20;
MIN_RATIO <- 500;
VIVIER_RATIO_FILTER <- true;
CLEAN_DENSITY_SCORE <- true;
/* C29.1 + C29.2 : Deverrouillage du rabattement (feeders) vers hubs aeriens et ferroviaires */
FEEDER_UNLOCK <- true;
/* C29.3 : Pricing du feeder calculé sur le revenu hub et le bassin de captage */
FEEDER_PRICING <- true;
/* C29.4 : Couverture multi-arrêts urbaine pour rabattement (modèle AAAHogEx) */
FEEDER_TOWN_COVERAGE <- true;
PROBE_STASH_K <- 12;
/* "Presque admis" : predit > -1000. L'echelle du plancher MIN_RATIO * iterations/1000
 * pour une ligne courte (~500*310/1000 = 155) est plus petite ; -1000 reste du meme
 * ordre qu'une ligne mediocre, pas un gouffre d'amortissement. */
const PROBE_NEAR_ZERO = -1000;

/* Retuning pax borne (suite item 7). Les 11/11 paires pax <=100 tuiles force-construites
 * avec predit -146..-9 etaient rentables en derniere annee ; au-dela de 100 la mediane
 * reelle est 0. On admet cette famille au classement, rien d'autre : pas le fret, pas
 * le long, pas un decalage de OpexLineEconomics. ratio = 1 les place sous tout candidat
 * qui passe MIN_RATIO. _tryBuild les bride a 1 tentative/an au plafond dur.
 * PAX_NEAR_MIN_PROFIT = -200 couvre l'echantillon (-146) sans ouvrir le gouffre. */
const PAX_NEAR_MAX_DISTANCE = 100;
const PAX_NEAR_MIN_PROFIT = -200;
const PAX_NEAR_MAX_ATTEMPTS_PER_YEAR = 1;
const PAX_NEAR_RATIO = 1;

/* Etage 2 : le cout, AJUSTE sur la campagne v3 (1997 lignes reelles, OpenTTD 13.4).
 *
 * La grandeur utile n'est pas "iterations d'une tentative" mais "iterations par ligne REUSSIE",
 * qui absorbe l'echec : iterations_moyennes / P(construite).
 *
 * On garde une table de noeuds avec interpolation lineaire : exacte aux noeuds, entierement
 * en entiers, aucune fonction mathematique flottante en Squirrel.
 *
 *   distance :    23     33     48     63     81    105     150
 *   iterations:  371    673   2188   4066   7745  15308   53951
 *
 * Deux tables, memes abcisses. astar_cost=0 : noeuds 13.4 (TrainLineAI). astar_cost=1 :
 * iterations AMORTIES par succes, fenetre +/-12 tuiles autour de chaque noeud, 227 tentatives
 * (docs/opex_attempt_distance_20y_5seeds.json). ATTEMPT_MULTIPLIER reste 4 : p95(iter OK) /
 * amort <= 2,7 sur toutes les bandes, donc 4x couvre la queue d'une tentative isolee. Le
 * plancher 2000 absorbe le court (4*310=1240 < 2000). Recalibrer les noeuds SANS ce M
 * reproduirait "budgets 50-400, zero ligne".
 *
 *   distance :                 23    33    48    63    81     105     150
 *   v1 (13.4) :               371   673  2188  4066  7745   15308   53951
 *   v2 (amorti 15.3) :        310   690  2500  5400  8200   26000   52000
 *
 * v2 est plus cher a 63 (ABND dans 50-70) et surtout a 105 (8 des 12 ABND au-dela).
 * Le court reste du meme ordre. Le classement a v2 prefere le court, et MIN_RATIO coupe
 * le long. Banc 20 graines : gares -7,9 % (t = -3,23), valeur sous le plancher. Defaut 0.
 */
KNOT_DISTANCE <- [23, 33, 48, 63, 81, 105, 150];
KNOT_ITERATIONS_V1 <- [371, 673, 2188, 4066, 7745, 15308, 53951];
KNOT_ITERATIONS_V2 <- [310, 690, 2500, 5400, 8200, 26000, 52000];
ASTAR_COST_V2 <- false;

function OpexRailIterations(distance)
{
  local knots = ASTAR_COST_V2 ? KNOT_ITERATIONS_V2 : KNOT_ITERATIONS_V1;
  local n = KNOT_DISTANCE.len();
  if (distance <= KNOT_DISTANCE[0]) return knots[0];
  for (local i = 1; i < n; i++) {
    if (distance <= KNOT_DISTANCE[i]) {
      local d0 = KNOT_DISTANCE[i - 1];
      local d1 = KNOT_DISTANCE[i];
      local v0 = knots[i - 1];
      local v1 = knots[i];
      return v0 + ((v1 - v0) * (distance - d0)) / (d1 - d0);
    }
  }
  /* Au-dela du dernier noeud, la complexite empirique d'un pathfinder A* sur grille 2D croit
   * au moins comme le carre de la distance (surface exploree). */
  local dLast = KNOT_DISTANCE[n - 1];
  local vLast = knots[n - 1];
  return (vLast * distance * distance) / (dLast * dLast);
}

/* Une origine rail est constructible s'il existe, dans le bassin, une tuile de TERRE qui voit
 * le cargo et qui n'est pas le batiment d'industrie lui-meme. Sans ce test, des origines fret
 * dont tout le bassin est de l'eau (ou du batiment) entraient au TOP_K puis mouraient en SITEA
 * a ~14 M d'opcodes (mesure 2026-08-29, graine 42 : 7 a 15 SITEA fret, nCargo=0, nCmd=0). */
function OpexRailOriginSitable(tile, cargo, coverage, wantProduction)
{
  local radius = coverage + 3;
  for (local r = 0; r <= radius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local t = tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(t)) continue;
        if (AITile.IsWaterTile(t)) continue;
        if (AITile.IsStationTile(t) || AIRail.IsRailTile(t)) continue;
        local industry = AIIndustry.GetIndustryID(t);
        if (AIIndustry.IsValidIndustry(industry)) continue;
        local value = wantProduction
            ? AITile.GetCargoProduction(t, cargo, 1, 1, coverage)
            : AITile.GetCargoAcceptance(t, cargo, 1, 1, coverage);
        if (wantProduction ? (value > 0) : (value >= 8)) return true;
      }
    }
  }
  return false;
}

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats, isTransformer = false)
{
  if (monthly <= 0) {
    stats.noMonthly++;
    return null;
  }
  /* Source seulement, et seulement si origin_sitable = 1. Les 7 a 15 SITEA mesures etaient
   * tous du fret a nCargo=0 cote A. Filtrer aussi le puits enlevait des paires urbaines encore
   * constructibles. A 0, le classement est celui d'avant le filtre (SITEA reste possible). */
  if (ORIGIN_SITABLE && !OpexRailOriginSitable(srcTile, cargo, catalog.railCoverage, true)) {
    stats.unsitable++;
    return null;
  }
  local distance = AIMap.DistanceManhattan(srcTile, dstTile);
  if (distance < MIN_DISTANCE) {
    stats.distanceShort++;
    return null;
  }
  if (distance > MAX_DISTANCE) {
    stats.distanceLong++;
    return null;
  }

  local economics = OpexLineEconomics(catalog, cargo, distance, monthly, kind);
  if (economics == null) {
    stats.economicsUnavailable++;
    return null;
  }
  /* Un candidat dont le profit annuel attendu est negatif ne merite AUCUN opcode,
   * SAUF la famille pax_near (pax, <=100 tuiles, predit > -200) : le sondage a
   * 40 000 iterations a trouve 11/11 rentables en derniere annee, et le long non.
   * Derriere probe_negative=1, les AUTRES rejets sont ranges pour le force-build. */
  if (economics.profitAnnual <= 0) {
    if (PAX_NEAR && kind == "pax" && distance <= PAX_NEAR_MAX_DISTANCE
        && economics.profitAnnual > PAX_NEAR_MIN_PROFIT) {
      return OpexMakePaxNearCandidate(kind, cargo, srcTile, dstTile, monthly, originServed,
                                      distance, economics, stats);
    }
    stats.profitNonPositive++;
    if (PROBE_NEGATIVE) OpexStashNegative(stats, kind, cargo, srcTile, dstTile, monthly,
                                          originServed, distance, economics);
    return null;
  }

  local iterations = OpexRailIterations(distance);
  local opcodeRatio = (economics.profitAnnual * 1000) / iterations;
  /* MIN_RATIO reste une mesure et le cout d'opportunite terminal du pathfinder, mais il ne peut
   * plus eliminer un mode AVANT l'arbitrage par couple O/D. La contrainte d'opcodes est appliquee
   * apres la contrainte de capital dans projects.nut. */
  local minRatio = (kind == "freight") ? 200 : MIN_RATIO;
  local isLowRatio = (opcodeRatio < minRatio);
  if (isLowRatio) {
    stats.ratioTooLow++;
    if (VIVIER_RATIO_FILTER) return null;
  }

  /* Score composite : priorise le fort ROI et le retour sur investissement rapide (cash turnover).
   * Une rotation rapide (oneWayDays court) reinjecte du cash rapidement pour financer les lignes suivantes. */
  local turnoverBonus = 100;
  if (economics.oneWayDays <= 12) turnoverBonus = 130;
  else if (economics.oneWayDays <= 25) turnoverBonus = 115;
  else if (economics.oneWayDays <= 45) turnoverBonus = 100;
  else turnoverBonus = 60;
  local freightBonus = 100;
  if (kind == "freight") {
    /* Le fret beneficie d'un monopole d'exploitation absolu sans concurrence adverse (+40%) */
    freightBonus = 140;
    if (isTransformer) {
      /* Bonus de chaîne industrielle : alimenter une usine génère des marchandises en aval (+35%) */
      freightBonus = (freightBonus * 135) / 100;
    }
  }
  local adjustedRoi = (((economics.roi * turnoverBonus) / 100) * freightBonus) / 100;
  local ratio = opcodeRatio + (adjustedRoi * 15);
  local effectiveRoi = (economics.roi * freightBonus) / 100;

  stats.accepted++;
  return {
    mode = "rail",
    kind = kind,            // "pax" ou "freight"
    cargo = cargo,
    /* Vrai quand UNE des deux extremites reutilise une origine deja desservie : ce candidat n'est
     * constructible que si _tooClose lui trouve un quai joint (cf. OpexOriginService ci-dessous).
     * Sert a l'instrumentation, pas a la decision -- l'autorite reste _tooClose. */
    originServed = originServed,
    src = srcTile,
    dst = dstTile,
    distance = distance,
    monthly = monthly,
    trains = economics.trains,
    wagons = economics.wagons,
    perTrain = economics.perTrain,
    platformLength = economics.platformLength,
    loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed,
    tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays,
    stationRating = economics.stationRating,
    offered = economics.offered,
    monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway,
    trainsForVolume = economics.trainsForVolume,
    carried = economics.carried,
    capital = economics.capital,
    vehicleCost = economics.vehicleCost,
    immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
    roi = effectiveRoi,
    freightBonus = freightBonus,
    isTransformer = isTransformer,
    profitAnnual = economics.profitAnnual,
    /* Detail du calcul, garde pour l'instrumentation predit-vs-reel (cf. main.nut). */
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = iterations,
    ratio = ratio,
    opcodeRatio = opcodeRatio,
    isLowRatio = isLowRatio,
  };
}

/* Famille pax_near : meme tableau qu'un candidat classe, ratio = 1 (sous MIN_RATIO),
 * slot paxNear pour que _tryBuild bride a une tentative/an au plafond dur.
 * Un helper evite de copier 30 champs dans le chemin profit>0. */
function OpexMakePaxNearCandidate(kind, cargo, srcTile, dstTile, monthly, originServed,
                                  distance, economics, stats)
{
  stats.paxNearAdmitted++;
  stats.accepted++;
  local candidate = {
    mode = "rail", kind = kind, cargo = cargo, originServed = originServed,
    src = srcTile, dst = dstTile, distance = distance, monthly = monthly,
    trains = economics.trains, wagons = economics.wagons, perTrain = economics.perTrain,
    platformLength = economics.platformLength, loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed, tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays, stationRating = economics.stationRating,
    offered = economics.offered, monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway, trainsForVolume = economics.trainsForVolume,
    carried = economics.carried, capital = economics.capital, roi = economics.roi,
    profitAnnual = economics.profitAnnual, revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual, amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = OpexRailIterations(distance),
    ratio = PAX_NEAR_RATIO,
  };
  candidate.paxNear <- true;
  return candidate;
}

/* Histogramme de TOUTES les paires a profit <= 0, plus les PROBE_STASH_K moins negatives.
 * Appele seulement si probe_negative = 1 : a 0, OpexMakeCandidate rend null comme avant
 * et le classement ne paie aucune de ces recopies. */
function OpexStashNegative(stats, kind, cargo, srcTile, dstTile, monthly, originServed,
                           distance, economics)
{
  if (kind == "pax") stats.negPax++; else stats.negFreight++;
  if (distance < 50) stats.negBand50++;
  else if (distance < 75) stats.negBand75++;
  else if (distance < 100) stats.negBand100++;
  else stats.negBand200++;
  if (economics.profitAnnual > PROBE_NEAR_ZERO) stats.negNear++;
  stats.negSum += economics.profitAnnual;
  if (stats.profitNonPositive == 1 || economics.profitAnnual < stats.negMin) {
    stats.negMin = economics.profitAnnual;
  }

  local profit = economics.profitAnnual;
  local stash = stats.negativeStash;
  if (stash.len() >= PROBE_STASH_K && profit <= stash[stash.len() - 1].profitAnnual) return;
  local candidate = {
    kind = kind,
    cargo = cargo,
    originServed = originServed,
    src = srcTile,
    dst = dstTile,
    distance = distance,
    monthly = monthly,
    trains = economics.trains,
    wagons = economics.wagons,
    perTrain = economics.perTrain,
    platformLength = economics.platformLength,
    loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed,
    tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays,
    stationRating = economics.stationRating,
    offered = economics.offered,
    monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway,
    trainsForVolume = economics.trainsForVolume,
    carried = economics.carried,
    capital = economics.capital,
    profitAnnual = profit,
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    /* Inutilise pour le budget : _tryProbeNegative passe alternativeRatio 0
     * (chemin Z, HARD_ITERATION_CAP). ratio = 0 pour qu'un probe ne puisse jamais
     * gagner un TOP_K s'il fuyait dans `all`. */
    iterations = 0,
    ratio = 0,
    probe = true,
  };
  local pos = stash.len();
  while (pos > 0 && stash[pos - 1].profitAnnual < profit) pos--;
  stash.insert(pos, candidate);
  if (stash.len() > PROBE_STASH_K) stash.pop();
}

/* Ne garder que les K meilleurs, sans trier les autres.
 *
 * Mesure du 2026-08-28 : trier les 687 candidats coutait 96 803 opcodes, soit 56 % du cout annuel
 * total de l'IA -- alors qu'on ne consomme jamais que la tete du classement. Contrairement au
 * catalogue (ou la mesure a REFUTE l'optimisation), ici elle la justifie. */
function OpexTopK(all, k)
{
  local best = [];
  local floor = 0;      // ratio minimal present dans best, une fois best plein
  foreach (candidate in all) {
    if (best.len() >= k && candidate.ratio <= floor) continue;
    local pos = best.len();
    while (pos > 0 && best[pos - 1].ratio < candidate.ratio) pos--;
    best.insert(pos, candidate);
    if (best.len() > k) best.pop();
    if (best.len() >= k) floor = best[best.len() - 1].ratio;
  }
  return best;
}

/* Exclusion a la GENERATION plutot qu'au FILTRAGE (2026-08-28). Mesure sur graine 42/20 ans
 * (docs/opex_full_campaign_20y.json) : les stalles restants de la campagne sont 20/20 candidats du
 * TOP_K rejetes par _tooClose (main.nut) pour la MEME raison -- une origine deja desservie, jamais
 * une proximite physique (near=20/far=0 a chaque annee bloquee). Le classement n'a alors aucune
 * chance de contenir un candidat constructible : TOP_K entier gaspille sur des origines mortes.
 * Exclure ici, avant OpexMakeCandidate, libere le TOP_K pour des candidats reellement
 * constructibles et evite le calcul economique (OpexLineEconomics) sur un candidat deja perdu.
 * Duplique deliberement le test ORIGIN_SEPARATION de _tooClose (meme rayon, meme regle "un seul
 * raccordement par origine") plutot que de changer sa signature : ORIGIN_SEPARATION reste une
 * const globale definie dans main.nut, visible ici car require()d avant toute execution (les
 * fonctions de ce fichier ne s'executent qu'apres que main.nut a fini de se charger).
 *
 * ATTENTION, cette exclusion a ete RAMENEE a son noyau le 2026-08-29 : elle ne vaut plus que pour
 * les paires dont les DEUX extremites sont servies. Une seule extremite servie passe desormais et
 * doit etre recuperee par un quai joint -- voir OpexOriginService plus bas, qui remplace l'appel
 * direct a OpexOriginServed dans les deux generateurs. _tooClose redevient l'autorite sur les deux
 * tests, MIN_SEPARATION comme identite d'origine.
 *
 * `includeRoad` (2026-08-29) : les lignes ROUTIERES vivent dans le meme tableau _lines que le rail
 * (pour etre rapportees et mises au rebut par le meme code), mais elles ne doivent PAS verrouiller
 * une ville pour une liaison rail interurbaine -- une desserte de bus sur 12 tuiles n'epuise pas
 * une ville, et le rail vaut bien davantage par ligne. Les generateurs rail passent donc false, et
 * seul le generateur routier passe true : lui doit s'exclure du rail ET de ses propres lignes,
 * sans quoi il rebatirait chaque annee la meme paire. */
function OpexOriginServed(lines, tile, includeRoad)
{
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail" && (!includeRoad || line.mode != "road")) continue;
    if (AIMap.DistanceManhattan(tile, line.originA) < ORIGIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(tile, line.originB) < ORIGIN_SEPARATION) return true;
  }
  return false;
}

/* DE LA GUILLOTINE AU FILET (2026-08-29). L'exclusion ci-dessus, ecrite le 2026-08-28, rejetait la
 * paire des qu'UNE de ses deux extremites etait servie. Mesure sur 20 ans, graine 42
 * (docs/opex_road_20y_42.json) : a partir de 1982 elle ecarte 213 a 242 paires par an et il ne
 * reste que 0 a 3 candidats classes -- la regle "un seul raccordement par origine" a consomme la
 * carte, et huit annees ne produisent que six lignes. Elle emportait aussi station_join, ecrit le
 * meme jour pour recuperer exactement ce vivier : 0 tentative en 20 ans, parce que le candidat
 * mourait un etage plus haut, avant que _tooClose puisse proposer un quai joint.
 *
 * La regle reste entiere -- on ne pose JAMAIS une seconde gare sur une origine deja servie -- mais
 * elle cesse d'etre un rejet : une extremite servie doit desormais etre RECUPEREE par un quai
 * joint, ou le candidat est rejete plus bas par _tooClose. Ce qui reste exclu ici sans appel :
 *  - les DEUX extremites servies (la ligne neuve doublerait un corridor deja tenu) ;
 *  - une origine servie par PLUSIEURS gares distinctes : OpexFindStationJoin exige un objet gare
 *    unique, aucune jointure n'est possible ;
 *  - une origine dont la ligne ne peut pas etre jointe (mode non rail, autre cargo, autre nature,
 *    role fret inverse) -- meme test que OpexJoinCompatible, appele ici pour ne pas le dupliquer.
 *
 * Ce filtre reste un SUR-ENSEMBLE de la decision reelle : il ignore MIN_SEPARATION et l'arbitrage
 * "une seule gare, une seule extremite" que seul _tooClose peut faire une fois les gares baties.
 * Son role est d'eviter de payer OpexLineEconomics pour une jointure structurellement impossible,
 * pas de trancher a la place de _tooClose. */

/* Etat d'une origine face aux lignes RAIL deja baties. Rend null si elle est libre, sinon la ligne
 * qui la sert et l'extremite concernee -- ou une table dont `blocked` est vrai quand plusieurs
 * gares DISTINCTES la servent. Les lignes non ferroviaires sont ignorees. */
function OpexOriginService(lines, tile)
{
  local found = null;
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    foreach (lineEnd in ["A", "B"]) {
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      if (AIMap.DistanceManhattan(tile, originTile) >= ORIGIN_SEPARATION) continue;
      local stationId = OpexLineStationId(line, lineEnd);
      if (found == null) {
        found = { line = line, lineEnd = lineEnd, stationId = stationId, blocked = false };
      } else if (found.stationId != stationId) {
        return { line = null, lineEnd = "", stationId = -1, blocked = true };
      }
    }
  }
  return found;
}

/* Une extremite servie merite-t-elle qu'on calcule son economie ? `end` est son role dans le
 * candidat a naitre ("A" = source/premiere ville, "B" = puits/seconde ville). */
function OpexOriginJoinable(service, kind, cargo, end)
{
  if (service.blocked || service.stationId < 0) return false;
  /* Meme regle que la jointure elle-meme, sans la recopier : OpexJoinCompatible ne lit que
   * .kind/.cargo du candidat et .line/.end/.lineEnd du conflit. */
  return OpexJoinCompatible({ kind = kind, cargo = cargo },
                            { line = service.line, end = end, lineEnd = service.lineEnd });
}

/* Combien de lignes RAIL utilisent deja ce StationID pour ce cargo. Les modes avec un champ
 * `mode` (air, eau, route) n'ont pas de quai rail a partager. */
function OpexStationCargoLineCount(lines, stationId, cargo)
{
  if (stationId < 0) return 0;
  local n = 0;
  foreach (line in lines) {
    if (("mode" in line)) continue;
    if (!("cargo" in line) || line.cargo != cargo) continue;
    if (OpexLineStationId(line, "A") == stationId || OpexLineStationId(line, "B") == stationId) n++;
  }
  return n;
}

/* La part du nouvel arrivant : 1/(n+1) de la production de CETTE extremite, n = lignes deja
 * la. n = 0 (StationID invalide) laisse le montant intact. */
function OpexShareBasin(amount, lines, stationId, cargo)
{
  local n = OpexStationCargoLineCount(lines, stationId, cargo);
  return amount / (n + 1);
}

/* Part de la production TOTALE d'une ville qui tombe dans le rayon de couverture d'UNE gare.
 * CALIBRE le 2026-08-28 (meme mesure que STATION_RATING_PCT ci-dessus) : en isolant le facteur
 * note de gare (mesure separement via AIStation.GetCargoRating), le residu -- production reelle
 * ayant atteint la gare divisee par AITown.GetLastMonthProduction -- vaut 8 a 37 % selon la
 * ligne, moyenne 22 % sur 9 lignes pax reelles. C'etait le biais deja signale, non calibre, dans
 * le commentaire precedent : AITown.GetLastMonthProduction porte sur la ville ENTIERE, une gare
 * n'en couvre qu'un rayon local. Domine le gap x10 predit/reel bien plus que STATION_RATING_PCT
 * (~1,4x seulement) : voir docs/opex_predict_vs_actual.json.
 * Ne s'applique QU'aux paires de villes : une industrie produit depuis une seule tuile, elle n'a
 * pas cette dilution geometrique -- non mesure ici, donc non touche. */
const TOWN_CATCHMENT_SHARE_PCT = 22;

function OpexJoinPlaceMaxDistance()
{
  local maxDist = JOIN_PLACE_MAX;
  if (JOIN_MAX_DISTANCE > 0 && JOIN_MAX_DISTANCE < maxDist) maxDist = JOIN_MAX_DISTANCE;
  return maxDist;
}

/* H2 pax : depuis chaque gare rail OpexAI, la ville libre la plus proche
 * dans la bande. L'objet join est attache ici, _tryBuild ne le redecouvre
 * pas via _tooClose. Une seule paire par ville libre (la gare la plus
 * proche), jamais deux gares sur la meme origine. */
function OpexPlaceJoinPax(catalog, lines, out, stats, towns, produced, served, cargo)
{
  local maxDist = OpexJoinPlaceMaxDistance();
  local stations = [];
  foreach (line in lines) {
    if (("mode" in line) || !("kind" in line) || line.kind != "pax") continue;
    if (!("platformA" in line) || !("platformB" in line) || line.cargo != cargo) continue;
    foreach (lineEnd in ["A", "B"]) {
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId < 0) continue;
      stations.append({
        stationId = stationId,
        platform = lineEnd == "A" ? line.platformA : line.platformB,
        tile = lineEnd == "A" ? line.stationA : line.stationB,
        origin = lineEnd == "A" ? line.originA : line.originB,
      });
    }
  }
  if (stations.len() == 0) return;

  for (local t = 0; t < towns.len(); t++) {
    if (served[t] != null) continue;
    local best = null;
    local bestD = 0;
    foreach (st in stations) {
      local d = AIMap.DistanceManhattan(st.tile, towns[t].tile);
      if (d < MIN_DISTANCE || d > maxDist) continue;
      if (best == null || d < bestD) {
        best = st;
        bestD = d;
      }
    }
    if (best == null) continue;
    stats.placeJoinPairs++;
    local originTown = AITile.GetClosestTown(best.origin);
    local originProd = AITown.GetLastMonthProduction(originTown, cargo);
    local monthly = ((originProd + produced[t]) * TOWN_CATCHMENT_SHARE_PCT) / 100;
    local candidate = OpexMakeCandidate(catalog, "pax", cargo, best.origin, towns[t].tile,
                                        monthly, true, stats);
    if (candidate == null) continue;
    local key = OpexAbandonedPairKey(candidate);
    if (key in stats.placeJoinKeys) continue;
    stats.placeJoinKeys[key] <- true;
    candidate.placeJoin <- {
      candidateEnd = "A",
      stationId = best.stationId,
      platform = best.platform,
    };
    stats.placeJoinAccepted++;
    out.append(candidate);
  }
}

/* H2 fret : un puits libre rejoint la source existante la plus proche du
 * meme cargo (candidateEnd A) ; une source libre rejoint le puits existant
 * le plus proche (candidateEnd B). Roles v1, pas d'inversion. */
function OpexPlaceJoinFreight(catalog, lines, out, stats, industries, served)
{
  local maxDist = OpexJoinPlaceMaxDistance();
  local sources = [];
  local sinks = [];
  foreach (line in lines) {
    if (("mode" in line) || !("kind" in line) || line.kind != "freight") continue;
    if (!("platformA" in line) || !("platformB" in line)) continue;
    local sidA = OpexLineStationId(line, "A");
    local sidB = OpexLineStationId(line, "B");
    if (sidA >= 0) {
      sources.append({
        cargo = line.cargo, stationId = sidA, platform = line.platformA,
        tile = line.stationA, origin = line.originA,
        srcIndustry = ("srcIndustry" in line) ? line.srcIndustry : -1,
      });
    }
    if (sidB >= 0) {
      sinks.append({
        cargo = line.cargo, stationId = sidB, platform = line.platformB,
        tile = line.stationB, origin = line.originB,
      });
    }
  }

  foreach (cargo, sinkIdxs in catalog.acceptors) {
    foreach (di in sinkIdxs) {
      if (served[di] != null) continue;
      local sink = industries[di];
      local best = null;
      local bestD = 0;
      foreach (st in sources) {
        if (st.cargo != cargo) continue;
        local d = AIMap.DistanceManhattan(st.tile, sink.tile);
        if (d < MIN_DISTANCE || d > maxDist) continue;
        if (best == null || d < bestD) {
          best = st;
          bestD = d;
        }
      }
      if (best == null) continue;
      stats.placeJoinPairs++;
      local monthly = (best.srcIndustry >= 0)
          ? AIIndustry.GetLastMonthProduction(best.srcIndustry, cargo) : 0;
      local candidate = OpexMakeCandidate(catalog, "freight", cargo, best.origin, sink.tile,
                                          monthly, true, stats);
      if (candidate == null) continue;
      local key = OpexAbandonedPairKey(candidate);
      if (key in stats.placeJoinKeys) continue;
      stats.placeJoinKeys[key] <- true;
      candidate.placeJoin <- {
        candidateEnd = "A",
        stationId = best.stationId,
        platform = best.platform,
      };
      stats.placeJoinAccepted++;
      out.append(candidate);
    }
  }

  foreach (cargo, srcIdxs in catalog.producers) {
    foreach (si in srcIdxs) {
      if (served[si] != null) continue;
      local source = industries[si];
      local best = null;
      local bestD = 0;
      foreach (st in sinks) {
        if (st.cargo != cargo) continue;
        local d = AIMap.DistanceManhattan(st.tile, source.tile);
        if (d < MIN_DISTANCE || d > maxDist) continue;
        if (best == null || d < bestD) {
          best = st;
          bestD = d;
        }
      }
      if (best == null) continue;
      stats.placeJoinPairs++;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile, best.origin,
                                          monthly, true, stats);
      if (candidate == null) continue;
      local key = OpexAbandonedPairKey(candidate);
      if (key in stats.placeJoinKeys) continue;
      stats.placeJoinKeys[key] <- true;
      candidate.placeJoin <- {
        candidateEnd = "B",
        stationId = best.stationId,
        platform = best.platform,
      };
      stats.placeJoinAccepted++;
      out.append(candidate);
    }
  }
}

/* Paires de villes pour les passagers. */
function OpexPaxCandidates(catalog, lines, out, stats)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  for (local i = 0; i < n; i++) {
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
    produced.append(p);
    local service = OpexOriginService(lines, towns[i].tile);
    served.append(service);
    if (service != null) stats.townsServed++; else stats.townsUnserved++;
  }
  if (JOIN_PLACE) OpexPlaceJoinPax(catalog, lines, out, stats, towns, produced, served, cargo);
  for (local a = 0; a < n; a++) {
    for (local b = a + 1; b < n; b++) {
      stats.pairsTotal++;
      local sa = served[a];
      local sb = served[b];
      /* Les deux extremites servies, ou le bras de controle du banc (station_join = 0) : rejet
       * sec, exactement comme avant le 2026-08-29. Le compteur garde donc le meme sens dans les
       * deux bras. */
      if ((sa != null && sb != null) || (!STATION_JOIN && (sa != null || sb != null))) {
        stats.pairsOriginServed++;
        continue;
      }
      if (sa != null && !OpexOriginJoinable(sa, "pax", cargo, "A")) {
        stats.pairsJoinImpossible++;
        continue;
      }
      if (sb != null && !OpexOriginJoinable(sb, "pax", cargo, "B")) {
        stats.pairsJoinImpossible++;
        continue;
      }
      local originServed = sa != null || sb != null;
      if (originServed) stats.pairsOneServed++;
      /* Une ligne dessert les deux sens, et chaque sens transporte la production de SON
       * origine : le debit utile est la somme, pas le minimum. On ignore encore la croissance de
       * la ville que la desserte provoque (sous-estimation non calibree, plus petite que le
       * facteur ci-dessus d'apres la mesure). */
      local prodA = produced[a];
      local prodB = produced[b];
      /* basin_share : la ville DEJA servie n'offre plus sa production entiere. Ce n'est PAS le
       * double comptage mesure (et ecarte) ci-dessous : c'est le partage de stock une fois le
       * StationID joint, docs/taches.md §2.9.3. */
      if (BASIN_SHARE && sa != null) prodA = OpexShareBasin(prodA, lines, sa.stationId, cargo);
      if (BASIN_SHARE && sb != null) prodB = OpexShareBasin(prodB, lines, sb.stationId, cargo);
      local monthly = ((prodA + prodB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      /* BIAIS MESURE, ET CE N'EST PAS LUI LE COUPABLE (2026-08-29, sweeps/opex_join_bias.py sur
       * 10 graines x 20 ans, 155 lignes). Quand `originServed` est vrai, la ville servie voit deja
       * une partie de sa production partir par la ligne existante et ce calcul la compte une
       * seconde fois : le rapport brut reel/predit semblait donner x1,53. Mais les lignes a origine
       * servie sont aussi plus LONGUES (mediane 84 tuiles contre 47) et plus TARDIVES (1981 contre
       * 1975). Une fois type, distance et epoque neutralises ensemble, il ne reste que x0,81, IC
       * 95 % [0,63 ; 1,03] -- l'intervalle contient 1. Le double comptage existe peut-etre, il ne
       * depasse pas le bruit a cet effectif, et il n'explique PAS le verdict du banc.
       * Ce que la mesure designe a sa place est dans docs/taches.md : le profit reel vaut 1,47 fois
       * le predit sous 50 tuiles, 0,41 entre 50 et 75, et la MEDIANE tombe a 0,00 au-dela de 100.
       * Corriger `monthly` ici serait donc traiter le mauvais terme. */
      local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                          monthly, originServed, stats);
      if (candidate != null) {
        if (JOIN_PLACE && (OpexAbandonedPairKey(candidate) in stats.placeJoinKeys)) {
          /* H2 porte deja le join ; ne pas occuper un second slot TOP_K. */
        } else {
          out.append(candidate);
        }
      }
    }
  }
}

/* Industries : on n'apparie que des couples producteur/accepteur du MEME cargo, ce qui garde
 * l'etage 1 lineaire en nombre d'industries plutot que quadratique sur tout le catalogue. */
function OpexFreightCandidates(catalog, lines, out, stats)
{
  local industries = catalog.industries;
  local served = [];
  for (local i = 0; i < industries.len(); i++) {
    local service = OpexOriginService(lines, industries[i].tile);
    served.append(service);
    if (service != null) stats.industriesServed++; else stats.industriesUnserved++;
  }
  if (JOIN_PLACE) OpexPlaceJoinFreight(catalog, lines, out, stats, industries, served);
  foreach (cargo, sources in catalog.producers) {
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = COMPLEX_CARGO && (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];
    foreach (si in sources) {
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      /* Source seulement : le puits n'a pas de production a partager. */
      if (BASIN_SHARE && ss != null) {
        monthly = OpexShareBasin(monthly, lines, ss.stationId, cargo);
      }
      foreach (di in sinks) {
        if (di == si) continue;
        stats.pairsTotal++;
        local sd = served[di];
        /* Meme regle qu'en pax ci-dessus, roles compris : la source est l'extremite "A" du
         * candidat a naitre, le puits l'extremite "B". */
        if ((ss != null && sd != null) || (!STATION_JOIN && (ss != null || sd != null))) {
          stats.pairsOriginServed++;
          continue;
        }
        if (ss != null && !OpexOriginJoinable(ss, "freight", cargo, "A")) {
          stats.pairsJoinImpossible++;
          continue;
        }
        if (sd != null && !OpexOriginJoinable(sd, "freight", cargo, "B")) {
          stats.pairsJoinImpossible++;
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local originServed = ss != null || sd != null;
        if (originServed) stats.pairsOneServed++;
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                            industries[di].tile, monthly, originServed, stats, isTransformer);
        if (candidate != null) {
          if (JOIN_PLACE && (OpexAbandonedPairKey(candidate) in stats.placeJoinKeys)) {
            /* H2 porte deja le join ; ne pas occuper un second slot TOP_K. */
          } else {
            out.append(candidate);
          }
        }
      }

      /* Livraison des marchandises complexes aux villes acceptatrices (Goods, Food, Mail, etc.) */
      if (hasTownSinks) {
        local townSinks = catalog.townAcceptors[cargo];
        foreach (town in townSinks) {
          stats.pairsTotal++;
          local st = OpexOriginService(lines, town.tile);
          if ((ss != null && st != null) || (!STATION_JOIN && (ss != null || st != null))) {
            stats.pairsOriginServed++;
            continue;
          }
          if (ss != null && !OpexOriginJoinable(ss, "freight", cargo, "A")) {
            stats.pairsJoinImpossible++;
            continue;
          }
          if (st != null && !OpexOriginJoinable(st, "freight", cargo, "B")) {
            stats.pairsJoinImpossible++;
            continue;
          }
          local townMonthly = monthly;
          if (townMonthly <= 0 && ss != null) {
            /* Industrie de transformation activement approvisionnée en amont */
            townMonthly = 45;
          }
          if (townMonthly <= 0) continue;
          local originServed = ss != null || st != null;
          if (originServed) stats.pairsOneServed++;
          local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                              town.tile, townMonthly, originServed, stats, false);
          if (candidate != null) {
            candidate.dstTown <- town.id;
            out.append(candidate);
          }
        }
      }
    }
  }
}

/* Construit et classe tous les candidats. Rend la liste triee par rapport decroissant.
 * `lines` (this._lines de main.nut) sert a exclure les origines deja desservies avant meme de
 * calculer un candidat -- voir OpexOriginServed ci-dessus. */
function OpexBuildCandidates(catalog, budget, lines)
{
  local all = [];
  /* Comptes de rejet : ils se trouvent ici, avant que TOP_K ne masque les candidats restants.
   * Une table explicite evite une closure imbriquee, non portable dans le Squirrel du scenario. */
  local stats = {
    townsServed = 0, townsUnserved = 0, industriesServed = 0, industriesUnserved = 0,
    pairsTotal = 0, pairsOriginServed = 0, pairsJoinImpossible = 0, pairsOneServed = 0,
    noMonthly = 0, unsitable = 0,
    distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
    profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
  };
  /* Slots de l'item 7 : `<-` seulement a probe_negative=1. A 0, la table de stats
   * est bit a bit celle d'avant ce commit, et OpexMakeCandidate ne les touche pas. */
  if (PROBE_NEGATIVE) {
    stats.negativeStash <- [];
    stats.negBand50 <- 0;
    stats.negBand75 <- 0;
    stats.negBand100 <- 0;
    stats.negBand200 <- 0;
    stats.negPax <- 0;
    stats.negFreight <- 0;
    stats.negNear <- 0;
    stats.negSum <- 0;
    stats.negMin <- 0;
  }
  if (PAX_NEAR) stats.paxNearAdmitted <- 0;
  if (JOIN_PLACE) {
    stats.placeJoinKeys <- {};
    stats.placeJoinPairs <- 0;
    stats.placeJoinAccepted <- 0;
  }

  budget.begin();
  OpexPaxCandidates(catalog, lines, all, stats);
  budget.end("cand_pax");

  budget.begin();
  OpexFreightCandidates(catalog, lines, all, stats);
  budget.end("cand_freight");

  budget.begin();
  local best = OpexTopK(all, TOP_K);
  budget.end("cand_rank");

  stats.topKOmitted = all.len() - best.len();

  if (DECISION_LOG) {
    OpexDecide("VIVIER_GEN", "mode=rail produced=" + stats.pairsTotal + " kept=" + all.len());
    if (stats.pairsOriginServed > 0) {
      OpexDecide("VIVIER_REJECT", "reason=origin_served n=" + stats.pairsOriginServed);
    }
    if (stats.pairsJoinImpossible > 0) {
      OpexDecide("VIVIER_REJECT", "reason=join_impossible n=" + stats.pairsJoinImpossible);
    }
    if (stats.noMonthly > 0) {
      OpexDecide("VIVIER_REJECT", "reason=no_monthly n=" + stats.noMonthly);
    }
    if (stats.unsitable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=unsitable n=" + stats.unsitable);
    }
    if (stats.distanceShort > 0) {
      OpexDecide("VIVIER_REJECT", "reason=distance_short n=" + stats.distanceShort);
    }
    if (stats.distanceLong > 0) {
      OpexDecide("VIVIER_REJECT", "reason=distance_long n=" + stats.distanceLong);
    }
    if (stats.economicsUnavailable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=economics_unavailable n=" + stats.economicsUnavailable);
    }
    if (stats.profitNonPositive > 0) {
      OpexDecide("VIVIER_REJECT", "reason=profit_non_positive n=" + stats.profitNonPositive);
    }
    if (stats.ratioTooLow > 0) {
      OpexDecide("VIVIER_REJECT", "reason=ratio_too_low n=" + stats.ratioTooLow);
    }
  }

  return { all = all.len(), candidates = all, best = best,
           bands = OpexBands(all), stats = stats };
}

/* Meilleur rapport atteint dans chaque bande de distance.
 *
 * Diagnostic, pas decision : il sert a confronter la FORME de notre modele a la courbe mesuree
 * sur la campagne v3 (optimum profit/iteration a 48-63 tuiles, docs/opex_cost_model.json). Si
 * notre modele prefere systematiquement une autre bande, c'est lui qui est faux, pas la mesure. */
BAND_EDGES <- [25, 45, 70, 110, 200];

function OpexBands(all)
{
  local best = [0, 0, 0, 0];
  foreach (candidate in all) {
    for (local i = 0; i < 4; i++) {
      if (candidate.distance >= BAND_EDGES[i] && candidate.distance < BAND_EDGES[i + 1]) {
        if (candidate.ratio > best[i]) best[i] = candidate.ratio;
        break;
      }
    }
  }
  return best;
}

/* --- Candidats ROUTIERS (2026-08-29) ---------------------------------------------------------
 *
 * Le creneau route reste borne a 5--25 tuiles, mais le rail descend maintenant a 5 : ce
 * chevauchement est volontaire. Une gare, une voie et une locomotive amortissent souvent moins
 * bien une liaison courte qu'un camion sans voie ni signaux ; projects.nut mesure pourtant les
 * deux au lieu de graver cette conclusion dans une bande de distance. Les modes se disputent donc
 * bien la meme PAIRE, et le gagnant est celui au meilleur ROI. Le revenu/capital remplit ensuite
 * le budget commun, puis le revenu/opcodes ordonne seulement les projets finances.
 *
 * Trois familles de candidats, la deuxieme et la troisieme etant l'objet meme de la manoeuvre --
 * "des petites lignes courtes avec du cargo" :
 *   1. ville <-> ville, passagers (l'ancienne liaison bus v1, desormais une famille parmi trois) ;
 *   2. industrie -> industrie, un cargo produit par l'une et accepte par l'autre ;
 *   3. industrie -> ville, pour les cargos qu'une ville accepte (biens, nourriture...) -- la
 *      famille la plus dense sur nos cartes, parce que les villes sont nombreuses et proches des
 *      industries de transformation, la ou deux industries appariables sont rarement voisines.
 */
const ROAD_MIN_DISTANCE = 5;
const ROAD_MAX_DISTANCE = 25;

/* TOP_K reste une vue de diagnostic propre a la route. La decision d'investissement utilise la
 * liste complete candidates et le portefeuille commun de projects.nut ; ce plafond ne peut donc
 * plus imposer une priorite modale. */
ROAD_TOP_K <- 48;

/* Repere historique de profit, conserve pour RS et les campagnes comparables. Il ne coupe plus
 * aucun candidat rentable avant l'arbitrage modal : profitTooLow compte les projets sous ce
 * repere, tandis que profitAnnual <= 0 reste le seul rejet economique. Mesure 2026-08-30
 * (docs/opex_road_predict_vs_actual.json) : 12 pax, mediane reel/predit 3,91 ; fret temoin 1,21.
 * La valeur n'est donc plus un parametre de decision.
 */
const ROAD_MIN_PROFIT_ANNUAL = 1000;

/* Seuil d'acceptation d'une ville pour un cargo. AITile.GetCargoAcceptance rend une acceptation en
 * huitiemes d'unite ; le moteur exige 8 (une unite pleine) pour livrer quoi que ce soit. En dessous
 * la gare accepterait le cargo a l'affichage sans que la livraison paie. */
const ROAD_ACCEPTANCE_MIN = 8;

/* Cout en "iterations equivalentes" d'une tentative routiere, pour rester dans la meme unite que
 * le rail (1 iteration ~ 2 700 opcodes).
 *
 * Mesure 2026-08-30 (docs/opex_road_rb_calibrate.json, panneau RB, campagne TRACEX 5 graines,
 * n = 10). Plan OK mediane 31 440 opcodes (~11,7 iter) contre 20+d ~ 42,5 (rapport 0,29).
 * BASE impliquee plan seul : -9. TRACEX 70-107 k. Le build (mediane 287 k) est maintenant inclus
 * dans expectedOpcodes, comme la transaction rail : l'unite commune ne sert qu'a ordonner sous
 * contrainte de calcul APRES le choix modal par ROI et la selection sous capital.
 */
const ROAD_PLAN_ITERATIONS_BASE = 20;

function OpexRoadIterations(distance)
{
  return ROAD_PLAN_ITERATIONS_BASE + distance;
}

/* Un candidat routier porte les memes champs que son homologue rail (le constructeur de ligne, le
 * rapport annuel et la mise au rebut sont communs), plus ce qu'il faut pour retrouver les sites
 * d'arret : le role de chaque extremite (ville ou industrie) et, pour une ville, son identifiant. */
function OpexMakeRoadCandidate(catalog, kind, cargo, src, dst, srcTown, dstTown, distance,
                               monthly, stats, isTransformer = false, isFeeder = false)
{
  local engine = (cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[cargo] : null;
  if (engine == null) {
    stats.noEngine++;
    return null;
  }
  local economics = OpexRoadLineEconomics(catalog, cargo, distance, monthly, engine, kind);
  if (economics == null) {
    stats.economicsUnavailable++;
    return null;
  }
  /* Le plancher historique reste telemetre mais ne peut plus eliminer un mode avant le ROI.
   * Pour un feeder, le profit direct routier est souvent negatif sur courte distance (5-10 tuiles),
   * mais sa rentabilite globale est portee par le reseau aerien/ferroviaire (FEEDER_PRICING). */
  if (!isFeeder && economics.profitAnnual <= 0) {
    stats.profitTooLow++;
    return null;
  }
  if (!isFeeder && economics.profitAnnual < ROAD_MIN_PROFIT_ANNUAL) stats.profitTooLow++;
  local iterations = OpexRoadIterations(distance);
  local freightBonus = 100;
  if (kind == "freight") {
    freightBonus = 140;
    if (isTransformer) freightBonus = (freightBonus * 135) / 100;
  }
  local effectiveRoi = (economics.roi * freightBonus) / 100;
  stats.accepted++;
  return {
    mode = "road",
    kind = kind,
    cargo = cargo,
    src = src,
    dst = dst,
    /* -1 = extremite industrielle : le site d'arret se cherche dans un petit rayon autour de la
     * tuile de l'industrie. Un identifiant de ville >= 0 contraint au contraire la recherche a
     * rester dans cette ville (AITile.GetClosestTown), comme le faisait la v1. */
    srcTown = srcTown,
    dstTown = dstTown,
    distance = distance,
    monthly = monthly,
    engine = engine,
    trains = economics.trains,
    carried = economics.carried,
    capital = economics.capital,
    immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
    roi = effectiveRoi,
    freightBonus = freightBonus,
    isTransformer = isTransformer,
    profitAnnual = economics.profitAnnual,
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    effectiveSpeed = economics.effectiveSpeed,
    iterations = iterations,
    ratio = (economics.profitAnnual * 1000) / iterations,
  };
}

function OpexRoadPairServed(lines, tileA, tileB)
{
  if (lines == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if ((AIMap.DistanceManhattan(tileA, line.originA) < ORIGIN_SEPARATION &&
         AIMap.DistanceManhattan(tileB, line.originB) < ORIGIN_SEPARATION) ||
        (AIMap.DistanceManhattan(tileA, line.originB) < ORIGIN_SEPARATION &&
         AIMap.DistanceManhattan(tileB, line.originA) < ORIGIN_SEPARATION)) {
      return true;
    }
  }
  return false;
}

function OpexTownRoadLineCount(lines, townTile)
{
  local count = 0;
  if (lines == null) return 0;
  local townId = AITile.GetClosestTown(townTile);
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    local isFeeder = (("isFeeder" in line) && line.isFeeder) ||
                     (("purpose" in line) && line.purpose == "feeder");
    if (isFeeder) {
      if (("srcTown" in line && line.srcTown == townId) ||
          AITile.GetClosestTown(line.originA) == townId) {
        count++;
      }
    } else {
      if (AITile.GetClosestTown(line.originA) == townId ||
          AITile.GetClosestTown(line.originB) == townId) {
        count++;
      }
    }
  }
  return count;
}

/* C29.4 : Compte le nombre de lignes de rabattement (feeders) actives reliant une ville à un hub donné. */
function OpexTownFeederCount(lines, townTile, hubStationId)
{
  if (lines == null || !AIStation.IsValidStation(hubStationId)) return 0;
  local count = 0;
  local townId = AITile.GetClosestTown(townTile);
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    local isFeeder = (("isFeeder" in line) && line.isFeeder) ||
                     (("purpose" in line) && line.purpose == "feeder");
    if (!isFeeder) continue;
    local targetStation = ("hubStationId" in line) ? line.hubStationId : -1;
    if (targetStation < 0 && ("stationB" in line)) {
      targetStation = AIStation.GetStationID(line.stationB);
    }
    if (targetStation == hubStationId) {
      if (("srcTown" in line && line.srcTown == townId) ||
          AITile.GetClosestTown(line.originA) == townId) {
        count++;
      }
    }
  }
  return count;
}

/* C29.2 : Verifie si une ville possede deja une ligne de rabattement (feeder) active vers un hub donne.
 * Contrairement a OpexRoadPairServed, les lignes routieres ordinaires (interurbaines) ne bloquent pas
 * le rabattement vers ce hub. */
function OpexTownFeederServed(lines, townTile, hubStationId)
{
  return OpexTownFeederCount(lines, townTile, hubStationId) > 0;
}

/* C31.3 : index (ville, hub) -> { count, stops }, construit en UN SEUL parcours des lignes.
 *
 * OpexTownFeederCount etait rappele pour CHAQUE couple (ville, hub) et reparcourait a chaque fois
 * toutes les lignes en appelant AITile.GetClosestTown. Sur l'etat mesure -- 57 villes, jusqu'a
 * 45 hubs (docs/diag_1v1_10y.json.gz), 14 feeders -- cela fait de l'ordre de 36 000 appels API par
 * execution de la tache, pour un resultat qui ne depend que des lignes. L'index le rend en
 * O(lignes) : un seul appel GetClosestTown par ligne heritee, aucun pour les lignes posees depuis
 * C29 puisqu'elles portent `srcTown` (main.nut:1552).
 *
 * Difference de semantique assumee : l'ancien code rattachait une ligne heritee a une ville par
 * proximite (DistanceManhattan < ORIGIN_SEPARATION), l'index le fait par IDENTITE de ville. C'est
 * le meme test que celui deja applique aux lignes portant `srcTown`, donc l'index est homogene la
 * ou l'ancien code melangeait deux criteres. */
function OpexBuildFeederIndex(lines)
{
  local index = {};
  if (lines == null) return index;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    local isFeeder = (("isFeeder" in line) && line.isFeeder) ||
                     (("purpose" in line) && line.purpose == "feeder");
    if (!isFeeder) continue;
    local hubId = ("hubStationId" in line) ? line.hubStationId : -1;
    if (hubId < 0 && ("stationB" in line)) hubId = AIStation.GetStationID(line.stationB);
    if (hubId < 0) continue;
    local townId = ("srcTown" in line && line.srcTown >= 0)
        ? line.srcTown : AITile.GetClosestTown(line.originA);
    local key = townId + "|" + hubId;
    if (!(key in index)) index[key] <- { count = 0, stops = [] };
    index[key].count++;
    if (("stationA" in line) && line.stationA != null) index[key].stops.append(line.stationA);
  }
  return index;
}

/* C23 : Modélisation physique du bassin de captage d'un arrêt de bus (rayon 3 tuiles).
 *
 * Un arrêt de bus OpenTTD possède un rayon de couverture de 3 tuiles, soit une empreinte
 * de 7x7 = 49 tuiles. Compte tenu du réseau viaire et des espaces publics, un arrêt couvre
 * physiquement au maximum ~20 maisons (ROAD_STOP_CATCHMENT_HOUSES = 20).
 * La part de captage d'une ville ayant H maisons est donc bornée par :
 *   pct = min(ROAD_PAX_CATCHMENT_SHARE_PCT, (ROAD_STOP_CATCHMENT_HOUSES * 100) / H)
 * Si H <= 0 ou non disponible, repli physique sur pop / 25.
 */
function OpexTownBusCatchment(town, marginalProd)
{
  if (marginalProd <= 0) return 0;
  local houses = ("houses" in town && town.houses > 0) ? town.houses : (town.pop / 25);
  if (houses <= 0) houses = 1;
  local pct = (ROAD_STOP_CATCHMENT_HOUSES * 100) / houses;
  if (pct > ROAD_PAX_CATCHMENT_SHARE_PCT) pct = ROAD_PAX_CATCHMENT_SHARE_PCT;
  if (pct < 1) pct = 1;
  local captured = (marginalProd * pct) / 100;
  return captured > 0 ? captured : 1;
}

/* Famille 1 : ville <-> ville, passagers. */
function OpexRoadPaxCandidates(catalog, lines, out, stats)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local roadLinesPerTown = [];
  for (local i = 0; i < n; i++) {
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
    produced.append(p);
    roadLinesPerTown.append(OpexTownRoadLineCount(lines, towns[i].tile));
  }
  for (local a = 0; a < n; a++) {
    local maxLinesA = 4 + (towns[a].pop / 300);
    if (roadLinesPerTown[a] >= maxLinesA) continue;
    for (local b = a + 1; b < n; b++) {
      local maxLinesB = 4 + (towns[b].pop / 300);
      if (roadLinesPerTown[b] >= maxLinesB) continue;
      if (OpexRoadPairServed(lines, towns[a].tile, towns[b].tile)) continue;
      local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (distance < ROAD_MIN_DISTANCE || distance > ROAD_MAX_DISTANCE) continue;
      stats.pairsInBand++;
      local marginalA = produced[a] - (roadLinesPerTown[a] * 40);
      if (marginalA < 25) marginalA = 25;
      local marginalB = produced[b] - (roadLinesPerTown[b] * 40);
      if (marginalB < 25) marginalB = 25;
      local capturedA = OpexTownBusCatchment(towns[a], marginalA);
      local capturedB = OpexTownBusCatchment(towns[b], marginalB);
      local monthly = capturedA + capturedB;
      if (monthly <= 0) { stats.noMonthly++; continue; }
      local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                              towns[a].id, towns[b].id, distance, monthly, stats);
      if (candidate != null) out.append(candidate);
    }
  }
}

/* Familles 2 et 3 : industrie -> industrie, et industrie -> ville.
 *
 * Le sens est ORIENTE (un producteur vers un accepteur) : contrairement au pax, rien ne revient.
 * C'est exactement la lecon du fret rail du 2026-08-28 -- poser OF_FULL_LOAD_ANY au puits d'une
 * ligne a sens unique y bloquait le convoi pour toujours -- et builder_road.nut applique la meme
 * regle aux camions.
 *
 * Aucune dilution de bassin n'est appliquee au producteur : une industrie produit depuis une seule
 * tuile, elle n'a pas la dilution geometrique d'une ville (cf. TOWN_CATCHMENT_SHARE_PCT). */
function OpexRoadFreightCandidates(catalog, lines, out, stats)
{
  local industries = catalog.industries;
  local towns = catalog.towns;
  local servedIndustry = [];
  for (local i = 0; i < industries.len(); i++) {
    servedIndustry.append(OpexOriginServed(lines, industries[i].tile, true));
  }
  local servedTown = [];
  for (local i = 0; i < towns.len(); i++) {
    servedTown.append(OpexOriginServed(lines, towns[i].tile, true));
  }

  /* L'acceptation d'une ville ne depend que du couple (ville, cargo) : la calculer une fois par
   * couple, et non par paire industrie-ville, evite de repayer AITile.GetCargoAcceptance pour
   * chaque producteur du meme cargo. Cle chaine plutot que table imbriquee : une seule table. */
  local acceptanceCache = {};
  /* Rayon d'une aire de chargement : c'est bien l'empreinte de la gare qu'on projette de poser,
   * pas un rayon arbitraire autour du centre administratif. Lu une fois, il ne change jamais. */
  local truckCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);

  foreach (cargo, sources in catalog.producers) {
    if (!(cargo in catalog.roadEngineByCargo)) { stats.noEngine++; continue; }
    /* Les passagers sont traites par la famille 1 : les inclure ici apparierait une industrie a
     * une ville pour un cargo qu'aucune industrie ne produit utilement en volume. */
    if (cargo == catalog.paxCargo) continue;
    local sinks = (cargo in catalog.acceptors) ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
      if (servedIndustry[si]) continue;
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if (monthly <= 0) { stats.noMonthly++; continue; }

      foreach (di in sinks) {
        if (di == si || servedIndustry[di]) continue;
        local distance = AIMap.DistanceManhattan(source.tile, industries[di].tile);
        if (distance < ROAD_MIN_DISTANCE || distance > ROAD_MAX_DISTANCE) continue;
        stats.pairsInBand++;
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                industries[di].tile, -1, -1, distance, monthly,
                                                stats, isTransformer);
        if (candidate != null) out.append(candidate);
      }

      for (local t = 0; t < towns.len(); t++) {
        if (servedTown[t]) continue;
        local distance = AIMap.DistanceManhattan(source.tile, towns[t].tile);
        if (distance < ROAD_MIN_DISTANCE || distance > ROAD_MAX_DISTANCE) continue;
        local key = t + "|" + cargo;
        local acceptance;
        if (key in acceptanceCache) {
          acceptance = acceptanceCache[key];
        } else {
          acceptance = AITile.GetCargoAcceptance(towns[t].tile, cargo, 1, 1, truckCoverage);
          acceptanceCache.rawset(key, acceptance);
        }
        if (acceptance < ROAD_ACCEPTANCE_MIN) { stats.townRejected++; continue; }
        stats.pairsInBand++;
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                towns[t].tile, -1, towns[t].id, distance, monthly,
                                                stats);
        if (candidate != null) out.append(candidate);
      }
    }
  }
}

/* Famille 4 (Transferts / Feeders) : ville satellite libre -> Gare Hub ou Aéroport existant.
 * Les bus acheminent les passagers vers le hub avec un ordre de transfert (OF_TRANSFER),
 * décuplant le flux capté par les lignes ferroviaires et aériennes longue distance. */
function OpexRoadFeederCandidates(catalog, lines, out, stats)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local towns = catalog.towns;
  local n = towns.len();

  /* air_fleet_probe : ZERO feeder n'a jamais ete bati (mesure du 2026-09-02, 5 graines x 3 ans),
   * alors que le mecanisme est cable de bout en bout. Impossible de dire si c'est la GENERATION
   * ou l'ELECTION qui echoue sans compter les deux. `feederHubs` et `feederCandidates` repondent
   * a la premiere question ; le panneau FE| de main.nut repond a la seconde. */
  if (!("feederHubs" in stats)) stats.feederHubs <- 0;
  if (!("feederCandidates" in stats)) stats.feederCandidates <- 0;

  local hubs = [];
  local hubMap = {};
  local feedersPerHub = {};

  foreach (line in lines) {
    if (!("mode" in line)) continue;
    local isFeeder = (("isFeeder" in line) && line.isFeeder) ||
                     (("purpose" in line) && line.purpose == "feeder");
    if (isFeeder) {
      local hId = ("hubStationId" in line) ? line.hubStationId : -1;
      if (hId < 0 && ("stationB" in line)) hId = AIStation.GetStationID(line.stationB);
      if (hId >= 0) {
        feedersPerHub[hId] <- (hId in feedersPerHub) ? feedersPerHub[hId] + 1 : 1;
      }
      continue;
    }

    if (FEEDER_UNLOCK) {
      /* C29.1 : Seuls l'aerien passagers et le rail passagers sont des hubs.
       * Le fret ferroviaire (charbon, minerai, etc.) et le bus ordinaire sont exclus. */
      if (line.mode == "air") {
        if (("cargo" in line) && line.cargo != cargo) continue;
      } else if (line.mode == "rail") {
        if (!("cargo" in line) || line.cargo != cargo) continue;
      } else {
        continue;
      }
    } else {
      if (line.mode != "rail" && line.mode != "air") continue;
    }

    local stA = OpexLineStationId(line, "A");
    local stB = OpexLineStationId(line, "B");
    local rev = ("predRevenue" in line) ? line.predRevenue : (("predicted" in line) ? line.predicted : 0);
    local carried = ("predCarried" in line) ? line.predCarried : 0;

    local ends = [ { st = stA, tile = line.stationA }, { st = stB, tile = line.stationB } ];
    foreach (end in ends) {
      local st = end.st;
      if (st < 0) continue;
      if (!(st in hubMap)) {
        hubMap[st] <- {
          stationId = st,
          tile = end.tile,
          /* C31.3 : la ville du hub ne depend pas de la ville candidate. La resoudre ici, une fois
           * par hub, au lieu d'un AITile.GetClosestTown(hub.tile) par couple (ville, hub). */
          townId = AITile.GetClosestTown(end.tile),
          mode = line.mode,
          totalRevenue = 0,
          totalCarried = 0,
          lineCount = 0,
          airLines = 0,
          railLines = 0,
          totalAirRevenue = 0,
          totalAirCarried = 0,
          totalRailRevenue = 0,
          totalRailCarried = 0,
        };
      }
      local h = hubMap[st];
      if (rev > 0) h.totalRevenue += rev;
      if (carried > 0) h.totalCarried += carried;
      h.lineCount++;
      if (line.mode == "air") {
        h.airLines++;
        if (rev > 0) h.totalAirRevenue += rev;
        if (carried > 0) h.totalAirCarried += carried;
        h.mode = "air";
      } else if (line.mode == "rail") {
        h.railLines++;
        if (rev > 0) h.totalRailRevenue += rev;
        if (carried > 0) h.totalRailCarried += carried;
      }
    }
  }

  foreach (st, h in hubMap) {
    h.existingFeeders <- (st in feedersPerHub) ? feedersPerHub[st] : 0;
    hubs.append(h);
  }
  stats.feederHubs = hubs.len();
  if (hubs.len() == 0) return;

  /* C31.3 : un seul parcours des lignes pour tout le double balayage ville x hub ci-dessous. */
  local feederIndex = OpexBuildFeederIndex(lines);

  for (local i = 0; i < n; i++) {
    if (!FEEDER_UNLOCK && OpexOriginServed(lines, towns[i].tile, true)) continue;
    local pop = towns[i].pop;
    if (pop < 200) continue;
    local produced = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (produced <= 0) continue;

    /* C31.3 : towns[i].id EST l'identifiant de la ville (catalog.nut garde AITown.GetLocation),
     * donc aucun AITile.GetClosestTown n'est necessaire de ce cote non plus. */
    local townKeyPrefix = towns[i].id + "|";

    foreach (hub in hubs) {
      local isHubTown = (towns[i].id == hub.townId);
      local distance = AIMap.DistanceManhattan(towns[i].tile, hub.tile);

      /* Distance :
       * - Pour la ville du hub : l'aéroport/gare est implanté dans la ville (distance <= 16 tuiles).
       * - Pour les villes satellites : bande interurbaine standard 5..25 tuiles (ROAD_MAX_DISTANCE). */
      if (isHubTown) {
        if (distance > 16) continue;
      } else {
        if (distance < ROAD_MIN_DISTANCE || distance > ROAD_MAX_DISTANCE) continue;
      }

      /* Nombre de feeders autorisés pour cette ville :
       * - Pour la ville du hub sous FEEDER_TOWN_COVERAGE (C29.4) : jusqu'à ceil(maisons / ROAD_STOP_CATCHMENT_HOUSES)
       *   arrêts de rabattement séparés (plafonné à 4), sur le modèle de couverture intégrale AAAHogEx.
       * - Pour une ville satellite : exactement 1 feeder (slot 0) pour rabattre le satellite vers le hub. */
      local feederEntry = ((townKeyPrefix + hub.stationId) in feederIndex)
          ? feederIndex[townKeyPrefix + hub.stationId] : null;
      local existingCount = (feederEntry != null) ? feederEntry.count : 0;
      local maxFeeders = 1;
      if (isHubTown && FEEDER_TOWN_COVERAGE) {
        local houses = ("houses" in towns[i] && towns[i].houses > 0) ? towns[i].houses : (towns[i].pop / 25);
        maxFeeders = OpexCeilDiv(houses, ROAD_STOP_CATCHMENT_HOUSES);
        if (maxFeeders > 4) maxFeeders = 4;
        if (maxFeeders < 1) maxFeeders = 1;
      }
      if (FEEDER_UNLOCK && existingCount >= maxFeeders) continue;

      stats.pairsInBand++;
      /* Part de la production restant à capter après les arrêts déjà construits */
      local houses = ("houses" in towns[i] && towns[i].houses > 0) ? towns[i].houses : (towns[i].pop / 25);
      if (houses <= 0) houses = 1;
      local remainingHouses = houses - (existingCount * ROAD_STOP_CATCHMENT_HOUSES);
      if (remainingHouses < 1) remainingHouses = 1;
      local marginalProd = (produced * remainingHouses) / houses;
      local monthly = OpexTownBusCatchment(towns[i], marginalProd);
      if (monthly <= 0) continue;

      /* Plancher de distance pour le modèle économique routier (distance >= 5 tuiles) */
      local candDist = distance < ROAD_MIN_DISTANCE ? ROAD_MIN_DISTANCE : distance;
      local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, towns[i].tile, hub.tile,
                                              towns[i].id, -1, candDist, monthly, stats, false, true);
      if (candidate != null) {
        stats.feederCandidates++;
        candidate.isFeeder <- true;
        candidate.hubStationId <- hub.stationId;
        candidate.hubMode <- hub.mode;
        candidate.feederSlot <- existingCount;
        candidate.isHubTown <- isHubTown;

        /* Collecter les gares pour garantir la séparation spatiale >= 6 tuiles (modèle AAAHogEx) :
         * - Pour la ville du hub : TOUJOURS exclure l'emplacement du hub (hub.tile) pour que
         *   l'arrêt de bus de quartier soit posé à >= 6 tuiles de l'aéroport/gare et capte
         *   un quartier différent !
         * - Exclure également les arrêts de bus déjà construits dans cette ville vers ce hub. */
        local existingStops = [];
        if (isHubTown) {
          existingStops.append(hub.tile);
        }
        /* C31.3 : les arrets deja poses de ce couple (ville, hub) viennent de l'index, qui les a
         * collectes dans le meme parcours unique que les compteurs. */
        if (feederEntry != null) {
          foreach (stopTile in feederEntry.stops) existingStops.append(stopTile);
        }
        candidate.existingStops <- existingStops;

        if (FEEDER_PRICING) {
          /* C29.3 : Pricing economique physique du feeder selon le rendement par passager du hub.
           * Valeur = passagers apportes par le feeder * (revenu hub / passagers hub).
           * Plafonne a 78 % (100 - TOWN_CATCHMENT_SHARE_PCT) du revenu total de la ligne du hub. */
          local hubRev = 0;
          local hubCarried = 0;
          if (("airLines" in hub) && hub.airLines > 0) {
            hubRev = hub.totalAirRevenue;
            hubCarried = hub.totalAirCarried;
          } else if (("railLines" in hub) && hub.railLines > 0) {
            hubRev = hub.totalRailRevenue;
            hubCarried = hub.totalRailCarried;
          } else if (("lineCount" in hub) && hub.lineCount > 0) {
            hubRev = hub.totalRevenue;
            hubCarried = hub.totalCarried;
          }

          if (hubRev > 0) {
            local feederPax = (("carried" in candidate) && candidate.carried > 0) ? candidate.carried : monthly;
            local maxSharePct = 100 - TOWN_CATCHMENT_SHARE_PCT; /* 78 % */
            local networkRev = 0;

            if (hubCarried > 0) {
              /* Rendement physique : passagers feeder * rendement unitaire hub */
              networkRev = (feederPax * hubRev) / hubCarried;
              local maxRev = (hubRev * maxSharePct) / 100;
              if (networkRev > maxRev) networkRev = maxRev;
            } else {
              /* Repli si hubCarried n'est pas renseigne : part du bassin communal */
              local hubPop = AITown.IsValidTown(hub.townId) ? AITown.GetPopulation(hub.townId) : 0;
              local sharePct = maxSharePct;
              if (hubPop > 0) {
                local hubCapturedPax = (hubPop * TOWN_CATCHMENT_SHARE_PCT) / 100;
                if (hubCapturedPax > 0) {
                  sharePct = (feederPax * 100) / hubCapturedPax;
                  if (sharePct > maxSharePct) sharePct = maxSharePct;
                  if (sharePct < 1) sharePct = 1;
                }
              }
              networkRev = (hubRev * sharePct) / 100;
            }

            /* Reserve #2 : Prevention du double compte / repartition entre feeders sur le meme hub */
            local k = ("existingFeeders" in hub) ? hub.existingFeeders : 0;
            networkRev = networkRev / (k + 1);

            /* Marge operationnelle reseau (~80 % pour l'aerien/rail) */
            local networkProfit = (networkRev * 80) / 100;

            candidate.networkRevenue <- networkRev;
            candidate.networkProfit <- networkProfit;
            candidate.feederBonus <- networkProfit;
            local totalProfit = candidate.profitAnnual + networkProfit;
            if (totalProfit <= 0) continue;
            candidate.profitAnnual = totalProfit;
            candidate.revenueAnnual += networkRev;
            candidate.roi = candidate.capital > 0 ? (totalProfit * 1000) / candidate.capital : candidate.roi;
            candidate.ratio = candidate.iterations > 0 ? (totalProfit * 1000) / candidate.iterations : candidate.ratio;
          } else {
            /* Repli historique si aucun revenu de ligne n'est encore disponible sur le hub */
            if (candidate.profitAnnual <= 0) continue;
            candidate.roi = (candidate.roi * 160) / 100;
            candidate.ratio = (candidate.ratio * 160) / 100;
            candidate.feederBonus <- 160;
            if (!CLEAN_DENSITY_SCORE) {
              candidate.profitAnnual = (candidate.profitAnnual * 160) / 100;
              candidate.revenueAnnual = (candidate.revenueAnnual * 160) / 100;
            }
          }
        } else {
          /* Bonus ROI forfaitaire historique (+60 %) */
          if (candidate.profitAnnual <= 0) continue;
          candidate.roi = (candidate.roi * 160) / 100;
          candidate.ratio = (candidate.ratio * 160) / 100;
          candidate.feederBonus <- 160;
          if (!CLEAN_DENSITY_SCORE) {
            candidate.profitAnnual = (candidate.profitAnnual * 160) / 100;
            candidate.revenueAnnual = (candidate.revenueAnnual * 160) / 100;
          }
        }
        out.append(candidate);
      }
    }
  }
}

/* Classement routier complet. Rendu a part de celui du rail : les deux ne partagent ni leur unite
 * de cout (cf. ROAD_PLAN_ITERATIONS_BASE) ni leur phase de construction. */
function OpexBuildRoadCandidates(catalog, budget, lines)
{
  local all = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
    economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
    feederHubs = 0, feederCandidates = 0,
  };
  if (catalog.roadType < 0) return { all = 0, best = [], stats = stats, opcodes = 0 };

  budget.begin();
  OpexRoadPaxCandidates(catalog, lines, all, stats);
  OpexRoadFreightCandidates(catalog, lines, all, stats);
  /* Les feeders sont exclusivement construits par leur tâche dédiée _tryBuildFeeders (main.nut:1422).
   * Ne pas les inclure ici empêche toute collision d'OD et évite d'évincer les lignes aériennes
   * lors de l'arbitrage modal OpexProjectRemember / OpexProjectModeBetter. */
  local ops = budget.end("cand_road");

  if (DECISION_LOG) {
    OpexDecide("VIVIER_GEN", "mode=road produced=" + stats.pairsInBand + " kept=" + all.len());
    if (stats.noMonthly > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_no_monthly n=" + stats.noMonthly);
    }
    if (stats.noEngine > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_no_engine n=" + stats.noEngine);
    }
    if (stats.townRejected > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_town_rejected n=" + stats.townRejected);
    }
    if (stats.economicsUnavailable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_economics_unavailable n=" + stats.economicsUnavailable);
    }
    if (stats.profitTooLow > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_profit_too_low n=" + stats.profitTooLow);
    }
  }

  /* Le cout de CETTE annee, pas le cumul : budget.get() totalise depuis le debut de la partie, et
   * c'est le debit annuel qui dit si la generation routiere merite sa place. Il est paye meme les
   * annees ou rien n'est bati, donc le panneau RN le porte sans condition (main.nut). */
  return { all = all.len(), candidates = all, best = OpexTopK(all, ROAD_TOP_K),
           stats = stats, opcodes = ops };
}

/* Rehausse la reputation municipale aupres de l'autorite locale en plantant des arbres.
 * Cout : ~40 £ par arbre, gain : +7 points de note par arbre plante (plafond standard +220).
 * Empeche le blocage ERR_LOCAL_AUTHORITY_REFUSES lors des constructions urbaines. */
function OpexBoostTownRating(townId, targetRating = 700, maxTrees = 35)
{
  if (!AITown.IsValidTown(townId)) return;
  /* ⚠️ AITown.GetRating rend un ENUM de 0 a 8 (script_town.hpp:83 : NONE, APPALLING, VERY_POOR,
   * POOR, MEDIOCRE, GOOD, VERY_GOOD, EXCELLENT, OUTSTANDING), PAS la note brute -1000..1000.
   * Le garde historique comparait cet enum aux `targetRating` 100/700/800 passes par les
   * appelants : la condition etait donc TOUJOURS fausse et la fonction plantait `maxTrees`
   * arbres a chaque appel, quelle que soit la note deja acquise.
   *
   * Planter ne sert qu'en dessous de RATING_TREE_MAXIMUM = 220 en note brute : tree_cmd.cpp:591
   * appelle ChangeTownRating(t, +7, 220), qui ne monte la note que `if (rating < max)`. Au-dessus,
   * chaque arbre est une depense a rendement strictement nul. 220 tombe juste au-dessus de
   * l'echelon MEDIOCRE (note brute <= 200), d'ou le plafond ci-dessous.
   *
   * `targetRating` n'est plus lu : aucun appelant ne peut exprimer un seuil utile sur cette
   * echelle. Le parametre reste dans la signature pour ne pas toucher aux quatre sites d'appel.
   *
   * Effet au reglage par defaut : AUCUN. La plantation preventive est coupee (tree_planting = 0)
   * et le seul appel vivant est le recours reactif de builder_air.nut, ou la ville vient
   * precisement de refuser -- donc note brute <= -200, tres en dessous du plafond. Ce correctif
   * repare la plantation preventive pour le jour ou on la remesure : c'est le garde mort qui
   * explique mecaniquement son -22,1 % de valeur (info.nut, tree_planting). */
  local currentRating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
  if (currentRating != AITown.TOWN_RATING_NONE &&
      currentRating > AITown.TOWN_RATING_MEDIOCRE) return;

  local center = AITown.GetLocation(townId);
  local planted = 0;
  local radius = 7;

  for (local dx = -radius; dx <= radius && planted < maxTrees; dx++) {
    for (local dy = -radius; dy <= radius && planted < maxTrees; dy++) {
      local tile = center + AIMap.GetTileIndex(dx, dy);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != townId) continue;
      if (AITile.IsBuildable(tile)) {
        if (AITile.PlantTree(tile)) {
          planted++;
        }
      }
    }
  }
}
