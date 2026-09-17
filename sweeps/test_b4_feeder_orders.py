"""Contrats B4 : ordres des feeders bus et éligibilité aux extensions."""
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
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non fermé: {signature}")

class TestB4FeederOrders(unittest.TestCase):
    def setUp(self):
        self.builder = source("builder_road.nut")
        self.feeders = source("task_feeders.nut")
        self.candidates = source("candidates.nut")

    def test_feeder_order_helpers_encode_one_way_contract(self):
        src = function_body(self.builder, "function OpexRoadFeederSourceOrderFlags()")
        hub = function_body(self.builder, "function OpexRoadFeederHubOrderFlags()")
        self.assertIn("AIOrder.OF_NO_UNLOAD", src)
        self.assertNotIn("OF_TRANSFER", src)
        self.assertIn("AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD", hub)
        self.assertIn("C53_ORDER_NONSTOP", src)
        self.assertIn("C53_ORDER_NONSTOP", hub)

    def test_base_build_and_refleet_use_same_feeder_helpers(self):
        build = function_body(self.builder, "function OpexBuildRoadRoute(")
        refleet = function_body(self.builder, "function OpexRoadRefleet(")
        for body in (build, refleet):
            self.assertIn("OpexRoadFeederSourceOrderFlags()", body)
            self.assertIn("OpexRoadFeederHubOrderFlags()", body)

    def test_feeder_extension_inserts_city_flags_before_hub(self):
        extension = function_body(self.builder, "function OpexBuildRoadExtension(")
        marker = 'candidate.extensionType == "feeder_extension"'
        start = extension.index(marker)
        feeder_branch = extension[start : extension.index("}", start) + 1]
        self.assertIn("targetStation = stationB", feeder_branch)
        self.assertIn("flags = OpexRoadFeederSourceOrderFlags()", feeder_branch)
        self.assertIn("insertPos = targetPos", extension)

    def test_dedicated_bus_feeder_keeps_kind_for_extension_filter(self):
        build = function_body(self.feeders, "function OpexAI::_tryBuildFeeders(")
        append_start = build.index("this._lines.append({")
        append_end = build.index("});", append_start)
        line_payload = build[append_start:append_end]
        self.assertIn('mode = "road", kind = candidate.kind', line_payload)
        self.assertIn("isFeeder = true", line_payload)
        self.assertIn('purpose = "feeder"', line_payload)

    def test_mail_feeder_is_not_accidentally_made_pax_extension_eligible(self):
        mail = function_body(self.feeders, "function OpexAI::_tryBuildMailFeeder(")
        append_start = mail.index("this._lines.append({")
        append_end = mail.index("});", append_start)
        line_payload = mail[append_start:append_end]
        self.assertNotIn("kind =", line_payload)
        self.assertIn('purpose = "feeder_mail"', line_payload)

    def test_extension_filter_requires_pax_kind(self):
        candidates = function_body(self.candidates, "function OpexRoadExtensionCandidates(")
        self.assertIn('line.kind != "pax"', candidates)
        self.assertIn('extensionType = isFeeder ? "feeder_extension"', candidates)

if __name__ == "__main__":
    unittest.main()
