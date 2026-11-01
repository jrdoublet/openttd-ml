"""ROAD1Y: garde route seule (master multimodal inchange) et defauts mail/long_v3.

Chaque ROAD1Y_* lu dans settings.nut ne s'active que si mode_road est actif
et mode_air / mode_rail / mode_water inactifs, comme ROAD100_SOLO_PAX.
Hors route seule, les variables reprennent les valeurs de origin/master.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"


# Valeur hors route seule = origin/master (le levier n'existe pas ou est inerte).
ROAD1Y_OFF = {
    "ROAD1Y_LOAD_ORDERS": "false",
    "ROAD1Y_DIST_BANDS": "false",
    "ROAD1Y_FLEET": "0",
    "ROAD1Y_PAX_ECONOMY": "false",
    "ROAD1Y_PAX_REFLEET": "false",
    "ROAD1Y_MAIL_ON_PAX": "false",
    "ROAD1Y_FLEET_UNLOCK": "0",
    "ROAD1Y_LONG_BAND": "0",
    "ROAD1Y_LONG_V3": "0",
    "ROAD1Y_BUS_FIXES": "0",
    "ROAD1Y_EXTRA_STOPS": "0",
    "ROAD1Y_PAX_SITES": "false",
}

SETTING_TO_GLOBAL = {
    "road1y_load_orders": "ROAD1Y_LOAD_ORDERS",
    "road1y_dist_bands": "ROAD1Y_DIST_BANDS",
    "road1y_fleet": "ROAD1Y_FLEET",
    "road1y_pax_economy": "ROAD1Y_PAX_ECONOMY",
    "road1y_pax_refleet": "ROAD1Y_PAX_REFLEET",
    "road1y_mail_on_pax": "ROAD1Y_MAIL_ON_PAX",
    "road1y_fleet_unlock": "ROAD1Y_FLEET_UNLOCK",
    "road1y_long_band": "ROAD1Y_LONG_BAND",
    "road1y_long_v3": "ROAD1Y_LONG_V3",
    "road1y_bus_fixes": "ROAD1Y_BUS_FIXES",
    "road1y_extra_stops": "ROAD1Y_EXTRA_STOPS",
    "road1y_pax_sites": "ROAD1Y_PAX_SITES",
}

LOAD_SETTINGS_KEYS = (
    "road1y_load_orders",
    "road1y_dist_bands",
    "road1y_fleet",
    "road1y_pax_economy",
    "road1y_pax_refleet",
    "road1y_mail_on_pax",
    "road1y_fleet_unlock",
    "road1y_long_band",
    "road1y_long_v3",
)
BUS_DISTRICT_KEYS = (
    "road1y_bus_fixes",
    "road1y_extra_stops",
    "road1y_pax_sites",
    "road1y_mail_on_pax",
)

ROAD100_SOLO_MODES = "MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER"
BUS_DISTRICT_MODES = (
    'AIController.GetSetting("mode_road") != 0',
    'AIController.GetSetting("mode_air") == 0',
    'AIController.GetSetting("mode_rail") == 0',
    'AIController.GetSetting("mode_water") == 0',
)


def _info_road1y_names():
    return re.findall(r'name = "(road1y_[^"]+)"', source("info.nut"))


def _getsetting_road1y(text):
    return re.findall(r'GetSetting\("(road1y_[^"]+)"\)', text)


def _gate_line(global_name):
    return f"if (!road1yRoadOnly) {global_name} = {ROAD1Y_OFF[global_name]};"


class TestRoad1yMultimodalGate(unittest.TestCase):
    def test_info_declares_every_loaded_road1y_setting(self):
        declared = _info_road1y_names()
        self.assertEqual(sorted(declared), sorted(SETTING_TO_GLOBAL))
        self.assertEqual(len(declared), len(set(declared)))

    def test_getsetting_sites_are_only_the_two_loaders(self):
        settings = source("settings.nut")
        found = _getsetting_road1y(settings)
        self.assertEqual(sorted(set(found)), sorted(SETTING_TO_GLOBAL))
        load = body("settings.nut", "OpexLoadSettings")
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertEqual(sorted(_getsetting_road1y(load)), sorted(LOAD_SETTINGS_KEYS))
        self.assertEqual(sorted(_getsetting_road1y(bus)), sorted(BUS_DISTRICT_KEYS))
        self.assertEqual(settings.count('GetSetting("road1y_mail_on_pax")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_',
                path.read_text(encoding="utf-8"),
                path.name,
            )

    def test_opex_load_settings_uses_road100_solo_mode_condition(self):
        load = body("settings.nut", "OpexLoadSettings")
        self.assertIn(
            "ROAD100_SOLO_PAX = AIController.GetSetting(\"road100_solo_pax\") == 1\n"
            f"      && {ROAD100_SOLO_MODES};",
            load,
        )
        self.assertIn(f"local road1yRoadOnly = {ROAD100_SOLO_MODES};", load)
        self.assertLess(
            load.index("if (MODE_WATER && !OpexModeAllowedByGame(\"water\")) MODE_WATER = false;"),
            load.index(f"local road1yRoadOnly = {ROAD100_SOLO_MODES};"),
        )
        defined = load.index(f"local road1yRoadOnly = {ROAD100_SOLO_MODES};")
        for key in LOAD_SETTINGS_KEYS:
            global_name = SETTING_TO_GLOBAL[key]
            gate = _gate_line(global_name)
            self.assertIn(gate, load, gate)
            self.assertLess(defined, load.index(gate), global_name)
            if key == "road1y_load_orders":
                self.assertLess(load.index('GetSetting("road1y_load_orders")'), defined)
            else:
                self.assertLess(defined, load.index(f'GetSetting("{key}")'), key)
                self.assertLess(load.index(f'GetSetting("{key}")'), load.index(gate), key)

    def test_bus_district_loader_reads_mode_settings_directly(self):
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn("local road1yRoadOnly = AIController.GetSetting(\"mode_road\") != 0", bus)
        for fragment in BUS_DISTRICT_MODES:
            self.assertIn(fragment, bus.split("GetSetting(\"road1y_")[0], fragment)
        defined = bus.index("local road1yRoadOnly =")
        require_at = bus.index('require("bus_districts_overrides.nut")')
        for key in BUS_DISTRICT_KEYS:
            global_name = SETTING_TO_GLOBAL[key]
            gate = _gate_line(global_name)
            self.assertIn(gate, bus, gate)
            get_at = bus.index(f'GetSetting("{key}")')
            gate_at = bus.index(gate)
            self.assertLess(defined, get_at, key)
            self.assertLess(get_at, gate_at, key)
            self.assertLess(gate_at, require_at, key)

    def test_trace_tiles_follow_gated_dist_bands_then_long_levers(self):
        load = body("settings.nut", "OpexLoadSettings")
        dist_gate = _gate_line("ROAD1Y_DIST_BANDS")
        long_band_gate = _gate_line("ROAD1Y_LONG_BAND")
        long_v3_gate = _gate_line("ROAD1Y_LONG_V3")
        trace_master = "ROAD_MAX_TRACE_TILES = ROAD1Y_DIST_BANDS ? 128 : 48;"
        self.assertIn(trace_master, load)
        self.assertLess(load.index(dist_gate), load.index(trace_master))
        self.assertLess(load.index(trace_master), load.index("if (ROAD1Y_LONG_BAND == 1)"))
        self.assertLess(load.index(long_band_gate), load.index("if (ROAD1Y_LONG_BAND == 1)"))
        self.assertLess(
            load.index(long_v3_gate),
            load.index("if (ROAD1Y_LONG_V3 == 1 && ROAD1Y_DIST_BANDS && ROAD1Y_LONG_BAND == 0)"),
        )
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_DIST_BANDS"], "false")

    def test_mail_on_pax_and_long_v3_default_to_one(self):
        info = source("info.nut")
        for name in ("road1y_mail_on_pax", "road1y_long_v3"):
            block = info.split(f'name = "{name}",')[1].split("});")[0]
            for difficulty in ("easy", "medium", "hard", "custom"):
                self.assertIn(f"{difficulty}_value = 1", block, name)
                self.assertNotIn(f"{difficulty}_value = 0", block, name)

    def test_every_road1y_off_value_is_the_master_inert_value(self):
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_DIST_BANDS"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_FLEET"], "0")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_EXTRA_STOPS"], "0")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_PAX_SITES"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_MAIL_ON_PAX"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_LONG_V3"], "0")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_BUS_FIXES"], "0")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_LOAD_ORDERS"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_PAX_ECONOMY"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_PAX_REFLEET"], "false")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_FLEET_UNLOCK"], "0")
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_LONG_BAND"], "0")
        load = body("settings.nut", "OpexLoadSettings")
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        for global_name, off in ROAD1Y_OFF.items():
            blob = load if global_name not in (
                "ROAD1Y_BUS_FIXES", "ROAD1Y_EXTRA_STOPS", "ROAD1Y_PAX_SITES",
            ) else bus
            if global_name == "ROAD1Y_MAIL_ON_PAX":
                self.assertIn(_gate_line(global_name), load)
                self.assertIn(_gate_line(global_name), bus)
            else:
                self.assertIn(f"if (!road1yRoadOnly) {global_name} = {off};", blob)


if __name__ == "__main__":
    unittest.main()
