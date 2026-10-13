"""Guard bounded sample and exact fields in AIR veto logs."""
import unittest

from analyse_p0_air_veto_shadow_20261012 import parse, summarize


def line(day, *, first="servedA", reasons="servedA", src=1, stage="projects"):
    return (f"dbg: [script:4] [0] [I] OPEX 1973-6-{day} P0_AIR_VETO "
            f"mode=air stage={stage} tick=100 rank=2 built_before=1 best=64 "
            f"arm=hubsite src={src} dst=2 anchorA=3 anchorB=4 reuseA=1 "
            f"reuseB=0 first={first} reasons={reasons}")


class AIRVetoParserTests(unittest.TestCase):
    def test_multiple_reason_fields_counted_and_od_dedup(self):
        parsed = parse([line(7, first="servedA", reasons="servedA,capA"),
                        line(7, first="servedA", reasons="servedA,capA"),
                        line(8, first="recovery", reasons="recovery", stage="builder")])
        out = summarize(parsed)["1973"]
        self.assertEqual(3, out["logged_veto_replays"])
        self.assertEqual(1, out["unique_od_arm_in_sample"])
        self.assertEqual(2, out["unique_od_arm_day_in_sample"])
        self.assertEqual(2, out["first_reason"]["servedA"])
        self.assertEqual(2, out["all_reason_occurrences"]["capA"])
        self.assertEqual(1, out["stage"]["builder"])

    def test_no_log_does_not_mean_zero_veto(self):
        self.assertEqual({}, summarize(parse(["unrelated NOAI line"])) )

    def test_missing_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing AIR veto"):
            parse([line(8).replace(" best=64", "")])

    def test_duplicate_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate AIR veto"):
            parse([line(8) + " rank=3"])


if __name__ == "__main__":
    unittest.main()
