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

    The three replacements correspond to the adopted freight failure memory:
    allocating the capture table, recognizing a persistent path-lead failure,
    and publishing the original A-side lead in the failure log. Require each
    exact addition so that unrelated builder edits still invalidate the SHA.
    """
    replacements = (
        (
            'if (DECISION_LOG || RAIL_GEOMETRY_GUARD\n'
            '      || (RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight")) trackFailure = {};',
            'if (DECISION_LOG || RAIL_GEOMETRY_GUARD) trackFailure = {};',
        ),
        (
            'if (trackFailed > 0 &&\n'
            '        ((RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY\n'
            '            && OpexRailTrackFailureIsPersistentGeometry(trackFailure, planA, planB))\n'
            '         || (RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight"\n'
            '             && OpexRailTrackFailureIsPersistentPathLead(trackFailure, tiles)))) {',
            'if (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY && trackFailed > 0 &&\n'
            '        OpexRailTrackFailureIsPersistentGeometry(trackFailure, planA, planB)) {',
        ),
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
        self.assertEqual(digest(body), PRE_EXTRACTION_HASHES["OpexBuildTrack"])

    def test_testmode_twin_is_unchanged(self):
        self.assertEqual(digest(function_body(self.source, "OpexTestRailTrack")),
                         PRE_EXTRACTION_HASHES["OpexTestRailTrack"])

    def test_failure_logs_and_rollback_order_are_unchanged(self):
        current = function_body(self.source, "OpexExecuteRailPlan")
        self.assertEqual(digest(without_freight_memory(current)),
                         PRE_EXTRACTION_HASHES["OpexExecuteRailPlan"])

    def test_freight_memory_does_not_skip_failure_diagnostics_or_rollback(self):
        body = function_body(self.source, "OpexExecuteRailPlan")
        self.assertEqual(body.count('RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight"'), 2)
        self.assertLess(body.index("local trackFailed = OpexBuildTrack(tiles, plan.structures, trackFailure);"),
                        body.index("OpexRailTrackFailureIsPersistentPathLead(trackFailure, tiles)"))
        self.assertLess(body.index("OpexRailTrackFailureIsPersistentPathLead(trackFailure, tiles)"),
                        body.index('OpexDecide("RAIL_TRACK_FAIL", fields);'))
        self.assertLess(body.index('OpexDecide("RAIL_TRACK_FAIL", fields);'),
                        body.index("OpexRollback(tiles, planA, planB, null, null);"))
        self.assertIn('result.opcodes += budget.end("build_track"); result.reason = "TRKFAIL"; return result;', body)


if __name__ == "__main__":
    unittest.main()
