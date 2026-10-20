/* V294h : recherche rail en deux temps (idee utilisateur du 20/10).
 * Le creneau unique ne tente qu'un trace rapide (V294H_RAIL_DEFER iterations). S'il
 * s'arrete en ABND, l'etat segmente n'est pas jete : il passe dans une file de fond
 * avancee seulement sur le reliquat du tick (apres V89, avant Sleep(1)), avec un budget
 * plus large. Un trace trouve en fond est rattache au candidat de la meme paire quand le
 * portefeuille le represente ; un echec de fond marque la paire abandonnee comme un ABND.
 * Etat transitoire, jamais sauve (comme _railReadyStock). Aucune closure. */

/* Budget total de la recherche de fond : 4 plafonds durs (le creneau principal n'y perd
 * rien, seul le reliquat paie). Litteral : const n'accepte qu'un scalaire. */
const V294H_BG_BUDGET = 20000;
/* Recherches differees au plus ; au-dela, l'ABND rapide reste un ABND. */
const V294H_QUEUE_MAX = 3;
/* Duree de vie d'une recherche de fond et d'un trace pret, en jours de jeu. */
const V294H_BG_MAX_DAYS = 365;
const V294H_READY_TTL_DAYS = 180;
/* Opcodes gardes en reserve sous la suspension, et plus petite tranche utile. */
const V294H_OPS_MARGIN = 800;
const V294H_MIN_SLICE_ITERS = 5;

function OpexV294hPairKey(candidate)
{
  return OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
}

function OpexV294hLog(event, fields)
{
  if (DECISION_LOG) OpexDecide("V294H", "event=" + event + " " + fields);
}

/* Budget du trace rapide : jamais au-dessus du budget du plan. */
function OpexV294hQuickBudget(planBudget)
{
  if (V294H_RAIL_DEFER <= 0) return planBudget;
  return (planBudget > V294H_RAIL_DEFER) ? V294H_RAIL_DEFER : planBudget;
}

function OpexV294hIsDeferred(owner, pairKey)
{
  if (owner._v294Deferred == null) return false;
  foreach (entry in owner._v294Deferred) {
    if (entry.pairKey == pairKey) return true;
  }
  return false;
}

/* Appele quand une recherche primaire s'arrete en ABND. Retourne true si la recherche
 * part en fond : le plan principal porte alors le motif DEFER (non abandonne). */
function OpexV294hTryDefer(owner, state, slice, plan)
{
  if (V294H_RAIL_DEFER <= 0 || slice.stop != "ABND") return false;
  if (!("segmented" in state) || state.segmented == null) return false;
  if (("isStockSearch" in state) && state.isStockSearch) return false;
  if (owner._v294Deferred == null) owner._v294Deferred = [];
  local candidate = state.candidate;
  local pairKey = OpexV294hPairKey(candidate);
  if (owner._v294Deferred.len() >= V294H_QUEUE_MAX || OpexV294hIsDeferred(owner, pairKey)) {
    OpexV294hLog("full", "src=" + candidate.src + " dst=" + candidate.dst + " queue=" + owner._v294Deferred.len());
    return false;
  }
  local seg = state.segmented;
  if (seg.iterations >= V294H_BG_BUDGET) return false;
  seg.iterationBudget = V294H_BG_BUDGET;
  seg.timeSafe = (SEGMENTED_TIME_SAFE_ITERS < V294H_BG_BUDGET) ? SEGMENTED_TIME_SAFE_ITERS : V294H_BG_BUDGET;
  owner._v294Deferred.push({
    pairKey = pairKey,
    candidate = candidate,
    plan = clone plan,
    segmented = seg,
    quickIters = seg.iterations,
    slices = 0,
    calls = 0,
    starved = 0,
    lastLog = AIDate.GetCurrentDate(),
    startDate = AIDate.GetCurrentDate(),
  });
  plan.reason = "DEFER";
  OpexV294hLog("defer", "src=" + candidate.src + " dst=" + candidate.dst + " manh=" + candidate.distance
               + " quick_iters=" + seg.iterations + " queue=" + owner._v294Deferred.len());
  return true;
}

/* Fin de boucle, une tranche par passage. Une iteration A* coute ~1 500 opcodes (mediane
 * 1 615 sur 115 tentatives des smokes du 20/10), une tranche de 50 environ 7 ticks : le seuil
 * V89 n'est jamais atteint en fin de boucle (652 passages sur 653 sans tranche, ~6 k opcodes
 * restants, ~2 a 5 passages par jour). V294H_OPS_PER_ITER part de 200 et n'est mis a jour
 * que sans suspension : il reste en pratique a 200, d'ou ~30 iterations par passage, soit
 * ~7 % du temps du script quand la file est non vide. Ce n'est PAS un pur reliquat : un
 * reliquat strict donnerait ~3 iterations par passage et rendrait la file inerte. */
function OpexV294hAdvance(owner)
{
  if (V294H_RAIL_DEFER <= 0 || owner._v294Deferred == null || owner._v294Deferred.len() == 0) return 0;
  local tick = AIController.GetTick();
  local slices = 0;
  local head = owner._v294Deferred[0];
  head.calls++;
  if (DECISION_LOG && AIDate.GetCurrentDate() - head.lastLog >= 30) {
    head.lastLog = AIDate.GetCurrentDate();
    OpexV294hLog("progress", "src=" + head.candidate.src + " dst=" + head.candidate.dst
                 + " iters=" + head.segmented.iterations + " slices=" + head.slices + " calls=" + head.calls
                 + " starved=" + head.starved + " ops=" + AIController.GetOpsTillSuspend()
                 + " per_iter=" + V294H_OPS_PER_ITER);
  }
  while (owner._v294Deferred.len() > 0 && AIController.GetTick() == tick) {
    local opsBefore = AIController.GetOpsTillSuspend();
    local iters = (opsBefore - V294H_OPS_MARGIN) / V294H_OPS_PER_ITER;
    if (iters < V294H_MIN_SLICE_ITERS) {
      if (slices == 0) head.starved++;
      break;
    }
    if (iters > RAIL_SEARCH_SLICE) iters = RAIL_SEARCH_SLICE;
    local entry = owner._v294Deferred[0];
    local now = AIDate.GetCurrentDate();
    if (now - entry.startDate > V294H_BG_MAX_DAYS) {
      OpexV294hFinish(owner, entry, null, "TIMEOUT");
      continue;
    }
    local deadlineTick = tick + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;
    local itersBefore = entry.segmented.iterations;
    local slice = OpexAdvanceSegmentedSearch(entry.segmented, iters, deadlineTick);
    local spent = entry.segmented.iterations - itersBefore;
    /* Mesure seulement dans le meme tick : une suspension remet le compteur a neuf. */
    if (spent > 0 && AIController.GetTick() == tick) {
      local perIter = (opsBefore - AIController.GetOpsTillSuspend()) / spent;
      if (perIter > 0) V294H_OPS_PER_ITER = (3 * V294H_OPS_PER_ITER + perIter) / 4;
    }
    slices++;
    entry.slices++;
    if (slice.done) OpexV294hFinish(owner, entry, slice, slice.stop);
    else if (spent == 0) break;
  }
  return slices;
}

function OpexV294hFinish(owner, entry, slice, stop)
{
  /* Pas de array.find dans le Squirrel d'OpenTTD (smoke du 20/10 : « the index 'find' does not exist »). */
  for (local i = 0; i < owner._v294Deferred.len(); i++) {
    if (owner._v294Deferred[i] == entry) {
      owner._v294Deferred.remove(i);
      break;
    }
  }
  local candidate = entry.candidate;
  local now = AIDate.GetCurrentDate();
  local iters = entry.segmented.iterations;
  entry.segmented = null;
  local ok = false;
  if (slice != null && stop == "OK") {
    local plan = OpexCompleteRailRouteAfterSearch(owner._catalog, candidate, entry.plan, slice);
    if (plan.ok) {
      if (owner._v294Ready == null) owner._v294Ready = {};
      owner._v294Ready[entry.pairKey] <- { plan = plan, date = now };
      ok = true;
    } else {
      stop = plan.reason;
    }
  }
  OpexV294hLog(ok ? "found" : "fail", "src=" + candidate.src + " dst=" + candidate.dst
               + " manh=" + candidate.distance + " stop=" + stop + " quick_iters=" + entry.quickIters
               + " iters=" + iters + " slices=" + entry.slices + " days=" + (now - entry.startDate));
  if (!ok) owner._markPairAbandoned(OpexAbandonedPairKey(candidate));
}

/* Avant de lancer un A* : une paire encore en fond est refusee ; un trace pret encore frais
 * est rattache au candidat. Il reste en table jusqu'a la tentative de pose
 * (OpexV294hConsumed) : un refus de tresorerie avant la pose ne le perd pas. */
function OpexV294hBeforeSearch(owner, candidate)
{
  if (V294H_RAIL_DEFER <= 0) return { blocked = false, attached = false };
  local pairKey = OpexV294hPairKey(candidate);
  if (OpexV294hIsDeferred(owner, pairKey)) return { blocked = true, attached = false };
  if (owner._v294Ready == null || !(pairKey in owner._v294Ready)) return { blocked = false, attached = false };
  local ready = owner._v294Ready[pairKey];
  if (AIDate.GetCurrentDate() - ready.date > V294H_READY_TTL_DAYS) {
    delete owner._v294Ready[pairKey];
    OpexV294hLog("expired", "src=" + candidate.src + " dst=" + candidate.dst);
    return { blocked = false, attached = false };
  }
  if (("railPlan" in candidate) && candidate.railPlan != null) return { blocked = false, attached = false };
  if (!("railPlan" in candidate)) candidate.railPlan <- ready.plan;
  else candidate.railPlan = ready.plan;
  OpexV294hLog("attach", "src=" + candidate.src + " dst=" + candidate.dst);
  return { blocked = false, attached = true };
}

/* Apres OpexBuildLine sur un trace rattache : reussi ou non, il ne sert plus. */
function OpexV294hConsumed(owner, candidate, result)
{
  local pairKey = OpexV294hPairKey(candidate);
  if (owner._v294Ready != null && (pairKey in owner._v294Ready)) delete owner._v294Ready[pairKey];
  OpexV294hLog("built", "src=" + candidate.src + " dst=" + candidate.dst
               + " ok=" + (result.ok ? 1 : 0) + " reason=" + (result.reason == "" ? "-" : result.reason));
}
