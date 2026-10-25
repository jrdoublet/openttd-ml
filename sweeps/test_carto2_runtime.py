"""CARTO-2 runtime wiring and safety contracts, without Docker or Squirrel edits.

The requested experiment is three fixed seeds (42, 100, 999), five game years
(1970-1974), with free and guided A* on exactly the same snapshot of each
pair. Built houses and roads are the primary corrected city indicator; a
supplementary town-center inventory can be incomplete and must report this.
Source-level checks cannot prove an atomic FindPath(1) stays within one tick,
nor that the engine completes 3x5; those require separately instrumented games.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
RLW = 1 << 24
CARTO1 = 1 << 25
V309 = 1 << 26
COMBO = RLW | CARTO1 | V309
EXPERIMENT_SEEDS = (42, 100, 999)
EXPERIMENT_START_YEAR = 1970
EXPERIMENT_YEARS = 5
EXPERIMENT_END_YEAR = EXPERIMENT_START_YEAR + EXPERIMENT_YEARS - 1


def source(filename: str) -> str:
    return (AI / filename).read_text(encoding="utf-8")


def uncomment(data: str) -> str:
    """Remove comments, retaining quoted strings for behavioral assertions."""
    tokens = re.compile(
        r'(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
        r'|(?P<comment>/\*.*?\*/|//[^\n]*)', re.DOTALL,
    )
    return tokens.sub(lambda m: m.group("string") or "", data)


def body(data: str, name: str) -> str:
    """Extract a named Squirrel function, accounting for nested braces."""
    data = uncomment(data)
    match = re.search(r"\bfunction\s+" + re.escape(name)
                      + r"\s*\([^)]*\)\s*\{", data)
    if match is None:
        raise AssertionError(f"Missing function {name}")
    start = match.end()
    depth = 1
    for i in range(start, len(data)):
        if data[i] == "{":
            depth += 1
        elif data[i] == "}":
            depth -= 1
            if depth == 0:
                return data[start:i]
    raise AssertionError(f"Unclosed function {name}")


class Carto2RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = {name: uncomment(source(name)) for name in (
            "probe_carto2.nut", "probe_carto1.nut", "probe_carto1_long.nut",
            "rail_long_window_enumerator.nut", "globals_pre.nut",
            "settings.nut", "main.nut", "probes.nut", "info.nut",
            "persist.nut", "task_rail.nut", "orchestrator.nut",
        )}

    def fn(self, name: str, file: str = "probe_carto2.nut") -> str:
        return body(self.code[file], name)

    def test_default_off_and_requires_all_three_existing_probe_bits(self):
        self.assertEqual(COMBO, 117440512)
        globals_ = self.code["globals_pre.nut"]
        for var in ("CARTO1_SHADOW", "CARTO2_SHADOW", "RLW04B_SHADOW",
                    "V309_IDLE_PROBE", "CARTO2_IDLE_READY"):
            self.assertRegex(globals_, rf"\b{var}\s*<-\s*false\s*;")
        settings = self.fn("OpexLoadSettings", "settings.nut")
        for name, bit in (("CARTO1_SHADOW", CARTO1),
                          ("RLW04B_SHADOW", RLW),
                          ("V309_IDLE_PROBE", V309)):
            self.assertRegex(settings, rf"\b{name}\s*=\s*OpexProbeEnabled\(\s*{bit}\s*\)")
        self.assertRegex(settings, r"\bCARTO2_SHADOW\s*=\s*"
                         r"CARTO1_SHADOW\s*&&\s*RLW04B_SHADOW\s*&&\s*V309_IDLE_PROBE")
        self.assertNotIn('GetSetting("carto2', settings)
        get_settings = self.fn("GetSettings", "info.nut")
        probe_setting = re.search(r'AddSetting\(\s*\{\s*name\s*=\s*"probes"\s*,(.*?)\}\s*\)',
                                  get_settings, re.DOTALL)
        self.assertIsNotNone(probe_setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(probe_setting.group(1),
                             rf"\b{difficulty}_value\s*=\s*2\b")
        self.assertEqual(2 & COMBO, 0)

    def test_full_turn_top_dispatch_and_unique_sleep_in_both_loops(self):
        main = self.code["main.nut"]
        self.assertEqual(main.count('require("probe_carto2.nut")'), 1)
        self.assertLess(main.index('require("probe_carto1.nut")'),
                        main.index('require("probe_carto2.nut")'))
        for label, loop in (("ordinary", self.fn("OpexAI::Start", "main.nut")),
                            ("profiled", self.fn("OpexAI::_mainLoopProfiled", "probes.nut"))):
            with self.subTest(loop=label):
                self.assertEqual(loop.count("OpexCarto2FullTurn(this)"), 1,
                                 "Only the top-of-loop dispatcher may start a full shadow tick")
                self.assertNotIn("OpexCarto2Step(this)", loop,
                                 "Remove old end-of-turn CARTO2 hook")
                self.assertLess(loop.index("OpexCarto2FullTurn(this)"),
                                loop.index("this._processEvents()"),
                                "Full-turn eligibility must run before ordinary live work")
                self.assertLess(loop.index("OpexCarto2FullTurn(this)"),
                                loop.index("this._runOrchestratorTick()"))
                # A single literal Sleep site is ideal; two mutually
                # exclusive call sites are also valid when the shadow branch
                # immediately continues, so one (never two) executes per turn.
                sleeps = loop.count("AIController.Sleep(1)")
                self.assertIn(sleeps, (1, 2),
                              "Exactly one Sleep must execute on each loop iteration")
                if sleeps == 2:
                    shadow = re.search(
                        r"if\s*\(\s*CARTO2_SHADOW\s*&&\s*"
                        r"OpexCarto2FullTurn\(this\)\s*\)\s*\{\s*"
                        r"AIController\.Sleep\(1\)\s*;\s*continue\s*;\s*\}", loop)
                    self.assertIsNotNone(shadow,
                                         "Two Sleep call sites need an unconditional "
                                         "continue after the shadow Sleep")
                    self.assertEqual(loop[shadow.end():].count("AIController.Sleep(1)"), 1)
                self.assertIn("OpexV309IdleBegin()", loop)
                self.assertIn("OpexV309IdleTick(this)", loop)
                self.assertLess(loop.index("OpexV309IdleBegin()"),
                                loop.index("OpexV309IdleTick(this)"))
                self.assertLess(loop.index("OpexCarto2FullTurn(this)"),
                                loop.index("AIController.Sleep(1)"))

    def test_carto1_long_shadow_cannot_run_alongside_carto2_shadow(self):
        # Both CARTO-1 long and CARTO-2 own persistent A* objects.  Suppress
        # the former when CARTO-2 is active to honor the single-shadow rule.
        for label, loop in (("ordinary", self.fn("OpexAI::Start", "main.nut")),
                            ("profiled", self.fn("OpexAI::_mainLoopProfiled", "probes.nut"))):
            with self.subTest(loop=label):
                gate = re.search(r"if\s*\(([^)]*)\)\s*OpexCarto1LongStep\(this\)", loop)
                self.assertIsNotNone(gate, "Missing CARTO-1 LONG activation gate")
                for required in ("!CARTO2_SHADOW", "CARTO1_SHADOW", "RLW04B_SHADOW"):
                    self.assertIn(required, gate.group(1),
                                  "CARTO-2 must own the only shadow A* while enabled")

    def test_no_world_changing_commands_in_shadow_probe(self):
        probe = self.code["probe_carto2.nut"]
        for pattern in (
            r"\b(?:AITile|AIRail|AIRoad|AIAirport|AITown|AIIndustry|AIStation|"
            r"AIVehicle|AIBridge|AITunnel|AICompany|AIWater)\."
            r"(?:Build\w*|Remove\w*|Demolish\w*|Terraform\w*|"
            r"Set\w*|Move\w*|Sell\w*|DoCommand\w*)\s*\(",
            r"\bOpex(?:Build|Demolish|Remove|Terraform)\w*\s*\(",
            r"\b(?:AIController\.)?Sleep\s*\(",
        ):
            with self.subTest(pattern=pattern):
                self.assertNotRegex(probe, pattern)
        self.assertIn("OpexDecide(", probe)

    def test_v309_finance_revalidation_emergency_fairness_and_turn_ops(self):
        v309 = self.fn("OpexV309IdleTick", "probes.nut")
        self.assertRegex(v309, r"if\s*\(\s*CARTO2_SHADOW\s*\)\s*CARTO2_IDLE_READY")
        self.assertIn('projects.source == "unfunded_snapshot"', v309)
        self.assertIn("projects.cost == state.priorCost", v309)
        self.assertIn("revision == state.priorRevision", v309)
        self.assertIn("OpexAvailableCapital() < projects.cost", v309)
        self.assertIn("ai._railSearch == null", v309)
        can = self.fn("OpexCarto2CanTakeTurn")
        full = self.fn("OpexCarto2FullTurn")
        self.assertRegex(can, r"!CARTO2_SHADOW\s*\|\|\s*!CARTO2_IDLE_READY")
        self.assertIn('v.priorSource != "unfunded_snapshot"', can)
        self.assertIn("OpexAvailableCapital() >= v.priorCost", can)
        self.assertIn("OpexV309IdleRevisionKey(ai) != v.priorRevision", can)
        self.assertRegex(can, r"portfolio\s*!=\s*v\.cachedPortfolio")
        self.assertRegex(can, r"SELECT_BISECT_STAMP\s*!=\s*v\.cachedSelectStamp")
        self.assertRegex(can, r"best\s*!=\s*v\.cachedBest")
        self.assertRegex(can, r"v\.cachedBestCount\s*!=\s*0")
        self.assertRegex(can, r"best\s*!=\s*null\s*&&\s*best\.len\(\)\s*!=\s*0")
        # Squirrel tables are mutable: the same portfolio/best object and
        # selection stamp can retain a newly affordable capital quote.
        for field in ("nextProjectCapital", "minCapital"):
            self.assertIn(f'"{field}" in portfolio.stats', can)
        self.assertIn("nextCost != v.cachedNextCost", can)
        self.assertIn("minCost != v.cachedMinCost", can)
        for urgency in ("ai._railSearch", "ai._activeWorker", "ai._railExpansion",
                        "ai._po01cPending", "ai._po01cJob"):
            self.assertIn(urgency, can, f"Unexpected live interruption if {urgency} pending")
        self.assertIn("ai._hasReactiveIntentions()", can,
                      "A pending C80 reactive intent preempts shadow computation")
        self.assertNotRegex(can, r"_taskQueue\.len\(\)\s*>\s*0",
                            "Ordinary periodic tasks do not by themselves signal urgency")
        self.assertRegex(can, r"\bconsecutive\s*>=\s*\d+",
                         "A quota of consecutive shadow turns must preserve live fairness")
        self.assertIn("OpexCarto2CanTakeTurn(ai)", full)
        self.assertIn("CARTO2_IDLE_READY = false", full)
        self.assertIn("s.fullTurns++", full)
        self.assertIn("s.fullTurnOps += used", full)
        self.assertIn("s.fullTurnLeft += AIController.GetOpsTillSuspend()", full)
        self.assertIn('OpexDecide("CARTO2_TURN"', full)
        self.assertRegex(full, r'"[^"\n]*\bops="\s*\+\s*used',
                         "Expose measured actual per-full-turn opcode consumption")
        self.assertIn("s.fullTurnOps", self.fn("OpexCarto2Summary"))

    def test_v309_cached_fields_initialized_and_refreshed_before_full_turn(self):
        begin = self.fn("OpexV309IdleBegin", "probes.nut")
        projects = self.fn("OpexV309IdleProjects", "probes.nut")
        tick = self.fn("OpexV309IdleTick", "probes.nut")
        can = self.fn("OpexCarto2CanTakeTurn")
        fields = ("cachedPortfolio", "cachedBest", "cachedBestCount",
                  "cachedHead", "cachedSelectStamp", "cachedNextCost",
                  "cachedMinCost", "cachedProject")
        for field in fields:
            with self.subTest(field=field):
                self.assertRegex(begin, rf"\b{field}\s*=\s*",
                                 "All cached slots must exist before Squirrel member reads")
                self.assertRegex(projects, rf"state\.{field}\s*=\s*",
                                 "The V309 project scan must publish refreshed snapshots")
        self.assertLess(tick.index("OpexV309IdleProjects(ai, state)"),
                        tick.index("CARTO2_IDLE_READY ="))
        self.assertRegex(can, r'portfolio\s*==\s*null\s*\|\|\s*'
                         r'portfolio\s*!=\s*v\.cachedPortfolio',
                         "A null/missing portfolio must fail closed, not crash on best/stats")
        self.assertIn("ai._hasReactiveIntentions()", can)
        self.assertRegex(self.fn("OpexAI::_hasReactiveIntentions", "orchestrator.nut"),
                         r"_reactiveQueue\s*!=\s*null\s*&&\s*"
                         r"!this\._reactiveQueue\.isEmpty\(\)")

    def test_long_sample_score_uses_actual_production_and_cargo_income(self):
        collect = self.fn("OpexCarto2Collect")
        self.assertIn("ai._rlw04bState.sample", collect)
        self.assertIn("AIIndustry.IsValidIndustry(p.srcId)", collect)
        self.assertIn("AIIndustry.IsValidIndustry(p.dstId)", collect)
        self.assertRegex(collect, r"AIIndustry\.GetLastMonthProduction\(\s*p\.srcId\s*,\s*p\.cargo\s*\)")
        self.assertRegex(collect, r"AICargo\.GetCargoIncome\(\s*p\.cargo\s*,\s*p\.distance")
        self.assertRegex(collect, r"\bscore\s*=\s*prod\s*\*\s*income")
        self.assertRegex(collect, r'OpexCarto2NewRow\([^;]*"long"\s*,\s*score')
        self.assertIn("OpexCarto2Insert(s, row)", collect)
        insert = self.fn("OpexCarto2Insert")
        self.assertRegex(insert, r"s\.rows\[n\s*-\s*1\]\.score\s*<\s*row\.score")
        self.assertNotRegex(collect, r"AIBase\.Rand|\.Sort\(|\.sort\(")

    def test_real_rail_portfolio_has_distinct_provenance(self):
        collect = self.fn("OpexCarto2Collect")
        self.assertIn("ai._projects.rail", collect)
        self.assertIn("rail.best", collect)
        self.assertIn("rail.candidates", collect)
        self.assertRegex(collect, r'OpexCarto2NewRow\([^;]*"live"')
        self.assertIn("s.liveCount < 6", collect)
        self.assertIn("previous.key == row.key", collect)
        pair = self.fn("OpexCarto2Step")
        self.assertIn('" source=" + row.source', pair)

    def test_live_rail_kind_is_retained_in_pair_identity(self):
        new = self.fn("OpexCarto2NewRow")
        collect = self.fn("OpexCarto2Collect")
        # Real portfolio candidates include both pax and freight. A pax
        # attempt should never be relabeled as freight in pairing or logs.
        self.assertTrue(re.search(r"\bkind\b", new),
                        "NewRow must accept and retain the candidate transport kind")
        self.assertTrue(re.search(r"key\s*=\s*kind\s*\+", new),
                        "Pair key must encode pax/freight instead of always freight")
        self.assertTrue(re.search(r"\bcand\.kind\b", collect),
                        "Live pair collection must pass the real candidate.kind")

    def test_live_astar_uses_real_rail_plans_only_when_available(self):
        search = self.fn("OpexCarto2StartSearch")
        capture = self.fn("OpexCarto2CaptureLivePlans")
        log = self.fn("OpexCarto2LogSearch")
        # The portfolio row is not evidence of feasible station placement.
        # Reuse genuine plans only when they already exist; otherwise explicitly
        # mark missing live endpoints as unavailable (NOPA), not virtual.
        self.assertIn("plan.plansA == null", capture)
        self.assertIn("plan.plansB == null", capture)
        self.assertIn("row.plansA = OpexCarto2FreezePlans(plan.plansA)", capture)
        self.assertIn("row.plansB = OpexCarto2FreezePlans(plan.plansB)", capture)
        frozen = self.fn("OpexCarto2FreezePlans")
        self.assertIn("lead = p.lead", frozen)
        self.assertIn("station_exit = p.station_exit", frozen)
        self.assertIn("row.livePlans = true", capture)
        self.assertRegex(search, r'row\.plansA\s*==\s*null\s*&&\s*row\.source\s*!=\s*"live"',
                         "Do not manufacture virtual endpoints for real live candidates")
        self.assertRegex(log,
                         r'"\s+source="\s*\+\s*row\.source\s*\+\s*'
                         r'"\s+live_plans="\s*\+\s*\(\s*row\.livePlans\s*\?\s*1\s*:\s*0\s*\)',
                         "SEARCH must emit a conditional real-plan flag, not an unconditional 0/1")

    def test_free_and_guided_reuse_one_frozen_endpoint_snapshot_per_pair(self):
        row = self.fn("OpexCarto2NewRow")
        start = self.fn("OpexCarto2StartSearch")
        for field in ("plansA", "plansB"):
            self.assertRegex(row, rf"\b{field}\s*=",
                             "Pair must own stable endpoint plans through both A* arms")
            self.assertRegex(start, rf"\brow\.{field}\b",
                             "The A* arm must consume the pair's cached endpoint list")
        self.assertRegex(start, r"local\s+a\s*=\s*row\.plansA\b")
        self.assertRegex(start, r"local\s+b\s*=\s*row\.plansB\b")
        self.assertRegex(start, r"OpexCreateRailPathfinder\(\s*(?:a|row\.plansA)\s*,\s*"
                         r"(?:b|row\.plansB)\s*,",
                         "Both free and guided must receive the same row-owned endpoint snapshot")
        self.assertRegex(start, r'row\.plansA\s*==\s*null|mode\s*==\s*"free"',
                         "Live/virtual endpoints may be initialized once, never reselected for guided")
        self.assertIn('mode == "guided"', start)
        self.assertIn('row.guideTiles', start)

    def test_unmapped_route_cannot_masquerade_as_guided_astar(self):
        start = self.fn("OpexCarto2StartSearch")
        self.assertRegex(start,
                         r'mode\s*==\s*"guided"\s*&&\s*row\.route\s*<\s*0',
                         "A missing Dijkstra route has no guide: record that outcome separately")
        self.assertIn('row.guideTiles', start)

    def test_live_plan_capture_never_changes_endpoints_after_first_search_starts(self):
        capture = self.fn("OpexCarto2CaptureLivePlans")
        new_row = self.fn("OpexCarto2NewRow")
        search = self.fn("OpexCarto2StartSearch")
        self.assertRegex(new_row, r"planFrozen\s*=\s*false")
        self.assertRegex(search, r"row\.planFrozen\s*=\s*true",
                         "Freeze endpoint identity for both arms at first search")
        self.assertRegex(capture,
                         r"if\s*\(\s*row\.planFrozen\s*\|\|\s*row\.free\s*!=\s*null"
                         r"\s*\|\|\s*row\.plansA\s*!=\s*null\s*\|\|\s*"
                         r"\(\s*s\.search\s*!=\s*null\s*&&\s*s\.search\.row\s*==\s*row\s*\)\s*\)"
                         r"\s*return\s*;",
                         "Reject late live-plan capture when plans frozen, free resolved or search active")
        self.assertLess(capture.index("row.planFrozen"), capture.index("row.plansA = OpexCarto2FreezePlans"))
        self.assertIn("row.plansA = OpexCarto2FreezePlans(plan.plansA)", capture)
        self.assertIn("row.plansB = OpexCarto2FreezePlans(plan.plansB)", capture)

    def test_city_measurement_is_not_town_authority_proxy(self):
        read = self.fn("OpexCarto1ReadBlock", "probe_carto1.nut")
        self.assertIn("OpexV308Arm(bx, by, 1)", read)
        self.assertNotRegex(read, r"\bs\.town\b")
        self.assertIn("s.house", read)
        self.assertIn("s.road", read)
        probe = self.code["probe_carto2.nut"]
        self.assertNotIn("AITile.GetTownAuthority(", probe)
        self.assertRegex(probe, r"\bAITownList\s*\(",
                         "Enumerate actual towns, not zones of municipal authority")
        self.assertRegex(probe, r"\bAITown\.GetLocation\s*\(",
                         "Locate real town centers before counting crossed towns")
        self.assertRegex(probe, r'"\s+(?:real_towns|town_ids|town_count)="',
                         "Emit a separate, real-town count in CARTO2_COST, not route_town")

    def test_town_inventory_is_supplementary_and_exposes_partial_status(self):
        init = self.fn("OpexCarto2Init")
        row = self.fn("OpexCarto2NewRow")
        scan = self.fn("OpexCarto2TownStep")
        step = self.fn("OpexCarto2Step")
        record = self.fn("OpexCarto2RecordBlock")
        cost = self.fn("OpexCarto2FinishMap")
        summary = self.fn("OpexCarto2Summary")
        self.assertRegex(init, r"\btownScanDone\s*=\s*false")
        self.assertRegex(init, r"\btownCenters\s*=\s*\{\s*\}")
        self.assertRegex(row, r"\brealTowns\s*=\s*0",
                         "Access to missing row.realTowns is a fatal Squirrel slot error")
        self.assertIn("AITownList()", scan)
        self.assertIn("AITown.GetLocation(id)", scan)
        self.assertIn("row.realTowns", record)
        self.assertIn("OpexCarto2TownStep(s)", step)
        # Do NOT gate the main map on completion of a supplementary inventory.
        # Its provisional value must be explicitly flagged as unknown until
        # enumeration finishes; built houses and roads remain valid meanwhile.
        self.assertRegex(cost, r'"\s+real_towns="\s*\+\s*'
                         r'\(\s*s\.townScanDone\s*\?\s*row\.realTowns\s*:\s*-1\s*\)')
        self.assertRegex(cost, r'"\s+town_centers_complete="\s*\+\s*'
                         r'\(\s*s\.townScanDone\s*\?\s*1\s*:\s*0\s*\)')
        self.assertRegex(summary, r'"\s+town_centers_complete="\s*\+\s*'
                         r'\(\s*s\.townScanDone\s*\?\s*1\s*:\s*0\s*\)')
        for observed in ('row.houses += item.house', 'row.roads += item.road'):
            self.assertIn(observed, record)
        self.assertIn('" houses=" + row.houses + " roads=" + row.roads', cost)

    def test_three_seed_five_year_paired_analysis_and_provenance_fixture(self):
        """Three *synthetic* game logs, not a claimed completed engine campaign."""
        from sweeps.analyze_carto2 import analyze_sources, validate_campaign

        self.assertEqual(EXPERIMENT_SEEDS, (42, 100, 999))
        self.assertEqual(EXPERIMENT_END_YEAR, 1974)
        self.assertIn('" years=5 seed="', self.fn("OpexCarto2Init"))
        self.assertRegex(self.fn("OpexCarto2Step"),
                         r"year\s*>\s*OPEX_START_YEAR\s*\+\s*4")
        pair_log = self.fn("OpexCarto2Step")
        search_log = self.fn("OpexCarto2LogSearch")
        self.assertIn('" key=" + row.key', pair_log)
        self.assertIn('" key=" + row.key', search_log)
        self.assertIn('" mode=" + q.mode', search_log)

        def event(day, tag, **fields):
            return ("DEBUG [AI] OPEX " + day + " " + tag + " "
                    + " ".join(f"{k}={v}" for k, v in fields.items()) + "\n")

        sources = []
        for seed in EXPERIMENT_SEEDS:
            # A pair may differ across worlds; both arms of that seed must
            # share a physical identity, key, endpoints and terminal year.
            key = f"freight:1:{seed}:{seed + 240}"
            lines = [
                event("1970-01-01", "CARTO2_START", seed=seed, mapx=1024,
                      mapy=1024, years=5, start_year=1970, source_sha="fixture-sha"),
                event("1974-12-31", "CARTO2_PAIR", id=0, key=key, src=seed,
                      dst=seed + 240, dist=240, source="long"),
                event("1974-12-31", "CARTO2_COST", id=0, key=key,
                      map_mode="line", line_ops=70, band_ops=-1,
                      line_ticks=0, band_ticks=-1,
                      line_cells=10, band_cells=-1, houses=3, roads=2,
                      real_towns=-1, town_centers_complete=0),
                event("1974-12-31", "CARTO2_SEARCH", id=0, key=key,
                      mode="free", phase="end", outcome="OK", iters=200,
                      ops=5400, ticks=0, ready=1, path_dist=252, live_plans=0),
                event("1974-12-31", "CARTO2_SEARCH", id=0, key=key,
                      mode="guided", phase="end", outcome="OK", iters=120,
                      ops=3400, ticks=0, ready=1, path_dist=246, live_plans=0),
                event("1974-12-31", "CARTO2_SUMMARY", phase="done", pairs=1,
                      mapped=1, completed=1, ready=1, year=1974),
            ]
            sources.append((f"reference_seed{seed}_r0.log", lines))

        result = {
            "campaign_id": "carto2_3x5_fixture", "years": 5,
            "start_year": 1970, "expected_last_year": 1974,
            "source_bundle_sha256": "fixture-bundle", "seeds": list(EXPERIMENT_SEEDS),
            "repeats": 1, "map_size": 10,
            "games": [
                {"policy_id": "reference", "seed": seed, "repeat": 0,
                 "engine_log_path": f"/work/fixture/reference_seed{seed}_r0.log",
                 "game_status": "complete", "game_ok": True,
                 "unattributed_errors": [], "companies": {"OpexAI": {"horizon_complete": True}}}
                for seed in EXPERIMENT_SEEDS],
        }
        manifest = {
            "campaign_id": "carto2_3x5_fixture",
            "git": {"sha": "fixture-sha"},
            "source_bundle": {"sha256": "fixture-bundle"},
            "execution": {"options": {"script_debug": True,
                                      "docker_image_id": "sha256:fixture"}},
            "configuration": {"years": 5, "starting_year": 1970,
                              "seeds": list(EXPERIMENT_SEEDS),
                              "repeats": 1, "map_size": 10},
            "games": [{"policy_id": "reference", "seed": seed, "repeat": 0}
                      for seed in EXPERIMENT_SEEDS],
        }
        report = analyze_sources(sources)
        validate_campaign(report, result, manifest)
        policy = report["policies"]["reference"]
        self.assertTrue(policy["complete"], policy["errors"])
        self.assertEqual(len(policy["games"]), 3)
        self.assertEqual(policy["aggregate"]["pairs"], 3)
        self.assertEqual(policy["aggregate"]["saved_iters"]["sum"], 3 * 80)
        self.assertEqual(policy["aggregate"]["saved_ops"]["sum"], 3 * 2000)
        self.assertEqual(policy["aggregate"]["free_ready1974"], 3)
        self.assertEqual(policy["aggregate"]["guided_ready1974"], 3)
        for game in policy["games"]:
            self.assertEqual(game["pairs_valid"], 1)
            self.assertEqual(game["rows"][0]["saved_ticks"], 0)

        # A mismatched guided endpoint identity is not a paired comparison.
        broken = list(sources[0][1])
        broken[4] = broken[4].replace(" key=freight:", " key=WRONG:")
        invalid = analyze_sources([(sources[0][0], broken)])
        self.assertFalse(invalid["policies"]["reference"]["log_complete"])

    def test_line_only_corridor_and_bounded_dijkstra(self):
        corridor = self.fn("OpexCarto2LineStep")
        dijkstra = self.fn("OpexCarto1RouteStep", "probe_carto1.nut")
        map_step = self.fn("OpexCarto2Step")
        finish = self.fn("OpexCarto2FinishMap")
        # CARTO2b scans only Bresenham center blocks, not the ±1 band;
        # <=420 physical 8x8 blocks, one Dijkstra node per call.
        self.assertRegex(corridor, r'row\.ids\.len\(\)\s*>\s*420\s*\?\s*"skip"')
        self.assertRegex(corridor, r"row\.member\[id\]\s*<-\s*true")
        self.assertRegex(corridor, r"row\.lineMember\[id\]\s*<-\s*true")
        self.assertIn("row.ids.append(id)", corridor)
        self.assertNotRegex(corridor, r"\bfor\s*\(\s*local\s+(?:ox|oy)\b")
        self.assertIn("OpexCarto2LineStep(CARTO1_STATE, row)", self.fn("OpexCarto2MapSlice"))
        self.assertNotIn("OpexCarto1CorridorStep", self.fn("OpexCarto2MapSlice"))
        self.assertRegex(dijkstra, r'GetOpsTillSuspend\(\)\s*<\s*6000')
        self.assertRegex(dijkstra, r"foreach\s*\(\s*id\s*,\s*active\s+in\s+job\.frontier\s*\)")
        self.assertIn("delete job.frontier[best]", dijkstra)
        self.assertIn("job.visited[best] <- true", dijkstra)
        self.assertIn("next in job.visited", dijkstra)
        self.assertIn("next in job.member", dijkstra)
        self.assertRegex(dijkstra, r'for\s*\(\s*local\s+oy\s*=\s*-1\s*;\s*oy\s*<=\s*1')
        self.assertRegex(dijkstra, r'for\s*\(\s*local\s+ox\s*=\s*-1\s*;\s*ox\s*<=\s*1')
        self.assertRegex(map_step, r'if\s*\(\s*row\.phase\s*==\s*"route"\s*\)\s*break')
        self.assertIn("while (count < 420)", finish)
        self.assertNotRegex(dijkstra, r"\bwhile\s*\(\s*true\s*\)")

    def test_bounded_guide_tile_expansion_has_a_fixed_per_step_work_cap(self):
        guide = self.fn("OpexCarto2GuideSlice")
        cap = re.search(r'for\s*\(\s*local\s+n\s*=\s*0\s*;\s*n\s*<\s*(\d+)', guide)
        self.assertIsNotNone(cap)
        self.assertGreaterEqual(int(cap.group(1)), 1)
        self.assertLessEqual(int(cap.group(1)), 64)
        self.assertRegex(guide, r'row\.guideTilePos\s*==\s*64')
        self.assertIn("row.guidePos < row.routeIds.len()", guide)
        self.assertIn("row.guideTiles[tile] <- 0", guide)
        self.assertRegex(guide, r'AIController\.GetOpsTillSuspend\(\)\s*>=\s*\d{3,5}',
                         "The tile cap alone is not an opcode budget")
        # A tile cap does not prove the full 3x5 run can finish; latency from
        # Dijkstra, candidate selection and actual A* is still unmeasured.

    def test_line_only_cost_and_band_is_explicitly_unmeasured(self):
        new = self.fn("OpexCarto2NewRow")
        corridor = self.fn("OpexCarto2LineStep")
        record = self.fn("OpexCarto2RecordBlock")
        read = self.fn("OpexCarto1ReadBlock", "probe_carto1.nut")
        for field in ("lineMember", "lineCost", "lineOps", "bandOps", "lineBlocks"):
            self.assertRegex(new, rf"\b{field}\s*=")
        self.assertRegex(new, r"bandOps\s*=\s*-1")
        self.assertRegex(corridor, r"row\.lineMember\[[^]]+\]\s*<-\s*true")
        self.assertRegex(corridor, r"row\.member\[id\]\s*<-\s*true")
        self.assertRegex(record, r"if\s*\(\s*id\s+in\s+row\.lineMember\s*\)")
        for required in ("row.lineCost += item.cost", "row.lineOps += ops",
                         "row.lineBlocks++"):
            self.assertIn(required, record)
        self.assertNotIn("row.bandOps += ops", record)
        for field in ("cost", "house", "road", "relief", "water"):
            self.assertRegex(read, rf"\b{field}\s*=")
        map_slice = self.fn("OpexCarto2MapSlice")
        self.assertIn("CARTO1_STATE.cache[id]", map_slice)
        self.assertIn("CARTO1_STATE.ops - priorOps", map_slice)
        log = self.fn("OpexCarto2FinishMap")
        for metric in ("map_mode=line", "line_ops=", "band_ops=", "line_cells=",
                       "band_cells=-1", "line_cost=", "quote="):
            self.assertIn(metric, log)
        self.assertRegex(log, r'"\s+band_ticks=-1"')

    def test_live_search_pauses_then_resumes_same_shadow_astar_without_cancel(self):
        init = self.fn("OpexCarto2Init")
        new = self.fn("OpexCarto2StartSearch")
        advance = self.fn("OpexCarto2Slice")
        step = self.fn("OpexCarto2Step")
        yield_live = self.fn("OpexCarto2YieldToLive")
        self.assertRegex(init, r"\bsearch\s*=\s*null")
        self.assertIn("OpexCarto1LongRailBusy(ai)", new)
        self.assertIn("ai._railSearch != null", new)
        self.assertIn("OpexCarto1LongRailBusy(ai)", advance)
        self.assertIn("ai._railSearch != null", advance)
        self.assertRegex(advance, r"search\.paused\s*=\s*true\s*;\s*return\s*;",
                         "Live A* must pause shadow without killing its frontier")
        self.assertRegex(advance, r"search\.paused\s*=\s*false\s*;",
                         "After rail live releases control, continue the same A* object")
        self.assertIn("s.search.paused = true", yield_live)
        self.assertNotRegex(advance + yield_live, r"\b(?:search|s\.search)\.pf\s*=\s*null")
        self.assertNotIn('"CANCEL"', advance + yield_live)
        self.assertRegex(advance, r"\bsearch\.pf\.FindPath\(1\)")
        self.assertRegex(step, r"if\s*\(\s*row\.free\s*==\s*null\s*\)"
                         r'\s*OpexCarto2StartSearch\(ai, s, row, "free"\)')
        self.assertRegex(step, r'else\s+OpexCarto2StartSearch\(ai, s, row, "guided"\)')
        self.assertIn("s.search = null", self.fn("OpexCarto2LogSearch"))

    def test_full_turn_quantum_budget_and_zero_tick_guards(self):
        step = self.fn("OpexCarto2Step")
        map_slice = self.fn("OpexCarto2MapSlice")
        setup = self.fn("OpexCarto2StartSearch")
        advance = self.fn("OpexCarto2Slice")
        full = self.fn("OpexCarto2FullTurn")
        unsafe = self.fn("OpexCarto2Unsafe")
        self.assertIn("OpexCarto2CanTakeTurn(ai)", full)
        self.assertRegex(full, r"\bwhile\s*\(\s*!s\.stopped\s*&&\s*"
                         r"AIController\.GetTick\(\)\s*==\s*mark\.tick")
        self.assertRegex(full, r"GetOpsTillSuspend\(\)\s*>=\s*\d{3,5}\s*&&\s*n\s*<\s*\d+")
        self.assertIn("OpexCarto2Step(ai)", full)
        self.assertNotIn("AIController.Sleep(", full)
        self.assertIn('OpexCarto2Unsafe(s, "full_turn_tick")', full)
        self.assertIn("s.fullTurnOps += used", full)
        self.assertIn("s.fullTurnLeft += AIController.GetOpsTillSuspend()", full)
        self.assertRegex(full, r"s\.search\s*!=\s*null\s*&&\s*s\.search\.paused")
        self.assertRegex(step, r"for\s*\(\s*local\s+i\s*=\s*0\s*;\s*i\s*<\s*3")
        self.assertIn('OpexCarto2Unsafe(s, "mapping_tick")', step)
        self.assertIn("AIController.GetTick() != mark.tick", map_slice)
        self.assertRegex(setup, r"GetOpsTillSuspend\(\)\s*<\s*\d{4}")
        self.assertIn('OpexCarto2Unsafe(s, "search_setup_tick")', setup)
        self.assertIn("AIController.GetOpsTillSuspend() < OpexCarto2AstarReserve(s)",
                      advance,
                      "The atomic guard is dynamic and must never revert to a fixed 6500 limit")
        self.assertIn("FindPath(1)", advance)
        self.assertIn("if (used > s.peakAstarOps)", advance)
        self.assertIn("AIController.GetTick() - mark.tick", advance)
        self.assertIn('OpexCarto2Unsafe(s, "astar_atomic_tick")', advance)
        self.assertRegex(unsafe, r"s\.search\s*=\s*null")
        self.assertRegex(unsafe, r"s\.stopped\s*=\s*true")
        self.assertIn('OpexCarto2Summary(s, "unsafe")', unsafe)

    def test_astar_atomic_budget_is_admitted_only_at_start_of_a_fresh_full_turn(self):
        init = self.fn("OpexCarto2Init")
        reserve = self.fn("OpexCarto2AstarReserve")
        full = self.fn("OpexCarto2FullTurn")
        step = self.fn("OpexCarto2Step")
        slice_ = self.fn("OpexCarto2Slice")

        # Observed atomic peak on 1024² seed100 was 7844 opcodes. The old
        # unknown=4500/max=6500 reserve cannot protect the same tick.
        self.assertRegex(reserve, r"reserve\s*=\s*9[0-9]{3}")
        self.assertRegex(reserve, r"s\.peakAstarOps\s*\+\s*[1-9][0-9]{3}")
        self.assertNotRegex(reserve, r"reserve\s*>\s*6500")
        self.assertNotRegex(reserve, r"reserve\s*=\s*6500")
        self.assertRegex(init, r"\bastarTurnTick\s*=\s*-1")
        self.assertRegex(init, r"\bastarTurnLeft\s*=\s*0")

        # Snapshot of admission at the beginning of a full quantum: a
        # constructor/setup that starts search_run mid-turn MUST wait for
        # the next turn and cannot immediately spend the remaining 5k ops.
        self.assertRegex(full, r's\.phase\s*==\s*"search_run"')
        self.assertIn("OpexCarto2AstarReserve(s)", full)
        self.assertIn("s.astarTurnTick = mark.tick", full)
        self.assertIn("s.astarTurnLeft = AIController.GetOpsTillSuspend()", full)
        self.assertIn('s.astarTurnTick != mark.tick', full)
        self.assertIn("s.astarTurnTick = -1", full)
        self.assertLess(full.index("s.astarTurnTick = mark.tick"),
                        full.index("OpexCarto2Step(ai)"))

        # An atomic step can start only at admission tick, with >=9k
        # opcodes still available and bounded pre-Search overhead.
        self.assertIn("s.astarTurnTick != AIController.GetTick()", slice_)
        self.assertIn("s.astarTurnLeft - AIController.GetOpsTillSuspend()", slice_)
        self.assertIn("s.astarTurnLeft - AIController.GetOpsTillSuspend() > 500", slice_)
        self.assertIn("AIController.GetOpsTillSuspend() < OpexCarto2AstarReserve(s)", slice_)
        self.assertLess(slice_.index("s.astarTurnTick = -1"),
                        slice_.index("search.pf.FindPath(1)"),
                        "Disarm BEFORE the atomic call; at most one per whole turn")
        self.assertRegex(step, r's\.phase\s*!=\s*"search_run"\s*&&'
                         r'\s*!s\.townScanDone',
                         "Even a small town scan before FindPath would consume the reserve")
        self.assertIn('if (s.phase == "search_run" && s.astarTurnTick != mark.tick) break;', full,
                      "Do not attempt to call Slice after the setup starts a new pf")
        self.assertRegex(full, r'CARTO2_STATE\.phase\s*==\s*"search_run"[\s\S]*?'
                         r'OpexCarto2AstarReserve\(CARTO2_STATE\)\s*\+\s*100',
                         "Yield the entire tick to the live loop when admission is impossible")
        self.assertNotIn("OpexCarto2AstarReserve(s) + 100", self.fn("OpexCarto2CanTakeTurn"),
                         "Worker1 owns CanTakeTurn; this fix must not change its gate")

    def test_safety_is_idempotent_when_one_atomic_step_crosses_same_tick(self):
        unsafe = self.fn("OpexCarto2Unsafe")
        full = self.fn("OpexCarto2FullTurn")
        map_slice = self.fn("OpexCarto2MapSlice")
        self.assertRegex(unsafe, r"if\s*\(\s*s\.stopped\s*\)\s*return\s*;")
        self.assertLess(unsafe.index("if (s.stopped) return;"),
                        unsafe.index("s.ticks++"))
        self.assertLess(unsafe.index("if (s.stopped) return;"),
                        unsafe.index('OpexDecide("CARTO2_SAFETY"'))
        self.assertIn('OpexCarto2Unsafe(s, "astar_atomic_tick")',
                      self.fn("OpexCarto2Slice"))
        self.assertIn('OpexCarto2Unsafe(s, "full_turn_tick")', full)
        self.assertIn("row.ticks++", map_slice)
        self.assertNotIn("s.ticks++", map_slice,
                         "A mapping overrun is counted once by OpexCarto2Unsafe")
        self.assertRegex(full, r"if\s*\(\s*!crossed\s*&&"
                         r"\s*AIController\.GetOpsTillSuspend\(\)\s*>=\s*2500\s*\)",
                         "Crossed ticks must not be logged as healthy full turns")

    def test_virtual_endpoint_early_exit_accounts_for_setup_ops_and_ticks(self):
        setup = self.fn("OpexCarto2StartSearch")
        no_endpoints = re.search(r"if\s*\(\s*a\.len\(\)\s*==\s*0\s*\|\|\s*"
                                 r"b\.len\(\)\s*==\s*0\s*\)\s*\{(.*?)\}",
                                 setup, re.DOTALL)
        self.assertIsNotNone(no_endpoints, "Missing endpoint failure branch")
        self.assertIn("OpexOpsMeasureEnd(mark)", no_endpoints.group(1),
                      "Endpoint discovery must account for opcodes even without a pathfinder")
        self.assertIn("AIController.GetTick()", no_endpoints.group(1),
                      "Endpoint failure must still verify that setup did not cross a tick")

    def test_empty_astar_frontier_is_nopa_and_guide_preparation_is_bounded(self):
        advance = self.fn("OpexCarto2Slice")
        self.assertTrue(re.search(r"if\s*\(\s*path\s*==\s*null\s*\)\s*\{\s*"
                                  r'search\.outcome\s*=\s*"NOPA"', advance),
                        "Empty A* frontier is NOPA; DEAD is reserved for a time limit")
        guide = self.fn("OpexCarto2GuideSlice")
        self.assertRegex(guide, r"for\s*\(\s*local\s+n\s*=\s*0\s*;\s*n\s*<\s*\d+")
        self.assertIn("row.guideTiles[tile] <- 0", guide)
        self.assertIn("row.guidePos < row.routeIds.len()", guide)
        search = self.fn("OpexCarto2StartSearch")
        self.assertIn('mode == "guided"', search)
        self.assertRegex(search, r"OpexCreateRailPathfinder\([^;]*\bguide\b")

    def test_ready_cache_has_bounded_ttl_and_truthful_search_outcome(self):
        log = self.fn("OpexCarto2LogSearch")
        summary = self.fn("OpexCarto2Summary")
        self.assertRegex(log, r'\bready\s*=\s*q\.outcome\s*==\s*"OK"\s*&&\s*'
                         r'q\.pathDist\s*>=\s*0')
        self.assertRegex(log, r'row\.expires\s*=\s*AIDate\.GetCurrentDate\(\)\s*\+\s*180')
        self.assertRegex(log, r"s\.ready\[row\.key\]\s*<-\s*row\.expires")
        self.assertRegex(summary, r"expiry\s*>=\s*date")
        # SEARCH.ready records a successful path *when searched*, whereas
        # SUMMARY.ready counts only entries whose TTL is still valid today.
        # The analyzer's 'ready1974' means 'found by 1974', not 'unexpired on
        # December 31, 1974'.  Keep those two measures deliberately distinct.
        self.assertRegex(log, r'\bAIDate\.GetYear\(AIDate\.GetCurrentDate\(\)\)')

    def test_probe_jobs_and_ready_ttl_do_not_persist_across_save_load(self):
        start = self.fn("OpexAI::Start", "main.nut")
        self.assertRegex(start, r"\bOpexLoadSettings\(\)\s*;\s*"
                         r"if\s*\(\s*CARTO1_SHADOW\s*\)\s*CARTO1_STATE\s*=\s*null")
        self.assertRegex(start, r"if\s*\(\s*CARTO2_SHADOW\s*\)\s*"
                         r"CARTO2_STATE\s*=\s*null")
        self.assertLess(start.index("CARTO2_STATE = null"),
                        start.index("this._reconcileAfterLoad()"))
        for name in ("OpexAI::Save", "OpexAI::Load",
                     "OpexAI::_reconcileAfterLoad"):
            persist = self.fn(name, "persist.nut")
            self.assertNotRegex(persist, r"\b(?:CARTO2_STATE|CARTO2_IDLE_READY|carto2|OpexCarto2)\b")

    def test_squirrel_new_probe_avoids_known_compilation_traps(self):
        probe = self.code["probe_carto2.nut"]
        self.assertNotRegex(probe, r"\.find\s*\(")
        self.assertNotRegex(probe, r"\bfunction\s*\(")
        self.assertNotRegex(probe, r"\bconst\s+\w+\s*=\s*(?!-?\d+\s*;|true\s*;|false\s*;|\"[^\"]*\"\s*;)")
        reserved = ("base", "parent", "static", "delegate", "clone",
                    "resume", "yield", "vargc", "vargv", "constructor", "instanceof")
        for token in reserved:
            with self.subTest(token=token):
                self.assertNotRegex(probe, rf"\b(?:local|foreach\s*\()\s*{token}\b")


if __name__ == "__main__":
    unittest.main()
