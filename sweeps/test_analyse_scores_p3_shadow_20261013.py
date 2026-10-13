import tempfile
from pathlib import Path
import unittest
from analyse_scores_p3_shadow_20261013 import analyse


class P3ShadowParser(unittest.TestCase):
    def test_election_and_rank_inversion(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reference_seed42_r0.log"
            p.write_text("\n".join([
                "[I] P3_PORTFOLIO eligible=3 air=2 affected=2 head_flip=1 head_match=1 "
                "base_mode=rail variant_mode=air budget=130000 k_dec=5000 year=1971 month=6 day=1",
                "[I] P3_CANDIDATE mode=air arm=newpair kind=pax src=1 dst=2 tier=0 "
                "finance=130000 cap0=130000 cap1=100000 score0=700 score1=910 "
                "rank0=1 rank1=0 year=1971 month=6 day=1",
            ]), encoding="utf8")
            row = analyse([p])["sources"][p.name]["years"]["1971"]
            self.assertEqual(row["elections"], 1)
            self.assertEqual(row["head_flips"], 1)
            self.assertEqual(row["affected"], 2)
            self.assertEqual(row["air_score_changes"], 1)
            self.assertEqual(row["rank_up"], 1)


if __name__ == "__main__":
    unittest.main()
