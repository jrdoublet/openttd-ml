/* Extrait adapte de MinchinWeb's MetaLibrary v.11 (2025-09-30), Copyright (c) 2011-15, 2025 by
 * W. Minchin (https://github.com/MinchinWeb/openttd-metalibrary). Licence permissive maison
 * (ai/library/MinchinWeb_s_MetaLibrary-11/license.txt) : usage, copie, modification autorises,
 * a condition de conserver cet avis. Vendorise et adapte le 2026-09-09 pour OpexAI --
 * voir docs/taches.md et AGENTS.md, section "Bibliotheques tierces vendorisees".
 *
 * Ne copie QUE ce qui est reellement utilise par builder_water.nut, verifie fonction par
 * fonction contre le fichier source avant de coller quoi que ce soit :
 *   - _MinchinWeb_Lakes_ (Lakes.nut) : connectivite maritime memorisee entre bassins deja
 *     explores. Preseed()/_AddGridPoints() NON copiees (dependent de _MinchinWeb_DLS_, jamais
 *     appelees ici -- AddPoint() decouvre les bassins a la demande, pas besoin de pre-semer).
 *     Tous les appels _MinchinWeb_Log_.Note()/.Sign() du fichier source sont retires : ce sont
 *     des logs de debogage de la bibliotheque d'origine, sans effet sur le resultat (verifie :
 *     aucune valeur de retour de Log.Note/.Sign n'est utilisee), et ca evite de copier Log.nut.
 *   - _MinchinWeb_Marine_ (Marine.nut) : seulement DistanceShip, GetDockFrontTiles,
 *     NearestDepot -- PAS GetPossibleDockTiles (reservee aux industries, AIIndustry.* partout,
 *     inutilisable pour une gare passagers autour d'une ville), PAS RateShips2/3 (dependent de
 *     _MinchinWeb_Engine_, remplacees par OpexWaterEconomics), PAS BuildBuoy (SpiralWalker +
 *     WBC, hors perimetre v1 sans bouees), et PAS BuildDepot -- verifie le 2026-09-09 en lisant
 *     son corps reel (pas seulement sa signature) : elle depend de _MinchinWeb_WBC_, donc de
 *     graph.aystar v6, la meme dependance manquante que ShipPathfinder. OpexWaterFindDepot
 *     (builder_water.nut) reste donc la seule methode de construction de depot.
 *   - _MinchinWeb_Array_ : seulement les fonctions reellement appelees par le code ci-dessus
 *     (RemoveDuplicates, Compare1D, ContainedIn1D, Append, RemoveValueAt, ToAIList). Les
 *     fonctions d'affichage (ToString1D, ToStringTiles1D/2D) ne servaient qu'aux logs retires,
 *     donc pas copiees.
 *   - _MinchinWeb_C_.Infinity() et _MinchinWeb_Extras_.MinDistance() : deux utilitaires d'une
 *     ligne chacun, copies tels quels.
 *
 * Fibonacci_Heap (Queue.FibonacciHeap-3, GPLv2, vendorise a part dans ai/library/) est importe
 * via le mecanisme NoAI standard -- chaine confirmee par deux usages independants deja presents
 * dans ce depot : ai/AdmiralAI/main.nut:22 et Lakes.nut:98 lui-meme (import("queue.fibonacci_heap",
 * ..., 3)). L'import de MinchinWeb's MetaLibrary elle-meme (import("util.minchinweb", ...)) n'est
 * PAS tente : sa chaine exacte n'est confirmee nulle part dans ce depot, d'ou la copie de source
 * plutot qu'un import live -- coherent avec la decision deja prise pour SuperLib/MinchinWeb
 * (mismatch de GetAPIVersion, voir AGENTS.md).
 */

/* Slot de table racine, PAS un `local` de fichier : une methode de classe (le constructeur de
 * _MinchinWeb_Lakes_ ci-dessous) doit pouvoir le lire, et ce depot a deja verifie empiriquement
 * a deux reprises qu'une closure imbriquee ne capture jamais une `local` englobante dans cet
 * environnement (voir ::REASON_CODES dans ai/TrainLineAI/main.nut, et AGENTS.md). */
::_WaterHeapClass <- import("queue.fibonacci_heap", "FibonacciHeap", 3);

/* == Constants (Constants.nut, un seul utilitaire necessaire) ============================= */

class _MinchinWeb_C_ {
  function Infinity() { return 10000; }
}

/* == Extras (Extras.nut, un seul utilitaire necessaire) ==================================== */

class _MinchinWeb_Extras_ {
  function MinDistance(TileID, TargetArray);
}
function _MinchinWeb_Extras_::MinDistance(TileID, TargetArray)
{
  local MinDist = _MinchinWeb_C_.Infinity();
  foreach (Target in TargetArray) {
    MinDist = min(MinDist, AITile.GetDistanceManhattanToTile(TileID, Target));
  }
  return MinDist;
}

/* == Array (Array.nut, seulement les fonctions appelees par Lakes/Marine/Station ci-dessous) */

class _MinchinWeb_Array_ {
  function RemoveDuplicates(Array);
  function Compare1D(InArray1D, TestArray1D);
  function ContainedIn1D(InArray, SearchValue);
  function Append(Array1, Array2);
  function RemoveValueAt(InArray, Index);
  function ToAIList(Array);
}
function _MinchinWeb_Array_::RemoveDuplicates(Array)
{
  local ReturnArray = Array;
  for (local i = 0; i < ReturnArray.len(); i++) {
    for (local j = i + 1; j < ReturnArray.len(); j++) {
      if (ReturnArray[i] == ReturnArray[j]) {
        ReturnArray = _MinchinWeb_Array_.RemoveValueAt(ReturnArray, j);
        j--;
      }
    }
  }
  return ReturnArray;
}
function _MinchinWeb_Array_::Compare1D(InArray1D, TestArray1D)
{
  if (InArray1D.len() != TestArray1D.len()) return false;
  for (local i = 0; i < InArray1D.len(); i++) {
    if (InArray1D[i] != TestArray1D[i]) return false;
  }
  return true;
}
function _MinchinWeb_Array_::ContainedIn1D(InArray, SearchValue)
{
  if (InArray == null) return null;
  for (local i = 0; i < InArray.len(); i++) {
    if (InArray[i] == SearchValue) return true;
  }
  return false;
}
function _MinchinWeb_Array_::Append(Array1, Array2)
{
  local ReturnArray = [];
  for (local i = 0; i < Array1.len(); i++) ReturnArray.push(Array1[i]);
  for (local i = 0; i < Array2.len(); i++) ReturnArray.push(Array2[i]);
  return ReturnArray;
}
function _MinchinWeb_Array_::RemoveValueAt(InArray, Index)
{
  local i = 0;
  local Return = [];
  for (i; i < Index; i++) Return.push(InArray[i]);
  i++;
  for (i; i < InArray.len(); i++) Return.push(InArray[i]);
  return Return;
}
function _MinchinWeb_Array_::ToAIList(Array)
{
  local list = AIList();
  foreach (item in Array) list.AddItem(item, 0);
  return list;
}

/* == Lakes (Lakes.nut) : connectivite maritime memorisee entre bassins deja explores ======= */

class _MinchinWeb_Lakes_
{
  _heap_class = null;

  _map = null;
  _connections = null;
  _areas = null;
  _open_neighbours = null;
  _group_tiles = null;
  _AGroup = null;
  _BGroup = null;
  _A = null;
  _B = null;
  _running = null;
  _lastIterationsUsed = null; /* diagnostic : combien d'iterations le dernier FindPath a
                                 * reellement consomme avant de conclure -- sert a calibrer
                                 * WATER_LAKES_ITERATIONS sur mesure, pas au juge. */

  constructor()
  {
    this._heap_class = ::_WaterHeapClass;
    this._map = AIList();
    for (local i = 0; i < AIMap.GetMapSize(); i++) {
      this._map.AddItem(i, -2);
    }
    this._connections = array(0);
    this._areas = array(0);
    this._open_neighbours = array(0);
    this._group_tiles = array(0);
    this._running = false;
  }

  function InitializePath(sources, goals)
  {
    this._AGroup = array(0);
    this._BGroup = array(0);
    this._A = sources;
    this._B = goals;

    foreach (node in sources) this._AGroup.push(this.AddPoint(node));
    foreach (node in goals) this._BGroup.push(this.AddPoint(node));

    this._AGroup = _MinchinWeb_Array_.RemoveDuplicates(this._AGroup);
    this._BGroup = _MinchinWeb_Array_.RemoveDuplicates(this._BGroup);
    this._running = true;
  }

  /* iterations : > 0 borne le nombre de tours d'expansion (pas de -1 infini ici -- ce projet
   * borne toujours ses recherches, voir HARD_ITERATION_CAP pour le rail). Retourne true
   * (connecte), null (aucun chemin possible, un cote est epuise) ou false (budget d'iterations
   * consomme sans conclusion -- appelant peut retenter avec un budget plus grand ou abandonner
   * la paire, comme pour tout PATHLIM du projet). */
  function FindPath(iterations);

  function AddPoint(myTileID);
  function _AllGroups(StartGroupArray);
  function GetPathLength();
  function _AddNeighbour(NextTile);
}

function _MinchinWeb_Lakes_::FindPath(iterations)
{
  for (local i = 0; i < iterations; i++) {
    if (_MinchinWeb_Array_.Compare1D(this._AGroup, [-1]) || _MinchinWeb_Array_.Compare1D(this._BGroup, [-1])) {
      this._lastIterationsUsed = i + 1;
      this._running = false;
      return null;
    }

    local AAllGroups = this._AllGroups(this._AGroup);
    foreach (Group in AAllGroups) {
      if (_MinchinWeb_Array_.ContainedIn1D(this._BGroup, Group)) {
        this._lastIterationsUsed = i + 1;
        this._running = false;
        return true;
      }
    }

    local ANeighbours = array(0);
    local AEdge = array(0);
    local BAllGroups = array(0);
    AAllGroups = this._AllGroups(this._AGroup);
    BAllGroups = this._AllGroups(this._BGroup);

    foreach (Group in AAllGroups) {
      ANeighbours = _MinchinWeb_Array_.Append(ANeighbours, this._open_neighbours[Group]);
    }
    foreach (neighbour in ANeighbours) AEdge.append(neighbour[0]);
    AEdge = _MinchinWeb_Array_.RemoveDuplicates(AEdge);

    if (ANeighbours.len() > 0) {
      local BTileList = AIList();
      foreach (group in BAllGroups) BTileList.AddList(this._group_tiles[group]);
      local AEdgeHeap = this._heap_class();
      foreach (edge in AEdge) {
        AEdgeHeap.Insert(edge, _MinchinWeb_Extras_.MinDistance(edge, BTileList));
      }
      for (local j = 0; j < 12; j++) {
        if (AEdgeHeap.Count() > 0) {
          local NextNeighbour = AEdgeHeap.Pop();
          local AddedNeighbours = this._AddNeighbour(NextNeighbour);
          foreach (Tile in AddedNeighbours) {
            if (Tile != null) AEdgeHeap.Insert(Tile, _MinchinWeb_Extras_.MinDistance(Tile, BTileList));
          }
        }
      }
    } else {
      this._lastIterationsUsed = i + 1;
      this._running = false;
      return null;
    }

    local BNeighbours = array(0);
    local BEdge = array(0);
    AAllGroups = this._AllGroups(this._AGroup);
    BAllGroups = this._AllGroups(this._BGroup);

    foreach (Group in BAllGroups) {
      if (_MinchinWeb_Array_.ContainedIn1D(this._AGroup, Group)) {
        this._lastIterationsUsed = i + 1;
        this._running = false;
        return true;
      }
    }

    foreach (Group in BAllGroups) {
      BNeighbours = _MinchinWeb_Array_.Append(BNeighbours, this._open_neighbours[Group]);
    }
    foreach (neighbour in BNeighbours) BEdge.append(neighbour[0]);
    BEdge = _MinchinWeb_Array_.RemoveDuplicates(BEdge);

    if (BNeighbours.len() > 0) {
      local ATileList = AIList();
      foreach (group in AAllGroups) ATileList.AddList(this._group_tiles[group]);
      local BEdgeHeap = this._heap_class();
      foreach (edge in BEdge) {
        BEdgeHeap.Insert(edge, _MinchinWeb_Extras_.MinDistance(edge, ATileList));
      }
      for (local j = 0; j < 12; j++) {
        if (BEdgeHeap.Count() > 0) {
          local NextNeighbour = BEdgeHeap.Pop();
          local AddedNeighbours = this._AddNeighbour(NextNeighbour);
          foreach (Tile in AddedNeighbours) {
            if (Tile != null) BEdgeHeap.Insert(Tile, _MinchinWeb_Extras_.MinDistance(Tile, ATileList));
          }
        }
      }
    } else {
      this._lastIterationsUsed = i + 1;
      this._running = false;
      return null;
    }
  }
  /* budget d'iterations consomme, toujours en cours */
  this._lastIterationsUsed = iterations;
  return false;
}

function _MinchinWeb_Lakes_::GetPathLength()
{
  /* Distance MANHATTAN, pas une distance navigable -- voir l'avertissement en tete de fichier
   * et le point d'usage dans builder_water.nut (distance tarifaire, pas le temps de trajet). */
  local BList = _MinchinWeb_Array_.ToAIList(this._B);
  BList.Valuate(_MinchinWeb_Extras_.MinDistance, this._A);
  return BList.GetValue(BList.Begin());
}

function _MinchinWeb_Lakes_::AddPoint(myTileID)
{
  switch (this._map.GetValue(myTileID)) {
    case -2:
      if (AITile.IsWaterTile(myTileID) == true) {
        local myArea = this._areas.len();
        this._areas.append(myTileID);
        this._open_neighbours.append([]);
        this._connections.append([]);
        this._map.SetValue(myTileID, myArea);
        this._group_tiles.append(AIList());
        this._group_tiles[myArea].AddItem(myTileID, myTileID);

        local offsets = [AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
                          AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0)];

        foreach (offset in offsets) {
          local next_tile = myTileID + offset;
          /* Garde ajoutee (absente de la source d'origine) : AIMarine.AreWaterTilesConnected
           * est suppose sans risque sur une tuile hors carte (convention NoAI standard,
           * renvoie false), mais on evite meme l'appel par coherence avec le reste du projet
           * (OpexWaterInMap verifie toujours les bords avant d'utiliser une tuile calculee). */
          if (!AIMap.IsValidTile(next_tile)) continue;
          if (AIMarine.AreWaterTilesConnected(myTileID, next_tile)) {
            if (this._map.GetValue(next_tile) == -2) {
              this._open_neighbours[myArea].append([myTileID, next_tile]);
            } else if (this._map.GetValue(next_tile) == -1) {
              this._map.SetValue(next_tile, -2);
              this._open_neighbours[myArea].append([myTileID, next_tile]);
            } else {
              local ConnectedArea = this._map.GetValue(next_tile);
              this._connections[myArea].append(ConnectedArea);
              this._connections[ConnectedArea].append(myArea);

              local AllConnectedAreas = this._AllGroups([ConnectedArea]);
              foreach (ThisArea in AllConnectedAreas) {
                for (local i = 0; i < this._open_neighbours[ThisArea].len(); i++) {
                  if (this._open_neighbours[ThisArea][i][1] == myTileID) {
                    this._open_neighbours[ThisArea] = _MinchinWeb_Array_.RemoveValueAt(this._open_neighbours[ThisArea], i);
                    i--;
                  }
                }
              }
            }
          }
        }
        return myArea;
      } else {
        this._map.SetValue(myTileID, -1);
        return -1;
      }
    case -1:
      return -1;
    default:
      return this._map.GetValue(myTileID);
  }
}

function _MinchinWeb_Lakes_::_AllGroups(StartGroupArray)
{
  local StartIndex = 0;
  local ReturnGroup = StartGroupArray;
  local NextStartIndex = 0;
  local MoreAdded = true;

  do {
    MoreAdded = false;
    NextStartIndex = ReturnGroup.len();
    for (local i = StartIndex; i < NextStartIndex; i++) {
      if ((ReturnGroup[i] >= 0) && (this._connections[ReturnGroup[i]].len() > 0)) {
        ReturnGroup = _MinchinWeb_Array_.Append(ReturnGroup, this._connections[ReturnGroup[i]]);
        ReturnGroup = _MinchinWeb_Array_.RemoveDuplicates(ReturnGroup);
        MoreAdded = true;
      }
    }
    StartIndex = NextStartIndex;
  } while (MoreAdded == true);

  return ReturnGroup;
}

function _MinchinWeb_Lakes_::_AddNeighbour(NextTile)
{
  local ReturnTiles = array(0);
  local OnwardTiles = array(0);
  for (local i = 0; i < this._open_neighbours.len(); i++) {
    for (local j = 0; j < this._open_neighbours[i].len(); j++) {
      if (this._open_neighbours[i][j][0] == NextTile) {
        OnwardTiles.append(this._open_neighbours[i][j][1]);
        this._open_neighbours[i] = _MinchinWeb_Array_.RemoveValueAt(this._open_neighbours[i], j);
        j--;
      }
    }
  }
  OnwardTiles = _MinchinWeb_Array_.RemoveDuplicates(OnwardTiles);
  local ConnectedGroups = this._AllGroups([this._map[NextTile]]);
  for (local i = 0; i < OnwardTiles.len(); i++) {
    if (this._map[OnwardTiles[i]] != -2) {
      if (_MinchinWeb_Array_.ContainedIn1D(ConnectedGroups, this._map[OnwardTiles[i]])) {
        OnwardTiles = _MinchinWeb_Array_.RemoveValueAt(OnwardTiles, i);
        i--;
      }
    }
  }

  if (OnwardTiles.len() == 0) {
    return [null];
  } else {
    local FromGroup = this._map.GetValue(NextTile);
    local offsets = [AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
                      AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0)];

    foreach (OnwardTile in OnwardTiles) {
      if (AIMarine.AreWaterTilesConnected(NextTile, OnwardTile)) {
        this._map.SetValue(OnwardTile, FromGroup);
        this._group_tiles[FromGroup].AddItem(OnwardTile, OnwardTile);
        ReturnTiles.append(OnwardTile);
        foreach (offset in offsets) {
          local next_tile = OnwardTile + offset;
          if (!AIMap.IsValidTile(next_tile)) continue;
          if (AIMarine.AreWaterTilesConnected(OnwardTile, next_tile) && (this._map.GetValue(next_tile) != this._map.GetValue(OnwardTile))) {
            this._open_neighbours[FromGroup].append([OnwardTile, next_tile]);
          }
        }
      }

      for (local i = 0; i < this._open_neighbours.len(); i++) {
        for (local j = 0; j < this._open_neighbours[i].len(); j++) {
          if (this._open_neighbours[i][j][1] == OnwardTile) {
            local ActiveFromGroup = this._map.GetValue(this._open_neighbours[i][j][0]);
            this._connections[FromGroup].append(ActiveFromGroup);
            this._connections[ActiveFromGroup].append(FromGroup);
            this._open_neighbours[i] = _MinchinWeb_Array_.RemoveValueAt(this._open_neighbours[i], j);
            j--;
            this._connections[ActiveFromGroup] = _MinchinWeb_Array_.RemoveDuplicates(this._connections[ActiveFromGroup]);
            this._connections[FromGroup] = _MinchinWeb_Array_.RemoveDuplicates(this._connections[FromGroup]);
          }
        }
      }
    }
  }
  return ReturnTiles;
}

/* == Marine (Marine.nut) : seulement 3 fonctions sans dependance sur Engine/SpiralWalker/WBC == */

class _MinchinWeb_Marine_
{
  function DistanceShip(TileA, TileB);
  function GetDockFrontTiles(Tile);
  function NearestDepot(TileID);
}

/* Approximation de distance navigable en mer ouverte (45 degres puis fin cardinale) --
 * PAS un substitut a une vraie mesure de distance navigable sur une cote detouree, voir le
 * commentaire d'usage dans builder_water.nut. */
function _MinchinWeb_Marine_::DistanceShip(TileA, TileB)
{
  return ((AIMap.DistanceManhattan(TileA, TileB) - AIMap.DistanceMax(TileA, TileB)) * 0.4 + AIMap.DistanceMax(TileA, TileB)).tointeger();
}

/* Tuile(s) d'eau "front" d'une tuile de quai (terre ou eau), en derivant la bonne direction
 * depuis la pente reelle (AITile.GetSlope) -- remplace le scan aveugle des 4 cardinaux de
 * OpexWaterFindDockAccess par un calcul correct de la pente cotiere. */
function _MinchinWeb_Marine_::GetDockFrontTiles(Tile)
{
  local ReturnTiles = [];
  local offset = AIMap.GetTileIndex(0, 0);
  local DockEnd = null;
  local offsets = [AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
                    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0)];

  if (!AIMap.IsValidTile(Tile)) return ReturnTiles;

  if (AITile.IsWaterTile(Tile)) {
    DockEnd = Tile;
  } else {
    switch (AITile.GetSlope(Tile)) {
      case 0: offset = AIMap.GetTileIndex(0, 0); break;
      case 3: offset = AIMap.GetTileIndex(-1, 0); break;
      case 6: offset = AIMap.GetTileIndex(0, -1); break;
      case 9: offset = AIMap.GetTileIndex(0, 1); break;
      case 12: offset = AIMap.GetTileIndex(1, 0); break;
    }
    DockEnd = Tile + offset;
  }

  if (DockEnd != null && AIMap.IsValidTile(DockEnd)) {
    foreach (off in offsets) {
      local next_tile = DockEnd + off;
      if (AIMap.IsValidTile(next_tile) && AITile.IsWaterTile(next_tile)) {
        ReturnTiles.push(next_tile);
      }
    }
  }
  return ReturnTiles;
}

/* _MinchinWeb_Marine_::BuildDepot n'est PAS copiee ici : verification faite le 2026-09-09 en
 * lisant son corps reel (Marine.nut:384-490, pas seulement sa signature) -- elle depend de
 * _MinchinWeb_WBC_ (Waterbody Check) pour verifier la connexion au depot existant/candidat,
 * donc de graph.aystar v6, la meme dependance manquante que ShipPathfinder (voir AGENTS.md).
 * Premiere version de ce fichier affirmait a tort qu'elle etait sans dependance et en proposait
 * une reimplementation maison faussement presentee comme une copie -- corrige avant tout usage.
 * OpexWaterFindDepot (builder_water.nut) reste donc la methode de construction de depot,
 * inchangee. */

function _MinchinWeb_Marine_::NearestDepot(TileID)
{
  local AllDepots = AIDepotList(AITile.TRANSPORT_WATER);
  AllDepots.Valuate(AITile.GetDistanceManhattanToTile, TileID);
  AllDepots.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  return AllDepots.Begin();
}

/* == Passerelle Opex : instance persistante pour toute la partie ============================
 *
 * Le constructeur de _MinchinWeb_Lakes_ peuple _map avec une entree par tuile de la carte
 * ENTIERE (~65 536 sur 256x256) : cree une seule fois, jamais par generation (contrairement
 * aux caches ephemeres C41.30/C41.38 vides a chaque OpexBuildCandidates). Slot de table
 * racine, meme pattern que ::REASON_CODES dans ai/TrainLineAI/main.nut -- jamais un `local`
 * de fichier, qui ne persisterait pas entre appels. */
::OpexWaterLakes <- null;

/* TEMPORAIRE : constante locale a builder_water.nut, PAS un reglage info.nut -- une autre
 * session modifie info.nut/main.nut/candidates.nut en parallele (isolation 2026-09-09). A
 * migrer vers AddSetting() des que ces fichiers sont de nouveau libres.
 *
 * Calibree par mesure, pas devinee (2026-09-09) : instrumentation temporaire de
 * `_lastIterationsUsed` (toujours presente, activee via `profile`) branchee un temps sur l'appel
 * reel de `projects.nut::OpexProjects`, 8 graines x 6 ans, 240 cycles mensuels, 27 requetes
 * Lakes reelles (`results` non conserve, mesure ponctuelle) :
 *   - connecte (25/27) : 1 a 4 iterations, moyenne 1,12 -- quasi gratuit.
 *   - non connecte (2/27) : 4 a 153 iterations, moyenne 98,5.
 *   - budget epuise (`exhausted`) : 0/27, jamais atteint.
 * L'ancien 2000 etait donc surdimensionne d'un facteur ~13 par rapport au pire cas mesure.
 * Retenu : 500 (~3,3x le pire cas observe, marge pour des cartes/configs non echantillonnees --
 * pas 153 pile, l'echantillon est petit). A rementer si `lakes_iterations_exhausted_n` (champ de
 * profil deja cable, voir OpexWaterLakesConnected) se met a mordre sur un banc plus large. */
WATER_LAKES_ITERATIONS <- 500;

function OpexWaterLakesInstance(profile = null)
{
  if (::OpexWaterLakes == null) {
    local mark = profile != null ? OpexOpsMeasureBegin() : null;
    ::OpexWaterLakes = _MinchinWeb_Lakes_();
    if (profile != null) profile.lakes_init_ops = OpexOpsMeasureEnd(mark);
  }
  return ::OpexWaterLakes;
}

/* Connectivite maritime memorisee : true (connecte), false (pas de chemin), null (budget
 * d'iterations consomme sans conclusion -- traite comme un echec par l'appelant, au meme titre
 * qu'un PATHLIM ailleurs dans le projet). */
/* `waterTilesA`/`waterTilesB` : tuiles d'EAU adjacentes a chaque quai (site.waterTiles), PAS
 * les tuiles de quai elles-memes -- _MinchinWeb_Lakes_::AddPoint marque toute tuile terre comme
 * groupe -1 et s'arrete la (bug trouve et corrige le 2026-09-09 : passer les tuiles de quai
 * faisait echouer AGroup/BGroup des l'appel, FindPath sortant immediatement sur son tout premier
 * garde -- zero paire jamais confirmee connectee, silencieusement, sur la graine 24 ou l'ancien
 * BFS construit pourtant une ligne). Un site n'est retenu par OpexWaterFindSite que si
 * waterTiles.len() > 0, donc jamais de tableau vide ici. */
function OpexWaterLakesConnected(waterTilesA, waterTilesB, profile = null)
{
  local lakes = OpexWaterLakesInstance(profile);
  local mark = profile != null ? OpexOpsMeasureBegin() : null;
  lakes.InitializePath(waterTilesA, waterTilesB);
  local result = lakes.FindPath(WATER_LAKES_ITERATIONS);
  if (profile != null) {
    profile.lakes_query_ops += OpexOpsMeasureEnd(mark);
    profile.lakes_queries++;
    local used = lakes._lastIterationsUsed;
    if (used != null) {
      if (result == true) {
        profile.lakes_iterations_connected_sum += used;
        profile.lakes_iterations_connected_n++;
        if (used > profile.lakes_iterations_connected_max) profile.lakes_iterations_connected_max = used;
      } else if (result == null) {
        profile.lakes_iterations_no_path_sum += used;
        profile.lakes_iterations_no_path_n++;
        if (used > profile.lakes_iterations_no_path_max) profile.lakes_iterations_no_path_max = used;
      } else {
        /* result == false : budget epuise sans conclusion -- used == WATER_LAKES_ITERATIONS. */
        profile.lakes_iterations_exhausted_n++;
      }
    }
  }
  if (result == true) return true;
  if (result == null) return false;
  /* result == false : budget epuise sans conclusion. */
  return null;
}
