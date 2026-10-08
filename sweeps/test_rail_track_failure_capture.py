"""UR-15a: static equivalence to the pre-extraction rail builder (856c82c).

Inlining the common capture must restore the original construction and
diagnostics exactly, modulo comments/whitespace. This is not a NoAI VM test.
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
        self.assertEqual(digest(function_body(self.source, "OpexExecuteRailPlan")),
                         PRE_EXTRACTION_HASHES["OpexExecuteRailPlan"])


if __name__ == "__main__":
    unittest.main()
