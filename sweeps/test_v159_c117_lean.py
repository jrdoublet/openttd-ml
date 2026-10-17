#!/usr/bin/env python3
"""Contrats statiques V159 — echantillonnage C117 lean hors sonde.

Aucun runtime OpenTTD. Verifie le defaut 0, le chemin historique a 0, et
qu'aucun champ lu hors sonde n'est omis a 1.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


def setting_block(info: str, name: str) -> str:
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def guarded_blocks(source: str, predicate: str) -> list[str]:
    """Extract `if (predicate) { ... }` bodies, brace-balanced."""
    blocks = []
    needle = f"if ({predicate})"
    start = 0
    while True:
        i = source.find(needle, start)
        if i < 0:
            return blocks
        after = source[i + len(needle):].lstrip()
        if not after.startswith("{"):
            start = i + len(needle)
            continue
        brace = source.find("{", i + len(needle))
        depth = 0
        for idx in range(brace, len(source)):
            if source[idx] == "{":
                depth += 1
            elif source[idx] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[brace : idx + 1])
                    start = idx + 1
                    break
        else:
            raise AssertionError(f"unterminated {predicate}")


# Champs d'etat lus par OpexC121FirstLiveObserve / Balanced90.
C121_FIRST_LIVE_STATE_FIELDS = (
    "lastLive", "lastDate", "startDate", "trips", "tripsA", "tripsB",
    "profit", "pax", "seatLegs", "waitASum", "waitAN", "waitBSum", "waitBN",
    "lastCap",
)

# Hub delay C121 (decisions economiques), alimente avant le skip de chaine.
C121_HUB_STATE_FIELDS = (
    "hubResidualASum", "hubResidualASq", "hubResidualAN",
    "hubResidualBSum", "hubResidualBSq", "hubResidualBN",
)

# Champs sautes a 1 : uniquement le journal C117 / extras de sonde.
SKIPPED_STATE_FIELDS = (
    "runEst", "mailSeatLegs", "paxA", "seatLegsA", "mailA", "mailSeatLegsA",
    "paxB", "seatLegsB", "mailB", "mailSeatLegsB", "legDays", "legDaysN",
    "legDaysMin", "legDaysMax", "invalidOrderSamples", "unobservedTransitions",
    "engineChanges", "lastEngine", "mixedEngineSamples", "liveSum", "capSum",
    "ratingASum", "ratingAN", "ratingBSum", "ratingBN",
)


class TestV159C117Lean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.probes = read("ai/OpexAI/probes.nut")
        cls.flush = body(cls.probes, "function OpexC117FlushLine(")
        cls.step = body(cls.probes, "function OpexC117AirThroughputStep(")
        cls.observe = body(cls.probes, "function OpexC121FirstLiveObserve(")
        cls.balanced = body(cls.probes, "function OpexC121FirstLiveBalanced90(")
        cls.hub_flush = body(cls.probes, "function OpexC121HubDelayFlushLine(")
        cls.ai_files = {
            path.name: path.read_text(encoding="utf-8")
            for path in AI.glob("*.nut")
        }

    def test_default_one_all_difficulties(self):
        # défaut 1 depuis le 13/10 (porte B 20x10 passée, décision utilisateur) ;
        # le global reste à 0 : seul info.nut porte le défaut
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c117_lean_sampling',))

    def test_settings_guard_unknown_name(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c117_lean_sampling',))

    def test_mode0_historical_observe_order(self):
        """A 0, Observe reste apres les locaux de journal et avant AIAirport."""
        skip_i = self.flush.index("if (skipChain)")
        rest = self.flush[skip_i:]
        rest = rest[rest.index("return;") + len("return;"):]
        cap = rest.index("local profitCapitalPm")
        observe = rest.index("OpexC121FirstLiveObserve(line, state, ageDays);")
        airport = rest.index("AIAirport.IsAirportTile")
        self.assertLess(cap, observe)
        self.assertLess(observe, airport)
        self.assertIn("/* C119 diagnostic passif", rest[observe:airport])

    def test_mode0_does_not_take_lean_skip(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c117_lean_sampling',))

    def test_mode1_skips_probe_only_work(self):
        skip_blocks = guarded_blocks(self.step, "!skipUnused")
        joined = "\n".join(skip_blocks)
        self.assertGreaterEqual(len(skip_blocks), 6)
        self.assertIn("state.runEst +=", joined)
        self.assertIn("GetRunningCost(v)", joined)
        self.assertIn("GetCargoRating", joined)
        self.assertIn("state.mail +=", joined)
        self.assertIn("state.paxA +=", joined)
        self.assertIn("state.invalidOrderSamples++", joined)
        self.assertIn("state.unobservedTransitions++", joined)
        self.assertIn("state.lastEngine = firstEngine", joined)
        self.assertIn("state.liveSum += live", joined)
        self.assertIn("AICargo.IsValidCargo(catalog.mailCargo)", joined)
        self.assertIn("if (skipChain)", self.flush)
        self.assertIn('OpexSpanAgg("loop.c117.flush", flushMark)', self.flush)
        self.assertIn("AIAirport.IsAirportTile", self.flush)
        self.assertLess(
            self.flush.index("if (skipChain)"),
            self.flush.index("AIAirport.IsAirportTile"),
        )

    def test_mode1_keeps_c121_first_live_fields(self):
        skip_blocks = guarded_blocks(self.step, "!skipUnused")
        joined = "\n".join(skip_blocks)
        for field in C121_FIRST_LIVE_STATE_FIELDS:
            self.assertIsNone(
                re.search(r"state\." + re.escape(field) + r"\b", joined),
                f"champ C121 FirstLive {field} saute derriere !skipUnused",
            )
        for field in C121_HUB_STATE_FIELDS:
            self.assertIsNone(
                re.search(r"state\." + re.escape(field) + r"\b", joined),
                f"champ hub delay {field} saute derriere !skipUnused",
            )
        for field in (
            "state.lastLive = live",
            "state.lastCap = totalCap",
            "state.lastDate = now",
            "state.samples++",
            "state.trips++",
            "state.tripsA++",
            "state.tripsB++",
            "state.profit += profitDelta",
            "state.pax +=",
            "state.seatLegs +=",
            "state.waitASum += waitA",
            "state.waitBSum += waitB",
            "state.hubResidualASum += residual",
            "state.hubResidualBSum += residual",
        ):
            self.assertIn(field, self.step)
            self.assertNotIn(field, joined)
        self.assertIn("OpexC121HubDelayFlushLine(line, state)", self.flush)
        self.assertLess(
            self.flush.index("OpexC121HubDelayFlushLine(line, state)"),
            self.flush.index("if (skipChain)"),
        )
        self.assertIn("OpexC121FirstLiveObserve(line, state, ageDaysLean)", self.flush)

    def test_observe_and_balanced90_only_read_kept_state_fields(self):
        state_reads = set(re.findall(r"state\.([A-Za-z0-9_]+)", self.observe))
        allowed = set(C121_FIRST_LIVE_STATE_FIELDS)
        self.assertTrue(state_reads <= allowed, state_reads - allowed)
        self.assertNotIn("state.", self.balanced)
        hub_reads = set(re.findall(r"state\.([A-Za-z0-9_]+)", self.hub_flush))
        self.assertTrue(
            hub_reads <= set(C121_HUB_STATE_FIELDS) | {"startDate", "lastDate", "samples"},
            hub_reads,
        )

    def test_skipped_fields_have_no_non_probe_readers(self):
        """Chaque champ saute n'est lu que dans probes.nut (journal C117)."""
        step_and_flush = self.step + "\n" + self.flush
        for field in SKIPPED_STATE_FIELDS:
            pattern = r"state\." + re.escape(field) + r"\b"
            readers = []
            for name, text in self.ai_files.items():
                if name == "probes.nut":
                    continue
                if re.search(pattern, text):
                    readers.append(name)
            self.assertEqual(readers, [], f"state.{field} lu hors probes.nut: {readers}")
            self.assertIsNotNone(re.search(pattern, step_and_flush), field)

    def test_mode2_dual_path_uses_historical_state(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c117_lean_sampling',))

    def test_span_flush_is_free_outside_probe(self):
        self.assertIn(
            'local flushMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;',
            self.flush,
        )
        self.assertEqual(self.flush.count('OpexSpanAgg("loop.c117.flush", flushMark)'), 2)
        self.assertIn("if (flushMark != null) OpexSpanAgg", self.flush)
        self.assertNotIn("OpexSpanBegin", self.flush)

    def test_mail_invariant_is_outside_vehicle_loop(self):
        """Le test cargo courrier est invariant : une fois par echantillon."""
        loop_i = self.step.index("foreach (v in line.vehicles)")
        before = self.step[:loop_i]
        inside = self.step[loop_i:]
        self.assertIn("AICargo.IsValidCargo(catalog.mailCargo)", before)
        self.assertNotIn("AICargo.IsValidCargo", inside)
        self.assertIn("if (mailActive)", inside)
        self.assertIn("AIVehicle.GetCapacity(v, mailCargoId)", inside)


if __name__ == "__main__":
    unittest.main()
