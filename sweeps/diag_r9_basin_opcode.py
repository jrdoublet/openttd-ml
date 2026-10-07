"""R9: paired opcode diagnostic for the forced-false BASIN_SHARE guards.

Production is never edited.  Two disposable OpexAI copies are loaded in separate
OpenTTD experiments: the reference is byte-for-byte production; the variant removes
only the three executed BASIN_SHARE guards in candidates.nut.  The abandoned basin
policy remains disabled in both arms.  Existing probe_candidates_rail instrumentation
publishes rail-generation opcodes and candidate/call counts.

This script is diagnostic evidence only.  A positive saving does not authorize a
production/default change; adoption still needs the repository's paired 20x10
non-erosion gate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import sys


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab  # noqa: E402
import diag_cadence_duel as duel  # noqa: E402
from diag_c121_postbuild import run_isolated_arms  # noqa: E402
from diag_r1_r3_mechanisms import new_directory, write_new  # noqa: E402
from run_mechanism_fixtures import tree_hashes  # noqa: E402


SEEDS = [42, 100, 999, 1234, 5678]
PROFILE = re.compile(r"C41_RAIL_CANDIDATE_PROFILE\s+(.*)$")
FREIGHT = re.compile(r"C41_RAIL_FREIGHT_CANDIDATE_PROFILE\s+(.*)$")
PAX = re.compile(r"C41_RAIL_PAX_PROFILE\s+(.*)$")

BASIN_GUARD = re.compile(
    r"(?m)^(?P<indent>[ \t]+)if \(BASIN_SHARE && ss != null\) \{\n"
    r"(?P=indent)  (?:(?:monthly = OpexShareBasin\(monthly, lines, ss\.stationId, cargo\);)|"
    r"(?:inputMonthly = OpexShareBasin\(inputMonthly, lines, ss\.stationId, cargoIn\);))\n"
    r"(?P=indent)\}\n"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_copy(target: Path, variant: bool) -> dict:
    shutil.copytree(ROOT / "ai" / "OpexAI", target)
    if not variant:
        return {"removed_guards": 0, "candidates_sha256": digest(target / "candidates.nut")}
    path = target / "candidates.nut"
    text = path.read_text(encoding="utf-8")
    text, removed = BASIN_GUARD.subn("", text)
    if removed != 3:
        raise ValueError(f"R9 staging expected 3 BASIN_SHARE guards, got {removed}")
    path.write_text(text, encoding="utf-8")
    if text.count("if (BASIN_SHARE && ss != null)") != 0:
        raise ValueError("R9 staged candidates.nut still contains BASIN_SHARE guard")
    return {"removed_guards": removed, "candidates_sha256": digest(path)}


def fields(rest: str) -> dict[str, int | str]:
    out = {}
    for token in rest.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            out[key] = int(value)
        except ValueError:
            out[key] = value
    return out


def parse_profiles(text: str) -> dict:
    result = {"rail": [], "freight": [], "pax": []}
    for raw in text.splitlines():
        for name, pattern in (("rail", PROFILE), ("freight", FREIGHT), ("pax", PAX)):
            match = pattern.search(raw)
            if match:
                result[name].append(fields(match.group(1)))
                break
    rail = result["rail"]
    result["rail_samples"] = len(rail)
    result["rail_ops_total"] = sum(int(row.get("ops", 0)) for row in rail)
    result["rail_ops_mean"] = statistics.mean(int(row.get("ops", 0)) for row in rail) if rail else None
    return result


def semantic_signature(profile: dict) -> dict:
    """Ignore opcode fields; keep quantities that must remain behaviorally equal."""
    return {
        "rail": [(row.get("candidates"),) for row in profile["rail"]],
        "freight": [(
            row.get("industry_candidate_calls"), row.get("town_candidate_calls")
        ) for row in profile["freight"]],
        "pax": [(
            row.get("pairs_scanned"), row.get("candidate_calls"), row.get("candidates")
        ) for row in profile["pax"]],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 10:
        raise ValueError("workers must be 1..10")

    folder = new_directory(args.out, ROOT / "results/r9_basin_opcode")
    production = ROOT / "ai" / "OpexAI"
    before = tree_hashes(production)
    copies = {}
    staged = {}
    arms = {}
    for name, variant in (("reference", False), ("variant", True)):
        target = folder / "copies" / name / "OpexAI"
        staged[name] = stage_copy(target, variant)
        copies[name] = target
        arms[name] = openttdlab.local_folder(
            str(target), "OpexAI", (("probe_candidates_rail", 1), ("probe_catalogue", 1)))

    opponent = folder / "copies" / "AAAHogEx-115"
    shutil.copytree(ROOT / "ai" / "AAAHogEx-115", opponent)
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    frozen = tree_hashes(folder / "copies")
    cfg = duel.bench_v2.make_cfg(1970)
    days = (date(1970 + args.years, 1, 1) - date(1970, 1, 1)).days + 32
    write_new(folder / "plan.json", {
        "kind": "R9_BASIN_SHARE_opcode_diagnostic_not_adoption",
        "intervention": "remove three forced-false BASIN_SHARE guards from candidates.nut only",
        "seeds": args.seeds, "years": args.years, "workers": args.workers,
        "settings": {"probe_candidates_rail": 1, "probe_catalogue": 1}, "configuration": cfg,
        "source_loading": "separate_run_experiments_per_arm",
        "production_hashes": before, "staged": staged,
        "decision_rule": "require positive rail-generation opcode saving and exact semantic profile signatures before any 20x10 adoption gate",
    })

    experiments = [{
        "arm": arm, "seed": seed, "years": args.years, "days": days,
        "openttd_config": cfg, "ais": (arms[arm], aaa),
        "log_path": str(folder / f"{arm}_{seed}.log"),
        "checkpoint_path": str(folder / f"{arm}_{seed}.jsonl"),
    } for seed in args.seeds for arm in ("reference", "variant")]
    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(run_isolated_arms(
        openttdlab.run_experiments,
        openttd_version=duel.bench_v2.OPENTTD_VERSION,
        opengfx_version=duel.bench_v2.OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=duel.collect,
        ai_libraries=(
            openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["arm"], row["seed"]].append(row)
    games = [duel.finish_game(series, args.years) for series in grouped.values()]
    by_game = {(g["arm"], g["seed"]): g for g in games}

    profiles = {}
    pairs = []
    for seed in args.seeds:
        per_arm = {}
        for arm in ("reference", "variant"):
            game = by_game.get((arm, seed))
            if game is None:
                per_arm[arm] = None
                continue
            parsed = parse_profiles(Path(game["log_path"]).read_text(encoding="utf-8"))
            profiles[f"{arm}_{seed}"] = parsed
            per_arm[arm] = parsed
        ref, var = per_arm["reference"], per_arm["variant"]
        comparable = ref is not None and var is not None and ref["rail_samples"] > 0 \
            and ref["rail_samples"] == var["rail_samples"]
        signature_equal = comparable and semantic_signature(ref) == semantic_signature(var)
        saving = (ref["rail_ops_total"] - var["rail_ops_total"]) if comparable else None
        saving_per_sample = saving / ref["rail_samples"] if comparable else None
        pairs.append({"seed": seed, "comparable": comparable,
                      "semantic_signature_equal": signature_equal,
                      "reference_samples": ref["rail_samples"] if ref else 0,
                      "variant_samples": var["rail_samples"] if var else 0,
                      "reference_ops": ref["rail_ops_total"] if ref else None,
                      "variant_ops": var["rail_ops_total"] if var else None,
                      "saving_ops": saving, "saving_per_sample": saving_per_sample})

    usable = [p for p in pairs if p["comparable"]]
    savings = [p["saving_per_sample"] for p in usable]
    checks = {
        "all_games": len(games) == len(experiments) and all(g["valid"] for g in games),
        "all_pairs_comparable": len(usable) == len(args.seeds),
        "semantic_profiles_equal": bool(usable) and all(p["semantic_signature_equal"] for p in usable),
        "positive_mean_saving": bool(savings) and statistics.mean(savings) > 0,
        "production_sources_unchanged": before == tree_hashes(production),
        "staged_copies_unchanged": frozen == tree_hashes(folder / "copies"),
    }
    comparison = {
        "pairs": pairs,
        "mean_saving_per_profile_sample": statistics.mean(savings) if savings else None,
        "median_saving_per_profile_sample": statistics.median(savings) if savings else None,
        "positive_pairs": sum(x > 0 for x in savings),
        "negative_pairs": sum(x < 0 for x in savings),
    }
    report = {"checks": checks, "diagnostic_pass": all(checks.values()),
              "comparison": comparison, "games": games,
              "economic_verdict": "not_evaluated", "profiles": profiles}
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "comparison": comparison}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
