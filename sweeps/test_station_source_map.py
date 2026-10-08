import struct
import unittest
import zlib
from station_source_map import raw_map_chunks, station_catchments, audit_sources, decode_map


def riff(tag, body):
    return tag.encode() + len(body).to_bytes(4, "big") + body


def fixture():
    chunks = b"".join(riff(k, b"\0\0") for k in ("MAPT", "MAP2", "MAPE", "M3LO", "MAP8"))
    # Table header block + sparse record block; the map reader skips their contents.
    chunks += b"TEST\x04\x04abc\x05defg\x00" + b"\0" * 4
    return b"OTTN" + struct.pack(">HH", 362, 0) + chunks


class RawMapTests(unittest.TestCase):
    def test_house_type_town_completion_and_lengths(self):
        raw = {"MAPT": bytes([0x30, 0x30, 0x50, 0]),
               "MAP2": struct.pack(">4H", 7, 7, 3, 0),
               "MAP8": struct.pack(">4H", 0xa001, 1, 0, 0),
               "M3LO": bytes([128, 0, 0, 0]), "MAPE": bytes([0, 0, 24, 0])}
        data = b"OTTN" + struct.pack(">HH", 362, 0) + b"".join(
            riff(k, v) for k, v in raw.items()) + b"\0"*4
        game = {"savegame_version": 362, "chunks": {
            "MAPS": {"records": {"0": {"dim_x": 2, "dim_y": 2}}},
            "CITY": {"records": {"7": {"population": 40}}}}}
        decoded = decode_map(data, game, [0, 40])
        self.assertEqual(decoded["town_population_reconstructed"], {7: 40})
        self.assertFalse(decoded["houses"][1]["completed"])
        self.assertEqual(decoded["facility_tiles"], [{"tile": 2, "station": 3, "type": 3}])
        with self.assertRaises(ValueError):
            decode_map(data.replace(b"MAP8", b"NONE"), game, [0, 40])

    def test_riff_with_table_and_compression(self):
        plain = fixture()
        a = raw_map_chunks(plain)
        compressed = b"OTTZ" + plain[4:8] + zlib.compress(plain[8:])
        self.assertEqual(raw_map_chunks(compressed), a)
        self.assertEqual(set(a), {"MAPT", "MAP2", "MAPE", "M3LO", "MAP8"})

    def test_fail_closed_on_version_truncation_duplicate_missing(self):
        for bad in (fixture()[:-1], fixture() + b"x", fixture()[:4] + b"\x01\x69" + fixture()[6:],
                    fixture().replace(b"MAP2", b"MAPT"), fixture().replace(b"MAP8", b"NONE")):
            with self.assertRaises(ValueError):
                raw_map_chunks(bad)

    def test_joined_stops_union_not_bounding_rectangle_and_map_edges(self):
        decoded = {"width": 32, "height": 16, "facility_tiles": [
            {"tile": 0, "station": 1, "type": 1},
            {"tile": 31, "station": 1, "type": 3},
            {"tile": 15, "station": 2, "type": 7}]}
        covered = station_catchments(decoded, {1: {"airport.type": 1}})
        self.assertIn(5 + 5*32, covered[1])  # city radius 5
        self.assertNotIn(6, covered[1])
        self.assertIn(28 + 3*32, covered[1])  # joined bus radius 3
        self.assertNotIn(27, covered[1])
        self.assertNotIn(15, covered[1])  # no filled bounding-box gap
        self.assertNotIn(2, covered)  # waypoint
        self.assertTrue(all(0 <= t < 512 for t in covered[1]))

    def test_same_house_sharing_and_loading_eligibility(self):
        def station(owner, speed):
            return {"normal": [{"airport.type": 1,
                "base": [{"town": 1, "owner": owner, "facilities": 8}],
                "goods": [{"rating": 128, "last_speed": speed, "status": 0}]}]}
        game = {"chunks": {k: {"records": v} for k, v in {
            "PATS": {"0": {"economy.town_cargogen_mode": 1,
                "economy.town_cargo_scale": 100, "station.serve_neutral_industries": 1,
                "order.selectgoods": 1, "station.modified_catchment": 1}},
            "CITY": {"0": {"xy": 17, "exclusive_counter": 0, "exclusivity": 255,
                "valid_history": 2, "supplied": [{"cargo": 0, "history": [{}, {"production": 100}]}]}},
            "STNN": {"0": station(0, 100), "1": station(1, 100), "2": station(2, 0)}
        }.items()}}
        decoded = {"width": 16, "height": 16, "town_population_reconstructed": {0: 40},
            "facility_tiles": [{"tile": 17, "station": i, "type": 1} for i in range(3)],
            "houses": [{"tile": 18, "town": 0, "completed": True, "population": 40},
                       {"tile": 19, "town": 0, "completed": False, "population": 80}]}
        audit = audit_sources(decoded, game, 0)
        self.assertEqual(audit["eligible_stations"], 2)
        self.assertEqual(audit["town_source_weights"], {0: 5})
        self.assertEqual(audit["station_sources"][0]["competition_ratio"], .5)
        self.assertEqual(audit["station_sources"][0]["shared_rival_weight"], 5)
        self.assertEqual(audit["station_sources"][0]["all_companies_monthly"], 100*129/256/2)
        self.assertEqual(audit["station_sources"][0]["covered_town_producers"], 2)
        self.assertEqual(audit["station_sources"][0]["producer_count"], 1)
        town = game["chunks"]["CITY"]["records"]["0"]
        town["valid_history"] = 0
        missing = audit_sources(decoded, game, 0)
        self.assertIsNone(missing["station_sources"][0]["all_companies_monthly"])
        town.update(valid_history=2, exclusive_counter=1, exclusivity=1)
        exclusive = audit_sources(decoded, game, 0)
        self.assertEqual(exclusive["eligible_stations"], 1)
        self.assertEqual(exclusive["station_sources"][1]["competition_ratio"], 1)


if __name__ == "__main__":
    unittest.main()
