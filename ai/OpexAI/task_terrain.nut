/* C67.4 : cycle de vie de la carte par blocs (contrat docs/c67_cartographie_contrat.md §14).
 *
 * Le service n'existe que sous c67_terrain_map=1. Le crochet s'execute dans le RELIQUAT du tick,
 * juste avant le Sleep(1) de la boucle principale qui abandonne ce reliquat de toute facon : il ne
 * franchit jamais un tick, ne preempte aucune tache metier et n'emet aucune commande de jeu (ni
 * panneau, ni construction). Sans consommateur, une partie avec le service doit donc rester
 * identique a la meme graine sans lui. Rien n'est sauvegarde : le cache se reconstruit. */

C67_SIDE <- 5;             // C67.3 §13 : S=5 retenu provisoirement.
C67_SLACK_RESERVE <- 3000; // opcodes laisses au tick : une lecture de tuile ne doit pas le franchir.
C67_SLACK_MIN <- 4000;     // en dessous, le reliquat ne paie pas la tranche.
C67_BG_BATCH <- 4;         // blocs sondes par le fond a chaque crochet.
C67_BG_QUEUE <- 8;         // le fond ne remplit jamais la file au-dela.
C67_LINE_MARGIN <- 8;      // tuiles autour de la boite englobante d'une nouvelle ligne.

function OpexAI::_c67TerrainInit()
{
  this._c67Terrain = OpexTerrainMap(C67_SIDE);
  this._c67BgCursor = 0;
  this._c67BgFresh = 0;
  this._c67BgIdle = false;
  /* Les lignes deja presentes (partie rechargee) precedent un cache vide : rien a invalider. */
  this._c67LinesSeen = this._lines == null ? 0 : this._lines.len();
  this._c67Ledger = { hooks = 0, skipped = 0, lines = 0, bg_requests = 0 };
  this._c67Year = AIDate.GetYear(AIDate.GetCurrentDate());
}

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

/* Travaux propres : toute ligne ajoutee depuis le dernier crochet invalide sa boite englobante.
 * Les retraits de lignes, agrandissements et routes de croissance ne sont pas couverts (§14). */
function OpexAI::_c67NoteNewLines()
{
  local n = this._lines.len();
  if (n < this._c67LinesSeen) this._c67LinesSeen = n;
  while (this._c67LinesSeen < n) {
    local rect = OpexC67LineRect(this._lines[this._c67LinesSeen]);
    this._c67LinesSeen++;
    if (rect == null) continue;
    this._c67Terrain.InvalidateRect(rect.x0, rect.y0, rect.x1, rect.y1);
    this._c67Ledger.lines++;
    this._c67BgIdle = false;
  }
}

/* Remplissage opportuniste : ordre raster, sans eviction (le service refuse le fond plein). */
function OpexAI::_c67FeedBackground()
{
  local map = this._c67Terrain;
  local total = map.BlockCount();
  for (local i = 0; i < C67_BG_BATCH; i++) {
    if (this._c67BgIdle || map.PendingCount() >= C67_BG_QUEUE || map.BackgroundRoom() <= 0) return;
    local id = this._c67BgCursor;
    this._c67BgCursor = (id + 1) % total;
    if (map.Request(id, 0) == "pending") {
      this._c67BgFresh++;
      this._c67Ledger.bg_requests++;
    }
    if (this._c67BgCursor == 0) {
      /* Un tour complet sans demande : carte couverte, attendre la prochaine invalidation. */
      if (this._c67BgFresh == 0) this._c67BgIdle = true;
      this._c67BgFresh = 0;
    }
  }
}

function OpexAI::_c67LogYear()
{
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year == this._c67Year) return;
  local s = this._c67Terrain.Stats();
  local l = this._c67Ledger;
  AILog.Info("C67_TERRAIN year=" + this._c67Year + " resident=" + s.resident
             + " pending=" + s.pending + " completed=" + s.completed + " reads=" + s.reads
             + " ops_total=" + s.ops_total + " ops_max=" + s.ops_max + " steps=" + s.steps
             + " evictions=" + s.evictions + " bg_refused=" + s.bg_refused
             + " bg_dropped=" + s.bg_dropped + " invalidations=" + s.invalidations
             + " cancelled=" + s.cancelled + " rects=" + s.rects + " hooks=" + l.hooks
             + " skipped=" + l.skipped + " lines=" + l.lines + " bg_requests=" + l.bg_requests
             + " bg_idle=" + (this._c67BgIdle ? 1 : 0) + " blocks=" + this._c67Terrain.BlockCount());
  this._c67Year = year;
}

/* Appele par la boucle principale juste avant Sleep(1), sous C67_TERRAIN_MAP seulement. */
function OpexAI::_c67TerrainSlackStep()
{
  if (this._c67Terrain == null) {
    /* Construction paresseuse, elle aussi dans le reliquat : Start() ne paie rien, sinon les
     * frontieres des premiers ticks se decaleraient par rapport a la partie sans service. */
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return;
    this._c67TerrainInit();
    return;
  }
  this._c67NoteNewLines();
  this._c67LogYear();
  if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) {
    this._c67Ledger.skipped++;
    return;
  }
  this._c67Ledger.hooks++;
  this._c67FeedBackground();
  local left = AIController.GetOpsTillSuspend();
  if (left < C67_SLACK_MIN || this._c67Terrain.PendingCount() == 0) return;
  this._c67Terrain.Step(left - C67_SLACK_RESERVE, AIController.GetTick() + 1);
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
  if (C67_TERRAIN_MAP) this._c67TerrainSlackStep();
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
