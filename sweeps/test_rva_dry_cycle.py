"""RVA-06/07 : unités, incertitude et calcul de composition hors moteur."""
from pathlib import Path
import unittest

from rva_dry_cycle import dry_cycle, from_snapshot


class DryCycle(unittest.TestCase):
    def compute(self, cargos, **kw):
        options = dict(waiting_a_days=0, waiting_b_days=0,
                       rating_anchor_pct=50, parallel_loading=True)
        options.update(kw)
        return dry_cycle(10, 2, cargos, **options)

    def cargo(self, identity=0, capacity=40, dwell=2, monthly=100):
        return dict(cargo=identity, capacity=capacity, dwell_a_days=dwell,
                    dwell_b_days=dwell, monthly=monthly)

    def test_complete_cycle_and_offer_have_same_clock(self):
        row = self.compute([self.cargo()])
        self.assertEqual(row["cycle_days"], 24)
        self.assertEqual(row["headway_days"], 12)
        self.assertEqual(row["rating_pct"], 50)
        cargo, = row["cargos"]
        self.assertEqual(cargo["capacity_month"], 200)
        self.assertEqual(cargo["offered_month"], 50)
        self.assertEqual(cargo["carried_month"], 50)
        self.assertIsNone(row["delivered_rate"])

    def test_mail_parallel_bottleneck_changes_entire_cycle(self):
        # Mail takes longer; it slows passengers as well, without adding units.
        row = self.compute([self.cargo(), self.cargo(2, 20, 6, 10000)])
        self.assertEqual(row["cycle_days"], 32)
        self.assertEqual(row["headway_days"], 16)
        pax, mail = row["cargos"]
        self.assertEqual(pax["capacity_month"], 150)
        self.assertEqual(mail["capacity_month"], 75)
        self.assertEqual(mail["carried_month"], 75)
        self.assertLess(pax["offered_month"], 50)

    def test_unknown_is_not_zero_and_waiting_is_not_double_counted(self):
        row = self.compute([self.cargo(monthly=None)], waiting_a_days=3)
        self.assertEqual(row["cycle_days"], 27)
        self.assertIsNone(row["cargos"][0]["carried_month"])
        self.assertEqual(self.compute([self.cargo(capacity=None)])["coverage"], "not_covered")
        self.assertEqual(self.compute([self.cargo()], parallel_loading=None)["coverage"], "not_covered")
        self.assertEqual(self.compute([self.cargo()], waiting_a_days=float("nan"))["coverage"], "not_covered")
        with self.assertRaises(ValueError):
            self.compute([self.cargo(), self.cargo()])

    def test_legacy_snapshot_does_not_invent_demand_or_mail_physics(self):
        row = from_snapshot(dict(trips_month=2.5, one_way_days=10, trains=2,
                                cargo=0, per_train=40, cargo2=2, per_train2=20))
        self.assertEqual(row["cycle_days"], 24)
        self.assertEqual(row["mixed_loading_coverage"], "not_covered")
        self.assertTrue(all(c["offered_month"] is None for c in row["cargos"]))


class EquipmentContract(unittest.TestCase):
    def test_descriptor_is_guarded_readonly_and_preserves_uncertainty(self):
        root = Path(__file__).resolve().parents[1] / "ai/OpexAI"
        source = (root / "rva_equipment.nut").read_text()
        self.assertIn("if (!RVA_CYCLE_PROBE) return null;", source)
        for token in ("AIEngine.CanRefitCargo", "AIEngine.IsArticulated", "AIEngine.CanRunOnRail",
                      "AIEngine.HasPowerOnRail", "AIEngine.CanPullCargo", "capacity = null",
                      "length16 = null", "requires_builder_callbacks_and_length_check"):
            self.assertIn(token, source)
        self.assertNotRegex(source, r"\b(?:BuildVehicle|RefitVehicle|SetCurrentRailType)\b")
        for name in ("rva_equipment.nut", "probe_rva_cycle.nut"):
            text = (root / name).read_text()
            self.assertNotRegex(text, r"\blocal\s+(clone|base|parent)\b")
            self.assertNotIn("function(", text)
        consumers = [p.name for p in root.glob("*.nut")
                     if "OpexRvaEquipment(" in p.read_text()]
        self.assertEqual(sorted(consumers), ["probe_rva_cycle.nut", "rva_equipment.nut"])
