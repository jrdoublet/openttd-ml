"""Copied-source exposure diagnostic for ``road_loading_fix``.

Production ``ai/OpexAI`` is never edited.  A disposable copy keeps
``road_loading_fix=0`` and adds a shadow-only counterfactual inside
``_refleetRoadLines``.  The live OFF decision is computed first; only then do
we inspect ``AIVehicle.GetState`` for vehicles that were already observed at
speed 0.  The diagnostic never executes the ON branch or changes target/refill
decisions.  It emits one aggregate line per completed calendar year.

This is mechanism/exposure evidence only, never an economic A/B or adoption
campaign.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
import shutil
import sys


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from diag_r1_r3_mechanisms import new_directory, write_new  # noqa: E402
from run_mechanism_fixtures import replace_once, tree_hashes  # noqa: E402


DEFAULT_SEEDS = (512, 515222, 230185)
START = 1970
PROBE_RE = re.compile(r"ROAD_LOADING_EXPOSURE\s+(.*)$")


def parse_fields(text: str) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        try:
            out[key] = int(raw)
        except ValueError:
            out[key] = raw
    return out


def instrument(target: Path) -> None:
    """Add the shadow probe to a disposable OpexAI directory only."""
    globals_path = target / "globals_pre.nut"
    globals_text = globals_path.read_text(encoding="utf-8")
    globals_text = replace_once(
        globals_text,
        "ROAD_LOADING_FIX <- false;\n",
        "ROAD_LOADING_FIX <- false;\n"
        "ROAD_LOADING_EXPOSURE_DIAG <- null; /* copied-source diagnostic only */\n",
    )
    globals_path.write_text(globals_text, encoding="utf-8")

    road_path = target / "task_road.nut"
    road_text = road_path.read_text(encoding="utf-8")

    helper_anchor = "/* Une ligne routiere a zero (ou trop peu de) vehicules avec arrets et depot encore la :\n"
    helpers = r'''/* Copied-source ROAD_LOADING exposure probe.  Never shipped in production. */
function OpexRoadLoadingExposureNew(year)
{
  return {
    year = year,
    eligible = 0,
    stopped = 0,
    state_reads = 0,
    invalid_stopped = 0,
    at_station = 0,
    off_station = 0,
    wait_flip = 0,
    extra_flip = 0,
    target_flip = 0,
    new_refill = 0,
    refill_delta_sum = 0,
    at_station_pax = 0,
    at_station_freight = 0,
    wait_flip_pax = 0,
    wait_flip_freight = 0,
    extra_flip_pax = 0,
    extra_flip_freight = 0,
    target_flip_pax = 0,
    target_flip_freight = 0
  };
}

function OpexRoadLoadingExposureLog(s)
{
  AILog.Info("ROAD_LOADING_EXPOSURE year=" + s.year
      + " eligible=" + s.eligible + " stopped=" + s.stopped
      + " state_reads=" + s.state_reads + " invalid_stopped=" + s.invalid_stopped
      + " at_station=" + s.at_station + " off_station=" + s.off_station
      + " wait_flip=" + s.wait_flip + " extra_flip=" + s.extra_flip
      + " target_flip=" + s.target_flip + " new_refill=" + s.new_refill
      + " refill_delta_sum=" + s.refill_delta_sum
      + " at_station_pax=" + s.at_station_pax + " at_station_freight=" + s.at_station_freight
      + " wait_flip_pax=" + s.wait_flip_pax + " wait_flip_freight=" + s.wait_flip_freight
      + " extra_flip_pax=" + s.extra_flip_pax + " extra_flip_freight=" + s.extra_flip_freight
      + " target_flip_pax=" + s.target_flip_pax + " target_flip_freight=" + s.target_flip_freight);
}

'''
    road_text = replace_once(road_text, helper_anchor, helpers + helper_anchor)

    entry_anchor = "function OpexAI::_refleetRoadLines(year)\n{\n  if (!ROAD_REFLEET) return;\n"
    entry_replacement = entry_anchor + r'''  local rlfFlush = null;
  if (ROAD_LOADING_EXPOSURE_DIAG == null || ROAD_LOADING_EXPOSURE_DIAG.year != year) {
    rlfFlush = ROAD_LOADING_EXPOSURE_DIAG;
    ::ROAD_LOADING_EXPOSURE_DIAG = OpexRoadLoadingExposureNew(year);
  }
  local rlfEligible = 0;
  local rlfStoppedLines = 0;
  local rlfStateReads = 0;
  local rlfInvalidStopped = 0;
  local rlfAtStation = 0;
  local rlfOffStation = 0;
  local rlfWaitFlip = 0;
  local rlfExtraFlip = 0;
  local rlfTargetFlip = 0;
  local rlfNewRefill = 0;
  local rlfRefillDelta = 0;
  local rlfAtStationPax = 0;
  local rlfAtStationFreight = 0;
  local rlfWaitFlipPax = 0;
  local rlfWaitFlipFreight = 0;
  local rlfExtraFlipPax = 0;
  local rlfExtraFlipFreight = 0;
  local rlfTargetFlipPax = 0;
  local rlfTargetFlipFreight = 0;
'''
    road_text = replace_once(road_text, entry_anchor, entry_replacement)

    vehicles_anchor = (
        "    local vehicles = OpexLineVehicleIds(line, stationA);\n"
        "    local isAnyWaiting = false;\n"
        "    local movingCount = 0;\n"
        "    foreach (v in vehicles) {\n"
    )
    vehicles_replacement = (
        "    local vehicles = OpexLineVehicleIds(line, stationA);\n"
        "    local isAnyWaiting = false;\n"
        "    local movingCount = 0;\n"
        "    local rlfStopped = [];\n"
        "    foreach (v in vehicles) {\n"
    )
    road_text = replace_once(road_text, vehicles_anchor, vehicles_replacement)

    stopped_anchor = "      if (AIVehicle.GetCurrentSpeed(v) == 0) {\n"
    road_text = replace_once(
        road_text,
        stopped_anchor,
        stopped_anchor + "        rlfStopped.append(v);\n",
    )

    base_target_anchor = "    if (have + extraNeeded > target) target = have + extraNeeded;\n"
    road_text = replace_once(
        road_text,
        base_target_anchor,
        "    local rlfBaseTarget = target;\n" + base_target_anchor,
    )

    decision_anchor = (
        "    if (target > physicalCap) target = physicalCap;\n"
        "    if (have >= target) {\n"
    )
    decision_probe = r'''    if (target > physicalCap) target = physicalCap;

    /* OFF target/extraNeeded is now frozen.  Only now pay GetState for already-stopped IDs. */
    rlfEligible++;
    if (rlfStopped.len() > 0) {
      rlfStoppedLines++;
      local rlfAt = 0;
      local rlfOff = 0;
      foreach (rv in rlfStopped) {
        if (!AIVehicle.IsValidVehicle(rv)) { rlfInvalidStopped++; continue; }
        rlfStateReads++;
        if (AIVehicle.GetState(rv) == AIVehicle.VS_AT_STATION) rlfAt++;
        else rlfOff++;
      }
      local rlfKind = ("kind" in line) ? line.kind : "unknown";
      if (rlfAt > 0) {
        rlfAtStation++;
        if (rlfKind == "pax") rlfAtStationPax++;
        else if (rlfKind == "freight") rlfAtStationFreight++;
      }
      if (rlfOff > 0) rlfOffStation++;
      local rlfFixWaiting = rlfOff > 0;
      local rlfFixExtra = 0;
      if (totalWaiting >= capacity && !rlfFixWaiting) {
        rlfFixExtra = totalWaiting / capacity;
        if (rlfFixExtra > 3) rlfFixExtra = 3;
      } else if (minRating < 65 && have < physicalCap && !rlfFixWaiting && money > 35000) {
        rlfFixExtra = 1;
      } else if (("lastProfit" in line) && line.lastProfit > 1000
                 && have < physicalCap && money > 60000 && !rlfFixWaiting) {
        rlfFixExtra = 1;
      }
      if (have + rlfFixExtra > physicalCap) rlfFixExtra = physicalCap - have;
      if (rlfFixExtra < 0) rlfFixExtra = 0;
      local rlfFixTarget = rlfBaseTarget;
      if (have + rlfFixExtra > rlfFixTarget) rlfFixTarget = have + rlfFixExtra;
      if (rlfFixTarget > physicalCap) rlfFixTarget = physicalCap;
      local rlfWaitChanged = isAnyWaiting && !rlfFixWaiting;
      if (rlfWaitChanged) {
        rlfWaitFlip++;
        if (rlfKind == "pax") rlfWaitFlipPax++;
        else if (rlfKind == "freight") rlfWaitFlipFreight++;
      }
      if (rlfFixExtra != extraNeeded) {
        rlfExtraFlip++;
        if (rlfKind == "pax") rlfExtraFlipPax++;
        else if (rlfKind == "freight") rlfExtraFlipFreight++;
      }
      if (rlfFixTarget != target) {
        rlfTargetFlip++;
        if (rlfKind == "pax") rlfTargetFlipPax++;
        else if (rlfKind == "freight") rlfTargetFlipFreight++;
      }
      if (have >= target && have < rlfFixTarget) rlfNewRefill++;
      local rlfOffNeed = (target > have) ? (target - have) : 0;
      local rlfFixNeed = (rlfFixTarget > have) ? (rlfFixTarget - have) : 0;
      rlfRefillDelta += rlfFixNeed - rlfOffNeed;
    }

    if (have >= target) {
'''
    road_text = replace_once(road_text, decision_anchor, decision_probe)

    end_anchor = "    OpexSign(anchor, \"RF|\" + year + \"|\" + line.lineId + \"|\" + refill.added + \"|\"\n                     + (refill.added > 0 ? refill.after : refill.reason));\n  }\n}\n"
    end_replacement = end_anchor[:-2] + r'''  ROAD_LOADING_EXPOSURE_DIAG.eligible += rlfEligible;
  ROAD_LOADING_EXPOSURE_DIAG.stopped += rlfStoppedLines;
  ROAD_LOADING_EXPOSURE_DIAG.state_reads += rlfStateReads;
  ROAD_LOADING_EXPOSURE_DIAG.invalid_stopped += rlfInvalidStopped;
  ROAD_LOADING_EXPOSURE_DIAG.at_station += rlfAtStation;
  ROAD_LOADING_EXPOSURE_DIAG.off_station += rlfOffStation;
  ROAD_LOADING_EXPOSURE_DIAG.wait_flip += rlfWaitFlip;
  ROAD_LOADING_EXPOSURE_DIAG.extra_flip += rlfExtraFlip;
  ROAD_LOADING_EXPOSURE_DIAG.target_flip += rlfTargetFlip;
  ROAD_LOADING_EXPOSURE_DIAG.new_refill += rlfNewRefill;
  ROAD_LOADING_EXPOSURE_DIAG.refill_delta_sum += rlfRefillDelta;
  ROAD_LOADING_EXPOSURE_DIAG.at_station_pax += rlfAtStationPax;
  ROAD_LOADING_EXPOSURE_DIAG.at_station_freight += rlfAtStationFreight;
  ROAD_LOADING_EXPOSURE_DIAG.wait_flip_pax += rlfWaitFlipPax;
  ROAD_LOADING_EXPOSURE_DIAG.wait_flip_freight += rlfWaitFlipFreight;
  ROAD_LOADING_EXPOSURE_DIAG.extra_flip_pax += rlfExtraFlipPax;
  ROAD_LOADING_EXPOSURE_DIAG.extra_flip_freight += rlfExtraFlipFreight;
  ROAD_LOADING_EXPOSURE_DIAG.target_flip_pax += rlfTargetFlipPax;
  ROAD_LOADING_EXPOSURE_DIAG.target_flip_freight += rlfTargetFlipFreight;
  if (rlfFlush != null) OpexRoadLoadingExposureLog(rlfFlush);
}
'''
    road_text = replace_once(road_text, end_anchor, end_replacement)
    road_path.write_text(road_text, encoding="utf-8")


def read_exposure(log_path: Path) -> list[dict[str, int | str]]:
    rows = []
    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PROBE_RE.search(raw)
        if match:
            rows.append(parse_fields(match.group(1)))
    return rows


def aggregate(rows_by_seed: dict[int, list[dict]]) -> dict:
    numeric = (
        "eligible", "stopped", "state_reads", "invalid_stopped", "at_station", "off_station",
        "wait_flip", "extra_flip", "target_flip", "new_refill", "refill_delta_sum",
        "at_station_pax", "at_station_freight", "wait_flip_pax", "wait_flip_freight",
        "extra_flip_pax", "extra_flip_freight", "target_flip_pax", "target_flip_freight",
    )
    totals = {name: 0 for name in numeric}
    for rows in rows_by_seed.values():
        for row in rows:
            for name in numeric:
                totals[name] += int(row.get(name, 0))
    if totals["at_station"] == 0:
        gate = "close_no_speed0_at_station"
    elif totals["wait_flip"] == 0:
        gate = "close_station_seen_but_isAnyWaiting_unchanged"
    elif totals["extra_flip"] == 0:
        gate = "close_isAnyWaiting_flip_but_extraNeeded_unchanged"
    elif totals["target_flip"] == 0:
        gate = "semantic_extraNeeded_exposure_only_target_unchanged"
    else:
        gate = "actionable_target_exposure_proved"
    return {"totals": totals, "exposure_gate": gate}


def stage(folder: Path) -> tuple[Path, Path, dict, dict]:
    production = ROOT / "ai" / "OpexAI"
    before = tree_hashes(production)
    target = folder / "copies" / "OpexAI"
    shutil.copytree(production, target)
    instrument(target)
    opponent = folder / "copies" / "AAAHogEx-115"
    shutil.copytree(ROOT / "ai" / "AAAHogEx-115", opponent)
    staged = tree_hashes(folder / "copies")
    return target, opponent, before, staged


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    if args.years != 3:
        parser.error("ce protocole d'exposition est fige a 3 ans")
    if tuple(args.seeds) != DEFAULT_SEEDS:
        parser.error(f"ce protocole est fige aux graines {DEFAULT_SEEDS}")
    if not 1 <= args.workers <= 3:
        parser.error("workers doit valoir 1..3")

    folder = new_directory(args.out, ROOT / "results/road_loading_fix_exposure")
    target, opponent, production_before, staged_before = stage(folder)
    plan = {
        "kind": "road_loading_fix_exposure_copied_source_not_economic_ab",
        "starting_year": START,
        "years": args.years,
        "seeds": list(args.seeds),
        "workers": args.workers,
        "policy": "live copied source; road_loading_fix=0; decision_log=0; probe_portfolio=0",
        "probe_semantics": (
            "OFF extraNeeded/target is computed first; GetState is called only for IDs already "
            "seen at speed 0, after the OFF target is frozen; no ON decision is executed"
        ),
        "production_hashes": production_before,
        "staged_hashes": staged_before,
        "economic_verdict": "not_evaluated",
        "prepare_only": bool(args.prepare_only),
    }
    write_new(folder / "plan.json", plan)

    if args.prepare_only:
        checks = {
            "production_sources_unchanged": production_before == tree_hashes(ROOT / "ai" / "OpexAI"),
            "road_loading_fix_still_default_off_in_copy": "ROAD_LOADING_FIX <- false;" in (target / "globals_pre.nut").read_text(encoding="utf-8"),
            "probe_staged_only": "ROAD_LOADING_EXPOSURE_DIAG" in (target / "globals_pre.nut").read_text(encoding="utf-8"),
        }
        write_new(folder / "prepare_report.json", {"checks": checks, "engine_executed": False})
        print(json.dumps({"folder": str(folder), "checks": checks}, indent=2), flush=True)
        if not all(checks.values()):
            raise SystemExit(1)
        return

    import openttdlab  # noqa: E402
    import diag_cadence_duel as duel  # noqa: E402

    arm = openttdlab.local_folder(
        str(target), "OpexAI",
        (("road_loading_fix", 0), ("decision_log", 0), ("probe_portfolio", 0)),
    )
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    cfg = duel.bench_v2.make_cfg(START)
    days = (date(START + args.years, 1, 1) - date(START, 1, 1)).days + 32
    experiments = [{
        "arm": "live_off_shadow",
        "seed": seed,
        "years": args.years,
        "days": days,
        "openttd_config": cfg,
        "ais": (arm, aaa),
        "log_path": str(folder / f"road_loading_off_seed{seed}.log"),
        "checkpoint_path": str(folder / f"road_loading_off_seed{seed}.jsonl"),
    } for seed in args.seeds]

    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(openttdlab.run_experiments(
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
        grouped[row["seed"]].append(row)
    games = [duel.finish_game(series, args.years) for series in grouped.values()]
    exposure = {
        seed: read_exposure(folder / f"road_loading_off_seed{seed}.log")
        for seed in args.seeds
    }
    expected_years = set(range(START, START + args.years))
    exposure_years = {
        seed: sorted(int(row["year"]) for row in rows)
        for seed, rows in exposure.items()
    }
    checks = {
        "all_games_valid": len(games) == len(args.seeds) and all(game.get("valid") for game in games),
        "all_exposure_years_present": all(set(years) == expected_years for years in exposure_years.values()),
        "production_sources_unchanged": production_before == tree_hashes(ROOT / "ai" / "OpexAI"),
        "staged_copies_unchanged_during_run": staged_before == tree_hashes(folder / "copies"),
    }
    report = {
        "checks": checks,
        "exposure_by_seed": exposure,
        "exposure_years": exposure_years,
        "aggregate": aggregate(exposure),
        "games": games,
        "economic_verdict": "not_evaluated",
        "instrumentation_risk": (
            "GetState and shadow arithmetic add NoAI opcodes and can perturb later cadence; "
            "therefore this report proves only mechanism exposure on the instrumented OFF trajectory"
        ),
    }
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "aggregate": report["aggregate"]}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
