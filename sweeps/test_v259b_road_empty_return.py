"""V259b : chaque retour d'OpexBuildRoadCandidates porte la clé candidates (départ 1925 sans véhicule routier)."""
from pathlib import Path
import re
import unittest

SRC = (Path(__file__).resolve().parents[1] / "ai/OpexAI/candidates.nut").read_text(encoding="utf-8")


class RoadEmptyReturn(unittest.TestCase):
    def test_every_literal_return_has_candidates(self):
        start = SRC.index("function OpexBuildRoadCandidates(")
        body = SRC[start:SRC.index("\n}\n", start)]
        literals = re.findall(r"return \{[^}]*\}", body)
        self.assertGreaterEqual(len(literals), 2)
        for literal in literals:
            self.assertIn("candidates =", literal)


if __name__ == "__main__":
    unittest.main()
