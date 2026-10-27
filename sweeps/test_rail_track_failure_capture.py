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
# rebasé le 24/10 : eec5db81 (revue R11, helper partagé OpexBridgeSortBySpeed)
PRE_EXTRACTION_HASHES = {
    "OpexBuildTrack": "f41b05fb24607dfc781ac3f740e90773e4016329ca1643ba2ef12a7eecf3815a",
    "OpexTestRailTrack": "ee1f11817b57d8d37dbcaefafb536e31e2fe7f91d2fd4f50177bddecd0477e25",
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


def without_v233l_pose(source):
    """Project builder_rail.nut to origin/master before the historical capture.

    Pose-time V233L repair is several reviewed hunks; the OFF fixture as a
    whole restores the pre-V233L function, including V296a log counts.
    """
    from v233_long_good_legacy import off_source
    return off_source("builder_rail.nut", source)


def without_v199(body):
    """Project the current builder onto the pre-V199 capture contract."""
    body = re.sub(r'local isDouble = .*?local retriesCount = 0;', '', body, flags=re.S)
    body = re.sub(r'// V199 : Demolition.*?// V199 : Reprise locale', '// V199 : Reprise locale', body, flags=re.S)
    body = re.sub(r'// V199 : Reprise locale.*?if \(!ok\) \{', 'if (!ok) {', body, flags=re.S)
    body = re.sub(r'\} else if \(V199_ROBUST_BUILD && isDouble\) \{.*?\}\n  \}', '}\n  }', body, flags=re.S)
    body = re.sub(r'if \(V199_ROBUST_BUILD && signalsBuiltCount > 0.*?\n  \}', '', body, flags=re.S)
    return body


def without_v296a(body):
    """Project OpexBuildTrack onto its pre-V296a form (grouped track laying).

    V296a adds the `batch` declaration, one guarded block at the top of the
    loop and an OpexV296aLog(batch) before each of the 3 returns. Each exact
    addition is required, so that unrelated builder edits still change the SHA.
    """
    decl = re.search(r'\n  /\* V296a : .*?\? \{ runs = 0, tiles = 0, single = 0, fallbacks = 0, mismatch = 0, skipUntil = 0 \} : null;', body, re.S)
    if decl is None:
        raise AssertionError("V296a declaration missing")
    body = body[:decl.start()] + body[decl.end():]
    block = re.search(r'    if \(batch != null && i > batch\.skipUntil\) \{.*?\n        batch\.single\+\+;\n      \}\n    \}\n', body, re.S)
    if block is None:
        raise AssertionError("V296a loop block missing")
    body = body[:block.start()] + body[block.end():]
    if body.count("OpexV296aLog(batch);") != 3:
        raise AssertionError("V296a logs missing or duplicated")
    return re.sub(r'OpexV296aLog\(batch\);\s*', '', body)


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
        source = without_v233l_pose(self.source)
        helper = function_body(source, "OpexRailCaptureTrackFailure")
        body = function_body(source, "OpexBuildTrack")
        for kind in ('"connect"', "segmentKind"):
            call = ("OpexRailCaptureTrackFailure(failure, tiles, i, cur, "
                    + kind + ", err, manhPrev, manhNext);")
            self.assertEqual(body.count(call), 1)
            body = body.replace(call, helper.replace("failure.kind <- kind;",
                                                    "failure.kind <- " + kind + ";"))
        self.assertEqual(digest(without_v199(without_v296a(body))),
                         PRE_EXTRACTION_HASHES["OpexBuildTrack"])

    def test_testmode_twin_is_unchanged(self):
        self.assertEqual(digest(function_body(self.source, "OpexTestRailTrack")),
                         PRE_EXTRACTION_HASHES["OpexTestRailTrack"])

    def test_failure_logs_and_rollback_order_are_unchanged(self):
        current = function_body(self.source, "OpexExecuteRailPlan")
        # V233 graft and its fail-before-spend branch were retired. Preserve
        # the complete historical rollback/hash check below without stripping
        # an obsolete guard that no longer exists in the executable source.
        self.assertNotIn("V233_GOODS_GRAFT", current)
        self.assertNotIn("OpexV233SpendAllowed", current)
        # V237 makes the existing site-cache invalidation unconditional.
        call = "OpexAir0310InvalidateSiteValidity();"
        self.assertEqual(current.count(call), 1)
        current = current.replace(call, "if (AIR0310_SITE_VALIDITY_CACHE) " + call)
        # V246 freezes the existing quote block ON; restore only that guard
        # for comparison with the original builder, keeping its entire body.
        self.assertNotIn("RAIL_DEVIS", current)
        quote = "  {\n    local quoteFailure = {};"
        self.assertEqual(current.count(quote), 1)
        current = current.replace(quote, "  if (RAIL_DEVIS) {\n    local quoteFailure = {};")
        # V296c adds phaseOps tracking
        current = current.replace(
            "                   phaseOps = { plans = plan.phaseOps.plans, search = plan.phaseOps.search,\n                                stations = plan.phaseOps.stations, track = plan.phaseOps.track,\n                                trains = plan.phaseOps.trains },\n",
            ""
        )
        current = current.replace(
            "    local stnOps = budget.end(\"build_stations\");\n    result.opcodes += stnOps;\n    if (result.phaseOps.stations < 0) result.phaseOps.stations = 0;\n    result.phaseOps.stations += stnOps;\n    result.reason = \"STNFAIL\"; return result;",
            "    result.opcodes += budget.end(\"build_stations\"); result.reason = \"STNFAIL\"; return result;"
        )
        current = current.replace(
            "    local trkOps = budget.end(\"build_track\");\n    result.opcodes += trkOps;\n    if (result.phaseOps.track < 0) result.phaseOps.track = 0;\n    result.phaseOps.track += trkOps;\n    result.reason = \"TRKFAIL\"; return result;",
            "    result.opcodes += budget.end(\"build_track\"); result.reason = \"TRKFAIL\"; return result;"
        )
        current = current.replace(
            "  local trkOps = budget.end(\"build_track\");\n  result.opcodes += trkOps;\n  if (result.phaseOps.track < 0) result.phaseOps.track = 0;\n  result.phaseOps.track += trkOps;",
            "  result.opcodes += budget.end(\"build_track\");"
        )
        current = current.replace(
            "  local trnOps = budget.end(\"build_trains\");\n  result.opcodes += trnOps;\n  if (result.phaseOps.trains < 0) result.phaseOps.trains = 0;\n  result.phaseOps.trains += trnOps;",
            "  result.opcodes += budget.end(\"build_trains\");"
        )
        # V307R (defaut 0) : quai B anticipe ou a deux voies ; restaurer le chemin historique.
        v307r = (
            ("      if ((V307_SINK_ROOM & 2) != 0) OpexV307SinkRoomApplyMaintenance(candidate, planB);\n", ""),
            ("  if (!(\"v307Prebuilt\" in planB)) {\n    for (local i = 0; i < planB.length; i++) {\n"
             "      AITile.DemolishTile(planB.anchor + planB.step * i);\n    }\n"
             "    OpexV307SinkRoomDemolishExtra(planB);\n  }\n",
             "  for (local i = 0; i < planB.length; i++) {\n    AITile.DemolishTile(planB.anchor + planB.step * i);\n  }\n"),
            ("  local okB = (\"v307Prebuilt\" in planB) ? OpexV307SinkRoomPrebuiltReady(planB)\n"
             "      : AIRail.BuildRailStation(OpexV307SinkRoomStationAnchor(planB), planB.direction,\n"
             "                                OpexV307SinkRoomPlatforms(planB), planB.length, stIdB);\n",
             "  local okB = AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length, stIdB);\n"),
            ("  if (OpexV307SinkRoomPlatforms(planB) == 2) {\n    result.platformB.v307RoomPlatforms <- 2;\n"
             "    result.platformB.v307RoomStripAnchor <- planB.v307RoomStripAnchor;\n"
             "    result.platformB.v307RoomSide <- planB.v307RoomSide;\n  }\n", ""),
        )
        for addition, original in v307r:
            self.assertEqual(current.count(addition), 1, addition)
            current = current.replace(addition, original)
        self.assertEqual(digest(without_v199_v163_plan(without_freight_memory(current))),
                         PRE_EXTRACTION_HASHES["OpexExecuteRailPlan"])

    def test_freight_memory_removed(self):
        body = function_body(self.source, "OpexExecuteRailPlan")
        self.assertNotIn("RAIL_FREIGHT_TRKFAIL_MEMORY", self.source)
        self.assertNotIn("OpexRailTrackFailureIsPersistentPathLead", self.source)
        self.assertLess(body.index('OpexDecide("RAIL_TRACK_FAIL", fields);'),
                        body.index("OpexRollback(tiles, planA, planB, null, null);"))
        self.assertIn('result.reason = "TRKFAIL"; return result;', body)
        self.assertIn('budget.end("build_track")', body)

if __name__ == "__main__":
    unittest.main()
