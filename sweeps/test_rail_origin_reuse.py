#!/usr/bin/env python3
"""Contrats du relachement d'exclusivite d'origine dans la generation rail."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:pos]
    raise AssertionError(f"corps non ferme: {signature}")


def blocked(origin_reuse, a_served, b_served):
    """Modele de verite du petit predicat Squirrel teste statiquement ci-dessous."""
    if origin_reuse:
        return a_served and b_served
    return a_served or b_served


class TestRailOriginReuse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = source("candidates.nut")
        cls.builder = source("builder_rail.nut")
        cls.task_rail = source("task_rail.nut")
        cls.task_projects = source("task_projects.nut")
        cls.projects = source("projects_generation.nut")
        cls.projects_full = source("projects.nut")
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")

    def test_setting_is_dedicated_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_reuse"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("RAIL_ORIGIN_REUSE <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE = AIController.GetSetting("rail_origin_reuse") != 0;',
            self.settings,
        )

    def test_origin_exposure_shadow_is_independent_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_exposure_shadow"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_EXPOSURE_SHADOW <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_EXPOSURE_SHADOW = AIController.GetSetting("rail_origin_exposure_shadow") != 0;',
            self.settings,
        )
        self.assertNotIn("RAIL_ORIGIN_REUSE && AIController.GetSetting", self.settings[
            self.settings.index('RAIL_ORIGIN_EXPOSURE_SHADOW ='):self.settings.index(
                'RAIL_ORIGIN_REUSE_FALLBACK ='
            )
        ])

    def test_origin_exposure_detail_shadow_is_parent_scoped_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_exposure_detail_shadow"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_EXPOSURE_DETAIL_SHADOW <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_EXPOSURE_DETAIL_SHADOW = RAIL_ORIGIN_EXPOSURE_SHADOW\n'
            '      && AIController.GetSetting("rail_origin_exposure_detail_shadow") != 0;',
            self.settings,
        )

    def test_fallback_setting_is_off_by_default(self):
        start = self.info.index('name = "rail_origin_reuse_fallback"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_REUSE_FALLBACK <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE_FALLBACK = AIController.GetSetting("rail_origin_reuse_fallback") != 0;',
            self.settings,
        )

    def test_kind_subswitches_reproduce_parent_candidate_by_default(self):
        for setting, symbol in (
            ("rail_origin_reuse_pax", "RAIL_ORIGIN_REUSE_PAX"),
            ("rail_origin_reuse_freight", "RAIL_ORIGIN_REUSE_FREIGHT"),
        ):
            start = self.info.index(f'name = "{setting}"')
            block = self.info[start:self.info.index("});", start)]
            for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertIn(f"{name} = 1", block)
            self.assertIn(f"{symbol} <- true;", self.globals)
            self.assertIn(
                f'{symbol} = AIController.GetSetting("{setting}") != 0;',
                self.settings,
            )

    def test_multiline_match_is_parent_scoped_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_reuse_multiline_match"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_REUSE_MULTILINE_MATCH <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE_MULTILINE_MATCH = RAIL_ORIGIN_REUSE\n'
            '      && AIController.GetSetting("rail_origin_reuse_multiline_match") != 0;',
            self.settings,
        )

    def test_multiline_match_resolves_compatible_service_without_relaxing_station_identity(self):
        origin = function_body(self.candidates, "function OpexOriginService(lines, tile)")
        self.assertIn("if (found.stationId != stationId)", origin)
        self.assertIn("blocked = true", origin)
        self.assertIn("found.sameStationServices <- [service];", origin)
        self.assertIn("found.sameStationServices.append(service);", origin)
        resolver = function_body(
            self.candidates,
            "function OpexRailOriginCompatibleService(service, kind, cargo, candidateEnd)",
        )
        self.assertIn("if (RAIL_ORIGIN_REUSE_MULTILINE_MATCH", resolver)
        self.assertIn("line.kind != kind", resolver)
        self.assertIn('local sameCargo = ("cargo" in line) && line.cargo == cargo;', resolver)
        self.assertIn("!sameCargo && !RAIL_ORIGIN_REUSE_CROSS_CARGO", resolver)
        self.assertIn('kind == "freight" && sameCargo && candidateEnd != choice.lineEnd', resolver)
        self.assertIn("return choice;", resolver)

    def test_cross_cargo_reuse_is_parent_scoped_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_reuse_cross_cargo"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_REUSE_CROSS_CARGO <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE_CROSS_CARGO = RAIL_ORIGIN_REUSE\n'
            '      && AIController.GetSetting("rail_origin_reuse_cross_cargo") != 0;',
            self.settings,
        )

    def test_cross_cargo_relaxes_only_cargo_and_only_old_role(self):
        resolver = function_body(
            self.candidates,
            "function OpexRailOriginCompatibleService(service, kind, cargo, candidateEnd)",
        )
        self.assertIn('if (!("kind" in line) || line.kind != kind) continue;', resolver)
        self.assertIn('if (!sameCargo && !RAIL_ORIGIN_REUSE_CROSS_CARGO) continue;', resolver)
        self.assertIn(
            'if (kind == "freight" && sameCargo && candidateEnd != choice.lineEnd) continue;',
            resolver,
        )
        reason = function_body(
            self.candidates,
            "function OpexRailOriginServiceJoinReason(service, kind, cargo, candidateEnd)",
        )
        self.assertIn('if (!sameCargo && !RAIL_ORIGIN_REUSE_CROSS_CARGO)', reason)
        self.assertIn(
            'if (kind == "freight" && sameCargo && candidateEnd != choice.lineEnd) continue;',
            reason,
        )

    def test_multiline_match_annotation_reaches_decision_log(self):
        attach = function_body(
            self.candidates, "function OpexRailAttachOriginReuse(candidate, sa, sb)"
        )
        self.assertIn("local matchedService = OpexRailOriginCompatibleService", attach)
        matched = function_body(
            self.candidates, "function OpexRailAttachMatchedOriginReuse(candidate, sa, sb, matchedService)"
        )
        self.assertIn("candidate.joinMatchedAlternate <- RAIL_ORIGIN_REUSE_MULTILINE_MATCH", matched)
        self.assertIn('" reuse_alt=" + ((("joinMatchedAlternate" in candidate)', self.task_rail)

    def test_air_priority_settings_are_parent_scoped_and_off_by_default(self):
        for setting, symbol in (
            ("rail_origin_reuse_air_priority_shadow", "RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW"),
            ("rail_origin_reuse_air_priority", "RAIL_ORIGIN_REUSE_AIR_PRIORITY"),
        ):
            start = self.info.index(f'name = "{setting}"')
            block = self.info[start:self.info.index("});", start)]
            for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertIn(f"{name} = 0", block)
            self.assertIn(f"{symbol} <- false;", self.globals)
            self.assertIn(
                f'{symbol} = RAIL_ORIGIN_REUSE\n      && AIController.GetSetting("{setting}") != 0;',
                self.settings,
            )

    def test_origin_reuse_search_cap_is_parent_scoped_and_off_by_default(self):
        start = self.info.index('name = "rail_origin_reuse_search_cap_k"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 0, max_value = 100", block)
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{name} = 0", block)
        self.assertIn("RAIL_ORIGIN_REUSE_SEARCH_CAP <- 0;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE_SEARCH_CAP = RAIL_ORIGIN_REUSE\n'
            '      ? AIController.GetSetting("rail_origin_reuse_search_cap_k") * 1000 : 0;',
            self.settings,
        )

    def test_origin_reuse_search_cap_changes_only_origin_served_candidates(self):
        helper = function_body(
            self.builder, "function OpexRailCandidateHardCap(candidate, baseCap)"
        )
        self.assertIn("RAIL_ORIGIN_REUSE_SEARCH_CAP <= baseCap", helper)
        self.assertIn('!("originServed" in candidate) || !candidate.originServed', helper)
        self.assertIn("return RAIL_ORIGIN_REUSE_SEARCH_CAP;", helper)

        # Tous les chemins primaires qui calculent un hardCap passent par le meme garde.
        self.assertGreaterEqual(self.task_rail.count("OpexRailCandidateHardCap("), 4)
        self.assertIn(
            "OpexRailCandidateHardCap(candidate,\n          OpexDynamicHardCap(this._lines.len(), lowCash))",
            self.task_rail,
        )

    def test_segmented_final_tail_cannot_reenter_existing_prefix(self):
        body = function_body(self.builder, "function OpexAdvanceSegmentedSearch(")
        final = body.index("if (path != false && path != null)")
        cut = body.index("if (path == null)", final)
        block = body[final:cut]
        self.assertIn("local tail = OpexSegmentTiles(path);", block)
        self.assertIn("state.prefix != null && !OpexCanAppendSegment(state.prefix, tail)", block)
        self.assertIn("if (OpexTrySegmentedBacktrack(state)) continue;", block)
        self.assertIn('return OpexSegmentedResult(state, null, "NOPA", true);', block)
        self.assertLess(
            block.index("!OpexCanAppendSegment(state.prefix, tail)"),
            block.index("state.prefix.push(tail[i])"),
        )

    def test_segmented_search_blocks_planned_prefix_before_each_new_astar(self):
        append = function_body(self.builder, "function OpexCanAppendSegment(prefix, tail)")
        self.assertIn("for (local i = 0; i < prefix.len(); i++) seen[prefix[i]] <- true;", append)
        self.assertIn("seen[tail[i]] <- true;", append)

        ignored = function_body(self.builder, "function OpexSegmentIgnoredTiles(state)")
        self.assertIn("foreach (tile in state.ignoredTiles)", ignored)
        self.assertIn("local limit = state.prefix.len() - 2;", ignored)
        self.assertIn("for (local i = 0; i < limit; i++)", ignored)

        advance = function_body(self.builder, "function OpexAdvanceSegmentedSearch(")
        self.assertIn("local ignored = OpexSegmentIgnoredTiles(state);", advance)
        self.assertIn("pathfinder.InitializePath(state.activeSources, state.goals, ignored);", advance)
        self.assertIn("if (!OpexSegmentPrefixContains(state.prefix, choice.to))", advance)
        self.assertIn("nonLoopChoices[0].to", advance)

    def test_air_priority_detects_only_direct_capital_displacement(self):
        body = function_body(
            self.task_projects,
            "function OpexRailOriginReuseAirOpportunity(projects, project, rank, lines)",
        )
        self.assertIn('project.mode != "rail"', body)
        self.assertIn('("originServed" in project.payload)', body)
        self.assertIn("local available = OpexAvailableCapital();", body)
        self.assertIn("local railCap = OpexProjectFinanceCapital(project);", body)
        self.assertIn('next.mode != "air"', body)
        self.assertIn("!OpexAirBatchPlanStillLive(next.payload, lines)", body)
        self.assertIn("airFundableNow = airCap <= available", body)
        self.assertIn(
            "displaced = railCap <= available && airCap <= available && railCap + airCap > available",
            body,
        )

    def test_air_priority_shadow_has_opcode_parity_until_real_defer(self):
        loop = self.task_projects[self.task_projects.index("for (local i = 0; i < this._projects.best.len(); i++)"):]
        self.assertIn(
            "if ((RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW || RAIL_ORIGIN_REUSE_AIR_PRIORITY)",
            loop,
        )
        self.assertIn("OpexRailOriginReuseAirOpportunity(this._projects, project, i, this._lines)", loop)
        self.assertIn("railReuseAirOpp.nextRank == i + 1 && builtCount == 0", loop)
        self.assertIn("if (railReuseAirShouldDefer && RAIL_ORIGIN_REUSE_AIR_PRIORITY)", loop)
        self.assertIn('reason = "rail_origin_reuse_air_priority"', loop)
        self.assertIn("RAIL_ORIGIN_REUSE_AIR_PRIORITY_DEFER", loop)

    def test_off_keeps_historical_or_and_on_uses_both_served(self):
        helper = function_body(self.candidates, "function OpexRailOriginPairBlocked(sa, sb)")
        self.assertIn("if (RAIL_ORIGIN_REUSE) return sa != null && sb != null;", helper)
        self.assertIn("return sa != null || sb != null;", helper)

        # OFF : une seule extremite servie suffit toujours a bloquer.
        self.assertTrue(blocked(False, True, False))
        self.assertTrue(blocked(False, False, True))
        # ON : exactement une extremite servie reste generable, deux restent refusees.
        self.assertFalse(blocked(True, True, False))
        self.assertFalse(blocked(True, False, True))
        self.assertTrue(blocked(True, True, True))
        self.assertFalse(blocked(True, False, False))

    def test_pax_fresh_pass_is_historical_and_never_reads_reuse_policy(self):
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        self.assertIn("local sa = served[a];", pax)
        self.assertIn("local sb = served[b];", pax)
        guard = pax.index("if (sa != null || sb != null)")
        rejection = pax.index("stats.pairsOriginServed++;", guard)
        continuation = pax.index("continue;", rejection)
        self.assertLess(guard, rejection)
        self.assertLess(rejection, continuation)
        self.assertNotIn("RAIL_ORIGIN_REUSE", pax)
        self.assertNotIn("allowOneServed", pax)
        self.assertNotIn("deferOriginReuse", pax)
        self.assertIn("OpexRailAttachOriginReuse(candidate, sa, sb);", pax)

    def test_freight_industry_fresh_pass_is_historical_and_never_reads_reuse_policy(self):
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertIn("local sd = served[di];", freight)
        guard = freight.index("if (ss != null || sd != null)")
        rejection = freight.index("stats.pairsOriginServed++;", guard)
        self.assertLess(guard, rejection)
        self.assertNotIn("RAIL_ORIGIN_REUSE", freight)
        self.assertIn("OpexRailAttachOriginReuse(candidate, ss, sd);", freight)

    def test_freight_town_fresh_pass_is_historical_and_never_reads_reuse_policy(self):
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertIn("st = OpexOriginService(lines, town.tile);", freight)
        guard = freight.index("if (ss != null || st != null)")
        rejection = freight.index("stats.pairsOriginServed++;", guard)
        self.assertLess(guard, rejection)
        self.assertNotIn("RAIL_ORIGIN_REUSE", freight)
        self.assertIn("OpexRailAttachOriginReuse(candidate, ss, st);", freight)

    def test_rail_revalidation_already_rejects_only_both_served(self):
        body = function_body(self.projects, "function OpexCandidateStillValid(")
        rail = body[body.index('if (mode == "rail")'):]
        self.assertIn(
            "if (OpexOriginServed(lines, p.src, false) && OpexOriginServed(lines, p.dst, false))",
            rail,
        )

    def test_reused_endpoint_requires_unambiguous_persisted_join_geometry(self):
        resolver = function_body(
            self.candidates,
            "function OpexRailOriginCompatibleService(service, kind, cargo, candidateEnd)",
        )
        self.assertIn('if (("blocked" in service) && service.blocked) return null;', resolver)
        self.assertIn('if (("mode" in line) && line.mode != "rail") continue;', resolver)
        self.assertIn('if (!("kind" in line) || line.kind != kind) continue;', resolver)
        self.assertIn('local sameCargo = ("cargo" in line) && line.cargo == cargo;', resolver)
        self.assertIn('if (!sameCargo && !RAIL_ORIGIN_REUSE_CROSS_CARGO) continue;', resolver)
        self.assertIn('if (kind == "freight" && sameCargo && candidateEnd != choice.lineEnd) continue;', resolver)
        self.assertIn('if (!("lineId" in line)) continue;', resolver)
        self.assertIn('line[platformKey] != null', resolver)

    def test_joinability_keeps_pax_role_symmetric_but_freight_role_directional(self):
        resolver = function_body(
            self.candidates,
            "function OpexRailOriginCompatibleService(service, kind, cargo, candidateEnd)",
        )
        self.assertEqual(resolver.count('candidateEnd != choice.lineEnd'), 1)
        self.assertIn('kind == "freight"', resolver)
        reuse = function_body(
            self.candidates,
            "function OpexRailOriginReuseJoinable(sa, sb, kind, cargo)",
        )
        self.assertIn('OpexRailOriginServiceJoinable(sa, kind, cargo, "A")', reuse)
        self.assertIn('OpexRailOriginServiceJoinable(sb, kind, cargo, "B")', reuse)
        self.assertIn('if (kind == "pax" && !RAIL_ORIGIN_REUSE_PAX) return false;', reuse)
        self.assertIn('if (kind == "freight" && !RAIL_ORIGIN_REUSE_FREIGHT) return false;', reuse)

    def test_late_fast_negative_uses_only_necessary_line_contract(self):
        helper = function_body(
            self.candidates,
            "function OpexRailOriginReuseHasPotentialLine(lines, kind, cargo = null)",
        )
        self.assertIn("if (lines == null) return false;", helper)
        self.assertIn('if (("mode" in line) && line.mode != "rail") continue;', helper)
        self.assertIn('if (!("kind" in line) || line.kind != kind) continue;', helper)
        self.assertIn("if (cargo != null)", helper)
        self.assertIn('local sameCargo = ("cargo" in line) && line.cargo == cargo;', helper)
        self.assertIn("if (!sameCargo && !RAIL_ORIGIN_REUSE_CROSS_CARGO) continue;", helper)
        self.assertIn('else if (!("cargo" in line) && !RAIL_ORIGIN_REUSE_CROSS_CARGO)', helper)
        self.assertIn('if (!("lineId" in line)) continue;', helper)
        self.assertIn('local hasEndA = ("platformA" in line) && line.platformA != null', helper)
        self.assertIn('OpexLineStationId(line, "A") >= 0;', helper)
        self.assertIn('local hasEndB = ("platformB" in line) && line.platformB != null', helper)
        self.assertIn('OpexLineStationId(line, "B") >= 0;', helper)
        self.assertIn("if (hasEndA || hasEndB) return true;", helper)
        # Pas de condition de paire ici : proximite/role/ambiguite restent au resolver complet.
        self.assertNotIn("candidateEnd", helper)
        self.assertNotIn("OpexOriginService(", helper)
        self.assertNotIn("catalog.", helper)

    def test_late_fast_negative_runs_only_inside_reuse_evaluation(self):
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertNotIn("OpexRailOriginReuseHasPotentialLine(", pax)
        self.assertNotIn("OpexRailOriginReuseHasPotentialLine(", freight)

        pax_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluatePax(")
        cargo = pax_eval.index("local cargo = catalog.paxCargo;")
        fast = pax_eval.index('if (!OpexRailOriginReuseHasPotentialLine(lines, "pax", cargo))')
        towns = pax_eval.index("local towns = catalog.towns;")
        self.assertLess(cargo, fast)
        self.assertLess(fast, towns)
        self.assertIn("stats.originReuseFastNegative++;", pax_eval[fast:towns])
        self.assertIn("return;", pax_eval[fast:towns])

        freight_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluateFreight(")
        fast = freight_eval.index(
            'if (!OpexRailOriginReuseHasPotentialLine(lines, "freight", deferred.freightCargo))'
        )
        industries = freight_eval.index("local industries = catalog.industries;")
        self.assertLess(fast, industries)
        self.assertIn("stats.originReuseFastNegative++;", freight_eval[fast:industries])
        self.assertIn("return;", freight_eval[fast:industries])

    def test_fast_negative_is_profiled_in_reuse_stats_and_logs(self):
        stats = function_body(self.candidates, "function OpexRailCandidateStats()")
        self.assertIn("originReuseFastNegative = 0", stats)
        finalize = function_body(
            self.candidates,
            "function OpexRailOriginReuseFinalize(set, k, catalog = null, budget = null, lines = null,",
        )
        self.assertGreaterEqual(finalize.count('" fast_negative="'), 2)
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertIn('" fast_negative=" + (reuseStats != null ? reuseStats.originReuseFastNegative : 0)', build)

    def test_search_supersede_is_rank0_origin_reuse_only(self):
        body = function_body(
            self.task_rail,
            "function OpexAI::_maybeSupersedeRailSearchForOriginReuse(candidate, rank)",
        )
        self.assertIn("if (!RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE || candidate == null || rank != 0) return false;", body)
        self.assertIn('if (!("originServed" in candidate) || !candidate.originServed) return false;', body)
        self.assertIn('state.kind != "primary"', body)
        self.assertIn('state.phase != "search"', body)
        self.assertIn('if (("originServed" in old) && old.originServed) return false;', body)
        self.assertIn('("isChainStep2" in old)', body)
        self.assertIn('("c121PrepStock" in old)', body)
        self.assertIn('OpexDecide("RAIL_REUSE_SUPERSEDE"', body)
        self.assertIn("this._railSearch = null;", body)

    def test_search_supersede_runs_before_search_in_progress_rejection(self):
        body = function_body(self.task_rail, "function OpexAI::_tryBuildRailProject(")
        call = body.index("this._maybeSupersedeRailSearchForOriginReuse(candidate, i);")
        reject = body.index('reason = "search_in_progress"')
        self.assertLess(call, reject)
        self.assertIn('&& (!("railPlan" in candidate) || candidate.railPlan == null)', body[:call])
        self.assertIn('OpexDecide("RAIL_REUSE_BLOCKED_SEARCH"', body[:call])

    def test_search_supersede_setting_defaults_off_and_is_parent_scoped(self):
        self.assertIn("RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE <- false;", self.globals)
        self.assertIn(
            'RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE = RAIL_ORIGIN_REUSE\n'
            '      && AIController.GetSetting("rail_origin_reuse_search_supersede") != 0;',
            self.settings,
        )
        self.assertIn('name = "rail_origin_reuse_search_supersede"', self.info)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", self.info)

    def test_free_pair_fast_paths_precede_origin_reuse_toggle_reads(self):
        reuse = function_body(
            self.candidates,
            "function OpexRailOriginReuseJoinable(sa, sb, kind, cargo)",
        )
        self.assertLess(
            reuse.index("if (sa == null && sb == null) return true;"),
            reuse.index("if (!RAIL_ORIGIN_REUSE) return true;"),
        )
        attach = function_body(
            self.candidates, "function OpexRailAttachOriginReuse(candidate, sa, sb)"
        )
        self.assertLess(
            attach.index("if (candidate == null || (sa == null && sb == null)) return;"),
            attach.index("if (!RAIL_ORIGIN_REUSE) return;"),
        )

    def test_reuse_annotation_transports_station_platform_line_and_end(self):
        attach = function_body(
            self.candidates, "function OpexRailAttachOriginReuse(candidate, sa, sb)"
        )
        self.assertIn('if (sa != null && sb == null) { service = sa; joinEnd = "A"; }', attach)
        self.assertIn('else if (sa == null && sb != null) { service = sb; joinEnd = "B"; }', attach)
        self.assertIn(
            "OpexRailOriginCompatibleService(service, candidate.kind, candidate.cargo, joinEnd)",
            attach,
        )
        self.assertIn("OpexRailAttachMatchedOriginReuse(candidate, sa, sb, matchedService);", attach)
        matched = function_body(
            self.candidates, "function OpexRailAttachMatchedOriginReuse(candidate, sa, sb, matchedService)"
        )
        self.assertIn("candidate.originServed = true;", matched)
        self.assertIn("candidate.joinPlatform <- matchedService.line[platformKey];", matched)
        self.assertIn("candidate.joinStationId <- matchedService.stationId;", matched)
        self.assertIn("candidate.joinLineId <- matchedService.line.lineId;", matched)
        self.assertIn("candidate.joinEnd <- joinEnd;", matched)
        self.assertIn('if (("line" in service) && service.line != null && ("lineId" in service.line))', matched)
        self.assertIn("originalLineId < 0 || matchedService.line.lineId != originalLineId", matched)

    def test_builder_supports_join_on_a_and_b_without_reversing_candidate(self):
        plans = function_body(self.builder, "function OpexRailPlatformPlans(catalog, candidate)")
        self.assertIn('local joinB = ("joinEnd" in candidate) && candidate.joinEnd == "B";', plans)
        self.assertIn("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA)", plans)
        self.assertIn("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB)", plans)
        self.assertIn(
            "OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, jointLength",
            plans,
        )
        self.assertIn(
            "return { plansA = plansA, plansB = jointPlansB, length = jointLength,",
            plans,
        )

    def test_join_on_b_keeps_freight_source_as_production_side(self):
        plans = function_body(self.builder, "function OpexRailPlatformPlans(catalog, candidate)")
        join_b = plans.index("} else {", plans.index("if (!joinB)"))
        strict = plans.index("if (strictOriginReuseJoin)", join_b)
        branch = plans[join_b:strict]
        self.assertIn(
            "OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, jointLength,",
            branch,
        )
        self.assertIn("catalog.railCoverage,\n                                        true, statsA);", branch)
        self.assertNotIn("candidate.kind == \"pax\", statsA", branch)
        # Le cote B libre du cas joinEnd=A reste symetrique : pax produit, fret accepte.
        join_a = plans[plans.index("if (!joinB)"):join_b]
        self.assertIn('candidate.kind == "pax", statsB', join_a)

    def test_fallback_preserves_every_fresh_candidate_and_only_fills_top_k(self):
        body = function_body(
            self.candidates, "function OpexRailOriginReuseFallback(fresh, reuse, k)"
        )
        self.assertIn('local slots = k - fresh.len();', body)
        self.assertIn('if (slots <= 0 || reuse.len() == 0)', body)
        self.assertIn('local admitted = OpexTopK(reuse, slots);', body)
        self.assertIn('foreach (candidate in admitted) fresh.append(candidate);', body)

    def test_fallback_is_applied_only_under_both_reuse_toggles(self):
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertIn("local needFallbackReuse = all.len() < TOP_K && stats.pairsOriginServed > 0;", build)
        self.assertIn(
            "local runFallbackReuse = needFallbackReuse && RAIL_ORIGIN_REUSE && RAIL_ORIGIN_REUSE_FALLBACK;",
            build,
        )
        self.assertIn("OpexRailOriginReuseFallback(all, reuse, TOP_K)", build)
        self.assertIn('budget.end("cand_origin_reuse")', build)
        self.assertIn('OpexDecide("RAIL_ORIGIN_REUSE_FALLBACK"', build)

    def test_fallback_creates_only_postscan_requests_without_first_pass_reuse_state(self):
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertNotIn("OpexRailOriginReuseDeferredMatch(", pax)
        self.assertNotIn("OpexRailOriginReuseDeferredMatch(", freight)
        self.assertNotIn("originReusePaxDeferred", pax)
        self.assertNotIn("originReuseFreightDeferred", freight)
        self.assertNotIn("originReuseQueued", pax)
        self.assertNotIn("originReuseQueued", freight)
        self.assertIn("stats.pairsOriginServed++;", pax)
        self.assertGreaterEqual(freight.count("stats.pairsOriginServed++;"), 2)
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertIn("local reuseQueued = 0;", build)
        self.assertIn("local paxRequest = null;", build)
        self.assertIn("local freightRequest = null;", build)
        self.assertIn("paxRequest = { abandonedPairs = abandonedPairs, paxBand = paxBand,", build)
        self.assertIn("freightRequest = { abandonedPairs = abandonedPairs, freightCargo = freightCargo,", build)
        self.assertIn("stats.originReuseQueued = reuseQueued;", build)

    def test_join_reason_explains_current_physical_contract(self):
        body = function_body(
            self.candidates,
            "function OpexRailOriginServiceJoinReason(service, kind, cargo, candidateEnd)",
        )
        self.assertIn("if (RAIL_ORIGIN_REUSE_MULTILINE_MATCH", body)
        for reason in (
            "ambiguous", "invalid_station", "kind_mismatch", "cargo_mismatch",
            "cargo_mismatch_same_role", "cargo_mismatch_cross_role",
            "role_mismatch", "missing_platform", "joinable",
        ):
            self.assertIn(f'"{reason}"', body)
        self.assertIn('kind == "freight" && sameCargo && candidateEnd != choice.lineEnd', body)

    def test_origin_exposure_shadow_classifies_presence_without_defining_joinability(self):
        body = function_body(
            self.candidates,
            "function OpexRailOriginExposureObserve(exposure, sa, sb, kind, cargo)",
        )
        # libre/libre : aucune exposition ; servi/servi : compteur distinct.
        self.assertIn("if (sa == null && sb == null) return;", body)
        self.assertIn("if (sa != null && sb != null)", body)
        self.assertIn("exposure.bothServed++;", body)
        # Exactly-one-served conserve le sens A/B avant de deleguer le contrat physique existant.
        self.assertIn("exposure.oneServedTotal++;", body)
        self.assertIn("exposure.oneServedA++;", body)
        self.assertIn('candidateEnd = "A";', body)
        self.assertIn("exposure.oneServedB++;", body)
        self.assertIn('candidateEnd = "B";', body)
        self.assertIn(
            "local reason = OpexRailOriginServiceJoinReason(service, kind, cargo, candidateEnd);",
            body,
        )
        detail_gate = body.index("if (!RAIL_ORIGIN_EXPOSURE_DETAIL_SHADOW) return;")
        reason = body.index("local reason = OpexRailOriginServiceJoinReason")
        self.assertLess(detail_gate, reason)
        self.assertNotIn("OpexRailOriginCompatibleService(", body)

    def test_origin_exposure_shadow_maps_joinable_and_structural_rejections(self):
        body = function_body(
            self.candidates,
            "function OpexRailOriginExposureObserve(exposure, sa, sb, kind, cargo)",
        )
        expected = {
            "joinable": "exposure.joinable++",
            "ambiguous": "exposure.ambiguous++",
            "invalid_station": "exposure.invalidStation++",
            "nonrail": "exposure.nonrail++",
            "kind_mismatch": "exposure.kindMismatch++",
            "cargo_mismatch": "exposure.cargoMismatch++",
            "role_mismatch": "exposure.roleMismatch++",
            "missing_line": "exposure.missingLine++",
            "missing_line_id": "exposure.missingLineId++",
            "missing_platform": "exposure.missingPlatform++",
        }
        for reason, counter in expected.items():
            self.assertIn(f'reason == "{reason}"', body)
            self.assertIn(counter, body)
        self.assertIn('reason == "cargo_mismatch_same_role"', body)
        self.assertIn("exposure.cargoMismatchSameRole++;", body)
        self.assertIn('reason == "cargo_mismatch_cross_role"', body)
        self.assertIn("exposure.cargoMismatchCrossRole++;", body)

    def test_origin_exposure_shadow_only_observes_the_historical_or_rejections(self):
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        pax_guard = pax.index("if (sa != null || sb != null)")
        pax_continue = pax.index("continue;", pax_guard)
        self.assertIn(
            'OpexRailOriginExposureObserve(stats.originExposurePax, sa, sb, "pax", cargo);',
            pax[pax_guard:pax_continue],
        )
        self.assertIn("if (RAIL_ORIGIN_EXPOSURE_SHADOW)", pax[pax_guard:pax_continue])
        self.assertIn(
            'if (!("originExposurePax" in stats)) stats.originExposurePax <- OpexRailOriginExposureStats();',
            pax[pax_guard:pax_continue],
        )
        ind_guard = freight.index("if (ss != null || sd != null)")
        ind_continue = freight.index("continue;", ind_guard)
        self.assertIn(
            'OpexRailOriginExposureObserve(stats.originExposureFreight, ss, sd, "freight", cargo);',
            freight[ind_guard:ind_continue],
        )
        town_guard = freight.index("if (ss != null || st != null)")
        town_continue = freight.index("continue;", town_guard)
        self.assertIn(
            'OpexRailOriginExposureObserve(stats.originExposureFreight, ss, st, "freight", cargo);',
            freight[town_guard:town_continue],
        )
        # Le garde causal reste un continue historique : le shadow ne peut atteindre MakeCandidate.
        self.assertLess(pax_continue, pax.index("OpexMakeCandidate(", pax_guard))
        self.assertLess(ind_continue, freight.index("OpexMakeCandidate(", ind_guard))
        self.assertLess(town_continue, freight.index("OpexMakeCandidate(", town_guard))

    def test_origin_exposure_shadow_has_no_candidate_economics_astar_or_admission_path(self):
        observe = function_body(
            self.candidates,
            "function OpexRailOriginExposureObserve(exposure, sa, sb, kind, cargo)",
        )
        fields = function_body(
            self.candidates,
            "function OpexRailOriginExposureFields(stats, freshCandidates)",
        )
        combined = observe + fields
        for forbidden in (
            "OpexMakeCandidate(", "OpexLineEconomics(", "OpexTopK(",
            "OpexRailOriginReuseFallback(", "PathFinder", "InitializePath(",
            "out.append(", "candidates.append(",
        ):
            self.assertNotIn(forbidden, combined)

    def test_origin_exposure_summary_uses_fresh_pool_before_any_reuse_admission(self):
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        fresh = build.index("stats.originExposureFreshCandidates <- all.len();")
        reuse = build.index("local reuseFallback = null;")
        self.assertLess(fresh, reuse)
        fields = function_body(
            self.candidates,
            "function OpexRailOriginExposureFields(stats, freshCandidates)",
        )
        self.assertIn("local underTopK = freshCandidates < TOP_K;", fields)
        self.assertIn('" fresh_candidates=" + freshCandidates', fields)
        self.assertIn('" fresh_lt_top_k=" + (underTopK ? 1 : 0)', fields)
        self.assertIn('"_detail=" + (RAIL_ORIGIN_EXPOSURE_DETAIL_SHADOW ? 1 : 0)', fields)
        self.assertIn('"_joinable_when_fresh_lt_top_k="', fields)
        self.assertIn("(underTopK ? exposure.joinable : 0)", fields)
        reject = build.index('OpexDecide("VIVIER_REJECT", "reason=origin_served n="')
        self.assertGreater(reject, reuse)
        self.assertIn(
            "OpexRailOriginExposureFields(stats, stats.originExposureFreshCandidates)",
            build[reject:reject + 500],
        )

    def test_origin_exposure_reuses_existing_origin_reject_log_call(self):
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertNotIn('OpexDecide("RAIL_ORIGIN_EXPOSURE"', self.candidates)
        vivier = build.index('OpexDecide("VIVIER_GEN"')
        origin_block = build[build.index("if (stats.pairsOriginServed > 0)", vivier):]
        end = origin_block.index("if (stats.noMonthly > 0)")
        origin_block = origin_block[:end]
        self.assertEqual(origin_block.count('OpexDecide("VIVIER_REJECT"'), 2)
        self.assertIn('if ("originExposureFreshCandidates" in stats)', origin_block)
        self.assertIn(
            'OpexDecide("VIVIER_REJECT", "reason=origin_served n=" + stats.pairsOriginServed);',
            origin_block,
        )

    def test_origin_exposure_shadow_allocates_only_inside_real_or_rejections(self):
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertNotIn("OpexRailOriginExposureStats(", build)
        self.assertIn(
            "local prePair = (RAIL_ORIGIN_EXPOSURE_SHADOW && DECISION_LOG) ? OpexRailPrePairStats() : null;",
            build,
        )
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        pax_guard = pax.index("if (sa != null || sb != null)")
        pax_continue = pax.index("continue;", pax_guard)
        self.assertIn("OpexRailOriginExposureStats()", pax[pax_guard:pax_continue])
        self.assertNotIn("OpexRailOriginExposureStats()", pax[:pax_guard])
        ind_guard = freight.index("if (ss != null || sd != null)")
        self.assertNotIn("OpexRailOriginExposureStats()", freight[:ind_guard])

    def test_origin_exposure_shadow_counts_pre_pair_funnel_without_new_api_work(self):
        pre_stats = function_body(self.candidates, "function OpexRailPrePairStats()")
        pre_fields = function_body(self.candidates, "function OpexRailPrePairFields(")
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        for field in (
            "paxCargoValid", "paxGridPairs", "paxTargetSkipped", "paxBandSkipped", "paxAbandonSkipped",
            "freightCargoMatched", "freightCargoNoSinks", "freightSources",
            "freightIndustrySinks", "freightTownSinks",
            "freightIndustryCartesian", "freightTownCartesian",
            "freightSelfSkipped", "freightTargetSkipped", "freightAbandonSkipped",
            "freightIndustryPairs", "freightTownPairs", "freightTownZeroMonthly",
        ):
            self.assertIn(field, pre_stats)
        for context in (
            '" generate_pax="', '" generate_freight="', '" pax_band="',
            '" freight_cargo="', '" target_kind="', '" target_id="',
        ):
            self.assertIn(context, pre_fields)
        self.assertIn("if (prePair != null) prePair.paxGridPairs++;", pax)
        self.assertIn("if (prePair != null) prePair.paxCargoValid = 1;", pax)
        self.assertIn("if (prePair != null) prePair.paxAbandonSkipped++;", pax)
        self.assertIn("prePair.freightCargoMatched++;", freight)
        self.assertIn("prePair.freightCargoNoSinks++;", freight)
        self.assertIn("if (prePair != null) prePair.freightSelfSkipped++;", freight)
        self.assertIn("if (prePair != null) prePair.freightAbandonSkipped++;", freight)
        self.assertIn("if (prePair != null) prePair.freightTownZeroMonthly++;", freight)
        self.assertIn('OpexDecide("RAIL_PREPAIR"', build)
        combined = pre_stats + pre_fields
        for forbidden in (
            "AITown.", "AIIndustry.", "AIMap.", "OpexMakeCandidate(",
            "OpexLineEconomics(", "OpexOriginService(", "OpexTopK(",
        ):
            self.assertNotIn(forbidden, combined)

    def test_rail_attempt_logs_reuse_and_predicted_iterations(self):
        self.assertIn('" reuse=" + ((("originServed" in candidate)', self.task_rail)
        self.assertIn('" pred_astar=" + (("iterations" in candidate)', self.task_rail)

    def test_fallback_uses_historical_first_scan_then_targeted_reuse_scan(self):
        self.assertNotIn("function OpexRailOriginPairAllowed(", self.candidates)
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertNotIn("allowOneServed", pax)
        self.assertNotIn("allowOneServed", freight)
        self.assertNotIn("deferOriginReuse", pax)
        self.assertNotIn("deferOriginReuse", freight)
        self.assertNotIn("RAIL_ORIGIN_REUSE", pax)
        self.assertNotIn("RAIL_ORIGIN_REUSE", freight)
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        self.assertEqual(build.count("OpexPaxCandidates("), 1)
        self.assertEqual(build.count("OpexFreightCandidates("), 1)
        self.assertNotIn("originReuseOnly", build)
        self.assertIn("OpexRailOriginReuseEvaluatePax(", build)
        self.assertIn("OpexRailOriginReuseEvaluateFreight(", build)
        self.assertIn("if (generatePax && RAIL_ORIGIN_REUSE_PAX", build)
        self.assertIn("if (generateFreight && RAIL_ORIGIN_REUSE_FREIGHT)", build)
        self.assertIn("profile.paxOps += OpexOpsMeasureEnd(reusePaxMark);", build)
        self.assertIn("profile.freightOps += OpexOpsMeasureEnd(reuseFreightMark);", build)

    def test_deferred_reuse_resolves_join_service_only_once_on_success(self):
        match = function_body(
            self.candidates, "function OpexRailOriginReuseDeferredMatch(stats, sa, sb, kind, cargo)"
        )
        self.assertIn("OpexRailOriginCompatibleService(service, kind, cargo, candidateEnd)", match)
        self.assertIn("if (!DECISION_LOG) return null;", match)
        pax_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluatePax(")
        freight_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluateFreight(")
        self.assertIn("local matchedService = OpexRailOriginReuseDeferredMatch", pax_eval)
        self.assertIn("OpexRailAttachMatchedOriginReuse(candidate, sa, sb, matchedService);", pax_eval)
        self.assertIn("local matchedService = OpexRailOriginReuseDeferredMatch", freight_eval)
        self.assertIn("OpexRailAttachMatchedOriginReuse(candidate, ss, sd, matchedService);", freight_eval)
        self.assertIn("OpexRailAttachMatchedOriginReuse(candidate, ss, st, matchedService);", freight_eval)

    def test_targeted_reuse_rescans_only_after_fresh_generation(self):
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        pax_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluatePax(")
        freight_eval = function_body(self.candidates, "function OpexRailOriginReuseEvaluateFreight(")
        self.assertNotIn("deferred.append(", pax)
        self.assertNotIn("deferred.append(", freight)
        self.assertIn("local towns = catalog.towns;", pax_eval)
        self.assertIn("served.append(OpexOriginService(lines, towns[i].tile));", pax_eval)
        self.assertIn("local grid = OpexSpatialGrid();", pax_eval)
        self.assertIn("for (local a = 0; a < towns.len(); a++)", pax_eval)
        self.assertIn("local neighbors = grid.GetCandidatesFor(a);", pax_eval)
        self.assertIn("local sa = served[a];", pax_eval)
        self.assertIn("local sb = served[b];", pax_eval)
        self.assertIn("local industries = catalog.industries;", freight_eval)
        self.assertIn("served.append(OpexOriginService(lines, industries[i].tile));", freight_eval)
        self.assertIn("foreach (cargo, sources in catalog.producers)", freight_eval)
        self.assertIn("for (local k = 0; k < sinks.len(); k++)", freight_eval)
        self.assertIn("foreach (town in townSinks)", freight_eval)
        self.assertIn("local townServiceCache = C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE ? {} : null;", freight_eval)

    def test_freight_cargo_fallback_sees_only_fresh_before_reuse_finalize(self):
        main = function_body(self.projects_full, "function OpexBuildProjects(")
        rail_block = main.index("if (doPaxRail || doFreight)")
        defer_decl = main.index("local deferRailReuseAdmission =")
        self.assertLess(defer_decl, rail_block)
        first_build = main.index("OpexBuildCandidates(")
        has_freight = main.index("local hasFreight = false;", first_build)
        finalize = main.index("OpexRailOriginReuseFinalize(rail, TOP_K, catalog, budget, lines", has_freight)
        self.assertLess(first_build, has_freight)
        self.assertLess(has_freight, finalize)
        self.assertIn("deferRailReuseAdmission", main[first_build:has_freight])
        self.assertIn("rail = OpexRailSelectFreightReusePool(rail, extraFreight);", main[has_freight:finalize])
        self.assertIn("rail = OpexMergeRailCandidateSet(rail, extraFreight, false);", main[has_freight:finalize])
        self.assertLess(
            main.index("if (extraFreight.candidates.len() == 0) continue;", has_freight),
            main.index("rail = OpexRailSelectFreightReusePool(rail, extraFreight);", has_freight),
        )

        regen = function_body(self.projects, "function OpexGenerateModeProjects(")
        has_freight = regen.index("local hasFreight = false;")
        finalize = regen.index("OpexRailOriginReuseFinalize(rail, TOP_K, catalog, budget, lines);", has_freight)
        self.assertIn("deferRailReuseAdmission", regen[:has_freight])
        self.assertLess(
            regen.index("if (extra.candidates.len() == 0) continue;", has_freight),
            regen.index("rail = OpexRailSelectFreightReusePool(rail, extra);", has_freight),
        )
        self.assertIn("rail = OpexMergeRailCandidateSet(rail, extra, false);", regen[has_freight:finalize])
        self.assertLess(has_freight, finalize)

    def test_selected_freight_cargo_replaces_only_freight_reuse_pool(self):
        helper = function_body(
            self.projects_full, "function OpexRailSelectFreightReusePool(base, selected)"
        )
        self.assertIn('"reuseFreightDeferred" in selected', helper)
        self.assertIn("base.reuseFreightDeferred <- selected.reuseFreightDeferred;", helper)
        self.assertIn("base.reuseFreightDeferred = null;", helper)
        self.assertIn('candidate.kind != "freight"', helper)
        self.assertIn('candidate.kind == "freight"', helper)
        merge = function_body(
            self.projects_full, "function OpexMergeRailCandidateSet(base, extra, mergeReuse = true)"
        )
        self.assertIn("if (mergeReuse &&", merge)

    def test_deferred_freight_reuse_is_evaluated_only_at_finalize(self):
        build = function_body(self.candidates, "function OpexBuildCandidates(")
        defer_branch = build.index("if (deferReuseAdmission && runFallbackReuse)")
        immediate_branch = build.index("} else {", defer_branch)
        result = build.index("local result =", immediate_branch)
        self.assertIn("deferredReusePax = paxRequest;", build[defer_branch:immediate_branch])
        self.assertIn("deferredReuseFreight = freightRequest;", build[defer_branch:immediate_branch])
        self.assertNotIn("OpexRailOriginReuseEvaluatePax(", build[defer_branch:immediate_branch])
        self.assertNotIn("OpexRailOriginReuseEvaluateFreight(", build[defer_branch:immediate_branch])
        self.assertIn("result.reusePaxDeferred <- deferredReusePax;", build[result:])
        self.assertIn("result.reuseFreightDeferred <- deferredReuseFreight;", build[result:])

        finalize = function_body(
            self.candidates,
            "function OpexRailOriginReuseFinalize(set, k, catalog = null, budget = null, lines = null,",
        )
        self.assertIn("OpexRailOriginReuseEvaluatePax(catalog, lines, set.reusePaxDeferred, reuse,", finalize)
        self.assertIn("OpexRailOriginReuseEvaluateFreight(catalog, lines, set.reuseFreightDeferred,", finalize)
        self.assertIn('budget.end("cand_origin_reuse_finalize")', finalize)
        self.assertIn("OpexRailOriginReuseFallback(set.candidates, reuse, k)", finalize)
        self.assertIn('if ("reuseCandidates" in set) set.reuseCandidates = [];', finalize)
        self.assertNotIn("\n  set.reuseCandidates = [];", finalize)
        self.assertLess(
            finalize.index("OpexRailOriginReuseEvaluateFreight("),
            finalize.index("OpexRailOriginReuseFallback(set.candidates, reuse, k)"),
        )

    def test_origin_reuse_join_failure_cannot_fall_through_to_two_new_stations(self):
        plans = function_body(self.builder, "function OpexRailPlatformPlans(catalog, candidate)")
        strict = plans.index("local strictOriginReuseJoin = RAIL_ORIGIN_REUSE")
        strict_return = plans.index("if (strictOriginReuseJoin)", strict)
        free_search = plans.index("for (local length = wanted; length >= floor; length--)")
        self.assertLess(strict_return, free_search)
        self.assertIn("reason = OpexRailSiteReason(joinHasA, joinHasB)", plans[strict_return:free_search])
        self.assertIn('("originServed" in candidate) && candidate.originServed', plans[strict:strict_return])
        self.assertIn('("joinEnd" in candidate)', plans[strict:strict_return])

    def test_decision_log_identifies_actual_reuse_attempts_and_builds(self):
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', self.task_rail)
        self.assertIn('" reuse=" + ((("originServed" in candidate) && candidate.originServed) ? 1 : 0)', self.task_rail)
        self.assertIn('" join_end=" + (("joinEnd" in candidate) ? candidate.joinEnd : "-")', self.task_rail)
        self.assertIn('" pred_profit=" + (("profitAnnual" in candidate) ? candidate.profitAnnual : -1)', self.task_rail)
        build = self.task_rail[self.task_rail.index('OpexDecide("RAIL_BUILD"'):]
        self.assertIn('" reuse=" + ((("originServed" in candidate) && candidate.originServed) ? 1 : 0)', build)
        self.assertIn('" pred_profit=" + (("profitAnnual" in candidate) ? candidate.profitAnnual : -1)', build)

    def test_policy_is_limited_to_the_three_rail_generation_guards(self):
        self.assertNotIn("OpexRailOriginPairAllowed(", self.candidates)
        pax = function_body(self.candidates, "function OpexPaxCandidates(")
        freight = function_body(self.candidates, "function OpexFreightCandidates(")
        self.assertEqual(pax.count("if (sa != null || sb != null)"), 1)
        self.assertEqual(freight.count("if (ss != null || sd != null)"), 1)
        self.assertEqual(freight.count("if (ss != null || st != null)"), 1)
        # Trois gardes rail seulement : pax, fret industrie, fret ville. Aucun chemin route/AIR.
        self.assertEqual(self.candidates.count("OpexRailOriginPairBlocked("), 1)
        # Le helper historique reste disponible pour les contrats externes ; la generation encode
        # directement free / both-served / exactly-one sans lire les toggles sur une paire libre.


if __name__ == "__main__":
    unittest.main()
