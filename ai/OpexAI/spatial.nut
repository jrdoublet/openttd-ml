/* Indexation spatiale conservative pour les paires de villes.
 *
 * Cellules de cote S : une paire a |dx| + |dy| <= S est forcement dans la cellule
 * de l'origine ou dans l'une de ses 8 voisines de Moore. Aucun faux negatif en
 * distance de Manhattan. Les listes sont plates ; la grille se reconstruit a
 * chaque generation (O(n) insertions). */

function OpexIsqrt(n)
{
  if (n <= 0) return 0;
  local x = n;
  local y = (x + 1) / 2;
  while (y < x) {
    x = y;
    y = (x + n / x) / 2;
  }
  return x;
}

class OpexSpatialGrid {
  _cells = null;
  _cellSize = 1;
  _towns = null;

  constructor()
  {
    this._cells = {};
    this._cellSize = 1;
    this._towns = [];
  }

  function Clear();
  function Build(townList, cellSize);
  function GetCandidatesFor(townIndex);
}

function OpexSpatialGrid::Clear()
{
  this._cells = {};
  this._cellSize = 1;
  this._towns = [];
}

function OpexSpatialGrid::Build(townList, cellSize)
{
  this.Clear();
  if (townList == null) return;
  if (cellSize < 1) cellSize = 1;
  this._cellSize = cellSize;
  this._towns = townList;
  local n = townList.len();
  for (local i = 0; i < n; i++) {
    local tile = townList[i].tile;
    local cx = AIMap.GetTileX(tile) / cellSize;
    local cy = AIMap.GetTileY(tile) / cellSize;
    local key = cx + ":" + cy;
    if (key in this._cells) {
      this._cells[key].append(i);
    } else {
      this._cells[key] <- [i];
    }
  }
}

/* Indices des villes dans le voisinage 3x3, avec idx > townIndex pour casser
 * la symmetrie (equivalent au ancien `for b = a + 1`). */
function OpexSpatialGrid::GetCandidatesFor(townIndex)
{
  local out = [];
  if (this._towns == null || townIndex < 0 || townIndex >= this._towns.len()) return out;
  local tile = this._towns[townIndex].tile;
  local cellSize = this._cellSize;
  local cx = AIMap.GetTileX(tile) / cellSize;
  local cy = AIMap.GetTileY(tile) / cellSize;
  for (local dx = -1; dx <= 1; dx++) {
    for (local dy = -1; dy <= 1; dy++) {
      local key = (cx + dx) + ":" + (cy + dy);
      if (!(key in this._cells)) continue;
      local bucket = this._cells[key];
      foreach (idx in bucket) {
        if (idx > townIndex) out.append(idx);
      }
    }
  }
  return out;
}

/* Indexation spatiale dirigee (asymetrique) pour paires source -> puits (C46).
 *
 * Cellules de cote S : tout puits a |dx| + |dy| <= S est forcement dans la cellule
 * de la source ou dans l'une de ses 8 voisines de Moore.
 * La grille indexe les puits en O(sinks) et retourne pour une tuile source
 * la liste des indices k de puits ordonnee strictement par index croissant.
 *
 * Complexite :
 * - Construction de la grille : O(sinks).
 * - Par source, GetSortedCandidates copie et trie les q_s puits des 9 cellules : O(q_s log q_s).
 * - Coût global de generation : O(sinks + sum_{s} q_s log q_s).
 * - En repartition spatiale standard, q_s << sinks, ce qui supprime le balayage cartesien global
 *   inconditionnel. Toutefois, dans le pire cas ou les puits seraient tous concentres dans
 *   ces cellules (q_s ~ sinks), le parcours reste au moins O(sources x sinks). */
class OpexDirectedSpatialGrid {
  _cells = null;
  _cellSize = 1;
  _sinkCount = 0;

  constructor()
  {
    this._cells = {};
    this._cellSize = 1;
    this._sinkCount = 0;
  }

  function Clear();
  function Build(items, cellSize, container = null);
  function GetSortedCandidates(srcTile);
}

function OpexDirectedSpatialGrid::Clear()
{
  this._cells = {};
  this._cellSize = 1;
  this._sinkCount = 0;
}

function OpexDirectedSpatialGrid::Build(items, cellSize, container = null)
{
  this.Clear();
  if (items == null) return;
  if (cellSize < 1) cellSize = 1;
  this._cellSize = cellSize;
  this._sinkCount = items.len();
  for (local k = 0; k < this._sinkCount; k++) {
    local tile;
    if (container != null) {
      local idx = items[k];
      tile = container[idx].tile;
    } else {
      local it = items[k];
      tile = (typeof it == "integer") ? it : (("tile" in it) ? it.tile : null);
    }
    if (tile == null || !AIMap.IsValidTile(tile)) continue;
    local cx = AIMap.GetTileX(tile) / cellSize;
    local cy = AIMap.GetTileY(tile) / cellSize;
    if (cx < 0 || cy < 0) continue;
    local key = (cx << 16) | (cy & 0xFFFF);
    if (key in this._cells) {
      this._cells[key].append(k);
    } else {
      this._cells[key] <- [k];
    }
  }
}

/* Retourne les indices k des puits situes dans les 9 cellules voisines de Moore,
 * tries par ordre d'indice croissant (garantit la parite exacte de vivier avec la boucle historique).
 * Cout : O(q_s log q_s) avec q_s = nombre de puits dans les 9 cellules. */
function OpexDirectedSpatialGrid::GetSortedCandidates(srcTile)
{
  local out = [];
  if (this._sinkCount == 0 || !AIMap.IsValidTile(srcTile)) return out;
  local cellSize = this._cellSize;
  local cx = AIMap.GetTileX(srcTile) / cellSize;
  local cy = AIMap.GetTileY(srcTile) / cellSize;
  for (local dx = -1; dx <= 1; dx++) {
    local nx = cx + dx;
    if (nx < 0) continue;
    for (local dy = -1; dy <= 1; dy++) {
      local ny = cy + dy;
      if (ny < 0) continue;
      local key = (nx << 16) | (ny & 0xFFFF);
      if (!(key in this._cells)) continue;
      local bucket = this._cells[key];
      foreach (k in bucket) {
        out.append(k);
      }
    }
  }
  if (out.len() > 1) {
    out.sort();
  }
  return out;
}
