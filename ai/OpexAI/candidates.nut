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

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly)
{
  if (monthly <= 0) return null;
  local distance = AIMap.DistanceManhattan(srcTile, dstTile);
  if (distance < MIN_DISTANCE || distance > MAX_DISTANCE) return null;

  local economics = OpexLineEconomics(catalog, cargo, distance, monthly);
  if (economics == null) return null;
  /* Un candidat dont le profit annuel attendu est negatif ne merite AUCUN opcode. */
  if (economics.profitAnnual <= 0) return null;

  local iterations = OpexRailIterations(distance);
  local ratio = (economics.profitAnnual * 1000) / iterations;
  /* Sous MIN_RATIO, le candidat coute structurellement plus qu'il ne rapporte compare au reste du
   * classement -- ne merite pas d'occuper une place dans le TOP_K meme s'il est techniquement
   * profitable (economics.profitAnnual > 0 ne suffit pas, voir MIN_RATIO ci-dessus). */
  if (ratio < MIN_RATIO) return null;
  return {
    kind = kind,            // "pax" ou "freight"
    cargo = cargo,
    src = srcTile,
    dst = dstTile,
    distance = distance,
    monthly = monthly,
    trains = economics.trains,
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
 * fonctions de ce fichier ne s'executent qu'apres que main.nut a fini de se charger). _tooClose
 * reste utile pour son second test, MIN_SEPARATION, qui depend de la gare BATIE et ne peut pas se
 * calculer a la generation. */
function OpexOriginServed(lines, tile)
{
  foreach (line in lines) {
    if (AIMap.DistanceManhattan(tile, line.originA) < ORIGIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(tile, line.originB) < ORIGIN_SEPARATION) return true;
  }
  return false;
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
function OpexPaxCandidates(catalog, lines, out)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  for (local i = 0; i < n; i++) {
    produced.append(AITown.GetLastMonthProduction(towns[i].id, cargo));
  }
  for (local a = 0; a < n; a++) {
    if (OpexOriginServed(lines, towns[a].tile)) continue;
    for (local b = a + 1; b < n; b++) {
      if (OpexOriginServed(lines, towns[b].tile)) continue;
      /* Une ligne dessert les deux sens, et chaque sens transporte la production de SON
       * origine : le debit utile est la somme, pas le minimum. On ignore encore la croissance de
       * la ville que la desserte provoque (sous-estimation non calibree, plus petite que le
       * facteur ci-dessus d'apres la mesure). */
      local monthly = ((produced[a] + produced[b]) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile, monthly);
      if (candidate != null) out.append(candidate);
    }
  }
}

/* Industries : on n'apparie que des couples producteur/accepteur du MEME cargo, ce qui garde
 * l'etage 1 lineaire en nombre d'industries plutot que quadratique sur tout le catalogue. */
function OpexFreightCandidates(catalog, lines, out)
{
  local industries = catalog.industries;
  foreach (cargo, sources in catalog.producers) {
    if (!(cargo in catalog.acceptors)) continue;
    local sinks = catalog.acceptors[cargo];
    foreach (si in sources) {
      local source = industries[si];
      if (OpexOriginServed(lines, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if (monthly <= 0) continue;
      foreach (di in sinks) {
        if (di == si) continue;
        if (OpexOriginServed(lines, industries[di].tile)) continue;
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile, industries[di].tile, monthly);
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

  budget.begin();
  OpexPaxCandidates(catalog, lines, all);
  budget.end("cand_pax");

  budget.begin();
  OpexFreightCandidates(catalog, lines, all);
  budget.end("cand_freight");

  budget.begin();
  local best = OpexTopK(all, TOP_K);
  budget.end("cand_rank");

  return { all = all.len(), best = best, bands = OpexBands(all) };
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
