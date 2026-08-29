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

/* Etage 2 : le cout, AJUSTE sur la campagne v3 (1997 lignes reelles, OpenTTD 13.4).
 *
 * La grandeur utile n'est pas "iterations d'une tentative" mais "iterations par ligne REUSSIE",
 * qui absorbe l'echec : iterations_moyennes / P(construite). Elle explose bien plus vite que
 * lineairement -- une loi de puissance en d^2,67 l'approche a 0,82-1,15x pres.
 *
 * On garde une table de noeuds avec interpolation lineaire plutot que la loi de puissance :
 * exacte aux noeuds, entierement en entiers, aucune fonction mathematique flottante en Squirrel.
 *
 *   distance :    23     33     48     63     81    105     150
 *   iterations:  371    673   2188   4066   7745  15308   53951
 *
 * Consequence mesuree, et contre-intuitive : le rapport profit/iteration culmine vers 48-63
 * tuiles (553 puis 456), pas au plus court (negatif) ni au plus rentable en valeur absolue
 * (74 seulement a 150 tuiles). Le classement par rapport choisit donc des lignes MOYENNES.
 */
KNOT_DISTANCE <- [23, 33, 48, 63, 81, 105, 150];
KNOT_ITERATIONS <- [371, 673, 2188, 4066, 7745, 15308, 53951];

function OpexRailIterations(distance)
{
  local n = KNOT_DISTANCE.len();
  if (distance <= KNOT_DISTANCE[0]) return KNOT_ITERATIONS[0];
  for (local i = 1; i < n; i++) {
    if (distance <= KNOT_DISTANCE[i]) {
      local d0 = KNOT_DISTANCE[i - 1];
      local d1 = KNOT_DISTANCE[i];
      local v0 = KNOT_ITERATIONS[i - 1];
      local v1 = KNOT_ITERATIONS[i];
      return v0 + ((v1 - v0) * (distance - d0)) / (d1 - d0);
    }
  }
  /* Au-dela du dernier noeud on prolonge la derniere pente : la vraie courbe monte plus vite
   * encore, donc c'est une SOUS-estimation du cout -- prudent dans le mauvais sens, a surveiller. */
  local last = n - 1;
  local slope = (KNOT_ITERATIONS[last] - KNOT_ITERATIONS[last - 1])
              / (KNOT_DISTANCE[last] - KNOT_DISTANCE[last - 1]);
  return KNOT_ITERATIONS[last] + slope * (distance - KNOT_DISTANCE[last]);
}

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats)
{
  if (monthly <= 0) {
    stats.noMonthly++;
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
  /* Un candidat dont le profit annuel attendu est negatif ne merite AUCUN opcode. */
  if (economics.profitAnnual <= 0) {
    stats.profitNonPositive++;
    return null;
  }

  local iterations = OpexRailIterations(distance);
  local ratio = (economics.profitAnnual * 1000) / iterations;
  /* Sous MIN_RATIO, le candidat coute structurellement plus qu'il ne rapporte compare au reste du
   * classement -- ne merite pas d'occuper une place dans le TOP_K meme s'il est techniquement
   * profitable (economics.profitAnnual > 0 ne suffit pas, voir MIN_RATIO ci-dessus). */
  if (ratio < MIN_RATIO) {
    stats.ratioTooLow++;
    return null;
  }
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
    profitAnnual = economics.profitAnnual,
    /* Detail du calcul, garde pour l'instrumentation predit-vs-reel (cf. main.nut). */
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = iterations,
    /* Le classement interne : profit annuel attendu par millier d'iterations d'A* attendues.
     * On divise par les iterations et non par les opcodes : c'est le meme classement (2700
     * opcodes par iteration, un facteur constant) mais les entiers restent petits et la valeur
     * est directement comparable au "profit par iteration" mesure sur les campagnes. Deja calcule
     * ci-dessus pour le test MIN_RATIO -- repris tel quel, pas recalcule. */
    ratio = ratio,
  };
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
      local monthly = ((produced[a] + produced[b]) * TOWN_CATCHMENT_SHARE_PCT) / 100;
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
      if (candidate != null) out.append(candidate);
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
  foreach (cargo, sources in catalog.producers) {
    if (!(cargo in catalog.acceptors)) continue;
    local sinks = catalog.acceptors[cargo];
    foreach (si in sources) {
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      foreach (di in sinks) {
        if (di == si) continue;
        stats.pairsTotal++;
        local ss = served[si];
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
        if (candidate != null) out.append(candidate);
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
    noMonthly = 0,
    distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
    profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
  };

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
 * marginale. A trancher au banc, pas par le raisonnement. */
const ROAD_MIN_PROFIT_ANNUAL = 1000;

/* Seuil d'acceptation d'une ville pour un cargo. AITile.GetCargoAcceptance rend une acceptation en
 * huitiemes d'unite ; le moteur exige 8 (une unite pleine) pour livrer quoi que ce soit. En dessous
 * la gare accepterait le cargo a l'affichage sans que la livraison paie. */
const ROAD_ACCEPTANCE_MIN = 8;

/* Cout en "iterations equivalentes" d'une tentative routiere, pour rester dans la meme unite que
 * le rail (1 iteration ~ 2 700 opcodes).
 *
 * ⚠️ NON CALIBRE. La seule mesure disponible est indirecte : 171 356 opcodes pour le balayage
 * complet de toutes les paires de la carte par la v1 (docs/opexai_mode_route), soit ~63 iterations
 * pour un travail bien plus large que le plan d'UNE paire fait ici. La forme (une base plus la
 * longueur du trace, qui borne le nombre d'aretes revalidees sous AITestMode) est defendable, les
 * coefficients ne le sont pas. Consequence assumee : ce nombre ne sert QU'A classer les candidats
 * routiers ENTRE EUX, jamais a les comparer au rail -- une comparaison inter-modes exigerait
 * d'abord de mesurer le cout reel d'un plan routier, ce que le panneau RB pose desormais chaque
 * tentative (main.nut) pour permettre cette calibration. */
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
       * (TOWN_CATCHMENT_SHARE_PCT, calibre sur des lignes reelles). */
      local monthly = ((produced[a] + produced[b]) * TOWN_CATCHMENT_SHARE_PCT) / 100;
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
