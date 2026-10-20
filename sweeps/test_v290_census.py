"""Unit tests and static contracts for V290 industry census probe and analyzer."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v290_census import (
    analyze_census,
    parse_v290_logs,
    write_csv_summary,
    stage_fixture,
    TARGET_CARGOS,
)

SAMPLE_SYNTHETIC_LOG = """
dbg: [ai] [1] [I] V290_START map_w=256 map_h=256
dbg: [ai] [1] [I] V290_WATER_INIT comps=4
dbg: [ai] [1] [I] V290_IND id=1 type=Oil_Rig tile=1000 x=10 y=20 on_water=1 coastal=1 water_comp=0 dock=1 prod=OIL_:15,PASS:2 accept=-
dbg: [ai] [1] [I] V290_IND id=2 type=Oil_Refinery tile=2500 x=40 y=30 on_water=0 coastal=1 water_comp=0 dock=0 prod=- accept=OIL_
dbg: [ai] [1] [I] V290_IND id=3 type=Coal_Mine tile=5000 x=80 y=50 on_water=0 coastal=1 water_comp=1 dock=0 prod=COAL:120 accept=-
dbg: [ai] [1] [I] V290_IND id=4 type=Power_Station tile=6000 x=120 y=70 on_water=0 coastal=1 water_comp=1 dock=0 prod=- accept=COAL
dbg: [ai] [1] [I] V290_IND id=5 type=Power_Station tile=8000 x=150 y=90 on_water=0 coastal=0 water_comp=-1 dock=0 prod=- accept=COAL
dbg: [ai] [1] [I] V290_IND id=6 type=Iron_Ore_Mine tile=9000 x=20 y=100 on_water=0 coastal=1 water_comp=2 dock=0 prod=IORE:80 accept=-
dbg: [ai] [1] [I] V290_IND id=7 type=Steel_Mill tile=9500 x=60 y=140 on_water=0 coastal=1 water_comp=3 dock=0 prod=STEL:40 accept=IORE
dbg: [ai] [1] [I] V290_MONTH date=1970-01-01 industries=7 oil_rigs=1 coastal=6
dbg: [ai] [1] [I] V290_PAIR src=1 dst=2 cargo=OIL_ dist=40 same_comp=1
dbg: [ai] [1] [I] V290_PAIR src=3 dst=4 cargo=COAL dist=60 same_comp=1
dbg: [ai] [1] [I] V290_PAIR src=6 dst=7 cargo=IORE dist=80 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY cargo=COAL pairs=1 same_comp=1
dbg: [ai] [1] [I] V290_SUMMARY cargo=IORE pairs=1 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY cargo=GRAI pairs=0 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY cargo=WOOD pairs=0 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY cargo=OIL_ pairs=1 same_comp=1
dbg: [ai] [1] [I] V290_SUMMARY cargo=STEL pairs=0 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY cargo=GOOD pairs=0 same_comp=0
dbg: [ai] [1] [I] V290_SUMMARY_TOTAL total_pairs=3 total_same_comp=2
dbg: [ai] [1] [I] V290_MONTH date=1970-02-01 industries=7 oil_rigs=1 coastal=6
dbg: [ai] [1] [I] V290_MONTH date=1971-01-01 industries=7 oil_rigs=1 coastal=6
dbg: [ai] [1] [I] V290_IND id=8 type=Oil_Rig tile=1200 x=15 y=25 on_water=1 coastal=1 water_comp=0 dock=1 prod=OIL_:15,PASS:2 accept=-
dbg: [ai] [1] [I] V290_MONTH date=1971-06-01 industries=8 oil_rigs=2 coastal=7
dbg: [ai] [1] [I] V290_MONTH date=1972-01-01 industries=8 oil_rigs=2 coastal=7
dbg: [ai] [1] [I] V290_IND_CLOSE id=3
dbg: [ai] [1] [I] V290_MONTH date=1972-03-01 industries=7 oil_rigs=2 coastal=6
"""


class TestV290Census(unittest.TestCase):
    def test_parse_v290_logs(self) -> None:
        data = parse_v290_logs(SAMPLE_SYNTHETIC_LOG)
        self.assertEqual(data["map_size"], {"w": 256, "h": 256})
        self.assertEqual(data["water_comps"], 4)
        self.assertEqual(len(data["industries"]), 8)
        self.assertIn(1, data["industries"])
        self.assertEqual(data["industries"][1]["type"], "Oil_Rig")
        self.assertEqual(data["industries"][1]["on_water"], 1)
        self.assertEqual(data["industries"][1]["dock"], 1)
        self.assertEqual(data["industries"][1]["water_comp"], 0)

        # Closed industry
        self.assertEqual(data["closed_industries"], [3])

        # Months
        self.assertEqual(len(data["months"]), 6)
        self.assertEqual(data["months"][0]["date"], "1970-01-01")
        self.assertEqual(data["months"][0]["oil_rigs"], 1)
        self.assertEqual(data["months"][-1]["oil_rigs"], 2)

        # Pairs
        self.assertEqual(len(data["pairs"]), 3)
        self.assertEqual(data["pairs"][0]["cargo"], "OIL_")
        self.assertEqual(data["pairs"][0]["same_comp"], 1)
        self.assertEqual(data["pairs"][2]["cargo"], "IORE")
        self.assertEqual(data["pairs"][2]["same_comp"], 0)

    def test_analyze_census(self) -> None:
        analysis = analyze_census(SAMPLE_SYNTHETIC_LOG, years=3)
        self.assertEqual(analysis["oil_rigs_start"], 1)
        self.assertEqual(analysis["oil_rigs_by_year"]["1970"], 1)
        self.assertEqual(analysis["oil_rigs_by_year"]["1971"], 1)
        self.assertEqual(analysis["oil_rigs_by_year"]["1972"], 2)

        self.assertEqual(analysis["total_industries_start"], 7)
        self.assertEqual(analysis["closed_industries_count"], 1)

        # Coastal industries by type
        coastal_types = analysis["coastal_industries_by_type"]
        self.assertEqual(coastal_types.get("Oil_Rig"), 2)
        self.assertEqual(coastal_types.get("Oil_Refinery"), 1)
        self.assertEqual(coastal_types.get("Coal_Mine"), 1)
        self.assertEqual(coastal_types.get("Power_Station"), 1)  # only id 4 was coastal, id 5 was not
        self.assertEqual(coastal_types.get("Iron_Ore_Mine"), 1)
        self.assertEqual(coastal_types.get("Steel_Mill"), 1)
        self.assertEqual(analysis["coastal_industries_count"], 7)

        # Pairs by cargo
        pairs_cargo = analysis["pairs_by_cargo"]
        self.assertEqual(pairs_cargo["OIL_"]["total"], 1)
        self.assertEqual(pairs_cargo["OIL_"]["same_comp"], 1)
        self.assertEqual(pairs_cargo["OIL_"]["median_dist"], 40.0)

        self.assertEqual(pairs_cargo["COAL"]["total"], 1)
        self.assertEqual(pairs_cargo["COAL"]["same_comp"], 1)
        self.assertEqual(pairs_cargo["COAL"]["median_dist"], 60.0)

        self.assertEqual(pairs_cargo["IORE"]["total"], 1)
        self.assertEqual(pairs_cargo["IORE"]["same_comp"], 0)
        self.assertIsNone(pairs_cargo["IORE"]["median_dist"])

        self.assertEqual(analysis["total_pairs"], 3)
        self.assertEqual(analysis["total_same_comp"], 2)
        # Median of [40, 60] is 50.0
        self.assertEqual(analysis["median_distance_same_comp"], 50.0)

    def test_csv_summary_generation(self) -> None:
        analysis42 = analyze_census(SAMPLE_SYNTHETIC_LOG, years=3)
        results = {42: analysis42}

        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tf:
            csv_path = Path(tf.name)

        try:
            write_csv_summary(csv_path, results, years=3)
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["seed"], "42")
            self.assertEqual(row["years"], "3")
            self.assertEqual(row["oil_rigs_start"], "1")
            self.assertEqual(row["oil_rigs_1970"], "1")
            self.assertEqual(row["oil_rigs_1971"], "1")
            self.assertEqual(row["oil_rigs_1972"], "2")
            self.assertEqual(row["total_industries"], "7")
            self.assertEqual(row["coastal_industries"], "7")
            self.assertEqual(row["same_comp_pairs_total"], "2")
            self.assertEqual(row["same_comp_pairs_oil_"], "1")
            self.assertEqual(row["same_comp_pairs_coal"], "1")
            self.assertEqual(row["same_comp_pairs_iore"], "0")
            self.assertEqual(row["median_dist_same_comp"], "50.0")
        finally:
            csv_path.unlink(missing_ok=True)

    def test_static_contracts_no_build_calls(self) -> None:
        """Verify that IndustryCensusProbe contains zero build or modification calls."""
        main_nut = ROOT / "sweeps/fixtures/IndustryCensusProbe/main.nut"
        self.assertTrue(main_nut.is_file(), "main.nut fixture exists")
        code = main_nut.read_text(encoding="utf-8")

        forbidden_patterns = [
            r"\bAI\w+\.Build\w+",
            r"\bAI\w+\.Demolish\w+",
            r"\bAI\w+\.Level\w+",
            r"\bAI\w+\.Plant\w+",
            r"\bAI\w+\.Prospect\w+",
            r"\bAISign\.BuildSign\b",
            r"\bAIMarine\.Build\w+",
            r"\bAIRail\.Build\w+",
            r"\bAIRoad\.Build\w+",
            r"\bAIAirport\.Build\w+",
            r"\bAIStation\.Build\w+",
            r"\bAIVehicle\.Build\w+",
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, code)
            self.assertEqual(matches, [], f"Fixture must not contain build calls matching {pattern}")

    def test_static_contracts_api_validity(self) -> None:
        """Verify that all NoAI API functions used in IndustryCensusProbe exist in noai_api_15.3.tsv."""
        tsv_path = ROOT / "docs/noai_api_15.3.tsv"
        self.assertTrue(tsv_path.is_file(), "noai_api_15.3.tsv exists")

        # Load valid API tokens
        valid_api_methods: set[tuple[str, str]] = set()
        valid_classes: set[str] = set()

        for line in tsv_path.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                kind, cls = parts[0], parts[1]
                valid_classes.add(cls)
                if len(parts) >= 3 and parts[2]:
                    method = parts[2]
                    valid_api_methods.add((cls, method))

        main_nut = ROOT / "sweeps/fixtures/IndustryCensusProbe/main.nut"
        code = main_nut.read_text(encoding="utf-8")

        # Extract AI<Class>.<Method> calls
        call_pattern = re.compile(r"\b(AI[A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\b")
        for cls, method in call_pattern.findall(code):
            self.assertIn(cls, valid_classes, f"Class {cls} must be declared in NoAI 15.3 API")
            self.assertIn(
                (cls, method),
                valid_api_methods,
                f"Method {cls}.{method} must exist in NoAI 15.3 API tsv",
            )

        # Extract AI<Class> constructor / class references
        class_pattern = re.compile(r"\b(AI[A-Za-z0-9_]+)\b")
        for cls in class_pattern.findall(code):
            self.assertIn(cls, valid_classes, f"Symbol {cls} must exist in NoAI 15.3 API")

    def test_fixture_info_metadata(self) -> None:
        """Verify that info.nut has valid metadata."""
        info_nut = ROOT / "sweeps/fixtures/IndustryCensusProbe/info.nut"
        self.assertTrue(info_nut.is_file(), "info.nut fixture exists")
        code = info_nut.read_text(encoding="utf-8")

        self.assertIn('function CreateInstance() { return "IndustryCensusProbe"; }', code)
        self.assertIn('function GetAPIVersion() { return "15"; }', code)
        self.assertIn('RegisterAI(IndustryCensusProbeInfo());', code)

        short_name_match = re.search(r'function GetShortName\(\)\s*\{\s*return\s*"([^"]+)";\s*\}', code)
        self.assertIsNotNone(short_name_match)
        short_name = short_name_match.group(1)
        self.assertEqual(len(short_name), 4, f"GetShortName must be exactly 4 chars: {short_name}")

    def test_stage_fixture(self) -> None:
        """Verify stage_fixture copies files and writes valid sources.json."""
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "bundle"
            manifest = stage_fixture(dest)
            self.assertIn("main.nut", manifest)
            self.assertIn("info.nut", manifest)
            self.assertTrue((dest / "main.nut").is_file())
            self.assertTrue((dest / "info.nut").is_file())
            self.assertTrue((dest / "sources.json").is_file())
            sources_data = json.loads((dest / "sources.json").read_text(encoding="utf-8"))
            self.assertEqual(sources_data, manifest)

    def test_dry_run_cli(self) -> None:
        """Verify bench_v290_census.py --dry-run prints expected plan and docker command."""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "sweeps/bench_v290_census.py"), "--dry-run", "--seeds", "42", "100", "--years", "3"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, f"dry-run returned {proc.returncode}: {proc.stderr}")
        self.assertIn("=== DRY-RUN PLAN ===", proc.stdout)
        self.assertIn("docker run", proc.stdout)
        self.assertIn("IndustryCensusProbe", proc.stdout or proc.stderr or "")

    def test_parse_log_cli(self) -> None:
        """Verify bench_v290_census.py --parse-log prints valid JSON analysis."""
        with tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False) as tf:
            tf.write(SAMPLE_SYNTHETIC_LOG)
            log_path = Path(tf.name)

        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "sweeps/bench_v290_census.py"), "--parse-log", str(log_path)],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            self.assertEqual(proc.returncode, 0, f"--parse-log returned {proc.returncode}: {proc.stderr}")
            data = json.loads(proc.stdout)
            self.assertEqual(data["oil_rigs_start"], 1)
            self.assertEqual(data["total_same_comp"], 2)
            self.assertEqual(data["median_distance_same_comp"], 50.0)
        finally:
            log_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
