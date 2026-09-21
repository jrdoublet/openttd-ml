"""Les sondes du vivier ne doivent pas lire des compteurs retirés par nettoyage."""
from pathlib import Path
import re
import unittest


class TestC73StatsContract(unittest.TestCase):
    def test_candidate_stats_reads_have_a_declared_counter(self):
        source = (Path(__file__).resolve().parents[1] / "ai/OpexAI/candidates.nut").read_text(encoding="utf-8")
        reads = set(re.findall(r"\bstats\.(\w+)", source))
        missing = [name for name in reads if not re.search(r"\b" + name + r"\s*(?:=|<-)", source)]
        self.assertEqual(sorted(missing), [])
