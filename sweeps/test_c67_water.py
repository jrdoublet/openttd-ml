"""Host tests for the C67.5 water diagnostic collection, not a Squirrel VM."""
from pathlib import Path
import hashlib
import tempfile
import unittest

from diag_c67_water import NAME, ROOT, keep, parse_lines, stage_fixture, summarise_pairs


class WaterHarnessTests(unittest.TestCase):
    def test_staged_sources_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = stage_fixture(Path(tmp) / "fixture")
            source = (ROOT / "ai/OpexAI/water_graph.nut").read_bytes()
            self.assertEqual(manifest["water_graph.nut"], hashlib.sha256(source).hexdigest())
            self.assertIn("builder_water.nut", manifest)
            with self.assertRaises(FileExistsError):
                stage_fixture(Path(tmp) / "fixture")

    def test_processor_tuple_and_exact_marker(self):
        row = {"experiment": {"bench_run": [NAME, 42, 8]}, "date": "1972-12-01",
               "chunks": {"SIGN": {1: {"name": "C675|PASS"}}}}
        self.assertIsInstance(keep(row), tuple)
        self.assertTrue(keep(row)[0]["passed"])
        row["chunks"]["SIGN"][1]["name"] = "C675|PASSX"
        self.assertFalse(keep(row)[0]["passed"])

    def test_parse_and_summary(self):
        out = ("[I] C675_PAIR i=0 manh=5 exact=1 oracle=connected reason=- wrong=0 blocks=3 "
               "nodes=4 ops=900 builder=7 builder_ops=500 corridor=found cdist=7 cops=300\n"
               "[I] C675_PAIR i=1 manh=90 exact=1 oracle=unknown reason=block_budget wrong=0 "
               "blocks=1024 nodes=900 ops=9000 builder=-1 builder_ops=800 corridor=- cdist=-1 cops=0\n"
               "[I] C675_ALL_PASS\n")
        lines = parse_lines(out)
        self.assertEqual(len(lines["C675_PAIR"]), 2)
        self.assertIn("C675_ALL_PASS", lines)
        s = summarise_pairs(lines["C675_PAIR"])
        self.assertEqual(s["builder_false_reject"], 1)
        self.assertEqual(s["unknown_reasons"], {"block_budget": 1})
        self.assertEqual(s["corridor_vs_builder"]["equal"], 1)
        self.assertEqual(s["wrong"], 0)


if __name__ == "__main__":
    unittest.main()
