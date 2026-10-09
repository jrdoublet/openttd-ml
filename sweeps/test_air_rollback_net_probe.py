"""Contrats statiques R19 : mesurer sans confondre coûts initiaux/différés."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class AirRollbackNetProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.construction = (ROOT / "air_construction.nut").read_text(encoding="utf-8")
        cls.recovery = (ROOT / "air_recovery.nut").read_text(encoding="utf-8")
        cls.task = (ROOT / "task_air.nut").read_text(encoding="utf-8")

    def test_new_logs_are_guarded_by_existing_passive_probe(self):
        self.assertIn("if (PROBE_AIR_FINANCE_MARGIN) {", self.construction)
        self.assertIn('AILog.Info("AIR_RECOVERY_CREATE id=" + traceId', self.construction)
        self.assertIn('AILog.Info("AIR_RECOVERY_COMPLETE id=" + traceId', self.construction)
        self.assertIn("local account = PROBE_AIR_FINANCE_MARGIN ? AIAccounting() : null;", self.recovery)
        self.assertIn('AILog.Info("AIR_RECOVERY_STEP id=" + traceId', self.recovery)
        self.assertIn('if (PROBE_AIR_FINANCE_MARGIN) AILog.Info("AIR_RECOVERY_COMPLETE id="', self.recovery)
        self.assertIn('if (PROBE_AIR_FINANCE_MARGIN) {', self.task)

    def test_deferred_cost_has_its_own_scope_and_remains_signed(self):
        process = self.recovery.split("function OpexAirProcessRollbacks(", 1)[1].split("\nfunction ", 1)[0]
        self.assertEqual(process.count("OpexAirContinueRollback(ticket, lines)"), 1)
        self.assertIn("local delta = account.GetCosts();", process)
        self.assertIn("ticket.v126RecoveryNet += delta;", process)
        self.assertNotIn("if (delta > 0)", process)
        self.assertLess(process.index("local account ="), process.index("OpexAirContinueRollback(ticket, lines)"))
        self.assertIn('" deferred_net=" + ticket.v126RecoveryNet', process)

    def test_only_one_returning_ticket_call_for_each_route_rollback(self):
        route = self.construction.split("function OpexBuildAirRoute(", 1)[1].split("\nfunction ", 1)[0]
        self.assertEqual(route.count("result.recoveryTraceId = OpexAirRollback("), 8)
        self.assertEqual(route.count("OpexAirRollback("), 8)
        self.assertIn("else result.orphanRetained = !reuseA;", route)
        self.assertIn("return traceId;", self.construction)
        self.assertEqual(self.task.count("+ OpexAirV126RecoveryFields(result)"), 2)

    def test_trace_id_and_partial_accounting_survive_save_load(self):
        loader = self.recovery.split("function OpexLoadAirRollbacks(", 1)[1]
        self.assertIn('typeof ticket.v126TraceId == "string"', loader)
        self.assertIn("restored.v126TraceId <- ticket.v126TraceId;", loader)
        self.assertIn('typeof ticket.v126RecoveryNet == "integer"', loader)
        self.assertIn("restored.v126RecoveryNet <- ticket.v126RecoveryNet;", loader)
        self.assertIn("OPEX_AIR_ROLLBACK_TRACE_SEQ <- 0;", self.recovery)


if __name__ == "__main__":
    unittest.main()
