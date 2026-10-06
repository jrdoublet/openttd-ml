"""R22 source contracts only; depot order semantics need an OpenTTD smoke."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestRetirementRetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "ai/OpexAI/task_report.nut").read_text(encoding="utf-8")
        cls.retire = source.split("function OpexAI::_scrapRetiredVehicles(", 1)[1].split("\nfunction ", 1)[0]
        cls.retry = cls.retire.split('local lastSend = ("lastSendDate" in ticket)', 1)[1].split("foreach (vehicle in removeTickets)", 1)[0]

    def test_actual_current_order_is_queried_not_list_position(self):
        self.assertIn("AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)", self.retry)
        self.assertIn("AIOrder.GetOrderFlags(vehicle, AIOrder.ORDER_CURRENT)", self.retry)
        self.assertNotIn("ResolveOrderPosition", self.retry)
        self.assertLess(self.retry.index("AIOrder.IsGotoDepotOrder"), self.retry.index("AIOrder.GetOrderFlags"))

    def test_halt_and_unknown_flags_skip_but_service_can_be_converted(self):
        self.assertIn("if (flags == AIOrder.OF_INVALID || (flags & AIOrder.OF_STOP_IN_DEPOT) != 0) continue;", self.retry)
        self.assertNotIn("OF_SERVICE_IF_NEEDED", self.retry)
        self.assertNotIn("SetOrderFlags", self.retry)
        self.assertLess(self.retry.index("continue;"), self.retry.index("AIVehicle.SendVehicleToDepot(vehicle)"))

    def test_retry_interval_and_success_only_ticket_updates(self):
        self.assertIn("if (lastSend < 0 || now - lastSend >= 90)", self.retry)
        self.assertRegex(
            self.retry,
            r'if \(AIVehicle.SendVehicleToDepot\(vehicle\)\)\s*\{\s*'
            r'ticket.rawset\("lastSendDate", now\);\s*'
            r'ticket.rawset\("attempts", \("attempts" in ticket\) \? ticket.attempts \+ 1 : 1\);',
        )
        self.assertEqual(self.retry.count('ticket.rawset("lastSendDate"'), 1)
        self.assertEqual(self.retry.count('ticket.rawset("attempts"'), 1)

    def test_sale_and_timeout_are_processed_before_waiting_for_depot(self):
        guard = self.retire.index("AIOrder.IsGotoDepotOrder")
        self.assertLess(self.retire.index("AIVehicle.SellVehicle(vehicle)"), guard)
        self.assertLess(self.retire.index("if (now - started >= SCRAP_TIMEOUT_YEARS * 365)"), guard)
        self.assertIn("if (!known) line.vehicles.append(vehicle);", self.retire)
        self.assertIn("if (AIVehicle.IsStoppedInDepot(vehicle)) AIVehicle.StartStopVehicle(vehicle);", self.retire)
        self.assertIn('"action=cancel_timeout vehicle="', self.retire)

    def test_invalid_vehicles_and_reequipment_remain_guarded(self):
        guard = self.retire.index("AIOrder.IsGotoDepotOrder")
        self.assertLess(self.retire.index("if (!AIVehicle.IsValidVehicle(vehicle))"), guard)
        self.assertLess(self.retire.index("if (OpexAirLineReequipPending(ownerLine)) continue;"), guard)
        self.assertIn("delete this._vehiclesToRetire[vehicle];", self.retire)
        self.assertIn("delete this._unprofitableStreaks[vehicle];", self.retire)

    def test_legacy_upgrade_and_ticket_persistence_remain(self):
        self.assertIn("ticket = { lineId = savedTicket, startedDate = now, lastSendDate = now, attempts = 0 };", self.retire)
        self.assertIn("this._vehiclesToRetire.rawset(upgrade.vehicle, upgrade.ticket);", self.retire)
        persist = (ROOT / "ai/OpexAI/persist.nut").read_text(encoding="utf-8")
        self.assertIn("vehiclesToRetire = this._vehiclesToRetire,", persist)
        self.assertIn("this._vehiclesToRetire = data.vehiclesToRetire;", persist)
        # No persisted "already sent" bit: each due retry observes engine state.
        self.assertNotIn("ticket.sentToDepot", self.retire)


if __name__ == "__main__":
    unittest.main()