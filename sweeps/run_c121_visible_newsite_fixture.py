"""Directed new-site quote in a real shared duel; never an economic A/B."""
import argparse
from datetime import date
import json
from pathlib import Path
import shutil
import sys

from .diag_r1_r3_mechanisms import new_directory, write_new
from .run_c121_target_limit_fixtures import stage
from .run_mechanism_fixtures import digest, tree_hashes

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None, *, fixture=None, settings=None, marker="C121_NEWSITE", stage_transform=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--years", type=int, default=1)
    args = parser.parse_args(argv)
    folder = new_directory(args.out, ROOT / "results/c121_target_limit")
    fixture = fixture or ROOT / "tests/mechanisms/c121_visible_newsite_vm.nut"
    target = stage(folder, fixture)
    if stage_transform is not None:
        stage_transform(target)
    if marker == "C121_VISIBLE_COST":
        from .run_mechanism_fixtures import replace_once
        source = target / "air_fleet.nut"
        source.write_text(replace_once(source.read_text(encoding="utf8"),
            "function OpexC121RefreshVisibleFleet(catalog, line, lines, force = false)",
            "function FxVCOriginal(catalog, line, lines, force = false)"), encoding="utf8")
    opponent = folder / "ai/AAAHogEx"
    shutil.copytree(ROOT / "ai/AAAHogEx-115", opponent)
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    from . import bench_v2
    from .diag_cadence_duel import collect, enable_script_debug
    from .game_health import assess_game, enable_engine_failure_capture
    settings = settings or (("c121_air_visible_competition", 1), ("decision_log", 1))
    copied = {"opex": tree_hashes(target), "opponent": tree_hashes(opponent)}
    cfg = bench_v2.make_cfg(1970)
    kind = ("matched_live_fleet_redundancy_not_economic" if stage_transform is not None
            else "passive_live_fleet_cost_not_economic" if marker == "C121_VISIBLE_COST"
            else "directed_newsite_quote_not_economic")
    write_new(folder / "plan.json", {"kind": kind,
        "seed": 42, "years": args.years, "settings": settings, "configuration": cfg,
        "copied_hashes": copied, "fixture_sha256": digest(fixture)})
    bench_v2.enable_savegame_cleanup()
    enable_script_debug()
    enable_engine_failure_capture()
    rows = list(openttdlab.run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=1, result_processor=collect,
        experiments=[{"arm": marker, "seed": 42, "years": args.years,
            "days": (date(1970+args.years, 1, 1)-date(1970, 1, 1)).days+32,
            "openttd_config": cfg,
            "ais": (openttdlab.local_folder(str(target), "OpexAI", settings),
                    openttdlab.local_folder(str(opponent), "AAAHogEx", ())),
            "log_path": str(folder / "engine.log"),
            "checkpoint_path": str(folder / "rows.jsonl")}],
        ai_libraries=(openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"))))
    log = (folder / "engine.log").read_text(encoding="utf8")
    health = assess_game([r for row in rows for r in row["records"]],
                        starting_year=1970, years=args.years, engine_log=log)
    checks = {"healthy": health["game_ok"],
              "mechanism_exposed": marker + "_WORLD pass=1" in log,
              "no_assertion": marker + "_ASSERT" not in log,
              "copies_unchanged": copied == {"opex": tree_hashes(target), "opponent": tree_hashes(opponent)}}
    report = {"checks": checks, "pass": all(checks.values()), "health": health,
              "log_sha256": digest(folder / "engine.log"), "economic_verdict": "not_evaluated"}
    write_new(folder / "report.json", report)
    print(json.dumps(checks, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("New-site exposure incomplete; preserve diagnostic")


if __name__ == "__main__":
    main()
