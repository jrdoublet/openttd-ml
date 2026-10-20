/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C41.4/C41.5 : l'attribution ne consulte que l'identite deja persistee par la ligne.
 * Elle ne reconstruit pas un voisinage de gares et ne modifie jamais la table retournee. */
function OpexC41PersistedLineForVehicle(lines, vehicle)
{
  return OpexFindLineForVehicle(lines, vehicle);
}
/* Code d'arret compact pour OR. Le panneau contient deja beaucoup de mesures ; un seul caractere
 * garde le nom sous le plafond silencieux de 31 caracteres. */
function OpexAttemptReasonCode(reason)
{
  if (reason == "OK") return "K";
  if (reason == "ABND") return "A";
  if (reason == "DEAD") return "D";
  if (reason == "NOPA") return "P";
  if (reason == "NOPLAN") return "L";
  if (reason == "SITEA") return "B";
  if (reason == "SITEB") return "C";
  if (reason == "SITEAB") return "G";
  if (reason == "ECON") return "F";
  if (reason == "SHORT") return "H";
  if (reason == "NOMATCH") return "M";
  if (reason == "STNFAIL") return "S";
  if (reason == "TRKFAIL") return "T";
  if (reason == "DEPFAIL") return "E";
  if (reason == "SIGFAIL") return "U";
  if (reason == "ORDFAIL") return "R";
  if (reason == "NOTRAIN") return "V";
  if (reason == "REPLAN_GEOM") return "J";
  if (reason == "DEFER") return "W";
  return "X";
}
/* P4 : la memoire d'abandon ne doit retenir que les impossibilites durables.
 * Un constructeur peut constater une caisse insuffisante APRES le garde du
 * portefeuille (prix reel, re-emprunt refuse ou cout devenu plus eleve que le
 * devis). Ce refus est transitoire : le memoriser retire injustement la paire
 * du vivier, dans le batch comme sur le chemin unitaire. */
function OpexBuildFailureIsAbandonable(result)
{
  if (result == null) return false;
  /* Attente de liquidation R19 : ni impossibilite geometrique ni nouvel echec. */
  if (("reason" in result) && result.reason == "RECOVERY") return false;

  if (("reason" in result) && result.reason == "CASH") return false;
  /* Plafond de vehicules : transitoire, des slots peuvent se liberer. */
  if (("reason" in result) && result.reason == "NOSLOT") return false;
  if (("error" in result) && result.error == AIError.ERR_NOT_ENOUGH_CASH) return false;
  return true;
}
/* Le station_id est l'identite de bassin, pas la tuile de quai : deux lignes raccordees ont des
 * sorties differentes mais le meme ID. Un ancien etat sauvegarde sans la liste vehicles retombe
 * prudemment sur la requete par gare ; les nouvelles lignes rail n'utilisent jamais ce repli
 * ambigu.
 *
 * 🔴 EXCEPTION ROUTE (2026-08-29), et c'est une correction, pas une commodite. Mesure, campagne
 * 20 ans graine 42 : trois lignes routieres sur quatre finissaient a vehCount = 0 alors que leur
 * gare gardait une note de 48 a 60 -- et l'une d'elles est repassee de 0 a 1 vehicule d'une annee
 * sur l'autre, ce qu'aucune disparition ne peut expliquer. La liste figee a la construction est
 * donc FAUSSE des qu'un vehicule est remplace : le renouvellement automatique detruit l'ancien
 * identifiant et en cree un neuf, et OpenTTD RECYCLE les identifiants liberes -- une liste figee
 * finit par ne plus rien designer, ou pire par designer le vehicule d'une autre ligne.
 *
 * La raison qui imposait la liste figee cote rail ne s'applique pas ici : un arret routier est
 * toujours pose en STATION_NEW et n'est jamais joint a un autre, donc AIVehicleList_Station rend
 * exactement les vehicules de CETTE ligne. C'est la seule source de verite qui survit au
 * renouvellement. */
/* Un vehicule dessert-il cette gare dans ses ordres ? Sert a distinguer NOS vehicules de ceux
 * d'une ligne voisine quand un StationID est partage. */
function OpexVehicleServesStation(vehicle, stationId)
{
  if (!AIStation.IsValidStation(stationId)) return false;
  local count = AIOrder.GetOrderCount(vehicle);
  for (local i = 0; i < count; i++) {
    if (!AIOrder.IsValidVehicleOrder(vehicle, i)) continue;
    local dest = AIOrder.GetOrderDestination(vehicle, i);
    if (AIStation.GetStationID(dest) == stationId) return true;
  }
  return false;
}
function OpexLineVehicleIds(line, stationId)
{
  if (("mode" in line) && line.mode == "road") {
    /* Le commentaire de _scrapDeadLines jure que la liste vient des vehicules POSES PAR CETTE
     * LIGNE, « PAS une interrogation par gare qui prendrait les convois du voisin sur un
     * StationID partage ». C'etait faux ici, et exactement pour la route : AIVehicleList_Station
     * rend TOUS les vehicules qui desservent la gare, donc ferrailler une ligne morte envoyait au
     * depot et vendait les camions de toutes les lignes co-localisees (docs/taches.md S0 nonies).
     *
     * Les lignes routieres ne portent pas de liste `vehicles` par conception. On filtre donc par
     * les ORDRES : un camion de cette ligne dessert forcement son AUTRE extremite. Un voisin qui
     * ne partage que stationA est ainsi ecarte. Si stationB est inconnue ou invalide, on retombe
     * sur l'ancien comportement plutot que de rendre une liste vide -- ne jamais transformer un
     * defaut de precision en perte de ferraillage. */
    local roadIds = [];
    local other = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
    local filter = AIStation.IsValidStation(other) && other != stationId;
    local roadVehicles = AIVehicleList_Station(stationId);
    for (local v = roadVehicles.Begin(); !roadVehicles.IsEnd(); v = roadVehicles.Next()) {
      if (filter && !OpexVehicleServesStation(v, other)) continue;
      if (("cargo" in line) && line.cargo >= 0 && AIVehicle.GetCapacity(v, line.cargo) <= 0) continue;
      roadIds.append(v);
    }
    return roadIds;
  }
  if ("vehicles" in line) return line.vehicles;
  if (("v233SharedStationId" in line) && ("mode" in line) && line.mode == "rail") {
    local ownIds = [];
    local other = OpexLineStationId(line, "B");
    local atStation = AIVehicleList_Station(stationId);
    for (local v = atStation.Begin(); !atStation.IsEnd(); v = atStation.Next()) {
      if (other < 0 || other == stationId || !OpexVehicleServesStation(v, other)) continue;
      if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL || AIVehicle.GetCapacity(v, line.cargo) <= 0) continue;
      ownIds.append(v);
    }
    return ownIds;
  }
  local ids = [];
  local vehicles = AIVehicleList_Station(stationId);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) ids.append(v);
  return ids;
}
/* Retrouve la ligne proprietaire d'un vehicule quel que soit son mode (rail, route, air, eau),
 * y compris pour la route dont les vehicules ne sont pas tous stockes dans line.vehicles. */
function OpexFindLineForVehicle(lines, vehicle, tile = null)
{
  if (lines == null) return null;
  // 1. Inventaire direct : tableau vehicles, scalaire vehicle, ou scrapVehicles
  foreach (line in lines) {
    if (line == null) continue;
    if (("vehicles" in line) && line.vehicles != null) {
      foreach (known in line.vehicles) {
        if (known == vehicle) return line;
      }
    }
    if (("vehicle" in line) && line.vehicle == vehicle) return line;
    if (("scrapVehicles" in line) && line.scrapVehicles != null) {
      foreach (known in line.scrapVehicles) {
        if (known == vehicle) return line;
      }
    }
  }
  // 2. Si le vehicule est valide, distinction par ordres et stations
  if (AIVehicle.IsValidVehicle(vehicle)) {
    local vType = AIVehicle.GetVehicleType(vehicle);
    local targetMode = (vType == AIVehicle.VT_ROAD) ? "road"
                     : ((vType == AIVehicle.VT_RAIL) ? "rail"
                     : ((vType == AIVehicle.VT_AIR) ? "air" : "water"));
    foreach (line in lines) {
      if (line == null) continue;
      if (("mode" in line) && line.mode != targetMode) continue;
      local stA = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;
      local stB = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
      if (OpexVehicleServesStation(vehicle, stA) && OpexVehicleServesStation(vehicle, stB)) {
        return line;
      }
    }
    // Repli : au moins une station desservie
    foreach (line in lines) {
      if (line == null) continue;
      if (("mode" in line) && line.mode != targetMode) continue;
      local stA = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;
      local stB = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
      if (OpexVehicleServesStation(vehicle, stA) || OpexVehicleServesStation(vehicle, stB)) {
        return line;
      }
    }
  }
  // 3. Repli spatial si une tuile d'evenement est fournie
  if (tile != null && AIMap.IsValidTile(tile)) {
    local bestLine = null;
    local bestDist = 999999;
    foreach (line in lines) {
      if (line == null) continue;
      local stA = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;
      if (AIStation.IsValidStation(stA)) {
        local distA = AIMap.DistanceManhattan(tile, AIStation.GetLocation(stA));
        if (distA < bestDist && distA <= 20) {
          bestDist = distA;
          bestLine = line;
        }
      }
      local stB = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
      if (AIStation.IsValidStation(stB)) {
        local distB = AIMap.DistanceManhattan(tile, AIStation.GetLocation(stB));
        if (distB < bestDist && distB <= 20) {
          bestDist = distB;
          bestLine = line;
        }
      }
    }
    if (bestLine != null) return bestLine;
  }
  return null;
}
/* Le type de vehicule se deduit du mode de la ligne, et d'un seul endroit : _reportLines et
 * _scrapDeadLines le demandaient chacun de leur cote, le second en le codant en dur a VT_RAIL --
 * ce qui aurait laisse une ligne routiere morte rouler pour toujours. */
function OpexMedianInt(values)
{
  local n = values.len();
  if (n == 0) return 0;
  for (local i = 1; i < n; i++) {
    local v = values[i];
    local j = i;
    while (j > 0 && values[j - 1] > v) {
      values[j] = values[j - 1];
      j--;
    }
    values[j] = v;
  }
  return values[n / 2];
}
function OpexLineVehicleType(line)
{
  if (!("mode" in line)) return AIVehicle.VT_RAIL;
  if (line.mode == "air") return AIVehicle.VT_AIR;
  if (line.mode == "water") return AIVehicle.VT_WATER;
  if (line.mode == "road") return AIVehicle.VT_ROAD;
  return AIVehicle.VT_RAIL;
}
function OpexLineStationId(line, end)
{
  local tile = end == "A" ? line.stationA : line.stationB;
  local stationId = AIStation.GetStationID(tile);
  return AIStation.IsValidStation(stationId) ? stationId : -1;
}
function OpexRememberClosest(distance, threshold, closest)
{
  return distance < threshold && (closest < 0 || distance < closest) ? distance : closest;
}
/* Les tuiles candidate.src/dst sont des positions, tandis que les identifiants de ville/industrie
 * restent stables si le plan de gare evolue. Les deux types actuels ont ces identifiants ; le
 * repli sur les tuiles garde la fonction sure pour un futur type de candidat. La cle fret reste
 * orientee (producteur -> accepteur), mais la cle pax normalise les deux villes pour survivre a un
 * changement de l'ordre de catalog.towns entre deux rafraichissements. */
function OpexAbandonedPairKey(candidate)
{

  if (("isSubsidy" in candidate) && candidate.isSubsidy) {
    return "subsidy|" + candidate.subsidyId;
  }
  local src = candidate.src;
  local dst = candidate.dst;
  if (candidate.kind == "pax") {
    /* catalog.nut garde AITown.GetLocation(t), donc GetClosestTown retrouve ici t a distance 0. */
    src = AITile.GetClosestTown(candidate.src);
    dst = AITile.GetClosestTown(candidate.dst);
    if (src > dst) {
      local swap = src;
      src = dst;
      dst = swap;
    }
  } else if (candidate.kind == "freight") {
    src = AIIndustry.GetIndustryID(candidate.src);
    dst = AIIndustry.GetIndustryID(candidate.dst);
    /* G9§1 : Pour du fret vers une ville, GetIndustryID retourne -1 (invalide).
     * La cle devenait freight|cargo|sourceId|-1, partagee par TOUTES les villes du
     * meme producteur/cargo : un seul echec bannissait la famille entiere pendant
     * au moins un an. On utilise dstTown (pose par les generateurs) prefixe "t"
     * pour distinguer ville/industrie sans collision d'identifiants. */
    if (dst < 0 && ("dstTown" in candidate) && candidate.dstTown >= 0) {
      dst = "t" + candidate.dstTown;
    }
    if (src < 0 && ("srcTown" in candidate) && candidate.srcTown >= 0) {
      src = "t" + candidate.srcTown;
    }
  }
  return candidate.kind + "|" + candidate.cargo + "|" + src + "|" + dst;
}
/* V100 : cle d'echec de doublement de voie d'une ligne dans _abandonedPairs (sauvegardee,
 * purgee par _pruneAbandonedPairs au meme delai que les paires de lignes neuves). */
function OpexRailUpgradeRejectKey(lineId)
{
  return "rail_upgrade|" + lineId;
}

/* V294g : cle de lieu pour une extremite de candidat rail ("t" + townId ou "" + industryId). */
function OpexRailCandidatePlaceKey(candidate, end)
{
  if (candidate == null) return null;
  local tile = (end == "A" || end == "src") ? candidate.src : candidate.dst;
  local isPax = ("kind" in candidate) && candidate.kind == "pax";
  if (isPax) {
    local townId = (end == "A" || end == "src")
      ? (("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(tile))
      : (("dstTown" in candidate && candidate.dstTown >= 0) ? candidate.dstTown : AITile.GetClosestTown(tile));
    if (townId < 0) return null;
    return "t" + townId;
  }
  /* Fret : industrie par defaut, repli sur ville prefixee "t" */
  local indId = AIIndustry.GetIndustryID(tile);
  if (indId >= 0) return "" + indId;
  local townId = (end == "A" || end == "src")
    ? (("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(tile))
    : (("dstTown" in candidate && candidate.dstTown >= 0) ? candidate.dstTown : AITile.GetClosestTown(tile));
  if (townId >= 0) return "t" + townId;
  return null;
}

/* V294g : verifie si l'une des extremites d'un candidat rail est memorisee en echec. */
function OpexRailCandidateBannedPlace(candidate, abandonedPlaces)
{
  if (candidate == null || abandonedPlaces == null || abandonedPlaces.len() == 0) return null;
  local keyA = OpexRailCandidatePlaceKey(candidate, "A");
  if (keyA != null && (keyA in abandonedPlaces)) return keyA;
  local keyB = OpexRailCandidatePlaceKey(candidate, "B");
  if (keyB != null && (keyB in abandonedPlaces)) return keyB;
  return null;
}

/* V294g : delai d'expiration selon le motif d'echec (mode 2). */
function OpexV294gReasonCooldown(reason)
{
  if (reason == "SITEA" || reason == "SITEB" || reason == "SITEAB") return V294G_EXPIRY_SITE_DAYS;
  if (reason == "ABND") return V294G_EXPIRY_ABND_DAYS;
  if (reason == "NOPA") return V294G_EXPIRY_NOPA_DAYS;
  if (reason == "STNFAIL") return V294G_EXPIRY_STNFAIL_DAYS;
  return V294G_EXPIRY_DEFAULT_DAYS;
}

/* C33.3 : Enregistre un échec de construction avec horodatage et compteur d'échecs cumulés. */
/* function OpexAI::_markPairAbandoned(key) */
function OpexAI::_markPairAbandoned(key, reason = null)
{
  local now = AIDate.GetCurrentDate();
  local count = (key in this._abandonCounts) ? (this._abandonCounts[key] + 1) : 1;
  this._abandonCounts[key] <- count;
  local cooldown;
  if (V294_RAIL_FAIL_MEMORY >= 2 && reason != null) {
    cooldown = OpexV294gReasonCooldown(reason);
  } else {
    cooldown = ABANDON_COOLDOWN_DAYS * count;
    if (cooldown > 1825) cooldown = 1825;
  }
  local until = now + cooldown;
  this._abandonedPairs[key] <- { date = now, count = count };
  if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;
  if (V294_RAIL_FAIL_MEMORY == 2) {
    this._abandonedPairs[key].reason <- reason;
    this._abandonedPairs[key].cooldown <- cooldown;
    this._abandonedPairs[key].until <- until;
  }
  /* G4§1 : signaler qu'un abandon a eu lieu dans cette passe. _tryBuildProjects lit ce
   * drapeau pour declencher la reelection incrementale C36.1 apres un echec, sans
   * dependre de passDiscards qui est garde par DECISION_LOG (defaut 0). */
  this._hadAbandonsThisPass = true;
  if (DECISION_LOG) {
    OpexDecide("ABANDON_PAIR", "key=" + key + " count=" + count + " cooldown=" + cooldown);
  }
  this._c76BumpLayer("lines", false);
}
/* C33.3 : Purge les paires dont le délai de reprise est écoulé.
 * Délai = ABANDON_COOLDOWN_DAYS * count (plafonné à 5 ans / 1825 jours). */
function OpexAI::_pruneAbandonedPairs(now)
{
  local toDelete = [];
  foreach (key, val in this._abandonedPairs) {
    if (typeof val != "table" || !("date" in val)) continue;
    local cooldown;
    if (V294_RAIL_FAIL_MEMORY >= 2 && ("cooldown" in val)) {
      cooldown = val.cooldown;
    } else {
      local count = ("count" in val) ? val.count : 1;
      cooldown = ABANDON_COOLDOWN_DAYS * count;
      if (cooldown > 1825) cooldown = 1825;
    }
    if ((now - val.date) >= cooldown) {
      toDelete.append(key);
    }
  }
  foreach (k in toDelete) {
    delete this._abandonedPairs[k];
  }
  if (toDelete.len() > 0 && V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;
  if (toDelete.len() > 0 && DECISION_LOG) {
    OpexDecide("ABANDON_PRUNE", "count=" + toDelete.len() + " remaining=" + this._abandonedPairs.len());
  }
  if (V294_RAIL_FAIL_MEMORY > 0) {
    this._pruneAbandonedPlaces(now);
  }
}

/* V294g : mémorise une extrémité en échec de site de gare (SITEA, SITEB, SITEAB). */
function OpexAI::_markPlaceAbandoned(candidate, end, reason)
{
  if (V294_RAIL_FAIL_MEMORY <= 0) return;
  local key = OpexRailCandidatePlaceKey(candidate, end);
  if (key == null) return;
  local now = AIDate.GetCurrentDate();
  local cooldown = (V294_RAIL_FAIL_MEMORY >= 2) ? V294G_EXPIRY_SITE_DAYS : ABANDON_COOLDOWN_DAYS;
  local until = now + cooldown;
  this._abandonedPlaces[key] <- { date = now, reason = reason, cooldown = cooldown, until = until };
  if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;
  this._hadAbandonsThisPass = true;
  if (DECISION_LOG) {
    OpexDecide("V294G", "event=place_ban key=" + key + " reason=" + reason + " until=" + until);
  }
  this._c76BumpLayer("lines", false);
}

/* V294g : purge les lieux dont le délai d'expiration est atteint. */
function OpexAI::_pruneAbandonedPlaces(now)
{
  if (this._abandonedPlaces == null || this._abandonedPlaces.len() == 0) return;
  local toDelete = [];
  foreach (key, val in this._abandonedPlaces) {
    if (typeof val != "table" || !("date" in val)) continue;
    local cooldown = ("cooldown" in val) ? val.cooldown : ABANDON_COOLDOWN_DAYS;
    local until = ("until" in val) ? val.until : (val.date + cooldown);
    if (now >= until) {
      toDelete.append(key);
    }
  }
  foreach (k in toDelete) {
    if (DECISION_LOG) {
      local entry = this._abandonedPlaces[k];
      local rsn = ("reason" in entry) ? entry.reason : "SITE";
      local unt = ("until" in entry) ? entry.until : (entry.date + (("cooldown" in entry) ? entry.cooldown : ABANDON_COOLDOWN_DAYS));
      OpexDecide("V294G", "event=expire key=" + k + " reason=" + rsn + " until=" + unt);
    }
    delete this._abandonedPlaces[k];
  }
  if (toDelete.len() > 0 && V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;
}
/* Precalcule le trace des meilleurs candidats en avance pendant les ticks d'opcodes dormants. */
/* Verifie les separations d'origine et de gare pour une nouvelle ligne rail. */
function OpexAI::_tooClose(candidate)
{
  /* V178 : la ligne rattachee partage volontairement la gare de la ligne existante. */
  local joinLineId = ("joinLineId" in candidate) ? candidate.joinLineId : -1;
  local joinStationId = ("joinStationId" in candidate) ? candidate.joinStationId : -1;
  local isSharedDest = ("shared_dest" in candidate) && candidate.shared_dest == 1;
  /* V264 : l'extremite B est la gare deja posee a l'industrie. V194 gardait la paire
   * sans jointure et _tooClose la rejetait too_close_no_join (MIN_SEPARATION, main.nut).
   * On n'exempte B que si le candidat porte deja le quai a joindre. A reste controlee. */
  local shareEndB = isSharedDest
      || (("convergent_dest" in candidate) && candidate.convergent_dest == 1);
  local entries = [["A", candidate.src], ["B", candidate.dst]];

  local originA = -1;
  local originB = -1;
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    if (joinLineId >= 0 && ("lineId" in line) && line.lineId == joinLineId) continue;
    foreach (lineEnd in ["A", "B"]) {
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      foreach (entry in entries) {
        if (isSharedDest && entry[0] == "B") continue;
        if (shareEndB && entry[0] == "B") continue;
        local d = AIMap.DistanceManhattan(entry[1], originTile);
        if (d >= ORIGIN_SEPARATION) continue;
        if (entry[0] == "A") originA = OpexRememberClosest(d, ORIGIN_SEPARATION, originA);
        else originB = OpexRememberClosest(d, ORIGIN_SEPARATION, originB);
      }
    }
  }
  if (originA >= 0 && originB >= 0) {
    return { hard = (originA < originB ? originA : originB), blocking = -1 };
  }
  local blocking = originA >= 0 ? originA : originB;

  foreach (line in this._lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    if (joinLineId >= 0 && ("lineId" in line) && line.lineId == joinLineId) continue;
    foreach (lineEnd in ["A", "B"]) {
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId < 0) continue;
      if (isSharedDest && stationId == joinStationId) continue;
      local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
      foreach (entry in entries) {
        if (isSharedDest && entry[0] == "B") continue;
        if (shareEndB && entry[0] == "B") continue;
        local d = AIMap.DistanceManhattan(entry[1], stationTile);
        blocking = OpexRememberClosest(d, MIN_SEPARATION, blocking);
      }
    }
  }
  return { hard = -1, blocking = blocking };
}

/* V178 : rattache un candidat fret a une gare rail existante qui accepte son cargo si la destination
 * est a moins de MIN_SEPARATION, tout en exigeant une source neuve. */
function OpexAI::_tryAttachSharedDest(candidate)
{

  if (candidate == null) return false;
  if (!("kind" in candidate) || candidate.kind != "freight") return false;
  if (!("cargo" in candidate) || !AICargo.IsValidCargo(candidate.cargo)) return false;
  if (!("src" in candidate) || !("dst" in candidate)) return false;
  if (("joinPlatform" in candidate) && candidate.joinPlatform != null) return false;

  /* L'extremite source doit rester neuve : aucune origine a moins de ORIGIN_SEPARATION
   * ni gare rail a moins de MIN_SEPARATION. */
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    foreach (lineEnd in ["A", "B"]) {
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      if (AIMap.DistanceManhattan(candidate.src, originTile) < ORIGIN_SEPARATION) return false;
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId >= 0) {
        local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
        if (AIMap.DistanceManhattan(candidate.src, stationTile) < MIN_SEPARATION) return false;
      }
    }
  }

  /* Cherche parmi nos gares rail existantes une gare a moins de MIN_SEPARATION de candidate.dst
   * qui accepte candidate.cargo. */
  local bestMatch = null;
  local bestDist = MIN_SEPARATION;
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    if (!("lineId" in line)) continue;
    foreach (lineEnd in ["A", "B"]) {
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId < 0 || !AIStation.IsValidStation(stationId)) continue;
      local platformKey = lineEnd == "A" ? "platformA" : "platformB";
      if (!(platformKey in line) || line[platformKey] == null) continue;
      local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
      local dStation = AIMap.DistanceManhattan(candidate.dst, stationTile);
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      local dOrigin = AIMap.DistanceManhattan(candidate.dst, originTile);
      if (dStation >= MIN_SEPARATION && dOrigin >= ORIGIN_SEPARATION) continue;

      local accepts = false;
      if (("cargo" in line) && line.cargo == candidate.cargo) {
        accepts = true;
      } else {
        local accepting = AICargoList_StationAccepting(stationId);
        if (accepting.HasItem(candidate.cargo)) accepts = true;
      }
      if (!accepts) continue;

      if (dStation < bestDist) {
        bestDist = dStation;
        bestMatch = {
          line = line,
          lineEnd = lineEnd,
          stationId = stationId,
          platform = line[platformKey]
        };
      }
    }
  }

  if (bestMatch == null) return false;

  candidate.joinPlatform <- bestMatch.platform;
  candidate.joinStationId <- bestMatch.stationId;
  candidate.joinLineId <- bestMatch.line.lineId;
  candidate.joinEnd <- "B";
  candidate.originServed <- true;
  candidate.shared_dest <- 1;
  return true;
}
function OpexAI::_findLineById(lineId)
{
  foreach (line in this._lines) {
    if (("lineId" in line) && line.lineId == lineId) return line;
  }
  return null;
}
