/* Etage 3 : construire une ligne rail, sous budget d'opcodes explicite.
 *
 * Reprend les correctifs durement gagnes de ai/TrainLineAI (chacun a coute une session) :
 *  - les plans de quai sont VALIDES avant tout (tuiles constructibles et plates, plus une tuile
 *    de sortie), et le pathfinder choisit lui-meme le couple de plans en cherchant depuis
 *    plusieurs sources vers plusieurs buts. C'est ce qui a supprime le facteur x24 d'une
 *    recherche par combinaison de quais, et c'est aussi ce qui evite qu'un quai avale un virage ;
 *  - la convention [lead, station_exit] des sources/buts : la bibliotheque traite node[0] comme
 *    la vraie case de depart et node[1] comme un predecesseur virtuel, et elle AJOUTE goal[1]
 *    apres avoir atteint goal[0]. Se tromper d'ordre fait chercher depuis le quai lui-meme ;
 *  - le depot : on pose l'aiguillage AVANT le batiment et on verifie AIRail.AreTilesConnected a
 *    chaque etape. Un appel de construction qui renvoie "reussi" ne prouve PAS que le resultat
 *    est fonctionnellement raccorde.
 *
 * Ce qui est NOUVEAU ici, et propre a OpexAI : la recherche a un budget d'iterations calcule, pas
 * une constante. Voir OpexIterationBudget().
 */

/* La longueur n'est PAS une constante : catalog.nut lit `station.station_spread` chaque annee,
 * puis OpexStationPlans appelle le vrai BuildRailStation sous AITestMode avant de proposer un
 * plan. Le jeu, et non une valeur supposee, reste donc l'autorite sur le maximum utilisable. */
/* Classement natif partage des ponts : priorite vitesse, meme departage AIList. */
function OpexBridgeSortBySpeed(bridges)
{
  bridges.Valuate(AIBridge.GetMaxSpeed);
  bridges.Sort(AIList.SORT_BY_VALUE, false);
}

const STATION_SEARCH_RADIUS = 30;
const MAX_STATION_PLANS = 12;
/* V207 : facteur d'echantillonnage des sites passagers avant classement par production. */
const V207_SITE_SAMPLE_FACTOR = 3;
/* V307S=3 : complement d'octants plafonne a ce pourcentage des opcodes de la spirale du
 * meme appel (critere pre-enregistre du 22/10 : ops medianes <= 1,5 x la spirale). */
const V307S3_BUDGET_PCT = 60;
/* v1 reste un parallele dedie, pas l'enveloppe spread. Offset 1 est le colle d'origine ;
 * 2-4 sautent la sortie/voie qui occupe le voisin. 4 x 2 x 2 = 16 sondes, rien a cote d'A*.
 * Mesure 2026-08-30 : 658/692 SITE a nClear=0, 100 % du pax. */
const JOIN_PARALLEL_MAX_SIDE = 4;
const PATH_CHUNK = 50;
const PATHFINDER_MAX_COST = 200000;
/* Une tranche = un chunk de la bibliotheque. PATH_CHUNK=50 rend deja la main au moteur ;
 * c'est le rebouclage while dans OpexSearchPath qui confisquait la file (7 mois sans panneau,
 * docs/taches.md S0 undecies ter, 2026-09-03). Un seul chunk par tour, puis l'ordonnanceur
 * reprend les autres taches. */
/* ⚠️ LITTERAL OBLIGATOIRE : `const` n'accepte en Squirrel qu'un scalaire litteral. Ni
 * `= PATH_CHUNK` (reference a une autre constante) ni `= 74 * 365 * 2` (expression) ne
 * compilent -- « scalar expected : integer,float or string », et le fichier entier echoue a
 * la compilation, donc l'IA meurt au demarrage sur TOUS les bras, y compris le defaut.
 * Doit rester egal a PATH_CHUNK ci-dessus. */
const RAIL_SEARCH_SLICE = 50;
/* Borne horaire de SECURITE seulement. deadlineTick = iter/3 + 3000 gelait 7 mois parce que
 * la boucle ne rendait pas la main ; une fois etalee, le temps ECOULE inclut le travail des
 * autres taches, donc cette formule tuerait exactement les recherches qu'A4 doit sauver.
 * 54 020 = 74 ticks/jour * 365 * 2, soit deux ans de jeu, ~8x le plus long gel mesure
 * (litteral pour la meme raison que ci-dessus). Le vrai arret reste
 * spent >= iterationBudget (ABND). */
const RAIL_SEARCH_SAFETY_TICKS = 54020;

/* Pathfinding segmente (docs/taches.md A5), porte tel quel depuis
 * TrainLineAI::_segmentedPath (ai/TrainLineAI-segmented/main.nut:511).
 *
 * POURQUOI MAINTENANT. Sonde 2026-09-03 : 4 tentatives rail sur 10 meurent en ABND
 * (budget epuise sans chemin) -- une a 10 000 (plafond dur A3), trois a 5 000
 * (budget dynamique). Le prototype gagnait 1,7x a 3x d'iterations, mais 98 % de
 * ce gain venait des cas a 36k-95k, que A3 tronque desormais. L'objectif n'est
 * donc plus d'aller plus vite sur ce qui marche, c'est de trouver un chemin
 * sous 5 000-10 000 iterations la ou l'A* classique echoue.
 *
 * ⚠️ LITTERAUX OBLIGATOIRES : `const` n'accepte qu'un scalaire litteral
 * (tache A4, « scalar expected » tuait l'IA au demarrage sur TOUS les bras). */
const SEGMENTED_SEGMENT_ITERS = 2000;
const SEGMENTED_RECOVERY_ITERS = 10000;
const SEGMENTED_FRONTIER_WIDTH = 3;
const SEGMENTED_MAX_BACKTRACKS = 4;
/* Garde-fou historique du prototype (50 000). Sous A3 le budget vaut 5k-10k,
 * donc timeSafe = min(50 000, iterationBudget) se confond avec le budget. */
const SEGMENTED_TIME_SAFE_ITERS = 50000;
const SEGMENTED_BRIDGE_MIN_LEN = 3;
const SEGMENTED_BRIDGE_MAX_LEN = 20;

/* Plafond absolu, garde-fou reglable depuis main.nut::HARD_ITERATION_CAP. La mesure du 2026-08-29
 * (4 graines x 20 ans) a trouve 36 600 iterations comme maximum d'une reussite ; 40 000 garde 9 %
 * de marge, alors que les ABND a 60 000 absorbaient 56,5 % des opcodes de construction. */

/* Le budget derive du rapport est AMORTI (itérations par ligne REUSSIE) ; une tentative
 * INDIVIDUELLE en demande plus, queue asymetrique. 227 tentatives 15.3 : p95(iter OK) /
 * amort <= 2,7 sur toutes les bandes, donc 4x couvre la queue. Le plancher 2000 absorbe
 * le court une fois les noeuds v2 a 310 (4*310=1240 < 2000). Mesure du 2026-08-28 : sans
 * ce facteur, 60 tentatives sur 5 ans, budgets de 50 a 400, zero ligne. Ne PAS baisser
 * M en meme temps que les noeuds. */
const ATTEMPT_MULTIPLIER = 4;
const ATTEMPT_FLOOR = 2000;

/* LA regle d'arret optimal.
 *
 * Le budget d'opcodes est un debit non reportable : la seule question est de savoir a quel
 * candidat va le prochain tick. On continue donc a chercher cette ligne-ci tant qu'elle bat
 * encore l'alternative -- c'est-a-dire tant que son rapport, recalcule sur les iterations
 * REELLEMENT depensees, reste au-dessus du rapport du meilleur candidat non essaye.
 *
 * Le seuil a une forme fermee. Avec ratio = profit * 1000 / iterations, la ligne cesse de battre
 * l'alternative des que :
 *     profit * 1000 / (depense + reste_minimal) < ratio_alternative
 * d'ou le budget maximal ci-dessous. Aucune constante magique : le seuil est le rapport du
 * candidat suivant. Pour le dernier, l'appelant fournit MIN_RATIO, le plus petit rapport encore
 * acceptable au prochain classement annuel. Le cas <=0 reste seulement un garde-fou defensif.
 */

function OpexIterationBudget(profitAnnual, alternativeRatio, hardCap = 10000)
{
  /* Le chemin est retourne avec le budget pour l'instrumentation : Z = pas d'alternative,
   * F = plancher de tentative, C = plafond dur, N = forme fermee non bornee. */
  if (alternativeRatio <= 0) return { budget = hardCap, path = "Z" };
  local budget = ATTEMPT_MULTIPLIER * (profitAnnual * 1000) / alternativeRatio;
  if (budget < ATTEMPT_FLOOR) return { budget = ATTEMPT_FLOOR, path = "F" };
  if (budget > hardCap) return { budget = hardCap, path = "C" };
  return { budget = budget, path = "N" };
}

/* Plans de quai autour d'un centre, orientes vers l'autre extremite.
 * Porte de TrainLineAI::_makeStationPlans. */
/* Une gare rail peut etre parfaitement plate, acceptee par BuildRailStation et pourtant ne servir
 * AUCUN cargo : le smoke traction 42 a construit ainsi 5 lignes fret a note -1 permanente. Les
 * trois trains etaient en VS_AT_STATION a l'ordre source, vitesse et chargement nuls, alors que
 * l'industrie produisait encore 135 unites/mois. La commande et la voie etaient donc innocente ;
 * l'empreinte du quai etait hors du bassin de l'industrie.
 *
 * GetCargoProduction/Acceptance est la sonde exacte deja utilisee par builder_road.nut. On la
 * consulte pour chacune des `length` tuiles : une seule partie de gare dans le rayon suffit au
 * moteur. 8 est le seuil documente de l'acceptation complete (en huitiemes), pas un rendement
 * suppose. Ce preflight epargne une voie, un depot et 1 a 8 locomotives a une ligne qui ne pourra
 * jamais charger. */
function OpexRailPlatformCargoValue(anchor, step, length, cargo, coverage, wantProduction)
{
  local best = 0;
  for (local i = 0; i < length; i++) {
    local tile = anchor + step * i;
    local value = wantProduction
        ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
        : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
    if (value > best) best = value;
  }
  return best;
}

/* V190 : Recherche les quais paralleles candidats pour un plan de quai avant construction de la gare. */
function OpexV190FindParallelPlatformPlans(platform)
{
  local length = platform.length;
  local plans = [];
  local sideways = platform.direction == AIRail.RAILTRACK_NE_SW
      ? AIMap.GetTileIndex(0, 1) : AIMap.GetTileIndex(1, 0);
  local existingStId = ("stationId" in platform) ? platform.stationId
      : (AIMap.IsValidTile(platform.anchor) ? AIStation.GetStationID(platform.anchor) : AIStation.STATION_INVALID);

  for (local dist = 1; dist <= JOIN_PARALLEL_MAX_SIDE; dist++) {
    for (local flip = -1; flip <= 1; flip += 2) {
      local anchor2 = platform.anchor + sideways * (dist * flip);
      local farExit = (platform.station_exit != platform.anchor) ? 1 : 0;
      local stationExit2 = farExit != 0 ? anchor2 + platform.step * (length - 1) : anchor2;
      local lead2 = farExit != 0 ? stationExit2 + platform.step : stationExit2 - platform.step;

      local usable = AIMap.IsValidTile(lead2) && AITile.IsBuildable(lead2) &&
          AITile.GetSlope(lead2) == AITile.SLOPE_FLAT;
      for (local i = 0; i < length && usable; i++) {
        local tile = anchor2 + platform.step * i;
        usable = AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&
            AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
      }
      if (!usable) continue;

      local joins = false;
      {
        local probe = AITestMode();
        if (AIStation.IsValidStation(existingStId)) {
          joins = AIRail.BuildRailStation(anchor2, platform.direction, 1, length, existingStId);
        } else if (dist == 1) {
          local testAnchor = (flip > 0) ? platform.anchor : anchor2;
          joins = AIRail.BuildRailStation(testAnchor, platform.direction, 2, length, AIStation.STATION_NEW);
        } else {
          local ok1 = AIRail.BuildRailStation(platform.anchor, platform.direction, 1, length, AIStation.STATION_NEW);
          if (ok1) {
            local testStId = AIStation.GetStationID(platform.anchor);
            if (AIStation.IsValidStation(testStId)) {
              joins = AIRail.BuildRailStation(anchor2, platform.direction, 1, length, testStId);
            }
          }
        }
      }
      if (joins) {
        plans.push({ anchor = anchor2, station_exit = stationExit2, lead = lead2,
                     direction = platform.direction, step = platform.step, length = length });
      }
    }
  }
  return plans;
}

/* V307R : seulement la PREMIERE ligne fret vers une industrie partageable.
 * V178/V179 conservent leurs sites et leur jointure sans aucun filtrage. */
function OpexV307SinkRoomEligible(catalog, candidate)
{
  if ((V307_SINK_ROOM & 3) == 0 || candidate.kind != "freight") return false;
  if (!("cargo" in candidate) || !(candidate.cargo in catalog.producers)
      || catalog.producers[candidate.cargo].len() < 2) return false;
  if (AIIndustry.GetIndustryID(candidate.dst) < 0) return false;
  if (("joinPlatform" in candidate) && candidate.joinPlatform != null) return false;
  if (("shared_dest" in candidate) && candidate.shared_dest) return false;
  if (("convergent_dest" in candidate) && candidate.convergent_dest) return false;
  return true;
}

/* Emprise du quai de la prochaine ligne, du cote oppose a la source amont.
 * Tester les deux directions est incorrect : le cote de la premiere voie
 * resterait occupe. Chaque proposition implique longueur + lead libres et
 * validation native de la commande de gare en AITestMode. */
function OpexV307SinkRoomParallel(platform, source, bit)
{
  local available = [];
  local horizontal = platform.direction == AIRail.RAILTRACK_NE_SW;
  local srcCoord = horizontal ? AIMap.GetTileY(source) : AIMap.GetTileX(source);
  local baseCoord = horizontal ? AIMap.GetTileY(platform.anchor) : AIMap.GetTileX(platform.anchor);
  if (srcCoord == baseCoord) return available;
  local flip = srcCoord > baseCoord ? -1 : 1;
  local sideways = horizontal ? AIMap.GetTileIndex(0, 1) : AIMap.GetTileIndex(1, 0);
  local endFar = platform.station_exit != platform.anchor;
  local length = platform.length;
  for (local dist = 1; dist <= 2; dist++) {
    local widthTwo = (bit & 2) != 0 && dist == 1;
    if (!widthTwo && (bit & 1) == 0) continue;
    local anchor = platform.anchor + sideways * (dist * flip);
    if (!AIMap.IsValidTile(anchor)) continue;
    if (horizontal && (AIMap.GetTileX(anchor) != AIMap.GetTileX(platform.anchor)
        || abs(AIMap.GetTileY(anchor) - baseCoord) != dist)) continue;
    if (!horizontal && (AIMap.GetTileY(anchor) != AIMap.GetTileY(platform.anchor)
        || abs(AIMap.GetTileX(anchor) - baseCoord) != dist)) continue;
    local station_exit = endFar ? anchor + platform.step * (length - 1) : anchor;
    local lead = endFar ? station_exit + platform.step : station_exit - platform.step;
    local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead)
        && AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
    for (local i = 0; i < length && usable; i++) {
      local tile = anchor + platform.step * i;
      usable = AIMap.IsValidTile(tile) && AITile.IsBuildable(tile)
          && AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
    }
    if (!usable) continue;
    local stationAnchor = dist == 1 && flip < 0 ? anchor : platform.anchor;
    local joins = false;
    {
      local probe = AITestMode();
      /* Dist=1 : construction native 2 quais (meme pour bit1 en reserve).
       * Dist=2 : bande vierge, puis V178 revalidera la jointure. */
      joins = AIRail.BuildRailStation(dist == 1 ? stationAnchor : anchor, platform.direction,
                                     dist == 1 ? 2 : 1, length, AIStation.STATION_NEW);
    }
    if (joins) available.push({ anchor = anchor, stationAnchor = stationAnchor,
                                lead = lead, side = flip, distance = dist,
                                platforms = widthTwo ? 2 : 1 });
  }
  return available;
}

function OpexV307SinkRoomFilterPlans(plans, candidate)
{
  local mark = DECISION_LOG ? OpexOpsClock() : 0;
  local filtered = [];
  local unreserved = [];
  local retainAll = (V307_SINK_ROOM & 4) != 0;
  local firstSide = 0;
  foreach (p in plans) {
    local rooms = OpexV307SinkRoomParallel(p, candidate.src, V307_SINK_ROOM);
    if (rooms.len() == 0) {
      if (retainAll) unreserved.push(p);
      continue;
    }
    local room = rooms[0];
    p.v307RoomPlatforms <- room.platforms;
    p.v307RoomAnchor <- room.stationAnchor;
    p.v307RoomStripAnchor <- room.anchor;
    p.v307RoomLead <- room.lead;
    p.v307RoomSide <- room.side;
    p.v307RoomDistance <- room.distance;
    if (firstSide == 0) firstSide = room.side;
    filtered.push(p);
  }
  if (DECISION_LOG) OpexDecide("V307R_SITE", "src=" + candidate.src + " dst=" + candidate.dst
      + " before=" + plans.len() + " after=" + (retainAll || filtered.len() == 0 ? plans.len() : filtered.len())
      + " side=" + firstSide + " bit=" + V307_SINK_ROOM
      + " ops=" + (OpexOpsClock() - mark) + " fallback=" + (filtered.len() == 0 ? 1 : 0));
  /* Bit 4 : tous les buts restent accessibles a l'A*. Les emprises libres
   * restent prioritaires, sans changer l'ordre initial de chaque groupe. */
  if (retainAll) {
    foreach (p in unreserved) filtered.push(p);
    return filtered;
  }
  if (filtered.len() == 0) return plans;
  return filtered;
}

/* Les voies A* ne doivent pas consommer la future entree ou le futur quai B.
 * Meme fonction pour le chemin bloquant, reprenable et segmente ; ne touche
 * aucune recherche sans plans B etiquetes V307R. */
function OpexV307SinkRoomIgnoredTiles(plansA, plansB, ignoredTiles)
{
  /* Bit 8 : laisser l'A* explorer les futures bandes, puis renoncer a la
   * reserve uniquement si le chemin retenu l'occupe. */
  if ((V307_SINK_ROOM & 3) == 0 || (V307_SINK_ROOM & 8) != 0) return ignoredTiles;
  local protected = {};
  local anyRoom = false;
  foreach (p in plansB) {
    if (!("v307RoomStripAnchor" in p)) continue;
    anyRoom = true;
    for (local i = 0; i < p.length; i++) {
      local tile = p.v307RoomStripAnchor + p.step * i;
      if (AIMap.IsValidTile(tile)) protected[tile] <- true;
    }
    if (AIMap.IsValidTile(p.v307RoomLead)) protected[p.v307RoomLead] <- true;
  }
  if (!anyRoom) return ignoredTiles;
  local merged = {};
  if (ignoredTiles != null) foreach (tile in ignoredTiles) merged[tile] <- true;
  foreach (tile, _ in protected) merged[tile] <- true;
  /* Aucun but ni depart virtuel ne doit etre interdit par un AUTRE plan. */
  foreach (p in plansA) {
    if (p.lead in merged) delete merged[p.lead];
    if (p.station_exit in merged) delete merged[p.station_exit];
  }
  foreach (p in plansB) {
    if (p.lead in merged) delete merged[p.lead];
    if (p.station_exit in merged) delete merged[p.station_exit];
  }
  local out = [];
  foreach (tile, _ in merged) out.push(tile);
  return out;
}

/* Un autre but du multi-A* peut rendre traversable une tuile reservee ; on
 * revalide donc le chemin retenu a B avant devis et terrassement. */
function OpexV307SinkRoomPathClear(platform, tiles)
{
  if (!("v307RoomStripAnchor" in platform)) return true;
  local forbidden = {};
  for (local i = 0; i < platform.length; i++) {
    forbidden[platform.v307RoomStripAnchor + platform.step * i] <- true;
  }
  forbidden[platform.v307RoomLead] <- true;
  foreach (tile in tiles) {
    if (tile in forbidden) return false;
  }
  return true;
}

/* Bit 8 : quai simple plutot qu'abandon de la ligne si l'A* occupe la
 * reserve. Tous les champs doivent etre retires avant devis et pose. */
function OpexV307SinkRoomDrop(planB, candidate)
{
  if (DECISION_LOG) OpexDecide("V307R_DROP", "src=" + candidate.src + " dst=" + candidate.dst);
  if ("v307RoomPlatforms" in planB) delete planB.v307RoomPlatforms;
  if ("v307RoomAnchor" in planB) delete planB.v307RoomAnchor;
  if ("v307RoomStripAnchor" in planB) delete planB.v307RoomStripAnchor;
  if ("v307RoomLead" in planB) delete planB.v307RoomLead;
  if ("v307RoomSide" in planB) delete planB.v307RoomSide;
  if ("v307RoomDistance" in planB) delete planB.v307RoomDistance;
}

function OpexV307SinkRoomPlatforms(plan)
{
  return plan != null && ("v307RoomPlatforms" in plan) && plan.v307RoomPlatforms == 2 ? 2 : 1;
}

function OpexV307SinkRoomStationAnchor(plan)
{
  return OpexV307SinkRoomPlatforms(plan) == 2 ? plan.v307RoomAnchor : plan.anchor;
}

function OpexV307SinkRoomDemolishExtra(plan)
{
  if (OpexV307SinkRoomPlatforms(plan) != 2) return;
  for (local i = 0; i < plan.length; i++) {
    AITile.DemolishTile(plan.v307RoomStripAnchor + plan.step * i);
  }
}

/* Entretien marginal du quai supplementaire (pas de seconde STATION).
 * OpenTTD facture aux entreprises les tuiles de station en N*(1+IntSqrt(N)).
 * On calibre le prix du monde sur AIInfrastructure ; entre N+2L (deux
 * quais historiques A/B) et N+3L (le quai en plus a B), seule cette
 * difference est imputee a V307R. Aucune hypothese de prix universel. */
function OpexV307SinkRoomAnnualMaintenance(plan)
{
  if (OpexV307SinkRoomPlatforms(plan) != 2) return 0;
  if (!AIGameSettings.IsValid("economy.infrastructure_maintenance")
      || AIGameSettings.GetValue("economy.infrastructure_maintenance") == 0) return 0;
  local company = AICompany.COMPANY_SELF;
  local kind = AIInfrastructure.INFRASTRUCTURE_STATION;
  local n = AIInfrastructure.GetInfrastructurePieceCount(company, kind);
  local monthly = AIInfrastructure.GetMonthlyInfrastructureCosts(company, kind);
  if (n <= 0 || monthly <= 0) {
    /* Premiere gare de la societe : impossible d'inferer le prix d'entretien
     * natif sans une infrastructure existante, a mesurer apres le smoke. */
    if (DECISION_LOG) OpexDecide("V307R_MAINT", "monthly_est=0 unknown=1 n=" + n);
    return 0;
  }
  local n0 = n.tofloat();
  local n1 = (n + 2 * plan.length).tofloat();
  local n2 = (n + 3 * plan.length).tofloat();
  local scale0 = n0 * (1 + sqrt(n0).tointeger());
  local scale1 = n1 * (1 + sqrt(n1).tointeger());
  local scale2 = n2 * (1 + sqrt(n2).tointeger());
  local extraMonthly = ((monthly.tofloat() * (scale2 - scale1) / scale0) + 0.5).tointeger();
  if (extraMonthly < 0) extraMonthly = 0;
  if (DECISION_LOG) OpexDecide("V307R_MAINT", "monthly_est=" + extraMonthly
      + " unknown=0 n=" + n + " tiles=" + plan.length);
  return extraMonthly * 12;
}

function OpexV307SinkRoomApplyMaintenance(candidate, planB)
{
  if (OpexV307SinkRoomPlatforms(planB) != 2) return;
  /* Le devis est parfois rejoue apres un replan : ne pas doubler la charge. */
  local old = ("v307RoomAnnual" in candidate) ? candidate.v307RoomAnnual : 0;
  local annual = OpexV307SinkRoomAnnualMaintenance(planB);
  candidate.runningAnnual = candidate.runningAnnual - old + annual;
  if ("v307RoomAnnual" in candidate) candidate.v307RoomAnnual = annual;
  else candidate.v307RoomAnnual <- annual;
  candidate.profitAnnual = candidate.revenueAnnual - candidate.runningAnnual - candidate.amortAnnual;
  local immobilise = ("immobilise" in candidate) ? candidate.immobilise : 0;
  candidate.roi = candidate.profitAnnual > 0 && candidate.capital + immobilise > 0
      ? (candidate.profitAnnual * 1000) / (candidate.capital + immobilise) : 0;
}

/* V307R bit2 : la gare a deja deux quais. Pour la future ligne V178, le
 * quai inutilise EST une gare : IsBuildable serait faux. Il faut le verifier
 * par son StationID, puis simplement poser sa nouvelle entree de voie. */
function OpexV307SinkRoomPrebuiltPlan(platform, stationId)
{
  local plans = [];
  if ((V307_SINK_ROOM & 2) == 0 || !("v307RoomPlatforms" in platform)
      || platform.v307RoomPlatforms != 2 || !("v307RoomStripAnchor" in platform)) return plans;
  local anchor = platform.v307RoomStripAnchor;
  for (local i = 0; i < platform.length; i++) {
    local tile = anchor + platform.step * i;
    if (!AIMap.IsValidTile(tile) || !AIRail.IsRailStationTile(tile)
        || AIStation.GetStationID(tile) != stationId) return plans;
  }
  for (local farExit = 0; farExit <= 1; farExit++) {
    local stationExit = farExit != 0 ? anchor + platform.step * (platform.length - 1) : anchor;
    local lead = farExit != 0 ? stationExit + platform.step : stationExit - platform.step;
    if (!AIMap.IsValidTile(lead) || !AITile.IsBuildable(lead)
        || AITile.GetSlope(lead) != AITile.SLOPE_FLAT) continue;
    plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                 direction = platform.direction, step = platform.step,
                 length = platform.length, v307Prebuilt = 1 });
  }
  return plans;
}

function OpexV307SinkRoomPrebuiltReady(plan)
{
  if (!("v307Prebuilt" in plan) || plan.v307Prebuilt != 1) return false;
  if (!("stationId" in plan) || !AIStation.IsValidStation(plan.stationId)) return false;
  for (local i = 0; i < plan.length; i++) {
    local tile = plan.anchor + plan.step * i;
    if (!AIMap.IsValidTile(tile) || !AIRail.IsRailStationTile(tile)
        || AIStation.GetStationID(tile) != plan.stationId) return false;
  }
  return true;
}

/* V190 : Collecte les tuiles de quai et de sortie (lead) reservees pour la seconde voie. */
function OpexV190CollectParallelTiles(plansA, plansB)
{
  local reserved = {};
  local allPlans = [];
  if (plansA != null) { foreach (p in plansA) if (p != null) allPlans.push(p); }
  if (plansB != null) { foreach (p in plansB) if (p != null) allPlans.push(p); }

  foreach (plan in allPlans) {
    local parallels = null;
    if (("parallels" in plan) && plan.parallels != null) {
      parallels = plan.parallels;
    } else {
      parallels = OpexV190FindParallelPlatformPlans(plan);
    }
    if (parallels != null) {
      foreach (p2 in parallels) {
        if (AIMap.IsValidTile(p2.lead)) reserved[p2.lead] <- true;
        for (local i = 0; i < p2.length; i++) {
          local t = p2.anchor + p2.step * i;
          if (AIMap.IsValidTile(t)) reserved[t] <- true;
        }
      }
    }
  }
  // Ne jamais interdire la sortie ou le lead d'un quai primaire de plansA ou plansB
  foreach (plan in allPlans) {
    if (("lead" in plan) && (plan.lead in reserved)) delete reserved[plan.lead];
    if (("station_exit" in plan) && (plan.station_exit in reserved)) delete reserved[plan.station_exit];
  }
  return reserved;
}

/* V190 : Fusionne les tuiles interdites d'urbanisme (clearance) et les tuiles reservees pour le quai 2. */
function OpexV190MergeIgnoredTiles(clearanceTiles, plansA, plansB)
{
  local reserved = OpexV190CollectParallelTiles(plansA, plansB);
  if (clearanceTiles == null || clearanceTiles.len() == 0) {
    local list = [];
    foreach (tile, _ in reserved) list.push(tile);
    return list;
  }
  local merged = {};
  foreach (tile in clearanceTiles) merged[tile] <- true;
  foreach (tile, _ in reserved) merged[tile] <- true;
  local list = [];
  foreach (tile, _ in merged) list.push(tile);
  return list;
}

/* V207 : production captee par l'emprise entiere du quai (union, pas le maximum par tuile).
 * Le quai fait une tuile de large ; anchor est toujours sa tuile d'indice minimal (step > 0). */
function OpexV207PlatformUnionValue(plan, cargo, coverage)
{
  local horizontal = plan.step == AIMap.GetTileIndex(1, 0);
  local w = horizontal ? plan.length : 1;
  local h = horizontal ? 1 : plan.length;
  local v = AITile.GetCargoProduction(plan.anchor, cargo, w, h, coverage);
  return v > 0 ? v : 0;
}

/* V207 : garde les sites dont la production captee atteint rankPct % du meilleur echantillon,
 * tries par production decroissante, au plus maxPlans. L'A* multi-source choisissait sinon le
 * quai le moins cher a relier, c'est-a-dire le bord de ville tourne vers l'autre extremite. */
function OpexV207RankStationPlans(plans, maxPlans, cargo, coverage, rankPct, center)
{
  if (plans.len() == 0) return plans;
  local firstValue = -1;
  local best = 0;
  foreach (plan in plans) {
    plan.unionValue <- OpexV207PlatformUnionValue(plan, cargo, coverage);
    if (firstValue < 0) firstValue = plan.unionValue;
    if (plan.unionValue > best) best = plan.unionValue;
  }
  plans.sort(function(a, b) {
    if (a.unionValue > b.unionValue) return -1;
    if (a.unionValue < b.unionValue) return 1;
    return 0;
  });
  local floorValue = best * rankPct / 100;
  local kept = [];
  foreach (plan in plans) {
    if (kept.len() >= maxPlans) break;
    if (plan.unionValue < floorValue) break;
    kept.push(plan);
  }
  if (DECISION_LOG) {
    OpexDecide("V207_SITE", "center=" + center + " sampled=" + plans.len() + " kept=" + kept.len()
        + " best=" + best + " min_kept=" + kept[kept.len() - 1].unionValue + " first=" + firstValue);
  }
  return kept;
}

/* V307S 1.8 : directions E, SE, S, SW, W, NW, N, NE.
 * Le calcul ne depend pas des sondes V307 longue distance. */
function OpexV307SiteOctant(dx, dy)
{
  if (dx == 0 && dy == 0) return -1;
  local ax = abs(dx), ay = abs(dy);
  if (ax > 2 * ay) return dx > 0 ? 0 : 4;
  if (ay > 2 * ax) return dy > 0 ? 2 : 6;
  if (dx > 0) return dy > 0 ? 1 : 7;
  return dy > 0 ? 3 : 5;
}

function OpexV307SiteOctantCount(counts)
{
  local n = 0;
  for (local i = 0; i < 8; i++) if (counts[i] > 0) n++;
  return n;
}

/* V275 : rejette tout quai rail dont le rayon de captage chevauche celui d'un de nos aeroports
 * (AITileList_StationCoverage sur AIStationList(AIStation.STATION_AIRPORT)). */
function OpexV275PlatformInOurAirportCatchment(anchor, step, length, coverage)
{
  local endTile = anchor + step * (length - 1);
  local x1 = AIMap.GetTileX(anchor), y1 = AIMap.GetTileY(anchor);
  local x2 = AIMap.GetTileX(endTile), y2 = AIMap.GetTileY(endTile);
  local minX = x1 < x2 ? x1 : x2, maxX = x1 > x2 ? x1 : x2;
  local minY = y1 < y2 ? y1 : y2, maxY = y1 > y2 ? y1 : y2;
  return OpexV275RectInOurAirportCatchment(minX, minY, maxX, maxY, coverage);
}

/* V307S : meme validation que la spirale historique, mais sur UN site deja filtre
 * et dans un octant qui n'a pas atteint ses trois quais. Le chemin 0 ne l'appelle
 * jamais. Aucun site ne devient admissible sans AITestMode(BuildRailStation). */
function OpexV307SiteTry(site, oct, ctx)
{
  if (ctx.counts[oct] >= 3 || ctx.plans.len() >= ctx.maxPlans) return;
  if (ctx.audit != null) ctx.audit.tested++;
  local axes = [
    [AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
    [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)]
  ];
  foreach (axis in axes) {
    for (local sign = -1; sign <= 1; sign += 2) {
      local step = axis[1];
      local anchor = sign > 0 ? site : site - step * (ctx.length - 1);
      local stationExit = sign > 0 ? anchor + step * (ctx.length - 1) : anchor;
      local lead = sign > 0 ? stationExit + step : stationExit - step;
      local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead)
          && AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
      for (local i = 0; i < ctx.length && usable; i++) {
        local platformTile = anchor + step * i;
        usable = AIMap.IsValidTile(platformTile) && AITile.IsBuildable(platformTile)
            && AITile.GetSlope(platformTile) == AITile.SLOPE_FLAT;
      }
      if (!usable) continue;
      if (ctx.audit != null) ctx.audit.clear++;
      if (ctx.stats != null) ctx.stats.nClear++;
      local cargoValue = OpexRailPlatformCargoValue(anchor, step, ctx.length,
          ctx.cargo, ctx.coverage, ctx.wantProduction);
      if (ctx.wantProduction ? (cargoValue <= 0) : (cargoValue < 8)) continue;
      if (ctx.audit != null) ctx.audit.cargo_ok++;
      if (ctx.stats != null) ctx.stats.nCargo++;
      if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")) {
        local endTile = anchor + step * (ctx.length - 1);
        local x1 = AIMap.GetTileX(anchor), y1 = AIMap.GetTileY(anchor);
        local x2 = AIMap.GetTileX(endTile), y2 = AIMap.GetTileY(endTile);
        local minX = x1 < x2 ? x1 : x2, maxX = x1 > x2 ? x1 : x2;
        local minY = y1 < y2 ? y1 : y2, maxY = y1 > y2 ? y1 : y2;
        if (OpexStationEncroachesRival(minX, minY, maxX, maxY, ctx.coverage)) continue;
      }
      if (V275_AIR_TOWN_FREE > 0 && OpexV275PlatformInOurAirportCatchment(anchor, step, ctx.length, ctx.coverage)) continue;
      local stationOk = false;
      {
        local probe = AITestMode();
        stationOk = AIRail.BuildRailStation(anchor, axis[0], 1, ctx.length, AIStation.STATION_NEW);
      }
      if (!stationOk) continue;
      if (ctx.audit != null) ctx.audit.station++;
      local parallels = null;
      if (ctx.requireDouble) {
        parallels = OpexV190FindParallelPlatformPlans({
          anchor = anchor, direction = axis[0], step = step, length = ctx.length,
          station_exit = stationExit, lead = lead
        });
        if (parallels.len() == 0) continue;
      }
      if (ctx.audit != null) ctx.audit.accepted++;
      if (ctx.stats != null) ctx.stats.nCmd++;
      local plan = { anchor = anchor, station_exit = stationExit, lead = lead,
                     direction = axis[0], step = step, length = ctx.length, cargoValue = cargoValue };
      if (parallels != null && parallels.len() > 0) {
        plan.parallels <- parallels;
        plan.parallel <- parallels[0];
      }
      ctx.plans.push(plan);
      ctx.counts[oct]++;
      if (ctx.counts[oct] >= 3 || ctx.plans.len() >= ctx.maxPlans) return;
    }
  }
}

/* Les valuations de la zone industrielle (et NON du carre entier) sont effectuees
 * en natif avant de parcourir les seules tuiles candidates. Puis round-robin des
 * octants : les 12 sites les plus proches ne peuvent plus evincer tous les autres
 * octants. Sur une ville, on prolonge les anneaux apres 12 plans tant que moins
 * de quatre octants sont trouves, sous budget d'opcodes borne. */
function OpexV307StationPlans(center, radius, length, maxPlans, cargo, coverage,
                              wantProduction, stats, requireDouble, rankPct, silent = false)
{
  local mark = OpexOpsClock();
  /* Pure decision_log accounting; disabled in uninstrumented games. */
  local audit = DECISION_LOG ? { native = -1, flat = -1, buildable = -1,
      bucketed = 0, tested = 0, clear = 0, cargo_ok = 0, station = 0,
      accepted = 0 } : null;
  local ctx = { plans = [], counts = [0, 0, 0, 0, 0, 0, 0, 0],
                maxPlans = maxPlans, length = length, cargo = cargo,
                coverage = coverage, wantProduction = wantProduction,
                stats = stats, requireDouble = requireDouble, audit = audit };
  local indId = AIIndustry.GetIndustryID(center);
  local mode = indId >= 0 ? "freight" : "pax";
  local budget = 73000;
  if (indId >= 0) {
    local tiles = wantProduction ? AITileList_IndustryProducing(indId, coverage)
                                : AITileList_IndustryAccepting(indId, coverage);
    if (audit != null) audit.native = tiles.Count();
    tiles.Valuate(AITile.GetSlope);
    tiles.KeepValue(AITile.SLOPE_FLAT);
    if (audit != null) audit.flat = tiles.Count();
    tiles.Valuate(AITile.IsBuildable);
    tiles.KeepValue(1);
    if (audit != null) audit.buildable = tiles.Count();
    tiles.Valuate(AIMap.DistanceManhattan, center);
    tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
    local buckets = [[], [], [], [], [], [], [], []];
    local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) {
      if (tiles.GetValue(tile) > radius * 2) continue;
      local oct = OpexV307SiteOctant(AIMap.GetTileX(tile) - cx, AIMap.GetTileY(tile) - cy);
      if (oct < 0 || buckets[oct].len() >= 12) continue;
      buckets[oct].push(tile);
      if (audit != null) audit.bucketed++;
    }
    for (local depth = 0; depth < 12 && ctx.plans.len() < maxPlans; depth++) {
      for (local k = 0; k < 8 && ctx.plans.len() < maxPlans; k++) {
        if (depth >= buckets[k].len() || ctx.counts[k] >= 3) continue;
        if (OpexOpsClock() - mark >= budget) break;
        OpexV307SiteTry(buckets[k][depth], k, ctx);
      }
      if (OpexOpsClock() - mark >= budget) break;
    }
  } else {
    local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
    local seen = {};
    for (local r = 0; r <= radius && ctx.plans.len() < maxPlans; r++) {
      for (local dx = -r; dx <= r; dx++) {
        for (local dy = -r; dy <= r; dy++) {
          if (abs(dx) != r && abs(dy) != r) continue;
          local oct = OpexV307SiteOctant(dx, dy);
          if (oct < 0 || ctx.counts[oct] >= 3) continue;
          local x = cx + dx, y = cy + dy;
          if (x <= 0 || y <= 0 || x >= AIMap.GetMapSizeX() - 1 || y >= AIMap.GetMapSizeY() - 1) continue;
          local tile = AIMap.GetTileIndex(x, y);
          if (tile in seen) continue;
          seen[tile] <- true;
          OpexV307SiteTry(tile, oct, ctx);
          if (OpexOpsClock() - mark >= budget) break;
        }
        if (OpexOpsClock() - mark >= budget) break;
      }
      if (OpexOpsClock() - mark >= budget) break;
      if (OpexV307SiteOctantCount(ctx.counts) >= 4 && ctx.plans.len() >= maxPlans) break;
    }
  }
  if (DECISION_LOG && !silent) {
    OpexDecide("V307S_PLANS", "mode=" + mode + " side=" + (wantProduction ? "A" : "B")
      + " center=" + center + " oct_n=" + OpexV307SiteOctantCount(ctx.counts)
      + " plans=" + ctx.plans.len() + " ops=" + (OpexOpsClock() - mark) + " v=1"
      + " native=" + audit.native + " flat=" + audit.flat + " buildable=" + audit.buildable
      + " bucketed=" + audit.bucketed + " tested=" + audit.tested + " clear=" + audit.clear
      + " cargo_ok=" + audit.cargo_ok + " station=" + audit.station + " accepted=" + audit.accepted);
  }
  if (rankPct > 0) return OpexV207RankStationPlans(ctx.plans, maxPlans, cargo, coverage, rankPct, center);
  return ctx.plans;
}

/* Copie privee du parcours historique pour la valeur 2 uniquement. Elle
 * respecte la limite V207 (3x lorsqu'il faut classer), le preflight cargo,
 * la validation moteur et les quais doubles, sans changer le chemin 0/1. */
function OpexV307SpiralPlanCandidates(center, radius, length, maxPlans, cargo,
                                       coverage, wantProduction, stats, requireDouble, rankPct,
                                       scan = null)
{
  local plans = [];
  local axes = [
    [AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
    [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)],
  ];
  local limit = (rankPct > 0) ? maxPlans * V207_SITE_SAMPLE_FACTOR : maxPlans;
  local lastRing = radius + 1;
  for (local r = 0; r <= radius && plans.len() < limit; r++) {
    lastRing = r;
    for (local dx = -r; dx <= r && plans.len() < limit; dx++) {
      for (local dy = -r; dy <= r && plans.len() < limit; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local tile = center + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(tile)) continue;
        /* V307S=3 seulement (scan non nul) : la tuile de base porte un quai dans les
         * quatre orientations ; non constructible ou en pente, aucune ne passe. Meme
         * resultat, sans les quatre essais. */
        if (scan != null && (!AITile.IsBuildable(tile) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT)) continue;
        foreach (axis in axes) {
          for (local sign = -1; sign <= 1; sign += 2) {
            local step = axis[1];
            local anchor = sign > 0 ? tile : tile - step * (length - 1);
            local stationExit = sign > 0 ? anchor + step * (length - 1) : anchor;
            local lead = sign > 0 ? stationExit + step : stationExit - step;
            local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead)
                && AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
            for (local i = 0; i < length && usable; i++) {
              local platformTile = anchor + step * i;
              usable = AIMap.IsValidTile(platformTile) && AITile.IsBuildable(platformTile)
                  && AITile.GetSlope(platformTile) == AITile.SLOPE_FLAT;
            }
            if (usable) {
              if (stats != null) stats.nClear++;
              local cargoValue = OpexRailPlatformCargoValue(anchor, step, length,
                  cargo, coverage, wantProduction);
              if (wantProduction ? (cargoValue <= 0) : (cargoValue < 8)) continue;
              if (stats != null) stats.nCargo++;
              if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")) {
                local endTile = anchor + step * (length - 1);
                local x1 = AIMap.GetTileX(anchor), y1 = AIMap.GetTileY(anchor);
                local x2 = AIMap.GetTileX(endTile), y2 = AIMap.GetTileY(endTile);
                local minX = x1 < x2 ? x1 : x2, maxX = x1 > x2 ? x1 : x2;
                local minY = y1 < y2 ? y1 : y2, maxY = y1 > y2 ? y1 : y2;
                if (OpexStationEncroachesRival(minX, minY, maxX, maxY, coverage)) continue;
              }
              if (V275_AIR_TOWN_FREE > 0 && OpexV275PlatformInOurAirportCatchment(anchor, step, length, coverage)) continue;
              local stationOk = false;
              {
                local probe = AITestMode();
                stationOk = AIRail.BuildRailStation(anchor, axis[0], 1, length, AIStation.STATION_NEW);
              }
              if (stationOk) {
                local parallels = null;
                if (requireDouble) {
                  parallels = OpexV190FindParallelPlatformPlans({
                    anchor = anchor, direction = axis[0], step = step, length = length,
                    station_exit = stationExit, lead = lead
                  });
                  if (parallels.len() == 0) continue;
                }
                if (stats != null) stats.nCmd++;
                local planObj = { anchor = anchor, station_exit = stationExit, lead = lead,
                                  direction = axis[0], step = step, length = length, cargoValue = cargoValue };
                if (parallels != null && parallels.len() > 0) {
                  planObj.parallels <- parallels;
                  planObj.parallel <- parallels[0];
                }
                plans.push(planObj);
              }
              if (plans.len() >= limit) break;
            }
          }
          if (plans.len() >= limit) break;
        }
      }
    }
  }
  /* V307S=3 : les anneaux < stopRing ont ete testes en entier. Spirale epuisee
   * (limite non atteinte) => tout le carre du rayon l'a ete : stopRing = radius + 1. */
  if (scan != null) scan.stopRing <- (plans.len() >= limit) ? lastRing : radius + 1;
  if (rankPct > 0) return OpexV207RankStationPlans(plans, maxPlans, cargo, coverage, rankPct, center);
  return plans;
}

/* V307S=2 : la spirale historique decide d'abord de tous ses quais, puis les
 * sites natifs ne servent qu'a ouvrir des octants absents, sans reduire le
 * nombre de buts de la spirale. Le classement V207 de la spirale est conserve.
 * Les plans natifs passent exactement le meme test moteur que pour la valeur 1. */
function OpexV307HybridStationPlans(center, otherCenter, radius, length, maxPlans, cargo,
                                    coverage, wantProduction, stats, requireDouble, rankPct)
{
  local mark = DECISION_LOG ? OpexOpsClock() : 0;
  local spiral = OpexV307SpiralPlanCandidates(center, radius, length, maxPlans,
      cargo, coverage, wantProduction, stats, requireDouble, rankPct);
  local plans = spiral.slice(0);
  local counts = [0, 0, 0, 0, 0, 0, 0, 0];
  local covered = [false, false, false, false, false, false, false, false];
  local seen = {};
  local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
  foreach (p in plans) {
    seen[p.anchor] <- true;
    local oct = OpexV307SiteOctant(AIMap.GetTileX(p.anchor) - cx,
                                   AIMap.GetTileY(p.anchor) - cy);
    if (oct >= 0) { counts[oct]++; covered[oct] = true; }
  }
  local added = 0;
  if (OpexV307SiteOctantCount(counts) < 8) {
    /* Ne pas facturer les diagnostics des propositions supplementaires a stats.
     * La recherche native est muette : une seule ligne V307S_PLANS par appel. */
    local nativePlans = OpexV307StationPlans(center, radius, length, maxPlans,
        cargo, coverage, wantProduction, null, requireDouble, 0, true);
    foreach (candidate in nativePlans) {
      if ((candidate.anchor in seen) && seen[candidate.anchor]) continue;
      local oct = OpexV307SiteOctant(AIMap.GetTileX(candidate.anchor) - cx,
                                     AIMap.GetTileY(candidate.anchor) - cy);
      if (oct < 0 || covered[oct] || counts[oct] > 0) continue;
      if (plans.len() < maxPlans) {
        plans.push(candidate);
        seen[candidate.anchor] <- true;
        counts[oct]++;
        added++;
        continue;
      }
      /* Au plafond : remplacer un plan d'un octant surrepresente, jamais le
       * dernier plan d'un octant. Le nombre de plans reste exactement stable. */
      local richest = -1, richestCount = 1;
      for (local k = 0; k < 8; k++) {
        if (counts[k] > richestCount) { richest = k; richestCount = counts[k]; }
      }
      if (richest < 0) continue;
      for (local i = plans.len() - 1; i >= 0; i--) {
        local p = plans[i];
        local oldOct = OpexV307SiteOctant(AIMap.GetTileX(p.anchor) - cx,
                                           AIMap.GetTileY(p.anchor) - cy);
        if (oldOct != richest) continue;
        seen[p.anchor] <- false;
        plans[i] = candidate;
        seen[candidate.anchor] <- true;
        counts[richest]--;
        counts[oct]++;
        added++;
        break;
      }
    }
  }
  if (DECISION_LOG) {
    OpexDecide("V307S_PLANS", "mode=" + (AIIndustry.GetIndustryID(center) >= 0 ? "freight" : "pax")
      + " side=" + (wantProduction ? "A" : "B") + " center=" + center
      + " oct_n=" + OpexV307SiteOctantCount(counts) + " plans=" + plans.len()
      + " ops=" + (OpexOpsClock() - mark) + " v=2 spiral=" + spiral.len()
      + " native_added=" + added);
  }
  return plans;
}

/* V307S=3 : prolonge la spirale au-dela de l'anneau ou elle s'est arretee, pour les
 * seuls octants encore voulus, un quai par octant. Les anneaux interieurs ont deja
 * ete testes a l'identique (memes tuiles de base, memes quatre orientations, meme
 * etat de carte, OpexV307SiteTry reprenant les filtres de la spirale) : les reprendre
 * ne trouverait rien. Chaque bord d'anneau se coupe en trois segments d'octant
 * (bas, milieu, haut) calcules d'avance. L'octant qui compte est celui de l'ANCRE du
 * quai (comme dans OpexV307TargetedStationPlans), pas celui de la tuile de base : une
 * orientation negative recule l'ancre de length - 1 tuiles. On parcourt donc les
 * segments voulus et leurs deux voisins, on garde toutes les orientations admises
 * d'une tuile (au plus trois, quota de OpexV307SiteTry) et on retient la premiere
 * dont l'ancre tombe dans un octant encore ouvert. */
function OpexV307SpiralContinue(center, startRing, maxRing, wanted, length, cargo,
                                coverage, wantProduction, requireDouble, budget, out)
{
  local mark = OpexOpsClock();
  local found = [];
  local open = [false, false, false, false, false, false, false, false];
  local nOpen = 0;
  for (local k = 0; k < 8; k++) {
    if (wanted[k]) { open[k] = true; nOpen++; }
  }
  local ctx = { plans = [], counts = [0, 0, 0, 0, 0, 0, 0, 0], maxPlans = 4,
                length = length, cargo = cargo, coverage = coverage,
                wantProduction = wantProduction, stats = null,
                requireDouble = requireDouble, audit = null };
  local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
  local mapX = AIMap.GetMapSizeX(), mapY = AIMap.GetMapSizeY();
  /* Bords E (dx=r, t=dy), S (dy=r, t=dx), O (dx=-r, t=dy), N (dy=-r, t=dx) ; octants
   * [t bas, milieu, t haut]. Milieu : r > 2|t| (OpexV307SiteOctant). E et O portent
   * les coins ; S et N s'arretent avant. */
  local edges = [[7, 0, 1], [3, 2, 1], [5, 4, 3], [5, 6, 7]];
  /* Reserve estimee (pas une borne) : l'essai le plus cher deja vu dans l'appel. */
  local worstTry = 0;
  for (local r = startRing; r <= maxRing && nOpen > 0; r++) {
    if (r <= 0) continue;
    out.ring = r;
    local half = (r - 1) / 2;
    for (local e = 0; e < 4 && nOpen > 0; e++) {
      local corner = (e == 0 || e == 2) ? r : r - 1;
      for (local seg = 0; seg < 3 && nOpen > 0; seg++) {
        local oct = edges[e][seg];
        if (!open[oct] && !open[(oct + 1) % 8] && !open[(oct + 7) % 8]) continue;
        local t0 = seg == 0 ? -corner : (seg == 1 ? -half : half + 1);
        local t1 = seg == 0 ? -half - 1 : (seg == 1 ? half : corner);
        for (local t = t0; t <= t1 && nOpen > 0; t++) {
          if (OpexOpsClock() - mark + worstTry > budget) { out.budgetStop = 1; return found; }
          local x = cx + (e == 0 ? r : (e == 2 ? -r : t));
          local y = cy + (e == 1 ? r : (e == 3 ? -r : t));
          if (x <= 0 || y <= 0 || x >= mapX - 1 || y >= mapY - 1) continue;
          local tile = AIMap.GetTileIndex(x, y);
          out.scanned++;
          /* La tuile de base est la premiere (ou la derniere) tuile de quai des quatre
           * orientations : non constructible ou en pente, toutes echouent. */
          if (!AITile.IsBuildable(tile) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT) continue;
          local before = OpexOpsClock();
          out.tries++;
          ctx.plans = [];
          ctx.counts[0] = 0;
          OpexV307SiteTry(tile, 0, ctx);
          local spent = OpexOpsClock() - before;
          if (spent > worstTry) worstTry = spent;
          foreach (plan in ctx.plans) {
            local aoct = OpexV307SiteOctant(AIMap.GetTileX(plan.anchor) - cx,
                                            AIMap.GetTileY(plan.anchor) - cy);
            if (aoct < 0 || !open[aoct]) continue;
            open[aoct] = false;
            nOpen--;
            found.push(plan);
            break;
          }
        }
      }
    }
  }
  return found;
}

/* V307S=3 : meme garantie que la valeur 2 (la spirale historique d'abord, jamais
 * moins de plans qu'elle), sans le double parcours :
 * - spirale epuisee sans atteindre sa limite => tout le rayon a ete teste, aucun
 *   site nouveau n'est possible : aucun complement ;
 * - sinon, prolongation de la spirale a partir de son anneau d'arret, octants absents
 *   seulement, un quai chacun ; en fret, borne par le captage natif de l'industrie
 *   (+ longueur de quai), en ville par le rayon ;
 * - complement plafonne a V307S3_BUDGET_PCT % des opcodes de la spirale du meme appel.
 * Au plafond de plans, meme remplacement que la valeur 2 (octant le plus fourni,
 * jamais son dernier quai). */
function OpexV307TargetedStationPlans(center, radius, length, maxPlans, cargo,
                                      coverage, wantProduction, stats, requireDouble, rankPct)
{
  local mark = OpexOpsClock();
  local scan = {};
  local spiral = OpexV307SpiralPlanCandidates(center, radius, length, maxPlans,
      cargo, coverage, wantProduction, stats, requireDouble, rankPct, scan);
  local spiralOps = OpexOpsClock() - mark;
  local plans = spiral.slice(0);
  local counts = [0, 0, 0, 0, 0, 0, 0, 0];
  local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
  foreach (p in plans) {
    local oct = OpexV307SiteOctant(AIMap.GetTileX(p.anchor) - cx,
                                   AIMap.GetTileY(p.anchor) - cy);
    if (oct >= 0) counts[oct]++;
  }
  local wanted = [false, false, false, false, false, false, false, false];
  local nWanted = 0;
  for (local k = 0; k < 8; k++) {
    if (counts[k] == 0) { wanted[k] = true; nWanted++; }
  }
  local added = 0;
  local maxRing = -1;
  local cont = { scanned = 0, tries = 0, budgetStop = 0, ring = -1 };
  if (nWanted > 0 && scan.stopRing <= radius) {
    maxRing = radius;
    local indId = AIIndustry.GetIndustryID(center);
    if (indId >= 0) {
      /* Portee du captage, mise en cache par tuile d'industrie et cote, verifiee par
       * type d'industrie et rayon (une industrie recreee au meme endroit est recalculee).
       * La borne ne fait que limiter la prolongation. Cache non sauvegarde. */
      local key = center * 2 + (wantProduction ? 1 : 0);
      local indType = AIIndustry.GetIndustryType(indId);
      local reach = -1;
      if ((key in V307S3_REACH) && V307S3_REACH[key][0] == indType && V307S3_REACH[key][1] == coverage) {
        reach = V307S3_REACH[key][2];
      } else {
        local tiles = wantProduction ? AITileList_IndustryProducing(indId, coverage)
                                    : AITileList_IndustryAccepting(indId, coverage);
        tiles.Valuate(AIMap.DistanceMax, center);
        tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
        reach = tiles.Count() > 0 ? tiles.GetValue(tiles.Begin()) : -1;
        V307S3_REACH[key] <- [indType, coverage, reach];
      }
      if (reach >= 0) reach += length - 1;
      if (reach < maxRing) maxRing = reach;
    }
  }
  /* Horloge non monotone ou appel sans cout mesure : pas de complement. */
  if (spiralOps <= 0) maxRing = -1;
  if (maxRing >= scan.stopRing) {
    local budget = spiralOps * V307S3_BUDGET_PCT / 100 - (OpexOpsClock() - mark - spiralOps);
    local extra = budget > 0 ? OpexV307SpiralContinue(center, scan.stopRing, maxRing, wanted,
        length, cargo, coverage, wantProduction, requireDouble, budget, cont) : [];
    foreach (candidate in extra) {
      local oct = OpexV307SiteOctant(AIMap.GetTileX(candidate.anchor) - cx,
                                     AIMap.GetTileY(candidate.anchor) - cy);
      if (oct < 0 || counts[oct] > 0) continue;
      if (plans.len() < maxPlans) {
        plans.push(candidate);
        counts[oct]++;
        added++;
        continue;
      }
      local richest = -1, richestCount = 1;
      for (local k = 0; k < 8; k++) {
        if (counts[k] > richestCount) { richest = k; richestCount = counts[k]; }
      }
      if (richest < 0) continue;
      for (local i = plans.len() - 1; i >= 0; i--) {
        local p = plans[i];
        if (OpexV307SiteOctant(AIMap.GetTileX(p.anchor) - cx,
                               AIMap.GetTileY(p.anchor) - cy) != richest) continue;
        plans[i] = candidate;
        counts[richest]--;
        counts[oct]++;
        added++;
        break;
      }
    }
  }
  if (DECISION_LOG) {
    local totalOps = OpexOpsClock() - mark;
    OpexDecide("V307S_PLANS", "mode=" + (AIIndustry.GetIndustryID(center) >= 0 ? "freight" : "pax")
      + " side=" + (wantProduction ? "A" : "B") + " center=" + center
      + " oct_n=" + OpexV307SiteOctantCount(counts) + " plans=" + plans.len()
      + " ops=" + totalOps + " v=3 spiral=" + spiral.len()
      + " native_added=" + added + " spiral_ops=" + spiralOps
      + " extra_ops=" + (totalOps - spiralOps) + " stop_ring=" + scan.stopRing
      + " max_ring=" + maxRing + " wanted=" + nWanted + " scanned=" + cont.scanned
      + " tries=" + cont.tries + " last_ring=" + cont.ring + " budget_stop=" + cont.budgetStop);
  }
  return plans;
}

function OpexStationPlans(center, otherCenter, radius, length, maxPlans, cargo, coverage,
                          wantProduction, stats = null, requireDouble = false, rankPct = 0)
{
  if (OPEX_LEVEL_LIMITS && wantProduction) {
    local indId = AIIndustry.GetIndustryID(center);
    if (indId >= 0 && OpexIndustryPrimaryRivalServed(indId, center, coverage)) return [];
  }
  if (V307_SITES == 3) return OpexV307TargetedStationPlans(center, radius, length,
      maxPlans, cargo, coverage, wantProduction, stats, requireDouble, rankPct);
  if (V307_SITES == 2) return OpexV307HybridStationPlans(center,
      otherCenter, radius, length, maxPlans, cargo, coverage, wantProduction,
      stats, requireDouble, rankPct);
  if (V307_SITES > 0) return OpexV307StationPlans(center, radius, length, maxPlans,
      cargo, coverage, wantProduction, stats, requireDouble, rankPct);
  local v307LogMark = DECISION_LOG ? OpexOpsClock() : 0;

  local plans = [];
  local axes = [
    [AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
    [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)],
  ];
  /* V207 : avec le classement, on echantillonne plus large avant de trier ; sinon limit = maxPlans. */
  local limit = (rankPct > 0) ? maxPlans * V207_SITE_SAMPLE_FACTOR : maxPlans;
  for (local r = 0; r <= radius && plans.len() < limit; r++) {
    for (local dx = -r; dx <= r && plans.len() < limit; dx++) {
      for (local dy = -r; dy <= r && plans.len() < limit; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local base = center + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(base)) continue;
        /* PO-02 : base est le premier/dernier quai selon sign, sur les deux axes.
         * Le filtre historique rejette avant stats/cargo/commande/paralleles.
         * Conserver le chemin historique pour une longueur non positive. */
        if (STATION_PLAN_PRECHECK && length > 0 &&
            (!AITile.IsBuildable(base) || AITile.GetSlope(base) != AITile.SLOPE_FLAT)) continue;
        foreach (axis in axes) {
          for (local sign = -1; sign <= 1; sign += 2) {
            local step = axis[1];
            local anchor = sign > 0 ? base : base - step * (length - 1);
            local stationExit = sign > 0 ? anchor + step * (length - 1) : anchor;
            local lead = sign > 0 ? stationExit + step : stationExit - step;
            local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&
                AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
            for (local i = 0; i < length && usable; i++) {
              local platformTile = anchor + step * i;
              usable = AIMap.IsValidTile(platformTile) && AITile.IsBuildable(platformTile) &&
                  AITile.GetSlope(platformTile) == AITile.SLOPE_FLAT;
            }
            if (usable) {
              if (stats != null) stats.nClear++;
              local cargoValue = OpexRailPlatformCargoValue(anchor, step, length, cargo, coverage,
                                                             wantProduction);
              if (wantProduction ? (cargoValue <= 0) : (cargoValue < 8)) continue;
              if (stats != null) stats.nCargo++;
              /* Levier B, Niveau 0 : rejet si le rayon de captage chevauche celui d'une gare rivale */
              if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")) {
                local endTile = anchor + step * (length - 1);
                local x1 = AIMap.GetTileX(anchor), y1 = AIMap.GetTileY(anchor);
                local x2 = AIMap.GetTileX(endTile), y2 = AIMap.GetTileY(endTile);
                local minX = x1 < x2 ? x1 : x2, maxX = x1 > x2 ? x1 : x2;
                local minY = y1 < y2 ? y1 : y2, maxY = y1 > y2 ? y1 : y2;
                if (OpexStationEncroachesRival(minX, minY, maxX, maxY, coverage)) continue;
              }
              if (V275_AIR_TOWN_FREE > 0 && OpexV275PlatformInOurAirportCatchment(anchor, step, length, coverage)) continue;
              /* Le rectangle plat ne prouve pas que la commande respecte le station_spread ou les
               * regles de gare. Ce test est au plus MAX_STATION_PLANS * 2 commandes par tentative
               * (24 avec le plafond deja mesure), tres petit devant les milliers d'iterations A* ;
               * il evite de lancer A* vers un quai que le moteur refuserait apres coup. */
              local stationOk = false;
              {
                local probe = AITestMode();
                stationOk = AIRail.BuildRailStation(anchor, axis[0], 1, length, AIStation.STATION_NEW);
              }
              if (stationOk) {
                local parallels = null;
                if (requireDouble) {
                  parallels = OpexV190FindParallelPlatformPlans({
                    anchor = anchor, direction = axis[0], step = step, length = length,
                    station_exit = stationExit, lead = lead
                  });
                  if (parallels.len() == 0) continue;
                }
                if (stats != null) stats.nCmd++;
                local planObj = { anchor = anchor, station_exit = stationExit, lead = lead,
                                  direction = axis[0], step = step, length = length, cargoValue = cargoValue };
                if (parallels != null && parallels.len() > 0) {
                  planObj.parallels <- parallels;
                  planObj.parallel <- parallels[0];
                }
                plans.push(planObj);
              }
              if (plans.len() >= limit) break;
            }
          }
          if (plans.len() >= limit) break;
        }
      }
    }
  }
  if (DECISION_LOG) {
    local usedOctants = [0, 0, 0, 0, 0, 0, 0, 0];
    foreach (p in plans) {
      local o = OpexV307SiteOctant(AIMap.GetTileX(p.anchor) - AIMap.GetTileX(center),
                                  AIMap.GetTileY(p.anchor) - AIMap.GetTileY(center));
      if (o >= 0) usedOctants[o]++;
    }
    OpexDecide("V307S_PLANS", "mode=" + (AIIndustry.GetIndustryID(center) >= 0 ? "freight" : "pax")
      + " side=" + (wantProduction ? "A" : "B") + " center=" + center
      + " oct_n=" + OpexV307SiteOctantCount(usedOctants)
      + " plans=" + plans.len() + " ops=" + (OpexOpsClock() - v307LogMark) + " v=0");
  }
  if (rankPct > 0) return OpexV207RankStationPlans(plans, maxPlans, cargo, coverage, rankPct, center);
  return plans;
}

/* Un raccordement v1 ne melange jamais deux circulations sur le meme quai : on ajoute un quai
 * parallele, joint au meme StationID mais avec sa propre entree. AIRail.BuildRailStation accepte
 * bien un StationID existant (api/script_rail.hpp), mais ne sait pas "agrandir" abstraitement une
 * gare : ce quai explicite est donc l'unite atomique, et l'absence d'aiguillage protege la voie
 * voisine du bouchon a une voie mesure le 2026-08-28.
 *
 * platform est le plan que nous avions nous-memes pose pour la ligne voisine. On ne cherche pas a
 * inferer une gare generique (aeroport, dock, ou gare humaine) : cette tranche n'est autorisee a
 * toucher que la geometrie dont elle connait l'origine. Les deux choix d'extremite donnent au
 * pathfinder une entree dediee sans avoir a raccorder la voie ancienne.
 *
 * L'offset 1 d'origine laissait les deux cotes bloques par la sortie, un depot ou un quai deja
 * joint. On elargit PERPENDICULAIREMENT seulement, meme orientation, meme longueur : ce n'est
 * pas le scan d'enveloppe de AAAHogEx. stats recoit nClear / nCargo (= nClear, le cargo n'est
 * pas un filtre ici) / nCmd, pour que PS ne reste plus a 0,0,0 sur un echec de quai joint. */
function OpexJoinPlatformPlans(platform, stationId, stats = null)
{
  local length = platform.length;
  local plans = [];
  local sideways = platform.direction == AIRail.RAILTRACK_NE_SW
      ? AIMap.GetTileIndex(0, 1) : AIMap.GetTileIndex(1, 0);
  if ((V307_SINK_ROOM & 2) != 0) {
    local prebuilt = OpexV307SinkRoomPrebuiltPlan(platform, stationId);
    if (prebuilt.len() > 0) {
      if (stats != null) { stats.nClear += prebuilt.len(); stats.nCargo += prebuilt.len(); stats.nCmd += prebuilt.len(); }
      return prebuilt;
    }
  }
  for (local dist = 1; dist <= JOIN_PARALLEL_MAX_SIDE; dist++) {
    for (local flip = -1; flip <= 1; flip += 2) {
      local anchor = platform.anchor + sideways * (dist * flip);
      for (local farExit = 0; farExit <= 1; farExit++) {
        local stationExit = farExit != 0 ? anchor + platform.step * (length - 1) : anchor;
        local lead = farExit != 0 ? stationExit + platform.step : stationExit - platform.step;
        local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&
            AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
        for (local i = 0; i < length && usable; i++) {
          local tile = anchor + platform.step * i;
          usable = AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&
              AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
        }
        if (!usable) continue;
        if (stats != null) {
          stats.nClear++;
          stats.nCargo++;
        }

        /* Le test inclut les regles de jointure et de taille de gare du moteur. Une reussite de
         * BuildRailStation ne suffit toujours pas pour la VOIE : elle sera controlee plus bas par
         * AreTilesConnected apres chaque pose. */
        local joins = false;
        {
          local probe = AITestMode();
          joins = AIRail.BuildRailStation(anchor, platform.direction, 1, length, stationId);
        }
        if (joins) {
          if (stats != null) stats.nCmd++;
          plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                       direction = platform.direction, step = platform.step, length = length });
        }
      }
    }
  }
  return plans;
}

/* V264 : boite inclusive des tuiles train de la gare (AITileList_StationType). */
function OpexV264StationRailBox(stationId)
{
  local tiles = AITileList_StationType(stationId, AIStation.STATION_TRAIN);
  local x0 = -1;
  local y0 = -1;
  local x1 = -1;
  local y1 = -1;
  for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) {
    local x = AIMap.GetTileX(tile);
    local y = AIMap.GetTileY(tile);
    if (x0 < 0 || x < x0) x0 = x;
    if (y0 < 0 || y < y0) y0 = y;
    if (x > x1) x1 = x;
    if (y > y1) y1 = y;
  }
  if (x0 < 0) return null;
  return { x0 = x0, y0 = y0, x1 = x1, y1 = y1 };
}

/* Distance de Tchebychev d'une ancre a un rectangle inclusif. 0 = dans le rectangle. */
function OpexV264RectDistance(ax, ay, x0, y0, x1, y1)
{
  local dx = 0;
  if (ax < x0) dx = x0 - ax;
  else if (ax > x1) dx = ax - x1;
  local dy = 0;
  if (ay < y0) dy = y0 - ay;
  else if (ay > y1) dy = ay - y1;
  return dx > dy ? dx : dy;
}

/* Union du quai neuf avec la gare : largeur et hauteur <= station.station_spread.
 * station_cmd.cpp CanExpandRailStation (~1204) et w_org/h_org (~1471).
 * script_rail.cpp:162 : NE_SW = AXIS_X (longueur en X), NW_SE = AXIS_Y.
 * alongX vrai : quai de `length` tuiles en X et 1 en Y. */
function OpexV264SpreadWindow(box, spread, length, alongX)
{
  local ax0;
  local ax1;
  local ay0;
  local ay1;
  if (alongX) {
    ax0 = box.x1 - spread + 1;
    ax1 = box.x0 + spread - length;
    ay0 = box.y1 - spread + 1;
    ay1 = box.y0 + spread - 1;
  } else {
    ax0 = box.x1 - spread + 1;
    ax1 = box.x0 + spread - 1;
    ay0 = box.y1 - spread + 1;
    ay1 = box.y0 + spread - length;
  }
  return { ax0 = ax0, ax1 = ax1, ay0 = ay0, ay1 = ay1 };
}

function OpexV264AnchorInWindow(win, ax, ay)
{
  return ax >= win.ax0 && ax <= win.ax1 && ay >= win.ay0 && ay <= win.ay1;
}

/* Ancres deja sondees par OpexJoinPlatformPlans : meme axe, offset perpendiculaire
 * 1..JOIN_PARALLEL_MAX_SIDE (builder_rail.nut:29). NE_SW decale en Y, sinon en X
 * (OpexJoinPlatformPlans, sideways). */
function OpexV264ParallelAnchor(platform, ax, ay)
{
  local px = AIMap.GetTileX(platform.anchor);
  local py = AIMap.GetTileY(platform.anchor);
  local sx = 1;
  local sy = 0;
  if (platform.direction == AIRail.RAILTRACK_NE_SW) {
    sx = 0;
    sy = 1;
  }
  local dx = ax - px;
  local dy = ay - py;
  if (sx == 0) {
    if (dx != 0 || dy == 0) return false;
    local ady = dy < 0 ? -dy : dy;
    return ady >= 1 && ady <= JOIN_PARALLEL_MAX_SIDE;
  }
  if (dy != 0 || dx == 0) return false;
  local adx = dx < 0 ? -dx : dx;
  return adx >= 1 && adx <= JOIN_PARALLEL_MAX_SIDE;
}

/* Un quai, deux sorties, meme contrat que OpexJoinPlatformPlans. Longueur unique :
 * platform.length, celle que OpexBuildTrains lit sur le candidat. */
function OpexV264TrySpreadAnchor(plans, stationId, stats, length, ax, ay, direction, step)
{
  if (plans.len() >= MAX_STATION_PLANS) return;
  local anchor = AIMap.GetTileIndex(ax, ay);
  for (local farExit = 0; farExit <= 1; farExit++) {
    if (plans.len() >= MAX_STATION_PLANS) return;
    local stationExit = farExit != 0 ? anchor + step * (length - 1) : anchor;
    local lead = farExit != 0 ? stationExit + step : stationExit - step;
    local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&
        AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
    for (local i = 0; i < length && usable; i++) {
      local tile = anchor + step * i;
      usable = AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&
          AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
    }
    if (!usable) continue;
    if (stats != null) {
      stats.nClear++;
      stats.nCargo++;
    }
    local joins = false;
    {
      local probe = AITestMode();
      joins = AIRail.BuildRailStation(anchor, direction, 1, length, stationId);
    }
    if (!joins) continue;
    if (stats != null) stats.nCmd++;
    /* stationId est pose par l'appelant avec <- : le slot ne doit pas deja exister. */
    local built = { anchor = anchor, station_exit = stationExit, lead = lead,
                    direction = direction, step = step, length = length };
    plans.push(built);
  }
}

function OpexV264SpreadVisit(plans, platform, stationId, stats, length, ax, ay, scan, dist)
{
  if (plans.len() >= MAX_STATION_PLANS) return;
  if (ax < 0 || ay < 0 || ax >= scan.mapX || ay >= scan.mapY) return;
  if (OpexV264RectDistance(ax, ay, scan.x0, scan.y0, scan.x1, scan.y1) != dist) return;
  if (OpexV264AnchorInWindow(scan.winX, ax, ay)) {
    if (platform.direction != AIRail.RAILTRACK_NE_SW || !OpexV264ParallelAnchor(platform, ax, ay)) {
      OpexV264TrySpreadAnchor(plans, stationId, stats, length, ax, ay,
                              AIRail.RAILTRACK_NE_SW, scan.stepX);
    }
  }
  if (plans.len() >= MAX_STATION_PLANS) return;
  if (OpexV264AnchorInWindow(scan.winY, ax, ay)) {
    if (platform.direction != AIRail.RAILTRACK_NW_SE || !OpexV264ParallelAnchor(platform, ax, ay)) {
      OpexV264TrySpreadAnchor(plans, stationId, stats, length, ax, ay,
                              AIRail.RAILTRACK_NW_SE, scan.stepY);
    }
  }
}

/* Anneau de Tchebychev autour du rectangle existant. Le proche (1..JOIN_PARALLEL_MAX_SIDE)
 * passe avant le reste de la boite, pour qu'un quai perpendiculaire adjacent ne balaie
 * pas toute l'emprise. Plafond MAX_STATION_PLANS (builder_rail.nut:23). */
function OpexV264SpreadScan(plans, platform, stationId, stats, box, spread, length, distMin, distMax)
{
  local scan = {
    mapX = AIMap.GetMapSizeX(),
    mapY = AIMap.GetMapSizeY(),
    x0 = box.x0, y0 = box.y0, x1 = box.x1, y1 = box.y1,
    winX = OpexV264SpreadWindow(box, spread, length, true),
    winY = OpexV264SpreadWindow(box, spread, length, false),
    stepX = AIMap.GetTileIndex(1, 0),
    stepY = AIMap.GetTileIndex(0, 1)
  };
  for (local dist = distMin; dist <= distMax; dist++) {
    if (plans.len() >= MAX_STATION_PLANS) return;
    local xLo = box.x0 - dist;
    local xHi = box.x1 + dist;
    local yNorth = box.y0 - dist;
    local ySouth = box.y1 + dist;
    for (local ax = xLo; ax <= xHi; ax++) {
      if (plans.len() >= MAX_STATION_PLANS) return;
      OpexV264SpreadVisit(plans, platform, stationId, stats, length, ax, yNorth, scan, dist);
      if (ySouth != yNorth) {
        OpexV264SpreadVisit(plans, platform, stationId, stats, length, ax, ySouth, scan, dist);
      }
    }
    local yLo = box.y0 - dist + 1;
    local yHi = box.y1 + dist - 1;
    for (local ay = yLo; ay <= yHi; ay++) {
      if (plans.len() >= MAX_STATION_PLANS) return;
      OpexV264SpreadVisit(plans, platform, stationId, stats, length, xLo, ay, scan, dist);
      if (xHi != xLo) {
        OpexV264SpreadVisit(plans, platform, stationId, stats, length, xHi, ay, scan, dist);
      }
    }
  }
}

/* V264 : quai joint hors du parallele, dans l'emprise moteur. Une seule longueur,
 * celle du quai deja pose. Echec = liste vide (pas de seconde gare, pas de quai plus court).
 * Aucun seuil de caisse ajoute : la reserve reste CASH_RESERVE_MIN/MAX (main.nut:42-43).
 * station.distant_join_stations (game_settings.ini:136, defaut vrai) et
 * station.station_spread (game_settings.ini:108, defaut 12, min 4, max 64).
 * Un spread < 4 est refuse : c'est le minimum moteur, sans repli a 12. */
function OpexV264SpreadJoinPlans(platform, stationId, stats = null)
{
  if (platform == null) return [];
  if (!("length" in platform) || !("anchor" in platform)
      || !("direction" in platform) || !("step" in platform)) return [];
  local length = platform.length;
  if (length < 1) return [];
  if (!AIStation.IsValidStation(stationId)) return [];
  if (!AIStation.HasStationType(stationId, AIStation.STATION_TRAIN)) return [];
  if (!AIGameSettings.GetValue("station.distant_join_stations")) return [];
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread == null || spread < 4) return [];
  if (length > spread) return [];
  local box = OpexV264StationRailBox(stationId);
  if (box == null) return [];
  local plans = [];
  OpexV264SpreadScan(plans, platform, stationId, stats, box, spread, length, 1, JOIN_PARALLEL_MAX_SIDE);
  if (plans.len() < MAX_STATION_PLANS) {
    OpexV264SpreadScan(plans, platform, stationId, stats, box, spread, length,
                       JOIN_PARALLEL_MAX_SIDE + 1, spread);
  }
  return plans;
}

/* Un couple de plans a une longueur donnee. Rend nA/nB meme en echec : c'est ce qui permet de
 * distinguer SITEA, SITEB et SITEAB, au lieu du seau unique NOPLAN. Les closures Squirrel de
 * cet environnement ne capturent pas les locaux englobants -- d'ou une fonction libre. */
function OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB)
{
  local isDoubleFreight = (OpexV190Active() && candidate.kind == "freight");
  local rankPct = (candidate.kind == "pax") ? V207_RAIL_PAX_SITE_RANK_PCT : 0;
  local plansA = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, length,
                                  MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true,
                                  statsA, isDoubleFreight, rankPct);
  if (isDoubleFreight && plansA.len() == 0) {
    plansA = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, length,
                              MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true,
                              statsA, false);
  }
  if (plansA.len() == 0) {
    return { ok = false, nA = 0, nB = -1, plansA = plansA, plansB = [] };
  }
  local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, length,
                                  MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                  candidate.kind == "pax", statsB, isDoubleFreight, rankPct);
  if (isDoubleFreight && plansB.len() == 0) {
    plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, length,
                              MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                              candidate.kind == "pax", statsB, false);
  }
  if (plansB.len() == 0) {
    return { ok = false, nA = plansA.len(), nB = 0, plansA = plansA, plansB = plansB };
  }
  if (V307_SINK_ROOM > 0 && OpexV307SinkRoomEligible(catalog, candidate)) {
    plansB = OpexV307SinkRoomFilterPlans(plansB, candidate);
  }
  return { ok = true, nA = plansA.len(), nB = plansB.len(), plansA = plansA, plansB = plansB };
}

function OpexRailSiteReason(sawA, sawB)
{
  if (!sawA && !sawB) return "SITEAB";
  if (!sawA) return "SITEA";
  return "SITEB";
}

/* Cherche les deux extremites a la meme longueur, du quai economiquement voulu vers le plancher
 * d'une locomotive et un wagon. Le test de chaque longueur reste celui de OpexStationPlans :
 * plat, constructible, cargo dans le rayon et BuildRailStation en AITest. Une longueur plus
 * courte est donc un vrai plan constructible, pas une approximation geometrique.
 *
 * Le seau NOPLAN est eclate : SITEA / SITEB / SITEAB. La cause mesuree du 50 % restant n'etait
 * pas le site search -- c'etaient des origines fret sans tuile de terre dans le bassin
 * (OpexRailOriginSitable, candidates.nut).
 */
function OpexRailPlatformPlans(catalog, candidate)
{
  local statsA = { nClear = 0, nCargo = 0, nCmd = 0 };
  local statsB = { nClear = 0, nCargo = 0, nCmd = 0 };

  local floor = OpexRailMinimumPlatformLength();
  local wanted = candidate.platformLength;
  if (wanted > catalog.platformLength) wanted = catalog.platformLength;
  local sawA = false;
  local sawB = false;

  /* V88 / V178 : si le candidat dispose d'un quai joint a une gare existante.
   * Historiquement V88 joint toujours A. `joinEnd=B` (V178, destination partagee) joint B
   * sans inverser src/dst (interdit pour le fret). */
  if (("joinPlatform" in candidate) && candidate.joinPlatform != null &&
      ("joinStationId" in candidate) && candidate.joinStationId >= 0) {
    local joinB = ("joinEnd" in candidate) && candidate.joinEnd == "B";
    local jointLength = candidate.joinPlatform.length;
    local joinHasA = false;
    local joinHasB = false;
    /* V178 : un rattachement a une destination partagee n'est PAS un simple indice de placement,
     * c'est le contrat physique du candidat. Sans ce garde, tomber dans la recherche libre plus
     * bas tout en gardant joinLineId fait ignorer la ligne existante dans _tooClose et permet de
     * contourner ORIGIN_SEPARATION avec une seconde gare. V88 conserve son fallback historique. */
    local strictOriginReuseJoin = (("shared_dest" in candidate) && candidate.shared_dest)
        || (("convergent_dest" in candidate) && candidate.convergent_dest);
    if (!joinB) {
      local jointPlansA = OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA);
      joinHasA = jointPlansA.len() > 0;
      if (jointPlansA.len() > 0) {
        foreach (p in jointPlansA) {
          p.stationId <- candidate.joinStationId;
        }
        local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, jointLength,
                                        MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                        candidate.kind == "pax", statsB);
        joinHasB = plansB.len() > 0;
        if (plansB.len() > 0) {
          return { plansA = jointPlansA, plansB = plansB, length = jointLength,
                   slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
        }
        sawA = true;
      }
    } else {
      local jointPlansB = OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB);
      if (("convergent_dest" in candidate) && candidate.convergent_dest == 1) {
        local joinMode = "parallel";
        if (jointPlansB.len() == 0) {
          jointPlansB = OpexV264SpreadJoinPlans(candidate.joinPlatform, candidate.joinStationId, statsB);
          joinMode = "spread";
        }
        if (DECISION_LOG) {
          local joinedLength = jointPlansB.len() > 0 ? jointPlansB[0].length : 0;
          OpexDecide("V264_JOIN", "mode=" + joinMode + " n=" + jointPlansB.len()
              + " len=" + joinedLength + " station=" + candidate.joinStationId
              + " src=" + candidate.src + " dst=" + candidate.dst);
        }
      }
      joinHasB = jointPlansB.len() > 0;
      if (jointPlansB.len() > 0) {
        foreach (p in jointPlansB) {
          p.stationId <- candidate.joinStationId;
        }
        /* A reste toujours l'origine productrice, y compris quand B reutilise une gare existante.
         * L'ancien `candidate.kind == "pax"` passait false pour le fret et testait donc
         * l'ACCEPTATION du cargo sur la source : faux SITEA systematique des extensions fret B. */
        local plansA = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, jointLength,
                                        MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                        true, statsA);
        joinHasA = plansA.len() > 0;
        if (plansA.len() > 0) {
          return { plansA = plansA, plansB = jointPlansB, length = jointLength,
                   slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
        }
        sawB = true;
      }
    }
    if (strictOriginReuseJoin) {
      return { plansA = null, plansB = null, length = jointLength,
               slopeRelaxed = 0, reason = OpexRailSiteReason(joinHasA, joinHasB),
               statsA = statsA, statsB = statsB };
    }
  }

  for (local length = wanted; length >= floor; length--) {
    local found = OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB);
    if (found.nA > 0) sawA = true;
    if (found.nB > 0) sawB = true;
    if (found.ok) {
      return { plansA = found.plansA, plansB = found.plansB, length = length,
               slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
    }
  }
  if (!sawA) {
    local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, floor,
                                    MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                    candidate.kind == "pax", statsB);
    if (plansB.len() > 0) sawB = true;
  }
  return { plansA = null, plansB = null, length = 0, slopeRelaxed = 0,
           reason = OpexRailSiteReason(sawA, sawB), statsA = statsA, statsB = statsB };
}

/* V129 : cumule les opcodes de la phase de recherche A* sur le candidat (lu par RAIL_ATTEMPT). */
function OpexAddRailSearchOps(candidate, ops)
{
  if ("searchOps" in candidate) candidate.searchOps += ops;
  else candidate.searchOps <- ops;
}

/* V172 : poids heuristique A* rail adaptatif a la distance Manhattan de la recherche.
 * Si v172_rail_long_weight_pct > 0 et distance >= v172_rail_long_weight_dist,
 * utilise ce poids au lieu de V91_ASTAR_WEIGHT_PCT.
 * V294c : si v294_rail_weight_pct > 0, poids unifié utilisé à toutes les distances (AAA : 200). */
function OpexRailAstarWeight(dist = null)
{
  if (V294_RAIL_WEIGHT_PCT > 0) {
    return V294_RAIL_WEIGHT_PCT;
  }
  if (dist != null && V172_RAIL_LONG_WEIGHT_PCT > 0 && dist >= V172_RAIL_LONG_WEIGHT_DIST) {
    return V172_RAIL_LONG_WEIGHT_PCT;
  }
  return V91_ASTAR_WEIGHT_PCT;
}

/* V294j : cache carte montagneuse (>= 30 de hauteur max sur 100 tuiles sonder, aligné sur AAA main.nut:3625). */
::OpexMountainousMapCache <- null;

function OpexIsMountainousMap()
{
  if (::OpexMountainousMapCache != null) return ::OpexMountainousMapCache;
  local mapSize = AIMap.GetMapSize();
  local maxH = 0;
  for (local i = 0; i < 100; ++i) {
    local tile = AIBase.RandRange(mapSize);
    local h = AITile.GetMaxHeight(tile);
    if (h > maxH) maxH = h;
  }
  ::OpexMountainousMapCache = (maxH >= 30);
  return ::OpexMountainousMapCache;
}

function OpexTrainSlopeSteepness()
{
  if (AIGameSettings.IsValid("vehicle.train_slope_steepness")) {
    return AIGameSettings.GetValue("vehicle.train_slope_steepness");
  }
  if (AIGameSettings.IsValid("train_slope_steepness")) {
    return AIGameSettings.GetValue("train_slope_steepness");
  }
  return 3;
}

/* V294j : adaptation des coûts de pente et virage si la locomotive est trop faible.
 * Si la locomotive n'est pas connue à la création (engine == null), rien n'est appliqué. */
function OpexV294jApplySlopeEngineCosts(pathfinder, engine)
{
  if (V294_RAIL_SLOPE_ENGINE <= 0 || engine == null) return;
  if (!AIEngine.IsValidEngine(engine)) return;

  local slope = OpexTrainSlopeSteepness();
  local te = AIEngine.GetMaxTractiveEffort(engine);
  local isWeak = false;
  if (te < slope * 50) {
    isWeak = true;
  } else if (OpexIsMountainousMap() && AIEngine.GetPower(engine) < slope * 600) {
    isWeak = true;
  }

  if (isWeak) {
    pathfinder.cost.slope = 1500;
    pathfinder.cost.turn = 100;
  }
}

/* V294j : locomotive d'un candidat ou d'une ligne (entree de catalogue {id=...} ou identifiant
 * brut), null si inconnue. */
function OpexRailEngineOf(obj)
{
  if (obj == null || !("loco" in obj) || obj.loco == null) return null;
  if (typeof(obj.loco) == "table") return ("id" in obj.loco) ? obj.loco.id : null;
  if (typeof(obj.loco) == "integer") return obj.loco;
  return null;
}

/* V294a/d/j : options de l'A* rail, appliquees a la creation du pathfinder et a chaque
 * segment de la recherche segmentee. Au defaut (tout a 0), rien n'est touche. */
function OpexV294ApplyRailCosts(pathfinder, engine)
{
  if (V294_RAIL_BRIDGE_LEN > 0) {
    pathfinder.cost.max_bridge_length = V294_RAIL_BRIDGE_LEN;
    pathfinder.cost.max_tunnel_length = V294_RAIL_BRIDGE_LEN;
  }
  if (V294_RAIL_AAA_COSTS > 0) {
    /* Table d'AAAHogEx (pathfinder.nut:102-185) ; surcouts des ouvrages au-dela de 7 et 11 tuiles. */
    pathfinder.cost.diagonal_tile = 67;
    pathfinder.cost.bridge_per_tile = 100;
    pathfinder.cost.tunnel_per_tile = 0;
    pathfinder.cost.level_crossing = 900;
    pathfinder.cost.bridge_per_tile_ex = 200;
    pathfinder.cost.bridge_per_tile_ex2 = 400;
    pathfinder.cost.tunnel_per_tile_ex = 200;
    pathfinder.cost.tunnel_per_tile_ex2 = 300;
  }
  if (V294_RAIL_SLOPE_ENGINE > 0 && engine != null) OpexV294jApplySlopeEngineCosts(pathfinder, engine);
}

/* Cree le pathfinder. L'objet doit survivre entre les tours (stocke sur this._railSearch) :
 * FindPath(PATH_CHUNK) reprend exactement ou il s'etait arrete. Ne pas recreer a chaque tranche. */
function OpexCreateRailPathfinder(plansA, plansB, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null, engine = null)
{
  if (V307_SINK_ROOM > 0) ignoredTiles = OpexV307SinkRoomIgnoredTiles(plansA, plansB, ignoredTiles);
  local sources = [];
  local goals = [];
  /* Convention [lead, station_exit] aux deux bouts : node[0] est le vrai depart, node[1] le
   * predecesseur virtuel ; a l'arrivee la bibliotheque ajoute goal[1] apres goal[0]. */
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);
  if (sources.len() == 0 || goals.len() == 0) return null;
  if (weight == null) {
    local dist = 0;
    if (plansA.len() > 0 && plansB.len() > 0) {
      dist = AIMap.DistanceManhattan(plansA[0].lead, plansB[0].lead);
    }
    weight = OpexRailAstarWeight(dist);
  }
  local pathfinder;
  pathfinder = OpexNewRailPathfinderV129();
  pathfinder.cost.max_cost = PATHFINDER_MAX_COST;
  if (weight != null) {
    pathfinder.cost.astar_weight_pct = weight;
  }
  OpexV294ApplyRailCosts(pathfinder, engine);
  if (outwardSide != null) pathfinder._outwardSide = outwardSide;
  if (guideTiles != null) pathfinder._guideTiles = guideTiles;
  pathfinder.InitializePath(sources, goals, ignoredTiles == null ? [] : ignoredTiles);
  return pathfinder;
}

/* V294f : sonde inverse bornée à iterationCap iterations (sources = plansB, buts = plansA).
 * Si un chemin est trouvé, il est retourné inversé au format attendu par la pose. */
function OpexV294fReverseProbe(plansA, plansB, clearanceTiles, searchWeight, candidate, iterationCap)
{
  local engine = OpexRailEngineOf(candidate);
  local revPf = OpexCreateRailPathfinder(plansB, plansA, clearanceTiles, searchWeight, null, null, engine);
  if (revPf == null) {
    if (DECISION_LOG) {
      local manh = (candidate != null && ("distance" in candidate)) ? candidate.distance :
                   (plansA.len() > 0 && plansB.len() > 0 ? AIMap.DistanceManhattan(plansA[0].lead, plansB[0].lead) : 0);
      OpexDecide("V294F_PROBE", "ok=0 iters=0 manh=" + manh);
    }
    return null;
  }
  local revRes = revPf.FindPath(iterationCap);
  local iters = revPf.LastConsumed();
  local ok = (revRes != null && revRes != false);
  if (DECISION_LOG) {
    local manh = (candidate != null && ("distance" in candidate)) ? candidate.distance :
                 (plansA.len() > 0 && plansB.len() > 0 ? AIMap.DistanceManhattan(plansA[0].lead, plansB[0].lead) : 0);
    OpexDecide("V294F_PROBE", "ok=" + (ok ? 1 : 0) + " iters=" + iters + " manh=" + manh);
  }
  if (!ok) return null;
  local revTiles = OpexPathTiles(revRes);
  revTiles.reverse();
  return {
    path = revRes,
    tiles = revTiles,
    structures = [],
    iterations = iters,
    stop = "OK",
    done = true,
    segments = 1,
    backtracks = 0,
    localChoices = 0,
  };
}

/* Une tranche d'A*. `spent` est le cumul DEJA consomme (denominateur du classement : mesurer,
 * pas estimer, et surtout pas remettre a zero d'une tranche a l'autre). `sliceIters` borne
 * CETTE tranche ; passer iterationBudget reconstitue la boucle bloquante historique.
 * deadlineTick : en mode bloquant, la formule historique (iter/3 + marge) ; en mode
 * reprenable, RAIL_SEARCH_SAFETY_TICKS -- le budget d'iterations est la vraie borne. */
function OpexAdvanceRailPathfinder(pathfinder, spent, iterationBudget, deadlineTick, sliceIters)
{
  local path = false;
  local sliceSpent = 0;
  /* Aucun Sleep entre les chunks : AAAHogEx ne dort pas non plus (V236 a retire
   * pathfinder_sleep_ticks, toujours a 0). */
  while (path == false && spent < iterationBudget && sliceSpent < sliceIters
         && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(PATH_CHUNK);
    spent += PATH_CHUNK;
    sliceSpent += PATH_CHUNK;
  }

  /* Codes courts : un nom de panneau accepte au plus 31 caracteres et echoue SILENCIEUSEMENT
   * au-dela (verifie sur TrainLineAI). ABND = budget d'iterations epuise, c'est-a-dire l'arret
   * optimal qui a joue ; DEAD = fenetre de temps epuisee ; NOPA = file vide, aucun chemin.
   * CONT = tranche epuisee, la recherche n'est pas finie -- ne jamais rapporter ce code au
   * classement, seulement reprendre au tour suivant. */
  local stop = "OK";
  local done = true;
  if (path == false) {
    /* Meme priorite que l'historique : DEAD gagne si les deux bornes sont franchies. */
    if (AIController.GetTick() >= deadlineTick) stop = "DEAD";
    else if (spent >= iterationBudget) stop = "ABND";
    else { stop = "CONT"; done = false; }
  } else if (path == null) {
    stop = "NOPA";
  }
  if (V294_RAIL_CONTINUOUS > 0) {
    local tiles = null;
    local structures = null;
    if (stop == "OK" && path != null && path != false) {
      tiles = OpexPathTiles(path);
      structures = [];
    }
    return {
      path = path,
      tiles = tiles,
      structures = structures,
      iterations = spent,
      stop = stop,
      done = done,
      segments = 1,
      backtracks = 0,
      localChoices = 0,
    };
  }
  return { path = path, iterations = spent, stop = stop, done = done };
}

/* Convertit une chaine AyStar en ordre de construction. Copie obligatoire : le segment suivant
 * repart d'un RailPathFinder neuf, et les noeuds du segment precedent meurent avec FindPath. */
function OpexSegmentTiles(node)
{
  local tiles = [];
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  local simplified = [];
  foreach (tile in tiles) {
    if (simplified.len() >= 2 && simplified[simplified.len() - 2] == tile) {
      simplified.pop();
    } else if (simplified.len() == 0 || simplified[simplified.len() - 1] != tile) {
      simplified.push(tile);
    }
  }
  return simplified;
}

/* Squirrel 3.0 ne capture pas les locales englobantes. clone() est refuse ; une copie
 * explicite rend les checkpoints de retour arriere independants. */
function OpexCopySegmentTiles(tiles)
{
  local copied = [];
  foreach (tile in tiles) copied.push(tile);
  return copied;
}

/* Une paire de tuiles eloignees peut etre un pont OU l'entree d'un tunnel naturel.
 * GetOtherTunnelEnd au moment de poser a produit TRKFAIL (prototype 4/9 -> 7/9,
 * 2026-09-03). Le kind retenu sous AITestMode doit voyager jusqu'a la construction. */
function OpexCopySegmentStructures(structures)
{
  local copied = [];
  foreach (structure in structures) {
    copied.push({ from = structure.from, to = structure.to, kind = structure.kind,
        length = structure.length });
  }
  return copied;
}

function OpexPlannedStructureKind(structures, fromTile, toTile)
{
  if (structures == null) return null;
  foreach (structure in structures) {
    if (structure.from == fromTile && structure.to == toTile) return structure.kind;
  }
  return null;
}

/* Un nouveau segment a un closed set vide. Sans ce garde, il reentre le prefixe deja
 * planifie et la pose boucle (TRKFAIL). Les deux dernieres cases restent autorisees :
 * elles sont la source directionnelle du segment. */
function OpexCanAppendSegment(prefix, tail)
{
  if (prefix == null) return true;
  local seen = {};
  /* tail[0..1] sont les deux cases directionnelles deja presentes dans prefix ; elles ne sont
   * jamais testees ci-dessous. Toute REAPPARITION ulterieure, y compris sur ces deux cases, est
   * une vraie boucle et doit etre refusee. Ajouter aussi chaque tuile du tail au fur et a mesure
   * ferme les boucles internes d'un segment. */
  for (local i = 0; i < prefix.len(); i++) seen[prefix[i]] <- true;
  for (local i = 2; i < tail.len(); i++) {
    if (tail[i] in seen) return false;
    seen[tail[i]] <- true;
  }
  return true;
}

/* Tuiles interdites au NOUVEAU segment A*. Les deux dernieres cases du prefix sont precisement
 * sa source directionnelle [front, previous] et ne doivent pas etre fermees avant InitializePath.
 * Le garde OpexCanAppendSegment ci-dessus interdit quand meme d'y revenir plus tard dans le tail.
 * Fusionner plutot que remplacer les ignoredTiles du caller conserve les autres contraintes. */
function OpexSegmentIgnoredTiles(state)
{
  local merged = [];
  local seen = {};
  if (state.ignoredTiles != null) {
    foreach (tile in state.ignoredTiles) {
      if (tile in seen) continue;
      seen[tile] <- true;
      merged.push(tile);
    }
  }
  if (state.prefix != null) {
    local limit = state.prefix.len() - 2;
    if (limit < 0) limit = 0;
    for (local i = 0; i < limit; i++) {
      local tile = state.prefix[i];
      if (tile in seen) continue;
      seen[tile] <- true;
      merged.push(tile);
    }
  }
  return merged;
}

function OpexSegmentPrefixContains(prefix, tile)
{
  if (prefix == null) return false;
  foreach (known in prefix) {
    if (known == tile) return true;
  }
  return false;
}

/* Extraire K minima par un petit front d'indices, sans retirer de noeud et sans
 * closure. Trier toute la file etait O(n log n) a chaque coupure et mangeait la
 * fenetre avant le prochain FindPath. */
function OpexFrontierAlternatives(pathfinder, maxAlternatives)
{
  if ("FrontierAlternatives" in pathfinder) return pathfinder.FrontierAlternatives(maxAlternatives);
  local open = pathfinder._pathfinder._open;
  if (open == null || open.Count() == 0) return [];
  local nodes = [];
  local seen = {};
  local candidates = [0];
  while (candidates.len() > 0 && nodes.len() < maxAlternatives) {
    local bestPosition = 0;
    local bestPriority = open._prios[candidates[0]];
    for (local i = 1; i < candidates.len(); i++) {
      local priority = open._prios[candidates[i]];
      if (priority < bestPriority) {
        bestPosition = i;
        bestPriority = priority;
      }
    }
    local heapIndex = candidates[bestPosition];
    candidates[bestPosition] = candidates[candidates.len() - 1];
    candidates.pop();
    local left = heapIndex * 2 + 1;
    local right = left + 1;
    if (left < open.Count()) candidates.push(left);
    if (right < open.Count()) candidates.push(right);
    local node = open._items[heapIndex];
    local key = node.GetTile() + ":" + node.GetDirection();
    if (key in seen) continue;
    seen[key] <- true;
    nodes.push(node);
  }
  return nodes;
}

/* Centre des station_exit de plansB : OpexAI a plusieurs buts, pas un centre-ville. */
function OpexDestinationCenter(plansB)
{
  local sumX = 0;
  local sumY = 0;
  local n = 0;
  foreach (plan in plansB) {
    sumX += AIMap.GetTileX(plan.station_exit);
    sumY += AIMap.GetTileY(plan.station_exit);
    n++;
  }
  if (n <= 0) return 0;
  return AIMap.GetTileIndex(sumX / n, sumY / n);
}

/* Ponts 3-20 et tunnels, sous AITestMode, UNIQUEMENT si le rail ne peut pas
 * continuer dans l'axe. Sonder 18 ponts a chaque coupure sans obstacle epuisait
 * la fenetre et mourait sans exception (piege 1 du prototype). */
function OpexLocalStructureChoices(front, previous, destinationCenter, state)
{
  local choices = [];
  local distance = AIMap.DistanceManhattan(front, previous);
  if (distance <= 0) return choices;
  local step = (front - previous) / distance;
  local before = AIMap.DistanceManhattan(front, destinationCenter);
  local next = front + step;
  if (!AIMap.IsValidTile(next)) return choices;

  local canContinue = false;
  {
    local testMode = AITestMode();
    canContinue = AIRail.BuildRail(previous, front, next);
  }
  if (canContinue) return choices;

  for (local length = SEGMENTED_BRIDGE_MIN_LEN; length <= SEGMENTED_BRIDGE_MAX_LEN; length++) {
    local target = front + (length - 1) * step;
    if (!AIMap.IsValidTile(target) || AIMap.DistanceManhattan(target, destinationCenter) >= before) {
      continue;
    }
    local bridges = AIBridgeList_Length(length);
    if (bridges.IsEmpty()) continue;
    OpexBridgeSortBySpeed(bridges);
    local usable = false;
    {
      local testMode = AITestMode();
      usable = AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), front, target);
    }
    if (usable) {
      choices.push({ to = target, kind = "bridge", length = length });
      state.bridgeTests++;
    }
  }

  local tunnelEnd = AITunnel.GetOtherTunnelEnd(front);
  if (AIMap.IsValidTile(tunnelEnd)) {
    local tunnelDistance = AIMap.DistanceManhattan(front, tunnelEnd);
    if (tunnelDistance >= 2 && tunnelDistance + 1 <= SEGMENTED_BRIDGE_MAX_LEN &&
        (tunnelEnd - front) / tunnelDistance == step &&
        AIMap.DistanceManhattan(tunnelEnd, destinationCenter) < before) {
      local usable = false;
      {
        local testMode = AITestMode();
        usable = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, front);
      }
      if (usable) {
        choices.push({ to = tunnelEnd, kind = "tunnel", length = tunnelDistance + 1 });
        state.tunnelTests++;
      }
    }
  }
  return choices;
}

function OpexSegmentedResult(state, path, stop, done)
{
  local tiles = null;
  local structures = null;
  if (stop == "OK") {
    tiles = state.prefix;
    structures = state.structures;
  }
  return {
    path = path,
    tiles = tiles,
    structures = structures,
    iterations = state.iterations,
    stop = stop,
    done = done,
    segments = state.segments,
    backtracks = state.backtracks,
    localChoices = state.localChoices,
  };
}

/* V294c : le but A* est goal[0] (lead), goal[1] etant le voisin de gare
 * ajoute une fois le but atteint. Plusieurs quais B sont possibles. */
function OpexV294cGoalDistance(state, tile)
{
  local nearest = null;
  foreach (goal in state.goals) {
    local dist = AIMap.DistanceManhattan(tile, goal[0]);
    if (nearest == null || dist < nearest) nearest = dist;
  }
  return nearest == null ? 0 : nearest;
}

function OpexV294cSourceDistance(state)
{
  local nearest = null;
  foreach (source in state.activeSources) {
    local dist = OpexV294cGoalDistance(state, source[0]);
    if (nearest == null || dist < nearest) nearest = dist;
  }
  return nearest == null ? 0 : nearest;
}

/* 0 = poids N, 1 = poids V172 historique, 2 = A* standard a 100 %.
 * Toute progression >= 10 % de la distance au depart du segment remet N. */
function OpexV294cSwitchWeight(state, stalled, remaining)
{
  if (stalled) {
    if (state.v294cTier < 2) state.v294cTier++;
  } else {
    state.v294cTier = 0;
  }
  local nextWeight = V294C_RAIL_WEIGHT_ADAPT;
  if (state.v294cTier == 1) nextWeight = state.weight;
  else if (state.v294cTier == 2) nextWeight = 100;
  if (nextWeight != state.v294cWeight) {
    state.v294cSwitches++;
    if (nextWeight < state.v294cMin) state.v294cMin = nextWeight;
    if (DECISION_LOG) {
      OpexDecide("V294C", "event=weight from=" + state.v294cWeight + " to=" + nextWeight
          + " seg=" + state.segments + " remaining=" + remaining);
    }
  }
  state.v294cWeight = nextWeight;
}

/* NOPA local : une derniere exploration plus large n'est possible que tant
 * qu'il reste du budget et un niveau de repli. Ne jamais remettre les compteurs
 * d'iterations a zero. */
function OpexV294cRetryNoPath(state, deadlineTick)
{
  if (state.v294cTier >= 2 || state.iterations >= state.iterationBudget ||
      state.iterations >= state.timeSafe || AIController.GetTick() >= deadlineTick) return false;
  /* Un palier de meme poids rejouerait exactement la meme recherche : passer au suivant. */
  local before = state.v294cWeight;
  local remaining = OpexV294cSourceDistance(state);
  while (state.v294cTier < 2 && state.v294cWeight == before) OpexV294cSwitchWeight(state, true, remaining);
  if (state.v294cWeight == before) return false;
  state.pathfinder = null;
  state.segmentPath = false;
  state.segmentUsed = 0;
  return true;
}

function OpexTrySegmentedBacktrack(state)
{
  if (state.alternatives.len() > 0 && state.backtracks < SEGMENTED_MAX_BACKTRACKS) {
    local alternative = state.alternatives.pop();
    state.prefix = OpexCopySegmentTiles(alternative.prefix);
    state.structures = OpexCopySegmentStructures(alternative.structures);
    state.activeSources = alternative.sources;
    if (V294C_RAIL_WEIGHT_ADAPT > 0) {
      OpexV294cSwitchWeight(state, true, OpexV294cSourceDistance(state));
    }
    state.backtracks++;
    state.nextSegmentLimit = SEGMENTED_RECOVERY_ITERS;
    state.pathfinder = null;
    state.segmentPath = false;
    state.segmentUsed = 0;
    return true;
  }
  return false;
}

/* Cree l'etat d'une recherche segmentee. Table passee en parametre : Squirrel ici
 * ne capture pas les locales englobantes (piege 6). pathfinder reste null jusqu'au
 * premier segment : le closed set ne survit jamais d'un segment a l'autre. */
function OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null, engine = null)
{
  if (V307_SINK_ROOM > 0) ignoredTiles = OpexV307SinkRoomIgnoredTiles(plansA, plansB, ignoredTiles);
  local sources = [];
  local goals = [];
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);
  if (sources.len() == 0 || goals.len() == 0) return null;

  /* timeSafe = min(50 000, budget). Sous A3 le budget vaut 5k-10k, donc se confond
   * avec iterationBudget ; le plafond historique reste pour un cap plus haut. */
  local timeSafe = SEGMENTED_TIME_SAFE_ITERS;
  if (iterationBudget < timeSafe) timeSafe = iterationBudget;

  if (weight == null) {
    local dist = 0;
    if (plansA.len() > 0 && plansB.len() > 0) {
      dist = AIMap.DistanceManhattan(plansA[0].lead, plansB[0].lead);
    }
    weight = OpexRailAstarWeight(dist);
  }

  local state = {
    activeSources = sources,
    goals = goals,
    ignoredTiles = ignoredTiles == null ? [] : ignoredTiles,
    destinationCenter = OpexDestinationCenter(plansB),
    prefix = null,
    structures = [],
    alternatives = [],
    nextSegmentLimit = SEGMENTED_SEGMENT_ITERS,
    currentSegmentLimit = SEGMENTED_SEGMENT_ITERS,
    pathfinder = null,
    segmentPath = false,
    segmentUsed = 0,
    iterations = 0,
    iterationBudget = iterationBudget,
    timeSafe = timeSafe,
    segments = 0,
    backtracks = 0,
    localChoices = 0,
    bridgeTests = 0,
    tunnelTests = 0,
    weight = weight,
    bridgeLen = (V294_RAIL_BRIDGE_LEN > 0) ? V294_RAIL_BRIDGE_LEN : null,
    outwardSide = outwardSide,
    guideTiles = guideTiles,
    engine = engine,
  };
  if (V294C_RAIL_WEIGHT_ADAPT > 0) {
    state.v294cWeight <- V294C_RAIL_WEIGHT_ADAPT;
    state.v294cTier <- 0;
    state.v294cLastDist <- OpexV294cSourceDistance(state);
    state.v294cMin <- V294C_RAIL_WEIGHT_ADAPT;
    state.v294cSwitches <- 0;
    if (DECISION_LOG && state.v294cWeight != state.weight) {
      OpexDecide("V294C", "event=weight from=" + state.weight + " to=" + state.v294cWeight
          + " seg=0 remaining=" + state.v294cLastDist);
    }
  }
  return state;
}

/* Une tranche de recherche segmentee. `state.iterations` est le denominateur du
 * classement : uniquement les vrais FindPath(1), cumules sur TOUS les segments et
 * TOUS les retours arriere, jamais remis a zero (piege 4).
 *
 * Slice : si FindPath s'arrete parce que sliceIters est epuise ALORS que le
 * segment court encore et que budget/deadline restent, CONT + garder le meme
 * pathfinder, SANS traiter la frontiere. Un segment fini (null ou 2000) est
 * traite comme le prototype, meme en mode reprenable. */
function OpexAdvanceSegmentedSearch(state, sliceIters, deadlineTick)
{
  local sliceSpent = 0;

  while (state.iterations < state.iterationBudget &&
         state.iterations < state.timeSafe &&
         AIController.GetTick() < deadlineTick &&
         sliceSpent < sliceIters) {
    if (state.pathfinder == null) {
      state.segments++;
      state.currentSegmentLimit = state.nextSegmentLimit;
      state.nextSegmentLimit = SEGMENTED_SEGMENT_ITERS;
      if (V294C_RAIL_WEIGHT_ADAPT > 0) {
        state.v294cLastDist = OpexV294cSourceDistance(state);
      }
      local pathfinder;
      pathfinder = OpexNewRailPathfinderV129();
      /* Table de cout inchangee : seulement max_cost, comme l'A* classique. */
      pathfinder.cost.max_cost = PATHFINDER_MAX_COST;
      if (V294C_RAIL_WEIGHT_ADAPT > 0) {
        pathfinder.cost.astar_weight_pct = state.v294cWeight;
      } else if (("weight" in state) && state.weight != null) {
        pathfinder.cost.astar_weight_pct = state.weight;
      }
      OpexV294ApplyRailCosts(pathfinder, ("engine" in state) ? state.engine : null);
      if (("outwardSide" in state) && state.outwardSide != null) pathfinder._outwardSide = state.outwardSide;
      if (("guideTiles" in state) && state.guideTiles != null) pathfinder._guideTiles = state.guideTiles;
      /* V214 : le coude serre ramene a 100 sous 40 tuiles se juge sur le trajet complet, pas sur
       * les sources intermediaires d'un segment. */
      if (V214_RAIL_TIGHT_TURN_COST > 0 && ("_v214RouteDist" in pathfinder)) {
        if (!("v214RouteDist" in state)) state.v214RouteDist <- OpexV214RouteDistance(state.activeSources, state.goals);
        pathfinder._v214RouteDist = state.v214RouteDist;
      }
      local ignored = OpexSegmentIgnoredTiles(state);
      pathfinder.InitializePath(state.activeSources, state.goals, ignored);
      state.pathfinder = pathfinder;
      state.segmentPath = false;
      state.segmentUsed = 0;
    }

    {
      /* V129 : FindPath(n) groupe. n est borne par TOUTES les limites de la boucle historique
       * (segment, budget, timeSafe, tranche) et le nombre d'iterations reellement consommees est
       * relu (LastConsumed) : memes totaux et meme point d'arret. Seule l'echeance au tick, relue
       * entre deux groupes, peut depasser de n-1 iterations au plus lorsqu'elle est franchie. */
      while (state.segmentPath == false &&
             state.segmentUsed < state.currentSegmentLimit &&
             state.iterations < state.iterationBudget &&
             state.iterations < state.timeSafe &&
             AIController.GetTick() < deadlineTick &&
             sliceSpent < sliceIters) {
        local n = V129_RAIL_BATCH_ITERS;
        if (state.currentSegmentLimit - state.segmentUsed < n) n = state.currentSegmentLimit - state.segmentUsed;
        if (state.iterationBudget - state.iterations < n) n = state.iterationBudget - state.iterations;
        if (state.timeSafe - state.iterations < n) n = state.timeSafe - state.iterations;
        if (sliceIters - sliceSpent < n) n = sliceIters - sliceSpent;
        state.segmentPath = state.pathfinder.FindPath(n);
        local used = state.pathfinder.LastConsumed();
        state.segmentUsed += used;
        state.iterations += used;
        sliceSpent += used;
      }
    }
    while (state.segmentPath == false &&
           state.segmentUsed < state.currentSegmentLimit &&
           state.iterations < state.iterationBudget &&
           state.iterations < state.timeSafe &&
           AIController.GetTick() < deadlineTick &&
           sliceSpent < sliceIters) {
      state.segmentPath = state.pathfinder.FindPath(1);
      state.segmentUsed++;
      state.iterations++;
      sliceSpent++;
    }

    local path = state.segmentPath;
    if (path != false && path != null) {
      local tail = OpexSegmentTiles(path);
      /* Le dernier segment etait le seul a echapper au garde anti-reentree applique aux coupures
       * intermediaires. Il pouvait donc revenir sur une tuile du prefixe, passer le devis en
       * AITestMode (les poses simulees ne persistent pas), puis casser la pose reelle quand la
       * meme tuile etait rencontree une seconde fois. Meme contrat que les segments intermediaires :
       * tenter d'abord un checkpoint de backtrack, sinon aucun chemin valide pour ce search. */
      if (state.prefix != null && !OpexCanAppendSegment(state.prefix, tail)) {
        state.pathfinder = null;
        state.segmentPath = false;
        if (OpexTrySegmentedBacktrack(state)) continue;
        if (V294C_RAIL_WEIGHT_ADAPT > 0 && OpexV294cRetryNoPath(state, deadlineTick)) continue;
        return OpexSegmentedResult(state, null, "NOPA", true);
      }
      if (state.prefix == null) state.prefix = tail;
      else for (local i = 2; i < tail.len(); i++) state.prefix.push(tail[i]);
      state.pathfinder = null;
      return OpexSegmentedResult(state, path, "OK", true);
    }

    if (path == null) {
      state.pathfinder = null;
      if (OpexTrySegmentedBacktrack(state)) continue;
      /* V294c : pas de reprise a poids plus bas ici. Le tas s'est vide : tout ce qui est
       * atteignable sous max_cost a ete ferme, et max_cost elague sur g (v129.nut:649), pas sur
       * f ; le poids ne change que l'ordre d'exploration, la reprise repaierait la recherche. */
      return OpexSegmentedResult(state, null, "NOPA", true);
    }

    /* path == false : le segment n'a pas abouti. */
    if (state.segmentUsed < state.currentSegmentLimit) {
      /* Segment encore en cours : slice, budget ou deadline. */
      if (state.iterations < state.iterationBudget &&
          state.iterations < state.timeSafe &&
          AIController.GetTick() < deadlineTick) {
        return OpexSegmentedResult(state, false, "CONT", false);
      }
      if (AIController.GetTick() >= deadlineTick) {
        return OpexSegmentedResult(state, false, "DEAD", true);
      }
      return OpexSegmentedResult(state, false, "ABND", true);
    }

    /* Coupure a 2000 (ou 10000 en reprise). Empiler 3 alternatives a CHAQUE
     * coupure, pas seulement aux obstacles : sinon la pile reste vide et
     * backtracks=0 / local_choices=0 (piege 3, echec initial du prototype). */
    local frontier = OpexFrontierAlternatives(state.pathfinder, SEGMENTED_FRONTIER_WIDTH * 4);
    state.pathfinder = null;
    local usable = [];
    foreach (node in frontier) {
      local candidateTail = OpexSegmentTiles(node);
      if (candidateTail.len() < 3 || !OpexCanAppendSegment(state.prefix, candidateTail)) continue;
      usable.push({ tail = candidateTail });
      if (usable.len() >= SEGMENTED_FRONTIER_WIDTH) break;
    }
    if (usable.len() == 0) {
      if (OpexTrySegmentedBacktrack(state)) continue;
      if (V294C_RAIL_WEIGHT_ADAPT > 0 && OpexV294cRetryNoPath(state, deadlineTick)) continue;
      return OpexSegmentedResult(state, null, "NOPA", true);
    }

    local tail = usable[0].tail;
    if (V294C_RAIL_WEIGHT_ADAPT > 0) {
      local remaining = OpexV294cGoalDistance(state, tail[tail.len() - 1]);
      local progress = state.v294cLastDist - remaining;
      OpexV294cSwitchWeight(state, progress * 10 < state.v294cLastDist, remaining);
    }
    /* Moins bon -> meilleur : Pop() essaie le deuxieme noeud tout de suite. */
    for (local i = usable.len() - 1; i >= 1; i--) {
      local alternativeTail = usable[i].tail;
      local alternativePrefix = state.prefix == null ? OpexCopySegmentTiles(alternativeTail) :
          OpexCopySegmentTiles(state.prefix);
      if (state.prefix != null) {
        for (local j = 2; j < alternativeTail.len(); j++) alternativePrefix.push(alternativeTail[j]);
      }
      if (alternativePrefix.len() < 2) continue;
      local alternativeFront = alternativePrefix[alternativePrefix.len() - 1];
      local alternativePrevious = alternativePrefix[alternativePrefix.len() - 2];
      state.alternatives.push({ prefix = alternativePrefix,
          structures = OpexCopySegmentStructures(state.structures),
          sources = [[alternativeFront, alternativePrevious]] });
    }

    if (state.prefix == null) state.prefix = tail;
    else for (local i = 2; i < tail.len(); i++) state.prefix.push(tail[i]);

    local front = state.prefix[state.prefix.len() - 1];
    local previous = state.prefix[state.prefix.len() - 2];
    local choices = OpexLocalStructureChoices(front, previous, state.destinationCenter, state);
    local nonLoopChoices = [];
    foreach (choice in choices) {
      if (!OpexSegmentPrefixContains(state.prefix, choice.to)) nonLoopChoices.push(choice);
    }
    if (nonLoopChoices.len() > 0) {
      for (local i = nonLoopChoices.len() - 1; i >= 1; i--) {
        local alternativePrefix = OpexCopySegmentTiles(state.prefix);
        alternativePrefix.push(nonLoopChoices[i].to);
        local alternativeStructures = OpexCopySegmentStructures(state.structures);
        alternativeStructures.push({ from = front, to = nonLoopChoices[i].to,
            kind = nonLoopChoices[i].kind, length = nonLoopChoices[i].length });
        state.alternatives.push({ prefix = alternativePrefix, structures = alternativeStructures,
            sources = [[nonLoopChoices[i].to, front]] });
      }
      state.prefix.push(nonLoopChoices[0].to);
      state.structures.push({ from = front, to = nonLoopChoices[0].to,
          kind = nonLoopChoices[0].kind, length = nonLoopChoices[0].length });
      state.activeSources = [[nonLoopChoices[0].to, front]];
      state.localChoices++;
    } else {
      state.activeSources = [[front, previous]];
    }
  }

  if (AIController.GetTick() >= deadlineTick) {
    return OpexSegmentedResult(state, false, "DEAD", true);
  }
  if (state.iterations >= state.timeSafe || state.iterations >= state.iterationBudget) {
    return OpexSegmentedResult(state, false, "ABND", true);
  }
  return OpexSegmentedResult(state, false, "CONT", false);
}

/* Recherche de chemin sous budget d'iterations. Rend une table avec le chemin brut et le compte
 * d'iterations reellement consommees -- ce compte est le DENOMINATEUR du classement, il doit etre
 * mesure, pas estime.
 *
 * Mode BLOQUANT (rail_search_resumable=0, defaut) : reconstitue la boucle historique. C'est
 * cette boucle qui gelait l'IA des mois entiers (7 mois, graine 100, juin-dec 1971) : la
 * bibliotheque rendait la main toutes les 50 iterations et on la reprenait aussitot, donc
 * _runNextTask ne tournait plus. Le mode reprenable vit dans OpexAI::_continueRailSearch.
 *
 * rail_segmented_search=1 : meme enveloppe, mais chaque A* vise les quais finals et s'arrete
 * a 2000 iterations. Defaut 0 = A* classique inchange (table de cout, plafond A3). */
function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null)
{
  local res;
  {
    local state = OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles, weight, outwardSide, guideTiles);
    if (state == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=blocking outcome=NOPA iters=0 budget=" + iterationBudget);
      return { path = null, iterations = 0, stop = "NOPA" };
    }
    /* sliceIters = iterationBudget : une seule avancee jusqu'au chemin / ABND / DEAD / NOPA. */
    res = OpexAdvanceSegmentedSearch(state, iterationBudget, deadlineTick);
  }
  if (DECISION_LOG) {
    OpexDecide("RAIL_SEARCH", "type=blocking outcome=" + res.stop + " iters=" + res.iterations + " budget=" + iterationBudget);
  }
  return res;
}

/* Deplie le chemin en liste de tuiles, en supprimant les allers-retours d'une tuile que le
 * pathfinder produit quand plusieurs directions d'entree sont proposees. */
function OpexPathTiles(path)
{
  local tiles = [];
  local node = path;
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  local simplified = [];
  foreach (tile in tiles) {
    if (simplified.len() >= 2 && simplified[simplified.len() - 2] == tile) {
      simplified.pop();
      continue;
    }
    if (simplified.len() == 0 || simplified[simplified.len() - 1] != tile) simplified.push(tile);
  }
  return simplified;
}

/* V214 : distance Manhattan minimale entre sources et buts d'une recherche ([tuile, voisine]). */
function OpexV214RouteDistance(sources, goals)
{
  local best = -1;
  foreach (s in sources) {
    foreach (g in goals) {
      local d = AIMap.DistanceManhattan(s[0], g[0]);
      if (best < 0 || d < best) best = d;
    }
  }
  return best;
}

/* V214 : geometrie d'un trace trouve, sur les pas unitaires (un pont ou un tunnel coupe la
 * fenetre). turns = changements de 45 degres (regle historique : 50 chacun), exits = sorties de
 * diagonale (regle AAA), tight = coudes de 90 degres pris sur une seule tuile. */
function OpexV214PathGeometry(tiles)
{
  local steps = 0;
  local turns = 0;
  local exits = 0;
  local tight = 0;
  local n = tiles.len();
  for (local i = 0; i + 1 < n; i++) {
    if (AIMap.DistanceManhattan(tiles[i], tiles[i + 1]) == 1) steps++;
  }
  for (local i = 0; i + 3 < n; i++) {
    if (AIMap.DistanceManhattan(tiles[i], tiles[i + 3]) != 3) continue;
    local s0 = tiles[i + 1] - tiles[i];
    local s1 = tiles[i + 2] - tiles[i + 1];
    local s2 = tiles[i + 3] - tiles[i + 2];
    if (s0 != s2) {
      turns++;
      if (s1 != s0) exits++;
    }
    if (i + 4 < n && AIMap.DistanceManhattan(tiles[i], tiles[i + 4]) == 4) {
      local s3 = tiles[i + 4] - tiles[i + 3];
      if (s0 == s1 && s2 == s3 && s1 != s2) tight++;
    }
  }
  return { steps = steps, turns = turns, exits = exits, tight = tight };
}

/* Un succes segmente porte `tiles` (prefixe complet, y compris ponts/tunnels locaux)
 * et pas seulement le dernier noeud AyStar. L'A* classique n'a pas ce champ. */
function OpexResolveSearchTiles(search)
{
  if (("tiles" in search) && search.tiles != null) return search.tiles;
  if (search.path == false || search.path == null) return [];
  return OpexPathTiles(search.path);
}

function OpexResolveSearchStructures(search)
{
  if (("structures" in search) && search.structures != null) return search.structures;
  return [];
}

function OpexMatchPlan(plans, tile)
{
  foreach (plan in plans) {
    if (plan.station_exit == tile) return plan;
  }
  return null;
}

/* Version stricte utilisee seulement sous RAIL_GEOMETRY_GUARD. Plusieurs plans peuvent partager
 * station_exit avec une orientation/lead differents. Le pathfinder choisit la paire complete
 * [lead, station_exit] : la reconstruction doit conserver cette identite. */
function OpexMatchPlanExact(plans, tile, lead)
{
  foreach (plan in plans) {
    if (plan.station_exit == tile && ("lead" in plan) && plan.lead == lead) return plan;
  }
  return null;
}

/* Recalcule uniquement la GEOMETRIE DE QUAI autour d'un chemin A* deja paye. Le chemin definit
 * l'interface physique [lead, station_exit] aux deux bouts ; une nouvelle implantation n'est
 * acceptable que si elle expose exactement la meme interface et conserve la meme longueur de
 * quai, donc les memes hypotheses economiques. Aucun pathfinder n'est appele ici. */
function OpexRailRefreshExactPlatforms(catalog, candidate, plan)
{
  if (plan == null || !("tiles" in plan) || plan.tiles == null || plan.tiles.len() < 3) {
    return { ok = false, reason = "invalid_plan" };
  }
  local fresh = OpexRailPlatformPlans(catalog, candidate);
  if (fresh.plansA == null || fresh.reason != "OK") {
    return { ok = false, reason = fresh.reason };
  }
  if (fresh.length != plan.length) {
    return { ok = false, reason = "length_changed" };
  }
  local tiles = plan.tiles;
  local last = tiles.len() - 1;
  local planA = OpexMatchPlanExact(fresh.plansA, tiles[0], tiles[1]);
  local planB = OpexMatchPlanExact(fresh.plansB, tiles[last], tiles[last - 1]);
  if (planA == null || planB == null) {
    return { ok = false, reason = "exact_interface_missing" };
  }
  if (RAIL_GEOMETRY_PREFILTER) {
    local geometryIssue = OpexRailPathGeometryIssue(tiles, planA, planB);
    if (geometryIssue != null) {
      return { ok = false, reason = "geometry_" + geometryIssue.kind };
    }
  }
  plan.plansA = fresh.plansA;
  plan.plansB = fresh.plansB;
  plan.planA = planA;
  plan.planB = planB;
  return { ok = true, reason = "ok" };
}

function OpexRailPlanContainsTile(plan, tile)
{
  if (plan == null || !("anchor" in plan) || !("step" in plan) || !("length" in plan)) return false;
  for (local i = 0; i < plan.length; i++) {
    if (plan.anchor + plan.step * i == tile) return true;
  }
  return false;
}

/* V153 : connectivite terminale rail supportant un saut (pont/tunnel) vers le lead.
 * outer : tuile de sortie de gare (plan.station_exit)
 * lead : tuile d'approche / tete de pont (tiles[1] cote A, tiles[last-1] cote B)
 * inner : tuile adjacente au trace (tiles[2] cote A, tiles[last-2] cote B) */
function OpexRailEndConnected(outer, lead, inner, side = null)
{
  if (AIMap.DistanceManhattan(lead, inner) <= 1) {
    return AIRail.AreTilesConnected(outer, lead, inner);
  }

  local kind = "none";
  if (AIBridge.IsBridgeTile(lead) && AIBridge.GetOtherBridgeEnd(lead) == inner) {
    kind = "bridge";
  } else if (AITunnel.IsTunnelTile(lead) && AITunnel.GetOtherTunnelEnd(lead) == inner) {
    kind = "tunnel";
  }

  local ok = false;
  if (kind != "none") {
    local d = AIMap.DistanceManhattan(lead, inner);
    local unit = (lead - inner) / d;
    if (outer == lead + unit) {
      local nextTile = outer + unit;
      if (AIMap.IsValidTile(nextTile)) {
        ok = AIRail.AreTilesConnected(lead, outer, nextTile);
      } else {
        ok = AIRail.IsRailTile(outer);
      }
    }
  }

  if (DECISION_LOG) {
    local sideStr = (side != null) ? side : "none";
    OpexDecide("RAIL_END_JUMP", "side=" + sideStr + " ok=" + (ok ? 1 : 0)
        + " kind=" + kind + " lead=" + lead + " inner=" + inner + " outer=" + outer);
  }

  return ok;
}

/* Invariants geometriques verifies APRES l'A* mais AVANT tout devis/terrassement reel.
 * 1) le lead choisi par le chemin ne doit appartenir a aucune des deux emprises de gare qui
 *    seront effectivement construites ;
 * 2) a l'arrivee B, un saut pont/tunnel vers le lead fait entrer OpexBuildTrack dans la branche
 *    "autre bout d'un franchissement deja pose" au dernier i : la transition lead->gare est alors
 *    ni posee ni verifiee. Cote A, le lead est traite AVANT le saut et ce skip n'existe pas ; ne
 *    pas bannir symetriquement un cas potentiellement constructible sans preuve. */
function OpexRailPathGeometryIssue(tiles, planA, planB)
{
  if (tiles == null || tiles.len() < 3 || planA == null || planB == null) return null;
  local last = tiles.len() - 1;
  local leadA = tiles[1];
  local leadB = tiles[last - 1];
  if (OpexRailPlanContainsTile(planA, leadA) || OpexRailPlanContainsTile(planB, leadA)) {
    return { kind = "lead_a_station", tile = leadA };
  }
  if (OpexRailPlanContainsTile(planA, leadB) || OpexRailPlanContainsTile(planB, leadB)) {
    return { kind = "lead_b_station", tile = leadB };
  }
  if (AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1) {
    return { kind = "end_jump", tile = leadB };
  }
  return null;
}

/* Fallback apres pose : ne classe persistant que la signature instrumentee le 03/10,
 * ERR_AREA_NOT_CLEAR sur le lead devenu NOTRE tuile de gare. Un TRKFAIL generique, une erreur
 * vehicule ou une autre occupation ne sont pas memorises par ce garde. */
function OpexRailTrackFailureIsPersistentGeometry(failure, planA, planB)
{
  if (failure == null || !("error" in failure) || !("tile" in failure)) return false;
  if (failure.error != AIError.ERR_AREA_NOT_CLEAR) return false;
  if (!("is_station" in failure) || failure.is_station != 1) return false;
  if (!("owner_self" in failure) || failure.owner_self != 1) return false;
  local leadA = (planA != null && ("lead" in planA)) ? planA.lead : null;
  local leadB = (planB != null && ("lead" in planB)) ? planB.lead : null;
  return failure.tile == leadA || failure.tile == leadB;
}

/* Une voie parallele d'upgrade doit rester une branche independante. Le pathfinder peut donner
 * un cout faible a un rail deja pose ; l'accepter fabriquerait un aiguillage implicite que le
 * rollback ne pourrait pas restaurer. Les deux sorties de quai (indices 0 et last) sont exclues. */
function OpexJoinPathIsDedicated(tiles)
{
  for (local i = 1; i < tiles.len() - 1; i++) {
    local tile = tiles[i];
    if (AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) {
      return false;
    }
  }
  return true;
}

function OpexPlanHitsSet(plan, forbidden)
{
  if (plan.lead in forbidden) return true;
  for (local i = 0; i < plan.length; i++) {
    if ((plan.anchor + plan.step * i) in forbidden) return true;
  }
  return false;
}

function OpexSameStationEnd(plan, original)
{
  return (plan.station_exit != plan.anchor) == (original.station_exit != original.anchor);
}

/* Deuxieme voie dediee, un train par voie. Jamais deux convois sur les memes tuiles :
 * le pathfinder ignore la premiere voie, le depot 2 n'y touche pas, et si la pose
 * echoue on garde la ligne a UN train. skip : 2=pas de quai, 3=pas de chemin, 4=voie,
 * 5=gare, 6=depot, 7=cash, 8=chevauchement, 9=court. */
function OpexTryDoubleTrack(catalog, planA, planB, tiles, depot, cashReserve, iterationBudget, deadlineTick, extraForbidden = null)
{
  local acc = { ok = false, skip = 2, tiles = null, planA = null, planB = null, depot = null,
                iterations = 0, actualCost = 0, structures = null };
  local stationIdA = AIStation.GetStationID(planA.anchor);
  local stationIdB = AIStation.GetStationID(planB.anchor);
  if (!AIStation.IsValidStation(stationIdA) || !AIStation.IsValidStation(stationIdB)) return acc;

  local forbidden = {};
  foreach (tile in tiles) forbidden[tile] <- true;
  for (local i = 0; i < planA.length; i++) forbidden[planA.anchor + planA.step * i] <- true;
  for (local i = 0; i < planB.length; i++) forbidden[planB.anchor + planB.step * i] <- true;
  forbidden[depot] <- true;
  local depotFront = AIRail.GetRailDepotFrontTile(depot);
  if (AIMap.IsValidTile(depotFront)) forbidden[depotFront] <- true;
  if (extraForbidden != null) {
    foreach (tile in extraForbidden) forbidden[tile] <- true;
  }

  local dualA = [];
  foreach (plan in OpexJoinPlatformPlans(planA, stationIdA)) {
    if (OpexSameStationEnd(plan, planA) && !OpexPlanHitsSet(plan, forbidden)) dualA.append(plan);
  }
  local dualB = [];
  foreach (plan in OpexJoinPlatformPlans(planB, stationIdB)) {
    if (OpexSameStationEnd(plan, planB) && !OpexPlanHitsSet(plan, forbidden)) dualB.append(plan);
  }
  if (dualA.len() == 0 || dualB.len() == 0) return acc;

  local ignored = [];
  foreach (tile, ignoredVal in forbidden) ignored.append(tile);
  local search = OpexSearchPath(dualA, dualB, iterationBudget, deadlineTick, ignored);
  acc.iterations = search.iterations;
  if (search.path == false || search.path == null) { acc.skip = 3; return acc; }

  local tiles2 = OpexResolveSearchTiles(search);
  local structures2 = OpexResolveSearchStructures(search);
  if (tiles2.len() < 3) { acc.skip = 9; return acc; }
  local planA2 = OpexMatchPlan(dualA, tiles2[0]);
  local planB2 = OpexMatchPlan(dualB, tiles2[tiles2.len() - 1]);
  if (planA2 == null || planB2 == null) { acc.skip = 9; return acc; }
  if (!OpexJoinPathIsDedicated(tiles2)) { acc.skip = 8; return acc; }
  for (local i = 1; i < tiles2.len() - 1; i++) {
    if (tiles2[i] in forbidden) { acc.skip = 8; return acc; }
  }

  local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
  local extra = tiles2.len() * catalog.costTrackPerTile
      + (planA2.length + planB2.length) * catalog.costStation + depotCost;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < extra + cashReserve) {
    acc.skip = 7;
    return acc;
  }

  local costs = AIAccounting();
  OpexAir0310InvalidateSiteValidity();
  for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
  for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
  local okA = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length, stationIdA);
  local okB = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length, stationIdB);
  local joinedA = AIStation.GetStationID(planA2.anchor) == stationIdA;
  local joinedB = AIStation.GetStationID(planB2.anchor) == stationIdB;
  if (!okA || !okB || !joinedA || !joinedB) {
    OpexRollback(null, planA2, planB2, null, null);
    acc.skip = 5;
    return acc;
  }

  local trackFailed = OpexBuildTrack(tiles2, structures2);
  local last = tiles2.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
      AIRail.AreTilesConnected(tiles2[last - 2], tiles2[last - 1], planB2.station_exit);
  if (!connected) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    acc.skip = 4;
    return acc;
  }

  local depot2 = OpexBuildDepot(tiles2, forbidden);
  if (depot2 == null) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    acc.skip = 6;
    return acc;
  }

  acc.ok = true;
  acc.skip = 0;
  acc.tiles = tiles2;
  acc.planA = planA2;
  acc.planB = planB2;
  acc.depot = depot2;
  acc.structures = structures2;
  acc.actualCost = costs.GetCosts();
  return acc;
}

/* V190 : Calcule une tuile decalee de (px, py) avec validation des bornes de carte. */
function OpexV190MakeTile(origTile, px, py)
{
  local x = AIMap.GetTileX(origTile) + px;
  local y = AIMap.GetTileY(origTile) + py;
  if (x < 0 || y < 0 || x >= AIMap.GetMapSizeX() || y >= AIMap.GetMapSizeY()) return null;
  local t = AIMap.GetTileIndex(x, y);
  if (!AIMap.IsValidTile(t)) return null;
  return t;
}

/* V190 : Vecteur perpendiculaire normalise pour la direction (dx, dy) selon le cote side (+1 ou -1). */
function OpexV190GetPerp(dx, dy, side)
{
  return { x = -side * dy, y = side * dx };
}

/* V190 : Trace la seconde voie par decalage parallele adjacent continu de la premiere voie.
 * Gere les virages interieurs (coupe d'angle), virages exterieurs (contournement continu),
 * et les ponts/tunnels paralleles avec verification sous AITestMode. */
function OpexV190TraceParallelTrack(tiles1, planA, planB, planA2, planB2, side, structures1 = null)
{
  local n1 = tiles1.len();
  if (n1 < 3) return null;

  local tiles2 = [];
  local structures2 = [];
  local hitSet = {};

  tiles2.append(planA2.station_exit);
  hitSet[planA2.station_exit] <- true;
  tiles2.append(planA2.lead);
  hitSet[planA2.lead] <- true;

  for (local i = 1; i < n1 - 1; i++) {
    local prev1 = tiles1[i - 1];
    local cur1 = tiles1[i];
    local next1 = tiles1[i + 1];

    local manhNext = AIMap.DistanceManhattan(cur1, next1);
    if (manhNext > 1) {
      // Franchissement (pont ou tunnel)
      local dx = AIMap.GetTileX(next1) - AIMap.GetTileX(cur1);
      local dy = AIMap.GetTileY(next1) - AIMap.GetTileY(cur1);
      local udx = (dx != 0) ? (dx > 0 ? 1 : -1) : 0;
      local udy = (dy != 0) ? (dy > 0 ? 1 : -1) : 0;
      local perp = OpexV190GetPerp(udx, udy, side);
      local start2 = OpexV190MakeTile(cur1, perp.x, perp.y);
      local end2 = OpexV190MakeTile(next1, perp.x, perp.y);
      if (start2 == null || end2 == null) return null;

      if (tiles2.top() != start2) {
        if (AIMap.DistanceManhattan(tiles2.top(), start2) != 1) return null;
        tiles2.append(start2);
        hitSet[start2] <- true;
      }

      local plannedKind = OpexPlannedStructureKind(structures1, cur1, next1);
      local structKind = plannedKind;
      {
        local testMode = AITestMode();
        if (plannedKind == "tunnel" || (plannedKind == null && AITunnel.GetOtherTunnelEnd(start2) == end2)) {
          if (!AITunnel.BuildTunnel(AIVehicle.VT_RAIL, start2)) return null;
          structKind = "tunnel";
        } else {
          local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(start2, end2) + 1);
          OpexBridgeSortBySpeed(bridges);
          if (bridges.IsEmpty() || !AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), start2, end2)) return null;
          structKind = "bridge";
        }
      }
      structures2.append({ start = start2, end = end2, kind = structKind });
      tiles2.append(end2);
      hitSet[end2] <- true;
      continue;
    }

    local manhPrev = AIMap.DistanceManhattan(prev1, cur1);
    local udx_in = 0;
    local udy_in = 0;
    if (manhPrev > 1) {
      local dx_in = AIMap.GetTileX(cur1) - AIMap.GetTileX(prev1);
      local dy_in = AIMap.GetTileY(cur1) - AIMap.GetTileY(prev1);
      udx_in = (dx_in != 0) ? (dx_in > 0 ? 1 : -1) : 0;
      udy_in = (dy_in != 0) ? (dy_in > 0 ? 1 : -1) : 0;
    } else {
      udx_in = AIMap.GetTileX(cur1) - AIMap.GetTileX(prev1);
      udy_in = AIMap.GetTileY(cur1) - AIMap.GetTileY(prev1);
    }

    local udx_out = AIMap.GetTileX(next1) - AIMap.GetTileX(cur1);
    local udy_out = AIMap.GetTileY(next1) - AIMap.GetTileY(cur1);

    local perp_in = OpexV190GetPerp(udx_in, udy_in, side);
    local perp_out = OpexV190GetPerp(udx_out, udy_out, side);

    if (udx_in == udx_out && udy_in == udy_out) {
      local p = OpexV190MakeTile(cur1, perp_in.x, perp_in.y);
      if (p == null) return null;
      if (tiles2.top() != p) {
        if (AIMap.DistanceManhattan(tiles2.top(), p) != 1) return null;
        tiles2.append(p);
        hitSet[p] <- true;
      }
    } else {
      local cross = udx_in * udy_out - udy_in * udx_out;
      if (cross == side) {
        // Virage interieur : point de coupe d'angle
        local p = OpexV190MakeTile(cur1, perp_in.x + perp_out.x, perp_in.y + perp_out.y);
        if (p == null) return null;
        if (tiles2.top() != p) {
          if (AIMap.DistanceManhattan(tiles2.top(), p) != 1) return null;
          tiles2.append(p);
          hitSet[p] <- true;
        }
      } else {
        // Virage exterieur : contournement continu sans coupure
        local p1 = OpexV190MakeTile(cur1, perp_in.x, perp_in.y);
        local p2 = OpexV190MakeTile(cur1, perp_in.x + perp_out.x, perp_in.y + perp_out.y);
        local p3 = OpexV190MakeTile(cur1, perp_out.x, perp_out.y);
        if (p1 == null || p2 == null || p3 == null) return null;
        local pts = [p1, p2, p3];
        foreach (pt in pts) {
          if (tiles2.top() != pt) {
            if (AIMap.DistanceManhattan(tiles2.top(), pt) != 1) return null;
            tiles2.append(pt);
            hitSet[pt] <- true;
          }
        }
      }
    }
  }

  // Raccordement gare B (lead puis station_exit)
  if (tiles2.top() != planB2.lead) {
    if (AIMap.DistanceManhattan(tiles2.top(), planB2.lead) != 1) return null;
    tiles2.append(planB2.lead);
    hitSet[planB2.lead] <- true;
  }
  if (tiles2.top() != planB2.station_exit) {
    if (AIMap.DistanceManhattan(tiles2.top(), planB2.station_exit) != 1) return null;
    tiles2.append(planB2.station_exit);
    hitSet[planB2.station_exit] <- true;
  }

  return { tiles = tiles2, structures = structures2 };
}

/* V197 : Construit la carte guideTiles (niveaux 0..8) autour de la voie 1. */
function OpexV197BuildGuideTiles(tiles, side, forbidden)
{
  local guide = {};
  if (tiles == null || tiles.len() < 2) return guide;

  // Niveau 0 : tuiles adjacentes sur le cote retour (side)
  for (local i = 0; i < tiles.len() - 1; i++) {
    local cur = tiles[i];
    local nxt = tiles[i + 1];
    local d = AIMap.DistanceManhattan(cur, nxt);
    if (d > 1) {
      local dx = AIMap.GetTileX(nxt) - AIMap.GetTileX(cur);
      local dy = AIMap.GetTileY(nxt) - AIMap.GetTileY(cur);
      local udx = (dx != 0) ? (dx > 0 ? 1 : -1) : 0;
      local udy = (dy != 0) ? (dy > 0 ? 1 : -1) : 0;
      local perp = OpexV190GetPerp(udx, udy, side);
      for (local step = 0; step <= d; step++) {
        local t = OpexV190MakeTile(cur, udx * step + perp.x, udy * step + perp.y);
        if (t != null && !guide.rawin(t) && (forbidden == null || !forbidden.rawin(t))) {
          guide.rawset(t, 0);
        }
      }
    } else if (d == 1) {
      local dx = AIMap.GetTileX(nxt) - AIMap.GetTileX(cur);
      local dy = AIMap.GetTileY(nxt) - AIMap.GetTileY(cur);
      local perp = OpexV190GetPerp(dx, dy, side);
      local adj1 = OpexV190MakeTile(cur, perp.x, perp.y);
      if (adj1 != null && !guide.rawin(adj1) && (forbidden == null || !forbidden.rawin(adj1))) {
        guide.rawset(adj1, 0);
      }
      local adj2 = OpexV190MakeTile(nxt, perp.x, perp.y);
      if (adj2 != null && !guide.rawin(adj2) && (forbidden == null || !forbidden.rawin(adj2))) {
        guide.rawset(adj2, 0);
      }
      if (i > 0) {
        local prv = tiles[i - 1];
        if (AIMap.DistanceManhattan(prv, cur) == 1) {
          local dx_in = AIMap.GetTileX(cur) - AIMap.GetTileX(prv);
          local dy_in = AIMap.GetTileY(cur) - AIMap.GetTileY(prv);
          local perp_in = OpexV190GetPerp(dx_in, dy_in, side);
          local corner = OpexV190MakeTile(cur, perp_in.x + perp.x, perp_in.y + perp.y);
          if (corner != null && !guide.rawin(corner) && (forbidden == null || !forbidden.rawin(corner))) {
            guide.rawset(corner, 0);
          }
        }
      }
    }
  }

  // Anneaux 1..8 par propagation 4-voisins
  local ringTiles = [];
  foreach (tile, _ in guide) ringTiles.append(tile);

  local dirOffsets = [
    AIMap.GetTileIndex(0, 1),
    AIMap.GetTileIndex(0, -1),
    AIMap.GetTileIndex(1, 0),
    AIMap.GetTileIndex(-1, 0)
  ];

  for (local ring = 1; ring <= 8; ring++) {
    local nextRing = [];
    foreach (t in ringTiles) {
      foreach (off in dirOffsets) {
        local neighbor = t + off;
        if (AIMap.IsValidTile(neighbor) && AIMap.DistanceManhattan(t, neighbor) == 1 &&
            !guide.rawin(neighbor) && (forbidden == null || !forbidden.rawin(neighbor))) {
          guide.rawset(neighbor, ring);
          nextRing.append(neighbor);
        }
      }
    }
    ringTiles = nextRing;
    if (ringTiles.len() == 0) break;
  }

  return guide;
}

/* V190 : Planifie la seconde voie d'une ligne neuve SANS modifier la carte.
 * Tente d'abord le trace parallele direct (0 opcode de recherche, alignement garanti).
 * En cas d'obstacle infranchissable en parallele direct, bascule sur recherche A*. */
function OpexV190PlanDoubleTrack(catalog, planA, planB, tiles, iterationBudget, deadlineTick, structures = null)
{
  local acc = { ok = false, skip = 2, reason = "NOPARALLEL", step = "NONE", tiles = null, planA = null, planB = null,
                iterations = 0, structures = null };

  local forbidden = {};
  foreach (tile in tiles) forbidden[tile] <- true;
  for (local i = 0; i < planA.length; i++) forbidden[planA.anchor + planA.step * i] <- true;
  for (local i = 0; i < planB.length; i++) forbidden[planB.anchor + planB.step * i] <- true;

  local dualA = [];
  local candsA = (("parallels" in planA) && planA.parallels != null && planA.parallels.len() > 0)
      ? planA.parallels : OpexV190FindParallelPlatformPlans(planA);
  foreach (p in candsA) {
    if (OpexSameStationEnd(p, planA) && !OpexPlanHitsSet(p, forbidden)) dualA.append(p);
  }
  local dualB = [];
  local candsB = (("parallels" in planB) && planB.parallels != null && planB.parallels.len() > 0)
      ? planB.parallels : OpexV190FindParallelPlatformPlans(planB);
  foreach (p in candsB) {
    if (OpexSameStationEnd(p, planB) && !OpexPlanHitsSet(p, forbidden)) dualB.append(p);
  }
  if (dualA.len() == 0 || dualB.len() == 0) {
    acc.skip = 2;
    acc.reason = (dualA.len() == 0 && dualB.len() == 0) ? "NOPLATFORM_AB"
               : (dualA.len() == 0 ? "NOPLATFORM_A" : "NOPLATFORM_B");
    acc.step = (dualA.len() == 0 && dualB.len() == 0) ? "NO_DUAL_AB"
             : (dualA.len() == 0 ? "NO_DUAL_A" : "NO_DUAL_B");
    return acc;
  }

  // 1. Essai du trace parallele direct
  local bestTrace = null;
  local bestPlanA2 = null;
  local bestPlanB2 = null;

  local dirA = planA.lead - planA.station_exit;
  local dxA = AIMap.GetTileX(dirA);
  local dyA = AIMap.GetTileY(dirA);

  local dirB = planB.lead - planB.station_exit;
  local dxB = AIMap.GetTileX(dirB);
  local dyB = AIMap.GetTileY(dirB);

  foreach (pA in dualA) {
    local offA = pA.station_exit - planA.station_exit;
    local oxA = AIMap.GetTileX(offA);
    local oyA = AIMap.GetTileY(offA);
    local side = dxA * oyA - dyA * oxA;
    if (side != 1 && side != -1) continue;

    local targetOxB = -side * dyB;
    local targetOyB = side * dxB;

    foreach (pB in dualB) {
      local offB = pB.station_exit - planB.station_exit;
      local oxB = AIMap.GetTileX(offB);
      local oyB = AIMap.GetTileY(offB);
      if (oxB != targetOxB || oyB != targetOyB) continue;

      local trace = OpexV190TraceParallelTrack(tiles, planA, planB, pA, pB, side, structures);
      if (trace == null) continue;

      local candidateTiles = trace.tiles;
      local candidateStructures = trace.structures;
      if (candidateTiles.len() < 3) continue;

      // Verification collision avec forbidden (voie 1 et quais)
      local hit = false;
      for (local i = 1; i < candidateTiles.len() - 1; i++) {
        if (candidateTiles[i] in forbidden) { hit = true; break; }
      }
      if (hit) continue;

      if (!OpexJoinPathIsDedicated(candidateTiles)) continue;

      // Verification constructibilite complete sous AITestMode
      local testFails = OpexTestRailTrack(candidateTiles, candidateStructures);
      if (testFails > 0) continue;

      local lastIdx = candidateTiles.len() - 1;
      if (!OpexRailEndConnected(pA.station_exit, candidateTiles[1], candidateTiles[2], "A")) continue;
      if (!OpexRailEndConnected(pB.station_exit, candidateTiles[lastIdx - 1], candidateTiles[lastIdx - 2], "B")) continue;

      // Verification aiguillages de sortie sous AITestMode
      local swOutA = false;
      local swOutB = false;
      {
        local testMode = AITestMode();
        for (local i2 = 1; i2 <= 6 && i2 < candidateTiles.len() - 2; i2++) {
          for (local i1 = 1; i1 <= 6 && i1 < tiles.len() - 2; i1++) {
            if (OpexV181TryBuildSwitch(candidateTiles[i2 - 1], candidateTiles[i2], tiles[i1], tiles[i1 + 1], null, true)) {
              swOutA = true; break;
            }
          }
          if (swOutA) break;
        }
        for (local d1 = 1; d1 <= 6; d1++) {
          local i1 = tiles.len() - 1 - d1;
          if (i1 <= 1) continue;
          for (local d2 = 1; d2 <= 6; d2++) {
            local i2 = candidateTiles.len() - 1 - d2;
            if (i2 <= 1) continue;
            if (OpexV181TryBuildSwitch(tiles[i1 + 1], tiles[i1], candidateTiles[i2], candidateTiles[i2 - 1], null, true)) {
              swOutB = true; break;
            }
          }
          if (swOutB) break;
        }
      }
      if (!swOutA || !swOutB) continue;

      bestTrace = trace;
      bestPlanA2 = pA;
      bestPlanB2 = pB;
      break;
    }
    if (bestTrace != null) break;
  }

  if (bestTrace != null) {
    if (DECISION_LOG && V197_GUIDED_DOUBLE) {
      OpexDecide("V197", "track=2 ok=1 iters=0 reason=PARALLEL_OK");
    }
    acc.ok = true;
    acc.skip = 0;
    acc.reason = "OK";
    acc.step = "PARALLEL_TRACE_OK";
    acc.tiles = bestTrace.tiles;
    acc.planA = bestPlanA2;
    acc.planB = bestPlanB2;
    acc.structures = bestTrace.structures;
    return acc;
  }

  // 2. Repli : recherche A*
  local ignored = [];
  foreach (tile, ignoredVal in forbidden) ignored.append(tile);
  local searchWeight = OpexRailAstarWeight(AIMap.DistanceManhattan(planA.station_exit, planB.station_exit));
  local guideTiles = V197_GUIDED_DOUBLE ? OpexV197BuildGuideTiles(tiles, 1, forbidden) : null;
  local search = OpexSearchPath(dualA, dualB, iterationBudget, deadlineTick, ignored, searchWeight, null, guideTiles);
  acc.iterations = search.iterations;
  if (search.path == false || search.path == null) {
    acc.skip = 3;
    acc.reason = "NOPATH2";
    acc.step = ("stop" in search) ? ("SEARCH_" + search.stop) : "SEARCH_NOPATH";
    if (DECISION_LOG && V197_GUIDED_DOUBLE) {
      OpexDecide("V197", "track=2 ok=0 iters=" + search.iterations + " reason=" + acc.reason);
    }
    return acc;
  }

  local tiles2 = OpexResolveSearchTiles(search);
  local structures2 = OpexResolveSearchStructures(search);
  if (tiles2.len() < 3) {
    acc.skip = 9;
    acc.reason = "SHORT2";
    acc.step = "SHORT2";
    if (DECISION_LOG && V197_GUIDED_DOUBLE) {
      OpexDecide("V197", "track=2 ok=0 iters=" + acc.iterations + " reason=" + acc.reason);
    }
    return acc;
  }
  local planA2 = OpexMatchPlan(dualA, tiles2[0]);
  local planB2 = OpexMatchPlan(dualB, tiles2[tiles2.len() - 1]);
  if (planA2 == null || planB2 == null) {
    acc.skip = 9;
    acc.reason = "NOMATCH2";
    acc.step = (planA2 == null && planB2 == null) ? "NOMATCH_AB" : (planA2 == null ? "NOMATCH_A" : "NOMATCH_B");
    if (DECISION_LOG && V197_GUIDED_DOUBLE) {
      OpexDecide("V197", "track=2 ok=0 iters=" + acc.iterations + " reason=" + acc.reason);
    }
    return acc;
  }
  if (!OpexJoinPathIsDedicated(tiles2)) {
    acc.skip = 8;
    acc.reason = "NOTDEDICATED2";
    acc.step = "NOT_DEDICATED";
    if (DECISION_LOG && V197_GUIDED_DOUBLE) {
      OpexDecide("V197", "track=2 ok=0 iters=" + acc.iterations + " reason=" + acc.reason);
    }
    return acc;
  }
  for (local i = 1; i < tiles2.len() - 1; i++) {
    if (tiles2[i] in forbidden) {
      acc.skip = 8;
      acc.reason = "HITFORBIDDEN2";
      acc.step = "HIT_FORBIDDEN_idx" + i;
      if (DECISION_LOG && V197_GUIDED_DOUBLE) {
        OpexDecide("V197", "track=2 ok=0 iters=" + acc.iterations + " reason=" + acc.reason);
      }
      return acc;
    }
  }

  acc.ok = true;
  acc.skip = 0;
  acc.reason = "OK";
  acc.step = "OK";
  acc.tiles = tiles2;
  acc.planA = planA2;
  acc.planB = planB2;
  acc.structures = structures2;
  if (DECISION_LOG && V197_GUIDED_DOUBLE) {
    OpexDecide("V197", "track=2 ok=1 iters=" + acc.iterations + " reason=OK");
  }
  return acc;
}

/* Capture commune du premier echec : l'appelant garde failure et lit GetLastError
 * avant les distances et le kind. Ce helper ne pose rien et ne relit pas l'erreur. */
function OpexRailCaptureTrackFailure(failure, tiles, i, cur, kind, err, manhPrev, manhNext)
{
  failure.index <- i;
  failure.tile <- cur;
  failure.kind <- kind;
  failure.error <- err;
  failure.manh_prev <- manhPrev;
  failure.manh_next <- manhNext;
  /* Apres GetLastError : les lectures suivantes ne doivent pas ecraser err. */
  failure.is_buildable <- AITile.IsBuildable(cur) ? 1 : 0;
  failure.is_rail <- AIRail.IsRailTile(cur) ? 1 : 0;
  failure.is_station <- AIRail.IsRailStationTile(cur) ? 1 : 0;
  failure.is_road <- AIRoad.IsRoadTile(cur) ? 1 : 0;
  failure.is_water <- AITile.IsWaterTile(cur) ? 1 : 0;
  failure.owner_self <- (AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) ? 1 : 0;
  failure.slope <- AITile.GetSlope(cur);
  local dupIndex = -1;
  for (local j = 0; j < i; j++) {
    if (tiles[j] == cur) {
      dupIndex = j;
      break;
    }
  }
  failure.dup_index <- dupIndex;
}

/* Pose la voie sur les cases intermediaires. Les extremites sont les sorties de quai.
 * `structures` propage le kind retenu sous AITestMode : GetOtherTunnelEnd sur une paire
 * eloignee a pris un tunnel naturel a la place d'un pont (TRKFAIL, prototype 4/9 -> 7/9).
 * Tableau vide ou null = deduction classique, A* inchange.
 * `failure` optionnel : null (defaut) n'ecrit rien. Sinon, au premier segment refuse
 * seulement (cles neuves en <-) : index, tile, kind (rail|bridge|tunnel|connect),
 * error, manh_prev, manh_next, puis l'etat de `cur` apres l'echec
 * (is_buildable, is_rail, is_station, is_road, is_water, owner_self, slope,
 * dup_index). Ces lectures restent dans le `if` deja garde : sonde eteinte ou
 * echec deja enregistre, aucun appel. connect = BuildRail vrai mais
 * AreTilesConnected faux. */
/* V199 : verification si une tuile genante peut etre demolie (arbres, maisons autorisees, hors rail adverse). */
function OpexV199CanDemolishTile(tile)
{
  if (!AIMap.IsValidTile(tile)) return false;
  if (AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL)) {
    if (!AICompany.IsMine(AITile.GetOwner(tile))) return false;
    if (AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) return false;
  }
  if (AITile.IsWaterTile(tile)) return false;
  local testMode = AITestMode();
  return AITile.DemolishTile(tile);
}

/* V199 : reprise locale de pose rail par A* bornee (budget <= 20%) vers une tuile 5 a 15 cases plus loin (ou la fin). */
function OpexV199RetryToBuild(tiles, failIdx, initialBudget, retriesCount, failure = null, options = null)
{
  local L = tiles.len();
  if (failIdx <= 0 || failIdx >= L - 1) return null;

  local startTile = tiles[failIdx - 1];
  local startPrev = (failIdx >= 2) ? tiles[failIdx - 2] : null;
  local faultyTile = tiles[failIdx];

  local ignored = [faultyTile];
  for (local k = 0; k < failIdx - 1; k++) {
    ignored.append(tiles[k]);
  }

  local budgetCap = (initialBudget != null && initialBudget > 0) ? initialBudget : 5000;
  local retryBudget = (budgetCap * 20) / 100;
  if (retryBudget < 200) retryBudget = 200;
  local deadlineTick = AIController.GetTick() + retryBudget / 3 + BUILD_TICK_MARGIN;

  local targetIndices = [];
  local step10 = failIdx + 10;
  if (step10 < L - 1) {
    targetIndices.append(step10);
  } else {
    local step5 = failIdx + 5;
    if (step5 < L - 1) targetIndices.append(step5);
  }
  if (targetIndices.len() == 0 || targetIndices[targetIndices.len() - 1] != L - 1) {
    targetIndices.append(L - 1);
  }

  local sourcesPlans = [{ lead = startTile, station_exit = (startPrev != null ? startPrev : startTile) }];

  foreach (targetIdx in targetIndices) {
    local tIdx = targetIdx;
    while (tIdx < L - 1 && AIMap.DistanceManhattan(tiles[tIdx], tiles[tIdx + 1]) > 1) {
      tIdx++;
    }
    local targetTile = tiles[tIdx];
    local targetNext = (tIdx < L - 1) ? tiles[tIdx + 1] : tiles[tIdx - 1];
    local goalsPlans = [{ lead = targetTile, station_exit = targetNext }];

    local preCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local preAccounting = null;
    local preAccountingCost = 0;
    if (options != null && ("accounting" in options) && options.accounting != null) {
      preAccounting = options.accounting;
      preAccountingCost = preAccounting.GetCosts();
    }

    local pathfinder = OpexCreateRailPathfinder(sourcesPlans, goalsPlans, ignored, 100);
    if (pathfinder == null) continue;

    local advance = OpexAdvanceRailPathfinder(pathfinder, 0, retryBudget, deadlineTick, retryBudget);

    if (preAccounting != null && options != null && ("retrySearchCost" in options)) {
      local deltaAcc = preAccounting.GetCosts() - preAccountingCost;
      if (deltaAcc > 0) options.retrySearchCost += deltaAcc;
    }

    if (advance.path != false && advance.path != null) {
      local subTiles = OpexPathTiles(advance.path);
      if (subTiles != null && subTiles.len() >= 2) {
        local startPos = 0;
        for (local s = 0; s < subTiles.len(); s++) {
          if (subTiles[s] == startTile) {
            startPos = s;
            break;
          }
        }
        local newTiles = [];
        for (local k = 0; k < failIdx; k++) newTiles.append(tiles[k]);
        for (local s = startPos + 1; s < subTiles.len(); s++) newTiles.append(subTiles[s]);
        for (local k = tIdx + 1; k < L; k++) newTiles.append(tiles[k]);

        local retryCost = preCash - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        if (retryCost < 0) retryCost = 0;

        if (DECISION_LOG) {
          OpexDecide("V199", "step=retry ok=1 n=" + retriesCount + " cost=" + retryCost);
        }
        return { ok = true, tiles = newTiles, resumeIdx = failIdx };
      }
    }
  }

  // Echec de la reprise : demolir proprement ce qui a ete pose
  for (local k = failIdx - 1; k >= 1; k--) {
    local t = tiles[k];
    if (AIMap.IsValidTile(t) && AICompany.IsMine(AITile.GetOwner(t))) {
      if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t)) {
        AITile.DemolishTile(t);
      }
    }
  }

  if (DECISION_LOG) {
    OpexDecide("V199", "step=retry ok=0 n=" + retriesCount + " cost=0");
  }
  return { ok = false };
}

/* V199 : nivellement de la bande laterale cote retour apres pose de voie 1 (RebuildForHomeward ameliore). */
function OpexV199RebuildForHomeward(tiles1, side = 1, budgetK = 20)
{
  if (!V199_ROBUST_BUILD) return 0;
  if (tiles1 == null || tiles1.len() < 2) return 0;

  local maxCost = budgetK * 1000;
  local totalCost = 0;
  local leveledCount = 0;

  for (local i = 0; i < tiles1.len() - 1; i++) {
    if (totalCost >= maxCost) break;

    local cur = tiles1[i];
    local nxt = tiles1[i + 1];
    local d = AIMap.DistanceManhattan(cur, nxt);
    if (d != 1) continue; // Sauter ponts et tunnels

    if (AIBridge.IsBridgeTile(cur) || AIBridge.IsBridgeTile(nxt) ||
        AITunnel.IsTunnelTile(cur) || AITunnel.IsTunnelTile(nxt)) {
      continue;
    }

    local dx = AIMap.GetTileX(nxt) - AIMap.GetTileX(cur);
    local dy = AIMap.GetTileY(nxt) - AIMap.GetTileY(cur);
    local perp = OpexV190GetPerp(dx, dy, side);
    local revCur = OpexV190MakeTile(cur, perp.x, perp.y);
    local revNxt = OpexV190MakeTile(nxt, perp.x, perp.y);

    if (revCur == null || revNxt == null) continue;
    if (!AIMap.IsValidTile(revCur) || !AIMap.IsValidTile(revNxt)) continue;

    // Sauter cotes, eau, ponts, tunnels, tuiles non constructibles
    if (AITile.IsCoastTile(revCur) || AITile.IsCoastTile(revNxt) ||
        AITile.IsWaterTile(revCur) || AITile.IsWaterTile(revNxt) ||
        AITile.IsCoastTile(cur) || AITile.IsCoastTile(nxt)) {
      continue;
    }
    if (AIBridge.IsBridgeTile(revCur) || AIBridge.IsBridgeTile(revNxt) ||
        AITunnel.IsTunnelTile(revCur) || AITunnel.IsTunnelTile(revNxt)) {
      continue;
    }
    if (!AITile.IsBuildable(revCur) || !AITile.IsBuildable(revNxt)) continue;
    if (AITile.HasTransportType(revCur, AITile.TRANSPORT_RAIL) ||
        AITile.HasTransportType(revNxt, AITile.TRANSPORT_RAIL)) {
      continue;
    }

    local slope1 = AITile.GetSlope(cur);
    local slopeRev = AITile.GetSlope(revCur);
    local h1 = AITile.GetMaxHeight(cur);
    local hRev = AITile.GetMaxHeight(revCur);

    if (slopeRev != slope1 || hRev != h1) {
      local preCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local leveled = false;

      if (slope1 == AITile.SLOPE_FLAT) {
        leveled = AITile.LevelTiles(cur, revCur);
      } else {
        local corners = [AITile.CORNER_W, AITile.CORNER_S, AITile.CORNER_E, AITile.CORNER_N];
        local slopes = [AITile.SLOPE_W, AITile.SLOPE_S, AITile.SLOPE_E, AITile.SLOPE_N];
        for (local cIdx = 0; cIdx < 4; cIdx++) {
          local c = corners[cIdx];
          local s = slopes[cIdx];
          local hc = AITile.GetCornerHeight(cur, c);
          local hr = AITile.GetCornerHeight(revCur, c);
          if (hr > hc) {
            if (AITile.LowerTile(revCur, s)) leveled = true;
          } else if (hr < hc) {
            if (AITile.RaiseTile(revCur, s)) leveled = true;
          }
        }
      }

      local postCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local cost = preCash - postCash;
      if (cost > 0) totalCost += cost;
      if (leveled) leveledCount++;
    }
  }

  if (DECISION_LOG) {
    OpexDecide("V199", "step=level ok=" + (leveledCount > 0 ? 1 : 0) +
               " n=" + leveledCount + " cost=" + totalCost);
  }
  return totalCost;
}

/* Pose la voie sur les cases intermediaires. Les extremites sont les sorties de quai.
 * `structures` propage le kind retenu sous AITestMode : GetOtherTunnelEnd sur une paire
 * eloignee a pris un tunnel naturel a la place d'un pont (TRKFAIL, prototype 4/9 -> 7/9).
 * Tableau vide ou null = deduction classique, A* inchange.
 * `failure` optionnel : null (defaut) n'ecrit rien. Sinon, au premier segment refuse
 * seulement (cles neuves en <-) : index, tile, kind (rail|bridge|tunnel|connect),
 * error, manh_prev, manh_next, puis l'etat de `cur` apres l'echec
 * (is_buildable, is_rail, is_station, is_road, is_water, owner_self, slope,
 * dup_index). Ces lectures restent dans le `if` deja garde : sonde eteinte ou
 * echec deja enregistre, aucun appel. connect = BuildRail vrai mais
 * AreTilesConnected faux.
 * `options` optionnel (V199) : isDouble, trainLength, initialBudget, accounting, retrySearchCost. */
/* V296a : chaque commande reelle suspend le script au moins un tick ; poser tuile par tuile coutait
 * ~1 tick par tuile (1,36 M d'opcodes hors A* par ligne posee, 20/10). AIRail.BuildRail(from, tile, to)
 * pose d'une seule commande tout un alignement droit ou diagonal (CmdBuildRailroadTrack, qui fait le
 * meme CMD_BUILD_SINGLE_RAIL par tuile ; en mode test il echoue en bloc sur le premier obstacle, et un
 * echec ne suspend pas). Rend le dernier indice k >= i tel que tiles[i..k] forme un tel alignement avec
 * tiles[i - 1] et tiles[k + 1] (k <= len - 2 : ni la premiere ni la derniere tuile ne sont posees),
 * ou i si aucun alignement de 2 tuiles ou plus. Une tuile deja en rail coupe l'alignement : la pose
 * unitaire y echoue (ALREADY_BUILT) alors que la pose groupee la sauterait. */
function OpexV296aRunEnd(tiles, i)
{
  local n = tiles.len();
  if (i + 1 > n - 2) return i;
  local s1 = tiles[i] - tiles[i - 1];
  local s2 = tiles[i + 1] - tiles[i];
  if (s2 == -s1) return i;
  if (AIMap.DistanceManhattan(tiles[i - 1], tiles[i]) != 1 ||
      AIMap.DistanceManhattan(tiles[i], tiles[i + 1]) != 1) return i;
  if (AIRail.IsRailTile(tiles[i])) return i;
  local straight = (s1 == s2);
  local last = i;
  for (local k = i + 1; k <= n - 2; k++) {
    /* Droit : toujours s1 ; diagonale : s1, s2, s1, s2... depuis tiles[i - 1]. */
    local expect = (straight || ((k - i) % 2 == 1)) ? s1 : s2;
    if (tiles[k + 1] - tiles[k] != expect) break;
    if (AIRail.IsRailTile(tiles[k])) break;
    last = k;
  }
  return last;
}

function OpexV296aLog(batch)
{
  if (batch == null || !DECISION_LOG || (batch.runs + batch.fallbacks + batch.mismatch) == 0) return;
  OpexDecide("V296A", "runs=" + batch.runs + " tiles=" + batch.tiles + " single=" + batch.single
             + " fallbacks=" + batch.fallbacks + " mismatch=" + batch.mismatch);
}

function OpexBuildTrack(tiles, structures = null, failure = null, options = null)
{
  local failed = 0;
  local isDouble = (options != null && ("isDouble" in options)) ? options.isDouble : false;
  local trainLen = (options != null && ("trainLength" in options)) ? options.trainLength : 3;
  local initialBudget = (options != null && ("initialBudget" in options)) ? options.initialBudget : 5000;
  local signalN = max(4, trainLen + 1);

  local signalDist = 0;
  local signalsBuiltCount = 0;
  local retriesCount = 0;
  /* V296a : la signalisation V199 de la double voie se pose tuile par tuile, on ne groupe pas. */
  local batch = (!V296A_MISMATCH && !(V199_ROBUST_BUILD && isDouble))
      ? { runs = 0, tiles = 0, single = 0, fallbacks = 0, mismatch = 0, skipUntil = 0 } : null;

  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    local ok = false;
    if (batch != null && i > batch.skipUntil) {
      local last = OpexV296aRunEnd(tiles, i);
      if (last > i) {
        local to = tiles[last + 1];
        if (AIRail.BuildRail(prev, cur, to)) {
          local k = i;
          while (k <= last && AIRail.AreTilesConnected(tiles[k - 1], tiles[k], tiles[k + 1])) k++;
          if (k > last) {
            batch.runs++;
            batch.tiles += last - i + 1;
            i = last;
            continue;
          }
          /* Trace different du trace prevu : on defait la meme commande et on ne groupe plus. */
          AIRail.RemoveRail(prev, cur, to);
          batch.mismatch++;
          V296A_MISMATCH = true;
          OpexV296aLog(batch);
          batch = null;
        } else {
          /* Obstacle, argent, pente : la pose unitaire rejoue l'alignement et garde la gestion
           * d'echec existante (V199, capture de l'erreur). */
          batch.fallbacks++;
          batch.skipUntil = last;
        }
      } else {
        batch.single++;
      }
    }
    if (prev == next) {
      ok = true;                                   // aller-retour, rien a poser
    } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
      ok = true;                                   // autre bout d'un franchissement deja pose
    } else if (AIMap.DistanceManhattan(cur, next) > 1) {
      local plannedKind = OpexPlannedStructureKind(structures, cur, next);
      if (plannedKind == "tunnel" ||
          (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
        ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
      } else {
        local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        OpexBridgeSortBySpeed(bridges);
        ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
      }
    } else {
      ok = AIRail.BuildRail(prev, cur, next);
      /* BuildRail peut repondre vrai sans dessiner la transition attendue. Pour les trois cases
       * adjacentes ou l'API autorise le predicat, la verification est immediate plutot que
       * reportee au seul test des sorties de gare. Ponts et tunnels n'acceptent pas ce predicat
       * (precondition de voisinage) et restent controles par les deux segments voisins. */
      if (ok && AIMap.DistanceManhattan(prev, cur) == 1 &&
          AIMap.DistanceManhattan(cur, next) == 1 &&
          !AIRail.AreTilesConnected(prev, cur, next)) {
        ok = false;
        /* failure null : un test, aucun appel en plus. L'erreur est lue avant Manhattan. */
        if (failure != null && !("index" in failure)) {
          local err = AIError.GetLastError();
          local manhPrev = AIMap.DistanceManhattan(prev, cur);
          local manhNext = AIMap.DistanceManhattan(cur, next);
          OpexRailCaptureTrackFailure(failure, tiles, i, cur, "connect", err, manhPrev, manhNext);
        }
      }
    }

    // V199 : Demolition avant reprise locale si ERR_AREA_NOT_CLEAR
    if (!ok && V199_ROBUST_BUILD && AIError.GetLastError() == AIError.ERR_AREA_NOT_CLEAR) {
      if (AIMap.DistanceManhattan(cur, next) > 1) {
        local dx = AIMap.GetTileX(next) - AIMap.GetTileX(cur);
        local dy = AIMap.GetTileY(next) - AIMap.GetTileY(cur);
        local dist = AIMap.DistanceManhattan(cur, next);
        local udx = (dx != 0) ? (dx > 0 ? 1 : -1) : 0;
        local udy = (dy != 0) ? (dy > 0 ? 1 : -1) : 0;
        local demAny = false;
        local preCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        for (local s = 1; s < dist; s++) {
          local midTile = OpexV190MakeTile(cur, udx * s, udy * s);
          if (midTile != null && OpexV199CanDemolishTile(midTile)) {
            if (AITile.DemolishTile(midTile)) demAny = true;
          }
        }
        if (demAny) {
          local bridges = AIBridgeList_Length(dist + 1);
          OpexBridgeSortBySpeed(bridges);
          ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
          local demCost = preCash - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (demCost < 0) demCost = 0;
          if (DECISION_LOG) {
            OpexDecide("V199", "step=demolish ok=" + (ok ? 1 : 0) + " n=1 cost=" + demCost);
          }
        }
      } else if (OpexV199CanDemolishTile(cur)) {
        local preCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        local demOk = AITile.DemolishTile(cur);
        local demCost = preCash - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        if (demCost < 0) demCost = 0;
        if (demOk) {
          ok = AIRail.BuildRail(prev, cur, next);
          if (ok && AIMap.DistanceManhattan(prev, cur) == 1 &&
              AIMap.DistanceManhattan(cur, next) == 1 &&
              !AIRail.AreTilesConnected(prev, cur, next)) {
            ok = false;
          }
          if (DECISION_LOG) {
            OpexDecide("V199", "step=demolish ok=" + (ok ? 1 : 0) + " n=1 cost=" + demCost);
          }
        }
      }
    }

    // V199 : Reprise locale (RetryToBuild) quand la pose echoue
    if (!ok && V199_ROBUST_BUILD) {
      if (retriesCount < 3) {
        retriesCount++;
        local retryResult = OpexV199RetryToBuild(tiles, i, initialBudget, retriesCount, failure, options);
        if (retryResult != null && retryResult.ok) {
          local newTiles = retryResult.tiles;
          tiles.clear();
          foreach (t in newTiles) tiles.append(t);
          i = retryResult.resumeIdx - 1;
          continue;
        } else {
          if (failure != null && !("index" in failure)) {
            local err = AIError.GetLastError();
            local manhPrev = AIMap.DistanceManhattan(prev, cur);
            local manhNext = AIMap.DistanceManhattan(cur, next);
            OpexRailCaptureTrackFailure(failure, tiles, i, cur, "rail", err, manhPrev, manhNext);
          }
          failed++;
          OpexV296aLog(batch);
          return failed;
        }
      } else {
        for (local k = i - 1; k >= 1; k--) {
          local t = tiles[k];
          if (AIMap.IsValidTile(t) && AICompany.IsMine(AITile.GetOwner(t))) {
            if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t)) {
              AITile.DemolishTile(t);
            }
          }
        }
        if (DECISION_LOG) {
          OpexDecide("V199", "step=retry ok=0 n=" + retriesCount + " cost=0");
        }
        if (failure != null && !("index" in failure)) {
          local err = AIError.GetLastError();
          local manhPrev = AIMap.DistanceManhattan(prev, cur);
          local manhNext = AIMap.DistanceManhattan(cur, next);
          OpexRailCaptureTrackFailure(failure, tiles, i, cur, "rail", err, manhPrev, manhNext);
        }
        failed++;
        OpexV296aLog(batch);
        return failed;
      }
    }

    if (!ok) {
      failed++;
      if (failure != null && !("index" in failure)) {
        local err = AIError.GetLastError();
        local manhPrev = AIMap.DistanceManhattan(prev, cur);
        local manhNext = AIMap.DistanceManhattan(cur, next);
        /* Meme predicat que la branche de pose, apres la capture de l'erreur. */
        local segmentKind = "rail";
        if (manhNext > 1) {
          local gapKind = OpexPlannedStructureKind(structures, cur, next);
          if (gapKind == "tunnel" ||
              (gapKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
            segmentKind = "tunnel";
          } else {
            segmentKind = "bridge";
          }
        }
        OpexRailCaptureTrackFailure(failure, tiles, i, cur, segmentKind, err, manhPrev, manhNext);
      }
    } else if (V199_ROBUST_BUILD && isDouble) {
      if (AIRail.IsRailTile(cur) && !AIBridge.IsBridgeTile(cur) && !AITunnel.IsTunnelTile(cur) &&
          AIMap.DistanceManhattan(prev, cur) == 1) {
        signalDist++;
        local placed = false;
        if (signalDist >= signalN) {
          if (AIRail.BuildSignal(cur, prev, AIRail.SIGNALTYPE_PBS_ONEWAY)) {
            signalDist = 0;
            signalsBuiltCount++;
            placed = true;
          }
        }
        if (!placed) {
          local isCrest = (AITile.GetMaxHeight(cur) > AITile.GetMaxHeight(prev)) &&
                          (AITile.GetMaxHeight(cur) >= AITile.GetMaxHeight(next));
          if (isCrest && signalDist >= 2) {
            if (AIRail.BuildSignal(cur, prev, AIRail.SIGNALTYPE_PBS_ONEWAY)) {
              signalDist = 2;
              signalsBuiltCount++;
            }
          }
        }
      }
    }
  }

  if (V199_ROBUST_BUILD && signalsBuiltCount > 0 && DECISION_LOG) {
    local sigCost = signalsBuiltCount * 100;
    OpexDecide("V199", "step=signal ok=1 n=" + signalsBuiltCount + " cost=" + sigCost);
  }

  OpexV296aLog(batch);
  return failed;
}

/* C80 : Re-verification d'un trace de voie sous AITestMode pour le stock de traces.
 * Meme parcours que OpexBuildTrack mais SANS le controle AreTilesConnected,
 * car sous mode test les voies ne sont pas reellement posees sur la carte. */
function OpexTestRailTrack(tiles, structures = null)
{
  local testMode = AITestMode();
  local failed = 0;
  local firstSegment = null;
  local firstTile = null;
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    local ok = false;
    if (prev == next) {
      ok = true;                                   // aller-retour, rien a poser
    } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
      ok = true;                                   // autre bout d'un franchissement deja pose
    } else if (AIMap.DistanceManhattan(cur, next) > 1) {
      local plannedKind = OpexPlannedStructureKind(structures, cur, next);
      if (plannedKind == "tunnel" ||
          (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
        ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
      } else {
        local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        OpexBridgeSortBySpeed(bridges);
        ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
      }
    } else {
      ok = AIRail.BuildRail(prev, cur, next);
    }
    if (!ok) {
      failed++;
      if (firstSegment == null) {
        firstTile = cur;
        firstSegment = prev + "-" + cur + "-" + next;
      }
    }
  }
  return { failed = failed, firstSegment = firstSegment, firstTile = firstTile };
}

/* Depot pres du depart. On pose l'aiguillage AVANT le batiment et on verifie la connectivite a
 * chaque etape : un appel qui renvoie "reussi" ne prouve pas que le resultat est raccorde. */
function OpexBuildDepot(tiles, forbidden = null)
{
  local offsets = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
    AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
  ];
  for (local index = 1; index < tiles.len() - 1; index++) {
    local anchor = tiles[index];
    if (AIRail.IsRailStationTile(anchor) || !AIRail.IsRailTile(anchor)) continue;
    local stationSide = tiles[index - 1];
    local lineSide = tiles[index + 1];
    if (AIMap.DistanceManhattan(stationSide, anchor) != 1) continue;
    if (AIMap.DistanceManhattan(lineSide, anchor) != 1) continue;

    AIRail.BuildRail(stationSide, anchor, lineSide);
    if (!AIRail.AreTilesConnected(stationSide, anchor, lineSide)) continue;

    foreach (offset in offsets) {
      local candidate = anchor + offset;
      if (!AIMap.IsValidTile(candidate)) continue;
      if (forbidden != null && (candidate in forbidden)) continue;
      if (AIRail.IsRailStationTile(candidate) || AIRail.IsRailDepotTile(candidate)) continue;
      local onRoute = false;
      foreach (routeTile in tiles) {
        if (routeTile == candidate) { onRoute = true; break; }
      }
      if (onRoute) continue;

      {
        /* Bouclier : AIAccounting compte le cout SIMULE des commandes jouees en AITestMode
         * (script_object.cpp:299-302). Sans lui, le sondage qui REUSSIT ajoutait un prix de
         * depot fantome (~450 £) au `actualCost` de chaque ligne rail. Le destructeur d'un
         * AIAccounting imbrique restaure le total superieur, donc tout ce qui entre ici est jete. */
        local shield = AIAccounting();
        local testMode = AITestMode();
        if (!AIRail.BuildRailDepot(candidate, anchor)) continue;
      }
      AITile.DemolishTile(candidate);
      AIRail.BuildRail(stationSide, anchor, candidate);
      if (!AIRail.AreTilesConnected(stationSide, anchor, candidate) ||
          !AIRail.AreTilesConnected(stationSide, anchor, lineSide)) {
        AIRail.RemoveRail(stationSide, anchor, candidate);
        AIRail.BuildRail(stationSide, anchor, lineSide);
        continue;
      }
      if (!AIRail.BuildRailDepot(candidate, anchor) ||
          AIRail.GetRailDepotFrontTile(candidate) != anchor) {
        AIRail.RemoveRail(stationSide, anchor, candidate);
        AIRail.BuildRail(stationSide, anchor, lineSide);
        continue;
      }
      return candidate;
    }
  }
  return null;
}

/* Une tentative ratee apres la pose ne doit RIEN laisser sur la carte.
 *
 * Sans cela chaque echec abandonne deux gares et toute une voie : mesure du 2026-08-28, 28 gares
 * orphelines pour zero ligne. Le cout n'est pas que financier -- une gare sans transfert depuis
 * 50 jours coute -15 par mois de note d'autorite locale (docs/mecanique_jeu.md §7), donc les
 * ruines degradent activement la capacite a construire dans ces villes. */
function OpexRollback(tiles, planA, planB, depot, vehicles)
{
  /* OpexBuildTrains ne demarre les convois qu'apres que TOUS leurs ordres sont poses. Si un
   * ordre echoue, ils sont donc encore vendables dans le depot et le rollback reste vraiment
   * atomique, y compris pour un nouveau quai joint. */
  if (vehicles != null) {
    foreach (vehicle in vehicles) {
      if (AIVehicle.IsValidVehicle(vehicle) && AIVehicle.IsStoppedInDepot(vehicle)) {
        AIVehicle.SellVehicle(vehicle);
      }
    }
  }
  if (depot != null) AITile.DemolishTile(depot);
  if (planA != null) {
    for (local i = 0; i < planA.length; i++) {
      local t = planA.anchor + planA.step * i;
      if (AIRail.IsRailStationTile(t)) AIRail.RemoveRailStationTileRectangle(t, t, false);
      else AITile.DemolishTile(planA.anchor + planA.step * i);
    }
  }
  if (planB != null && !(("v307Prebuilt" in planB) && planB.v307Prebuilt == 1)) {
    for (local i = 0; i < planB.length; i++) {
      local t = planB.anchor + planB.step * i;
      if (AIRail.IsRailStationTile(t)) AIRail.RemoveRailStationTileRectangle(t, t, false);
      else AITile.DemolishTile(planB.anchor + planB.step * i);
    }
    if ((V307_SINK_ROOM & 2) != 0 && OpexV307SinkRoomPlatforms(planB) == 2) {
      for (local i = 0; i < planB.length; i++) {
        local t = planB.v307RoomStripAnchor + planB.step * i;
        if (AIRail.IsRailStationTile(t)) AIRail.RemoveRailStationTileRectangle(t, t, false);
        else AITile.DemolishTile(t);
      }
    }
  }
  OpexAir0310InvalidateSiteValidity();
  if (tiles == null) return;
  for (local i = 1; i < tiles.len() - 1; i++) {
    AITile.DemolishTile(tiles[i]);
  }
}

/* V163 : prix des wagons du second cargo d'une ligne ou d'un candidat (0 sans second cargo). */
function OpexV163WagonsPrice(catalog, line)
{
  if (!("wagons2" in line) || line.wagons2 <= 0 || !("cargo2" in line)) return 0;
  if (!(line.cargo2 in catalog.wagonByCargo)) return 0;
  return line.wagons2 * catalog.wagonByCargo[line.cargo2].price;
}

/* V163 : (cargo2, wagons2) a passer a OpexBuildTrains pour une ligne ou un candidat. */
function OpexV163Cargo2(line)
{
  return (("wagons2" in line) && line.wagons2 > 0 && ("cargo2" in line)) ? line.cargo2 : -1;
}
function OpexV163Wagons2(line)
{
  return (("wagons2" in line) && line.wagons2 > 0 && ("cargo2" in line)) ? line.wagons2 : 0;
}

/* V301 : le wagon `car` (dernier de rollbackVehicles, pas encore attache) ne tient pas ; la rame
 * garde ses `kept` wagons. Le wagon isole est vendu et retire de la liste de rollback. */
function OpexV301Trim(car, rollbackVehicles, planned, kept, locoLength, limit)
{
  local err = AIError.GetLastError();
  if (rollbackVehicles.len() > 0 && rollbackVehicles[rollbackVehicles.len() - 1] == car) rollbackVehicles.pop();
  AIVehicle.SellVehicle(car);
  if (DECISION_LOG) {
    OpexDecide("V301_TRIM", "wagons=" + planned + "->" + kept + " loco_len=" + locoLength + " limit=" + limit
               + " err=" + err);
  }
}

function OpexBuildTrains(catalog, cargo, kind, depotTile, exitA, exitB, wanted, loco, wagons, platformLength, startVehicles = true,
                         cargo2 = -1, wagons2 = 0)
{
  local wagon = catalog.wagonByCargo[cargo];
  /* V163 : wagons du second cargo, attaches derriere ceux du premier dans la meme rame. */
  local wagon2 = (wagons2 > 0 && (cargo2 in catalog.wagonByCargo)) ? catalog.wagonByCargo[cargo2] : null;
  if (wagon2 == null) wagons2 = 0;
  local built = 0;
  local vehicles = [];          // locomotives tete : identite persistante de la ligne
  local rollbackVehicles = [];  // tete ET wagons isoles : cleanup atomique si MoveWagon echoue
  local lastError = 0;
  local diag = null;
  local measuredLength = 0;
  local measuredLocoLength = 0;
  local measuredWagonLength = 0;
  /* OpexRailNominalMaxWagons(p) = 2*p-1 donne, avec les mesures vanilla 8/16 + 8/16,
   * 8 + (2*p-1)*8 = p*16. Le constructeur applique exactement cette limite, puis mesure chaque
   * vehicule reel pour que ni une locomotive ni un wagon NewGRF plus long ne rende le modele plus
   * optimiste que le quai bati. */
  local nominalMaxWagons = OpexRailNominalMaxWagons(platformLength);
  local trainLengthLimit = platformLength * 16;
  if (wagons < 1 || wagons + wagons2 > nominalMaxWagons || trainLengthLimit < 1) {
    return { built = 0, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
             failed = true, failure = "LENGTH", error = 0, diag = diag };
  }
  /* Ordres de chargement : pour le fret (sens unique), seule la source attend le plein chargement.
   * Pour les passagers, plein chargement aux deux bouts (patron trAIns).
   * Le puits fret reste a OF_NONE : C53_ORDER_NOLOAD est fige a false. */
  local nonstopFlag = AIOrder.OF_NON_STOP_INTERMEDIATE;
  local flagsA = AIOrder.OF_FULL_LOAD_ANY | nonstopFlag;
  local flagsB = ((kind == "freight") ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag;
  for (local i = 0; i < wanted; i++) {
    local train = AIVehicle.BuildVehicle(depotTile, loco.id);
    if (!AIVehicle.IsValidVehicle(train)) {
      lastError = AIError.GetLastError();
      /* Diagnostic minimal au moment exact de l'echec : c'est moins cher que de deviner. */
      local testOk = 0;
      {
        /* Meme bouclier que dans OpexBuildDepot : ce sondage ne doit rien laisser dans la
         * comptabilite du caller, sans quoi un echec de convoi facturerait une loco fantome. */
        local shield = AIAccounting();
        local probe = AITestMode();
        testOk = AIVehicle.BuildVehicle(depotTile, loco.id) != null ? 1 : 0;
      }
      diag = {
        railtype = AIRail.GetCurrentRailType(),
        isDepot = AIRail.IsRailDepotTile(depotTile) ? 1 : 0,
        buildable = AIEngine.IsBuildable(loco.id) ? 1 : 0,
        canRun = AIEngine.CanRunOnRail(loco.id, AIRail.GetCurrentRailType()) ? 1 : 0,
        price = loco.price,
        cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF),
        engineRail = AIEngine.GetRailType(loco.id),
        depotRail = AIRail.GetRailType(depotTile),
        vehType = AIEngine.GetVehicleType(loco.id),
        testOk = testOk,
      };
      /* Le chemin et les convois deja poses ont une valeur : apres le premier train, garder une
       * frequence moindre est preferable a jeter l'A* et toute la ligne. Seul l'echec du tout
       * premier train laisse la ligne sans service et doit declencher le rollback. */
      if (built == 0) {
        return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                 failed = true, failure = "VEHICLE", error = lastError, diag = diag };
      }
      break;
    }
    /* Conserver le train avant les ordres : un echec d'ordre doit aussi pouvoir le vendre dans le
     * rollback, au lieu de laisser un depot impossible a demolir. */
    vehicles.append(train);
    rollbackVehicles.append(train);
    local trainLength = AIVehicle.GetLength(train);
    measuredLocoLength = trainLength;
    for (local w = 0; w < wagons + wagons2; w++) {
      local car = AIVehicle.BuildVehicle(depotTile, w < wagons ? wagon.id : wagon2.id);
      if (AIVehicle.IsValidVehicle(car)) {
        rollbackVehicles.append(car);
        local carLength = AIVehicle.GetLength(car);
        measuredWagonLength = carLength;
        /* Aucune longueur par moteur n'existe dans NoAI 15.3 : cette mesure porte donc sur les
         * vehicules reels, dans l'unite du moteur (1/16 de tuile). Elle verifie la formule qui a
         * donne `wagons` AVANT de lancer le train ; un NewGRF plus long ne peut pas deborder
         * silencieusement du quai. */
        if (trainLength + carLength > trainLengthLimit) {
          if ((V301_NOTRAIN_FIX & 4) && w > 0) {
            OpexV301Trim(car, rollbackVehicles, wagons + wagons2, w, measuredLocoLength, trainLengthLimit);
            break;
          }
          return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                   failed = true, failure = "LENGTH", error = 0, diag = diag, trainLength = trainLength,
                   locoLength = measuredLocoLength, wagonLength = measuredWagonLength };
        }
        if (!AIVehicle.MoveWagon(car, 0, train, 0)) {
          if ((V301_NOTRAIN_FIX & 4) && w > 0 && AIError.GetLastError() == AIVehicle.ERR_VEHICLE_TOO_LONG) {
            OpexV301Trim(car, rollbackVehicles, wagons + wagons2, w, measuredLocoLength, trainLengthLimit);
            break;
          }
          return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                   failed = true, failure = "WAGON", error = AIError.GetLastError(), diag = diag,
                   trainLength = trainLength, locoLength = measuredLocoLength,
                   wagonLength = measuredWagonLength };
        }
        trainLength += carLength;
      } else {
        return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                 failed = true, failure = "WAGON", error = AIError.GetLastError(), diag = diag,
                 trainLength = trainLength, locoLength = measuredLocoLength,
                 wagonLength = measuredWagonLength };
      }
    }
    measuredLength = trainLength;
    local okA = AIOrder.AppendOrder(train, exitA, flagsA);
    if (!okA) {
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "ORDER", error = AIError.GetLastError(), diag = diag };
    }
    local okB = AIOrder.AppendOrder(train, exitB, flagsB);
    if (!okB || AIOrder.GetOrderCount(train) != 2) {
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "ORDER", error = !okB ? AIError.GetLastError() : 0, diag = diag };
    }
    built++;
  }
  /* Pas de train lance avant que la transaction entiere soit certaine : voir OpexRollback.
   * La double voie construit un convoi par depot puis les demarre ensemble. */
  if (startVehicles) {
    local started = [];
    local startFailed = false;
    foreach (train in vehicles) {
      if (!AIVehicle.StartStopVehicle(train)) {
        startFailed = true;
        break;
      }
      started.append(train);
    }
    if (startFailed) {
      foreach (train in started) {
        AIVehicle.StartStopVehicle(train);
      }
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "START", error = AIError.GetLastError(), diag = diag,
               trainLength = measuredLength, locoLength = measuredLocoLength,
               wagonLength = measuredWagonLength };
    }
  }
  return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
           failed = false, failure = "", error = lastError, diag = diag, trainLength = measuredLength,
           locoLength = measuredLocoLength, wagonLength = measuredWagonLength };
}

/* Premier signal : PBS bidirectionnel devant le quai, pas un sens unique
 * au milieu (mecanique_jeu §12.2). GetSignalType(tile, front) : front est
 * la case vers laquelle le signal REGARDE. -1 = rien a poser (pas de rail). */
function OpexTryBuildSignal(tile, front)
{
  if (!AIMap.IsValidTile(tile) || !AIMap.IsValidTile(front)) return -1;
  if (AIMap.DistanceManhattan(tile, front) != 1) return -1;
  if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) return -1;
  if (!AIRail.IsRailTile(tile)) return -1;
  if (AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) return -1;
  if (AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_NONE) return 1;
  if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS)) return 1;
  if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_NORMAL_TWOWAY)) return 1;
  return 0;
}

function OpexTileTrackCount(tile)
{
  if (!AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) {
    return 0;
  }
  local tracks = AIRail.GetRailTracks(tile);
  if (tracks == AIRail.RAILTRACK_INVALID) return 0;
  local n = 0;
  if ((tracks & AIRail.RAILTRACK_NE_SW) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_SE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_NE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_SW_SE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_SW) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NE_SE) != 0) n++;
  return n;
}

function OpexAccountSignal(built, acc)
{
  if (built == 1) acc.ok++;
  else if (built == 0) acc.fail++;
}

/* Essaie les deux orientations d'un PBS. -1 = emplacement inutilisable (pont, gare, deja pose),
 * 0 = commande refusee, 1 = pose ou deja present. */
function OpexTryBuildSignalEither(tile, a, b)
{
  local first = OpexTryBuildSignal(tile, a);
  if (first == 1) return 1;
  if (b != null && AIMap.IsValidTile(b) && b != a) {
    local second = OpexTryBuildSignal(tile, b);
    if (second == 1) return 1;
    if (second == 0) return 0;
  }
  return first;
}

/* Cherche un PBS sur une voie simple en s’éloignant d’une gare ou d’un aiguillage.
 * OpenTTD 15.3 refuse structurellement les signaux sur TracksOverlap : le filtre trackCount == 1
 * est donc une precondition moteur, pas une heuristique. */
function OpexPlacePathApproachSignal(tiles, start, step, minDistance, maxDistance, acc, kind, used)
{
  local last = tiles.len() - 1;
  for (local distance = minDistance; distance <= maxDistance; distance++) {
    local i = start + step * distance;
    if (i <= 0 || i >= last) break;
    local tile = tiles[i];
    if (tile in used || OpexTileTrackCount(tile) != 1) continue;
    local built = OpexTryBuildSignalEither(tile, tiles[i - step], tiles[i + step]);
    if (built == -1) continue;
    OpexAccountSignal(built, acc);
    if (built == 1) {
      used[tile] <- true;
    } else {
      acc.failures.append({ kind = kind, slot = i, error = AIError.GetLastError(),
                            tracks = OpexTileTrackCount(tile),
                            x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile) });
    }
    return built;
  }
  acc.skip++;
  return -1;
}

function OpexPlaceJoinSignals(planA, planB, tiles, depot)
{
  local acc = { ok = 0, fail = 0, skip = 0, junc = 0, failures = [] };
  local last = tiles.len() - 1;
  local used = {};

  /* Slot 1 est la gorge de gare et porte souvent deux tracks. Deux tuiles plus loin suffit a
   * degager un train dont la longueur est bornee par le quai. */
  OpexPlacePathApproachSignal(tiles, 0, 1, 2, 8, acc, "A", used);
  OpexPlacePathApproachSignal(tiles, last, -1, 2, 8, acc, "B", used);

  /* Le depot ajoute un vrai aiguillage a la voie. Les PBS vont sur les deux approches simples,
   * jamais sur la tuile junc : CmdBuildSingleSignal refuse tout TracksOverlap. */
  if (depot != null) {
    local junc = AIRail.GetRailDepotFrontTile(depot);
    local juncIndex = -1;
    for (local i = 1; i < last; i++) {
      if (tiles[i] == junc) { juncIndex = i; break; }
    }
    if (juncIndex >= 0 && OpexTileTrackCount(junc) >= 2) {
      acc.junc++;
      OpexPlacePathApproachSignal(tiles, juncIndex, -1, 1, 8, acc, "L", used);
      OpexPlacePathApproachSignal(tiles, juncIndex, 1, 1, 8, acc, "R", used);
    }
  }
  return acc;
}

/* Quais + economie, AVANT l'A*. Separe pour que le mode reprenable puisse poser le pathfinder
 * et rendre la main sans rejouer ce travail a chaque tranche. plansA == null => echec, pas de
 * recherche a lancer. */
function OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)
{
  /* C67.6 rail : capital du candidat tel que finance avant A* (distance Manhattan). */
  if (DECISION_LOG && !("preCapital" in candidate)
      && !(("capitalIsActual" in candidate) && candidate.capitalIsActual))
    candidate.preCapital <- candidate.capital;
  local plan = { ok = false, reason = "", iterations = 0, opcodes = 0,
                 phaseOps = { plans = -1, search = -1, stations = -1, track = -1, trains = -1 },
                 plansA = null, plansB = null, planA = null, planB = null,
                 length = candidate.platformLength,
                 slopeRelaxed = 0, siteClear = 0, siteCargo = 0, siteCmd = 0,
                 tiles = null, depot = null, tiles2 = null, planA2 = null, planB2 = null, depot2 = null,
                 doubleTrack = 0, doubleTiles = 0, doubleDepot = null, doubleSkip = 0,
                 structures = null, structures2 = null,
                 segmentedSegments = 0, segmentedBacktracks = 0, segmentedLocalChoices = 0,
                 budgetInfo = null, iterationBudget = 0, capital = candidate.capital };

  plan.budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio, hardCap);
  plan.iterationBudget = plan.budgetInfo.budget;

  budget.begin();
  local platformPlans = OpexRailPlatformPlans(catalog, candidate);
  local plansOps = budget.end("build_plans");
  plan.opcodes += plansOps;
  if (plan.phaseOps.plans < 0) plan.phaseOps.plans = 0;
  plan.phaseOps.plans += plansOps;
  if (platformPlans.plansA == null || platformPlans.reason != "OK") {
    plan.reason = platformPlans.reason;
    local stats = platformPlans.reason == "SITEB" ? platformPlans.statsB : platformPlans.statsA;
    plan.siteClear = stats.nClear;
    plan.siteCargo = stats.nCargo;
    plan.siteCmd = stats.nCmd;
    return plan;
  }
  plan.plansA = platformPlans.plansA;
  plan.plansB = platformPlans.plansB;
  plan.length = platformPlans.length;
  plan.slopeRelaxed = platformPlans.slopeRelaxed ? 1 : 0;

  local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
                                      candidate.monthly, candidate.kind, plan.length,
                                      null, null, null, null, null, OpexV163CandidateSecondary(candidate));
  if (economics == null) { plan.reason = "ECON"; return plan; }
  plan.capital = economics.capital;
  OpexApplyRailEconomics(candidate, economics);
  plan.budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio, hardCap);
  plan.iterationBudget = plan.budgetInfo.budget;
  return plan;
}

/* Assemble le plan une fois l'A* termine. `search.iterations` DOIT etre le cumul de toutes
 * les tranches : c'est le denominateur du classement. */
function OpexCompleteRailRouteAfterSearch(catalog, candidate, plan, search)
{
  plan.iterations = search.iterations;
  if (("segments" in search)) {
    plan.segmentedSegments = search.segments;
    plan.segmentedBacktracks = search.backtracks;
    plan.segmentedLocalChoices = search.localChoices;
  }
  if (DECISION_LOG && V197_GUIDED_DOUBLE && OpexV190Active() && candidate != null && ("kind" in candidate) && candidate.kind == "freight") {
    local track1Ok = (search.path != false && search.path != null) ? 1 : 0;
    local track1Reason = ("stop" in search) ? search.stop : (track1Ok ? "OK" : "NOPA");
    OpexDecide("V197", "track=1 ok=" + track1Ok + " iters=" + search.iterations + " reason=" + track1Reason);
  }
  if (search.path == false || search.path == null) { plan.reason = search.stop; return plan; }

  local tiles = OpexResolveSearchTiles(search);
  if (tiles.len() < 3) { plan.reason = "SHORT"; return plan; }
  local last = tiles.len() - 1;
  local planA = (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_EXACT_IDENTITY)
      ? OpexMatchPlanExact(plan.plansA, tiles[0], tiles[1])
      : OpexMatchPlan(plan.plansA, tiles[0]);
  local planB = (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_EXACT_IDENTITY)
      ? OpexMatchPlanExact(plan.plansB, tiles[last], tiles[last - 1])
      : OpexMatchPlan(plan.plansB, tiles[last]);
  if (planA == null || planB == null) { plan.reason = "NOMATCH"; return plan; }
  if (V307_SINK_ROOM > 0 && !OpexV307SinkRoomPathClear(planB, tiles)) {
    if ((V307_SINK_ROOM & 8) != 0 && (V307_SINK_ROOM & 3) != 0) {
      OpexV307SinkRoomDrop(planB, candidate);
    } else {
      plan.reason = "TRKFAIL";
      plan.geometryReason <- "sink_room";
      return plan;
    }
  }

  if (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PREFILTER) {
    local geometryIssue = OpexRailPathGeometryIssue(tiles, planA, planB);
    if (geometryIssue != null) {
      /* Conserver TRKFAIL dans la telemetrie historique, mais distinguer sa persistance pour la
       * memoire d'abandon. Aucun AITile.DemolishTile/BuildRailStation n'a encore ete execute. */
      plan.reason = "TRKFAIL";
      plan.persistentGeometry <- RAIL_GEOMETRY_PAIR_MEMORY;
      plan.geometryReason <- geometryIssue.kind;
      if (DECISION_LOG) {
        OpexDecide("RAIL_GEOM_REJECT", "kind=" + geometryIssue.kind + " tile=" + geometryIssue.tile
                   + " src=" + candidate.src + " dst=" + candidate.dst);
      }
      return plan;
    }
  }

  plan.tiles = tiles;
  plan.structures = OpexResolveSearchStructures(search);
  plan.planA = planA;
  plan.planB = planB;

  /* Recalibrer avec la longueur effectivement trouvee AVANT de decider si une
   * seconde voie est necessaire. Sinon un detour peut faire passer le besoin de
   * une a deux rames apres que la topologie a ete figee : le constructeur ne
   * dispose alors que du premier depot et ne livre qu'une rame. */
  local routeDistance = 0;
  for (local i = 1; i < tiles.len(); i++) {
    routeDistance += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
  }
  /* Journal seulement : longueur du trace pour RAIL_ATTEMPT (detour du poids A*). */
  if (DECISION_LOG) {
    if (!("routeLen" in candidate)) candidate.routeLen <- routeDistance;
    else candidate.routeLen = routeDistance;
  }
  if (routeDistance > 0) {
    local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
                                        candidate.monthly, candidate.kind, plan.length,
                                        routeDistance, null, null, null, null,
                                        OpexV163CandidateSecondary(candidate));
    if (EQUIPMENT_ROI_PROBE) {
      OpexM3ProbeRailEquipment(catalog, candidate, plan.length, routeDistance, economics);
    }
    if (economics != null) {
      plan.capital = economics.capital;
      OpexApplyRailEconomics(candidate, economics);
    }
  }

  if (!OpexV198Active() && (candidate.trains > 1 || (OpexV190Active() && candidate.kind == "freight"))) {
    local remain = plan.iterationBudget - plan.iterations;
    if (remain < ATTEMPT_FLOOR) remain = ATTEMPT_FLOOR;
    /* Sous rail_search_resumable, la borne tick historique tuerait cette seconde recherche
     * des qu'elle est entrelacee. OpexTryDoubleTrack sort de toute facon avant l'A* pour une
     * ligne neuve (gares pas encore posees, docs/taches.md S0) : le changement de deadline
     * n'a donc d'effet que si ce chemin redevient vivant. */
    local dualDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS;
    local dual = null;
    if (OpexV190Active() && candidate.kind == "freight") {
      dual = OpexV190PlanDoubleTrack(catalog, planA, planB, tiles, remain, dualDeadline, plan.structures);
    } else {
      dual = OpexTryDoubleTrack(catalog, planA, planB, tiles, null, 0,
                                remain, dualDeadline, []);
    }
    /* Cumul : les iterations de la seconde voie s'ajoutent au denominateur, pas le remplacent. */
    plan.iterations += dual.iterations;
    plan.doubleSkip = dual.skip;
    plan.doubleReason <- ("reason" in dual) ? dual.reason : "";
    if ("step" in dual) plan.doubleStep <- dual.step;
    if (dual.ok) {
      plan.doubleTrack = 1;
      plan.doubleTiles = dual.tiles.len();
      plan.doubleDepot = ("depot" in dual) ? dual.depot : null;
      plan.tiles2 = dual.tiles;
      plan.planA2 = dual.planA;
      plan.planB2 = dual.planB;
      plan.depot2 = ("depot" in dual) ? dual.depot : null;
      plan.structures2 = dual.structures;
    }
  }

  plan.ok = true;
  plan.reason = "OK";
  return plan;
}

/* V131 : degagement urbain (clearance) de l'A* rail pour eviter les centres-villes
 * et les emprises de developpement futur (routes, immeubles, aeroports concurrents). */
function OpexV131LogClearance(candidate, plan, clearanceTiles)
{
  if (!DECISION_LOG || !V131_TOWN_CLEARANCE) return;
  local src = (candidate != null && ("src" in candidate)) ? candidate.src : -1;
  local dst = (candidate != null && ("dst" in candidate)) ? candidate.dst : -1;
  local count = (clearanceTiles != null) ? clearanceTiles.len() : 0;
  local pathLen = (plan != null && ("tiles" in plan) && plan.tiles != null) ? plan.tiles.len() : 0;
  OpexDecide("V131_CLEAR", "src=" + src + " dst=" + dst + " cleared_tiles=" + count + " avoided=" + count + " path_len=" + pathLen);
}

function OpexV131BuildTownClearance(candidate, plansA, plansB)
{
  if (!V131_TOWN_CLEARANCE || candidate == null) return [];
  if (!("src" in candidate) || !("dst" in candidate)) return [];

  local srcX = AIMap.GetTileX(candidate.src);
  local srcY = AIMap.GetTileY(candidate.src);
  local dstX = AIMap.GetTileX(candidate.dst);
  local dstY = AIMap.GetTileY(candidate.dst);
  local minX = (srcX < dstX ? srcX : dstX) - 15;
  local maxX = (srcX > dstX ? srcX : dstX) + 15;
  local minY = (srcY < dstY ? srcY : dstY) - 15;
  local maxY = (srcY > dstY ? srcY : dstY) + 15;

  local mapW = AIMap.GetMapSizeX();
  local mapH = AIMap.GetMapSizeY();
  if (minX < 1) minX = 1;
  if (maxX > mapW - 2) maxX = mapW - 2;
  if (minY < 1) minY = 1;
  if (maxY > mapH - 2) maxY = mapH - 2;

  local exempt = {};
  local allPlans = [];
  if (plansA != null) { foreach (p in plansA) if (p != null) allPlans.push(p); }
  if (plansB != null) { foreach (p in plansB) if (p != null) allPlans.push(p); }

  foreach (st in allPlans) {
    if (("anchor" in st) && ("step" in st) && ("length" in st)) {
      for (local i = 0; i < st.length; i++) {
        exempt[st.anchor + st.step * i] <- true;
      }
    }
    if ("lead" in st) {
      exempt[st.lead] <- true;
      local lx = AIMap.GetTileX(st.lead);
      local ly = AIMap.GetTileY(st.lead);
      for (local dx = -V131_TOWN_CLEAR_BUFFER; dx <= V131_TOWN_CLEAR_BUFFER; dx++) {
        local limY = V131_TOWN_CLEAR_BUFFER - (dx >= 0 ? dx : -dx);
        for (local dy = -limY; dy <= limY; dy++) {
          local t = AIMap.GetTileIndex(lx + dx, ly + dy);
          if (AIMap.IsValidTile(t)) exempt[t] <- true;
        }
      }
    }
    if ("station_exit" in st) exempt[st.station_exit] <- true;
  }

  local clearance = {};
  local towns = AITownList();
  foreach (town, _ in towns) {
    local loc = AITown.GetLocation(town);
    local tx = AIMap.GetTileX(loc);
    local ty = AIMap.GetTileY(loc);
    if (tx < minX || tx > maxX || ty < minY || ty > maxY) continue;

    local pop = AITown.GetPopulation(town);
    local radius = 4 + (pop / 500);
    if (radius < 4) radius = 4;
    if (radius > 10) radius = 10;

    for (local dx = -radius; dx <= radius; dx++) {
      local limY = radius - (dx >= 0 ? dx : -dx);
      for (local dy = -limY; dy <= limY; dy++) {
        local t = AIMap.GetTileIndex(tx + dx, ty + dy);
        if (AIMap.IsValidTile(t) && !(t in exempt)) {
          clearance[t] <- true;
        }
      }
    }
  }

  local list = [];
  foreach (tile, _ in clearance) list.push(tile);
  return list;
}

/* Precalcule le plan physique complet d'une ligne ferroviaire (quais, economie, trace A*,
 * depot, double voie eventuelle) SANS modifier la carte du jeu ni depenser de tresorerie.
 * Mode bloquant : conserve pour rail_search_resumable=0. Le mode reprenable orchestre
 * Prepare / tranches / Complete depuis OpexAI::_continueRailSearch. */
function OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)
{
  local plan = OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap);
  if (plan.plansA == null) return plan;

  budget.begin();
  local deadlineTick = AIController.GetTick() + plan.iterationBudget / 3 + BUILD_TICK_MARGIN;
  local clearanceTiles = V131_TOWN_CLEARANCE ? OpexV131BuildTownClearance(candidate, plan.plansA, plan.plansB) : null;
  if (OpexV190Active() && candidate.kind == "freight") {
    clearanceTiles = OpexV190MergeIgnoredTiles(clearanceTiles, plan.plansA, plan.plansB);
  }
  local outwardSide = (V197_GUIDED_DOUBLE && OpexV190Active() && candidate.kind == "freight") ? 1 : null;
  local search = OpexSearchPath(plan.plansA, plan.plansB, plan.iterationBudget, deadlineTick, clearanceTiles, null, outwardSide, null);
  local searchOps = budget.end("build_search");
  plan.opcodes += searchOps;
  if (plan.phaseOps.search < 0) plan.phaseOps.search = 0;
  plan.phaseOps.search += searchOps;
  if (DECISION_LOG) OpexAddRailSearchOps(candidate, searchOps);
  if (DECISION_LOG && V131_TOWN_CLEARANCE && clearanceTiles != null) {
    OpexV131LogClearance(candidate, plan, clearanceTiles);
  }
  return OpexCompleteRailRouteAfterSearch(catalog, candidate, plan, search);
}

/* Devis réel par AITestMode + AIAccounting avant engagement (docs/taches.md §0 tervicies point 8 & C7).
 * Simule la construction des gares et de la voie sans modifier la carte pour mesurer le coût exact. */
/* R23 : null signifie devis invalide, jamais un cout partiel utilisable.
 * Capturer le premier motif avant toute autre commande. L'argument diagnostic
 * est optionnel pour conserver les appelants qui ne demandent que le cout. */
function OpexRailQuoteFailure(failure, reason, tile, error)
{
  if (failure != null) {
    failure.reason <- reason;
    failure.tile <- tile;
    failure.error <- error;
  }
  return null;
}

function OpexSimulateRailInfraCost(plan, failure = null)
{
  local simulatedInfra = 0;
  {
    local testMode = AITestMode();
    local accounting = AIAccounting();

    local planA = plan.planA;
    local planB = plan.planB;
    local tiles = plan.tiles;
    for (local i = 0; i < planA.length; i++) {
      local tile = planA.anchor + planA.step * i;
      if (!AITile.DemolishTile(tile)) return OpexRailQuoteFailure(failure, "STNFAIL", tile, AIError.GetLastError());
    }
    if (!("v307Prebuilt" in planB)) {
      for (local i = 0; i < planB.length; i++) {
        local tile = planB.anchor + planB.step * i;
        if (!AITile.DemolishTile(tile)) return OpexRailQuoteFailure(failure, "STNFAIL", tile, AIError.GetLastError());
      }
      OpexV307SinkRoomDemolishExtra(planB);
    }
    local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
    local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
    if (!AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA)) {
      return OpexRailQuoteFailure(failure, "STNFAIL", planA.anchor, AIError.GetLastError());
    }
    local okB = ("v307Prebuilt" in planB) ? OpexV307SinkRoomPrebuiltReady(planB)
        : AIRail.BuildRailStation(OpexV307SinkRoomStationAnchor(planB), planB.direction,
                                  OpexV307SinkRoomPlatforms(planB), planB.length, stIdB);
    if (!okB) {
      return OpexRailQuoteFailure(failure, "STNFAIL", planB.anchor, AIError.GetLastError());
    }

    for (local i = 1; i < tiles.len() - 1; i++) {
      local prev = tiles[i - 1];
      local cur = tiles[i];
      local next = tiles[i + 1];
      local ok = false;
      if (prev == next) {
        continue;
      } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
        continue;
      } else if (AIMap.DistanceManhattan(cur, next) > 1) {
        local plannedKind = OpexPlannedStructureKind(
            (("structures" in plan) ? plan.structures : null), cur, next);
        if (plannedKind == "tunnel" ||
            (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
          ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
        } else {
          local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
          OpexBridgeSortBySpeed(bridges);
          if (bridges.IsEmpty()) {
            return OpexRailQuoteFailure(failure, "TRKFAIL", cur, AIError.ERR_PRECONDITION_FAILED);
          }
          ok = AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
        }
      } else {
        ok = AIRail.BuildRail(prev, cur, next);
      }
      if (!ok) {
        local error = AIError.GetLastError();
        /* Seulement une voie DEJA presente peut etre testee par connectivite.
         * Ne jamais exiger AreTilesConnected apres une pose seulement simulee. */
        if (error == AIError.ERR_ALREADY_BUILT &&
            AIMap.DistanceManhattan(prev, cur) == 1 && AIMap.DistanceManhattan(cur, next) == 1 &&
            AIRail.IsRailTile(cur) && AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF) &&
            AIRail.GetRailType(cur) == AIRail.GetCurrentRailType() &&
            AIRail.AreTilesConnected(prev, cur, next)) continue;
        return OpexRailQuoteFailure(failure, "TRKFAIL", cur, error);
      }
    }
    if (OpexV190Active() && ("doubleTrack" in plan) && plan.doubleTrack == 1
        && ("tiles2" in plan) && plan.tiles2 != null
        && ("planA2" in plan) && plan.planA2 != null
        && ("planB2" in plan) && plan.planB2 != null) {
      local pA2 = plan.planA2;
      local pB2 = plan.planB2;
      for (local i = 0; i < pA2.length; i++) {
        AITile.DemolishTile(pA2.anchor + pA2.step * i);
      }
      for (local i = 0; i < pB2.length; i++) {
        AITile.DemolishTile(pB2.anchor + pB2.step * i);
      }
      local testIdA = AIStation.GetStationID(planA.anchor);
      local testIdB = AIStation.GetStationID(planB.anchor);
      AIRail.BuildRailStation(pA2.anchor, pA2.direction, 1, pA2.length, testIdA);
      AIRail.BuildRailStation(pB2.anchor, pB2.direction, 1, pB2.length, testIdB);

      local t2 = plan.tiles2;
      for (local i = 1; i < t2.len() - 1; i++) {
        local prev = t2[i - 1];
        local cur = t2[i];
        local next = t2[i + 1];
        if (prev == next || AIMap.DistanceManhattan(prev, cur) > 1) continue;
        if (AIMap.DistanceManhattan(cur, next) > 1) {
          local plannedKind = OpexPlannedStructureKind(
              (("structures2" in plan) ? plan.structures2 : null), cur, next);
          if (plannedKind == "tunnel" || (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
            AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
          } else {
            local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
            OpexBridgeSortBySpeed(bridges);
            if (!bridges.IsEmpty()) {
              AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
            }
          }
        } else {
          AIRail.BuildRail(prev, cur, next);
        }
      }
    }
    simulatedInfra = accounting.GetCosts();
  }
  return simulatedInfra;
}

/* Capital total du devis rail utilise par le constructeur avant engagement. */
function OpexQuoteRailCapital(catalog, candidate, plan, failure = null)
{
  local realInfra = OpexSimulateRailInfraCost(plan, failure);
  if (realInfra == null) return null;
  if (realInfra <= 0) return 0;
  local depotCost = catalog.costRailDepot + 2 * catalog.costTrackPerTile;
  if (OpexV190Active() && ("doubleTrack" in plan) && plan.doubleTrack == 1) {
    depotCost = 2 * depotCost;
  }
  local vehicleCost = ("vehicleCost" in candidate) ? candidate.vehicleCost : 0;
  if (vehicleCost <= 0 && ("loco" in candidate) && candidate.loco != null &&
      (candidate.cargo in catalog.wagonByCargo)) {
    vehicleCost = candidate.trains * (candidate.loco.price
        + candidate.wagons * catalog.wagonByCargo[candidate.cargo].price
        + OpexV163WagonsPrice(catalog, candidate));
  }
  return realInfra + depotCost + vehicleCost;
}

/* V262 T12/T29 : plafond du mode, une lecture par chantier (pas par tuile).
 * Caps : game_settings.ini:245-291 (defauts 500/500/200/300, bancs 500).
 * GetFreeUnitNumber refuse si group_all[type].num_vehicle >= max (vehicle.cpp:1876-1891).
 * GetNumVehicles compte les primaires (group_cmd.cpp:139, IsPrimaryVehicle).
 * IsDisabledVehicleType lit ai.ai_disable_veh_* (script_gamesettings.cpp:49-55). */
function OpexVehicleSlotAvailable(vehicleType, planned)
{
  if (planned == null || planned < 1) planned = 1;
  if (AIGameSettings.IsDisabledVehicleType(vehicleType)) return false;
  local setting = "vehicle.max_trains";
  if (vehicleType == AIVehicle.VT_ROAD) setting = "vehicle.max_roadveh";
  else if (vehicleType == AIVehicle.VT_AIR) setting = "vehicle.max_aircraft";
  else if (vehicleType == AIVehicle.VT_WATER) setting = "vehicle.max_ships";
  else if (vehicleType != AIVehicle.VT_RAIL) return true;
  if (!AIGameSettings.IsValid(setting)) return true;
  local cap = AIGameSettings.GetValue(setting);
  local used = AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, vehicleType);
  if (planned > 1) return used + planned <= cap;
  return used < cap;
}

/* M4/16.2 : ne jamais engager d'infrastructure si OpenTTD n'a plus aucun slot train.
 * Ce test est volontairement duplique au plus pres de la transaction : task_rail l'utilise avant
 * de lancer l'A*, mais une recherche reprenable peut terminer plusieurs ticks plus tard, apres
 * qu'un autre chemin a consomme le dernier slot. Corps inchange : les appels rail existants
 * gardent le predicat `used < cap` et les opcodes du chemin historique. */
function OpexRailVehicleSlotAvailable()
{
  local setting = "vehicle.max_trains";
  if (!AIGameSettings.IsValid(setting)) return true;
  local cap = AIGameSettings.GetValue(setting);
  local used = AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL);
  return used < cap;
}

/* Execute la construction reelle d'un plan precalcule ou valide. */
function OpexV200WantDouble(candidate, cashReserve)
{
  if (V200_DOUBLE_CASH_K <= 0) return true;
  local capital = ("capital" in candidate) ? candidate.capital : 0;
  local need = capital * 2 + cashReserve;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local ok = money >= need;
  if (DECISION_LOG) OpexDecide("V200", "double=" + (ok ? 1 : 0) + " money=" + money + " need=" + need);
  return ok;
}

function OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)
{
  local result = { ok = false, reason = "", iterations = plan.iterations, opcodes = plan.opcodes,
                   phaseOps = { plans = plan.phaseOps.plans, search = plan.phaseOps.search,
                                stations = plan.phaseOps.stations, track = plan.phaseOps.track,
                                trains = plan.phaseOps.trains },
                   error = 0, diag = null, trains = 0, vehicles = [],
                   stationA = null, stationB = null, depot = null,
                   platformA = null, platformB = null, trainLength = 0, wagons = candidate.wagons,
                   platformLength = plan.length, locoLength = 0, wagonLength = 0,
                   wantedPlatformLength = candidate.platformLength, plansA = plan.plansA.len(),
                   plansB = plan.plansB.len(), slopeRelaxed = plan.slopeRelaxed,
                   siteClear = plan.siteClear, siteCargo = plan.siteCargo, siteCmd = plan.siteCmd,
                   siteKind = candidate.kind == "pax" ? "P" : "F",
                   capacitySignalsOk = 0, capacitySignalsFail = 0, capacitySignalSegments = 0, capacitySignalFailures = [],
                   doubleTrack = plan.doubleTrack, doubleSkip = plan.doubleSkip,
                   doubleTiles = plan.doubleTiles, doubleDepot = plan.doubleDepot,
                   capital = plan.capital, money = 0, actualCost = 0,
                   budgetInfo = plan.budgetInfo, iterationBudget = plan.iterationBudget,
                   segmentedSegments = plan.segmentedSegments,
                   segmentedBacktracks = plan.segmentedBacktracks,
                   segmentedLocalChoices = plan.segmentedLocalChoices };

  local planA = plan.planA;
  local planB = plan.planB;
  local tiles = plan.tiles;
  /* V100bis : si le devis prouve que l'interface A* memorisee n'existe plus dans le
   * vivier de quais courant, ce n'est pas une impossibilite durable de la paire. Le caller
   * efface deja candidate.railPlan apres OpexBuildLine ; un motif distinct lui permet donc
   * de laisser le scheduler refaire naturellement un A* frais, sans reintroduire le vieux
   * match station_exit-only et sans lancer un second pathfinder bloquant ici. */
  local replanGeometry = false;
  /* Franchissement colle a une sortie de gare. Deux entiers sur result, lus par
   * RAIL_ATTEMPT. -1 si le trace est absent ou trop court pour l'index. Nul au defaut. */
  if (DECISION_LOG) {
    local crossStart = -1;
    local crossEnd = -1;
    if (tiles != null && tiles.len() >= 2) {
      crossStart = (AIMap.DistanceManhattan(tiles[0], tiles[1]) > 1) ? 1 : 0;
    }
    if (tiles != null && tiles.len() >= 3) {
      local tail = tiles.len() - 1;
      crossEnd = (AIMap.DistanceManhattan(tiles[tail - 2], tiles[tail - 1]) > 1) ? 1 : 0;
    }
    result.startx <- crossStart;
    result.endx <- crossEnd;
  }
  {
    local quoteFailure = {};
    local realCapital = OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure);
    if (realCapital == null && RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_LIVE_REPLAN
        && ("reason" in quoteFailure) && quoteFailure.reason == "STNFAIL") {
      local firstError = ("error" in quoteFailure) ? quoteFailure.error : 0;
      local refresh = OpexRailRefreshExactPlatforms(catalog, candidate, plan);
      if (DECISION_LOG) {
        OpexDecide("RAIL_GEOM_REPLAN", "src=" + candidate.src + " dst=" + candidate.dst
                   + " refreshed=" + (refresh.ok ? 1 : 0) + " reason=" + refresh.reason
                   + " first_err=" + firstError);
      }
      if (refresh.ok) {
        planA = plan.planA;
        planB = plan.planB;
        result.plansA = plan.plansA.len();
        result.plansB = plan.plansB.len();
        quoteFailure = {};
        realCapital = OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure);
        if (DECISION_LOG) {
          OpexDecide("RAIL_GEOM_REPLAN_QUOTE", "src=" + candidate.src + " dst=" + candidate.dst
                     + " ok=" + (realCapital != null ? 1 : 0)
                     + " reason=" + (realCapital == null && ("reason" in quoteFailure)
                                     ? quoteFailure.reason : "OK"));
        }
      } else if (refresh.reason == "exact_interface_missing") {
        replanGeometry = true;
      }
    }
    if (realCapital == null) {
      if (DECISION_LOG) {
        local failTile = ("tile" in quoteFailure) ? quoteFailure.tile : -1;
        local failError = ("error" in quoteFailure) ? quoteFailure.error : 0;
        local failReason = ("reason" in quoteFailure) ? quoteFailure.reason : "UNKNOWN";
        OpexDecide("RAIL_QUOTE_FAIL", "src=" + candidate.src + " dst=" + candidate.dst
                   + " reason=" + failReason + " err=" + failError + " tile=" + failTile
                   + " reuse=" + ((("originServed" in candidate) && candidate.originServed) ? 1 : 0)
                   + " join_end=" + (("joinEnd" in candidate) ? candidate.joinEnd : "-")
                   + " plan_a=" + (planA != null ? planA.anchor : -1)
                   + " plan_b=" + (planB != null ? planB.anchor : -1)
                   + " lead_a=" + (planA != null && ("lead" in planA) ? planA.lead : -1)
                   + " lead_b=" + (planB != null && ("lead" in planB) ? planB.lead : -1));
      }
      result.error = quoteFailure.error;
      result.reason = result.error == AIError.ERR_NOT_ENOUGH_CASH ? "CASH"
          : (replanGeometry ? "REPLAN_GEOM" : quoteFailure.reason);
      result.quoteFailure <- quoteFailure;
      return result;
    }
    if (realCapital > 0) {
      result.capital = realCapital;
      /* G3 : le devis est une information economique, pas uniquement un garde de cash. */
      OpexApplyRailActualCapital(candidate, realCapital);
      if ((V307_SINK_ROOM & 2) != 0) OpexV307SinkRoomApplyMaintenance(candidate, planB);
      plan.capital = candidate.capital;
    }
  }

  result.money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = result.capital + cashReserve;
  if (result.money < need) {
    if (result.money < need) { result.reason = "CASH"; return result; }
  }

  /* Fail-before-spend : stations, voie, depot et terrassement commencent juste apres. */
  if (!OpexRailVehicleSlotAvailable()) {
    result.reason = "NOTRAIN";
    return result;
  }

  local costs = AIAccounting();

  budget.begin();
  OpexAir0310InvalidateSiteValidity();
  for (local i = 0; i < planA.length; i++) {
    AITile.DemolishTile(planA.anchor + planA.step * i);
  }
  if (!("v307Prebuilt" in planB)) {
    for (local i = 0; i < planB.length; i++) {
      AITile.DemolishTile(planB.anchor + planB.step * i);
    }
    OpexV307SinkRoomDemolishExtra(planB);
  }
  local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
  local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
  local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA);
  local okB = ("v307Prebuilt" in planB) ? OpexV307SinkRoomPrebuiltReady(planB)
      : AIRail.BuildRailStation(OpexV307SinkRoomStationAnchor(planB), planB.direction,
                                OpexV307SinkRoomPlatforms(planB), planB.length, stIdB);
  if (!okA || !okB) {
    /* Avant rollback : DemolishTile ecraserait GetLastError. decision_log=0 n'entre pas. */
    if (DECISION_LOG) {
      local err = AIError.GetLastError();
      OpexDecide("RAIL_STN_FAIL", "ok_a=" + (okA ? 1 : 0)
          + " ok_b=" + (okB ? 1 : 0)
          + " anchor_a=" + planA.anchor
          + " anchor_b=" + planB.anchor
          + " len_a=" + planA.length
          + " len_b=" + planB.length
          + " err=" + err);
    }
    OpexRollback(null, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    local stnOps = budget.end("build_stations");
    result.opcodes += stnOps;
    if (result.phaseOps.stations < 0) result.phaseOps.stations = 0;
    result.phaseOps.stations += stnOps;
    result.reason = "STNFAIL"; return result;
  }

  /* Table seulement sous decision_log ou garde geometrique : null au defaut 0/0. */
  local trackFailure = null;
  if (DECISION_LOG || RAIL_GEOMETRY_GUARD) trackFailure = {};
  local trackFailed = OpexBuildTrack(tiles, plan.structures, trackFailure);
  local last = tiles.len() - 1;
  local connected = trackFailed == 0 &&
      OpexRailEndConnected(planA.station_exit, tiles[1], tiles[2], "A") &&
      OpexRailEndConnected(planB.station_exit, tiles[last - 1], tiles[last - 2], "B");
  if (!connected) {
    if (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY && trackFailed > 0 &&
        OpexRailTrackFailureIsPersistentGeometry(trackFailure, planA, planB)) {
      result.persistentGeometry <- true;
      result.error = trackFailure.error;
    }
    /* Avant rollback, et seulement ici : `connected` court-circuite les deux
     * AreTilesConnected quand trackFailed > 0. Memes indices. len < 3 : -1. */
    if (DECISION_LOG) {
      local exitA = -1;
      local exitB = -1;
      if (tiles.len() >= 3) {
        exitA = AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) ? 1 : 0;
        exitB = AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit) ? 1 : 0;
      }
      local fields = "cause=" + (trackFailed > 0 ? "track" : "connect")
          + " failed=" + trackFailed
          + " tiles=" + tiles.len()
          + " exit_a=" + exitA
          + " exit_b=" + exitB;
      if (trackFailed > 0 && trackFailure != null && ("index" in trackFailure)) {
        fields += " idx=" + trackFailure.index
            + " tile=" + trackFailure.tile
            + " kind=" + trackFailure.kind
            + " err=" + trackFailure.error
            + " mprev=" + trackFailure.manh_prev
            + " mnext=" + trackFailure.manh_next;
        /* Cles optionnelles : une cle absente leve en Squirrel. */
        if ("is_buildable" in trackFailure) fields += " bld=" + trackFailure.is_buildable;
        if ("is_rail" in trackFailure) fields += " rail=" + trackFailure.is_rail;
        if ("is_station" in trackFailure) fields += " stn=" + trackFailure.is_station;
        if ("is_road" in trackFailure) fields += " road=" + trackFailure.is_road;
        if ("is_water" in trackFailure) fields += " watr=" + trackFailure.is_water;
        if ("owner_self" in trackFailure) fields += " own=" + trackFailure.owner_self;
        if ("slope" in trackFailure) fields += " slp=" + trackFailure.slope;
        if ("dup_index" in trackFailure) fields += " dup=" + trackFailure.dup_index;
      }
      /* Identite planifiee de la gare B, toujours sous DECISION_LOG. */
      if ("lead" in planA) fields += " leada=" + planA.lead;
      if ("lead" in planB) fields += " leadb=" + planB.lead;
      if ("station_exit" in planB) fields += " exitb=" + planB.station_exit;
      /* Deux bouts du trace, y compris quand failed=0 (table failure vide).
       * len < 3 : aucun index, ces champs sont absents. */
      if (tiles.len() >= 3) {
        fields += " h0=" + tiles[0]
            + " h1=" + tiles[1]
            + " h2=" + tiles[2]
            + " d01=" + AIMap.DistanceManhattan(tiles[0], tiles[1])
            + " d12=" + AIMap.DistanceManhattan(tiles[1], tiles[2])
            + " t2=" + tiles[last - 2]
            + " t1=" + tiles[last - 1]
            + " t0=" + tiles[last]
            + " d21=" + AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1])
            + " d10=" + AIMap.DistanceManhattan(tiles[last - 1], tiles[last]);
      }
      OpexDecide("RAIL_TRACK_FAIL", fields);
    }
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    local trkOps = budget.end("build_track");
    result.opcodes += trkOps;
    if (result.phaseOps.track < 0) result.phaseOps.track = 0;
    result.phaseOps.track += trkOps;
    result.reason = "TRKFAIL"; return result;
  }

  local depot = OpexBuildDepot(tiles);
  local trkOps = budget.end("build_track");
  result.opcodes += trkOps;
  if (result.phaseOps.track < 0) result.phaseOps.track = 0;
  result.phaseOps.track += trkOps;
  if (depot == null) {
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "DEPFAIL"; return result;
  }

  local primaryCost = costs.GetCosts();
  costs = null;

  local tiles2 = plan.tiles2;
  local planA2 = plan.planA2;
  local planB2 = plan.planB2;
  local depot2 = plan.depot2;
  local want = 1;
  local doubleCost = 0;
  local okD = false;

  if (plan.doubleTrack == 1 && tiles2 != null && planA2 != null && planB2 != null) {
    local dCosts = AIAccounting();
    if (V199_ROBUST_BUILD) {
      OpexV199RebuildForHomeward(tiles, 1, V199_LEVEL_BUDGET_K);
    }
    for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
    for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
    local okA2 = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length,
                                        AIStation.GetStationID(planA.anchor));
    local okB2 = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length,
                                        AIStation.GetStationID(planB.anchor));
    if (okA2 && okB2) {
      local trackOpt2 = { isDouble = true, trainLength = candidate.platformLength, initialBudget = plan.iterationBudget };
      local tFail = OpexBuildTrack(tiles2, plan.structures2, null, trackOpt2);
      local l2 = tiles2.len() - 1;
      local conn2 = tFail == 0 &&
          AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
          AIRail.AreTilesConnected(tiles2[l2 - 2], tiles2[l2 - 1], planB2.station_exit);
      if (conn2) {
        depot2 = OpexBuildDepot(tiles2);
        if (depot2 != null) {
          okD = true;
          doubleCost = dCosts.GetCosts();
          want = candidate.trains > 2 ? 2 : candidate.trains;
        }
      }
    }
    if (!okD) {
      OpexRollback(tiles2, planA2, planB2, depot2, null);
      tiles2 = null; planA2 = null; planB2 = null; depot2 = null;
    }
  }

  local postPathCosts = AIAccounting();
  budget.begin();
  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot,
                                 planA.station_exit, planB.station_exit, 1, candidate.loco,
                                 candidate.wagons, candidate.platformLength, false,
                                 OpexV163Cargo2(candidate), OpexV163Wagons2(candidate));
  if (!trains.failed && trains.built > 0 && want == 2 && depot2 != null) {
    local second = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot2,
                                   planA2.station_exit, planB2.station_exit, 1, candidate.loco,
                                   candidate.wagons, candidate.platformLength, false,
                                   OpexV163Cargo2(candidate), OpexV163Wagons2(candidate));
    if (second.failed || second.built == 0) {
      foreach (vehicle in trains.rollbackVehicles) second.rollbackVehicles.append(vehicle);
      trains = second;
    } else {
      foreach (vehicle in second.vehicles) trains.vehicles.append(vehicle);
      foreach (vehicle in second.rollbackVehicles) trains.rollbackVehicles.append(vehicle);
      trains.built += second.built;
    }
  }
  if (!trains.failed && trains.built > 0) {
    local started = [];
    local startFailed = false;
    foreach (train in trains.vehicles) {
      if (!AIVehicle.StartStopVehicle(train)) {
        startFailed = true;
        trains.failed = true;
        trains.failure = "START";
        trains.error = AIError.GetLastError();
        break;
      }
      started.append(train);
    }
    if (startFailed) {
      foreach (train in started) {
        AIVehicle.StartStopVehicle(train);
      }
    }
  }
  local trnOps = budget.end("build_trains");
  result.opcodes += trnOps;
  if (result.phaseOps.trains < 0) result.phaseOps.trains = 0;
  result.phaseOps.trains += trnOps;
  result.error = trains.error;
  result.diag = trains.diag;
  if (trains.failed || trains.built == 0) {
    if (tiles2 != null) OpexRollback(tiles2, planA2, planB2, depot2, trains.rollbackVehicles);
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.actualCost = primaryCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
    result.reason = (trains.failed && trains.failure == "ORDER") ? "ORDFAIL" : "NOTRAIN";
    return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.trainLength = trains.trainLength;
  result.locoLength = trains.locoLength;
  result.wagonLength = trains.wagonLength;
  result.vehicles = trains.vehicles;
  result.actualCost = primaryCost + doubleCost + postPathCosts.GetCosts();
  /* Les tuiles reellement payees (ponts, tunnels, demolitions, seconde voie) remplacent enfin
   * le devis avant que main.nut n'inscrive les predictions de la ligne. */
  OpexApplyRailActualCapital(candidate, result.actualCost);
  result.capital = candidate.capital;
  result.stationA = planA.station_exit;
  result.stationB = planB.station_exit;
  result.depot = depot;
  /* Le refleet est accessible avec les defauts livres : l'upgrade de seconde
   * voie relit station_exit et lead via OpexSameStationEnd. Ces metadonnees sont
   * donc un contrat de la ligne rail. */
  result.platformA = { anchor = planA.anchor, direction = planA.direction, step = planA.step,
                       length = planA.length, station_exit = planA.station_exit, lead = planA.lead };
  result.platformB = { anchor = planB.anchor, direction = planB.direction, step = planB.step,
                       length = planB.length, station_exit = planB.station_exit, lead = planB.lead };
  if (OpexV307SinkRoomPlatforms(planB) == 2) {
    result.platformB.v307RoomPlatforms <- 2;
    result.platformB.v307RoomStripAnchor <- planB.v307RoomStripAnchor;
    result.platformB.v307RoomSide <- planB.v307RoomSide;
  }
  result.doubleTrack <- (okD ? 1 : 0);
  if (okD && depot2 != null) {
    result.depot2 <- depot2;
    result.stationA2 <- planA2.station_exit;
    result.stationB2 <- planB2.station_exit;
    result.platformA2 <- { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length };
    result.platformB2 <- { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length };
  }
  return result;
}

/* Construit une ligne complete, en reutilisant le plan precalcule s'il est present.
 * Un railPlan non-null, y compris en echec (ABND/DEAD/SITE), est consomme tel quel : la
 * recherche reprenable a deja paye les iterations, les rejouer casserait le denominateur
 * et referait le gel. Le bras historique (railPlan absent) planifie puis construit. */
function OpexBuildLine(catalog, budget, candidate, alternativeRatio, cashReserve, hardCap = 10000)
{
  /* C67.6 rail : cout modele avant devis, pour mesurer l'ecart au facteur fixe 1,70.
   * Journal de decision seulement (defaut 0) : aucun effet sur la partie par defaut. */
  if (DECISION_LOG && !("modelCapital" in candidate)
      && !(("capitalIsActual" in candidate) && candidate.capitalIsActual))
    candidate.modelCapital <- candidate.capital;
  local plan = null;
  if (("railPlan" in candidate) && candidate.railPlan != null) {
    plan = candidate.railPlan;
  } else {
    plan = OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap);
    if (V259_BRIDGE_RENEW > 0) {
      if (!("railPlan" in candidate)) candidate.railPlan <- plan;
      else candidate.railPlan = plan;
    }
  }
  if (!plan.ok) {
    return { ok = false, reason = plan.reason, iterations = plan.iterations, opcodes = plan.opcodes,
             phaseOps = (("phaseOps" in plan) && plan.phaseOps != null)
                 ? { plans = plan.phaseOps.plans, search = plan.phaseOps.search,
                     stations = plan.phaseOps.stations, track = plan.phaseOps.track,
                     trains = plan.phaseOps.trains }
                 : { plans = -1, search = -1, stations = -1, track = -1, trains = -1 },
             siteClear = plan.siteClear, siteCargo = plan.siteCargo, siteCmd = plan.siteCmd,
             siteKind = "N", error = 0, diag = null,
             persistentGeometry = (("persistentGeometry" in plan) && plan.persistentGeometry),
             trains = 0, doubleTrack = 0, doubleSkip = (("doubleSkip" in plan) ? plan.doubleSkip : 0),
             doubleReason = (("doubleReason" in plan) ? plan.doubleReason : "NONE"),
             capacitySignalSegments = 0, capacitySignalsOk = 0, capacitySignalsFail = 0,
             capacitySignalFailures = [],
             budgetInfo = plan.budgetInfo, iterationBudget = plan.iterationBudget,
             segmentedSegments = plan.segmentedSegments,
             segmentedBacktracks = plan.segmentedBacktracks,
             segmentedLocalChoices = plan.segmentedLocalChoices };
  }
  /* V200 : comme l'estimateur d'AAAHogEx, ne doubler que si la caisse paie la ligne double
   * (environ deux fois le devis simple) avec une marge ; sinon voie unique historique. */
  local v200Double = OpexV200WantDouble(candidate, cashReserve);
  /* V198 replaces both station sites with independent templates. */
  if (v200Double && OpexV198Active() && candidate.kind == "freight") {
    return OpexV198ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);
  }
  if (v200Double && OpexV190Active() && candidate.kind == "freight") {
    return OpexV190ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);
  }
  return OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);
}

/* V190 : Verifie l'integrite complete de la voie primaire 1 apres repli.
 * Controle que les deux quais de gare existent et appartiennent a la compagnie,
 * que la voie est connectee de bout en bout et qu'aucun signal a sens unique ne bloque le convoi. */
function OpexV190VerifyPrimaryTrackIntact(tiles1, planA1, planB1, depot1)
{
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);

  if (planA1 == null || planB1 == null) return false;
  for (local i = 0; i < planA1.length; i++) {
    local t = planA1.anchor + planA1.step * i;
    if (!AIRail.IsRailStationTile(t) || AITile.GetOwner(t) != selfCompany) return false;
  }
  for (local i = 0; i < planB1.length; i++) {
    local t = planB1.anchor + planB1.step * i;
    if (!AIRail.IsRailStationTile(t) || AITile.GetOwner(t) != selfCompany) return false;
  }

  if (tiles1 == null || tiles1.len() < 3) return false;
  local last1 = tiles1.len() - 1;
  if (!OpexRailEndConnected(planA1.station_exit, tiles1[1], tiles1[2], "A")) return false;
  if (!OpexRailEndConnected(planB1.station_exit, tiles1[last1 - 1], tiles1[last1 - 2], "B")) return false;

  for (local i = 1; i < last1; i++) {
    local prev = tiles1[i - 1];
    local cur = tiles1[i];
    local next = tiles1[i + 1];
    if (prev == next) continue;
    if (AIMap.DistanceManhattan(prev, cur) > 1) continue;
    if (AIMap.DistanceManhattan(cur, next) > 1) {
      if (AIBridge.IsBridgeTile(cur)) {
        if (AIBridge.GetOtherBridgeEnd(cur) != next) return false;
      } else if (AITunnel.IsTunnelTile(cur)) {
        if (AITunnel.GetOtherTunnelEnd(cur) != next) return false;
      }
    } else {
      if (!AIRail.AreTilesConnected(prev, cur, next)) return false;
    }
  }

  for (local i = 1; i < last1; i++) {
    local t = tiles1[i];
    if (AIRail.IsRailTile(t) && !AIRail.IsRailStationTile(t) && !AIRail.IsRailDepotTile(t)) {
      local sigPrev = AIRail.GetSignalType(t, tiles1[i - 1]);
      local sigNext = AIRail.GetSignalType(t, tiles1[i + 1]);
      if (sigPrev == AIRail.SIGNALTYPE_NORMAL || sigNext == AIRail.SIGNALTYPE_NORMAL) return false;
      if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
        if (sigPrev == AIRail.SIGNALTYPE_PBS_ONEWAY || sigNext == AIRail.SIGNALTYPE_PBS_ONEWAY) return false;
      }
    }
  }

  if (depot1 != null) {
    if (!AIRail.IsRailDepotTile(depot1) || AITile.GetOwner(depot1) != selfCompany) return false;
  }

  return true;
}

/* V190 : Repli securise de la seconde voie.
 * Ne demolit QUE ce qui a ete pose pour la voie 2 (quais 2, tuiles de tiles2, depot 2, convois 2).
 * Ne touche JAMAIS aux tuiles de la voie 1 ni de la gare primaire.
 * Verifie ensuite que la voie 1 est intacte de bout en bout. */
function OpexV190RollbackDoubleTrack(tiles1, planA1, planB1, depot1, tiles2, planA2, planB2, depot2, secondVehicles = null)
{
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);

  if (secondVehicles != null) {
    foreach (v in secondVehicles) {
      if (AIVehicle.IsValidVehicle(v)) AIVehicle.SellVehicle(v);
    }
  }

  local protectedPrimary = {};
  if (tiles1 != null) {
    foreach (t in tiles1) protectedPrimary[t] <- true;
  }
  if (planA1 != null) {
    for (local i = 0; i < planA1.length; i++) protectedPrimary[planA1.anchor + planA1.step * i] <- true;
    if ("station_exit" in planA1) protectedPrimary[planA1.station_exit] <- true;
    if ("lead" in planA1) protectedPrimary[planA1.lead] <- true;
  }
  if (planB1 != null) {
    for (local i = 0; i < planB1.length; i++) protectedPrimary[planB1.anchor + planB1.step * i] <- true;
    if ("station_exit" in planB1) protectedPrimary[planB1.station_exit] <- true;
    if ("lead" in planB1) protectedPrimary[planB1.lead] <- true;
  }
  if (depot1 != null) {
    protectedPrimary[depot1] <- true;
    local df1 = AIRail.GetRailDepotFrontTile(depot1);
    if (AIMap.IsValidTile(df1)) protectedPrimary[df1] <- true;
  }

  if (depot2 != null && AIMap.IsValidTile(depot2) && depot2 != depot1 && !(depot2 in protectedPrimary)) {
    if (AIRail.IsRailDepotTile(depot2) && AITile.GetOwner(depot2) == selfCompany) {
      AITile.DemolishTile(depot2);
    }
  }

  if (planA2 != null) {
    for (local i = 0; i < planA2.length; i++) {
      local t = planA2.anchor + planA2.step * i;
      if (!(t in protectedPrimary) && AIRail.IsRailStationTile(t) && AITile.GetOwner(t) == selfCompany) {
        AIRail.RemoveRailStationTileRectangle(t, t, false);
      }
    }
  }
  if (planB2 != null) {
    for (local i = 0; i < planB2.length; i++) {
      local t = planB2.anchor + planB2.step * i;
      if (!(t in protectedPrimary) && AIRail.IsRailStationTile(t) && AITile.GetOwner(t) == selfCompany) {
        AIRail.RemoveRailStationTileRectangle(t, t, false);
      }
    }
  }

  if (tiles2 != null && tiles2.len() >= 3) {
    for (local i = 1; i < tiles2.len() - 1; i++) {
      local t = tiles2[i];
      if (t in protectedPrimary) continue;
      if (!AIMap.IsValidTile(t)) continue;
      if (AITile.GetOwner(t) != selfCompany) continue;
      if (AIRail.IsRailStationTile(t)) {
        AIRail.RemoveRailStationTileRectangle(t, t, false);
      } else if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t)) {
        AITile.DemolishTile(t);
      }
    }
  }

  if (tiles1 != null && tiles1.len() >= 3) {
    local last1 = tiles1.len() - 1;
    for (local i = 1; i < last1; i++) {
      local t = tiles1[i];
      if (AIRail.IsRailTile(t) && !AIRail.IsRailStationTile(t) && !AIRail.IsRailDepotTile(t)) {
        local sigPrev = AIRail.GetSignalType(t, tiles1[i - 1]);
        local sigNext = AIRail.GetSignalType(t, tiles1[i + 1]);
        if (sigPrev == AIRail.SIGNALTYPE_NORMAL || ("SIGNALTYPE_PBS_ONEWAY" in AIRail && sigPrev == AIRail.SIGNALTYPE_PBS_ONEWAY)) {
          AIRail.RemoveSignal(t, tiles1[i - 1]);
        }
        if (sigNext == AIRail.SIGNALTYPE_NORMAL || ("SIGNALTYPE_PBS_ONEWAY" in AIRail && sigNext == AIRail.SIGNALTYPE_PBS_ONEWAY)) {
          AIRail.RemoveSignal(t, tiles1[i + 1]);
        }
      }
    }
  }

  OpexAir0310InvalidateSiteValidity();

  return OpexV190VerifyPrimaryTrackIntact(tiles1, planA1, planB1, depot1);
}

/* V190 : Construit une ligne fret directement en double voie a sens unique avec 2 trains et boucle PBS.
 * En cas d'impossibilite de la seconde voie, repli propre et transparent en voie unique (1 train). */
function OpexV190ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)
{
  local result = { ok = false, reason = "", iterations = plan.iterations, opcodes = plan.opcodes,
                   phaseOps = { plans = plan.phaseOps.plans, search = plan.phaseOps.search,
                                stations = plan.phaseOps.stations, track = plan.phaseOps.track,
                                trains = plan.phaseOps.trains },
                   error = 0, diag = null, trains = 0, vehicles = [],
                   stationA = null, stationB = null, depot = null,
                   platformA = null, platformB = null, trainLength = 0, wagons = candidate.wagons,
                   platformLength = plan.length, locoLength = 0, wagonLength = 0,
                   wantedPlatformLength = candidate.platformLength, plansA = plan.plansA.len(),
                   plansB = plan.plansB.len(), slopeRelaxed = plan.slopeRelaxed,
                   siteClear = plan.siteClear, siteCargo = plan.siteCargo, siteCmd = plan.siteCmd,
                   siteKind = candidate.kind == "pax" ? "P" : "F",
                   capacitySignalsOk = 0, capacitySignalsFail = 0, capacitySignalSegments = 0, capacitySignalFailures = [],
                   doubleTrack = plan.doubleTrack, doubleSkip = plan.doubleSkip,
                    doubleReason = (("doubleReason" in plan) ? plan.doubleReason : "NONE"),
                   doubleTiles = plan.doubleTiles, doubleDepot = plan.doubleDepot,
                   capital = plan.capital, money = 0, actualCost = 0,
                   budgetInfo = plan.budgetInfo, iterationBudget = plan.iterationBudget,
                   segmentedSegments = plan.segmentedSegments,
                   segmentedBacktracks = plan.segmentedBacktracks,
                   segmentedLocalChoices = plan.segmentedLocalChoices };

  local planA = plan.planA;
  local planB = plan.planB;
  local tiles = plan.tiles;
  local replanGeometry = false;
  if (DECISION_LOG) {
    local crossStart = -1;
    local crossEnd = -1;
    if (tiles != null && tiles.len() >= 2) {
      crossStart = (AIMap.DistanceManhattan(tiles[0], tiles[1]) > 1) ? 1 : 0;
    }
    if (tiles != null && tiles.len() >= 3) {
      local tail = tiles.len() - 1;
      crossEnd = (AIMap.DistanceManhattan(tiles[tail - 2], tiles[tail - 1]) > 1) ? 1 : 0;
    }
    result.startx <- crossStart;
    result.endx <- crossEnd;
  }
  {
    local quoteFailure = {};
    local realCapital = OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure);
    if (realCapital == null && RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_LIVE_REPLAN
        && ("reason" in quoteFailure) && quoteFailure.reason == "STNFAIL") {
      local firstError = ("error" in quoteFailure) ? quoteFailure.error : 0;
      local refresh = OpexRailRefreshExactPlatforms(catalog, candidate, plan);
      if (DECISION_LOG) {
        OpexDecide("RAIL_GEOM_REPLAN", "src=" + candidate.src + " dst=" + candidate.dst
                   + " refreshed=" + (refresh.ok ? 1 : 0) + " reason=" + refresh.reason
                   + " first_err=" + firstError);
      }
      if (refresh.ok) {
        planA = plan.planA;
        planB = plan.planB;
        result.plansA = plan.plansA.len();
        result.plansB = plan.plansB.len();
        quoteFailure = {};
        realCapital = OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure);
        if (DECISION_LOG) {
          OpexDecide("RAIL_GEOM_REPLAN_QUOTE", "src=" + candidate.src + " dst=" + candidate.dst
                     + " ok=" + (realCapital != null ? 1 : 0)
                     + " reason=" + (realCapital == null && ("reason" in quoteFailure)
                                     ? quoteFailure.reason : "OK"));
        }
      } else if (refresh.reason == "exact_interface_missing") {
        replanGeometry = true;
      }
    }
    if (realCapital == null) {
      if (DECISION_LOG) {
        local failTile = ("tile" in quoteFailure) ? quoteFailure.tile : -1;
        local failError = ("error" in quoteFailure) ? quoteFailure.error : 0;
        local failReason = ("reason" in quoteFailure) ? quoteFailure.reason : "UNKNOWN";
        OpexDecide("RAIL_QUOTE_FAIL", "src=" + candidate.src + " dst=" + candidate.dst
                   + " reason=" + failReason + " err=" + failError + " tile=" + failTile
                   + " reuse=" + ((("originServed" in candidate) && candidate.originServed) ? 1 : 0)
                   + " join_end=" + (("joinEnd" in candidate) ? candidate.joinEnd : "-")
                   + " plan_a=" + (planA != null ? planA.anchor : -1)
                   + " plan_b=" + (planB != null ? planB.anchor : -1)
                   + " lead_a=" + (planA != null && ("lead" in planA) ? planA.lead : -1)
                   + " lead_b=" + (planB != null && ("lead" in planB) ? planB.lead : -1));
      }
      result.error = quoteFailure.error;
      result.reason = result.error == AIError.ERR_NOT_ENOUGH_CASH ? "CASH"
          : (replanGeometry ? "REPLAN_GEOM" : quoteFailure.reason);
      result.quoteFailure <- quoteFailure;
      return result;
    }
    if (realCapital > 0) {
      result.capital = realCapital;
      OpexApplyRailActualCapital(candidate, realCapital);
      if ((V307_SINK_ROOM & 2) != 0) OpexV307SinkRoomApplyMaintenance(candidate, planB);
      plan.capital = candidate.capital;
    }
  }

  result.money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = result.capital + cashReserve;
  if (result.money < need) {
    result.reason = "CASH";
    return result;
  }

  if (!OpexRailVehicleSlotAvailable()) {
    result.reason = "NOTRAIN";
    return result;
  }

  local costs = AIAccounting();

  budget.begin();
  OpexAir0310InvalidateSiteValidity();
  for (local i = 0; i < planA.length; i++) {
    AITile.DemolishTile(planA.anchor + planA.step * i);
  }
  if (!("v307Prebuilt" in planB)) {
    for (local i = 0; i < planB.length; i++) {
      AITile.DemolishTile(planB.anchor + planB.step * i);
    }
    OpexV307SinkRoomDemolishExtra(planB);
  }
  local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
  local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
  local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA);
  local okB = ("v307Prebuilt" in planB) ? OpexV307SinkRoomPrebuiltReady(planB)
      : AIRail.BuildRailStation(OpexV307SinkRoomStationAnchor(planB), planB.direction,
                                OpexV307SinkRoomPlatforms(planB), planB.length, stIdB);
  if (!okA || !okB) {
    if (DECISION_LOG) {
      local err = AIError.GetLastError();
      OpexDecide("RAIL_STN_FAIL", "ok_a=" + (okA ? 1 : 0)
          + " ok_b=" + (okB ? 1 : 0)
          + " anchor_a=" + planA.anchor
          + " anchor_b=" + planB.anchor
          + " len_a=" + planA.length
          + " len_b=" + planB.length
          + " err=" + err);
    }
    OpexRollback(null, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    local stnOps = budget.end("build_stations");
    result.opcodes += stnOps;
    if (result.phaseOps.stations < 0) result.phaseOps.stations = 0;
    result.phaseOps.stations += stnOps;
    result.reason = "STNFAIL"; return result;
  }

  local trackFailure = null;
  if (DECISION_LOG || RAIL_GEOMETRY_GUARD) trackFailure = {};
  local trackOpt1 = { isDouble = (plan.doubleTrack == 1), trainLength = candidate.platformLength, initialBudget = plan.iterationBudget };
  local trackFailed = OpexBuildTrack(tiles, plan.structures, trackFailure, trackOpt1);
  local last = tiles.len() - 1;
  local connected = trackFailed == 0 &&
      OpexRailEndConnected(planA.station_exit, tiles[1], tiles[2], "A") &&
      OpexRailEndConnected(planB.station_exit, tiles[last - 1], tiles[last - 2], "B");
  if (!connected) {
    if (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY && trackFailed > 0 &&
        OpexRailTrackFailureIsPersistentGeometry(trackFailure, planA, planB)) {
      result.persistentGeometry <- true;
      result.error = trackFailure.error;
    }
    if (DECISION_LOG) {
      local exitA = -1;
      local exitB = -1;
      if (tiles.len() >= 3) {
        exitA = AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) ? 1 : 0;
        exitB = AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit) ? 1 : 0;
      }
      OpexDecide("RAIL_TRACK_FAIL", "cause=" + (trackFailed > 0 ? "track" : "connect")
                 + " failed=" + trackFailed + " exit_a=" + exitA + " exit_b=" + exitB);
    }
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    local trkOps = budget.end("build_track");
    result.opcodes += trkOps;
    if (result.phaseOps.track < 0) result.phaseOps.track = 0;
    result.phaseOps.track += trkOps;
    result.reason = "TRKFAIL"; return result;
  }

  local tiles2 = plan.tiles2;
  local planA2 = plan.planA2;
  local planB2 = plan.planB2;

  if (V199_ROBUST_BUILD && plan.doubleTrack == 1) {
    local side = 1;
    if (planA2 != null && ("direction" in planA) && ("station_exit" in planA) && ("station_exit" in planA2)) {
      local offA = planA2.station_exit - planA.station_exit;
      local oxA = AIMap.GetTileX(offA);
      local oyA = AIMap.GetTileY(offA);
      local dxA = (planA.direction == 0) ? 0 : 1;
      local dyA = (planA.direction == 0) ? 1 : 0;
      local s = dxA * oyA - dyA * oxA;
      if (s == 1 || s == -1) side = s;
    }
    OpexV199RebuildForHomeward(tiles, side, V199_LEVEL_BUDGET_K);
  }

  local forbiddenDepot1 = {};
  if (plan.doubleTrack == 1 && tiles2 != null) {
    foreach (tile in tiles2) forbiddenDepot1[tile] <- true;
    if (planA2 != null) {
      for (local i = 0; i < planA2.length; i++) forbiddenDepot1[planA2.anchor + planA2.step * i] <- true;
      if ("station_exit" in planA2) forbiddenDepot1[planA2.station_exit] <- true;
      if ("lead" in planA2) forbiddenDepot1[planA2.lead] <- true;
    }
    if (planB2 != null) {
      for (local i = 0; i < planB2.length; i++) forbiddenDepot1[planB2.anchor + planB2.step * i] <- true;
      if ("station_exit" in planB2) forbiddenDepot1[planB2.station_exit] <- true;
      if ("lead" in planB2) forbiddenDepot1[planB2.lead] <- true;
    }
    // Interdire les 4 premieres tuiles a A et a B pour les aiguillages de croisement
    for (local k = 1; k <= 4 && k < tiles.len() - 1; k++) forbiddenDepot1[tiles[k]] <- true;
    for (local k = tiles.len() - 2; k >= tiles.len() - 5 && k >= 1; k--) forbiddenDepot1[tiles[k]] <- true;
  }

  local depot = OpexBuildDepot(tiles, forbiddenDepot1);
  local trkOps = budget.end("build_track");
  result.opcodes += trkOps;
  if (result.phaseOps.track < 0) result.phaseOps.track = 0;
  result.phaseOps.track += trkOps;
  if (depot == null) {
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "DEPFAIL"; return result;
  }

  local primaryCost = costs.GetCosts();
  costs = null;

  local depot2 = null;
  local doubleCost = 0;
  local okD = false;

  local postPathCosts = AIAccounting();
  budget.begin();

  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot,
                                 planA.station_exit, planB.station_exit, 1, candidate.loco,
                                 candidate.wagons, candidate.platformLength, false);
  if (trains.failed || trains.built == 0) {
    local trnOps = budget.end("build_trains");
    result.opcodes += trnOps;
    if (result.phaseOps.trains < 0) result.phaseOps.trains = 0;
    result.phaseOps.trains += trnOps;
    result.error = trains.error;
    result.diag = trains.diag;
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.actualCost = primaryCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
    result.reason = (trains.failed && trains.failure == "ORDER") ? "ORDFAIL" : "NOTRAIN";
    return result;
  }

  if (plan.doubleTrack == 1 && tiles2 != null && planA2 != null && planB2 != null) {
    local dCosts = AIAccounting();
    local stIdA_exist = AIStation.GetStationID(planA.anchor);
    local stIdB_exist = AIStation.GetStationID(planB.anchor);
    for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
    for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
    local okA2 = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length, stIdA_exist);
    local okB2 = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length, stIdB_exist);
    local tFail = -1;
    local conn2 = false;
    local connExitA2 = false;
    local connExitB2 = false;
    local trackFailure2 = {};
    local loopDiag = {};
    local secondRollbackVehicles = null;
    if (okA2 && okB2) {
      local trackOpt2 = { isDouble = true, trainLength = candidate.platformLength, initialBudget = plan.iterationBudget };
      tFail = OpexBuildTrack(tiles2, plan.structures2, trackFailure2, trackOpt2);
      local l2 = tiles2.len() - 1;
      connExitA2 = AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]);
      connExitB2 = AIRail.AreTilesConnected(tiles2[l2 - 2], tiles2[l2 - 1], planB2.station_exit);
      conn2 = (tFail == 0 && connExitA2 && connExitB2);
      if (conn2) {
        local forbiddenD = {};
        foreach (tile in tiles) forbiddenD[tile] <- true;
        forbiddenD[depot] <- true;
        local depotFront = AIRail.GetRailDepotFrontTile(depot);
        if (AIMap.IsValidTile(depotFront)) forbiddenD[depotFront] <- true;
        if (planA != null) {
          for (local i = 0; i < planA.length; i++) forbiddenD[planA.anchor + planA.step * i] <- true;
          if ("station_exit" in planA) forbiddenD[planA.station_exit] <- true;
          if ("lead" in planA) forbiddenD[planA.lead] <- true;
        }
        if (planB != null) {
          for (local i = 0; i < planB.length; i++) forbiddenD[planB.anchor + planB.step * i] <- true;
          if ("station_exit" in planB) forbiddenD[planB.station_exit] <- true;
          if ("lead" in planB) forbiddenD[planB.lead] <- true;
        }
        for (local k = 1; k <= 4 && k < tiles2.len() - 1; k++) forbiddenD[tiles2[k]] <- true;
        for (local k = tiles2.len() - 2; k >= tiles2.len() - 5 && k >= 1; k--) forbiddenD[tiles2[k]] <- true;
        depot2 = OpexBuildDepot(tiles2, forbiddenD);
        local trainDepot = (depot2 != null) ? depot2 : depot;
        local second = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, trainDepot,
                                       planA2.station_exit, planB2.station_exit, 1, candidate.loco,
                                       candidate.wagons, candidate.platformLength, false);
        if (!second.failed && second.built > 0) {
            secondRollbackVehicles = second.rollbackVehicles;
            local loopLine = {
              mode = "rail",
              doubleTrack = 1,
              lineId = candidate.src,
              stationA = planA.station_exit,
              stationB = planB.station_exit,
              stationA2 = planA2.station_exit,
              stationB2 = planB2.station_exit,
              platformA = { anchor = planA.anchor, direction = planA.direction, step = planA.step, length = planA.length, station_exit = planA.station_exit, lead = planA.lead },
              platformB = { anchor = planB.anchor, direction = planB.direction, step = planB.step, length = planB.length, station_exit = planB.station_exit, lead = planB.lead },
              platformA2 = { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length, station_exit = planA2.station_exit, lead = planA2.lead },
              platformB2 = { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length, station_exit = planB2.station_exit, lead = planB2.lead },
              vehicles = [trains.vehicles[0], second.vehicles[0]],
              tiles1 = tiles,
              tiles2 = tiles2,
              diag = loopDiag
            };
            if (OpexConvertDoubleTrackToLoop(loopLine, loopDiag)) {
              foreach (vehicle in second.vehicles) trains.vehicles.append(vehicle);
              foreach (vehicle in second.rollbackVehicles) trains.rollbackVehicles.append(vehicle);
              trains.built += second.built;
              okD = true;
              doubleCost = dCosts.GetCosts();
            }
          }
        }
      }
    if (!okD) {
      local failReason = (!okA2 || !okB2) ? "STN2FAIL" : (tFail != 0 || !conn2 ? "TRK2FAIL" : (depot2 == null ? "DEP2FAIL" : "LOOPFAIL"));
      local failDetail = "NONE";
      if (failReason == "STN2FAIL") {
        failDetail = (!okA2 ? "STN_A2" : "STN_B2");
      } else if (failReason == "TRK2FAIL") {
        if (tFail != 0) {
          local err = ("error" in trackFailure2) ? trackFailure2.error : 0;
          local idxFail = ("index" in trackFailure2) ? trackFailure2.index : -1;
          failDetail = "TRACK_FAIL_idx" + idxFail + "_err" + err;
        } else if (!connExitA2) {
          failDetail = "CONN_EXIT_A2";
        } else {
          failDetail = "CONN_EXIT_B2";
        }
      } else if (failReason == "DEP2FAIL") {
        failDetail = "DEPOT2_BUILD";
      } else if (failReason == "LOOPFAIL") {
        failDetail = ("step" in loopDiag) ? loopDiag.step : "CONVERT_FAIL";
      }

      local primaryIntact = OpexV190RollbackDoubleTrack(tiles, planA, planB, depot,
                                                         tiles2, planA2, planB2, depot2,
                                                         secondRollbackVehicles);
      tiles2 = null; planA2 = null; planB2 = null; depot2 = null;

      if (!primaryIntact) {
        failReason = "PRIMARY_BROKEN";
        result.doubleReason = failReason;
        result.doubleSkip = 4;
        result.doubleStep <- failDetail;
        if (DECISION_LOG) {
          OpexDecide("V190", "action=fallback_single line=" + candidate.src + "->" + candidate.dst + " trains=0 reason=" + failReason + " step=" + failDetail + " skip=4");
        }
        OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
        result.actualCost = primaryCost + doubleCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
        result.reason = "PRIMARY_BROKEN";
        result.ok = false;
        return result;
      }

      result.doubleReason = failReason;
      result.doubleSkip = 4;
      result.doubleStep <- failDetail;
      if (DECISION_LOG) {
        OpexDecide("V190", "action=fallback_single line=" + candidate.src + "->" + candidate.dst + " trains=1 reason=" + failReason + " step=" + failDetail + " skip=4");
      }
    }
  } else {
    local skipVal = (("doubleSkip" in plan) ? plan.doubleSkip : -1);
    local reasonVal = (("doubleReason" in plan) ? plan.doubleReason : "NOPLAN2");
    local stepVal = (("doubleStep" in plan) ? plan.doubleStep : "PLANNING");
    result.doubleReason = reasonVal;
    result.doubleSkip = skipVal;
    result.doubleStep <- stepVal;
    if (DECISION_LOG) {
      OpexDecide("V190", "action=fallback_single line=" + candidate.src + "->" + candidate.dst + " trains=1 reason=" + reasonVal + " step=" + stepVal + " skip=" + skipVal);
    }
  }

  local started = [];
  local startFailed = false;
  foreach (train in trains.vehicles) {
    if (!AIVehicle.StartStopVehicle(train)) {
      startFailed = true;
      trains.failed = true;
      trains.failure = "START";
      trains.error = AIError.GetLastError();
      break;
    }
    started.append(train);
  }
  if (startFailed) {
    foreach (train in started) {
      AIVehicle.StartStopVehicle(train);
    }
    local trnOps = budget.end("build_trains");
    result.opcodes += trnOps;
    if (result.phaseOps.trains < 0) result.phaseOps.trains = 0;
    result.phaseOps.trains += trnOps;
    result.error = trains.error;
    result.diag = trains.diag;
    if (tiles2 != null) OpexRollback(tiles2, planA2, planB2, depot2, trains.rollbackVehicles);
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.actualCost = primaryCost + doubleCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
    result.reason = "STARTFAIL";
    return result;
  }

  local trnOps = budget.end("build_trains");
  result.opcodes += trnOps;
  if (result.phaseOps.trains < 0) result.phaseOps.trains = 0;
  result.phaseOps.trains += trnOps;
  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.trainLength = trains.trainLength;
  result.locoLength = trains.locoLength;
  result.wagonLength = trains.wagonLength;
  result.vehicles = trains.vehicles;
  result.actualCost = primaryCost + doubleCost + postPathCosts.GetCosts();
  OpexApplyRailActualCapital(candidate, result.actualCost);
  result.capital = candidate.capital;
  result.stationA = planA.station_exit;
  result.stationB = planB.station_exit;
  result.depot = depot;
  result.platformA = { anchor = planA.anchor, direction = planA.direction, step = planA.step,
                       length = planA.length, station_exit = planA.station_exit, lead = planA.lead };
  result.platformB = { anchor = planB.anchor, direction = planB.direction, step = planB.step,
                       length = planB.length, station_exit = planB.station_exit, lead = planB.lead };
  if (OpexV307SinkRoomPlatforms(planB) == 2) {
    result.platformB.v307RoomPlatforms <- 2;
    result.platformB.v307RoomStripAnchor <- planB.v307RoomStripAnchor;
    result.platformB.v307RoomSide <- planB.v307RoomSide;
  }
  result.doubleTrack = (okD ? 1 : 0);
  if (okD) {
    result.v181Loop <- true;
    if (depot2 != null) {
      result.depot2 <- depot2;
      result.stationA2 <- planA2.station_exit;
      result.stationB2 <- planB2.station_exit;
      result.platformA2 <- { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length };
      result.platformB2 <- { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length };
    }
    if (DECISION_LOG) {
      OpexDecide("V190", "action=build_double line=" + candidate.src + "->" + candidate.dst + " trains=" + result.trains + " reason=OK");
    }
  }
  return result;
}

/* Prepare la recherche de seconde voie d'une ligne existante, SANS lancer l'A*.
 * ok=false => pas de pathfinder a poser (raison dans .reason). */
function OpexPrepareUpgradeSearch(line, hardCap = 10000)
{
  local prep = { ok = false, reason = "", dualA = null, dualB = null, ignored = null,
                 forbidden = null, iterationBudget = hardCap, planA = null, planB = null,
                 stationIdA = -1, stationIdB = -1 };
  if (line == null || (("doubleTrack" in line) && line.doubleTrack == 1)) {
    prep.reason = "ALREADY_DOUBLE";
    return prep;
  }
  if (!("platformA" in line) || !("platformB" in line) || line.platformA == null || line.platformB == null) {
    prep.reason = "NOPLATFORM";
    return prep;
  }
  local stationIdA = AIStation.GetStationID(line.stationA);
  local stationIdB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationIdA) || !AIStation.IsValidStation(stationIdB)) {
    prep.reason = "NOSTATION";
    return prep;
  }

  local forbidden = {};
  if (("depot" in line) && line.depot != null) {
    forbidden[line.depot] <- true;
    local df = AIRail.GetRailDepotFrontTile(line.depot);
    if (AIMap.IsValidTile(df)) forbidden[df] <- true;
  }
  local planA = line.platformA;
  local planB = line.platformB;
  for (local i = 0; i < planA.length; i++) forbidden[planA.anchor + planA.step * i] <- true;
  for (local i = 0; i < planB.length; i++) forbidden[planB.anchor + planB.step * i] <- true;

  local dualA = [];
  foreach (plan in OpexJoinPlatformPlans(planA, stationIdA)) {
    if (OpexSameStationEnd(plan, planA) && !OpexPlanHitsSet(plan, forbidden)) dualA.append(plan);
  }
  local dualB = [];
  foreach (plan in OpexJoinPlatformPlans(planB, stationIdB)) {
    if (OpexSameStationEnd(plan, planB) && !OpexPlanHitsSet(plan, forbidden)) dualB.append(plan);
  }
  if (dualA.len() == 0 || dualB.len() == 0) {
    prep.reason = "NOSPOT";
    return prep;
  }

  local ignored = [];
  foreach (tile, ignoredVal in forbidden) ignored.append(tile);
  prep.ok = true;
  prep.reason = "OK";
  prep.dualA = dualA;
  prep.dualB = dualB;
  prep.ignored = ignored;
  prep.forbidden = forbidden;
  prep.planA = planA;
  prep.planB = planB;
  prep.stationIdA = stationIdA;
  prep.stationIdB = stationIdB;
  return prep;
}

/* Pose la seconde voie une fois l'A* termine. search.iterations est ignore ici
 * (l'upgrade n'entre pas dans le denominateur du classement des candidats). */
function OpexExecuteUpgradeAfterSearch(catalog, budget, line, cashReserve, search, prep)
{
  local result = { ok = false, reason = "", cost = 0, train = null, depot2 = null,
                   stationA2 = null, stationB2 = null, platformA2 = null, platformB2 = null };
  if (search.path == false || search.path == null) {
    result.reason = "NOPATH";
    return result;
  }
  local tiles2 = OpexResolveSearchTiles(search);
  local structures2 = OpexResolveSearchStructures(search);
  if (tiles2.len() < 3) {
    result.reason = "SHORT";
    return result;
  }
  local planA2 = OpexMatchPlan(prep.dualA, tiles2[0]);
  local planB2 = OpexMatchPlan(prep.dualB, tiles2[tiles2.len() - 1]);
  if (planA2 == null || planB2 == null) {
    result.reason = "NOMATCH";
    return result;
  }
  if (!OpexJoinPathIsDedicated(tiles2)) {
    result.reason = "OVERLAP";
    return result;
  }
  for (local i = 1; i < tiles2.len() - 1; i++) {
    if (tiles2[i] in prep.forbidden) {
      result.reason = "OVERLAP";
      return result;
    }
  }

  local wagon = (line.cargo in catalog.wagonByCargo) ? catalog.wagonByCargo[line.cargo] : null;
  if (wagon == null) { result.reason = "NOWAGON"; return result; }
  local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
  local trackCost = tiles2.len() * catalog.costTrackPerTile + (planA2.length + planB2.length) * catalog.costStation + depotCost;
  local trainCost = line.loco.price + line.wagons * wagon.price + OpexV163WagonsPrice(catalog, line);
  local totalNeeded = trackCost + trainCost + cashReserve;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < totalNeeded) {
    result.reason = "CASH";
    return result;
  }

  local costs = AIAccounting();
  OpexAir0310InvalidateSiteValidity();
  for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
  for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
  local okA = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length, prep.stationIdA);
  local okB = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length, prep.stationIdB);
  local joinedA = AIStation.GetStationID(planA2.anchor) == prep.stationIdA;
  local joinedB = AIStation.GetStationID(planB2.anchor) == prep.stationIdB;
  if (!okA || !okB || !joinedA || !joinedB) {
    OpexRollback(null, planA2, planB2, null, null);
    result.reason = "STATIONFAIL";
    return result;
  }

  local trackFailed = OpexBuildTrack(tiles2, structures2);
  local last = tiles2.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
      AIRail.AreTilesConnected(tiles2[last - 2], tiles2[last - 1], planB2.station_exit);
  if (!connected) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    result.reason = "TRACKFAIL";
    return result;
  }

  local depot2 = OpexBuildDepot(tiles2, prep.forbidden);
  if (depot2 == null) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    result.reason = "DEPOTFAIL";
    return result;
  }

  local signals = OpexPlaceJoinSignals(planA2, planB2, tiles2, depot2);

  local newTrains = OpexBuildTrains(catalog, line.cargo, line.kind, depot2,
                                    planA2.station_exit, planB2.station_exit, 1,
                                    line.loco, line.wagons, line.platformLength, true,
                                    OpexV163Cargo2(line), OpexV163Wagons2(line));
  if (newTrains.failed || newTrains.built == 0) {
    OpexRollback(tiles2, planA2, planB2, depot2, newTrains.rollbackVehicles);
    result.reason = "TRAINFAIL";
    return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.depot2 = depot2;
  result.stationA2 = planA2.station_exit;
  result.stationB2 = planB2.station_exit;
  result.platformA2 = { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length };
  result.platformB2 = { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length };
  result.train = newTrains.vehicles[0];
  result.cost = costs.GetCosts();
  return result;
}

/* Construit un 2e train sur une ligne deja doublee avec depot2 valide. */
function OpexBuildSecondTrain(catalog, line, cashReserve)
{
  local result = { ok = false, reason = "", train = null };
  if (!("depot2" in line) || line.depot2 == null || !AIRail.IsRailDepotTile(line.depot2)) {
    result.reason = "NODEPOT2"; return result;
  }
  local wagon = (line.cargo in catalog.wagonByCargo) ? catalog.wagonByCargo[line.cargo] : null;
  if (wagon == null) { result.reason = "NOWAGON"; return result; }
  local trainCost = line.loco.price + line.wagons * wagon.price + OpexV163WagonsPrice(catalog, line);
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < trainCost + cashReserve) {
    result.reason = "CASH"; return result;
  }
  local stA = (("stationA2" in line) && line.stationA2 != null) ? line.stationA2 : line.stationA;
  local stB = (("stationB2" in line) && line.stationB2 != null) ? line.stationB2 : line.stationB;
  local newTrains = OpexBuildTrains(catalog, line.cargo, line.kind, line.depot2,
                                    stA, stB, 1, line.loco, line.wagons, line.platformLength, true,
                                    OpexV163Cargo2(line), OpexV163Wagons2(line));
  if (newTrains.failed || newTrains.built == 0) {
    OpexRollback(null, null, null, null, newTrains.rollbackVehicles);
    result.reason = "TRAINFAIL"; return result;
  }
  result.ok = true;
  result.reason = "OK";
  result.train = newTrains.vehicles[0];
  return result;
}

/* V181 : Trace les tuiles d'une voie ferree entre la sortie d'une gare et la gare destination. */
function OpexTraceTrackTiles(startStationTile, leadTile, endStationTile)
{
  if (!AIMap.IsValidTile(startStationTile) || !AIMap.IsValidTile(leadTile) ||
      !AIMap.IsValidTile(endStationTile) || !AIRail.IsRailTile(leadTile)) return null;

  local tiles = [startStationTile, leadTile];
  local cur = leadTile;
  local prev = startStationTile;
  local visited = {};
  visited[startStationTile] <- true;
  visited[leadTile] <- true;

  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local offsets = [xStep, -xStep, yStep, -yStep];

  local limit = 2000;
  local steps = 0;
  local endStId = AIStation.GetStationID(endStationTile);

  while (cur != endStationTile && steps < limit) {
    steps++;
    if (AIBridge.IsBridgeTile(cur) && AIMap.DistanceManhattan(prev, cur) == 1) {
      local other = AIBridge.GetOtherBridgeEnd(cur);
      if (other != cur && AIMap.IsValidTile(other)) {
        prev = cur;
        cur = other;
        tiles.append(cur);
        visited[cur] <- true;
        if (cur == endStationTile) break;
      }
    } else if (AITunnel.IsTunnelTile(cur) && AIMap.DistanceManhattan(prev, cur) == 1) {
      local other = AITunnel.GetOtherTunnelEnd(cur);
      if (other != cur && AIMap.IsValidTile(other)) {
        prev = cur;
        cur = other;
        tiles.append(cur);
        visited[cur] <- true;
        if (cur == endStationTile) break;
      }
    }

    local found = null;
    foreach (off in offsets) {
      local neighbor = cur + off;
      if (!AIMap.IsValidTile(neighbor) || !AIRail.IsRailTile(neighbor)) continue;
      if (neighbor == prev) continue;
      if (AIRail.IsRailDepotTile(neighbor)) continue;

      if (AIRail.AreTilesConnected(prev, cur, neighbor)) {
        if (AIRail.IsRailStationTile(neighbor)) {
          if (neighbor != endStationTile && AIStation.GetStationID(neighbor) != endStId) {
            continue;
          }
        }
        found = neighbor;
        break;
      }
    }

    if (found == null) return null;

    prev = cur;
    cur = found;
    tiles.append(cur);
    if (cur in visited) break;
    visited[cur] <- true;
    if (cur == endStationTile || (AIRail.IsRailStationTile(cur) && AIStation.GetStationID(cur) == endStId)) {
      break;
    }
  }

  if (tiles.len() < 3) return null;
  return tiles;
}

/* V181 : Tente de poser un segment de raccord d'aiguillage sur tCur entre tPrev et tNext. */
function OpexV181TryBuildSwitchSegment(tPrev, tCur, tNext, recordList, isSimulation = false)
{
  if (!AIMap.IsValidTile(tPrev) || !AIMap.IsValidTile(tCur) || !AIMap.IsValidTile(tNext)) return false;
  if (AIMap.DistanceManhattan(tPrev, tCur) != 1 || AIMap.DistanceManhattan(tCur, tNext) != 1) return false;
  if (AIBridge.IsBridgeTile(tCur) || AITunnel.IsTunnelTile(tCur)) return false;
  if (AIRail.IsRailStationTile(tCur) || AIRail.IsRailDepotTile(tCur)) return false;

  if (!isSimulation) {
    if (AIRail.GetSignalType(tCur, tPrev) != AIRail.SIGNALTYPE_NONE) {
      AIRail.RemoveSignal(tCur, tPrev);
    }
    if (AIRail.GetSignalType(tCur, tNext) != AIRail.SIGNALTYPE_NONE) {
      AIRail.RemoveSignal(tCur, tNext);
    }
  }

  local ok = AIRail.BuildRail(tPrev, tCur, tNext);
  if (!ok) return false;

  if (!isSimulation) {
    if (!AIRail.AreTilesConnected(tPrev, tCur, tNext)) {
      AIRail.RemoveRail(tPrev, tCur, tNext);
      return false;
    }
    if (recordList != null) {
      recordList.append({ prev = tPrev, cur = tCur, next = tNext });
    }
  }
  return true;
}

/* V181 : Tente de poser un aiguillage complet entre deux voies paralleles. */
function OpexV181TryBuildSwitch(tFromPrev, tFrom, tTo, tToNext, recordList, isSimulation = false)
{
  local dist = AIMap.DistanceManhattan(tFrom, tTo);
  if (dist == 1) {
    local ok1 = OpexV181TryBuildSwitchSegment(tFromPrev, tFrom, tTo, recordList, isSimulation);
    if (!ok1) return false;
    local ok2 = OpexV181TryBuildSwitchSegment(tFrom, tTo, tToNext, recordList, isSimulation);
    if (!ok2) {
      if (!isSimulation && recordList != null && recordList.len() > 0) {
        local lastPlaced = recordList.pop();
        AIRail.RemoveRail(lastPlaced.prev, lastPlaced.cur, lastPlaced.next);
      }
      return false;
    }
    return true;
  } else if (dist == 2) {
    local x1 = AIMap.GetTileX(tFrom);
    local y1 = AIMap.GetTileY(tFrom);
    local x2 = AIMap.GetTileX(tTo);
    local y2 = AIMap.GetTileY(tTo);
    if (abs(x1 - x2) == 1 && abs(y1 - y2) == 1) {
      local candidates = [
        AIMap.GetTileIndex(x1, y2),
        AIMap.GetTileIndex(x2, y1)
      ];
      foreach (mid in candidates) {
        if (!AIMap.IsValidTile(mid)) continue;
        if (AIBridge.IsBridgeTile(mid) || AITunnel.IsTunnelTile(mid)) continue;
        if (AIRail.IsRailStationTile(mid) || AIRail.IsRailDepotTile(mid)) continue;
        if (AITile.GetSlope(mid) != AITile.SLOPE_FLAT) continue;
        local ownerSelf = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
        local canUseMid = AITile.IsBuildable(mid) || (AIRail.IsRailTile(mid) && AITile.GetOwner(mid) == ownerSelf);
        if (!canUseMid) continue;

        local subRecords = [];
        local s1 = OpexV181TryBuildSwitchSegment(tFromPrev, tFrom, mid, subRecords, isSimulation);
        if (!s1) continue;
        local s2 = OpexV181TryBuildSwitchSegment(tFrom, mid, tTo, subRecords, isSimulation);
        if (!s2) {
          if (!isSimulation) {
            foreach (rec in subRecords) AIRail.RemoveRail(rec.prev, rec.cur, rec.next);
          }
          continue;
        }
        local s3 = OpexV181TryBuildSwitchSegment(mid, tTo, tToNext, subRecords, isSimulation);
        if (!s3) {
          if (!isSimulation) {
            foreach (rec in subRecords) AIRail.RemoveRail(rec.prev, rec.cur, rec.next);
          }
          continue;
        }
        if (!isSimulation && recordList != null) {
          foreach (rec in subRecords) recordList.append(rec);
        }
        return true;
      }
    }
  }
  return false;
}

/* V181 : Tente de poser un signal a sens unique (PBS one-way ou block one-way). */
function OpexV181BuildOneWaySignal(tile, front)
{
  if (!AIMap.IsValidTile(tile) || !AIMap.IsValidTile(front)) return -1;
  if (AIMap.DistanceManhattan(tile, front) != 1) return -1;
  if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) return -1;
  if (!AIRail.IsRailTile(tile)) return -1;
  if (AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) return -1;
  if (OpexTileTrackCount(tile) != 1) return -1;

  if (AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_NONE) {
    AIRail.RemoveSignal(tile, front);
  }
  if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
    if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS_ONEWAY)) return 1;
  }
  if ("SIGNALTYPE_NORMAL" in AIRail) {
    if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_NORMAL)) return 1;
  }
  if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS)) return 1;
  return 0;
}

/* V181 : Conversion en boucle a sens unique d'une ligne ferroviaire deja doublee.
 * Pose les aiguillages de croisement devant la gare A et la gare B,
 * pose les signaux a sens unique le long des deux voies et aux entrees de gare,
 * et unifie les ordres partages de tous les trains existants. */
function OpexConvertDoubleTrackToLoop(line, diag = null)
{
  local loopDiag = diag != null ? diag : (("diag" in line) ? line.diag : null);

  if (line == null || !("mode" in line) || line.mode != "rail") {
    if (loopDiag != null) loopDiag.step <- "INVALID_LINE";
    return false;
  }
  if (!("doubleTrack" in line) || line.doubleTrack != 1) {
    if (loopDiag != null) loopDiag.step <- "NOT_DOUBLE";
    return false;
  }
  if (!("stationA" in line) || !("stationB" in line) ||
      !("stationA2" in line) || !("stationB2" in line)) {
    if (loopDiag != null) loopDiag.step <- "NO_STN_KEY";
    return false;
  }
  if (line.stationA == null || line.stationB == null ||
      line.stationA2 == null || line.stationB2 == null) {
    if (loopDiag != null) loopDiag.step <- "NULL_STN";
    return false;
  }

  local stIdA = AIStation.GetStationID(line.stationA);
  local stIdA2 = AIStation.GetStationID(line.stationA2);
  local stIdB = AIStation.GetStationID(line.stationB);
  local stIdB2 = AIStation.GetStationID(line.stationB2);

  if (!AIStation.IsValidStation(stIdA) || !AIStation.IsValidStation(stIdB)) {
    if (loopDiag != null) loopDiag.step <- "INVALID_STN_ID";
    return false;
  }
  if (stIdA != stIdA2 || stIdB != stIdB2) {
    if (loopDiag != null) loopDiag.step <- "STN_ID_MISMATCH";
    return false;
  }

  local leadA1 = OpexC41RailApproachLead(("platformA" in line) ? line.platformA : null, line.stationA);
  local leadB1 = OpexC41RailApproachLead(("platformB" in line) ? line.platformB : null, line.stationB);
  local leadA2 = OpexC41RailApproachLead(("platformA2" in line) ? line.platformA2 : null, line.stationA2);
  local leadB2 = OpexC41RailApproachLead(("platformB2" in line) ? line.platformB2 : null, line.stationB2);

  if (leadA1 == null || leadB1 == null || leadA2 == null || leadB2 == null) {
    if (loopDiag != null) loopDiag.step <- "NO_LEAD";
    return false;
  }

  local tiles1 = (("tiles1" in line) && line.tiles1 != null) ? line.tiles1 : OpexTraceTrackTiles(line.stationA, leadA1, line.stationB);
  local tiles2 = (("tiles2" in line) && line.tiles2 != null) ? line.tiles2 : OpexTraceTrackTiles(line.stationA2, leadA2, line.stationB2);

  if (tiles1 == null || tiles2 == null) {
    if (loopDiag != null) loopDiag.step <- (tiles1 == null ? "TRACE_TILES1_FAIL" : "TRACE_TILES2_FAIL");
    return false;
  }
  if (tiles1.len() < 7 || tiles2.len() < 7) {
    if (loopDiag != null) loopDiag.step <- "TOO_SHORT";
    return false;
  }

  local switchOutA = null;
  local switchInA = null;
  local switchOutB = null;
  local switchInB = null;

  local last1 = tiles1.len() - 1;
  local last2 = tiles2.len() - 1;

  // 1. Recherche et validation des aiguillages en AITestMode
  {
    local testMode = AITestMode();

    // Gare A : switch outbound (Quai 2 -> Voie 1 vers B)
    for (local i2 = 1; i2 <= 6 && i2 < last2 - 2; i2++) {
      for (local i1 = 1; i1 <= 6 && i1 < last1 - 2; i1++) {
        if (OpexV181TryBuildSwitch(tiles2[i2 - 1], tiles2[i2], tiles1[i1], tiles1[i1 + 1], null, true)) {
          switchOutA = { fromIdx = i2, toIdx = i1 };
          break;
        }
      }
      if (switchOutA != null) break;
    }

    // Gare A : switch inbound (Voie 2 venant de B -> Quai 1)
    if (switchOutA != null) {
      for (local i2 = 1; i2 <= 6 && i2 < last2 - 2; i2++) {
        if (i2 == switchOutA.fromIdx) continue;
        for (local i1 = 1; i1 <= 6 && i1 < last1 - 2; i1++) {
          if (i1 == switchOutA.toIdx) continue;
          if (OpexV181TryBuildSwitch(tiles2[i2 + 1], tiles2[i2], tiles1[i1], tiles1[i1 - 1], null, true)) {
            switchInA = { fromIdx = i2, toIdx = i1 };
            break;
          }
        }
        if (switchInA != null) break;
      }
    }

    // Gare B : switch outbound (Quai 1 -> Voie 2 vers A)
    for (local d1 = 1; d1 <= 6; d1++) {
      local i1 = last1 - d1;
      if (i1 <= 1) continue;
      for (local d2 = 1; d2 <= 6; d2++) {
        local i2 = last2 - d2;
        if (i2 <= 1) continue;
        if (OpexV181TryBuildSwitch(tiles1[i1 + 1], tiles1[i1], tiles2[i2], tiles2[i2 - 1], null, true)) {
          switchOutB = { fromIdx = i1, toIdx = i2 };
          break;
        }
      }
      if (switchOutB != null) break;
    }

    // Gare B : switch inbound (Voie 1 venant de A -> Quai 2)
    if (switchOutB != null) {
      for (local d1 = 1; d1 <= 6; d1++) {
        local i1 = last1 - d1;
        if (i1 <= 1 || i1 == switchOutB.fromIdx) continue;
        for (local d2 = 1; d2 <= 6; d2++) {
          local i2 = last2 - d2;
          if (i2 <= 1 || i2 == switchOutB.toIdx) continue;
          if (OpexV181TryBuildSwitch(tiles1[i1 - 1], tiles1[i1], tiles2[i2], tiles2[i2 + 1], null, true)) {
            switchInB = { fromIdx = i1, toIdx = i2 };
            break;
          }
        }
        if (switchInB != null) break;
      }
    }
  }

  if (switchOutA == null || !("fromIdx" in switchOutA) || !("toIdx" in switchOutA) ||
      switchInA == null || !("fromIdx" in switchInA) || !("toIdx" in switchInA) ||
      switchOutB == null || !("fromIdx" in switchOutB) || !("toIdx" in switchOutB) ||
      switchInB == null || !("fromIdx" in switchInB) || !("toIdx" in switchInB)) {
    if (loopDiag != null) {
      if (switchOutA == null || !("fromIdx" in switchOutA) || !("toIdx" in switchOutA)) loopDiag.step <- "NO_SW_OUT_A";
      else if (switchInA == null || !("fromIdx" in switchInA) || !("toIdx" in switchInA)) loopDiag.step <- "NO_SW_IN_A";
      else if (switchOutB == null || !("fromIdx" in switchOutB) || !("toIdx" in switchOutB)) loopDiag.step <- "NO_SW_OUT_B";
      else loopDiag.step <- "NO_SW_IN_B";
    }
    return false;
  }

  // 2. Pose reelle des aiguillages avec rollback en cas d'echec
  local placedTracks = [];
  local placedSignals = [];
  local buildOk = true;

  if (!OpexV181TryBuildSwitch(tiles2[switchOutA.fromIdx - 1], tiles2[switchOutA.fromIdx],
                              tiles1[switchOutA.toIdx], tiles1[switchOutA.toIdx + 1], placedTracks, false)) {
    buildOk = false;
    if (loopDiag != null) loopDiag.step <- "BUILD_SW_OUT_A";
  }
  if (buildOk &&
      !OpexV181TryBuildSwitch(tiles2[switchInA.fromIdx + 1], tiles2[switchInA.fromIdx],
                              tiles1[switchInA.toIdx], tiles1[switchInA.toIdx - 1], placedTracks, false)) {
    buildOk = false;
    if (loopDiag != null) loopDiag.step <- "BUILD_SW_IN_A";
  }
  if (buildOk && !OpexV181TryBuildSwitch(tiles1[switchOutB.fromIdx + 1], tiles1[switchOutB.fromIdx],
                                        tiles2[switchOutB.toIdx], tiles2[switchOutB.toIdx - 1], placedTracks, false)) {
    buildOk = false;
    if (loopDiag != null) loopDiag.step <- "BUILD_SW_OUT_B";
  }
  if (buildOk &&
      !OpexV181TryBuildSwitch(tiles1[switchInB.fromIdx - 1], tiles1[switchInB.fromIdx],
                              tiles2[switchInB.toIdx], tiles2[switchInB.toIdx + 1], placedTracks, false)) {
    buildOk = false;
    if (loopDiag != null) loopDiag.step <- "BUILD_SW_IN_B";
  }

  if (!buildOk) {
    foreach (rec in placedTracks) {
      AIRail.RemoveRail(rec.prev, rec.cur, rec.next);
    }
    return false;
  }

  // 3. Pose des signaux a sens unique le long des voies et entrees de gare
  local maxA1 = switchOutA.toIdx > switchInA.toIdx ? switchOutA.toIdx : switchInA.toIdx;
  local startIdx1 = maxA1 + 1;

  local minB1 = switchOutB.fromIdx < switchInB.fromIdx ? switchOutB.fromIdx : switchInB.fromIdx;
  local endIdx1 = minB1 - 1;

  local maxA2 = switchOutA.fromIdx > switchInA.fromIdx ? switchOutA.fromIdx : switchInA.fromIdx;
  local startIdx2 = maxA2 + 1;

  local minB2 = switchOutB.toIdx < switchInB.toIdx ? switchOutB.toIdx : switchInB.toIdx;
  local endIdx2 = minB2 - 1;

  if (endIdx1 >= startIdx1) {
    OpexV181BuildOneWaySignal(tiles1[endIdx1], tiles1[endIdx1 - 1]);
    placedSignals.append({ tile = tiles1[endIdx1], front = tiles1[endIdx1 - 1] });
    for (local k = startIdx1; k < endIdx1; k += 7) {
      OpexV181BuildOneWaySignal(tiles1[k], tiles1[k - 1]);
      placedSignals.append({ tile = tiles1[k], front = tiles1[k - 1] });
    }
  }

  if (endIdx2 >= startIdx2) {
    OpexV181BuildOneWaySignal(tiles2[startIdx2], tiles2[startIdx2 + 1]);
    placedSignals.append({ tile = tiles2[startIdx2], front = tiles2[startIdx2 + 1] });
    for (local k = endIdx2; k > startIdx2; k -= 7) {
      OpexV181BuildOneWaySignal(tiles2[k], tiles2[k + 1]);
      placedSignals.append({ tile = tiles2[k], front = tiles2[k + 1] });
    }
  }

  // 4. Unification des ordres partages pour tous les trains existants
  local ordersOk = true;
  if (("vehicles" in line) && line.vehicles != null && line.vehicles.len() > 0) {
    local firstTrain = line.vehicles[0];
  if (AIVehicle.IsValidVehicle(firstTrain)) {
    for (local vIdx = 1; vIdx < line.vehicles.len(); vIdx++) {
      local otherTrain = line.vehicles[vIdx];
      if (AIVehicle.IsValidVehicle(otherTrain)) {
        local sharedOk = AIOrder.ShareOrders(otherTrain, firstTrain);
        if (!sharedOk) {
          while (AIOrder.GetOrderCount(otherTrain) > 0) {
            if (!AIOrder.RemoveOrder(otherTrain, 0)) break; // V262 : pas de boucle sans progres
          }
          sharedOk = AIOrder.ShareOrders(otherTrain, firstTrain);
          if (!sharedOk) {
            ordersOk = false;
            break;
          }
        }
      }
    }
  }
  }

  if (!ordersOk) {
    if (loopDiag != null) loopDiag.step <- "SHARE_ORDERS";
    foreach (sig in placedSignals) {
      AIRail.RemoveSignal(sig.tile, sig.front);
    }
    foreach (rec in placedTracks) {
      AIRail.RemoveRail(rec.prev, rec.cur, rec.next);
    }
    return false;
  }

  line.v181Loop <- true;
  if (DECISION_LOG) {
    OpexDecide("RAIL_LOOP", "action=convert line=" + line.lineId + " ok=1");
  }
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "RL|" + (line.lineId % 100) + "|1");
  return true;
}

/* V207 : arrets de bus traversants joints a une gare rail passagers pour etendre son bassin de captage. */
function OpexV207RailBuildJoinedStops(platform, stationId, townId, paxCargo, maxStops)
{
  if (maxStops <= 0 || platform == null) return 0;
  if (!AIStation.IsValidStation(stationId)) {
    if ("anchor" in platform) stationId = AIStation.GetStationID(platform.anchor);
  }
  if (!AIStation.IsValidStation(stationId)) return 0;
  if (!AITown.IsValidTown(townId)) return 0;

  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 4) spread = 12;

  /* Emprise de la gare = platform.length tuiles platform.anchor + platform.step * i */
  local pLen = ("length" in platform) ? platform.length : 1;
  local pStep = ("step" in platform) ? platform.step : 0;
  local pAnchor = platform.anchor;

  local pMinX = AIMap.GetTileX(pAnchor);
  local pMaxX = pMinX;
  local pMinY = AIMap.GetTileY(pAnchor);
  local pMaxY = pMinY;
  for (local i = 1; i < pLen; i++) {
    local t = pAnchor + pStep * i;
    local tx = AIMap.GetTileX(t);
    local ty = AIMap.GetTileY(t);
    if (tx < pMinX) pMinX = tx;
    if (tx > pMaxX) pMaxX = tx;
    if (ty < pMinY) pMinY = ty;
    if (ty > pMaxY) pMaxY = ty;
  }

  /* Boite permise par station_spread autour de l'emprise du quai */
  local minX = pMaxX - spread + 1;
  if (minX < 1) minX = 1;
  local maxX = pMinX + spread - 1;
  if (maxX >= mapX - 1) maxX = mapX - 2;

  local minY = pMaxY - spread + 1;
  if (minY < 1) minY = 1;
  local maxY = pMinY + spread - 1;
  if (maxY >= mapY - 1) maxY = mapY - 2;

  local rayonBus = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local railCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  local townLocation = AITown.GetLocation(townId);

  local dirs = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
    AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)
  ];

  local candidates = [];
  for (local x = minX; x <= maxX; x++) {
    for (local y = minY; y <= maxY; y++) {
      local tile = AIMap.GetTileIndex(x, y);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != townId) continue;
      if (!AIRoad.IsRoadTile(tile)) continue;
      if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile)) continue;

      /* Distance au rectangle du quai strictement superieure au rayon de couverture rail */
      local dx = 0;
      if (x < pMinX) dx = pMinX - x;
      else if (x > pMaxX) dx = x - pMaxX;
      local dy = 0;
      if (y < pMinY) dy = pMinY - y;
      else if (y > pMaxY) dy = y - pMaxY;
      if (dx + dy <= railCoverage) continue;

      local val = AITile.GetCargoProduction(tile, paxCargo, 1, 1, rayonBus);
      if (val <= 0) continue;

      candidates.append({ tile = tile, value = val, dist = AIMap.DistanceManhattan(tile, townLocation) });
    }
  }

  if (candidates.len() == 0) {
    if (DECISION_LOG) {
      OpexDecide("V207_STOPS", "station=" + stationId + " town=" + townId + " built=0 tried=0");
    }
    return 0;
  }

  candidates.sort(function(a, b) {
    if (a.value > b.value) return -1;
    if (a.value < b.value) return 1;
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });

  local builtStops = [];
  local tried = 0;
  foreach (cand in candidates) {
    if (builtStops.len() >= maxStops) break;
    tried++;

    local tooClose = false;
    foreach (prev in builtStops) {
      if (AIMap.DistanceManhattan(cand.tile, prev) <= 2 * rayonBus) {
        tooClose = true;
        break;
      }
    }
    if (tooClose) continue;

    local front = null;
    foreach (dir in dirs) {
      local tryFront = cand.tile + dir;
      if (!AIMap.IsValidTile(tryFront) || !AIRoad.IsRoadTile(tryFront)) continue;
      if (!AIRoad.AreRoadTilesConnected(cand.tile, tryFront)) continue;
      local testOk = false;
      {
        local shield = AIAccounting();
        local test = AITestMode();
        testOk = AIRoad.BuildDriveThroughRoadStation(
            cand.tile, tryFront, AIRoad.ROADVEHTYPE_BUS, stationId);
        test = null;
        shield = null;
      }
      if (testOk) {
        front = tryFront;
        break;
      }
    }
    if (front == null) continue;

    local ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
    if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(townId, 800, 40);
      ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
    }

    if (ok) {
      OpexAir0310InvalidateSiteValidity();
      builtStops.append(cand.tile);
      if (DECISION_LOG) {
        OpexDecide("V207_STOP", "station=" + stationId + " town=" + townId + " tile=" + cand.tile + " val=" + cand.value);
      }
    }
  }

  if (DECISION_LOG) {
    OpexDecide("V207_STOPS", "station=" + stationId + " town=" + townId + " built=" + builtStops.len() + " tried=" + tried);
  }

  return builtStops.len();
}
