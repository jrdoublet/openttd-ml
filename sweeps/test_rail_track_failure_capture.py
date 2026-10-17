"""UR-15a: static equivalence to the pre-extraction rail builder (856c82c).

Inlining the common capture must restore the original construction and
diagnostics exactly, modulo comments/whitespace. The later freight TRKFAIL
memory is checked separately and excluded from the historical comparison.
This is not a NoAI VM test.
"""
import hashlib
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
PRE_EXTRACTION_HASHES = {
    "OpexBuildTrack": "aa1b869d523c371e42e8667b24b297dd47dbd49061e474e13340d7c73cf7c081",
    "OpexTestRailTrack": "e58b4b7173e096515417348b7b2211d42e3c2efe3c23226502dd8fd262e1cf61",
    "OpexExecuteRailPlan": "f165d26650fea5c6926f2bb53c4d92da6f2f85517e03567b3d4d61993c2ba037",
}


def function_body(source, name):
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]
    raise AssertionError("Unclosed function: " + name)


def digest(body):
    # Preserve string literals exactly, including spaces in diagnostic logs.
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/|//[^\n]*|\s+', re.S)
    body = tokens.sub(lambda m: m.group() if m.group()[0] in ('"', "'") else "", body)
    return hashlib.sha256(body.encode()).hexdigest()


def without_freight_memory(body):
    """Project the current builder onto the original capture/rollback contract.

    The freight failure memory (rail_freight_trkfail_memory) was removed on
    2026-10-17; what remains is publishing the original A-side lead in the
    failure log and the end-connection helper. Require each
    exact addition so that unrelated builder edits still invalidate the SHA.
    """
    replacements = (
        (
            '      if ("lead" in planA) fields += " leada=" + planA.lead;\n',
            '',
        ),
        (
            '  local connected = trackFailed == 0 &&\n'
            '      OpexRailEndConnected(planA.station_exit, tiles[1], tiles[2], "A") &&\n'
            '      OpexRailEndConnected(planB.station_exit, tiles[last - 1], tiles[last - 2], "B");',
            '  local connected = trackFailed == 0 &&\n'
            '      AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&\n'
            '      AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);',
        ),
    )
    for addition, original in replacements:
        if body.count(addition) != 1:
            raise AssertionError("Freight memory addition missing or duplicated: " + addition)
        body = body.replace(addition, original, 1)
    return body


def without_v199(body):
    """Project the current builder onto the pre-V199 capture contract."""
    body = re.sub(r'local isDouble = .*?local retriesCount = 0;', '', body, flags=re.S)
    body = re.sub(r'// V199 : Demolition.*?// V199 : Reprise locale', '// V199 : Reprise locale', body, flags=re.S)
    body = re.sub(r'// V199 : Reprise locale.*?if \(!ok\) \{', 'if (!ok) {', body, flags=re.S)
    body = re.sub(r'\} else if \(V199_ROBUST_BUILD && isDouble\) \{.*?\}\n  \}', '}\n  }', body, flags=re.S)
    body = re.sub(r'if \(V199_ROBUST_BUILD && signalsBuiltCount > 0.*?\n  \}', '', body, flags=re.S)
    return body


def without_v199_v163_plan(body):
    """Project OpexExecuteRailPlan onto its pre-V199/V163 form.

    V199 (af1fcd3) levels the homeward track under V199_ROBUST_BUILD and passes
    double-track options to OpexBuildTrack; V163 (78acaa8) passes the second
    cargo, whose helpers return OpexBuildTrains' own defaults (-1, 0) when the
    line has no second cargo. Each exact addition is required.
    """
    replacements = (
        ('    if (V199_ROBUST_BUILD) {\n'
         '      OpexV199RebuildForHomeward(tiles, 1, V199_LEVEL_BUDGET_K);\n'
         '    }\n', '', 1),
        ('      local trackOpt2 = { isDouble = true, trainLength = candidate.platformLength, initialBudget = plan.iterationBudget };\n'
         '      local tFail = OpexBuildTrack(tiles2, plan.structures2, null, trackOpt2);',
         '      local tFail = OpexBuildTrack(tiles2, plan.structures2);', 1),
        ('candidate.wagons, candidate.platformLength, false,\n', 'candidate.wagons, candidate.platformLength, false', 2),
    )
    for addition, original, count in replacements:
        if body.count(addition) != count:
            raise AssertionError("V199/V163 addition missing or duplicated: " + addition)
        body = body.replace(addition, original)
    body = re.sub(r'false\s*OpexV163Cargo2\(candidate\), OpexV163Wagons2\(candidate\)\);', 'false);', body)
    return body


class TestRailTrackFailureCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (AI / "builder_rail.nut").read_text(encoding="utf-8")

    def test_inlining_capture_restores_original_builder(self):
        helper = function_body(self.source, "OpexRailCaptureTrackFailure")
        body = function_body(self.source, "OpexBuildTrack")
        for kind in ('"connect"', "segmentKind"):
            call = ("OpexRailCaptureTrackFailure(failure, tiles, i, cur, "
                    + kind + ", err, manhPrev, manhNext);")
            self.assertEqual(body.count(call), 1)
            body = body.replace(call, helper.replace("failure.kind <- kind;",
                                                    "failure.kind <- " + kind + ";"))
        self.assertEqual(digest(without_v199(body)), PRE_EXTRACTION_HASHES["OpexBuildTrack"])

    def test_testmode_twin_is_unchanged(self):
        self.assertEqual(digest(function_body(self.source, "OpexTestRailTrack")),
                         PRE_EXTRACTION_HASHES["OpexTestRailTrack"])

    def test_failure_logs_and_rollback_order_are_unchanged(self):
        current = function_body(self.source, "OpexExecuteRailPlan")
        # V237 makes the existing site-cache invalidation unconditional.
        call = "OpexAir0310InvalidateSiteValidity();"
        self.assertEqual(current.count(call), 1)
        current = current.replace(call, "if (AIR0310_SITE_VALIDITY_CACHE) " + call)
        self.assertEqual(digest(without_v199_v163_plan(without_freight_memory(current))),
                         PRE_EXTRACTION_HASHES["OpexExecuteRailPlan"])

    def test_freight_memory_removed(self):
        body = function_body(self.source, "OpexExecuteRailPlan")
        self.assertNotIn("RAIL_FREIGHT_TRKFAIL_MEMORY", self.source)
        self.assertNotIn("OpexRailTrackFailureIsPersistentPathLead", self.source)
        self.assertLess(body.index('OpexDecide("RAIL_TRACK_FAIL", fields);'),
                        body.index("OpexRollback(tiles, planA, planB, null, null);"))
        self.assertIn('result.opcodes += budget.end("build_track"); result.reason = "TRKFAIL"; return result;', body)

if __name__ == "__main__":
    unittest.main()
