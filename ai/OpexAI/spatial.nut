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

/* Levier B, Niveau 1 : verifie si une tuile de station rivale se trouve dans le rayon de captage
 * d'une industrie primaire (pas de gare de chargement sur industrie primaire rival-servie).
 * Niveaux 2 et 3 : zero opcode de plus (court-circuit en premiere ligne). */
function OpexIndustryPrimaryRivalServed(industryId, industryTile = null, coverage = -1)
{
  if (OpexLevelAllows("compete_primary_industry")) return false;
  if (!AIIndustry.IsValidIndustry(industryId)) return false;
  local indType = AIIndustry.GetIndustryType(industryId);
  if (!AIIndustryType.IsValidIndustryType(indType) || !AIIndustryType.IsRawIndustry(indType)) return false;
  if (AIIndustry.GetAmountOfStationsAround(industryId) == 0) return false;
  if (coverage <= 0) coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  /* Tuiles d'ou une gare capterait la production : exactement le critere « desservie ». */
  local me = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local tiles = AITileList_IndustryProducing(industryId, coverage);
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(1);
  foreach (tile, _ in tiles) {
    local owner = AITile.GetOwner(tile);
    if (owner == me || AICompany.ResolveCompanyID(owner) == AICompany.COMPANY_INVALID) continue;
    if (DECISION_LOG) OpexDecide("LEVEL_SKIP", "feature=compete_primary_industry industry=" + industryId
        + " rival_tile=" + tile + " rival_owner=" + owner);
    return true;
  }
  return false;
}

/* Levier B, Niveau 0 : verifie si une tuile de station rivale se trouve dans l'emprise etendue
 * du rayon de captage du type de gare (aucune gare chevauchant une gare rivale existante).
 * Niveaux 1, 2 et 3 : zero opcode de plus (court-circuit en premiere ligne). */
function OpexStationEncroachesRival(minX, minY, maxX, maxY, coverage = -1)
{
  if (OpexLevelAllows("encroach_rival_catchment")) return false;

  if (coverage <= 0) coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);

  local me = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local sMinX = minX - coverage < 1 ? 1 : minX - coverage;
  local sMinY = minY - coverage < 1 ? 1 : minY - coverage;
  local mapX = AIMap.GetMapSizeX() - 2;
  local mapY = AIMap.GetMapSizeY() - 2;
  local sMaxX = maxX + coverage > mapX ? mapX : maxX + coverage;
  local sMaxY = maxY + coverage > mapY ? mapY : maxY + coverage;

  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(sMinX, sMinY), AIMap.GetTileIndex(sMaxX, sMaxY));
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(1);

  foreach (tile, _ in tiles) {
    local owner = AITile.GetOwner(tile);
    if (owner != me && AICompany.ResolveCompanyID(owner) != AICompany.COMPANY_INVALID) {
      if (DECISION_LOG) {
        OpexDecide("LEVEL_SKIP", "feature=encroach_rival_catchment tile=" + tile + " rival_owner=" + owner);
      }
      return true;
    }
  }

  return false;
}
