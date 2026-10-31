"""Shared-map AAAHogEx-115 duels: seeds 512 and 1337, rail-only vs air-only.

Run in Docker/Linux from worktree root. Both duels use the same OpenTTD 15.3
world parameters, the current shipped OpexAI ESTIM31 defaults, and the same
local AAAHogEx-115 adversary. Only OpexAI transport-mode settings change.
"""

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE_REPO = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
sys.path.insert(0, str(ROOT / "sweeps"))

from openttdlab import local_folder, run_experiments
import bench_v2
from bench_1v1_5y_20seeds import extract_company_record
from campaign_freeze import _frozen_library_descriptor

OUT = ROOT / "results/seeds512_1337_rail_air_only_vs_aaa_5y_20261031.json"
LIB_DIR = ROOT / "results/frozen_rail_libraries_20261030"
MANIFEST = ROOT / "results/v233l_frozen_manifest_libraries_20261030.json"
AAAHOGEX = Path(os.environ.get("OPEX_AAAHOGEX_DIR", str(BASE_REPO / "ai/AAAHogEx-115")))
SEEDS = (512, 1337)
YEARS = 5
SETTINGS = {
    "RAIL": "OpexAI[mode_air=0,mode_road=0,mode_water=0,mode_rail=1]",
    "AIR": "OpexAI[mode_air=1,mode_road=0,mode_water=0,mode_rail=0]",
}


def frozen_libraries():
    groups = json.loads(MANIFEST.read_text(encoding="utf8"))
    by_id = {item["requested_unique_id"]: item["resolved"] for item in groups}
    for entries in by_id.values():
        for item in entries:
            file = LIB_DIR / item["filename"]
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if actual != item["sha256"]:
                raise RuntimeError("NoAI archive changed: " + str(file))
    return (
        _frozen_library_descriptor("Queue.FibonacciHeap", by_id["51554648"], LIB_DIR),
        _frozen_library_descriptor("Pathfinder.Rail", by_id["5046524c"], LIB_DIR),
    )


def keep_duel(row):
    exp = row["experiment"]
    date = str(row["date"])
    label = exp["duel_mode"]
    seed = exp["seed"]
    error = bench_v2.script_failure_reason(row.get("output") or "")
    records = []
    for owner, ai in enumerate(("OpexAI", "AAAHogEx")):
        record = extract_company_record(row["chunks"], owner, [ai, seed, 0], date)
        record["duel_mode"] = label
        record["ai"] = ai
        record["company_slot"] = owner
        record["engine_failure"] = row.get("engine_failure")
        record["script_failure_reason"] = error
        # The raw output could be many MB; save only health markers.
        record["openttd_output"] = None
        records.append(record)
        bench_v2.append_checkpoint(record)
    return tuple(records)


def main():
    if os.name == "nt":
        raise RuntimeError("Run this experiment inside openttd-lab Docker/Linux")
    if not AAAHOGEX.joinpath("info.nut").is_file():
        raise RuntimeError("Missing locally frozen AAAHogEx-115: " + str(AAAHOGEX))
    if OUT.exists() or OUT.with_suffix(".jsonl").exists():
        raise FileExistsError("Refuse overwrite of completed benchmark")

    source = ROOT / "ai/OpexAI"
    if not source.joinpath("info.nut").is_file():
        raise RuntimeError("Missing OpexAI source")
    libs = frozen_libraries()
    arms = bench_v2.build_arms(SETTINGS.values())
    cfg = bench_v2.make_cfg(starting_year=1970, map_size=8)
    adversary = local_folder(str(AAAHOGEX), "AAAHogEx", ())
    experiments = [
        {
            "seed": seed, "days": 365 * YEARS, "openttd_config": cfg,
            "ais": (arms[description], adversary),
            "duel_mode": mode,
        }
        for seed in SEEDS for mode, description in SETTINGS.items()
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = OUT.with_suffix(".jsonl")
    os.environ["OPEX_BENCH_CHECKPOINT_PATH"] = str(bench_v2.CHECKPOINT_PATH.resolve())
    bench_v2.enable_savegame_cleanup()

    # Two 1-vs-1 simulations with exactly the same opponents on the same map.
    results = list(run_experiments(
        openttd_version="15.3",
        opengfx_version="7.1",
        max_workers=4,
        result_processor=keep_duel,
        experiments=experiments,
        ai_libraries=libs,
    ))

    grouped = {}
    for record in results:
        grouped.setdefault((record["seed"] if "seed" in record else record["run"][1],
                            record["duel_mode"], record["ai"]), []).append(record)
    if set(grouped) != {(seed, mode, name) for seed in SEEDS for mode in SETTINGS
                       for name in ("OpexAI", "AAAHogEx")}:
        raise RuntimeError("Missing a company in the benchmark")
    summary = {}
    series = {}
    for (seed, mode, name), records in sorted(grouped.items()):
        records.sort(key=lambda item: item["date"])
        expected = [f"{year}-{month:02d}-01"
                    for year in range(1970, 1975) for month in range(1, 13)]
        dates = [r["date"] for r in records]
        if dates != expected:
            raise RuntimeError(f"Missing or unexpected snapshots for {mode}/{name}: {dates}")
        if any(r["script_failure_reason"] for r in records):
            raise RuntimeError(f"Script error for {seed}/{mode}/{name}")
        final = records[-1]
        if not (final["company_present"] and final["vehs_chunk_valid"]
                and final["stnn_chunk_valid"] and final["profit_year_coverage"] == "complete"
                and final["profit_year"] is not None):
            raise RuntimeError(f"Unhealthy final snapshot for {seed}/{mode}/{name}")
        summary.setdefault(str(seed), {}).setdefault(mode, {})[name] = {
            k: final.get(k) for k in (
                "profit_year", "company_value", "income_last_year",
                "expenses_last_year", "n_vehicles", "primary_vehicles_by_mode",
                "stations_by_facility", "n_stations", "money",
                "current_loan", "median_station_rating",
                "performance_history", "vehs_chunk_valid", "stnn_chunk_valid",
                "company_present", "profit_year_coverage",
            )
        }
        series.setdefault(str(seed), {}).setdefault(mode, {})[name] = [
            {k: r.get(k) for k in ("date", "profit_year", "company_value",
                                   "n_vehicles", "primary_vehicles_by_mode",
                                   "stations_by_facility", "n_stations")}
            for r in records if r["date"].endswith("-12-01")
        ]

    out = {
        # Docker image does not ship Git. Set this at launch from the host's
        # verified clean worktree if exact commit provenance is desired.
        "code_commit": os.environ.get("OPEX_SOURCE_COMMIT") or None,
        "seeds": SEEDS, "years": YEARS, "first_year": 1970,
        "openttd_version": "15.3", "opengfx_version": "7.1",
        "shared_map_opponents": True, "config": cfg,
        "opexai_modes": SETTINGS, "frozen_aaahogex_source": str(AAAHOGEX),
        "library_manifest": str(MANIFEST.relative_to(ROOT)),
        "health": "240/240 monthly game snapshots, all 8 company series healthy",
        "summary_1974": summary, "annual_trajectories": series,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("SAVED", OUT, flush=True)
    for seed in SEEDS:
        for mode in SETTINGS:
            op, aaa = summary[str(seed)][mode]["OpexAI"], summary[str(seed)][mode]["AAAHogEx"]
            print(seed, mode, "OPEX", op["profit_year"], "AAA", aaa["profit_year"],
                  "RATIO", (100 * op["profit_year"] / aaa["profit_year"]),
                  "OPEX_VEHS", op["primary_vehicles_by_mode"],
                  "OPEX_STATIONS", op["stations_by_facility"], flush=True)


if __name__ == "__main__":
    main()
