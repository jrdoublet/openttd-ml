/* V308 : mesure passive ponctuelle des blocs 8x8, defaut 0.
 * Verite exhaustive (64 tuiles), V307 5 points, quinconce 6 points, court-circuit
 * decisif, decalage de parite et variante plat/sec. Aucun effet sur le routage. */

V308_V307 <- [[4, 4], [2, 2], [6, 2], [2, 6], [6, 6]];
V308_PERIPHERAL <- [[3, 1], [6, 2], [1, 5], [4, 6]];
V308_CENTRAL <- [[2, 3], [5, 4]];

function OpexV308NewStats()
{
  return { n = 0, sea = 0, lake = 0, river = 0, coast = 0, house = 0,
           town = 0, road = 0, build = 0, obst = 0, lo = 999, hi = -1, relief = 0 };
}

/* Chaque lecture de motif rappelle vraiment les API, afin de mesurer leur cout.
 * Le champ town compte une autorite valide, les maisons sont comptees a part. */
function OpexV308ReadTile(bx, by, x, y)
{
  local tile = AIMap.GetTileIndex(bx * 8 + x, by * 8 + y);
  local sea = AITile.IsSeaTile(tile) ? 1 : 0;
  local river = AITile.IsRiverTile(tile) ? 1 : 0;
  local water = AITile.IsWaterTile(tile) ? 1 : 0;
  local coast = AITile.IsCoastTile(tile) ? 1 : 0;
  local house = AITile.IsHouseTile(tile) ? 1 : 0;
  local town = AITile.GetTownAuthority(tile);
  local road = AIRoad.IsRoadTile(tile) ? 1 : 0;
  local build = AITile.IsBuildable(tile) ? 1 : 0;
  return { sea = sea, river = river, lake = (water && !sea && !river) ? 1 : 0,
           coast = coast, house = house, town = AITown.IsValidTown(town) ? 1 : 0,
           road = road, build = build,
           obst = (!water && !house && !road && !build) ? 1 : 0,
           lo = AITile.GetMinHeight(tile), hi = AITile.GetMaxHeight(tile) };
}

function OpexV308Add(s, t)
{
  s.n++;
  s.sea += t.sea;
  s.lake += t.lake;
  s.river += t.river;
  s.coast += t.coast;
  s.house += t.house;
  s.town += t.town;
  s.road += t.road;
  s.build += t.build;
  s.obst += t.obst;
  if (t.lo < s.lo) s.lo = t.lo;
  if (t.hi > s.hi) s.hi = t.hi;
  s.relief = s.hi - s.lo;
}

/* Une composante fluviale connexe a quatre voisins touche deux bords opposes. */
function OpexV308RiverCrosses(rivers)
{
  local visited = [];
  for (local i = 0; i < 64; i++) visited.push(false);
  local dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  for (local start = 0; start < 64; start++) {
    if (rivers[start] == 0 || visited[start]) continue;
    local queue = [start];
    visited[start] = true;
    local index = 0, edges = 0;
    while (index < queue.len()) {
      local current = queue[index++];
      local x = current % 8, y = current / 8;
      if (x == 0) edges = edges | 1;
      if (x == 7) edges = edges | 2;
      if (y == 0) edges = edges | 4;
      if (y == 7) edges = edges | 8;
      if ((edges & 3) == 3 || (edges & 12) == 12) return 1;
      foreach (dir in dirs) {
        local nx = x + dir[0], ny = y + dir[1];
        if (nx < 0 || ny < 0 || nx >= 8 || ny >= 8) continue;
        local next = ny * 8 + nx;
        if (rivers[next] == 0 || visited[next]) continue;
        visited[next] = true;
        queue.push(next);
      }
    }
  }
  return 0;
}

function OpexV308Truth(bx, by)
{
  local s = OpexV308NewStats();
  local rivers = [];
  for (local y = 0; y < 8; y++) {
    for (local x = 0; x < 8; x++) {
      local t = OpexV308ReadTile(bx, by, x, y);
      OpexV308Add(s, t);
      rivers.push(t.river);
    }
  }
  s.riverCross <- OpexV308RiverCrosses(rivers);
  return s;
}

/* Modes : 0 V307, 1 full6, 2 short6, 3 parity6, 4 flatdry6.
 * Les quatre peripheriques sont toujours lus avant le test des deux centraux. */
function OpexV308Arm(bx, by, mode)
{
  local mark = OpexOpsMeasureBegin();
  local s = OpexV308NewStats();
  if (mode == 0) {
    foreach (p in V308_V307) OpexV308Add(s, OpexV308ReadTile(bx, by, p[0], p[1]));
  } else {
    local delta = (mode == 3 && ((bx + by) % 2) != 0) ? 1 : 0;
    foreach (p in V308_PERIPHERAL) {
      OpexV308Add(s, OpexV308ReadTile(bx, by, p[0] + delta, p[1] + delta));
    }
    local centers = true;
    if (mode == 2) {
      centers = !(s.sea + s.lake >= 2 || s.house >= 2 || s.town >= 3 || s.relief >= 4);
    } else if (mode == 4) {
      centers = s.relief == 0 && s.sea + s.lake + s.river == 0;
    }
    if (centers) {
      foreach (p in V308_CENTRAL) {
        OpexV308Add(s, OpexV308ReadTile(bx, by, p[0] + delta, p[1] + delta));
      }
    }
  }
  local ops = OpexOpsMeasureEnd(mark);
  return { stats = s, ops = ops };
}

function OpexV308ArmFields(name, arm)
{
  local s = arm.stats;
  return " " + name + "_n=" + s.n + " " + name + "_sea=" + s.sea
      + " " + name + "_lake=" + s.lake + " " + name + "_river=" + s.river
      + " " + name + "_coast=" + s.coast + " " + name + "_house=" + s.house
      + " " + name + "_town=" + s.town + " " + name + "_obst=" + s.obst
      + " " + name + "_relief=" + s.relief + " " + name + "_ops=" + arm.ops;
}

function OpexV308CartoProbe()
{
  local nx = AIMap.GetMapSizeX() / 8, ny = AIMap.GetMapSizeY() / 8;
  if (nx < 3 || ny < 3) {
    OpexDecide("V308_START", "n=0 reason=map_too_small");
    return;
  }
  OpexDecide("V308_START", "n=400 side=8 year_offset=" + V307_PROBE_YEAR
      + " mapx=" + AIMap.GetMapSizeX() + " mapy=" + AIMap.GetMapSizeY());
  for (local i = 0; i < 400; i++) {
    /* Exclure les blocs du pourtour, dont les tuiles en bord de carte sont invalides. */
    local bx = 1 + AIBase.RandRange(nx - 2);
    local by = 1 + AIBase.RandRange(ny - 2);
    local truth = OpexV308Truth(bx, by);
    local v307 = OpexV308Arm(bx, by, 0);
    local full6 = OpexV308Arm(bx, by, 1);
    local short6 = OpexV308Arm(bx, by, 2);
    local parity6 = OpexV308Arm(bx, by, 3);
    local flatdry6 = OpexV308Arm(bx, by, 4);
    OpexDecide("V308_BLOCK", "i=" + i + " bx=" + bx + " by=" + by
        + " t_n=" + truth.n + " t_sea=" + truth.sea + " t_lake=" + truth.lake
        + " t_river=" + truth.river + " t_river_cross=" + truth.riverCross
        + " t_coast=" + truth.coast + " t_house=" + truth.house
        + " t_town=" + truth.town + " t_build=" + truth.build
        + " t_road=" + truth.road + " t_obst=" + truth.obst
        + " t_relief=" + truth.relief
        + OpexV308ArmFields("v307", v307) + OpexV308ArmFields("full6", full6)
        + OpexV308ArmFields("short6", short6) + OpexV308ArmFields("parity6", parity6)
        + OpexV308ArmFields("flatdry6", flatdry6));
  }
  OpexDecide("V308_END", "n=400");
}

/* Identique a V307 : une fois apres le demarrage, jamais apres un chargement. */
function OpexV308MaybeRun(loadedFromSave)
{
  if (V308_DONE || loadedFromSave) return;
  if (AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + V307_PROBE_YEAR) return;
  V308_DONE = true;
  OpexV308CartoProbe();
}
