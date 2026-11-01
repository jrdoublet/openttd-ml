"""Targeted contract and logic tests for ROAD100-24 freight refleet target guards."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def simulate_refleet_target(
    *,
    has_freight_berths: bool,
    kind: str,
    have: int,
    physical_cap: int,
    waiting_a: int,
    capacity: int,
    money: int,
    unit_price: int,
    last_profit: int,
    is_any_waiting: bool,
    available_slots: int,
) -> int:
    """Exact reproduction of task_road.nut refleet logic for a line."""
    # Historical base target (nominal fleet)
    target = 2

    # Historical extraNeeded logic
    extra_needed = 0
    total_waiting = waiting_a  # for freight line, destination waiting is 0
    if total_waiting >= capacity and not is_any_waiting:
        extra_needed = total_waiting // capacity
        if extra_needed > 3:
            extra_needed = 3
    elif last_profit > 1000 and have < physical_cap and money > 60000 and not is_any_waiting:
        extra_needed = 1

    if have + extra_needed > physical_cap:
        extra_needed = physical_cap - have
    if extra_needed < 0:
        extra_needed = 0

    if have + extra_needed > target:
        target = have + extra_needed
    if target > physical_cap:
        target = physical_cap

    # ROAD100-24 final target guard on freight lines with double berths
    if has_freight_berths and kind == "freight":
        if target > have:
            if target > have + 2:
                target = have + 2
            if last_profit < 3000 or is_any_waiting or capacity <= 0:
                target = have
            else:
                demand_wanted = waiting_a // capacity - have
                if demand_wanted <= 0:
                    target = have
                else:
                    if target > have + demand_wanted:
                        target = have + demand_wanted
                    freight_price = unit_price
                    freight_cash = money
                    if freight_price <= 0 or freight_cash < 50000:
                        target = have
                    else:
                        can_pay = (freight_cash - 50000) // freight_price
                        if target - have > can_pay:
                            target = have + can_pay
                        missing = target - have
                        if missing > 0 and available_slots < missing:
                            if missing > 1 and available_slots >= 1:
                                target = have + 1
                            else:
                                target = have

    return target


class Road100FreightRefleetTargetTests(unittest.TestCase):
    def setUp(self):
        self.task_road = (ROOT / "ai" / "OpexAI" / "task_road.nut").read_text(encoding="utf-8")

    def test_task_road_contains_freight_berths_final_target_guards(self):
        """task_road.nut must guard the final target passed to OpexRoadRefleet."""
        self.assertIn('("road100FreightBerths" in line) && line.road100FreightBerths != null', self.task_road)
        self.assertIn('("kind" in line) && line.kind == "freight"', self.task_road)
        self.assertIn('if (target > have + 2) target = have + 2;', self.task_road)
        self.assertIn('line.lastProfit < 3000', self.task_road)
        self.assertIn('freightCash - 50000', self.task_road)
        self.assertIn('target - have > canPay', self.task_road)
        self.assertIn('OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, missing)', self.task_road)
        self.assertIn('OpexRoadRefleet(this._catalog, line, have, target)', self.task_road)

        # The guard must appear before the call to OpexRoadRefleet
        guard_idx = self.task_road.find('/* ROAD100-24 : la cible finale transmise à refleet')
        self.assertGreater(guard_idx, 0)
        refleet_idx = self.task_road.find('local refill = OpexRoadRefleet(this._catalog, line, have, target);', guard_idx)
        self.assertGreater(refleet_idx, guard_idx)

    def test_review_scenario_cash_55k_preserves_reserve(self):
        """Scenario from review: have=2, physicalCap=4, cash=55k, unitPrice=10k, profit=5000.
        Legacy would request 3 extra (capped at 2 by physicalCap), dropping cash to 35k.
        Guard must produce target=2 (0 reinforcements, preserving 50k reserve)."""
        target = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,  # 4 * capacity
            capacity=25,
            money=55000,
            unit_price=10000,
            last_profit=5000,
            is_any_waiting=False,
            available_slots=10,
        )
        self.assertEqual(target, 2, "Cash of 55k with unitPrice 10k can only afford (55k-50k)/10k = 0 extra above reserve")

    def test_cash_75k_allows_two_reinforcements(self):
        """Cash 75k affords (75k-50k)/10k = 2 vehicles, within cap of 2."""
        target = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,  # 4 * capacity
            capacity=25,
            money=75000,
            unit_price=10000,
            last_profit=5000,
            is_any_waiting=False,
            available_slots=10,
        )
        self.assertEqual(target, 4)

    def test_cap_of_two_enforced_even_with_excess_cash_and_demand(self):
        """Even with 200k cash and demand for 4 extra, freight berth policy caps at +2."""
        target = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=6,
            waiting_a=200,
            capacity=25,
            money=200000,
            unit_price=10000,
            last_profit=8000,
            is_any_waiting=False,
            available_slots=10,
        )
        self.assertEqual(target, 4, "Cap of 2 reinforcements must bound target to have + 2 = 4")

    def test_insufficient_profit_blocks_reinforcement(self):
        """Profit < 3000 £ must block reinforcement despite cash and stock."""
        target = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,
            capacity=25,
            money=100000,
            unit_price=10000,
            last_profit=2500,  # < 3000
            is_any_waiting=False,
            available_slots=10,
        )
        self.assertEqual(target, 2)

    def test_waiting_vehicles_block_reinforcement(self):
        """Any vehicle jammed at stop (is_any_waiting) must block reinforcement."""
        target = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,
            capacity=25,
            money=100000,
            unit_price=10000,
            last_profit=5000,
            is_any_waiting=True,
            available_slots=10,
        )
        self.assertEqual(target, 2)

    def test_slots_availability_constrains_reinforcement(self):
        """Available road slots must constrain the added target."""
        # Only 1 slot available
        target1 = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,
            capacity=25,
            money=100000,
            unit_price=10000,
            last_profit=5000,
            is_any_waiting=False,
            available_slots=1,
        )
        self.assertEqual(target1, 3, "Only 1 slot available: target reduced from 4 to 3")

        # 0 slots available
        target0 = simulate_refleet_target(
            has_freight_berths=True,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,
            capacity=25,
            money=100000,
            unit_price=10000,
            last_profit=5000,
            is_any_waiting=False,
            available_slots=0,
        )
        self.assertEqual(target0, 2, "0 slots available: target stays at have = 2")

    def test_default_line_without_freight_berths_unchanged(self):
        """A normal line without road100FreightBerths must follow historical logic."""
        target = simulate_refleet_target(
            has_freight_berths=False,
            kind="freight",
            have=2,
            physical_cap=4,
            waiting_a=100,
            capacity=25,
            money=55000,
            unit_price=10000,
            last_profit=1500,
            is_any_waiting=False,
            available_slots=10,
        )
        # Historical logic: extra_needed = min(100 // 25, 3) = 3, target = 2 + 3 = 5 -> capped at physical_cap = 4
        self.assertEqual(target, 4, "Without freight berths marker, historical behavior remains untouched")


if __name__ == "__main__":
    unittest.main()
