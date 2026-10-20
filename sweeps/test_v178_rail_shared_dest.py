#!/usr/bin/env python3
"""V178 : partage de gare de destination acceptante pour les candidats fret rail (fige actif par V263b)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class TestV178RailSharedDest(unittest.TestCase):
    def test_setting(self):
        self.assertNotIn("v178_rail_shared_dest", parse_ai_setting_specs(AI / "info.nut"))

    def test_loaded_once(self):
        self.assertNotIn("V178_RAIL_SHARED_DEST", _read("globals_pre.nut"))
        self.assertNotIn('GetSetting("v178_rail_shared_dest")', _read("settings.nut"))

    def test_method_declared_in_main(self):
        main = _read("main.nut")
        self.assertIn("function _tryAttachSharedDest(candidate);", main)

    def test_try_attach_shared_dest_implementation(self):
        lines = _read("lines.nut")
        self.assertIn("function OpexAI::_tryAttachSharedDest(candidate)", lines)
        body = lines[lines.index("function OpexAI::_tryAttachSharedDest(candidate)"):]
        # Preconditions
        self.assertNotIn("V178_RAIL_SHARED_DEST", body)
        self.assertIn('candidate.kind != "freight"', body)
        # Source must remain fresh
        self.assertIn("ORIGIN_SEPARATION", body)
        self.assertIn("MIN_SEPARATION", body)
        # Destination must be within MIN_SEPARATION of station that accepts cargo
        self.assertIn("AICargoList_StationAccepting(stationId)", body)
        # Proper attachment for joinEnd = B
        self.assertIn('candidate.joinEnd <- "B"', body)
        self.assertIn("candidate.joinPlatform <-", body)
        self.assertIn("candidate.joinStationId <-", body)
        self.assertIn("candidate.joinLineId <-", body)
        self.assertIn("candidate.shared_dest <- 1", body)

    def test_too_close_ignores_shared_dest_endpoint_b(self):
        lines = _read("lines.nut")
        tc = lines[lines.index("function OpexAI::_tooClose(candidate)"):lines.index("function OpexAI::_tryAttachSharedDest(candidate)")]
        self.assertNotIn("V178_RAIL_SHARED_DEST", tc)
        self.assertIn('("shared_dest" in candidate)', tc)
        self.assertIn('if (isSharedDest && entry[0] == "B") continue;', tc)

    def test_task_rail_precheck_invokes_attachment(self):
        task_rail = _read("task_rail.nut")
        self.assertIn("if (!v233Graft && !(\"joinPlatform\" in candidate))", task_rail)
        attach_idx = task_rail.index("this._tryAttachSharedDest(candidate);")
        too_close_idx = task_rail.index("local close = this._tooClose(candidate);", attach_idx)
        self.assertLess(attach_idx, too_close_idx)

    def test_builder_strict_fallback(self):
        builder = _read("builder_rail.nut")
        self.assertNotIn("V178_RAIL_SHARED_DEST", builder)
        self.assertIn('("shared_dest" in candidate)', builder)
        self.assertIn("strictOriginReuseJoin", builder)

    def test_decision_log_shared_dest_field(self):
        task_rail = _read("task_rail.nut")
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', task_rail)
        self.assertIn('shared_dest=" + ((("shared_dest" in candidate) && candidate.shared_dest) ? 1 : 0)', task_rail)
        build_idx = task_rail.index('OpexDecide("RAIL_BUILD"')
        self.assertIn('shared_dest=" + ((("shared_dest" in candidate) && candidate.shared_dest) ? 1 : 0)', task_rail[build_idx:])


if __name__ == "__main__":
    unittest.main()
