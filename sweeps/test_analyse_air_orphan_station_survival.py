"""Fixtures sans OpenTTD pour les archives de sauvegardes A orphelines."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

from analyse_air_orphan_station_survival import (
    EvidenceError, analyse, checked_archive, decode_latest, inspect_station,
    main, plan_from_manifest,
)


def engine_date(year, month, day):
    return (date(year, month, day) - date(1, 1, 1)).days + 366


def parse_fixture(stream):
    return json.loads(b"".join(stream).decode("utf-8"))


def snapshot(when, stnn):
    return {"chunks": {"DATE": {"records": {"0": {"date": engine_date(*when)}}},
                       "STNN": {"records": stnn}}}


def station(owner, facility, tile, *, nested=True):
    body = {"base": [{"owner": owner, "facilities": facility}], "airport.tile": tile}
    return {"normal": [body]} if nested else {"normal": {"base": {"owner": owner,
                                                                     "facilities": facility},
                                                     "airport.tile": tile}}


class ArchiveFixture(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path_manifest = self.root / "test.manifest.json"
        self.path_orphans = self.root / "test_orphans.json"
        self.archive_root = self.root / "saves"
        self.archive_root.mkdir()
        self.seeds = [999, 5678, 2026]
        self.stations = [(58, 34929), (164, 53072), (106, 31166)]
        self.manifest = {
            "campaign_id": "synthetic", "configuration": {
                "seeds": self.seeds, "repeats": 1, "years": 3, "starting_year": 1970},
            "policies": [{"id": "reference", "role": "reference"}],
            "games": [
                {"game_id": f"synthetic:policy=reference:s{s}:r0", "seed": s,
                 "repeat": 0, "policy_id": "reference", "company_slots": {
                     "0": {"ai": "OpexAI", "policy_id": "reference"},
                     "1": {"ai": "AAAHogEx", "policy_id": "AAAHogEx"}}}
                for s in self.seeds]}
        self.orphans = {"runs": [
            {"file": f"results/synthetic_engine/reference_seed{s}_r0.log",
             "seed": s, "repeat": 0, "arm": "reference",
             "orphans": [{"status": "censored", "reason": "BFAIL", "station": sid,
                          "anchor": tile, "date": engine_date(1971, 2, 1),
                          "cost_a_gbp": 20000}]}
            for s, (sid, tile) in zip(self.seeds, self.stations)]}
        self.snapshots = [
            snapshot((1972, 12, 1), {str(58): station(0, 8, 34929)}),
            snapshot((1972, 11, 1), {164: station(1, 8, 53072, nested=False)}),
            snapshot((1972, 12, 1), {})]
        self.save_all()
        for i, game in enumerate(self.snapshots):
            self.make_archive(i, game)

    def save_all(self):
        self.path_manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.path_orphans.write_text(json.dumps(self.orphans), encoding="utf-8")

    def make_archive(self, index, last):
        dest = self.archive_root / str(index)
        (dest / "save").mkdir(parents=True)
        entries = []
        for name, game in (("0.sav", snapshot((1970, 1, 1), {})),
                           ("000000000.sav", snapshot((1970, 2, 1), {})),
                           ("000000001.sav", last)):
            target = dest / "save" / name
            data = json.dumps(game).encode("utf-8")
            target.write_bytes(data)
            entries.append({"path": "save/" + name, "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
        (dest / "archive.json").write_text(json.dumps({"experiment_index": index,
                                                        "savegames": entries}), encoding="utf-8")

    def inspect(self):
        return analyse(self.path_manifest, self.archive_root,
                       self.path_orphans, parse_savegame=parse_fixture)

    def test_mapping_hash_inventory_latest_and_station_results(self):
        result = self.inspect()
        self.assertEqual([g["seed"] for g in result["mapping"]], self.seeds)
        self.assertEqual([c["status"] for c in result["cases"]],
                         ["present_same_airport", "station_missing", "different_owner"])
        for item in result["cases"]:
            self.assertEqual(item["archive_index"], self.seeds.index(item["seed"]))
            self.assertEqual(Path(item["savegame"]).name, "000000001.sav")
            self.assertEqual(item["archive_saves_verified"], 3)
            self.assertEqual(item["observation_scope"], "at_snapshot_only")
            self.assertEqual(len(item["archive_json_sha256"]), 64)
        self.assertEqual(result["cases"][2]["snapshot_date"], "1972-11-01")
        self.assertEqual(result["expected_horizon_exclusive"], "1973-01-01")

    def test_station_fails_closed_on_inexact_recycling_and_missing_fields(self):
        stnn = {"58": station(0, 8, 40000)}
        self.assertEqual(inspect_station({"STNN": stnn}, 58, 34929)["status"],
                         "different_anchor")
        self.assertEqual(inspect_station({"STNN": {"58": station(0, 1, 34929)}},
                                         58, 34929)["status"], "not_an_airport")
        self.assertEqual(inspect_station({"STNN": {"58": station(0, 8, None)}},
                                         58, 34929)["status"], "unknown_airport_tile")
        with self.assertRaises(EvidenceError):
            inspect_station({"STNN": {"58": {"normal": [{"base": [{}]}]}}}, 58, 34929)
        with self.assertRaises(EvidenceError):
            inspect_station({"STNN": None}, 58, 34929)

    def test_reject_corrupt_hash_and_extra_or_missing_inventory(self):
        sav = self.archive_root / "0" / "save" / "000000001.sav"
        sav.write_bytes(sav.read_bytes() + b"tamper")
        with self.assertRaisesRegex(EvidenceError, "hash/taille"):
            checked_archive(self.archive_root, 0)
        self.make_archive_reset(0)
        (self.archive_root / "0" / "save" / "unexpected.sav").write_bytes(b"x")
        with self.assertRaisesRegex(EvidenceError, "inventaire"):
            checked_archive(self.archive_root, 0)

    def make_archive_reset(self, index):
        for p in (self.archive_root / str(index) / "save").glob("*.sav"):
            p.unlink()
        self.make_archive_into_existing(index)

    def make_archive_into_existing(self, index):
        entries = []
        dest = self.archive_root / str(index)
        for name, obj in (("0.sav", snapshot((1970, 1, 1), {})),
                          ("000000000.sav", snapshot((1970, 2, 1), {})),
                          ("000000001.sav", self.snapshots[index])):
            data = json.dumps(obj).encode("utf-8")
            (dest / "save" / name).write_bytes(data)
            entries.append({"path": "save/" + name, "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
        (dest / "archive.json").write_text(json.dumps({"experiment_index": index,
                                                        "savegames": entries}), encoding="utf-8")

    def test_reject_incomplete_plan_or_wrong_experiment_index(self):
        self.manifest["games"][0]["seed"] = 100
        self.save_all()
        with self.assertRaisesRegex(EvidenceError, "association archive/seed"):
            self.inspect()
        self.manifest["games"][0]["seed"] = 999
        self.save_all()
        archive_file = self.archive_root / "2" / "archive.json"
        payload = json.loads(archive_file.read_text(encoding="utf-8"))
        payload["experiment_index"] = 1
        archive_file.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "index non concordant"):
            self.inspect()

    def test_no_cross_campaign_or_duplicate_orphan(self):
        self.orphans["runs"][0]["file"] = "results/another_engine/reference_seed999_r0.log"
        self.save_all()
        with self.assertRaisesRegex(EvidenceError, "hors campagne"):
            self.inspect()
        self.orphans["runs"][0]["file"] = "results/synthetic_engine/reference_seed999_r0.log"
        self.orphans["runs"][0]["orphans"] *= 2
        self.save_all()
        with self.assertRaisesRegex(EvidenceError, "origine repetee"):
            self.inspect()

    def test_parse_date_and_cli_without_real_engine(self):
        latest = self.archive_root / "0" / "save" / "000000001.sav"
        chunks, day, timestamp = decode_latest(latest, parse_fixture)
        self.assertEqual(day, engine_date(1972, 12, 1))
        self.assertEqual(timestamp, "1972-12-01")
        self.assertIn("STNN", chunks)
        fake = types.SimpleNamespace(parse_savegame=parse_fixture)
        args = ["--manifest", str(self.path_manifest), "--archives", str(self.archive_root),
                "--orphans", str(self.path_orphans)]
        with patch.dict(sys.modules, {"openttdlab": fake}):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args), 0)
            obj = json.loads(out.getvalue())
            self.assertEqual(len(obj["cases"]), 3)
            self.assertEqual(obj["counts"]["present_same_airport"], 1)
            self.orphans["runs"][0]["orphans"][0]["status"] = "first_use_confirmed"
            self.save_all()
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(main(args), 2)
            self.assertIn("NON_VERIFIABLE", err.getvalue())


if __name__ == "__main__":
    unittest.main()
