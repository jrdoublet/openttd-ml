"""Régressions de l'extraction des gardes source du selftest C63/C58."""
import unittest

from diag_c63_c58 import discard_append_conditions_from_source


class DiscardGuardTests(unittest.TestCase):
    def test_long_multiline_guard_is_not_truncated(self):
        condition = "C63_INVEST_PROBE || " + " || ".join(f"PROBE_{i}" for i in range(40))
        source = f'if ({condition}) passDiscards.append({{\n rank = i, reason = "build_failed" }});'
        self.assertEqual(discard_append_conditions_from_source(source, "build_failed"), [condition])

    def test_previous_guard_cannot_cover_unguarded_append(self):
        source = ('if (C63_INVEST_PROBE) passDiscards.append({ reason = "other" });\n'
                  'passDiscards.append({ reason = "build_failed" });')
        self.assertEqual(discard_append_conditions_from_source(source, "build_failed"), [""])

    def test_payload_cannot_supply_missing_probe_in_guard(self):
        source = ('if (DECISION_LOG) passDiscards.append({ extra = "C63_INVEST_PROBE", '
                  'reason = "build_failed" });')
        self.assertEqual(discard_append_conditions_from_source(source, "build_failed"), ["DECISION_LOG"])

    def test_every_matching_occurrence_is_checked(self):
        source = ('if (C63_INVEST_PROBE) passDiscards.append({ reason = "build_failed" });\n'
                  'if (DECISION_LOG) passDiscards.append({ reason = "build_failed" });')
        self.assertEqual(discard_append_conditions_from_source(source, "build_failed"),
                         ["C63_INVEST_PROBE", "DECISION_LOG"])
        self.assertEqual(discard_append_conditions_from_source(source, "absent"), [])


if __name__ == "__main__":
    unittest.main()