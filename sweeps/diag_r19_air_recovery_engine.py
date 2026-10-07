"""Directed engine qualification for R19 air rollback safety guards.

Runs on a copied OpexAI tree and waits for a normal live air line. It then
exercises production rollback helpers against real airports/aircraft:
  * a running aircraft keeps the rollback pending and prevents airport removal;
  * an airport used by a live line remains tracked and is not removed;
  * a reused endpoint, represented by the production `null` rollback argument,
    is never inserted into `ticket.airports` and remains physically present.

This is mechanism evidence only, not an economic benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
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

FIXTURE = r'''
FXR19 <- { done = false };

function FxR19Log(fields)
{
  AILog.Info("FXR19 " + fields + " date=" + AIDate.GetCurrentDate()
             + " tick=" + AIController.GetTick());
}

function FxR19Assert(ok, name)
{
  if (!ok) throw "FIXTURE_ASSERT R19 " + name;
}

function FxR19AirLine(ai)
{
  if (ai._lines == null) return null;
  foreach (line in ai._lines) {
    if (line == null || !("mode" in line) || line.mode != "air") continue;
    if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
    if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) continue;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsPrimaryVehicle(v)
          && !AIVehicle.IsStoppedInDepot(v)) return { line = line, vehicle = v };
    }
  }
  return null;
}

function FxR19CancelManualDepot(vehicle)
{
  if (!AIVehicle.IsValidVehicle(vehicle)) return;
  if (!AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)) return;
  local flags = AIOrder.GetOrderFlags(vehicle, AIOrder.ORDER_CURRENT);
  if (flags != AIOrder.OF_INVALID && (flags & AIOrder.OF_STOP_IN_DEPOT) != 0)
    AIVehicle.SendVehicleToDepot(vehicle);
}

function FxR19Tick(ai)
{
  if (FXR19.done) return;
  local chosen = FxR19AirLine(ai);
  if (chosen == null) return;
  local line = chosen.line;
  local vehicle = chosen.vehicle;
  local airportA = line.stationA;
  local airportB = line.stationB;
  FxR19Assert(AIAirport.IsAirportTile(airportA) && AIAirport.IsAirportTile(airportB),
              "live_airports_precondition");

  /* 1) Real running aircraft: production cleanup must leave it in `remaining`
   * and return before any airport-removal loop. */
  local running = { version = 1, vehicles = [vehicle], airports = [airportA],
                    pairKey = "fx|running", nextDate = 0 };
  local runningDone = OpexAirContinueRollback(running, ai._lines);
  FxR19Assert(!runningDone && running.vehicles.len() == 1,
              "running_aircraft_keeps_ticket");
  FxR19Assert(running.airports.len() == 1 && AIAirport.IsAirportTile(airportA),
              "running_aircraft_blocks_demolition");
  FxR19CancelManualDepot(vehicle);
  FxR19Log("phase=running_block pass=1 vehicle=" + vehicle + " airport=" + airportA);

  /* 2) No ticket aircraft left, but the live line still uses airport A. Both
   * logical-line and physical station-user guards must make removal fail closed. */
  local occupied = { version = 1, vehicles = [], airports = [airportA],
                     pairKey = "fx|occupied", nextDate = 0 };
  local occupiedDone = OpexAirContinueRollback(occupied, ai._lines);
  FxR19Assert(!occupiedDone && occupied.airports.len() == 1
              && occupied.airports[0] == airportA && AIAirport.IsAirportTile(airportA),
              "occupied_airport_preserved");
  FxR19Log("phase=occupied pass=1 airport=" + airportA
           + " station=" + AIStation.GetStationID(airportA));

  /* 3) Production rollback interface for a reused A endpoint passes null. Use
   * real live airports so we can assert the reusable hub is never published as
   * cleanup ownership. Airport B is deliberately still used, so the resulting
   * ticket remains pending and can be inspected safely. */
  local before = OPEX_AIR_ROLLBACKS.len();
  OpexAirRollback(null, airportB, [], "fx|reuse");
  FxR19Assert(OPEX_AIR_ROLLBACKS.len() == before + 1, "reuse_ticket_pending");
  local ticket = OPEX_AIR_ROLLBACKS[OPEX_AIR_ROLLBACKS.len() - 1];
  FxR19Assert(ticket.airports.len() == 1 && ticket.airports[0] == airportB,
              "only_new_endpoint_owned");
  foreach (tile in ticket.airports) FxR19Assert(tile != airportA, "reused_hub_excluded");
  FxR19Assert(AIAirport.IsAirportTile(airportA), "reused_hub_still_present");
  OPEX_AIR_ROLLBACKS.pop(); // fixture-owned synthetic ticket only
  FxR19Log("phase=reuse_hub pass=1 hub=" + airportA + " owned_endpoint=" + airportB);

  FXR19.done = true;
  FxR19Log("phase=complete pass=1 line=" + line.lineId);
  while (true) AIController.Sleep(100);
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


def stage_ai(folder: Path) -> Path:
    source = ROOT / "ai" / "OpexAI"
    target = folder / "ai"
    shutil.copytree(source, target)
    (target / "r19_fixture.nut").write_text(FIXTURE, encoding="utf-8")
    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, 'function OpexAI::Start()',
                        'require("r19_fixture.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text,
                        '    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;',
                        '    FxR19Tick(this);\n    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;')
    main.write_text(text, encoding="utf-8")
    return target


_REAL = openttdlab.subprocess.check_output


def _debug(command, *args, **kwargs):
    command = tuple(command)
    if any(str(part).startswith("-vnull") for part in command):
        command = command[:1] + ("-d", "script=4") + command[1:]
    return _REAL(command, *args, **kwargs)


def keep(row):
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "output": row.get("output", "")},)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    folder = args.out if args.out.is_absolute() else ROOT / args.out
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir(parents=True)

    source = ROOT / "ai" / "OpexAI"
    before = tree_hashes(source)
    staged = stage_ai(folder)
    staged_before = tree_hashes(staged)
    openttdlab.subprocess.check_output = _debug
    try:
        ai = local_folder(str(staged), "OpexAI", (("decision_log", 1),))
        rows = list(run_experiments(
            openttd_version="15.3", opengfx_version="7.1", max_workers=1,
            experiments=[{"seed": args.seed, "days": 365 * args.years,
                          "openttd_config": CFG, "ais": (ai,)}],
            result_processor=keep,
            ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                          bananas_ai_library("5046524c", "Pathfinder.Rail")),
        ))
    finally:
        openttdlab.subprocess.check_output = _REAL

    output = "\n".join(row["output"] for row in rows)
    log_lines = sorted(set(line.strip() for line in output.splitlines() if "FXR19 " in line))
    script_error = "FIXTURE_ASSERT" in output or "Your script made an error" in output \
        or "The script died unexpectedly" in output
    report = {
        "seed": args.seed,
        "years": args.years,
        "running_aircraft_blocks_demolition": "phase=running_block pass=1" in output,
        "occupied_airport_preserved": "phase=occupied pass=1" in output,
        "reused_hub_excluded": "phase=reuse_hub pass=1" in output,
        "complete": "phase=complete pass=1" in output,
        "script_error": script_error,
        "production_sources_unchanged": before == tree_hashes(source),
        "staged_copy_unchanged_during_run": staged_before == tree_hashes(staged),
        "markers": log_lines,
    }
    report["pass"] = (all(report[key] for key in (
        "running_aircraft_blocks_demolition", "occupied_airport_preserved",
        "reused_hub_excluded", "complete", "production_sources_unchanged",
        "staged_copy_unchanged_during_run")) and not script_error)
    (folder / "engine.log").write_text(output, encoding="utf-8")
    (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["pass"]:
        raise RuntimeError("R19 directed qualification incomplete")


if __name__ == "__main__":
    main()
