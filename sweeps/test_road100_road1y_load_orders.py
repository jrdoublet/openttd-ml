"""ROAD1Y: tests cibles des ordres de chargement route alignes sur AAAHogEx."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename: str) -> str:
    return (AI / filename).read_text(encoding="utf-8")


class Road1yLoadOrdersContracts(unittest.TestCase):
    def setUp(self):
        self.globals = src("globals_pre.nut")
        self.info = src("info.nut")
        self.settings = src("settings.nut")
        self.builder_road = src("builder_road.nut")

    def test_global_and_setting_declaration(self):
        # Globale a defaut false
        self.assertIn("ROAD1Y_LOAD_ORDERS <- false;", self.globals)

        # Reglage declare dans info.nut avec defaut 0
        block = re.search(r'name = "road1y_load_orders"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(block, "road1y_load_orders setting must be declared in info.nut")
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("flags = AICONFIG_BOOLEAN", block.group(1))

        # Lecture dans settings.nut
        self.assertIn('ROAD1Y_LOAD_ORDERS = AIController.GetSetting("road1y_load_orders") == 1;', self.settings)

    def test_builder_road_orders_logic(self):
        # Verification de la logique dans OpexBuildRoadRoute
        self.assertIn('local isFreight = (candidate.kind == "freight");', self.builder_road)
        self.assertIn("local sourceFullLoad = isFreight || ROAD1Y_LOAD_ORDERS;", self.builder_road)
        self.assertIn("local sourceFlags = (sourceFullLoad ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE) | nonstopFlag;", self.builder_road)
        self.assertIn("local destFlags = (ROAD1Y_LOAD_ORDERS && isFreight) ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD) : AIOrder.OF_NONE;", self.builder_road)

    def test_simulated_orders_flags(self):
        """Simulation des drapeaux d'ordres pour chaque mode et configuration."""
        OF_NONE = 0
        OF_NON_STOP_INTERMEDIATE = 1
        OF_FULL_LOAD_ANY = 2
        OF_UNLOAD = 4
        OF_NO_LOAD = 8

        def get_flags(is_freight: bool, road1y_load_orders: bool):
            nonstop = OF_NON_STOP_INTERMEDIATE
            source_full = is_freight or road1y_load_orders
            src_flags = (OF_FULL_LOAD_ANY if source_full else OF_NONE) | nonstop
            dest_flags = (OF_UNLOAD | OF_NO_LOAD if (road1y_load_orders and is_freight) else OF_NONE) | nonstop
            return src_flags, dest_flags

        # 1. Defaut fret (road1y_load_orders=0) : source pleine, dest OF_NONE
        src, dest = get_flags(is_freight=True, road1y_load_orders=False)
        self.assertEqual(src, OF_FULL_LOAD_ANY | OF_NON_STOP_INTERMEDIATE)
        self.assertEqual(dest, OF_NONE | OF_NON_STOP_INTERMEDIATE)

        # 2. Fret avec road1y_load_orders=1 : source pleine, dest UNLOAD | NO_LOAD
        src, dest = get_flags(is_freight=True, road1y_load_orders=True)
        self.assertEqual(src, OF_FULL_LOAD_ANY | OF_NON_STOP_INTERMEDIATE)
        self.assertEqual(dest, (OF_UNLOAD | OF_NO_LOAD) | OF_NON_STOP_INTERMEDIATE)

        # 3. Defaut pax (road1y_load_orders=0) : source OF_NONE, dest OF_NONE
        src, dest = get_flags(is_freight=False, road1y_load_orders=False)
        self.assertEqual(src, OF_NONE | OF_NON_STOP_INTERMEDIATE)
        self.assertEqual(dest, OF_NONE | OF_NON_STOP_INTERMEDIATE)

        # 4. Pax avec road1y_load_orders=1 : source pleine (alignee AAAHogEx), dest OF_NONE
        src, dest = get_flags(is_freight=False, road1y_load_orders=True)
        self.assertEqual(src, OF_FULL_LOAD_ANY | OF_NON_STOP_INTERMEDIATE)
        self.assertEqual(dest, OF_NONE | OF_NON_STOP_INTERMEDIATE)


if __name__ == "__main__":
    unittest.main()
