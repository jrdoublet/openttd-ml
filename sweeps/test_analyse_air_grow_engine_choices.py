"""Host-only contracts for counting engine-choice exposure in AIR-GROW logs."""

import unittest

from analyse_air_grow_engine_choices import parse_record, summarize


def event(phase, old, buy, *, decision="accept", fallback="none",
          rot_old="c117", rot_buy="c121"):
    return parse_record(
        f"2026-10-25 [AI] OPEX 1972-2-4 AIR_GROW_MARGINAL "
        f"line=12 n=2 decision={decision} fallback={fallback} phase={phase} "
        f"old_engine={old} buy_engine={buy} rot_old={rot_old} rot_buy={rot_buy}"
    )


class EngineChoiceReader(unittest.TestCase):
    def test_ignores_irrelevant_and_old_undocumented_logs(self):
        self.assertIsNone(parse_record("OPEX 1972-2-4 OTHER_EVENT phase=rank"))
        self.assertIsNone(parse_record("AIR_GROW_MARGINAL other_field=x"))
        old = parse_record("OPEX 1972-2-4 AIR_GROW_MARGINAL fallback=none phase=rank decision=accept")
        result = summarize([old])["rank"]
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["known_engines"], 0)

    def test_counts_exposure_by_phase_not_as_independent_purchases(self):
        summaries = summarize([
            event("rank", 217, 223), event("rank", 217, 223),
            event("purchase", 217, 223), event("purchase", 217, 217, rot_buy="c117"),
            event("purchase", 217, 223, decision="reject"),
        ])
        self.assertEqual(summaries["rank"]["rows"], 2)
        self.assertEqual(summaries["rank"]["different_engines"], 2)
        self.assertEqual(summaries["purchase"]["different_engines"], 2)
        self.assertEqual(summaries["purchase"]["different_accepted"], 1)
        self.assertEqual(summaries["purchase"]["rotation_sources_different_engine"][("c117", "c121")], 2)

    def test_unknown_and_fallback_are_not_verified_engine_exposure(self):
        summaries = summarize([
            event("purchase", -1, -1, fallback="obs_days", rot_old="unknown", rot_buy="unknown"),
            event("purchase", 217, 223, fallback="rotation", rot_old="unknown", rot_buy="unknown"),
            event("purchase", 217, 217, rot_buy="c117"),
        ])["purchase"]
        self.assertEqual(summaries["rows"], 3)
        self.assertEqual(summaries["known_engines"], 1)
        self.assertEqual(summaries["different_engines"], 0)


if __name__ == "__main__":
    unittest.main()
