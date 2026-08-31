/* Etages 1 et 2 : ce que rapporte un candidat, et ce qu'il coute en opcodes.
 *
 * Etage 1 -- le profit attendu. Changement de fond par rapport a TrainLineAI : la variable n'est
 * plus population_a * population_b / distance (un proxy) mais la PRODUCTION reelle multipliee par
 * le revenu unitaire reel (AICargo.GetCargoIncome), c'est-a-dire la grandeur physique.
 *
 * Etage 2 -- le cout en opcodes attendu. C'est l'etage que personne n'a, et le denominateur du
 * classement interne. Pour l'instant c'est un modele lineaire grossier ; il sera remplace par une
 * regression ajustee sur les campagnes, ou le nombre reel d'iterations d'A* par ligne est connu.
 *
 * Le classement se fait sur le RAPPORT revenu/opcode, jamais sur le revenu seul : le budget est un
 * debit non reportable, la seule question est de savoir a quel candidat va le prochain tick.
 */

/* Distance minimale : sous 25 tuiles le profit MEDIAN mesure est negatif (-296 626 sur 20 lignes
 * de la campagne v3). Ce n'est pas une precaution, c'est une mesure. */
const MIN_DISTANCE = 25;
const MAX_DISTANCE = 200;
/* H2 : bande courte depuis une gare deja a nous. MIN_DISTANCE inchange
 * pour les lignes neuves. join_max_distance > 0 bride aussi cette bande. */
const JOIN_PLACE_MAX = 75;

/* Nombre de candidats retenus en tete de classement. Au-dela, on ne consomme jamais. */
const TOP_K = 20;

/* Plancher de ratio (profit annuel attendu par millier d'iterations). Mesure du 2026-08-28,
 * graine 42/20 ans, apres l'exclusion d'origine ci-dessous (OpexOriginServed) : une fois les
 * bonnes origines epuisees, le TOP_K se remplit de candidats de moins en moins bons plutot que de
 * rester vide -- et certains, lointains, ont un ratio predit ecrase (15, 218, 275) bien en dessous
 * du plancher empirique observe sur cette meme campagne AVANT la correction (1278, jamais franchi
 * a la baisse quand le classement avait assez de bons candidats pour ne jamais descendre aussi
 * bas). Sans ce plancher, l'exclusion d'origine seule degradait le resultat (company_value
 * 2 067 089 contre 2 413 587 avant, emprunt non rembourse) en laissant l'IA s'engager sur ces
 * candidats marginaux -- avec MIN_RATIO=500, meme graine/duree : 17 lignes (contre 15),
 * company_value 2 716 098 (+12,5 % vs avant tout correctif), emprunt rembourse. Ce plancher ne
 * remplace pas la politique d'abandon : il coupe les candidats structurellement mauvais AVANT la
 * tentative, pas ceux dont le cout reel derape en cours de route (observe separement : une
 * tentative a 70 tuiles a consomme 60 000 iterations pour un profit predit de 3 149 avant d'etre
 * abandonnee, cf. docs/opexai_croissance.md). Il sert aussi de cout d'opportunite du dernier
 * candidat : attendre le classement annuel suivant vaut au moins ce rapport acceptable. */
const MIN_RATIO = 500;

/* Item 7 : echantillon des paires rejetees pour profit predit <= 0. Les moins negatives
 * d'abord -- si celles-la sont vraiment non rentables, le filtre est calibre ; si elles
 * rapportent, le modele sous-estime une famille que la calibration n'a jamais vue.
 * 12 tiennent dans leftover-cash : tropClose et le capital en eliment encore. */
const PROBE_STASH_K = 12;
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
  /* Au-dela du dernier noeud on prolonge la derniere pente : la vraie courbe monte plus vite
   * encore, donc c'est une SOUS-estimation du cout -- prudent dans le mauvais sens, a surveiller. */
  local last = n - 1;
  local slope = (knots[last] - knots[last - 1])
              / (KNOT_DISTANCE[last] - KNOT_DISTANCE[last - 1]);
  return knots[last] + slope * (distance - KNOT_DISTANCE[last]);
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

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats)
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
  /* Sous MIN_RATIO, le candidat coute structurellement plus qu'il ne rapporte compare au reste du
   * classement -- ne merite pas d'occuper une place dans le TOP_K meme s'il est techniquement
   * profitable (economics.profitAnnual > 0 ne suffit pas, voir MIN_RATIO ci-dessus). */
  if (opcodeRatio < MIN_RATIO) {
    stats.ratioTooLow++;
    return null;
  }

  /* Score composite : priorise le fort ROI et le retour sur investissement rapide (cash turnover).
   * Une rotation rapide (oneWayDays court) reinjecte du cash rapidement pour financer les lignes suivantes. */
  local turnoverBonus = 100;
  if (economics.oneWayDays <= 12) turnoverBonus = 130;
  else if (economics.oneWayDays <= 25) turnoverBonus = 115;
  else if (economics.oneWayDays <= 45) turnoverBonus = 100;
  else turnoverBonus = 75;

  local adjustedRoi = (economics.roi * turnoverBonus) / 100;
  local ratio = opcodeRatio + (adjustedRoi * 15);

  stats.accepted++;
  return {
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
    roi = economics.roi,
    profitAnnual = economics.profitAnnual,
    /* Detail du calcul, garde pour l'instrumentation predit-vs-reel (cf. main.nut). */
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = iterations,
    ratio = ratio,
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
    kind = kind, cargo = cargo, originServed = originServed,
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
    if (!includeRoad && ("mode" in line) && line.mode == "road") continue;
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
 * gares DISTINCTES la servent. Les lignes routieres sont ignorees, comme dans les deux autres
 * filets rail : une desserte de bus de 12 tuiles n'epuise pas une ville. */
function OpexOriginService(lines, tile)
{
  local found = null;
  foreach (line in lines) {
    if (("mode" in line) && line.mode == "road") continue;
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
    produced.append(AITown.GetLastMonthProduction(towns[i].id, cargo));
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
    if (!(cargo in catalog.acceptors)) continue;
    local sinks = catalog.acceptors[cargo];
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
        local originServed = ss != null || sd != null;
        if (originServed) stats.pairsOneServed++;
        /* Meme double comptage qu'en pax quand la SOURCE est deja servie -- et meme verdict :
         * mesure le 2026-08-29, il ne se distingue pas du bruit une fois la distance neutralisee.
         * Voir le commentaire detaille dans OpexPaxCandidates ci-dessus. */
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                            industries[di].tile, monthly, originServed, stats);
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
  return { all = all.len(), best = best, bands = OpexBands(all), stats = stats };
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
 * Creneau volontairement DISJOINT de celui du rail : 5 a 25 tuiles, la bande que MIN_DISTANCE = 25
 * refuse structurellement au rail parce que le profit median y est negatif POUR LE RAIL (une gare,
 * une voie et une locomotive ne s'amortissent pas sur 15 tuiles). Un camion, lui, n'a ni voie ni
 * signaux : son capital est d'un ordre de grandeur en dessous, donc le meme volume sur la meme
 * distance peut le rentabiliser. Les deux modes ne se disputent donc jamais la meme PAIRE ; ils
 * peuvent en revanche se disputer la meme ORIGINE, et c'est le rail qui sert en premier
 * (main.nut : _tryBuildRoads est appele APRES _tryBuild, et exclut toute origine deja servie).
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

/* Le classement routier est SEPARE de celui du rail (TOP_K), et plus court : une tentative
 * routiere est bornee et bon marche, mais chaque ligne consomme de la tresorerie et un couple
 * d'origines. Douze candidats couvrent largement les ROAD_MAX_NEW_LINES_PER_YEAR retenus. */
const ROAD_TOP_K = 12;

/* Plancher de profit annuel attendu. Ce n'est PAS l'equivalent de MIN_RATIO (un cout d'opportunite
 * en opcodes) mais un cout d'opportunite en TRESORERIE et en origines : une ligne routiere qui
 * rapporte quelques centaines par an immobilise une ville ou une industrie que le rail aurait pu
 * prendre, et ajoute un vehicule a surveiller. Valeur ARBITRAIRE, choisie a l'ordre de grandeur du
 * profit d'une liaison bus courte sur une petite ville (~1 500/an au modele) : elle laisse passer
 * le fret, qui la depasse d'un ou deux ordres de grandeur, et coupe la desserte passagers la plus
 * marginale. Mesure 2026-08-30 (docs/opex_road_predict_vs_actual.json) : 12 pax, mediane
 * reel/predit 3,91 ; fret temoin 1,21. Ne PAS baisser ce plancher pour « laisser passer le pax
 * sous-estime » : le 22 % de bassin est aussi le rail. */
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
 * BASE impliquee plan seul : -9. TRACEX 70-107 k. Le build (mediane 287 k) n'est pas le
 * denominateur du rail (A*). Un ratio route sur le plan reel (68 k-710 k) ecrase le rail
 * (mediane 5 040, MIN_RATIO 500) : ne PAS unifier les classements. BASE reste 20, intra-route
 * seulement. Le rail d'abord est une decision de valeur (docs/opexai_route.md §2), pas d'opcode. */
const ROAD_PLAN_ITERATIONS_BASE = 20;

function OpexRoadIterations(distance)
{
  return ROAD_PLAN_ITERATIONS_BASE + distance;
}

/* Un candidat routier porte les memes champs que son homologue rail (le constructeur de ligne, le
 * rapport annuel et la mise au rebut sont communs), plus ce qu'il faut pour retrouver les sites
 * d'arret : le role de chaque extremite (ville ou industrie) et, pour une ville, son identifiant. */
function OpexMakeRoadCandidate(catalog, kind, cargo, src, dst, srcTown, dstTown, distance,
                               monthly, stats)
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
  if (economics.profitAnnual < ROAD_MIN_PROFIT_ANNUAL) {
    stats.profitTooLow++;
    return null;
  }
  local iterations = OpexRoadIterations(distance);
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

/* Famille 1 : ville <-> ville, passagers. */
function OpexRoadPaxCandidates(catalog, lines, out, stats)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  for (local i = 0; i < n; i++) {
    produced.append(AITown.GetLastMonthProduction(towns[i].id, cargo));
    served.append(OpexOriginServed(lines, towns[i].tile, true));
  }
  for (local a = 0; a < n; a++) {
    if (served[a]) continue;
    for (local b = a + 1; b < n; b++) {
      if (served[b]) continue;
      local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (distance < ROAD_MIN_DISTANCE || distance > ROAD_MAX_DISTANCE) continue;
      stats.pairsInBand++;
      /* Meme lecture que le rail : les deux sens transportent chacun la production de LEUR
       * origine, donc le debit utile est la somme, corrigee de la part du bassin d'une seule gare
       * (ROAD_PAX_CATCHMENT_SHARE_PCT). Le repli 22 reproduit le calibrage rail ; un reglage
       * route explicite ne doit jamais contaminer le rail ou le fret. */
      local monthly = ((produced[a] + produced[b]) * ROAD_PAX_CATCHMENT_SHARE_PCT) / 100;
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
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                industries[di].tile, -1, -1, distance, monthly,
                                                stats);
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

/* Classement routier complet. Rendu a part de celui du rail : les deux ne partagent ni leur unite
 * de cout (cf. ROAD_PLAN_ITERATIONS_BASE) ni leur phase de construction. */
function OpexBuildRoadCandidates(catalog, budget, lines)
{
  local all = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
    economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
  };
  if (catalog.roadType < 0) return { all = 0, best = [], stats = stats, opcodes = 0 };

  budget.begin();
  OpexRoadPaxCandidates(catalog, lines, all, stats);
  OpexRoadFreightCandidates(catalog, lines, all, stats);
  local ops = budget.end("cand_road");

  /* Le cout de CETTE annee, pas le cumul : budget.get() totalise depuis le debut de la partie, et
   * c'est le debit annuel qui dit si la generation routiere merite sa place. Il est paye meme les
   * annees ou rien n'est bati, donc le panneau RN le porte sans condition (main.nut). */
  return { all = all.len(), best = OpexTopK(all, ROAD_TOP_K), stats = stats, opcodes = ops };
}

/* Rehausse la reputation municipale aupres de l'autorite locale en plantant des arbres.
 * Cout : ~40 £ par arbre, gain : +7 points de note par arbre plante (plafond standard +220).
 * Empeche le blocage ERR_LOCAL_AUTHORITY_REFUSES lors des constructions urbaines. */
function OpexBoostTownRating(townId, targetRating = 100, maxTrees = 20)
{
  if (!AITown.IsValidTown(townId)) return;
  local currentRating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
  if (currentRating >= targetRating) return;

  local center = AITown.GetLocation(townId);
  local planted = 0;
  local radius = 7;

  for (local dx = -radius; dx <= radius && planted < maxTrees; dx++) {
    for (local dy = -radius; dy <= radius && planted < maxTrees; dy++) {
      local tile = center + AIMap.GetTileIndex(dx, dy);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITown.GetNearestTown(tile) != townId) continue;
      if (AITile.IsBuildable(tile)) {
        if (AITile.PlantTree(tile)) {
          planted++;
        }
      }
    }
  }
}
