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
