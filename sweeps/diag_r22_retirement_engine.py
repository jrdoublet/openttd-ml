"""Directed OpenTTD qualification for R22 retirement retry semantics.

Runs only on a copied OpexAI tree. Production sources are hashed before/after.
Scenarios:
  active_save  - keep a real halt-to-depot order active past 90 days, prove the
                 retry does not toggle it off; cancel it deliberately, prove the
                 next retry restores it; save/reload the live ticket and sell once.
  maintenance  - present a real service-if-needed depot order and prove the due
                 retirement converts it to a halt order and advances attempts.
  timeout      - present an expired ticket and prove it is cancelled, removed and
                 the still-live vehicle is restored to the owning line inventory.

These are engineered mechanism tests, never economic benchmarks.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import openttdlab

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import save_load_roundtrip as reload  # noqa: E402


FIXTURE = r'''
FXR22 <- { scenario = "SCENARIO", phase = "search", vehicle = -1, lineId = -1,
           started = -1, depot = -1, expectedAttempts = 0 };

function FxR22Log(fields)
{
  AILog.Info("FXR22 " + fields + " date=" + AIDate.GetCurrentDate()
             + " tick=" + AIController.GetTick());
}

function FxR22Assert(ok, name)
{
  if (!ok) throw "FIXTURE_ASSERT R22 " + name;
}

function FxR22Ticket(ai)
{
  if (ai._vehiclesToRetire == null || !(FXR22.vehicle in ai._vehiclesToRetire)) return null;
  return ai._vehiclesToRetire[FXR22.vehicle];
}

function FxR22FindLine(ai)
{
  foreach (line in ai._lines) {
    if (line == null || !("lineId" in line) || !("mode" in line) || line.mode == "road") continue;
    if (FXR22.scenario == "maintenance" && line.mode != "rail") continue;
    if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
    if (OpexAirLineReequipPending(line)) continue;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsPrimaryVehicle(v)
          && !AIVehicle.IsStoppedInDepot(v))
        return { line = line, vehicle = v };
    }
  }
  return null;
}

function FxR22RemoveInventory(line, vehicle)
{
  for (local i = 0; i < line.vehicles.len(); i++) {
    if (line.vehicles[i] == vehicle) { line.vehicles.remove(i); break; }
  }
  if (("vehicle" in line) && line.vehicle == vehicle) {
    line.vehicle = line.vehicles.len() > 0 ? line.vehicles[0] : -1;
  }
  local n = line.vehicles.len();
  if ("vehCount" in line) line.vehCount = n; else line.vehCount <- n;
  if ("trains" in line) line.trains = n; else line.trains <- n;
}

function FxR22HasInventory(line, vehicle)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) return false;
  foreach (v in line.vehicles) if (v == vehicle) return true;
  return false;
}

function FxR22CurrentDepot(vehicle)
{
  if (!AIVehicle.IsValidVehicle(vehicle)) return { goto = false, flags = AIOrder.OF_INVALID, dest = -1 };
  local go = AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT);
  local flags = go ? AIOrder.GetOrderFlags(vehicle, AIOrder.ORDER_CURRENT) : AIOrder.OF_INVALID;
  local dest = go ? AIOrder.GetOrderDestination(vehicle, AIOrder.ORDER_CURRENT) : -1;
  return { goto = go, flags = flags, dest = dest };
}

function FxR22Arm(ai)
{
  local chosen = FxR22FindLine(ai);
  if (chosen == null) return false;
  local line = chosen.line;
  local vehicle = chosen.vehicle;
  local now = AIDate.GetCurrentDate();
  FXR22.vehicle = vehicle;
  FXR22.lineId = line.lineId;

  if (FXR22.scenario == "active_save") {
    if (!AIVehicle.SendVehicleToDepot(vehicle)) return false;
    local order = FxR22CurrentDepot(vehicle);
    FxR22Assert(order.goto && (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0, "initial_halt_order");
    FXR22.depot = order.dest;
    if (ai._vehiclesToRetire == null) ai._vehiclesToRetire = {};
    ai._vehiclesToRetire.rawset(vehicle, { lineId = line.lineId, startedDate = now,
                                          lastSendDate = now - 91, attempts = 1 });
    FxR22RemoveInventory(line, vehicle);
    /* The ticket date is intentionally backdated to put the production code at
     * its exact J+91 retry boundary immediately, while the engine order itself
     * is a real active manual halt-to-depot diversion. */
    FXR22.started = now;
    FXR22.expectedAttempts = 1;
    FXR22.phase = "active_due";
    FxR22Log("phase=armed scenario=active_save vehicle=" + vehicle + " line=" + line.lineId
             + " depot=" + FXR22.depot + " attempts=1");
    return true;
  }

  if (FXR22.scenario == "timeout") {
    if (ai._vehiclesToRetire == null) ai._vehiclesToRetire = {};
    ai._vehiclesToRetire.rawset(vehicle, { lineId = line.lineId,
                                          startedDate = now - SCRAP_TIMEOUT_YEARS * 365,
                                          lastSendDate = now - 91, attempts = 3 });
    FxR22RemoveInventory(line, vehicle);
    FXR22.phase = "timeout_due";
    FxR22Log("phase=armed scenario=timeout vehicle=" + vehicle + " line=" + line.lineId);
    return true;
  }
  return false;
}

function FxR22Tick(ai)
{
  if (FXR22.scenario != "maintenance" || FXR22.phase != "search" || ai._lines == null) return;
  foreach (line in ai._lines) {
    if (line == null || !("mode" in line) || line.mode != "rail"
        || !("vehicles" in line) || line.vehicles == null) continue;
    foreach (vehicle in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(vehicle) || !AIVehicle.IsPrimaryVehicle(vehicle)) continue;
      local order = FxR22CurrentDepot(vehicle);
      if (!order.goto || order.flags == AIOrder.OF_INVALID
          || (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0) continue;
      /* This is a naturally current service-only depot diversion produced by
       * OpenTTD, not an injected order. Put only the retirement ticket at its
       * J+91 boundary and invoke the production retirement function immediately
       * while ORDER_CURRENT still exposes the service order. */
      local now = AIDate.GetCurrentDate();
      FXR22.vehicle = vehicle;
      FXR22.lineId = line.lineId;
      FXR22.expectedAttempts = 2;
      if (ai._vehiclesToRetire == null) ai._vehiclesToRetire = {};
      ai._vehiclesToRetire.rawset(vehicle, { lineId = line.lineId, startedDate = now - 120,
                                            lastSendDate = now - 91, attempts = 1 });
      FxR22RemoveInventory(line, vehicle);
      FXR22.phase = "maintenance_due";
      FxR22Log("phase=maintenance_natural vehicle=" + vehicle + " line=" + line.lineId
               + " flags=" + order.flags + " depot=" + order.dest);
      ai._scrapRetiredVehicles(AIDate.GetYear(now));
      return;
    }
  }
}

function FxR22BeforeScrap(ai)
{
  if (FXR22.phase == "search") {
    if (FXR22.scenario != "maintenance") FxR22Arm(ai);
    return;
  }
  if (FXR22.scenario == "active_save" && FXR22.phase == "active_due") {
    local ticket = FxR22Ticket(ai);
    local order = FxR22CurrentDepot(FXR22.vehicle);
    FxR22Assert(ticket != null && ticket.attempts == 1, "active_ticket_before_retry");
    FxR22Assert(order.goto && (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0,
                "active_halt_before_retry");
    FxR22Log("phase=active_due attempts=" + ticket.attempts + " flags=" + order.flags);
  }
}

function FxR22AfterScrap(ai)
{
  if (FXR22.phase == "active_due") {
    local ticket = FxR22Ticket(ai);
    local order = FxR22CurrentDepot(FXR22.vehicle);
    FxR22Assert(ticket != null && ticket.attempts == 1, "active_retry_did_not_increment");
    FxR22Assert(order.goto && (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0,
                "active_retry_did_not_toggle");
    FxR22Log("phase=active_preserved pass=1 attempts=" + ticket.attempts);
    /* Deliberately lose the diversion: second engine call toggles the manual
     * depot order away. Make the ticket immediately due for the next scrap. */
    FxR22Assert(AIVehicle.SendVehicleToDepot(FXR22.vehicle), "deliberate_cancel");
    local lost = FxR22CurrentDepot(FXR22.vehicle);
    FxR22Assert(!lost.goto || (lost.flags & AIOrder.OF_STOP_IN_DEPOT) == 0,
                "diversion_lost_precondition");
    if (AIVehicle.IsStoppedInDepot(FXR22.vehicle)) AIVehicle.StartStopVehicle(FXR22.vehicle);
    ticket.rawset("lastSendDate", AIDate.GetCurrentDate() - 91);
    FXR22.phase = "lost_due";
    FxR22Log("phase=diversion_lost pass=1");
    return;
  }

  if (FXR22.phase == "lost_due") {
    local ticket = FxR22Ticket(ai);
    local order = FxR22CurrentDepot(FXR22.vehicle);
    FxR22Assert(ticket != null && ticket.attempts == 2, "lost_retry_incremented_once");
    FxR22Assert(order.goto && (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0,
                "lost_retry_restored_halt");
    FXR22.expectedAttempts = 2;
    FXR22.phase = "checkpoint";
    FxR22Log("phase=retry_restored pass=1 attempts=" + ticket.attempts);
    /* Hold the AI at the exact live-ticket boundary. Monthly engine saves keep
     * happening while the controller sleeps. */
    while (true) AIController.Sleep(100);
  }

  if (FXR22.phase == "maintenance_due") {
    local ticket = FxR22Ticket(ai);
    local order = FxR22CurrentDepot(FXR22.vehicle);
    FxR22Assert(ticket != null && ticket.attempts == 2, "maintenance_attempt_increment");
    FxR22Assert(order.goto && (order.flags & AIOrder.OF_STOP_IN_DEPOT) != 0,
                "maintenance_converted_to_halt");
    FXR22.phase = "done";
    FxR22Log("phase=maintenance_pass pass=1 attempts=" + ticket.attempts + " flags=" + order.flags);
    while (true) AIController.Sleep(100);
  }

  if (FXR22.phase == "timeout_due") {
    local line = ai._findLineById(FXR22.lineId);
    FxR22Assert(FxR22Ticket(ai) == null, "timeout_ticket_removed");
    FxR22Assert(AIVehicle.IsValidVehicle(FXR22.vehicle), "timeout_vehicle_still_live");
    FxR22Assert(FxR22HasInventory(line, FXR22.vehicle), "timeout_inventory_restored");
    FXR22.phase = "done";
    FxR22Log("phase=timeout_pass pass=1 vehicle=" + FXR22.vehicle + " line=" + FXR22.lineId);
    while (true) AIController.Sleep(100);
  }

  if (FXR22.phase == "reloaded_wait_sale") {
    if (!AIVehicle.IsValidVehicle(FXR22.vehicle)) {
      FxR22Assert(FxR22Ticket(ai) == null, "sale_ticket_removed");
      FXR22.phase = "done";
      FxR22Log("phase=reload_sale_pass pass=1 vehicle=" + FXR22.vehicle);
      while (true) AIController.Sleep(100);
    }
  }
}

function FxR22Save(ai, saveObj)
{
  FxR22Log("phase=save state=" + FXR22.phase + " vehicle=" + FXR22.vehicle
           + " expected_attempts=" + FXR22.expectedAttempts);
  saveObj.r22Fixture <- FXR22;
}

function FxR22Load(data)
{
  if (data != null && ("r22Fixture" in data)) FXR22 = data.r22Fixture;
}

function FxR22Resume(ai)
{
  if (!ai._loadedFromSave || FXR22.scenario != "active_save" || FXR22.phase != "checkpoint") return;
  local ticket = FxR22Ticket(ai);
  FxR22Assert(ticket != null && ticket.attempts == FXR22.expectedAttempts, "reload_ticket_persisted");
  FxR22Assert(AIVehicle.IsValidVehicle(FXR22.vehicle), "reload_vehicle_valid");
  FXR22.phase = "reloaded_wait_sale";
  FxR22Log("phase=reload_pass pass=1 attempts=" + ticket.attempts
           + " stopped_in_depot=" + (AIVehicle.IsStoppedInDepot(FXR22.vehicle) ? 1 : 0));
}
'''


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(folder: Path):
    return {p.relative_to(folder).as_posix(): digest(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected exactly one staging anchor: {old!r}")
    return text.replace(old, new)


def stage_ai(folder: Path, scenario: str) -> Path:
    source = ROOT / "ai" / "OpexAI"
    target = folder / "ai"
    shutil.copytree(source, target)
    (target / "r22_fixture.nut").write_text(FIXTURE.replace("SCENARIO", scenario), encoding="utf-8")

    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, 'require("task_report.nut");',
                        'require("r22_fixture.nut");\nrequire("task_report.nut");')
    text = replace_once(text, '  if (this._loadedFromSave) this._reconcileAfterLoad();',
                        '  if (this._loadedFromSave) this._reconcileAfterLoad();\n  FxR22Resume(this);')
    text = replace_once(text, '    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;',
                        '    FxR22Tick(this);\n    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;')
    main.write_text(text, encoding="utf-8")

    report = target / "task_report.nut"
    text = report.read_text(encoding="utf-8")
    text = replace_once(text, 'function OpexAI::_scrapRetiredVehicles(year)\n{',
                        'function OpexAI::_scrapRetiredVehicles(year)\n{\n  FxR22BeforeScrap(this);')
    text = replace_once(text,
                        '  if (this._unprofitableStreaks != null) {\n    foreach (vehicle in clearStreaks) {\n      if (vehicle in this._unprofitableStreaks) delete this._unprofitableStreaks[vehicle];\n    }\n  }\n}',
                        '  if (this._unprofitableStreaks != null) {\n    foreach (vehicle in clearStreaks) {\n      if (vehicle in this._unprofitableStreaks) delete this._unprofitableStreaks[vehicle];\n    }\n  }\n  FxR22AfterScrap(this);\n}')
    report.write_text(text, encoding="utf-8")

    persist = target / "persist.nut"
    text = persist.read_text(encoding="utf-8")
    text = replace_once(text, '  return saveObj;\n}\nfunction OpexAI::Load(version, data)',
                        '  FxR22Save(this, saveObj);\n  return saveObj;\n}\nfunction OpexAI::Load(version, data)')
    text = replace_once(text, '  if (data == null) return;\n',
                        '  if (data == null) return;\n  FxR22Load(data);\n')
    persist.write_text(text, encoding="utf-8")
    return target


def checkpoint_dates(log: str, state: str):
    return {str(date(1, 1, 1) + timedelta(days=int(day) - 365)) for day in re.findall(
        rf"FXR22 phase=save state={re.escape(state)} .* date=(\d+)", log)}


def choose_checkpoint(paths, log: str, state: str):
    records = [reload.parse_sav_file(path) for path in paths]
    eligible = [row for row in records if row["date"] in checkpoint_dates(log, state)]
    if not eligible:
        raise RuntimeError(f"no savegame at R22 state={state}")
    return min(eligible, key=lambda row: row["date"])


def markers(log: str):
    return sorted(set(line.strip() for line in (log or "").splitlines() if "FXR22 " in line))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("active_save", "maintenance", "timeout"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years-a", type=int, default=2)
    parser.add_argument("--years-b", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    folder = args.out if args.out.is_absolute() else ROOT / args.out
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir(parents=True)

    source = ROOT / "ai" / "OpexAI"
    before = tree_hashes(source)
    staged = stage_ai(folder, args.scenario)
    staged_before_run = tree_hashes(staged)

    reload.WORK_DIR = folder / "work"
    reload.CACHE_DIR = reload.WORK_DIR / "cache"
    reload.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    reload.SCRIPT_DEBUG_LEVEL = "4"
    cfg = reload.bench_v2.make_cfg(1970)
    if args.scenario == "maintenance":
        cfg += "\n[vehicle]\nservint_trains = 1\n"
    arm = openttdlab.local_folder(str(staged), "OpexAI",
                                  (("decision_log", 1), ("save_full_state", 1),
                                   ("policy_vehicle_events", 0)))
    phase_a = folder / "phase_a"
    phase_a.mkdir()
    rows_a, log_a, saves_a = reload.run_phase_a(
        args.seed, args.years_a, arm, cfg, phase_a / "rows.jsonl", phase_a / "saves")
    (phase_a / "engine.log").write_text(log_a or "", encoding="utf-8")

    errors_a = "FIXTURE_ASSERT" in (log_a or "") or "Your script made an error" in (log_a or "") \
        or "The script died unexpectedly" in (log_a or "")
    report = {
        "scenario": args.scenario,
        "seed": args.seed,
        "phase_a_markers": markers(log_a),
        "phase_a_script_error": errors_a,
        "production_sources_unchanged": before == tree_hashes(source),
        "staged_copy_unchanged_during_run": staged_before_run == tree_hashes(staged),
    }

    if args.scenario == "active_save":
        chosen = choose_checkpoint(saves_a, log_a, "checkpoint")
        phase_b = folder / "phase_b"
        phase_b.mkdir()
        rows_b, log_b, saves_b = reload.run_phase_b(
            args.seed, args.years_b, arm, cfg, phase_b / "rows.jsonl", chosen["path"], phase_b / "saves")
        (phase_b / "engine.log").write_text(log_b or "", encoding="utf-8")
        errors_b = "FIXTURE_ASSERT" in (log_b or "") or "Your script made an error" in (log_b or "") \
            or "The script died unexpectedly" in (log_b or "")
        report.update({
            "checkpoint": {"path": chosen["path"], "date": chosen["date"]},
            "phase_b_markers": markers(log_b),
            "phase_b_script_error": errors_b,
            "active_preserved": "phase=active_preserved pass=1" in (log_a or ""),
            "lost_diversion_retried": "phase=retry_restored pass=1" in (log_a or ""),
            "reload_ticket_persisted": "phase=reload_pass pass=1" in (log_b or ""),
            "sale_after_reload": "phase=reload_sale_pass pass=1" in (log_b or ""),
        })
        passed = (not errors_a and not errors_b and report["active_preserved"]
                  and report["lost_diversion_retried"] and report["reload_ticket_persisted"]
                  and report["sale_after_reload"])
    elif args.scenario == "maintenance":
        report["maintenance_converted"] = "phase=maintenance_pass pass=1" in (log_a or "")
        passed = not errors_a and report["maintenance_converted"]
    else:
        report["timeout_restored"] = "phase=timeout_pass pass=1" in (log_a or "")
        passed = not errors_a and report["timeout_restored"]

    report["pass"] = bool(passed and report["production_sources_unchanged"]
                          and report["staged_copy_unchanged_during_run"])
    (folder / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["pass"]:
        raise RuntimeError("R22 directed qualification incomplete")


if __name__ == "__main__":
    main()
