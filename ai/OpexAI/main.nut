/* OpexAI -- une IA qui traite les opcodes comme une ressource de jeu.
 *
 * Principe directeur : le budget du VM (10 000 opcodes par tick) n'est pas un stock qu'on
 * economise mais un DEBIT non reportable. La seule decision est donc l'ALLOCATION : a quel
 * candidat va le prochain tick de calcul. D'ou deux metriques :
 *   - externe, l'arbitre : company_value au banc (sweeps/bench.py) ;
 *   - interne, la regle d'allocation : profit par opcode.
 * En cas de desaccord, le banc gagne.
 *
 * Quatre etages :
 *   0  catalog.nut       -- villes, industries, cargos, materiel roulant (rafraichi chaque annee)
 *   1  economy.nut       -- profit annuel attendu d'une ligne
 *   2  candidates.nut    -- cout en iterations d'A* attendu, et le classement par rapport
 *   3  builder_rail.nut  -- construction, sous budget d'iterations calcule par l'arret optimal
 *
 * Instrumentation : AILog.Info n'apparait PAS dans la sortie capturee par OpenTTDLab (verifie le
 * 2026-08-28), et un nom de panneau echoue SILENCIEUSEMENT au-dela de 31 caracteres. D'ou des
 * panneaux courts et nombreux plutot que de longues lignes.
 */

import("pathfinder.rail", "RailPathFinder", 1);

require("budget.nut");
require("catalog.nut");
require("economy.nut");
require("candidates.nut");
require("builder_rail.nut");
require("builder_air.nut");
require("builder_water.nut");

/* Filet physique : deux gares reellement posees trop pres l'une de l'autre partagent leur bassin
 * de desserte, MEME si ce sont deux villes/industries differentes. Un rayon de couverture de gare
 * "petite" standard est ~4 tuiles ; MIN_SEPARATION couvre le double (dos-a-dos) plus une marge.
 * Abaisse de 15 a 10 le 2026-08-28 : mesure sur graine 42/20 ans, 84 % des rejets _tooClose
 * etaient a distance <5 de la MEME origine deja servie (couverts desormais par ORIGIN_SEPARATION
 * ci-dessous, avec precision, pas par ce filet) ; les 16 % restants, a distance 5-14, rejetaient
 * une ville VOISINE mais DIFFERENTE -- un faux positif du au seuil de 15, bien au-dela de tout
 * recouvrement de bassin plausible. Voir docs/opex_full_campaign_20y.json (signs GT/GN). */
const MIN_SEPARATION = 10;

/* Identite d'origine : candidate.src/dst est TOUJOURS la tuile exacte du catalogue (ville ou
 * industrie), stable d'une annee sur l'autre -- une reutilisation reelle de la MEME origine tombe
 * donc a distance 0 quel que soit l'endroit ou la gare a fini par etre posee (jusqu'a
 * STATION_SEARCH_RADIUS = 30 tuiles plus loin, builder_rail.nut). C'est la vraie protection
 * "pas de second raccordement sur une extremite deja servie" -- MIN_SEPARATION comparait a tort
 * l'origine du candidat a la gare BATIE d'une ligne existante, un proxy bruite par cet ecart de
 * recherche. La petite marge n'est qu'une precaution, pas le mecanisme principal. */
const ORIGIN_SEPARATION = 3;

/* Fenetre de temps accordee a une tentative, en plus du budget d'iterations. A ~3,7 iterations
 * par tick, N iterations demandent ~N/3,7 ticks ; la marge couvre la pose elle-meme. */
const BUILD_TICK_MARGIN = 3000;

/* Reserve de tresorerie. Sans elle l'IA construit jusqu'a la ruine : mesure du 2026-08-28,
 * 4 lignes construites puis solde a -542 avec l'emprunt au maximum. Une compagnie a sec ne peut
 * plus ni renouveler ses vehicules ni saisir une occasion, et la valeur d'entreprise tombe a 1. */
const CASH_RESERVE = 50000;

/* Seuil de remboursement d'emprunt : sous ce plancher de tresorerie on ne rembourse pas, un
 * emprunt a 5 % coute bien moins qu'une ligne manquee faute de cash. Au-dessus, l'argent qui
 * dort ne rapporte rien -- autant reduire l'emprunt. Valeur decidee par l'utilisateur. */
const LOAN_REPAY_FLOOR = 1000000;

/* Ligne fret morte (2026-08-28) : une industrie source qui ferme NE garantit PAS l'effondrement --
 * la gare peut recuperer une industrie voisine du meme cargo (ligne 4, campagne 20 ans, restee
 * rentable malgre srcAlive=0). Le diagnostic se fie donc TOUJOURS a la performance REELLE
 * (note de gare et revenu implicite), jamais a srcAlive seul, ET exige DEUX annees CONSECUTIVES
 * de confirmation pour exclure un accroc transitoire -- cf. OpexAI::_reportLines. */
const DEAD_STREAK_THRESHOLD = 2;

class OpexAI extends AIController {
  _budget = null;
  _catalog = null;
  _startTick = 0;
  _lines = null;        // [{stationA, stationB, cargo, predicted, iterations, trains, lineId, ...
                         //   deadStreak, scrapping, scrapVehicles (fret uniquement, cf.
                         //   _reportLines / _scrapDeadLines)}]
  _airBuilt = false;
  _waterBuilt = false;
  /* Identite stable des lignes pour les panneaux (2026-08-28) : this._lines.len() n'est plus un
   * identifiant valide des que _scrapDeadLines peut retirer un element -- Array.remove() DECALE
   * tous les indices suivants, donc un panneau IA|5|... loggue une annee peut, apres un retrait,
   * pointer sur une ligne totalement differente l'annee suivante (collision mesuree sur la
   * premiere execution : l'indice 5 melangeait une ligne fret morte 1977-1979 et une ligne saine
   * qui avait glisse dans ce slot). _nextLineId ne recule jamais, contrairement a _lines.len(). */
  _nextLineId = 0;

  constructor()
  {
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
  }

  function Start();
  function _tooClose(candidate);
  function _tryBuildAir(year);
  function _tryBuildWater(year);
  function _tryBuild(ranked, year);
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _scrapDeadLines(year);
}

/* Un seul avion suffit pour cette premiere liaison. Le scan des vehicules empeche un doublon apres
 * rechargement, ou si l'etat transitoire de l'IA a ete perdu. */
function OpexAI::_tryBuildAir(year)
{
  if (this._airBuilt || this._catalog.airport == null || this._catalog.plane == null) return;
  local vehicles = AIVehicleList();
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      this._airBuilt = true;
      return;
    }
  }

  this._budget.begin();
  local plan = OpexAirPlans(this._catalog);
  local planOps = this._budget.end("build_air_plans");
  if (plan == null) return;

  local capital = 2 * this._catalog.airport.price + this._catalog.plane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < capital + CASH_RESERVE + AIR_CAPITAL_MARGIN) return;

  local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
  local anchor = AIMap.GetTileIndex(1, 1);
  AISign.BuildSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
  if (result.error != 0) AISign.BuildSign(anchor, "OE|A|" + result.error);
  if (!result.ok) return;

  this._airBuilt = true;
  this._lines.append({
    stationA = result.stationA, stationB = result.stationB,
    /* Pas de notion d'origine distincte pour l'avion (une seule liaison jamais dupliquee, gardee
     * par _airBuilt) -- la gare batie sert de repli pour que _tooClose n'ait pas a distinguer les
     * modes. */
    originA = result.stationA, originB = result.stationB,
    cargo = this._catalog.paxCargo,
    predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
    mode = "air", vehicle = result.vehicle,
    lineId = this._nextLineId,
  });
  this._nextLineId++;
}

/* Une seule route v1 ; le scan apres rechargement empeche tout doublon maritime. */
function OpexAI::_tryBuildWater(year)
{
  if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0) return;
  local vehicles = AIVehicleList();
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_WATER) {
      this._waterBuilt = true;
      return;
    }
  }
  this._budget.begin();
  local plan = OpexWaterPlans(this._catalog);
  local planOps = this._budget.end("build_water_plans");
  if (plan == null) return;
  local capital = 2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < capital + CASH_RESERVE + WATER_CAPITAL_MARGIN) return;
  local result = OpexBuildWaterRoute(this._catalog, this._budget, plan);
  local anchor = AIMap.GetTileIndex(1, 1);
  if (result.ok) AISign.BuildSign(anchor, "OM|W|" + year + "|" + plan.distance + "|" + planOps);
  else AISign.BuildSign(anchor, "ON|W|" + result.reason + "|" + result.error);
  if (!result.ok) return;
  this._waterBuilt = true;
  this._lines.append({
    stationA = result.dockA, stationB = result.dockB,
    /* Idem avion : pas de notion d'origine distincte, repli sur le quai bati. */
    originA = result.dockA, originB = result.dockB,
    cargo = this._catalog.paxCargo,
    predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
    mode = "water", vehicle = result.vehicle,
    lineId = this._nextLineId,
  });
  this._nextLineId++;
}

/* Une extremite deja desservie par nous ne merite pas un second raccordement.
 *
 * Deux tests distincts, mesure du 2026-08-28 a l'appui (docs/opex_full_campaign_20y.json,
 * signs GT/GN) :
 *  1. Identite d'origine (ORIGIN_SEPARATION, serre) : la MEME ville/industrie deja servie, quel
 *     que soit l'endroit ou sa gare a fini par etre posee. C'etait 84 % des rejets sous l'ancien
 *     test unique -- desormais couvert avec precision, pas par une distance bruitee.
 *  2. Filet physique (MIN_SEPARATION, plus large mais abaisse) : deux gares BATIES reellement
 *     trop proches, meme pour deux origines differentes -- le vrai risque de cannibalisation.
 *
 * Rend -1 si aucun conflit, sinon la plus petite distance Manhattan trouvee parmi les deux
 * tests (0..MIN_SEPARATION-1, l'un ou l'autre seuil selon quel test a matche). */
function OpexAI::_tooClose(candidate)
{
  local worst = -1;
  foreach (line in this._lines) {
    local d;
    d = AIMap.DistanceManhattan(candidate.src, line.originA);
    if (d < ORIGIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.src, line.originB);
    if (d < ORIGIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.dst, line.originA);
    if (d < ORIGIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.dst, line.originB);
    if (d < ORIGIN_SEPARATION && (worst < 0 || d < worst)) worst = d;

    d = AIMap.DistanceManhattan(candidate.src, line.stationA);
    if (d < MIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.src, line.stationB);
    if (d < MIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.dst, line.stationA);
    if (d < MIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
    d = AIMap.DistanceManhattan(candidate.dst, line.stationB);
    if (d < MIN_SEPARATION && (worst < 0 || d < worst)) worst = d;
  }
  return worst;
}

/* Le coeur de l'allocation : on descend le classement tant qu'il reste de l'argent, et chaque
 * tentative recoit un budget d'iterations egal a ce qu'il faut pour continuer a battre le
 * candidat SUIVANT. Le seuil d'abandon n'est donc pas une constante : c'est l'alternative. */
function OpexAI::_tryBuild(ranked, year)
{
  local best = ranked.best;
  local anchor = AIMap.GetTileIndex(1, 1);

  /* Diagnostic goulot (2026-08-28) : _tooClose et la reserve de tresorerie rejettent tous deux
   * des candidats, mais rien ne comptait lequel des deux domine -- l'hypothese MIN_SEPARATION
   * n'etait deduite que par elimination. Ces compteurs le mesurent directement. */
  local nTooClose = 0;
  local nTooCloseNear = 0;   // distance 0..4 : origine reutilisee (ORIGIN_SEPARATION) ou gare tres proche
  local nTooCloseFar = 0;    // distance 5..MIN_SEPARATION-1 : filet physique seul (ORIGIN_SEPARATION=3 exclu)
  local nCashBlocked = 0;
  local nBuilt = 0;
  local nAttemptFailed = 0;  // ni tooClose ni cash, mais result.ok == false (pathfinding, etc.)

  for (local i = 0; i < best.len(); i++) {
    local candidate = best[i];
    local tooCloseDist = this._tooClose(candidate);
    if (tooCloseDist >= 0) {
      nTooClose++;
      if (tooCloseDist < 5) nTooCloseNear++; else nTooCloseFar++;
      continue;
    }

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < candidate.capital + CASH_RESERVE) {  // classement decroissant
      nCashBlocked++;
      AISign.BuildSign(anchor, "GC|" + year + "|" + money + "|" + candidate.capital);
      break;
    }

    local alternativeRatio = (i + 1 < best.len()) ? best[i + 1].ratio : 0;
    local iterationBudget = OpexIterationBudget(candidate.profitAnnual, alternativeRatio);
    local deadline = AIController.GetTick() + iterationBudget / 3 + BUILD_TICK_MARGIN;

    local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio, deadline);

    /* idx = this._nextLineId, pas this._lines.len() : depuis que _scrapDeadLines peut retirer un
     * element (et donc decaler tous les indices suivants), la longueur du tableau n'est plus un
     * identifiant stable -- cf. commentaire sur _nextLineId. _nextLineId ne recule jamais et
     * n'avance que sur un succes, exactement comme le faisait _lines.len() avant que le retrait
     * n'existe. */
    AISign.BuildSign(anchor, "OR|" + this._nextLineId + "|" + candidate.distance
                             + "|" + result.iterations + "|" + result.reason);
    if (result.error != 0) AISign.BuildSign(anchor, "OV|" + this._nextLineId + "|" + result.error);
    if (result.diag != null) {
      AISign.BuildSign(anchor, "OG|" + result.diag.railtype + "|" + result.diag.isDepot
                               + "|" + result.diag.buildable + "|" + result.diag.canRun);
      AISign.BuildSign(anchor, "OH|" + result.diag.price + "|" + result.diag.cash);
      AISign.BuildSign(anchor, "OI|" + result.diag.engineRail + "|" + result.diag.depotRail
                               + "|" + result.diag.vehType + "|" + result.diag.testOk);
    }

    if (result.ok) {
      nBuilt++;
      local idx = this._nextLineId;
      /* Predit-vs-reel (etage 1) : le detail du calcul au moment de la construction, pour pouvoir
       * le comparer plus tard a la mesure reelle (_reportLines). Un sign par grandeur : jamais
       * plus de 2 valeurs numeriques par nom pour rester sous la limite silencieuse de 31
       * caracteres meme quand i et les valeurs sont a leur maximum plausible. */
      AISign.BuildSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
      AISign.BuildSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
      AISign.BuildSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
      AISign.BuildSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains);
      AISign.BuildSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays);
      /* pax vs freight, et la production mensuelle BRUTE utilisee comme entree : pour trancher si
       * le residu du gap vient de la ville entiere comptee au lieu du seul rayon de la gare
       * (candidates.nut le signale deja comme biais non calibre sur les paires de villes). */
      AISign.BuildSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                               + "|" + candidate.monthly);

      /* Diagnostic effondrement fret (2026-08-28) : garder de quoi verifier, annee apres annee,
       * si les DEUX industries d'une ligne fret restent valides -- sans ca on ne peut pas
       * departager "industrie fermee" de "train coince" comme cause de la note -1. */
      this._lines.append({
        stationA = result.stationA, stationB = result.stationB,
        /* Identite d'origine (ville ou industrie) pour _tooClose -- cf. commentaire sur
         * ORIGIN_SEPARATION : la tuile exacte du candidat, pas la gare batie. */
        originA = candidate.src, originB = candidate.dst,
        cargo = candidate.cargo,
        predicted = candidate.profitAnnual, iterations = result.iterations,
        trains = result.trains, distance = candidate.distance, year = year,
        predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
        predAmort = candidate.amortAnnual, predCarried = candidate.carried,
        predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
        kind = candidate.kind,
        srcIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.src) : -1,
        dstIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.dst) : -1,
        /* Ligne morte (2026-08-28) : deadStreak/scrapping/scrapVehicles n'ont de sens que pour le
         * fret (cf. _reportLines et _scrapDeadLines) mais sont initialises ici pour toutes les
         * lignes rail -- inoffensif pour le pax, dont deadStreak reste a 0 pour toujours faute de
         * srcIndustry valide. */
        deadStreak = 0, scrapping = false, scrapVehicles = [],
        lineId = idx,
      });
      this._nextLineId++;
    } else {
      nAttemptFailed++;
    }
  }

  /* Sommaire annuel du goulot : combien de candidats classes ont ete rejetes par _tooClose,
   * combien par la reserve de tresorerie (dont l'"break" laisse le reste du classement
   * inexplore -- nUnreached compte ceux-la a part pour ne pas les confondre avec un rejet). */
  local nUnreached = best.len() - (nTooClose + nCashBlocked + nBuilt + nAttemptFailed);
  AISign.BuildSign(anchor, "GT|" + year + "|" + best.len() + "|" + nTooClose
                           + "|" + nCashBlocked + "|" + nBuilt + "|" + nUnreached
                           + "|" + nAttemptFailed);
  /* Repartition des rejets _tooClose : proche (probable meme ville) vs lointain (probable ville
   * DIFFERENTE, simple voisine -- signe que MIN_SEPARATION est trop grossier plutot que trop
   * grand). */
  AISign.BuildSign(anchor, "GN|" + year + "|" + nTooCloseNear + "|" + nTooCloseFar);
}

/* Le releve qui permet de calibrer l'etage 1 : pour chaque ligne, la note de gare REELLE (on
 * suppose STATION_RATING_PCT = 75) et le profit REEL des vehicules (on a predit profitAnnual).
 * C'est exactement la mesure qui manquait a la campagne v3. */
function OpexAI::_reportLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    if (!AIStation.IsValidStation(stationA)) continue;

    local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
    local ratingB = AIStation.IsValidStation(stationB)
        ? AIStation.GetCargoRating(stationB, line.cargo) : -1;
    /* line.lineId, pas i : identite stable qui survit a un retrait de _lines par _scrapDeadLines
     * (cf. commentaire sur _nextLineId). Toutes les lignes rail/avion/bateau en ont une. */
    AISign.BuildSign(anchor, "OY|" + line.lineId + "|" + year + "|" + ratingA + "|" + ratingB);

    /* Profit reel (deja mesure), plus le detail qui manquait : combien de convois roulent
     * VRAIMENT (vs. le trains predit dans _tryBuild), leur cout de fonctionnement reel, et le
     * revenu reel implicite (profit + cout de fonctionnement, puisque GetProfitLastYear n'est
     * pas decompose par l'API). C'est ce qui permet de departager "note de gare fausse" de
     * "cout de fonctionnement fausse" de "convois manquants" comme cause du 10x. */
    local profit = 0;
    local runCost = 0;
    local vehCount = 0;
    local isFreight = ("kind" in line) && line.kind == "freight";
    local diagSlot = 0;
    local vehicles = AIVehicleList_Station(stationA);
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
      if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL) continue;
      profit += AIVehicle.GetProfitLastYear(v);
      runCost += AIVehicle.GetRunningCost(v);
      vehCount++;
      /* Diagnostic effondrement fret : etat REEL de CHAQUE convoi (pas juste le premier -- une
       * gare a UNE seule voie, donc un convoi bloque au puits peut faire la queue derriere les
       * autres, qui rendraient "en marche, vitesse 0" sans etre eux-memes la cause). L'ordre
       * courant (0 = source, 1 = puits), l'etat, la vitesse et le chargement du cargo de la
       * ligne. Limite a 3 convois (MAX_TRAINS le permet toujours ici en pratique). */
      if (isFreight && diagSlot < 3) {
        local state = AIVehicle.GetState(v);
        local order = AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT);
        local speed = AIVehicle.GetCurrentSpeed(v);
        local load = AIVehicle.GetCargoLoad(v, line.cargo);
        AISign.BuildSign(anchor, "VS|" + line.lineId + "|" + year + "|" + diagSlot + "|" + state + "|" + order);
        AISign.BuildSign(anchor, "VL|" + line.lineId + "|" + year + "|" + diagSlot + "|" + speed + "|" + load);
        diagSlot++;
      }
    }
    AISign.BuildSign(anchor, "OZ|" + line.lineId + "|" + year + "|" + profit);
    AISign.BuildSign(anchor, "OU|" + line.lineId + "|" + year + "|" + vehCount + "|" + runCost);
    AISign.BuildSign(anchor, "OO|" + line.lineId + "|" + year + "|" + (profit + runCost));

    /* Les deux industries sont-elles encore valides ? Et l'industrie source produit-elle encore ?
     * Depart le blocage "train coince" (hypothese 2) de la fermeture d'industrie (hypothese 1). */
    if (isFreight) {
      local srcAlive = AIIndustry.IsValidIndustry(line.srcIndustry) ? 1 : 0;
      local dstAlive = AIIndustry.IsValidIndustry(line.dstIndustry) ? 1 : 0;
      local srcProd = srcAlive ? AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo) : -1;
      AISign.BuildSign(anchor, "IA|" + line.lineId + "|" + year + "|" + srcAlive + "|" + dstAlive + "|" + srcProd);

      /* Detection ligne morte : srcAlive=0 seul ne suffit PAS (cf. commentaire DEAD_STREAK_THRESHOLD
       * -- une gare peut recuperer une industrie voisine). srcSuffering couvre aussi l'industrie
       * encore ouverte mais a production nulle, meme consequence pour la ligne qu'une fermeture.
       * collapsed exige EN PLUS la preuve REELLE, mesuree ici meme : note de gare a -1 (aucun
       * cargo jamais vu) ET revenu implicite (profit + cout de fonctionnement) nul ou negatif,
       * c'est-a-dire rien transporte du tout cette annee. deadStreak ne compte que les annees
       * CONSECUTIVES ou les trois tiennent ensemble ; un seul manque et le compteur retombe a 0. */
      local srcSuffering = (!srcAlive) || (srcProd == 0);
      local collapsed = srcSuffering && ratingA <= 0 && (profit + runCost) <= 0;
      line.deadStreak = collapsed ? line.deadStreak + 1 : 0;
      if (line.deadStreak > 0) {
        AISign.BuildSign(anchor, "DL|" + year + "|" + line.lineId + "|" + line.deadStreak);
      }
    }
  }
}

/* Remediation ligne morte (2026-08-28) : une fois deadStreak >= DEAD_STREAK_THRESHOLD confirme
 * par _reportLines, on arrete l'hemorragie de cout de fonctionnement en vendant les convois --
 * mais AIVehicle.SellVehicle exige un convoi a l'arret DANS un depot (verifie sur la doc API
 * ai-api/classAIVehicle.html le 2026-08-28 : precondition "the vehicle must be stopped in the
 * depot", exception ERR_VEHICLE_NOT_IN_DEPOT sinon). La vente est donc etalee sur plusieurs
 * annees, au meme rythme annuel que le reste du cycle : l'annee ou le seuil est franchi on
 * envoie chaque convoi au depot (SendVehicleToDepot) et on fige la liste de leurs IDs sur la
 * ligne (scrapVehicles) -- PAS une reinterrogation par gare chaque annee, pour ne pas dependre
 * de savoir si l'ordre "aller au depot" fait toujours apparaitre le convoi dans
 * AIVehicleList_Station. Les annees suivantes, on verifie IsStoppedInDepot() sur cette liste figee
 * et on vend (SellVehicle) ce qui est arrive ; quand elle est vide, la ligne est retiree de
 * _lines -- ce qui l'arrete d'etre rapportee chaque annee ET libere stationA/stationB/originA/
 * originB du filet _tooClose, pour qu'une ligne neuve et proche ne soit plus bloquee par un
 * cadavre. Les gares et voies physiques ne sont PAS demolies : une fois hors de _lines elles ne
 * bloquent plus rien (le seul frein etait la presence dans _lines), et demolir ajoute un risque
 * (note d'autorite locale, infrastructure partagee) pour un gain nul ici. */
function OpexAI::_scrapDeadLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local toRemove = [];

  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("deadStreak" in line)) continue;  // pax/avion/bateau : jamais candidates

    if (!line.scrapping && line.deadStreak >= DEAD_STREAK_THRESHOLD) {
      line.scrapping = true;
      local stationA = AIStation.GetStationID(line.stationA);
      local ids = [];
      if (AIStation.IsValidStation(stationA)) {
        local vehicles = AIVehicleList_Station(stationA);
        for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
          if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL) continue;
          AIVehicle.SendVehicleToDepot(v);
          ids.append(v);
        }
      }
      line.scrapVehicles = ids;
      AISign.BuildSign(anchor, "DL|" + year + "|" + line.lineId + "|2");
    }

    if (line.scrapping) {
      local remaining = [];
      foreach (v in line.scrapVehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;  // deja vendu ou detruit
        if (AIVehicle.IsStoppedInDepot(v)) {
          AIVehicle.SellVehicle(v);
        } else {
          remaining.append(v);
        }
      }
      line.scrapVehicles = remaining;
      if (remaining.len() == 0) {
        toRemove.append(i);  // i = position physique dans _lines, pour le retrait -- pas le sign
        AISign.BuildSign(anchor, "DL|" + year + "|" + line.lineId + "|3");
      }
    }
  }

  /* Retrait du plus grand indice au plus petit pour ne jamais invalider un indice pas encore
   * traite dans toRemove. */
  for (local k = toRemove.len() - 1; k >= 0; k--) {
    this._lines.remove(toRemove[k]);
  }
}

function OpexAI::_reportYear(year, ranked)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local best = ranked.best.len() > 0 ? ranked.best[0] : null;

  AISign.BuildSign(anchor, "OX|" + year + "|" + this._catalog.towns.len()
                           + "|" + this._catalog.industries.len() + "|" + ranked.all);
  AISign.BuildSign(anchor, "OC|" + year + "|" + this._budget.get("cat_towns")
                           + "|" + this._budget.get("cat_industries")
                           + "|" + this._budget.get("cat_rail"));
  AISign.BuildSign(anchor, "OP|" + year + "|" + this._budget.get("cand_pax")
                           + "|" + this._budget.get("cand_freight"));
  AISign.BuildSign(anchor, "OS|" + year + "|" + this._budget.get("cand_rank")
                           + "|" + this._budget.utilisationPerMille(this._startTick));

  /* Le poste qui domine tout le reste : la recherche de chemin et la construction. */
  local buildOps = this._budget.get("build_plans") + this._budget.get("build_search")
                 + this._budget.get("build_stations") + this._budget.get("build_track")
                 + this._budget.get("build_trains") + this._budget.get("build_water_plans")
                 + this._budget.get("build_docks") + this._budget.get("build_water_depot")
                 + this._budget.get("build_ships");
  AISign.BuildSign(anchor, "OW|" + year + "|" + buildOps + "|" + this._lines.len());

  if (best != null) {
    AISign.BuildSign(anchor, "OB|" + year + "|" + best.distance
                             + "|" + best.monthly + "|" + best.ratio);
    AISign.BuildSign(anchor, "OE|" + year + "|" + best.trains
                             + "|" + best.profitAnnual + "|" + best.capital);
  }
  AISign.BuildSign(anchor, "OD|" + year + "|" + ranked.bands[0] + "|" + ranked.bands[1]
                           + "|" + ranked.bands[2] + "|" + ranked.bands[3]);
  if (this._catalog.loco != null) {
    AISign.BuildSign(anchor, "OL|" + year + "|" + this._catalog.loco.speed
                             + "|" + this._catalog.costTrackPerTile
                             + "|" + this._catalog.costStation);
  }
}

/* Remboursement annuel : une fois la tresorerie confortablement au-dessus du plancher, on
 * rembourse le maximum d'emprunt qui laisse encore ce plancher disponible pour l'annee
 * suivante. SetLoanAmount exige un multiple de GetLoanInterval() ; on arrondit donc le nouvel
 * emprunt VERS LE HAUT (jamais vers le bas, ce qui rembourserait plus que permis et pourrait
 * passer sous le plancher). Aucune reprise automatique d'emprunt n'existe ailleurs dans le
 * fichier (grep confirme le 2026-08-28) : rembourser ici ne sera donc pas annule au tick suivant. */
function OpexAI::_tryRepayLoan(year)
{
  local loan = AICompany.GetLoanAmount();
  if (loan <= 0) return;

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (cash <= LOAN_REPAY_FLOOR) return;

  local interval = AICompany.GetLoanInterval();
  local minNewLoan = loan - (cash - LOAN_REPAY_FLOOR);
  if (minNewLoan < 0) minNewLoan = 0;
  local newLoan = ((minNewLoan + interval - 1) / interval) * interval;
  if (newLoan >= loan) return;  // moins d'un palier remboursable : pas la peine

  local repaid = loan - newLoan;
  AICompany.SetLoanAmount(newLoan);
  local anchor = AIMap.GetTileIndex(1, 1);
  AISign.BuildSign(anchor, "LR|" + year + "|" + repaid + "|" + newLoan);
}

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  /* L'emprunt maximal des le depart : la note de compagnie recompense l'emprunt a zero (5 %),
   * mais une ligne non construite faute de tresorerie coute bien davantage. Le remboursement
   * viendra quand la tresorerie le permettra. */
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

  local lastYear = -1;
  while (true) {
    local year = AIDate.GetYear(AIDate.GetCurrentDate());
    if (year != lastYear) {
      lastYear = year;
      this._catalog.refresh(this._budget, year);
      local ranked = OpexBuildCandidates(this._catalog, this._budget);
      this._reportYear(year, ranked);
      this._reportLines(year);
      this._scrapDeadLines(year);
      this._tryBuildAir(year);
      this._tryBuildWater(year);
      this._tryBuild(ranked, year);
      this._tryRepayLoan(year);
    }
    AIController.Sleep(74 * 10);
  }
}
