"""Technical A/B/C/D isolation smoke for C121 economics and incremental catalog.

Production sources are never edited by this runner.  The normal runtime gates
the incremental catalog behind C121 economics, so every disposable copy gets
the same diagnostic-only decoupling before the four setting combinations run.
This proves effective settings/source loading only; it is not an economic test.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from diag_c121_postbuild import run_isolated_arms
from diag_r1_r3_mechanisms import new_directory, write_new
from run_mechanism_fixtures import replace_once, tree_hashes

ARMS = {
    "A": {"c121_air_economics": 0, "c121_catalog_incremental": 0},
    "B": {"c121_air_economics": 0, "c121_catalog_incremental": 1},
    "C": {"c121_air_economics": 1, "c121_catalog_incremental": 0},
    "D": {"c121_air_economics": 1, "c121_catalog_incremental": 1},
}
MARKER = re.compile(r"\[script:\d+\]\s*\[(\d+)\].*?C121_ABCD\s+(.*)$")


def stage_copy(target: Path) -> None:
    shutil.copytree(ROOT / "ai/OpexAI", target)
    settings = target / "settings.nut"
    text = settings.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '  C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS\n'
        '      && AIController.GetSetting("c121_catalog_incremental") != 0;',
        '  C121_CATALOG_INCREMENTAL = AIController.GetSetting("c121_catalog_incremental") != 0;',
    )
    settings.write_text(text, encoding="utf-8")

    fixture = ROOT / "tests/mechanisms/c121_abcd_probe.nut"
    shutil.copy2(fixture, target / fixture.name)
    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, "function OpexAI::Start()",
                        'require("c121_abcd_probe.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();\n",
                        "  OpexLoadSettings();\n  C121ABCDSource();\n")
    main.write_text(text, encoding="utf-8")


def marker(text: str):
    rows = []
    for raw in text.splitlines():
        match = MARKER.search(raw)
        if not match:
            continue
        fields = {}
        for token in match.group(2).split():
            if "=" in token:
                key, value = token.split("=", 1)
                fields[key] = value
        rows.append({"owner": int(match.group(1)), **fields})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    import openttdlab
    import diag_cadence_duel as duel

    folder = new_directory(args.out, ROOT / "results/c121_abcd")
    before = duel.source_hashes(ROOT)
    fixture = ROOT / "tests/mechanisms/c121_abcd_probe.nut"
    fixture_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    arms = {}
    copies = {}
    resolved = {}
    for name, values in ARMS.items():
        target = folder / "copies" / name / "OpexAI"
        stage_copy(target)
        copies[name] = target
        settings = tuple((key, value) for key, value in values.items())
        arms[name] = openttdlab.local_folder(str(target), "OpexAI", settings)
        spec = "OpexAI[" + ",".join(f"{key}={value}" for key, value in values.items()) + "]"
        resolved[name] = duel.bench_v2.resolve_opex_arm_settings(spec)

    opponent = folder / "copies/AAAHogEx-115"
    shutil.copytree(ROOT / "ai/AAAHogEx-115", opponent)
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    frozen = tree_hashes(folder / "copies")
    cfg = duel.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {
        "kind": "technical_isolation_not_economic", "seed": 42, "years": 1,
        "arms": ARMS, "resolved": resolved, "source_hashes": before,
        "source_loading": "separate_run_experiments_per_arm",
        "diagnostic_copy_change": "remove catalog=>C121 load gate equally in all arms",
        "copy_hashes": frozen, "fixture_sha256": fixture_hash,
        "configuration": cfg, "workers": 3,
    })

    experiments = [{
        "arm": name, "seed": 42, "years": 1, "days": 397,
        "openttd_config": cfg, "ais": (arms[name], aaa),
        "log_path": str(folder / f"{name}_42.log"),
        "checkpoint_path": str(folder / f"{name}_42.jsonl"),
    } for name in ARMS]
    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(run_isolated_arms(
        openttdlab.run_experiments,
        openttd_version=duel.bench_v2.OPENTTD_VERSION,
        opengfx_version=duel.bench_v2.OPENGFX_VERSION,
        experiments=experiments,
        max_workers=3,
        result_processor=duel.collect,
        ai_libraries=(
            openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["arm"], row["seed"]].append(row)
    games = [duel.finish_game(series, 1) for series in grouped.values()]

    markers = {}
    effective = True
    for game in games:
        name = game["arm"]
        rows_for_log = marker(Path(game["log_path"]).read_text(encoding="utf-8"))
        markers[name] = rows_for_log
        expected = ARMS[name]
        effective = effective and len(rows_for_log) == 1
        if len(rows_for_log) == 1:
            row = rows_for_log[0]
            effective = effective and row.get("owner") == 0 and row.get("v") == "1"
            effective = effective and row.get("econ") == str(expected["c121_air_economics"])
            effective = effective and row.get("catalog") == str(expected["c121_catalog_incremental"])
            effective = effective and row.get("c115") == "1"

    checks = {
        "all_games": len(games) == 4 and all(game["valid"] for game in games),
        "effective_matrix": effective and set(markers) == set(ARMS),
        "sources_unchanged": before == duel.source_hashes(ROOT),
        "copies_unchanged": frozen == tree_hashes(folder / "copies"),
        "fixture_unchanged": fixture_hash == hashlib.sha256(fixture.read_bytes()).hexdigest(),
    }
    write_new(folder / "report.json", {
        "checks": checks, "pass": all(checks.values()), "markers": markers,
        "games": games, "economic_verdict": "not_evaluated",
    })
    print(json.dumps({"checks": checks, "markers": markers}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
