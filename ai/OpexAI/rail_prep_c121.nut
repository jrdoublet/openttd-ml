/* C121 annee « aerien seul » : preparer le rail sans le construire.
 *
 * La preparation est active quand AIR et rail sont autorises. Chaque entree
 * de ce fichier est gardee par ce booleen : aucun catalogue, aucun A*, aucun
 * journal tant qu'il est faux. Le stock et la liste de candidats ne sont pas
 * sauvegardes ; Load les recalcule.
 *
 * Au plus C121_RAIL_PREP_MAX traces, le meilleur candidat d'abord, un A* a la
 * fois, via la recherche segmentee du stock C80. Les reglages c80_rail_stock_*
 * restent a 0 : cette branche ne les lit pas pour decider.
 */
const C121_RAIL_PREP_MAX = 3;

/* Moindre capital finançable des plans AIR encore vivants, dans tout le vivier
 * (pas seulement best, qui est deja filtre par la caisse). -1 si aucun. */
function OpexAI::_c121CheapestLivingAirCap()
{
  local minCap = -1;
  local projects = this._projects;
  local groups = (projects != null && ("candidateGroups" in projects)) ? projects.candidateGroups : null;
  if (groups != null) {
    local lines = this._lines;
    foreach (key, list in groups) {
      if (list == null) continue;
      foreach (project in list) {
        if (project == null || !("mode" in project) || project.mode != "air") continue;
        if (!("payload" in project) || project.payload == null) continue;
        if (!OpexAirBatchPlanStillLive(project.payload, lines)) continue;
        local cap = OpexProjectFinanceCapital(project);
        if (minCap < 0 || cap < minCap) minCap = cap;
      }
    }
  }
  this._c121RailPrepMinAirCap = minCap;
  return minCap;
}

function OpexAI::_c121RailPrepAirFundable()
{
  local cap = this._c121CheapestLivingAirCap();
  if (cap < 0) return false;
  return cap <= OpexAvailableCapital();
}

/* Pas de parcours du portefeuille : le minimum a ete fige en fin de passe.
 * Tant que la caisse seule ne couvre pas ce minimum, la reserve n'est pas lue. */
function OpexAI::_c121RailPrepAirFundableCheap()
{
  local cap = this._c121RailPrepMinAirCap;
  if (cap < 0) return false;
  /* Emprunt desactive : disponible <= caisse. Une caisse sous le minimum
   * dispense de la reserve (liste de vehicules). */
  if (cap > 0) {
    local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (cash < cap) return false;
  }
  return cap <= OpexAvailableCapital();
}

/* Vrai si la caisse seule exclut le moins cher des plans AIR vivants.
 * -1 (aucun plan) est aussi inabordable. Ne lit pas la liste de vehicules. */
function OpexAI::_c121RailPrepCashBelowAir()
{
  local cap = this._c121RailPrepMinAirCap;
  if (cap < 0) return true;
  if (cap <= 0) return false;
  return AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cap;
}

function OpexAI::_c121RailSearchIsPrep()
{
  if (!(MODE_AIR && MODE_RAIL)) return false;
  if (this._railSearch == null) return false;
  return ("isC121RailPrep" in this._railSearch) && this._railSearch.isC121RailPrep;
}

/* Condition 1 : premiere annee, aucun AIR vivant finançable, aucune recherche. */
function OpexAI::_c121RailPrepTrigger()
{
  if (!(MODE_AIR && MODE_RAIL)) return false;
  if (!C121_CATALOG_FIRST_YEAR_ACTIVE) return false;
  if (this._railSearch != null) return false;
  /* Vivier AIR vide (-1) : la regeneration AIR passe d'abord, ce n'est pas un
   * manque d'argent. */
  if (this._c121RailPrepMinAirCap < 0) return false;
  if (this._c121RailPrepAirFundableCheap()) return false;
  return true;
}

function OpexAI::_c121RailPrepRememberStock()
{
  if (this._projects == null || this._railReadyStock == null) return;
  if ("railReadyStock" in this._projects) this._projects.railReadyStock = this._railReadyStock;
  else this._projects.railReadyStock <- this._railReadyStock;
}

/* Jette un trace du stock. Le candidat perd railPlan pour qu'un chantier
 * ulterieur (apres l'annee 1) relance un A* normal au lieu de reposer le trace. */
function OpexAI::_c121RailPrepDropStock(candidate, reason, ops, ticks)
{
  if (!(MODE_AIR && MODE_RAIL) || candidate == null) return;
  if (("kind" in candidate) && ("cargo" in candidate)
      && ("src" in candidate) && ("dst" in candidate)
      && this._railReadyStock != null) {
    local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
    if (pairKey in this._railReadyStock) delete this._railReadyStock[pairKey];
  }
  if ("railPlan" in candidate) candidate.railPlan = null;
  if ("c121PrepStock" in candidate) candidate.c121PrepStock = false;
  this._c121RailPrepRememberStock();
}

/* Debut de passe projects : un A* de preparation termine va au stock, jamais
 * a _consumeResumableRailAtPassStart. Si l'AIR redevient finançable, on gele
 * les tranches pour ne pas manger le tick avant la pose. */
function OpexAI::_c121RailPrepOnPassStart()
{
  if (!(MODE_AIR && MODE_RAIL)) return;
  if (!this._c121RailSearchIsPrep()) {
    if (this._c121RailPrepHold) this._c121RailPrepHold = false;
    return;
  }
  if (this._railSearch.phase == "build") {
    this._handleRailStockSearchCompleted();
    this._c121RailPrepHold = false;
    this._c121RailPrepYieldLogged = false;
    return;
  }
  if (this._railSearch.phase == "search" && C121_CATALOG_FIRST_YEAR_ACTIVE
      && this._c121RailPrepAirFundableCheap()) {
    this._c121RailPrepHold = true;
    if (!this._c121RailPrepYieldLogged) {
      this._c121RailPrepYieldLogged = true;
    }
    return;
  }
  if (this._c121RailPrepHold) {
    this._c121RailPrepHold = false;
    this._c121RailPrepYieldLogged = false;
  }
}

/* Fin de passe : le portefeuille AIR a deja eu la main. On ne demarre le rail
 * que si la condition 1 est encore vraie, donc jamais a la place d'une pose. */
function OpexAI::_c121RailPrepAfterProjectsPass()
{
  if (!(MODE_AIR && MODE_RAIL)) return;
  if (this._c121RailSearchIsPrep() && this._railSearch.phase == "build") {
    this._handleRailStockSearchCompleted();
  }
  if (!C121_CATALOG_FIRST_YEAR_ACTIVE) {
    if (this._c121RailPrepHold) this._c121RailPrepHold = false;
    return;
  }
  /* Stock plein et aucun A* de preparation en vol : ni scan, ni catalogue. */
  if (!this._c121RailSearchIsPrep() && this._railReadyStock != null
      && this._railReadyStock.len() >= C121_RAIL_PREP_MAX) return;
  local mark = OpexOpsMeasureBegin();
  local fundable = this._c121RailPrepAirFundable();
  local ops = OpexOpsMeasureEnd(mark);
  local ticks = AIController.GetTick() - mark.tick;
  if (fundable) {
    if (this._c121RailSearchIsPrep() && this._railSearch.phase == "search") {
      this._c121RailPrepHold = true;
      if (!this._c121RailPrepYieldLogged) {
        this._c121RailPrepYieldLogged = true;
      }
    }
    return;
  }
  if (this._railSearch != null) return;
  if (this._c121RailPrepMinAirCap < 0) return;
  this._c121RailPrepMaybeCatalog();
  this._tryStartC121RailPrepSearch();
}

function OpexAI::_c121RailPrepMaybeCatalog()
{
  if (!this._c121RailPrepTrigger()) return;
  if (this._catalog == null) return;
  local date = AIDate.GetCurrentDate();
  local stamp = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  if (this._c121RailPrepMonth == stamp && this._c121RailPrepCandidates != null) return;
  local mark = OpexOpsMeasureBegin();
  if (V276_CAND_SLICES > 0) {
    local published = OpexV276Published(this._catalog);
    this._c121RailPrepCandidates = published.best;
    /* Ne pas estampiller le mois : une unite peut publier dans le meme mois. */
    return;
  }
  /* P1 est cantonne a cette passe C121 deja planifiee. Le scan lit la meme
   * population fret ; aucun nouveau catalogue, ni A* et aucun candidat long
   * expose au classement papier. */
  local p1State = (P1_RAIL_LONG_VALUE_RANK > 0 && !V269_RELAXED)
      ? { best = null, observed = 0, scanned = 0, candidate = null } : null;
  local built = OpexBuildCandidates(this._catalog, this._budget, this._lines,
      this._abandonedPairs, null, null, null, null, null, true, true, PAX_BAND_ALL,
      null, null, -1, p1State);
  local ranked = null;
  if (built != null && ("best" in built) && built.best != null && built.best.len() > 0) {
    ranked = built.best;
  } else if (built != null && ("candidates" in built) && built.candidates != null) {
    ranked = built.candidates;
  } else {
    ranked = [];
  }
  if (p1State != null && p1State.candidate != null) {
    /* Une seule place prioritaire de preparation, PAS une place TopK ni une
     * election de construction : seul plan.ok permet l'entree au stock. */
    ranked = clone ranked;
    ranked.insert(0, p1State.candidate);
    if (DECISION_LOG) OpexDecide("P1_LONG_SELECT", "cargo=" + p1State.candidate.cargo
        + " src=" + p1State.candidate.src + " dst=" + p1State.candidate.dst
        + " dist=" + p1State.candidate.distance
        + " profit=" + p1State.candidate.profitAnnual
        + " capital=" + p1State.candidate.capital);
  }
  this._c121RailPrepCandidates = ranked;
  this._c121RailPrepMonth = stamp;
  local ops = OpexOpsMeasureEnd(mark);
  local ticks = AIController.GetTick() - mark.tick;
}

/* Vrai si ce candidat ne doit pas recevoir d'A* de preparation. */
function OpexC121RailPrepCandidateBlocked(ai, candidate, curDate)
{
  if (ai == null || candidate == null) return true;
  if (!(("kind" in candidate) && ("cargo" in candidate)
      && ("src" in candidate) && ("dst" in candidate))) return true;
  if (("mode" in candidate) && candidate.mode != "rail") return true;
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  if (ai._railReadyStock != null && (pairKey in ai._railReadyStock)) return true;
  if (ai._railStockCooldown != null && (pairKey in ai._railStockCooldown)) {
    if (curDate <= ai._railStockCooldown[pairKey]) return true;
    delete ai._railStockCooldown[pairKey];
  }
  if (ai._abandonedPairs != null) {
    local abndKey = OpexAbandonedPairKey(candidate);
    if (abndKey in ai._abandonedPairs) return true;
  }
  if (candidate.kind != "pax") {
    /* src/dst sont des tuiles (OpexMakeCandidate), pas des IndustryID. */
    if (!AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(candidate.src)) || !AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(candidate.dst))) return true;
  }
  return false;
}

/* Un seul A*, le meilleur candidat encore libre. */
function OpexAI::_tryStartC121RailPrepSearch()
{
  if (!(MODE_AIR && MODE_RAIL)) return false;
  if (!C121_CATALOG_FIRST_YEAR_ACTIVE) return false;
  if (this._railSearch != null) return false;
  if (this._activeWorker != null && this._activeWorker.kind != "rail_stock") {
    return false;
  }
  if (this._c121RailPrepAirFundableCheap()) return false;
  if (this._railReadyStock != null && this._railReadyStock.len() >= C121_RAIL_PREP_MAX) return false;
  local ranked = this._c121RailPrepCandidates;
  if (ranked == null || ranked.len() == 0) {
    return false;
  }
  local curDate = AIDate.GetCurrentDate();
  local limit = ranked.len();
  if (limit > TOP_K) limit = TOP_K;
  local mark = OpexOpsMeasureBegin();
  local started = false;
  for (local i = 0; i < limit; i++) {
    local candidate = ranked[i];
    if (OpexC121RailPrepCandidateBlocked(this, candidate, curDate)) continue;
    if (this._startRailStockSearch(candidate)) {
      if (this._railSearch != null) this._railSearch.isC121RailPrep <- true;
      this._c121RailPrepHold = false;
      this._c121RailPrepYieldLogged = false;
      started = true;
      break;
    }
    mark = OpexOpsMeasureBegin();
  }
  local ops = OpexOpsMeasureEnd(mark);
  local ticks = AIController.GetTick() - mark.tick;
  return started;
}
