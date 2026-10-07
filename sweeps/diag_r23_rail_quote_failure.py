"""Directed R23 engine qualification on an isolated copy of OpexAI.

The fixture leaves route generation and A* untouched.  Immediately before the
normal rail quote it places a *real* company HQ on an interior path tile.  The
normal AITestMode quote must then fail closed after having simulated the station
work preceding that tile.  The test copy asserts that no rail construction was
committed and that the candidate's model capital was not promoted to an actual
capital value.

This is mechanism evidence, never an economic benchmark.  Production sources are
hashed before/after and are not edited by the fixture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

HELPER = r'''
FXR23 <- { armed = false, done = false };

function FxR23Log(fields)
{
  AILog.Info("FXR23 " + fields + " date=" + AIDate.GetCurrentDate()
             + " tick=" + AIController.GetTick());
}

function FxR23BeforeQuote(candidate, plan)
{
  if (FXR23.armed || FXR23.done || plan == null || !("ok" in plan) || !plan.ok
      || !("tiles" in plan) || plan.tiles == null || plan.tiles.len() < 7) return;

  /* Keep clear of both station throats.  Only ordinary one-tile rail segments
   * are eligible, so the injected HQ targets the BuildRail branch rather than a
   * bridge/tunnel command. */
  for (local i = 3; i < plan.tiles.len() - 3; i++) {
    local prev = plan.tiles[i - 1];
    local cur = plan.tiles[i];
    local next = plan.tiles[i + 1];
    if (!AIMap.IsValidTile(cur) || prev == next) continue;
    if (AIMap.DistanceManhattan(prev, cur) != 1 || AIMap.DistanceManhattan(cur, next) != 1) continue;
    if (AIBridge.IsBridgeTile(cur) || AITunnel.IsTunnelTile(cur)) continue;

    local beforeStations = AIStationList(AIStation.STATION_TRAIN).Count();
    local beforeCapital = candidate.capital;
    local beforeActual = (("capitalIsActual" in candidate) && candidate.capitalIsActual) ? 1 : 0;
    local ok = AICompany.BuildCompanyHQ(cur);
    FxR23Log("phase=obstacle ok=" + (ok ? 1 : 0) + " tile=" + cur + " slot=" + i
             + " capital=" + beforeCapital + " actual=" + beforeActual);
    if (!ok) continue;

    FXR23 = { armed = true, done = false, tile = cur, capital = beforeCapital,
              actual = beforeActual, stations = beforeStations };
    return;
  }
}

function FxR23AfterQuote(candidate, plan, result, failure)
{
  if (!FXR23.armed || FXR23.done) return;
  local reason = ("reason" in failure) ? failure.reason : "UNKNOWN";
  local failTile = ("tile" in failure) ? failure.tile : -1;
  local dx = AIMap.IsValidTile(failTile) ? AIMap.GetTileX(failTile) - AIMap.GetTileX(FXR23.tile) : -99;
  local dy = AIMap.IsValidTile(failTile) ? AIMap.GetTileY(failTile) - AIMap.GetTileY(FXR23.tile) : -99;
  /* BuildCompanyHQ occupies a 2x2 footprint rooted at the requested tile. */
  local hitInjectedHQ = dx >= 0 && dx <= 1 && dy >= 0 && dy <= 1;
  local afterActual = (("capitalIsActual" in candidate) && candidate.capitalIsActual) ? 1 : 0;
  local afterStations = AIStationList(AIStation.STATION_TRAIN).Count();
  local pass = reason == "TRKFAIL" && hitInjectedHQ
      && result.actualCost == 0 && candidate.capital == FXR23.capital
      && afterActual == FXR23.actual && afterStations == FXR23.stations;
  FxR23Log("phase=result pass=" + (pass ? 1 : 0) + " reason=" + reason
           + " err=" + (("error" in failure) ? failure.error : 0)
           + " tile=" + failTile + " hq_dx=" + dx + " hq_dy=" + dy
           + " result_cost=" + result.actualCost
           + " capital_before=" + FXR23.capital + " capital_after=" + candidate.capital
           + " actual_before=" + FXR23.actual + " actual_after=" + afterActual
           + " stations_before=" + FXR23.stations + " stations_after=" + afterStations);
  FXR23.done = true;
  if (!pass) throw "FIXTURE_ASSERT R23_QUOTE_FAIL";
}
'''


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(folder: Path):
    return {p.relative_to(folder).as_posix(): digest(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected one staging anchor: {old!r}")
    return text.replace(old, new)


def stage_ai(target: Path) -> Path:
    source = ROOT / "ai" / "OpexAI"
    shutil.copytree(source, target)
    (target / "r23_fixture.nut").write_text(HELPER, encoding="utf-8")

    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, 'function OpexAI::Start()',
                        'require("r23_fixture.nut");\n\nfunction OpexAI::Start()')
    main.write_text(text, encoding="utf-8")

    builder = target / "builder_rail.nut"
    text = builder.read_text(encoding="utf-8")
    text = replace_once(text,
                        '  if (RAIL_DEVIS) {\n    local quoteFailure = {};',
                        '  if (RAIL_DEVIS) {\n    FxR23BeforeQuote(candidate, plan);\n    local quoteFailure = {};')
    text = replace_once(text,
                        '      result.quoteFailure <- quoteFailure;\n      return result;',
                        '      result.quoteFailure <- quoteFailure;\n'
                        '      FxR23AfterQuote(candidate, plan, result, quoteFailure);\n'
                        '      return result;')
    builder.write_text(text, encoding="utf-8")
    return target


def keep(row):
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "output": row.get("output", ""),
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=65537)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path, required=True,
                        help="new result directory under results/")
    args = parser.parse_args()
    folder = args.out if args.out.is_absolute() else ROOT / args.out
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir(parents=True)

    source = ROOT / "ai" / "OpexAI"
    before = tree_hashes(source)
    staged = stage_ai(folder / "ai")
    staged_hash = tree_hashes(staged)

    real_check_output = openttdlab.subprocess.check_output
    def with_script_debug(command, *rest, **kwargs):
        command = tuple(command)
        if any(str(part).startswith("-vnull") for part in command):
            command = command[:1] + ("-d", "script=4") + command[1:]
        return real_check_output(command, *rest, **kwargs)
    openttdlab.subprocess.check_output = with_script_debug

    try:
        ai = local_folder(str(staged), "OpexAI", (("decision_log", 1),))
        experiments = [{"seed": args.seed, "days": 365 * args.years,
                        "openttd_config": CFG, "ais": (ai,)}]
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=experiments,
            max_workers=1,
            result_processor=keep,
            ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                          bananas_ai_library("5046524c", "Pathfinder.Rail")),
        ))
    finally:
        openttdlab.subprocess.check_output = real_check_output

    output = "\n".join(row["output"] for row in rows)
    results = re.findall(r"FXR23 phase=result pass=(\d).*", output)
    obstacle = re.findall(r"FXR23 phase=obstacle ok=1.*", output)
    quote_fail = re.findall(r"RAIL_QUOTE_FAIL .*reason=TRKFAIL.*", output)
    script_error = "Your script made an error" in output or "The script died unexpectedly" in output
    report = {
        "seed": args.seed,
        "years": args.years,
        "mechanism_exposed": bool(obstacle),
        "quote_fail_logged": bool(quote_fail),
        "fixture_pass": bool(results) and set(results) == {"1"},
        "script_error": script_error,
        "production_sources_unchanged": before == tree_hashes(source),
        "staged_copy_unchanged_during_run": staged_hash == tree_hashes(staged),
        "result_lines": sorted(set(re.findall(r"FXR23 phase=result .*", output))),
        "obstacle_lines": sorted(set(obstacle)),
        "quote_fail_lines": sorted(set(quote_fail)),
    }
    (folder / "engine.log").write_text(output, encoding="utf-8")
    (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not (report["mechanism_exposed"] and report["quote_fail_logged"]
            and report["fixture_pass"] and not report["script_error"]
            and report["production_sources_unchanged"] and report["staged_copy_unchanged_during_run"]):
        raise RuntimeError("R23 directed engine qualification incomplete")


if __name__ == "__main__":
    main()
