/* C67 : le remplissage de carte (ancien c67_terrain_map, defaut 0, sans consommateur) est retire.
 * Il ne reste que la sonde passive d'exposition eau, elle-meme eteinte au defaut.
 * Le crochet s'execute dans le reliquat du tick, juste avant Sleep(1), seulement si la sonde
 * est armee. Rien n'est sauvegarde. */

C67_SLACK_MIN <- 4000;     // en dessous, le reliquat ne paie pas la tranche.
C67_LINE_MARGIN <- 8;      // tuiles autour de la boite englobante d'une nouvelle ligne.

/* Une ligne stocke des tuiles dans stationA/stationB pour tous les modes. */
function OpexC67LineRect(line)
{
  local a = ("stationA" in line) ? line.stationA : null;
  local b = ("stationB" in line) ? line.stationB : null;
  if (a == null || b == null || !AIMap.IsValidTile(a) || !AIMap.IsValidTile(b)) return null;
  local xa = AIMap.GetTileX(a), ya = AIMap.GetTileY(a);
  local xb = AIMap.GetTileX(b), yb = AIMap.GetTileY(b);
  return { x0 = min(xa, xb) - C67_LINE_MARGIN, y0 = min(ya, yb) - C67_LINE_MARGIN,
           x1 = max(xa, xb) + C67_LINE_MARGIN + 1, y1 = max(ya, yb) + C67_LINE_MARGIN + 1 };
}

/* ---- C67.6 : sonde passive d'exposition eau (c67_water_exposure_probe, defaut 0). ----
 * Chaque paire de quais que le BFS borne d'OpexWaterPlans rejette (no_connection) est mise en
 * file ; l'oracle C67.5 la reevalue ensuite UNIQUEMENT dans le reliquat de tick. Aucune decision
 * n'est modifiee. Etat non sauvegarde : apres chargement, la sonde repart vide. */

C67_WATER_QUEUE_MAX <- 64;

/* Appelee au site du BFS d'OpexWaterPlans. Cout minimal : compteurs, deduplication, file. */
function OpexC67WaterExposureNote(siteA, siteB, navigable, tariff, order, pax)
{
  local s = C67_WATER_EXPO;
  if (s == null) {
    s = { queue = [], seen = {}, bfs = 0, rejects = 0, unique = 0, dup = 0, dropped = 0 };
    ::C67_WATER_EXPO = s;
  }
  s.bfs++;
  if (navigable >= 0) return;
  s.rejects++;
  local lo = siteA.dock < siteB.dock ? siteA.dock : siteB.dock;
  local hi = siteA.dock < siteB.dock ? siteB.dock : siteA.dock;
  local key = lo * 4194304 + hi;
  if (key in s.seen) { s.dup++; return; }
  s.seen.rawset(key, true);
  s.unique++;
  if (s.queue.len() >= C67_WATER_QUEUE_MAX) { s.dropped++; return; }
  s.queue.append({ a = siteA.waterTiles, b = siteB.waterTiles, dockA = siteA.dock,
                   dockB = siteB.dock, tariff = tariff, order = order, pax = pax,
                   date = AIDate.GetCurrentDate() });
}

function OpexAI::_c67SlackHook()
{
  /* Controle AVANT tout travail : sous le seuil, le crochet ne doit rien consommer, sinon il
   * peut franchir le tick et decaler le Sleep(1) (divergence observee en C67.6). */
  if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return;
  if (C67_WATER_EXPOSURE) this._c67WaterExposureStep();
}

function OpexAI::_c67WaterLogYear()
{
  local w = this._c67Water;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year == w.year) return;
  local s = C67_WATER_EXPO;
  local g = w.graph.Stats();
  AILog.Info("C67W_YEAR year=" + w.year + " bfs=" + (s == null ? 0 : s.bfs)
             + " rejects=" + (s == null ? 0 : s.rejects) + " unique=" + (s == null ? 0 : s.unique)
             + " dup=" + (s == null ? 0 : s.dup) + " dropped=" + (s == null ? 0 : s.dropped)
             + " pending=" + (s == null ? 0 : s.queue.len()) + " evaluated=" + w.evaluated
             + " connected=" + w.connected + " disconnected=" + w.disconnected
             + " unknown=" + w.unknown + " profitable=" + w.profitable
             + " analyzed=" + g.analyzed + " resident=" + g.resident + " ops_max=" + g.ops_max
             + " unit_ops_max=" + g.unit_ops_max);
  w.year = year;
}

/* Paire suivante (tuile d'eau de A, tuile d'eau de B) non encore tranchee par une composante
 * fermee deja enumeree ; null quand toutes le sont. */
function OpexAI::_c67WaterNextQuery(job)
{
  local g = this._c67Water.graph;
  while (job.ia < job.item.a.len()) {
    local ta = job.item.a[job.ia];
    while (job.ib < job.item.b.len()) {
      local tb = job.item.b[job.ib++];
      local na = g.NodeOf(AIMap.GetTileX(ta), AIMap.GetTileY(ta));
      local nb = g.NodeOf(AIMap.GetTileX(tb), AIMap.GetTileY(tb));
      local decided = false;
      if (na != null && nb != null) {
        foreach (closed in job.closed) {
          if ((na in closed) && !(nb in closed)) { decided = true; break; }
        }
      }
      if (!decided) return [ta, tb];
    }
    job.ia++;
    job.ib = 0;
  }
  return null;
}

function OpexAI::_c67WaterFinish(job, result, reason, cdist)
{
  local w = this._c67Water;
  local item = job.item;
  local profit = "-", roi = "-";
  w.evaluated++;
  w[result]++;
  if (result == "connected" && cdist >= 0 && this._catalog != null) {
    local e = OpexWaterEconomics(this._catalog, cdist, item.tariff, item.order, item.pax);
    if (e != null) {
      profit = e.profitAnnual;
      roi = e.roi;
      if (e.profitAnnual > 0) w.profitable++;
    }
  }
  AILog.Info("C67W_EXPO dock_a=" + item.dockA + " dock_b=" + item.dockB + " tariff=" + item.tariff
             + " order=" + item.order + " pax=" + item.pax + " result=" + result
             + " reason=" + (reason == null ? "-" : reason) + " cdist=" + cdist
             + " profit=" + profit + " roi=" + roi + " queries=" + job.queries
             + " ops=" + job.ops + " wait_days=" + (AIDate.GetCurrentDate() - item.date));
  w.job = null;
}

function OpexAI::_c67WaterExposureStep()
{
  if (this._c67Water == null) {
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return;
    this._c67Water = { graph = OpexWaterGraph(), job = null, evaluated = 0, connected = 0,
                       disconnected = 0, unknown = 0, profitable = 0,
                       linesSeen = this._lines == null ? 0 : this._lines.len(),
                       year = AIDate.GetYear(AIDate.GetCurrentDate()) };
    return;
  }
  this._c67WaterLogYear();
  local w = this._c67Water;
  local g = w.graph;
  /* Nos nouvelles lignes (quais, depots) modifient l'eau observee : invalider leur emprise. */
  local n = this._lines.len();
  if (n < w.linesSeen) w.linesSeen = n;
  while (w.linesSeen < n) {
    local rect = OpexC67LineRect(this._lines[w.linesSeen++]);
    if (rect != null) g.InvalidateRect(rect.x0, rect.y0, rect.x1, rect.y1);
  }
  if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return;
  if (w.job == null) {
    local s = C67_WATER_EXPO;
    if (s == null || s.queue.len() == 0) return;
    w.job = { item = s.queue.remove(0), ia = 0, ib = 0, closed = [], anyUnknown = false,
              reason = null, queries = 0, ops = 0, corridor = null, active = false, pair = null };
  }
  local job = w.job;
  local tick = AIController.GetTick();
  if (job.corridor != null) {
    local c = job.corridor;
    local before = c.ops_total;
    c.Step(AIController.GetOpsTillSuspend(), tick + 1);
    job.ops += c.ops_total - before;
    if (c.status != "running")
      this._c67WaterFinish(job, "connected", c.status == "found" ? null : "corridor_" + c.status,
                           c.distance == null ? -1 : c.distance);
    return;
  }
  if (!job.active) {
    local pair = this._c67WaterNextQuery(job);
    if (pair == null) {
      this._c67WaterFinish(job, job.anyUnknown ? "unknown" : "disconnected", job.reason, -1);
      return;
    }
    g.Begin(AIMap.GetTileX(pair[0]), AIMap.GetTileY(pair[0]),
            AIMap.GetTileX(pair[1]), AIMap.GetTileY(pair[1]));
    job.queries++;
    job.active = true;
    job.pair = pair;
  }
  local before = g.Stats().ops_total;
  g.Step(AIController.GetOpsTillSuspend(), tick + 1);
  job.ops += g.Stats().ops_total - before;
  local r = g.Result();
  if (r.status == "running") return;
  job.active = false;
  if (r.status == "connected") {
    local a = job.pair[0], b = job.pair[1];
    job.corridor = OpexWaterCorridor(g, g.CorridorBlocks(r.chain), AIMap.GetTileX(a),
                                     AIMap.GetTileY(a), AIMap.GetTileX(b), AIMap.GetTileY(b));
  } else if (r.status == "disconnected") {
    job.closed.append(r.component);
  } else if (r.reason == "invalidated") {
    job.ib--;               // rejouer la meme paire sur les blocs recalcules
    if (job.ib < 0) { job.ia--; job.ib = job.item.b.len() - 1; }
  } else {
    job.anyUnknown = true;
    job.reason = r.reason;
  }
}
