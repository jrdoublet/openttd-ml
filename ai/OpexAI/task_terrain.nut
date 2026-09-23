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
