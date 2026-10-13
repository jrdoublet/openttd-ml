"""Host contracts and exhaustive *model* oracle for P0's redundant check.

This is deliberately not a Squirrel VM or NoAI runtime test.  It checks the
actual source contracts and models the pure OpexCandidateIsAbandoned predicate
to prove that, on a stable snapshot, the second identical result is redundant.
"""

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import copy
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
FLAG = "p0_abandon_second_check_skip"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, signature):
    data = source(name)
    start = data.index(signature)
    open_brace = data.index("{", start)
    depth = 0
    for i in range(open_brace, len(data)):
        if data[i] == "{":
            depth += 1
        if data[i] == "}":
            depth -= 1
            if depth == 0:
                return data[start : i + 1]
    raise AssertionError("Unclosed Squirrel function: " + signature)


@dataclass(eq=False)
class Site:
    anchor: int
    tile: int


@dataclass(eq=False)
class Candidate:
    ident: int
    mode: str
    site_a: Site | None = None
    site_b: Site | None = None
    airport_type: int = 1
    reuse_a: bool = False
    reuse_b: bool = False
    pair: str = ""


def air_keys(p):
    a, b = p.site_a, p.site_b
    canonical = "air|" + str(min(a.tile, b.tile)) + "|" + str(max(a.tile, b.tile))
    return {
        "pair": (canonical, f"air|{a.tile}|{b.tile}", f"air|{b.tile}|{a.tile}"),
        "site_a": f"air_site|{p.airport_type}|{a.anchor}",
        "site_b": f"air_site|{p.airport_type}|{b.anchor}",
        "town_a": f"air_town_limit|{a.tile}",
        "town_b": f"air_town_limit|{b.tile}",
    }


def abandoned(p, memory, *, town_pad, site_pad, gen_filter, remember):
    """Mirror the read-only branches of projects_generation.nut:260-283."""
    if p is None or memory is None:
        return False
    if p.mode == "air" and p.site_a is not None and p.site_b is not None:
        keys = air_keys(p)
        return (
            any(key in memory for key in keys["pair"])
            or town_pad and (
                not p.reuse_a and keys["town_a"] in memory
                or not p.reuse_b and keys["town_b"] in memory
            )
            or site_pad and (
                keys["site_a"] in memory or keys["site_b"] in memory
            )
        )
    if p.mode in ("road", "rail") and gen_filter and remember and p.pair:
        return p.pair in memory
    return False


def legacy_replay(candidates, memory, valid, *, enabled, options):
    """Models exactly the incremental call sequence, not the world validators.

    The callback represents the unchanged tail of OpexCandidateStillValid
    (line, site, subsidy, etc.). It does not mutate the snapshot.
    """
    kept = []
    rejected = 0
    check_calls = 0
    for p in candidates:
        if p is None:
            continue
        # Original projects_update check is unconditionally performed.
        check_calls += 1
        if abandoned(p, memory, **options):
            rejected += 1
            continue
        # Wrapper receives abandonAlreadyClear only on this proven path.
        if not enabled:
            check_calls += 1
            if abandoned(p, memory, **options):
                continue
        if valid[p.ident]:
            kept.append(p)
    return kept, rejected, check_calls


class P0AbandonSecondCheckSkipTests(unittest.TestCase):
    def test_flag_disabled_at_all_difficulties_and_loaded_once(self):
        info = source("info.nut")
        settings = source("settings.nut")
        globals_pre = source("globals_pre.nut")
        expression = r'name\s*=\s*"' + FLAG + r'"(?P<fields>.*?)\}\);'
        matches = list(re.finditer(expression, info, flags=re.S))
        self.assertEqual(len(matches), 1)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(matches[0].group("fields"),
                             r"\b" + difficulty + r"_value\s*=\s*0\b")
        self.assertIn("flags = AICONFIG_BOOLEAN", matches[0].group("fields"))
        self.assertIn("P0_ABANDON_SECOND_CHECK_SKIP <- false;", globals_pre)
        self.assertIn(
            'P0_ABANDON_SECOND_CHECK_SKIP = AIController.GetSetting("' + FLAG + '") != 0;',
            settings,
        )

    def test_callsite_and_optional_default_are_narrow(self):
        generation = source("projects_generation.nut")
        update = body("projects_update.nut", "function OpexIncrementalUpdateProjects(")
        candidate = body("projects_generation.nut", "function OpexCandidateStillValid(")
        wrapper = body("projects_generation.nut", "function OpexIncrementalCandidateStillValid(")

        self.assertIn("abandonedPairs = null, abandonAlreadyClear = false)", candidate)
        self.assertIn("abandonedPairs = null, abandonAlreadyClear = false)", wrapper)
        self.assertIn(
            "return OpexCandidateStillValid(p, lines, abandonedPairs, abandonAlreadyClear);",
            wrapper,
        )
        self.assertIn(
            "if (!abandonAlreadyClear && OpexCandidateIsAbandoned(p, abandonedPairs)) return false;",
            candidate,
        )
        self.assertEqual(candidate.count("OpexCandidateIsAbandoned(p, abandonedPairs)"), 1)
        self.assertLess(
            update.index("if (OpexCandidateIsAbandoned(p, abandonedPairs))"),
            update.index("if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs,"),
        )
        self.assertIn(
            "P0_ABANDON_SECOND_CHECK_SKIP))", update
        )
        self.assertEqual(update.count("P0_ABANDON_SECOND_CHECK_SKIP"), 1)
        self.assertEqual(generation.count("function OpexCandidateStillValid("), 1)

        # No other caller in the whole source tree passes a fourth argument.
        for name in ("projects.nut", "orchestrator.nut"):
            text = source(name)
            self.assertRegex(text, r"OpexIncrementalCandidateStillValid\("
                             r"[^;]*?,\s*[^;]*?,\s*[^;]*?\)")
            self.assertNotIn("P0_ABANDON_SECOND_CHECK_SKIP", text)
        for name in ("task_projects.nut", "scheduler_tasks.nut",
                     "projects_selection.nut", "projects_builders.nut"):
            self.assertNotIn("P0_ABANDON_SECOND_CHECK_SKIP", source(name))

    def test_abandon_predicate_is_read_only_and_matches_key_contract(self):
        predicate = body("projects_generation.nut", "function OpexCandidateIsAbandoned(")
        pair = body("air_planning.nut", "function OpexAirPairIsAbandoned(")
        self.assertIn("OpexAirPairIsAbandoned(abandonedPairs, plan.siteA, plan.siteB)", predicate)
        self.assertIn("OpexAirSitePaddingKey", predicate)
        self.assertIn("OpexAirTownPaddingKey", predicate)
        self.assertIn("ABANDON_GEN_FILTER && ABANDON_MEMORY", predicate)
        self.assertIn("OpexAbandonedPairKey", predicate)
        self.assertIn("legacyForward", pair)
        self.assertIn("legacyReverse", pair)
        self.assertNotRegex(predicate + pair, r"\b(?:rawset|append|push|delete)\s*\(")
        self.assertNotIn("AIDate.GetCurrentDate", predicate + pair)
        self.assertNotIn("AIController.Sleep", predicate + pair)

    def test_exhaustive_snapshot_pair_site_town_flags_and_tail_outcomes(self):
        a = Site(anchor=101, tile=1001)
        b = Site(anchor=202, tile=2002)
        air = Candidate(1, "air", a, b, airport_type=4)
        rail = Candidate(2, "rail", pair="rail|4|100|200")
        road = Candidate(3, "road", pair="road|4|100|200")
        water = Candidate(4, "water")
        fleet = Candidate(5, "fleet")
        keys = air_keys(air)
        universe = [
            keys["pair"][0], keys["pair"][1], keys["pair"][2],
            keys["site_a"], keys["site_b"], keys["town_a"], keys["town_b"],
            rail.pair, road.pair, "unrelated",
        ]
        candidates = [air, rail, road, water, fleet, None]
        tested = 0
        # Exhaust all 2^10 possible abandoned keys and 2^4 setting mixes.
        for mask in range(1 << len(universe)):
            memory = {key: True for i, key in enumerate(universe) if mask & (1 << i)}
            for flags in product((False, True), repeat=4):
                options = dict(zip(("town_pad", "site_pad", "gen_filter", "remember"), flags))
                for valid_after in (False, True):
                    valid = {p.ident: valid_after for p in candidates if p is not None}
                    before = copy.deepcopy(memory)
                    original = legacy_replay(candidates, memory, valid, enabled=False, options=options)
                    optimized = legacy_replay(candidates, memory, valid, enabled=True, options=options)
                    self.assertEqual(
                        [id(p) for p in original[0]],
                        [id(p) for p in optimized[0]],
                    )
                    self.assertEqual(original[1], optimized[1])
                    self.assertEqual(original[2] - optimized[2], len(candidates) - 1 - original[1])
                    self.assertEqual(memory, before)
                    tested += 1
        self.assertEqual(tested, 32768)

    def test_null_memory_missing_air_payload_and_reused_sites(self):
        a, b = Site(30, 300), Site(40, 400)
        base = Candidate(1, "air", a, b)
        missing = Candidate(2, "air")
        for reuse_a, reuse_b in product((False, True), repeat=2):
            project = Candidate(1, "air", a, b, reuse_a=reuse_a, reuse_b=reuse_b)
            for memory in (None, {}, {"air_town_limit|300": True},
                           {"air_site|1|40": True}):
                options = dict(town_pad=True, site_pad=True, gen_filter=True, remember=True)
                entries = [project, missing, base]
                valid = {1: True, 2: True}
                original = legacy_replay(entries, memory, valid, enabled=False, options=options)
                optimized = legacy_replay(entries, memory, valid, enabled=True, options=options)
                self.assertEqual(original[:2], optimized[:2])
                self.assertGreaterEqual(original[2], optimized[2])

    def test_transient_opt_in_never_changes_save_or_c76_v141_code(self):
        state = source("persist.nut")
        for name in ("persist.nut", "scheduler_tasks.nut", "task_projects.nut",
                     "projects_selection.nut", "projects_update.nut"):
            if name == "projects_update.nut":
                continue  # This is the one authorized caller.
            self.assertNotIn("P0_ABANDON_SECOND_CHECK_SKIP", source(name))
        self.assertNotIn("abandonAlreadyClear", state)
        self.assertNotIn("P0_ABANDON_SECOND_CHECK_SKIP", state)
        update = source("projects_update.nut")
        self.assertIn("OpexC121PlanTouchesTowns(p, airTouchedTowns)", update)
        self.assertIn("OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K)", update)
        self.assertIn("OpexProjectsStampSelectionStats(stats", update)
        self.assertIn("OpexV141RefreshPublishedAir(project, catalog, airOpsPerPlan)", update)


if __name__ == "__main__":
    unittest.main()
