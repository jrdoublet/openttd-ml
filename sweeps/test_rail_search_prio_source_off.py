"""Strict OFF source projection for SEARCH_PRIO phase 1 (frozen literal hunks).

Only these opt-in additions are removed; unrelated dirty code and historical
fixtures must stay unchanged. No git access or fixture regeneration at test time.
"""
import hashlib
import unittest
from pathlib import Path
from rail_config_merge_witness import FIXTURE as MERGED_RAIL_CONFIG, expected_off_sha

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"

# (active, pre-SEARCH-PRIO, number of occurrences)
OFF_EDITS = {'scheduler.nut': [('  /* ON seulement: un upgrade calcule ne depense pas avant la passe projects\n'
                    '   * si une nouvelle ligne rail reste finançable dans le portefeuille '
                    'courant.\n'
                    "   * Celle-ci annulera proprement l'upgrade APRES ses gardes habituelles. */\n"
                    '  if (RAIL_SEARCH_PRIO && OpexRailSearchPrioDeferUpgrade(this)) return;\n',
                    '',
                    1)],
 'task_rail.nut': [('/* RAIL-SEARCH-PRIO phase 1 : les champs et les decisions restent '
                    'strictement\n'
                    ' * opt-in. Aucun etat persistant : la recherche A* et son worker sont '
                    'transitoires. */\n'
                    'function OpexRailSearchPrioOwner(state)\n'
                    '{\n'
                    '  if (state == null) return "other";\n'
                    '  if (("isStockSearch" in state) && state.isStockSearch) return "stock";\n'
                    '  if (("kind" in state) && state.kind == "upgrade") return "upgrade";\n'
                    '  if (("kind" in state) && state.kind == "primary") return "project";\n'
                    '  return "other";\n'
                    '}\n'
                    '\n'
                    'function OpexRailSearchPrioFields(state)\n'
                    '{\n'
                    '  if (state == null) return "owner=other src=-1 dst=-1 days=0 ticks=0";\n'
                    '  local now = AIDate.GetCurrentDate();\n'
                    '  local ticks = AIController.GetTick();\n'
                    '  local days = ("startDate" in state) ? now - state.startDate : 0;\n'
                    '  local elapsed = ("startTick" in state) ? ticks - state.startTick : 0;\n'
                    '  local fields = "owner=" + OpexRailSearchPrioOwner(state)\n'
                    '      + " kind=" + (("kind" in state) ? state.kind : "-")\n'
                    '      + " phase=" + (("phase" in state) ? state.phase : "-")\n'
                    '      + " days=" + days + " ticks=" + elapsed;\n'
                    '  if (("candidate" in state) && state.candidate != null) {\n'
                    '    local c = state.candidate;\n'
                    '    fields += " src=" + (("src" in c) ? c.src : -1)\n'
                    '        + " dst=" + (("dst" in c) ? c.dst : -1)\n'
                    '        + " cargo=" + (("cargo" in c) ? c.cargo : -1)\n'
                    '        + " service=" + (("kind" in c) ? c.kind : "-");\n'
                    '  } else if (("line" in state) && state.line != null) {\n'
                    '    fields += " line=" + (("lineId" in state.line) ? state.line.lineId : '
                    '-1);\n'
                    '  } else {\n'
                    '    fields += " src=-1 dst=-1";\n'
                    '  }\n'
                    '  return fields;\n'
                    '}\n'
                    '\n'
                    'function OpexRailSearchPrioLog(state, event, detail = "")\n'
                    '{\n'
                    '  if (!RAIL_SEARCH_PRIO || !DECISION_LOG) return;\n'
                    '  OpexDecide("RAIL_SEARCH_PRIO", "event=" + event + " "\n'
                    '      + OpexRailSearchPrioFields(state) + (detail != "" ? " " + detail : '
                    '""));\n'
                    '}\n'
                    '\n'
                    '/* Ne jamais preempter une recherche de projet ou reparation. Un A*\n'
                    ' * stock portant sur le MEME projet est deja le calcul souhaite : le finir '
                    'plutot\n'
                    ' * que le recommencer. Le montant finance provient du meme estimateur que la\n'
                    ' * selection et ne remplace aucune garde physique/de caisse dans le builder. '
                    '*/\n'
                    'function OpexRailSearchPrioCanPreempt(ai, project)\n'
                    '{\n'
                    '  if (!RAIL_SEARCH_PRIO || ai == null || ai._railSearch == null\n'
                    '      || project == null || project.mode != "rail" || project.payload == '
                    'null\n'
                    '      || project.profitAnnual <= 0) return false;\n'
                    '  local state = ai._railSearch;\n'
                    '  local owner = OpexRailSearchPrioOwner(state);\n'
                    '  if (owner != "stock" && owner != "upgrade") return false;\n'
                    '  if (ai._activeWorker != null && ai._activeWorker.kind != "rail_stock"\n'
                    '      && ai._activeWorker.kind != "rail_search") return false;\n'
                    '  if (owner == "stock" && ai._activeWorker != null\n'
                    '      && ai._activeWorker.kind != "rail_stock") return false;\n'
                    '  if (owner == "upgrade" && ai._activeWorker != null\n'
                    '      && ai._activeWorker.kind == "rail_stock") return false;\n'
                    '  if (OpexProjectFinanceCapital(project) > OpexAvailableCapital()) return '
                    'false;\n'
                    '  if (owner == "stock") {\n'
                    '    if (!("candidate" in state) || state.candidate == null) return false;\n'
                    '    local old = state.candidate;\n'
                    '    local next = project.payload;\n'
                    '    if (old.src == next.src && old.dst == next.dst\n'
                    '        && old.kind == next.kind && old.cargo == next.cargo) return false;\n'
                    '  }\n'
                    '  return true;\n'
                    '}\n'
                    '\n'
                    '/* Annulation synchronisee : jamais _railSearch=null avec un worker encore\n'
                    ' * actif, ni worker rail_stock pointant un nouveau projet. Le stock deja '
                    'PRET\n'
                    " * (_railReadyStock) n'est pas efface : il sera revalide a son utilisation. "
                    '*/\n'
                    'function OpexRailSearchPrioPreemptStock(ai, project)\n'
                    '{\n'
                    '  if (!OpexRailSearchPrioCanPreempt(ai, project)) return false;\n'
                    '  local search = ai._railSearch;\n'
                    '  OpexRailSearchPrioLog(search, "preempt", "by_src=" + project.payload.src\n'
                    '      + " by_dst=" + project.payload.dst + " reason=funded_project");\n'
                    "  /* Le resultat d'un A* stock termine est precieux : le deposer dans le "
                    'ready\n'
                    '   * stock AVANT de liberer le worker, sans jetter ni construire ce plan. */\n'
                    '  if (OpexRailSearchPrioOwner(search) == "stock" && search.phase == "build") '
                    '{\n'
                    '    ai._handleRailStockSearchCompleted();\n'
                    '    if (ai._railSearch != null) return false;\n'
                    '  }\n'
                    '  if (ai._activeWorker != null) {\n'
                    '    local worker = ai._activeWorker;\n'
                    '    OpexWorkerCancel(worker);\n'
                    '    ai._activeWorker = null;\n'
                    '  }\n'
                    '  if (ai._railSearch == search) {\n'
                    '    if (("pathfinder" in search)) search.pathfinder = null;\n'
                    '    if (("segmented" in search)) search.segmented = null;\n'
                    '    ai._railSearch = null;\n'
                    '  }\n'
                    '  ai._c121RailPrepHold = false;\n'
                    '  ai._c121RailPrepYieldLogged = false;\n'
                    '  return ai._railSearch == null && ai._activeWorker == null;\n'
                    '}\n'
                    '\n'
                    "/* L'upgrade termine ne doit pas consommer la caisse AVANT que le passage\n"
                    ' * projets ait pu donner sa chance a une nouvelle ligne rail deja '
                    'financable.\n'
                    ' * Aucun calcul de classement neuf : lecture seule de la selection existante. '
                    '*/\n'
                    'function OpexRailSearchPrioDeferUpgrade(ai)\n'
                    '{\n'
                    '  if (!RAIL_SEARCH_PRIO || ai == null || ai._railSearch == null\n'
                    '      || ai._railSearch.kind != "upgrade" || ai._railSearch.phase != "build"\n'
                    '      || ai._projects == null) return false;\n'
                    '  /* V158: ce lecteur peut etre appele avant la passe projects. Materialiser\n'
                    '   * la selection paresseuse seulement sous ON, avant de lire best. */\n'
                    '  ai._ensureSelection();\n'
                    '  if (ai._projects == null || ai._projects.best == null) return false;\n'
                    '  foreach (project in ai._projects.best) {\n'
                    '    if (project != null && project.mode == "rail"\n'
                    '        && OpexRailSearchPrioCanPreempt(ai, project)) return true;\n'
                    '  }\n'
                    '  return false;\n'
                    '}\n'
                    '\n',
                    '',
                    1),
                   ("      /* Le projet finançable peut prendre la place d'un stock/upgrade "
                    'secondaire,\n'
                    '       * MAIS seulement APRES les gardes abandon/slot/proximite/caisse '
                    'ci-dessous.\n'
                    "       * La recherche primaire deja elue n'est jamais preemptee. */\n"
                    '      local prioPreempt = RAIL_SEARCH_PRIO && searchBlocked\n'
                    '          && OpexRailSearchPrioCanPreempt(this, project);\n'
                    '      if (searchBlocked && !c121PrepPlan && !prioPreempt) {\n',
                    '      if (searchBlocked && !c121PrepPlan) {\n',
                    1),
                   ('        if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(this._railSearch, '
                    '"blocked", "rank=" + i\n'
                    '            + " wanted_src=" + candidate.src + " wanted_dst=" + '
                    'candidate.dst);\n'
                    '        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) '
                    'passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = '
                    'candidate.dst, reason = "search_in_progress", extra = RAIL_SEARCH_PRIO ? '
                    'OpexRailSearchPrioFields(this._railSearch) : "" });\n',
                    '        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) '
                    'passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = '
                    'candidate.dst, reason = "search_in_progress", extra = "" });\n',
                    1),
                   ('                                    reason = "search_in_progress", extra = '
                    'RAIL_SEARCH_PRIO\n'
                    '                                        ? "prep_dropped " + '
                    'OpexRailSearchPrioFields(this._railSearch)\n'
                    '                                        : "prep_dropped" });\n'
                    '            if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(this._railSearch, '
                    '"blocked", "rank=" + i\n'
                    '                + " wanted_src=" + candidate.src + " wanted_dst=" + '
                    'candidate.dst\n'
                    '                + " reason=prep_dropped");\n',
                    '                                    reason = "search_in_progress", extra = '
                    '"prep_dropped" });\n',
                    1),
                   ('        return { outcome = "rejected", discards = passDiscards };\n'
                    '      }\n'
                    '\n'
                    '      if (prioPreempt && !OpexRailSearchPrioPreemptStock(this, project)) {\n'
                    "        /* La carte n'est pas modifiee, la garde d'abandon/de caisse "
                    'ci-dessus a\n'
                    '         * deja tourne. Ne jamais ecraser un worker non reconnu. */\n'
                    '        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)\n'
                    '          passDiscards.append({ rank = i, mode = "rail", src = candidate.src, '
                    'dst = candidate.dst,\n'
                    '                                reason = "search_in_progress", extra = '
                    'RAIL_SEARCH_PRIO\n'
                    '                                    ? "preempt_refused " + '
                    'OpexRailSearchPrioFields(this._railSearch)\n'
                    '                                    : "preempt_refused" });\n',
                    '',
                    1),
                   ("  /* ON: un upgrade ne peut plus ecraser l'A* prioritaire d'un projet ou\n"
                    "   * le calcul d'un stock. OFF: conserver EXACTEMENT l'exception V190. */\n"
                    '  if (this._railSearch != null && (RAIL_SEARCH_PRIO || !OpexV190Active())) '
                    'return;\n',
                    '  if (this._railSearch != null && !OpexV190Active()) return;\n',
                    1),
                   ('        OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 '
                    'budget=" + plan.iterationBudget\n'
                    '            + (RAIL_SEARCH_PRIO ? " owner=project src=" + candidate.src + " '
                    'dst=" + candidate.dst\n'
                    '                + " days=0 ticks=0" : ""));\n',
                    '        OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 '
                    'budget=" + plan.iterationBudget);\n',
                    2),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(this._railSearch, "start", '
                    '"source=projects");\n',
                    '',
                    1),
                   ('    OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " '
                    'iters=" + state.spent + " budget=" + state.iterationBudget\n'
                    '        + (RAIL_SEARCH_PRIO ? " " + OpexRailSearchPrioFields(state) : ""));\n',
                    '    OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " '
                    'iters=" + state.spent + " budget=" + state.iterationBudget);\n',
                    1),
                   ('\n'
                    '  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(state, "end", "outcome=" + '
                    'slice.stop\n'
                    '      + " iters=" + state.spent);\n',
                    '',
                    1),
                   ('      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable '
                    'outcome=NOPA iters=0 budget=" + prep.iterationBudget\n'
                    '          + (RAIL_SEARCH_PRIO ? " owner=upgrade line=" + line.lineId + " '
                    'days=0 ticks=0" : ""));\n',
                    '      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable '
                    'outcome=NOPA iters=0 budget=" + prep.iterationBudget);\n',
                    2),
                   ('  if (RAIL_SEARCH_PRIO) {\n'
                    '    this._railSearch.startDate <- AIDate.GetCurrentDate();\n'
                    '    this._railSearch.startTick <- AIController.GetTick();\n'
                    '    OpexRailSearchPrioLog(this._railSearch, "start", "source=expand");\n'
                    '  }\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(this._railSearch, "start", '
                    '"source=stock");\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(state, "end", '
                    '"outcome=stock_timeout");\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(state, "stock_complete", '
                    '"result=deposit_or_cooldown");\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) {\n'
                    '    this._railSearch.startDate <- AIDate.GetCurrentDate();\n'
                    '    OpexRailSearchPrioLog(this._railSearch, "start", "source=repair");\n'
                    '  }\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(state, "end", '
                    '"outcome=repair_fail reason=" + why);\n',
                    '',
                    1),
                   ('  if (RAIL_SEARCH_PRIO) OpexRailSearchPrioLog(state, "end", '
                    '"outcome=repair_ok");\n',
                    '',
                    1)]}

def off_search_prio_source(name, source):
    """Idempotent, fail-closed removal of the known opt-in source hunks."""
    # A second projection on the frozen merge OFF witness must be a no-op.
    # Without this exact digest check, the older DOUBLE-GROW projector is
    # asked to reproject INVEST-STALL's already-removed platform source and
    # rejects its unfamiliar intermediate SHA. Unknown bytes still traverse
    # the strict original projector and fail closed.
    digest = hashlib.sha256(source.encode("utf8")).hexdigest()
    already_off = {
        FROZEN_OFF_SHA256.get(name),
        MERGED_RAIL_CONFIG["rail_search_prio_source_off"].get(name),
    }
    if digest in already_off and name in FROZEN_OFF_SHA256:
        if any(token in source for token in ("RAIL_SEARCH_PRIO", "OpexRailSearchPrio", "prioPreempt")):
            raise AssertionError(f"RAIL_SEARCH_PRIO {name}: OFF witness contains active signature")
        return source
    from double_grow_off import off_source as double_grow_off
    source = double_grow_off(name, source)
    from rail_long_source_off import off_source as rail_long_off
    if name == "scheduler.nut" and "INVEST_STALL" in source:
        from invest_stall_source_off import project_off as invest_stall_off
        source = invest_stall_off(name, source)
    source = rail_long_off(name, source)
    if name not in OFF_EDITS:
        return source
    signatures = ("RAIL_SEARCH_PRIO", "OpexRailSearchPrio", "prioPreempt")
    if not any(s in source for s in signatures):
        return source
    for active, prior, count in sorted(OFF_EDITS[name],key=lambda r:-len(r[0])):
        observed=source.count(active)
        if observed != count:
            raise AssertionError(
                f"RAIL_SEARCH_PRIO {name}: partial/changed hunk "
                f"expected {count}, observed {observed}: {active[:64]!r}")
        source=source.replace(active,prior)
    if any(s in source for s in signatures):
        raise AssertionError(f"RAIL_SEARCH_PRIO {name}: unprojected source")
    return source

# Independent dirty edits remain inside these frozen pre-PRIO snapshots.
FROZEN_OFF_SHA256 = {'scheduler.nut': '3ae35a91f352fce67c7923ecc5223ee000dbb9c066c6f7a5435049e2ee10cb18',
 'task_rail.nut': 'd9f29ba17b0998810559400bb190dfe848b9fb87f954bf88a6725a43b9c461ca'}

class TestRailSearchPrioSourceOffProjection(unittest.TestCase):
    def test_on_materializes_lazy_selection_before_best_reader(self):
        rail = (AI / "task_rail.nut").read_text(encoding="utf8")
        start = rail.index("function OpexRailSearchPrioDeferUpgrade(ai)")
        body = rail[start:rail.index("\n}\n", start)]
        self.assertLess(body.index("if (!RAIL_SEARCH_PRIO"),
                        body.index("ai._ensureSelection();"))
        self.assertLess(body.index("ai._ensureSelection();"),
                        body.index("foreach (project in ai._projects.best)"))

    def test_frozen_off_and_idempotence(self):
        for name, digest in FROZEN_OFF_SHA256.items():
            with self.subTest(name=name):
                original=(AI/name).read_text(encoding="utf8")
                projected=off_search_prio_source(name,original)
                self.assertNotEqual(original,projected)
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(),
                                 expected_off_sha(name, "rail_search_prio_source_off", digest, original))
                self.assertEqual(off_search_prio_source(name,projected),projected)
                self.assertNotIn("RAIL_SEARCH_PRIO",projected)

    def test_partial_hunks_fail_closed(self):
        for name, edits in OFF_EDITS.items():
            with self.subTest(name=name):
                original=(AI/name).read_text(encoding="utf8")
                fragment=edits[0][0]
                corrupted=original.replace(fragment,fragment.replace(fragment[:12],"BROKEN",1),1)
                with self.assertRaises(AssertionError):
                    off_search_prio_source(name,corrupted)
